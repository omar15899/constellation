#!/usr/bin/env python3
"""
Post-sync verification: prove that for every reminder in state, the LEDGER's
task body really does match the REMOTE reminder's body.

Why: a sync that detected misalignment in the past (sync 1 with the old JXA
fetcher) silently wrote OTHER reminders' bodies onto some tasks. After the
fetcher was rewritten in atomic AppleScript, a re-sync should propagate the
correct bodies via UPDATE_CONTENT. This script certifies that.

Output:
  • Counts: aligned / misaligned / unreadable
  • For each misaligned task: a short diff (first 80 chars of each body)
  • Optional ``--write-report PATH``: a markdown report under
    ``11_Documents_and_Reports/Reminders_Sync/Verify_<timestamp>.md``
  • Exit code 0 iff every checked task is aligned.

This is a read-only check. It never touches the ledger, the reminders, or
the state file. It is safe to run any time.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = Path("/Users/omarkhalil/OmarOS")
sys.path.insert(0, str(HERE))
from dedup import _norm  # noqa: E402

STATE = VAULT / "02_Tasks_and_Execution/Ledger/.sync_state/reminders.json"
DAILY = VAULT / "02_Tasks_and_Execution/Ledger/Daily"
REPORT_DIR = VAULT / "11_Documents_and_Reports/Reminders_Sync"

try:
    import yaml  # PyYAML — shipped with task-marshal's uv env
except ImportError:  # pragma: no cover
    yaml = None

_BLOCK = re.compile(r"```yaml task\n(.*?)\n```", re.DOTALL)


def _parse_block(block: str) -> dict:
    """Decode a single ``yaml task`` block. Uses PyYAML when available so
    multi-line block scalars with internal blank lines (Apple Reminders
    bodies happen to include those) are handled correctly. Falls back to a
    minimal parser that handles `key: value` and `key: |\\n  value…`."""
    if yaml is not None:
        try:
            return yaml.safe_load(block) or {}
        except yaml.YAMLError:
            pass  # fall through to the naive parser
    # Naive fallback: parse line-by-line.
    out: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\S+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in ("|", "|-"):
            i += 1
            body_lines = []
            while i < len(lines):
                if lines[i].strip() == "" or lines[i].startswith(("  ", "\t")):
                    body_lines.append(lines[i])
                    i += 1
                else:
                    break
            indents = [len(ln) - len(ln.lstrip(" \t"))
                       for ln in body_lines if ln.strip()]
            indent = min(indents) if indents else 0
            out[key] = "\n".join(ln[indent:] if len(ln) >= indent else ln
                                 for ln in body_lines).rstrip("\n")
            continue
        if val in ("null", "~", ""):
            out[key] = None
        elif val.lower() in ("true", "false"):
            out[key] = (val.lower() == "true")
        elif val.startswith(("'", '"')) and val.endswith(("'", '"')):
            out[key] = val[1:-1]
        else:
            out[key] = val
        i += 1
    return out


def index_ledger() -> dict[str, dict]:
    """{task_id: {title, body}} from every Daily/*.md file."""
    out: dict[str, dict] = {}
    for p in sorted(DAILY.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        for m in _BLOCK.finditer(text):
            block = m.group(1)
            rec = _parse_block(block)
            tid = rec.get("id")
            if not tid:
                continue
            out[tid] = {
                "title": rec.get("title") or "",
                "body": rec.get("body") or "",
                "file": str(p.relative_to(VAULT)),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remote", type=Path, required=True,
                    help="JSON file with the latest fetch output "
                         "(from fetch_reminders.py).")
    ap.add_argument("--write-report", action="store_true",
                    help="Write a markdown report to "
                    "11_Documents_and_Reports/Reminders_Sync/.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Show at most N misalignments in the printed output.")
    args = ap.parse_args()

    if not STATE.exists():
        print("[verify] no state file at", STATE, file=sys.stderr)
        return 2

    state = json.loads(STATE.read_text(encoding="utf-8"))
    remote_list = json.loads(args.remote.read_text(encoding="utf-8"))
    remote_by_id = {r["id"]: r for r in remote_list}
    ledger = index_ledger()

    aligned = 0
    misaligned: list[dict] = []
    unreadable: list[str] = []
    state_only: list[str] = []      # in state, no remote
    ledger_missing: list[str] = []  # in state, no ledger task

    for rid, rec in state.get("reminders", {}).items():
        tid = rec.get("task_id")
        if not tid:
            continue
        rem = remote_by_id.get(rid)
        if not rem:
            state_only.append(rid)
            continue
        task = ledger.get(tid)
        if not task:
            ledger_missing.append(tid)
            continue
        # Compare normalised body & title
        if (_norm(rem.get("name")) == _norm(task["title"])
                and _norm(rem.get("body")) == _norm(task["body"])):
            aligned += 1
        else:
            misaligned.append({
                "task_id": tid,
                "reminder_id": rid,
                "ledger_title": (task["title"] or "")[:80],
                "remote_title": (rem.get("name") or "")[:80],
                "ledger_body": (task["body"] or "")[:80],
                "remote_body": (rem.get("body") or "")[:80],
                "title_match": _norm(rem.get("name")) == _norm(task["title"]),
                "body_match": _norm(rem.get("body")) == _norm(task["body"]),
            })

    total = aligned + len(misaligned)
    pct = (aligned / total * 100.0) if total else 100.0

    print(f"[verify] aligned: {aligned}/{total}  ({pct:.1f}%)")
    print(f"[verify] misaligned: {len(misaligned)}")
    print(f"[verify] state-only (deleted in app): {len(state_only)}")
    print(f"[verify] ledger-missing tasks: {len(ledger_missing)}")

    shown = misaligned if args.limit is None else misaligned[: args.limit]
    for m in shown:
        kind = ("title" if not m["title_match"] else "") + \
               ("/body" if not m["body_match"] else "")
        kind = kind.lstrip("/") or "match"
        print(
            f"  ✗ {m['task_id']} ({kind})  "
            f"ledger={m['ledger_title']!r}  remote={m['remote_title']!r}",
            file=sys.stderr,
        )

    if args.write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = REPORT_DIR / f"Verify_{ts}.md"
        lines = [
            "---",
            f"title: Reminders Sync — Alignment Verification {ts}",
            "note_type: report",
            "domain: 11_Documents_and_Reports",
            "subdomain: Reminders_Sync",
            "tags: [reminders_sync, verification]",
            "status: active",
            f"created: {datetime.now().date().isoformat()}",
            f"updated: {datetime.now().date().isoformat()}",
            "ai_generated: true",
            "ai_reviewed: false",
            "---",
            "",
            "# Reminders ↔ Ledger Alignment Verification",
            "",
            f"**When:** {datetime.now().isoformat(timespec='seconds')}",
            f"**Aligned:** {aligned}/{total}  ({pct:.2f}%)",
            f"**Misaligned:** {len(misaligned)}",
            f"**State-only (reminder gone from app):** {len(state_only)}",
            f"**Ledger-missing (state points at unknown task_id):** {len(ledger_missing)}",
            "",
        ]
        if misaligned:
            lines += ["## Misaligned tasks", ""]
            for m in misaligned:
                lines.append(
                    f"- `{m['task_id']}` — title_match={m['title_match']}, "
                    f"body_match={m['body_match']}"
                )
                lines.append(f"  - ledger title: {m['ledger_title']!r}")
                lines.append(f"  - remote title: {m['remote_title']!r}")
                lines.append(f"  - ledger body : {m['ledger_body']!r}")
                lines.append(f"  - remote body : {m['remote_body']!r}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[verify] report → {path}")

    return 0 if not misaligned and not ledger_missing else 1


if __name__ == "__main__":
    sys.exit(main())
