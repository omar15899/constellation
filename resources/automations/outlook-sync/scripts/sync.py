from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from classify import Classification, Classifier, message_features
from config import (
    BY_MESSAGE_DIR,
    DIGEST_DIR,
    INDEX_PATH,
    ROOT_FOLDER_NAME,
    SKIP_WELL_KNOWN,
    SNAPSHOTS_DIR,
    SYNC_STATE_PATH,
    BACKFILL_DIR,
    OutlookConfig,
    ensure_dirs,
    load_config,
    safe_id,
)
from graph_client import Folder, GraphClient, GraphError
from rules import Taxonomy

STATE_VERSION = 1


@dataclass
class SyncSummary:
    folders: int = 0
    fetched: int = 0
    classified: int = 0
    labeled: int = 0
    moved: int = 0
    rescued: int = 0
    junked: int = 0
    dry_run: bool = True
    errors: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _append_undo(entry: dict) -> None:
    BACKFILL_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKFILL_DIR / f"undo_sync_{_utc_date()}.json"
    entries = _load_json(path, [])
    if not isinstance(entries, list):
        entries = []
    entries.append(entry)
    _atomic_write_json(path, entries)


def _from_display(msg: dict) -> str:
    addr = (msg.get("from") or {}).get("emailAddress", {}) or {}
    name = addr.get("name") or ""
    email = addr.get("address") or ""
    if name and email:
        return f"{name} <{email}>"
    return email or name or "unknown"


def _write_raw_landing(msg: dict, classification: Classification, action: str) -> None:
    imid = msg.get("internetMessageId") or msg.get("id") or ""
    record = dict(msg)
    record["_omaros"] = {
        "category": classification.category,
        "confidence": classification.confidence,
        "source": classification.source,
        "reason": classification.reason,
        "action": action,
        "ts": _now_iso(),
    }
    path = BY_MESSAGE_DIR / f"{safe_id(imid)}.json"
    _atomic_write_json(path, record)


def _write_snapshot(batch: list[dict]) -> None:
    if not batch:
        return
    path = SNAPSHOTS_DIR / f"{_utc_stamp()}.json"
    base = path
    counter = 1
    while path.exists():
        path = base.with_name(f"{base.stem}_{counter}{base.suffix}")
        counter += 1
    _atomic_write_json(path, batch)


def _resolve_target_folder_id(
    client: GraphClient, target_folder: str | None, root_id: str | None
) -> tuple[str, str | None]:
    """Resolve a category's target folder under the OmarOS root. Returns (root_id, dest_id)."""
    if not target_folder:
        return root_id or "", None
    if root_id is None:
        root_id = client.ensure_folder(ROOT_FOLDER_NAME)
    dest_id = client.ensure_folder(target_folder, root_id)
    return root_id, dest_id


def _decide_action(
    classification: Classification,
    folder: Folder,
    taxonomy: Taxonomy,
    cfg: OutlookConfig,
    effective_mode: str,
    junk_id: str,
    inbox_id: str,
) -> tuple[str, str | None]:
    """Return (action, dest_folder_id_or_None). action in label|to_junk|rescue|move."""
    category = classification.category
    confidence = classification.confidence
    is_junk_folder = folder.well_known_name == "junkemail" or junk_id == folder.id

    if (
        category == taxonomy.junk_category
        and not is_junk_folder
        and confidence >= cfg.move_confidence_threshold
    ):
        return "to_junk", junk_id

    if (
        taxonomy.rescue_from_junk
        and is_junk_folder
        and category != taxonomy.junk_category
        and confidence >= cfg.rescue_threshold
    ):
        return "rescue", inbox_id

    if effective_mode == "move" and category != taxonomy.junk_category:
        cat = taxonomy.get(category) if category else None
        if cat is not None and cat.target_folder and confidence >= cfg.move_confidence_threshold:
            return "move", None  # dest resolved lazily by caller (needs root)

    return "label", None


def run_sync(
    *,
    dry_run: bool = True,
    mode: str | None = None,
    only_folders: list[str] | None = None,
    limit: int | None = None,
) -> SyncSummary:
    ensure_dirs()
    cfg = load_config()
    effective_mode = mode or cfg.mode
    summary = SyncSummary(dry_run=dry_run)

    client = GraphClient.from_config()
    taxonomy = Taxonomy.load()
    clf = Classifier(
        taxonomy,
        cfg.model,
        cfg.escalation_model,
        escalation_threshold=cfg.escalation_threshold,
    )

    state = _load_json(SYNC_STATE_PATH, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("version", STATE_VERSION)
    state.setdefault("delta_links", {})
    state.setdefault("processed", {})
    delta_links: dict[str, str] = state["delta_links"]
    processed: dict[str, dict] = state["processed"]

    index = _load_json(INDEX_PATH, {})
    if not isinstance(index, dict):
        index = {}

    junk_id = client.well_known_folder_id("junkemail")
    inbox_id = client.well_known_folder_id("inbox")

    folders = client.list_folders()
    only = {f.lower() for f in only_folders} if only_folders else None
    watch = set(cfg.watch_folders or [])
    omaros_root_ids = {f.id for f in folders if f.display_name == ROOT_FOLDER_NAME}
    selected: list[Folder] = []
    for folder in folders:
        if folder.well_known_name in SKIP_WELL_KNOWN:
            continue
        if folder.display_name in cfg.skip_folders:
            continue
        # Never reprocess our own destination tree (OmarOS root + its children).
        if folder.id in omaros_root_ids or folder.parent_id in omaros_root_ids:
            continue
        if only is not None:
            if folder.display_name.lower() not in only:
                continue
        elif watch and folder.well_known_name not in watch:
            # Default incremental run: only watch the inbox (and any configured
            # well-known folders), leaving the user's curated folders untouched.
            continue
        selected.append(folder)
    summary.folders = len(selected)

    root_id: str | None = None
    digest_actions: list[dict] = []
    digest_counts: dict[str, int] = {}

    for folder in selected:
        try:
            messages, new_link = client.delta(
                folder.id, delta_links.get(folder.id)
            )
        except GraphError as exc:
            summary.errors.append(f"delta failed for {folder.display_name}: {exc}")
            continue

        if limit is not None:
            messages = messages[:limit]

        # delta can return removed/tombstone entries lacking a usable id; skip them.
        messages = [
            m for m in messages if m.get("id") and "@removed" not in m
        ]
        if not messages:
            if new_link:
                delta_links[folder.id] = new_link
            continue

        summary.fetched += len(messages)

        try:
            classifications = clf.classify(messages)
        except Exception as exc:  # classification must not abort the whole run
            summary.errors.append(
                f"classification failed for {folder.display_name}: {exc}"
            )
            if new_link:
                delta_links[folder.id] = new_link
            continue
        summary.classified += len(classifications)

        by_imid = {c.internet_message_id: c for c in classifications}
        batch_for_snapshot: list[dict] = []

        for msg in messages:
            imid = msg.get("internetMessageId") or ""
            classification = by_imid.get(imid)
            if classification is None:
                feats = message_features(msg)
                fallback_category = (
                    "Archive" if taxonomy.get("Archive") else taxonomy.category_ids()[-1]
                )
                classification = Classification(
                    internet_message_id=feats["internet_message_id"],
                    message_id=feats["id"],
                    category=fallback_category,
                    confidence=0.0,
                    reason="no classification returned",
                    source="fallback",
                )

            message_id = msg.get("id") or classification.message_id
            category = classification.category
            confidence = classification.confidence

            prior = processed.get(imid)
            already = (
                prior is not None
                and prior.get("category") == category
                and prior.get("folder") == folder.id
            )
            if already:
                # Same category + folder as last run: idempotent no-op. Do not
                # re-label on Graph and do not rewrite landing/index/state.
                continue

            action, dest_id = _decide_action(
                classification,
                folder,
                taxonomy,
                cfg,
                effective_mode,
                junk_id,
                inbox_id,
            )

            digest_counts[category] = digest_counts.get(category, 0) + 1
            if category == "Action":
                digest_actions.append(
                    {
                        "from": _from_display(msg),
                        "subject": msg.get("subject") or "(no subject)",
                    }
                )

            _write_raw_landing(msg, classification, action)
            batch_for_snapshot.append(
                {
                    "id": message_id,
                    "internetMessageId": imid,
                    "subject": msg.get("subject"),
                    "from": _from_display(msg),
                    "receivedDateTime": msg.get("receivedDateTime"),
                    "parentFolderId": folder.id,
                    "_category": category,
                    "_confidence": confidence,
                    "_source": classification.source,
                    "_action": action,
                }
            )

            applied_action = action
            new_message_id = message_id

            if dry_run:
                # compute, log, do not write.
                pass
            else:
                cat_obj = taxonomy.get(category)
                color = (cat_obj.color if cat_obj and cat_obj.color else "preset0")
                try:
                    client.ensure_master_category(category, color)
                    client.set_categories(message_id, [category])
                    summary.labeled += 1
                except GraphError as exc:
                    summary.errors.append(
                        f"label failed {imid}: {exc}"
                    )

                if action in ("to_junk", "rescue", "move"):
                    if action == "move":
                        cat_obj = taxonomy.get(category)
                        target = cat_obj.target_folder if cat_obj else None
                        root_id, dest_id = _resolve_target_folder_id(
                            client, target, root_id
                        )
                    elif action == "rescue":
                        # Mirror backfill: rescue into the category's OmarOS
                        # folder when it has one, else fall back to the inbox.
                        cat_obj = taxonomy.get(category)
                        target = cat_obj.target_folder if cat_obj else None
                        if target:
                            root_id, dest_id = _resolve_target_folder_id(
                                client, target, root_id
                            )
                    if dest_id and dest_id != folder.id:
                        prev_categories = list(msg.get("categories") or [])
                        try:
                            moved = client.move_message(message_id, dest_id)
                            new_message_id = moved.get("id", message_id)
                            _append_undo(
                                {
                                    "internet_message_id": imid,
                                    "message_id": new_message_id,
                                    "action": "move",
                                    "from_folder_id": folder.id,
                                    "to_folder_id": dest_id,
                                    "prev_categories": prev_categories,
                                    "ts": _now_iso(),
                                }
                            )
                            if action == "to_junk":
                                summary.junked += 1
                            elif action == "rescue":
                                summary.rescued += 1
                            else:
                                summary.moved += 1
                        except GraphError as exc:
                            summary.errors.append(
                                f"move failed {imid}: {exc}"
                            )
                            applied_action = "label"

            index[imid] = {
                "id": new_message_id,
                "folder": folder.display_name,
                "from": _from_display(msg),
                "subject": msg.get("subject") or "",
                "received": msg.get("receivedDateTime") or "",
                "category": category,
                "confidence": confidence,
                "action": applied_action,
            }
            processed[imid] = {
                "category": category,
                "folder": folder.id,
                "action": applied_action,
                "ts": _now_iso(),
            }

        _write_snapshot(batch_for_snapshot)
        if new_link:
            delta_links[folder.id] = new_link

    state["delta_links"] = delta_links
    state["processed"] = processed
    state["last_run"] = _now_iso()
    _atomic_write_json(SYNC_STATE_PATH, state)
    _atomic_write_json(INDEX_PATH, index)

    _write_digest(summary, digest_counts, digest_actions)

    client.close()
    _print_summary(summary)
    return summary


def _build_digest(
    summary: SyncSummary,
    counts: dict[str, int],
    actions: list[dict],
) -> str:
    today = _utc_date()
    lines: list[str] = []
    lines.append("---")
    lines.append("title: Inbox Digest")
    lines.append("note_type: report")
    lines.append("domain: 11_Documents_and_Reports")
    lines.append(f"created: {today}")
    lines.append(f"updated: {today}")
    lines.append("tags: [email, digest]")
    lines.append("---")
    lines.append("")
    lines.append(f"# Inbox Digest — {today}")
    lines.append("")
    mode = "dry-run" if summary.dry_run else "applied"
    lines.append(f"_Run mode: {mode}._")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Folders scanned: {summary.folders}")
    lines.append(f"- Messages fetched: {summary.fetched}")
    lines.append(f"- Classified: {summary.classified}")
    lines.append(f"- Labeled: {summary.labeled}")
    lines.append(f"- Moved: {summary.moved}")
    lines.append(f"- Rescued from Junk: {summary.rescued}")
    lines.append(f"- Sent to Junk: {summary.junked}")
    lines.append("")
    if counts:
        lines.append("## By category")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("| --- | --- |")
        for cat in sorted(counts, key=lambda c: (-counts[c], c)):
            lines.append(f"| {cat} | {counts[cat]} |")
        lines.append("")
    lines.append("## Action items")
    lines.append("")
    if actions:
        for item in actions:
            lines.append(f"- **{item['from']}** — {item['subject']}")
    else:
        lines.append("_No messages requiring a reply._")
    lines.append("")
    if summary.errors:
        lines.append("## Errors")
        lines.append("")
        for err in summary.errors:
            lines.append(f"- {err}")
        lines.append("")
    return "\n".join(lines)


def _write_digest(
    summary: SyncSummary,
    counts: dict[str, int],
    actions: list[dict],
) -> None:
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    path = DIGEST_DIR / f"{_utc_date()}_inbox_digest.md"
    content = _build_digest(summary, counts, actions)
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == content:
                return
        except OSError:
            pass
    path.write_text(content, encoding="utf-8")


def _print_summary(summary: SyncSummary) -> None:
    mode = "DRY-RUN" if summary.dry_run else "APPLIED"
    print(
        f"[outlook-sync {mode}] folders={summary.folders} "
        f"fetched={summary.fetched} classified={summary.classified} "
        f"labeled={summary.labeled} moved={summary.moved} "
        f"rescued={summary.rescued} junked={summary.junked} "
        f"errors={len(summary.errors)}"
    )
    for err in summary.errors:
        print(f"  ! {err}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Incremental morning sync of Outlook mail: classify, label, "
            "and (optionally) move/junk/rescue messages. Dry-run by default."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform Graph writes. Without this flag the run is a dry-run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicitly force a dry-run (the default). Wins over --apply if both are given.",
    )
    parser.add_argument(
        "--mode",
        choices=["label", "move"],
        default=None,
        help="Override the configured mode (label = categorise only; "
        "move = also relocate into OmarOS folders).",
    )
    parser.add_argument(
        "--folder",
        action="append",
        default=None,
        metavar="DISPLAY_NAME",
        help="Restrict to this folder (repeatable).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap messages processed per folder (testing).",
    )
    args = parser.parse_args()

    try:
        run_sync(
            dry_run=args.dry_run or not args.apply,
            mode=args.mode,
            only_folders=args.folder,
            limit=args.limit,
        )
    except GraphError as exc:
        print(f"[outlook-sync] Graph error: {exc}", file=sys.stderr)
        print(
            "Hint: run scripts/auth.py to (re)authenticate with Microsoft.",
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
