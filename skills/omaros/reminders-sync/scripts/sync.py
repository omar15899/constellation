#!/usr/bin/env python3
"""
End-to-end sync: Apple Reminders → OmarOS task ledger (via task-marshal).

Pipeline:

    1. fetch_reminders.py  → raw JSON of every reminder in every list.
    2. dedup.classify()    → decide CREATE / UPDATE_STATUS / UPDATE_CONTENT /
                             NOOP / (missing) for each remote reminder.
    3. For CREATEs, build the task-marshal JSON envelope and feed it through
       `log_task.py` on stdin — this is the exact same path a user hits when
       they invoke `/task`, so all task-marshal invariants apply (auto-tagged,
       auto-classified, aggregated, etc.).
    4. For UPDATE_STATUS / UPDATE_CONTENT, call `update_task.py --id …`.
    5. Re-bind the state file from the action results, save, and re-run
       `aggregate.py` to refresh the weekly/monthly/yearly views.

The script is **idempotent**: running it twice in a row with no Reminders
changes produces zero writes and exits with every action NOOP. This is the
1-1 invariant the user asked for — two Apple reminders map to exactly two
tasks, and re-running never creates a third.

Flags:
    --dry-run          : classify only; print the plan; touch nothing.
    --limit N          : only process the first N remote reminders (smoke test).
    --only-lists L,... : restrict to reminders from these Apple list names.
    --skip-completed   : ignore already-completed reminders (useful on first
                         sync to avoid pulling years of done items).
    --report PATH      : write a markdown sync report to PATH (default:
                         11_Documents_and_Reports/Reminders_Sync/YYYY-MM-DD.md).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

# Local imports — this script lives at
# /Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts/sync.py, and the task-marshal scripts
# live at /Users/omarkhalil/GitHub/Constellation/skills/omaros/task-marshal/scripts/. Resolve both via VAULT.
HERE = Path(__file__).resolve().parent
VAULT = Path("/Users/omarkhalil/OmarOS")
TASK_MARSHAL = Path("/Users/omarkhalil/GitHub/Constellation/skills/omaros/task-marshal/scripts")

sys.path.insert(0, str(HERE))
from dedup import (  # noqa: E402
    Action,
    SyncState,
    ReminderRecord,
    classify,
    load_state,
    save_state,
)
from fetch_reminders import fetch  # noqa: E402
import raw_landing  # noqa: E402


STATE_PATH = VAULT / "02_Tasks_and_Execution/Ledger/.sync_state/reminders.json"
INDEX_PATH = VAULT / "02_Tasks_and_Execution/Ledger/_index.json"
REPORT_DIR = VAULT / "11_Documents_and_Reports/Reminders_Sync"

# Apple Reminders priority → OmarOS P0/P1/P2/P3.
# Apple uses: 0 (none), 1 (high), 5 (medium), 9 (low).
PRIORITY_MAP = {1: "P0", 5: "P1", 9: "P2", 0: None}


# ── reminder → task envelope ──────────────────────────────────────────────────

def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s_-]+", "_", s)
    return s or "untitled"


# Apple Reminders surfaces #hashtags as plain text in the title/notes. We
# extract them so they become first-class structured tags in the ledger
# (in addition to surviving verbatim in the body). Anchored to start-of-
# line or whitespace to avoid catching markdown headings (`### Foo`).
_HASHTAG_RE = re.compile(r"(?:(?<=^)|(?<=\s))#([A-Za-z][\w-]{1,40})")


def _extract_hashtags(*texts: str | None) -> list[str]:
    seen: list[str] = []
    seen_lower: set[str] = set()
    for text in texts:
        if not text:
            continue
        for m in _HASHTAG_RE.findall(text):
            low = m.lower()
            if low not in seen_lower:
                seen_lower.add(low)
                seen.append(low)
    return seen


def reminder_to_task(r: dict, parent_lookup: dict[str, dict] | None = None) -> dict:
    """Build the task-marshal JSON dict for a remote reminder.

    Deliberately conservative: we only set fields we can derive from the
    reminder. Missing fields stay null — this is the task-marshal contract
    (never invent defaults).

    ``parent_lookup``: optional ``{reminder_id: reminder_dict}`` map. When a
    reminder has a ``parent_id`` and the parent is in the lookup, the child
    gets an extra tag ``parent_<slug-of-parent-title>`` so dashboards can
    group sub-tasks under the human-readable parent name without an extra
    round-trip through the task ledger.
    """
    title = (r.get("name") or "").strip()
    body = (r.get("body") or "").strip() or None
    when = (r.get("due_date") or "")[:10] or None
    created = (r.get("creation_date") or "")[:16] or None
    closed = (r.get("completion_date") or "")[:16] or None
    priority = PRIORITY_MAP.get(int(r.get("priority") or 0))
    status = "done" if r.get("completed") else "open"

    list_tag = f"reminder_{slugify(r.get('list', ''))}"
    tags = ["reminders_app", list_tag]
    # Apple #hashtags inside title/notes become first-class tags too.
    for ht in _extract_hashtags(r.get("name"), r.get("body")):
        if ht not in tags:
            tags.append(ht)
    # Sub-task marker: anything with a parent reminder is tagged so the
    # dashboard can group hierarchies and search "subtask" finds them all.
    parent_id = r.get("parent_id")
    if parent_id:
        if "subtask" not in tags:
            tags.append("subtask")
        if parent_lookup is not None:
            parent = parent_lookup.get(parent_id)
            if parent:
                parent_slug = slugify((parent.get("name") or "")[:40])
                if parent_slug and parent_slug != "untitled":
                    parent_tag = f"parent_{parent_slug}"
                    if parent_tag not in tags:
                        tags.append(parent_tag)

    task: dict = {
        "title": title or "(untitled reminder)",
        "when": when,
        "body": body,
        "status": status,
        "priority": priority,
        "tags": tags,
    }
    if created:
        task["created_at"] = created
    if closed and status == "done":
        task["closed_at"] = closed
    # Carry the parent's Apple UUID through. The actual `parent` task_id
    # field is populated by a second pass in main() once every reminder
    # has been logged, since log_task.py needs the parent's task_id and
    # the parent may not yet exist on first sight.
    if parent_id:
        task["parent_reminder_id"] = parent_id
    return task


# ── external script invocations ────────────────────────────────────────────────

def _run(cmd: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def log_tasks(tasks: list[dict]) -> list[str]:
    """Feed the task-marshal logger and return the assigned task ids.

    ``log_task.py`` emits JSON: ``{"tasks_created": N, "ids": [...], ...}`` and
    internally re-runs aggregate.py, so the caller does not need to.
    """
    if not tasks:
        return []
    payload = json.dumps(tasks, ensure_ascii=False)
    res = _run(["uv", "run", str(TASK_MARSHAL / "log_task.py")], stdin=payload)
    if res.returncode != 0:
        raise RuntimeError(
            f"[sync] log_task.py failed ({res.returncode}):\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
    try:
        result = json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"[sync] log_task.py stdout was not JSON:\n{res.stdout}"
        ) from exc
    ids = result.get("ids") or []
    if len(ids) != len(tasks):
        raise RuntimeError(
            f"[sync] log_task.py returned {len(ids)} ids for {len(tasks)} tasks"
        )
    return ids


def update_task(
    task_id: str,
    *,
    status: str | None = None,
    closed_at: str | None = None,
    title: str | None = None,
    body: str | None = None,
) -> None:
    """Mutate one task in the ledger via task-marshal.

    None  → don't touch this field.
    ""    → set to YAML null (task-marshal's _coerce treats empty as null).
    other → set to value.
    """
    cmd = ["uv", "run", str(TASK_MARSHAL / "update_task.py"), "--id", task_id]
    if status:
        cmd += ["--set", f"status={status}"]
    if closed_at is not None:
        cmd += ["--set", f"closed_at={closed_at}"]
    if title is not None:
        cmd += ["--set", f"title={title}"]
    if body is not None:
        cmd += ["--set", f"body={body}"]
    res = _run(cmd)
    if res.returncode != 0:
        raise RuntimeError(
            f"[sync] update_task.py failed on {task_id} ({res.returncode}):\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )


def run_aggregate() -> None:
    res = _run(["uv", "run", str(TASK_MARSHAL / "aggregate.py")])
    if res.returncode != 0:
        raise RuntimeError(
            f"[sync] aggregate.py failed ({res.returncode}):\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )


# ── main driver ───────────────────────────────────────────────────────────────

@dataclass
class SyncStats:
    total_remote: int = 0
    created: int = 0
    updated_status: int = 0
    updated_content: int = 0
    noop: int = 0
    missing: int = 0


def render_report(
    stats: SyncStats,
    actions: list[Action],
    missing: list[str],
    state: SyncState,
    report_path: Path,
) -> None:
    today = date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        f"title: Reminders Sync — {today}",
        "note_type: report",
        "domain: 11_Documents_and_Reports",
        "subdomain: Reminders_Sync",
        "tags: [reminders_sync, ingestion]",
        "status: active",
        f"created: {today}",
        f"updated: {today}",
        "ai_generated: true",
        "ai_reviewed: false",
        "---",
        "",
        "# Reminders → Ledger Sync",
        "",
        f"**Run at:** {now}",
        f"**Remote reminders:** {stats.total_remote}",
        f"**Created:** {stats.created}  **Status-updated:** {stats.updated_status}  "
        f"**Content-updated:** {stats.updated_content}  **No-op:** {stats.noop}  "
        f"**Missing from remote:** {stats.missing}",
        "",
    ]
    by_kind = {
        "CREATE": "## Created",
        "UPDATE_STATUS": "## Status changed",
        "UPDATE_CONTENT": "## Content changed",
    }
    for kind, header in by_kind.items():
        subset = [a for a in actions if a.kind == kind]
        if not subset:
            continue
        lines.append(header)
        lines.append("")
        for a in subset:
            t = (a.reminder.get("name") or "").strip().replace("\n", " ")
            tid = a.task_id or "?"
            completed = "✓" if a.reminder.get("completed") else "○"
            lines.append(f"- {completed} `{tid}` **{t}** — {a.reason}")
        lines.append("")
    if missing:
        lines.append("## Missing from remote (deleted in Reminders app)")
        lines.append("")
        for rid in missing:
            rec = state.reminders.get(rid)
            if rec:
                lines.append(f"- `{rec.task_id}` — {rec.title}")
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only-lists", type=str, default=None,
                    help="comma-separated list names to restrict to")
    ap.add_argument("--skip-completed", action="store_true")
    ap.add_argument("--dump", type=Path, default=None,
                    help="use a pre-fetched JSON dump instead of live fetch")
    ap.add_argument("--no-report", action="store_true")
    ap.add_argument("--no-landing", action="store_true",
                    help="skip writing the raw landing zone "
                    "(09_Data_Sources/Apple_Reminders/)")
    ap.add_argument("--changes-only", action="store_true",
                    help="when set, only write the raw landing zone and "
                    "the markdown report if at least one CREATE / "
                    "UPDATE_STATUS / UPDATE_CONTENT was produced. NOOP "
                    "cycles touch nothing on disk. Used by daemon mode "
                    "to make sub-minute polling cheap.")
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--state", type=Path, default=STATE_PATH)
    ap.add_argument("--bootstrap-state", action="store_true",
                    help="One-shot: seed sync_state with the current EventKit "
                    "view (every reminder marked as 'already known') WITHOUT "
                    "calling log_task.py / update_task.py. Use this once when "
                    "switching the fetcher (e.g. AppleScript→EventKit) makes "
                    "more reminders visible than were previously imported, "
                    "to avoid flooding the ledger with historical CREATEs.")
    args = ap.parse_args()

    print("[sync] fetching reminders…", file=sys.stderr)
    if args.dump:
        remote = json.loads(args.dump.read_text(encoding="utf-8"))
    else:
        remote = fetch()

    if args.only_lists:
        wanted = {s.strip() for s in args.only_lists.split(",")}
        remote = [r for r in remote if r.get("list") in wanted]
    if args.skip_completed:
        remote = [r for r in remote if not r.get("completed")]
    if args.limit:
        remote = remote[: args.limit]

    state = load_state(args.state)
    index_tasks = []
    if INDEX_PATH.exists():
        index_tasks = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

    if args.bootstrap_state:
        # Seed-only mode: take every remote reminder, hash it, and write
        # state as if everything is already known. No CREATEs, no UPDATEs,
        # no log_task.py / update_task.py invocations. Use this once after
        # switching the fetcher when EventKit reveals reminders that
        # AppleScript previously missed, so the daemon does not flood the
        # ledger with thousands of historical CREATEs on the first cycle.
        from dedup import content_hash  # noqa: E402
        new_state = SyncState(last_sync=datetime.now().isoformat(timespec="seconds"))
        for r in remote:
            rid = r.get("id", "")
            if not rid:
                continue
            prev = state.reminders.get(rid)
            new_state.reminders[rid] = ReminderRecord(
                task_id=prev.task_id if prev else "",
                hash=content_hash(r.get("name"), r.get("body")),
                completed=bool(r.get("completed")),
                last_seen=new_state.last_sync,
                list=r.get("list", ""),
                title=(r.get("name") or "").strip()[:200],
            )
        save_state(new_state, args.state)
        print(json.dumps({
            "mode": "bootstrap-state",
            "total_remote": len(remote),
            "state_entries_before": len(state.reminders),
            "state_entries_after": len(new_state.reminders),
        }))
        return 0

    actions, missing = classify(remote, state, index_tasks)

    stats = SyncStats(total_remote=len(remote), missing=len(missing))
    for a in actions:
        if a.kind == "CREATE":        stats.created += 1
        elif a.kind == "UPDATE_STATUS":  stats.updated_status += 1
        elif a.kind == "UPDATE_CONTENT": stats.updated_content += 1
        elif a.kind == "NOOP":           stats.noop += 1

    # Land the verbatim raw copy. Default = always (keeps the historical
    # daily-cron behaviour). With --changes-only we skip landing on pure
    # NOOP cycles so a 5-second daemon loop does not flood
    # 09_Data_Sources/ with 17k snapshots/day for an idle pipeline.
    #
    # NB: `missing` is intentionally excluded from has_changes. A
    # reminder that disappeared from remote stays in state as a tombstone;
    # otherwise every cycle would re-trigger writes for the same
    # already-known absence. Newly-deleted reminders only matter for the
    # report, which the user can produce on demand without --changes-only.
    has_changes = (stats.created + stats.updated_status +
                   stats.updated_content) > 0
    skip_landing = args.no_landing or (args.changes_only and not has_changes)
    if not skip_landing:
        landing = raw_landing.land(remote)
        print(
            f"[sync] raw landing: snapshot={landing['snapshot']} "
            f"per_reminder={landing['per_reminder_files']}",
            file=sys.stderr,
        )

    print(
        f"[sync] plan: create={stats.created} "
        f"status={stats.updated_status} content={stats.updated_content} "
        f"noop={stats.noop} missing={stats.missing}",
        file=sys.stderr,
    )

    if args.dry_run:
        for a in actions:
            if a.kind != "NOOP":
                print(json.dumps({
                    "kind": a.kind,
                    "task_id": a.task_id,
                    "title": a.reminder.get("name"),
                    "reason": a.reason,
                }, ensure_ascii=False))
        return 0

    # 1. CREATE — batch through task-marshal's log_task.py so every new task
    # goes through the full normalisation + auto-tag pipeline in one call.
    parent_lookup = {r["id"]: r for r in remote if r.get("id")}
    create_actions = [a for a in actions if a.kind == "CREATE"]
    if create_actions:
        envelopes = [reminder_to_task(a.reminder, parent_lookup)
                     for a in create_actions]
        new_ids = log_tasks(envelopes)
        for a, tid in zip(create_actions, new_ids):
            a.task_id = tid

    # 2. UPDATE_STATUS — flip status, stamp closed_at.
    for a in [a for a in actions if a.kind == "UPDATE_STATUS"]:
        completed = bool(a.reminder.get("completed"))
        closed_at = None
        if completed:
            closed_at = (a.reminder.get("completion_date") or "")[:16] or None
        update_task(
            a.task_id,                          # type: ignore[arg-type]
            status="done" if completed else "open",
            closed_at=closed_at,
        )

    # 3. UPDATE_CONTENT — rewrite title/body; also reconcile status.
    # Pass body / closed_at as empty string when missing so update_task.py
    # writes YAML null. (None means "leave the field alone", "" means "set to
    # null" — see update_task() docstring.)
    for a in [a for a in actions if a.kind == "UPDATE_CONTENT"]:
        completed = bool(a.reminder.get("completed"))
        title_val = (a.reminder.get("name") or "").strip()
        body_val = (a.reminder.get("body") or "").strip()
        closed_val = (a.reminder.get("completion_date") or "")[:16]
        update_task(
            a.task_id,                          # type: ignore[arg-type]
            title=title_val if title_val else None,
            body=body_val,
            status="done" if completed else "open",
            closed_at=closed_val if completed else "",
        )

    # 4. Rewrite the state file from the post-sync world.
    new_state = SyncState(last_sync=datetime.now().isoformat(timespec="seconds"))
    now_iso = new_state.last_sync
    for a in actions:
        if not a.task_id:
            continue  # shouldn't happen — every action gets an id
        new_state.reminders[a.reminder["id"]] = ReminderRecord(
            task_id=a.task_id,
            hash=a.new_hash,
            completed=bool(a.reminder.get("completed")),
            last_seen=now_iso,  # type: ignore[arg-type]
            list=a.reminder.get("list", ""),
            title=(a.reminder.get("name") or "").strip()[:200],
        )
    # Preserve the old entries for reminders missing from remote (they may come
    # back — Reminders lists shared between devices sometimes flicker). We
    # never delete from state on our own.
    for rid in missing:
        if rid in state.reminders:
            new_state.reminders[rid] = state.reminders[rid]
    save_state(new_state, args.state)

    # 5. Aggregate. log_task.py auto-aggregates after CREATEs, so we only need
    # an explicit run when the only writes were UPDATEs.
    if stats.created == 0 and (stats.updated_status + stats.updated_content) > 0:
        print("[sync] running aggregate.py…", file=sys.stderr)
        run_aggregate()

    # 6. Report. Skip on pure NOOP cycles when --changes-only is set so the
    # daemon does not rewrite the same markdown file 17k times/day.
    skip_report = args.no_report or (args.changes_only and not has_changes)
    if not skip_report:
        report = args.report or REPORT_DIR / f"{date.today().isoformat()}.md"
        render_report(stats, actions, missing, new_state, report)
        print(f"[sync] report → {report}", file=sys.stderr)

    print(json.dumps({
        "total_remote": stats.total_remote,
        "created": stats.created,
        "updated_status": stats.updated_status,
        "updated_content": stats.updated_content,
        "noop": stats.noop,
        "missing": stats.missing,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
