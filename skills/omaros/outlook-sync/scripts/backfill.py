from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from classify import Classification, Classifier, message_features
from config import (
    BACKFILL_DIR,
    BY_MESSAGE_DIR,
    INDEX_PATH,
    OutlookConfig,
    ROOT_FOLDER_NAME,
    SKIP_WELL_KNOWN,
    ensure_dirs,
    load_config,
    odata_quote,
    safe_id,
)
from graph_client import Folder, GraphClient, GraphError
from rules import Taxonomy


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _from_display(msg: dict) -> str:
    email = (msg.get("from") or {}).get("emailAddress", {}) or {}
    name = email.get("name") or ""
    address = email.get("address") or ""
    if name and address:
        return f"{name} <{address}>"
    return address or name


def _write_raw_landing(msg: dict, classification: Classification) -> None:
    imid = msg.get("internetMessageId") or msg.get("id") or "unknown"
    record = dict(msg)
    record["_omaros"] = {
        "category": classification.category,
        "confidence": classification.confidence,
        "source": classification.source,
        "reason": classification.reason,
        "action": None,
        "ts": _utc_now_iso(),
    }
    path = BY_MESSAGE_DIR / f"{safe_id(imid)}.json"
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _proposed_action(
    *,
    category: str,
    confidence: float,
    folder: Folder,
    taxonomy: Taxonomy,
    cfg: OutlookConfig,
) -> tuple[str, str | None]:
    is_junk_folder = (folder.well_known_name or "").lower() == "junkemail"

    if (
        category == taxonomy.junk_category
        and not is_junk_folder
        and confidence >= cfg.move_confidence_threshold
    ):
        return "to_junk", None

    if (
        taxonomy.rescue_from_junk
        and is_junk_folder
        and category != taxonomy.junk_category
        and confidence >= cfg.rescue_threshold
    ):
        cat = taxonomy.get(category)
        target = cat.target_folder if cat else None
        return "rescue", target

    if cfg.mode == "move" and category != taxonomy.junk_category:
        cat = taxonomy.get(category)
        if (
            cat
            and cat.target_folder
            and confidence >= cfg.move_confidence_threshold
        ):
            return "move", cat.target_folder

    return "label", None


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def _load_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        return {}
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _manifest_markdown(manifest: dict) -> str:
    lines: list[str] = []
    lines.append("# Outlook backfill manifest")
    lines.append("")
    lines.append(f"- created: {manifest['created']}")
    lines.append(f"- mode: {manifest['mode']}")
    lines.append(f"- total messages: {manifest['total']}")
    lines.append("")

    lines.append("## By category")
    lines.append("")
    lines.append("| category | count |")
    lines.append("| --- | --- |")
    for cat, count in sorted(
        manifest["by_category"].items(), key=lambda kv: (-kv[1], kv[0])
    ):
        lines.append(f"| {cat} | {count} |")
    lines.append("")

    lines.append("## By folder")
    lines.append("")
    lines.append("| folder | count |")
    lines.append("| --- | --- |")
    for folder, count in sorted(
        manifest["by_folder"].items(), key=lambda kv: (-kv[1], kv[0])
    ):
        lines.append(f"| {folder} | {count} |")
    lines.append("")

    actions = manifest["actions"]
    action_counts: dict[str, int] = {}
    for entry in actions:
        action_counts[entry["proposed_action"]] = (
            action_counts.get(entry["proposed_action"], 0) + 1
        )
    lines.append("## By proposed action")
    lines.append("")
    lines.append("| action | count |")
    lines.append("| --- | --- |")
    for action, count in sorted(
        action_counts.items(), key=lambda kv: (-kv[1], kv[0])
    ):
        lines.append(f"| {action} | {count} |")
    lines.append("")

    sample = actions[:25]
    lines.append(f"## Sample ({len(sample)} of {len(actions)})")
    lines.append("")
    lines.append("| folder | from | subject | category | conf | action | target |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for entry in sample:
        subject = (entry.get("subject") or "").replace("|", "/")[:60]
        sender = (entry.get("from") or "").replace("|", "/")[:40]
        folder_name = (entry.get("folder_name") or "").replace("|", "/")
        target = entry.get("target_folder") or ""
        lines.append(
            f"| {folder_name} | {sender} | {subject} | "
            f"{entry['category']} | {entry['confidence']:.2f} | "
            f"{entry['proposed_action']} | {target} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_manifest(
    *,
    only_folders: list[str] | None = None,
    limit_per_folder: int | None = None,
) -> dict:
    ensure_dirs()
    cfg = load_config()
    client = GraphClient.from_config()
    taxonomy = Taxonomy.load()
    clf = Classifier(
        taxonomy,
        cfg.model,
        cfg.escalation_model,
        escalation_threshold=cfg.escalation_threshold,
    )

    only = set(only_folders) if only_folders else None
    folders = client.list_folders()

    actions: list[dict] = []
    by_category: dict[str, int] = {}
    by_folder: dict[str, int] = {}
    index = _load_index()
    total = 0

    for folder in folders:
        if folder.well_known_name in SKIP_WELL_KNOWN:
            continue
        if folder.display_name in cfg.skip_folders:
            continue
        if only is not None and folder.display_name not in only:
            continue

        batch: list[dict] = []
        for msg in client.iter_messages(folder.id):
            batch.append(msg)
            if limit_per_folder is not None and len(batch) >= limit_per_folder:
                break

        if not batch:
            continue

        classifications = clf.classify(batch)
        by_imid = {c.internet_message_id: c for c in classifications}

        for msg in batch:
            features = message_features(msg)
            imid = features["internet_message_id"]
            classification = by_imid.get(imid)
            if classification is None:
                classification = Classification(
                    internet_message_id=imid,
                    message_id=features["id"],
                    category="Archive",
                    confidence=0.3,
                    reason="no classification produced",
                    source="fallback",
                )

            _write_raw_landing(msg, classification)

            action, target = _proposed_action(
                category=classification.category,
                confidence=classification.confidence,
                folder=folder,
                taxonomy=taxonomy,
                cfg=cfg,
            )

            entry = {
                "internet_message_id": imid,
                "message_id": features["id"],
                "folder_id": folder.id,
                "folder_name": folder.display_name,
                "from": _from_display(msg),
                "subject": features["subject"],
                "received": features["received"],
                "category": classification.category,
                "confidence": classification.confidence,
                "reason": classification.reason,
                "proposed_action": action,
                "target_folder": target,
            }
            actions.append(entry)

            by_category[classification.category] = (
                by_category.get(classification.category, 0) + 1
            )
            by_folder[folder.display_name] = (
                by_folder.get(folder.display_name, 0) + 1
            )
            total += 1

            index[imid] = {
                "id": features["id"],
                "folder": folder.display_name,
                "from": _from_display(msg),
                "subject": features["subject"],
                "received": features["received"],
                "category": classification.category,
                "confidence": classification.confidence,
                "action": "pending",
            }

    manifest = {
        "created": _utc_now_iso(),
        "mode": cfg.mode,
        "total": total,
        "by_category": by_category,
        "by_folder": by_folder,
        "actions": actions,
    }

    stamp = _utc_stamp()
    json_path = BACKFILL_DIR / f"manifest_{stamp}.json"
    md_path = BACKFILL_DIR / f"manifest_{stamp}.md"
    _atomic_write_json(json_path, manifest)
    md_path.write_text(_manifest_markdown(manifest), encoding="utf-8")
    _atomic_write_json(INDEX_PATH, index)

    manifest["_path"] = str(json_path)
    manifest["_markdown_path"] = str(md_path)
    client.close()
    return manifest


def _find_message_by_imid(client: GraphClient, imid: str) -> dict | None:
    if not imid:
        return None
    data = client._request(
        "GET",
        "/me/messages",
        params={
            "$filter": f"internetMessageId eq '{odata_quote(imid)}'",
            "$select": "id,internetMessageId,categories,parentFolderId",
            "$top": 1,
        },
    )
    if data is None:
        return None
    values = data.get("value", [])
    return values[0] if values else None


def apply_manifest(manifest_path: Path) -> dict:
    ensure_dirs()
    cfg = load_config()
    client = GraphClient.from_config()
    taxonomy = Taxonomy.load()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actions = manifest.get("actions", [])

    junk_id = client.well_known_folder_id("junkemail")
    inbox_id = client.well_known_folder_id("inbox")

    undo_entries: list[dict] = []
    summary = {
        "manifest": str(manifest_path),
        "total": len(actions),
        "labeled": 0,
        "moved": 0,
        "junked": 0,
        "rescued": 0,
        "skipped": 0,
        "errors": [],
    }
    errors: list[str] = summary["errors"]
    index = _load_index()

    for entry in actions:
        imid = entry.get("internet_message_id", "")
        category = entry.get("category", "")
        action = entry.get("proposed_action", "none")
        source_folder_id = entry.get("folder_id", "")
        target_folder = entry.get("target_folder")

        current = _find_message_by_imid(client, imid)
        if current is None:
            current_id = entry.get("message_id", "")
            current_categories: list[str] = []
            current_parent = source_folder_id
            if not current_id:
                errors.append(f"not located: {imid}")
                summary["skipped"] += 1
                continue
        else:
            current_id = current.get("id", "")
            current_categories = list(current.get("categories") or [])
            current_parent = current.get("parentFolderId", source_folder_id)

        if action == "none":
            summary["skipped"] += 1
            continue

        try:
            cat_def = taxonomy.get(category)
            color = cat_def.color if cat_def and cat_def.color else "preset0"

            if category and category not in current_categories:
                client.ensure_master_category(category, color)
                client.set_categories(current_id, [category])
                summary["labeled"] += 1
                applied_label = True
            else:
                applied_label = False

            if action == "to_junk":
                if current_parent == junk_id:
                    summary["skipped"] += 1
                else:
                    moved = client.move_message(current_id, junk_id)
                    undo_entries.append(
                        {
                            "internet_message_id": imid,
                            "message_id": moved.get("id", current_id),
                            "action": "move",
                            "from_folder_id": current_parent,
                            "to_folder_id": junk_id,
                            "prev_categories": current_categories,
                            "ts": _utc_now_iso(),
                        }
                    )
                    summary["junked"] += 1

            elif action == "rescue":
                if target_folder:
                    root_id = client.ensure_folder(ROOT_FOLDER_NAME)
                    dest_id = client.ensure_folder(target_folder, root_id)
                else:
                    dest_id = inbox_id
                if current_parent == dest_id:
                    summary["skipped"] += 1
                else:
                    moved = client.move_message(current_id, dest_id)
                    undo_entries.append(
                        {
                            "internet_message_id": imid,
                            "message_id": moved.get("id", current_id),
                            "action": "move",
                            "from_folder_id": current_parent,
                            "to_folder_id": dest_id,
                            "prev_categories": current_categories,
                            "ts": _utc_now_iso(),
                        }
                    )
                    summary["rescued"] += 1

            elif action == "move":
                if not target_folder:
                    summary["skipped"] += 1
                else:
                    root_id = client.ensure_folder(ROOT_FOLDER_NAME)
                    dest_id = client.ensure_folder(target_folder, root_id)
                    if current_parent == dest_id:
                        summary["skipped"] += 1
                    else:
                        moved = client.move_message(current_id, dest_id)
                        undo_entries.append(
                            {
                                "internet_message_id": imid,
                                "message_id": moved.get("id", current_id),
                                "action": "move",
                                "from_folder_id": current_parent,
                                "to_folder_id": dest_id,
                                "prev_categories": current_categories,
                                "ts": _utc_now_iso(),
                            }
                        )
                        summary["moved"] += 1

            elif action == "label":
                if not applied_label:
                    summary["skipped"] += 1

            if imid in index:
                index[imid]["action"] = action

        except GraphError as exc:
            errors.append(f"{imid}: {exc}")

    if undo_entries:
        undo_path = BACKFILL_DIR / f"undo_backfill_{_utc_stamp()}.json"
        _atomic_write_json(undo_path, undo_entries)
        summary["undo_manifest"] = str(undo_path)

    _atomic_write_json(INDEX_PATH, index)
    client.close()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Retroactive Outlook backfill. Default builds a dry-run manifest; "
            "--apply executes a manifest with an undo trail. Never applies "
            "without --apply."
        )
    )
    parser.add_argument(
        "--apply",
        metavar="MANIFEST_JSON",
        help="execute the actions in the given manifest .json file",
    )
    parser.add_argument(
        "--only-folder",
        action="append",
        dest="only_folders",
        metavar="DISPLAY_NAME",
        help="restrict to this folder (repeatable)",
    )
    parser.add_argument(
        "--limit-per-folder",
        type=int,
        default=None,
        help="cap messages scanned per folder (testing)",
    )
    args = parser.parse_args()

    try:
        if args.apply:
            manifest_path = Path(args.apply).expanduser().resolve()
            if not manifest_path.exists():
                print(f"manifest not found: {manifest_path}", file=sys.stderr)
                sys.exit(1)
            summary = apply_manifest(manifest_path)
            print("Backfill applied.")
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            manifest = build_manifest(
                only_folders=args.only_folders,
                limit_per_folder=args.limit_per_folder,
            )
            print("Dry-run manifest built. No Graph writes were performed.")
            print(f"  total messages : {manifest['total']}")
            print(f"  manifest (json): {manifest['_path']}")
            print(f"  manifest (md)  : {manifest['_markdown_path']}")
            print("")
            print("Review it, then apply with:")
            print(f"  python backfill.py --apply {manifest['_path']}")
    except GraphError as exc:
        print(f"Graph error: {exc}", file=sys.stderr)
        print("Hint: run auth.py to (re)authenticate.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
