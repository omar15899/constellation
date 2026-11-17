#!/usr/bin/env python3
"""Re-run the tag classifier against every task in the ledger and rewrite blocks.

Useful when the taxonomy has been extended or refined: existing tasks are
re-tagged in place using the new rules, user-provided tags are preserved, and
the rollups (_index, weekly/monthly/yearly) are regenerated.

Usage:
    python3 reclassify.py              # walk every Daily file
    python3 reclassify.py --only 2025-01-15
    python3 reclassify.py --dry-run    # print diffs, write nothing
    python3 reclassify.py --no-aggregate
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from parse import tasks_of, task_to_block  # noqa: E402
from classify_tags import classify as _classify_tags  # noqa: E402

VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
DAILY = VAULT_ROOT / "02_Tasks_and_Execution" / "Ledger" / "Daily"

_FENCE_OPEN = re.compile(r"^```yaml\s+task\s*$")
_FENCE_CLOSE = re.compile(r"^```\s*$")


def _reclassify_tasks_in_file(path: Path, dry_run: bool) -> tuple[int, int, int]:
    """Return (tasks_seen, tasks_changed, tags_added)."""
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=False)

    tasks_seen = 0
    tasks_changed = 0
    tags_added = 0

    new_lines: list[str] = []
    i = 0
    while i < len(lines):
        if not _FENCE_OPEN.match(lines[i]):
            new_lines.append(lines[i])
            i += 1
            continue
        # Collect the full block
        block_start = i
        i += 1
        body_lines = []
        while i < len(lines) and not _FENCE_CLOSE.match(lines[i]):
            body_lines.append(lines[i])
            i += 1
        # i points at closing fence, or end of file
        block_body = "\n".join(body_lines)
        # Re-use the same parser as everything else
        parsed = tasks_of("```yaml task\n" + block_body + "\n```")
        if not parsed:
            # Malformed block — leave untouched.
            new_lines.extend(lines[block_start:i + 1])
            if i < len(lines):
                i += 1
            continue
        task = parsed[0]
        tasks_seen += 1

        old_tags = list(task.get("tags") or [])
        new_tags = _classify_tags(
            title=task.get("title"),
            body=task.get("body"),
            references=task.get("references"),
            project=task.get("project"),
            existing_tags=old_tags,
        )
        if new_tags != old_tags:
            tasks_changed += 1
            tags_added += max(0, len(new_tags) - len(old_tags))
        task["tags"] = new_tags

        # Re-render
        rendered = task_to_block(task).splitlines()
        new_lines.extend(rendered)
        if i < len(lines) and _FENCE_CLOSE.match(lines[i]):
            i += 1  # consumed closing fence inside the rendered block
        # else: block was truncated at file end — already emitted.

    new_text = "\n".join(new_lines)
    if not new_text.endswith("\n"):
        new_text += "\n"

    if new_text != original and not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return tasks_seen, tasks_changed, tags_added


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="restrict to one Daily file (date stem, e.g. 2025-01-15)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-aggregate", action="store_true",
                    help="skip the rollup regeneration after rewriting")
    args = ap.parse_args()

    if not DAILY.exists():
        sys.stderr.write(f"error: no Daily dir at {DAILY}\n")
        sys.exit(4)

    files = sorted(DAILY.glob("*.md"))
    if args.only:
        files = [p for p in files if p.stem == args.only]
        if not files:
            sys.stderr.write(f"error: no Daily file matching stem {args.only!r}\n")
            sys.exit(4)

    total_seen = total_changed = total_tags_added = 0
    files_changed: list[str] = []
    for p in files:
        seen, changed, added = _reclassify_tasks_in_file(p, args.dry_run)
        total_seen += seen
        total_changed += changed
        total_tags_added += added
        if changed:
            files_changed.append(str(p.relative_to(VAULT_ROOT)))

    rollup_result: dict = {}
    if not args.no_aggregate and not args.dry_run and total_changed:
        try:
            import aggregate
            import contextlib
            import io
            saved_argv = sys.argv
            sys.argv = [sys.argv[0]]
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    aggregate.main()
            finally:
                sys.argv = saved_argv
            try:
                rollup_result = json.loads(buf.getvalue())
            except json.JSONDecodeError:
                rollup_result = {"raw": buf.getvalue()}
        except Exception as exc:
            rollup_result = {"error": str(exc)}

    print(json.dumps({
        "action": "reclassify",
        "dry_run": args.dry_run,
        "files_scanned": len(files),
        "tasks_scanned": total_seen,
        "tasks_changed": total_changed,
        "tags_added_total": total_tags_added,
        "files_changed": files_changed,
        "rollup": rollup_result,
    }, indent=2))


if __name__ == "__main__":
    main()
