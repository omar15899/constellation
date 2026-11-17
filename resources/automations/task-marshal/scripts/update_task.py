#!/usr/bin/env python3
"""Mutate an existing task inside a Daily ledger file.

Usage:
    python3 update_task.py --id 2026-04-22-001 --set status=done
    python3 update_task.py --id ... --set priority=P1 --set body='new notes'
    python3 update_task.py --id ... --append-body 'extra line'

--set KEY=VALUE may be repeated. Valid keys are any schema field (except `id`
and `created_at`).

Side effects:
  - stamps closed_at when status transitions to done/cancelled.
  - refuses to modify `id` (immutable).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from parse import SCHEMA_FIELDS, ENUMS, tasks_of, task_to_block  # noqa: E402
from classify_tags import classify as _classify_tags  # noqa: E402

_CLASSIFIER_INPUTS = {"title", "body", "references", "project", "tags"}

VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
DAILY = VAULT_ROOT / "02_Tasks_and_Execution" / "Ledger" / "Daily"

IMMUTABLE = {"id", "created_at"}
CLOSE_STATUSES = {"done", "cancelled"}


def _coerce(key: str, raw: str):
    if raw.lower() == "null" or raw == "":
        return None
    if key == "tags":
        return [s.strip() for s in raw.split(",") if s.strip()]
    if key == "duration_min":
        return int(raw)
    return raw


def _find_task(task_id: str) -> tuple[Path, list[dict], int]:
    """Return (path, all_tasks_in_file, index_of_matching_task)."""
    if not DAILY.exists():
        sys.stderr.write(f"error: no Daily dir at {DAILY}\n")
        sys.exit(4)
    for p in sorted(DAILY.glob("*.md")):
        tasks = tasks_of(p.read_text(encoding="utf-8"))
        for i, t in enumerate(tasks):
            if t.get("id") == task_id:
                return p, tasks, i
    sys.stderr.write(f"error: task id {task_id!r} not found\n")
    sys.exit(4)


def _splice_block(path: Path, index: int, new_block: str) -> None:
    """Rewrite the file replacing the i-th yaml task block with new_block."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=False)
    # Locate the i-th yaml task block bounds
    count = 0
    start = end = None
    i = 0
    while i < len(lines):
        if lines[i].strip() == "```yaml task":
            block_start = i
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                i += 1
            block_end = i  # closing fence line
            if count == index:
                start, end = block_start, block_end
                break
            count += 1
            i += 1
        else:
            i += 1
    if start is None:
        sys.stderr.write("error: could not locate block to splice\n")
        sys.exit(5)
    new_lines = lines[:start] + new_block.splitlines() + lines[end + 1:]
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--append-body", default=None)
    args = ap.parse_args()

    path, tasks, idx = _find_task(args.id)
    task = tasks[idx]
    touched_classifier_inputs = False

    for pair in args.set:
        if "=" not in pair:
            sys.stderr.write(f"error: bad --set {pair!r}\n")
            sys.exit(2)
        k, v = pair.split("=", 1)
        if k in IMMUTABLE:
            sys.stderr.write(f"error: field {k!r} is immutable\n")
            sys.exit(3)
        if k not in SCHEMA_FIELDS:
            sys.stderr.write(f"error: unknown field {k!r}\n")
            sys.exit(3)
        val = _coerce(k, v)
        if k in ENUMS and val is not None and val not in ENUMS[k]:
            sys.stderr.write(f"error: {k}={val!r} not in {sorted(ENUMS[k])}\n")
            sys.exit(3)
        task[k] = val
        if k in _CLASSIFIER_INPUTS:
            touched_classifier_inputs = True

    if args.append_body is not None:
        existing = task.get("body") or ""
        sep = "\n" if existing else ""
        task["body"] = existing + sep + args.append_body
        touched_classifier_inputs = True

    # Re-run the deterministic tag classifier when any signal field changed —
    # user-supplied tags always survive (they are fed back in as existing_tags).
    if touched_classifier_inputs:
        task["tags"] = _classify_tags(
            title=task.get("title"),
            body=task.get("body"),
            references=task.get("references"),
            project=task.get("project"),
            existing_tags=task.get("tags") or [],
        )

    # Auto-stamp closed_at on close
    if task.get("status") in CLOSE_STATUSES and not task.get("closed_at"):
        task["closed_at"] = dt.datetime.now().strftime("%Y-%m-%dT%H:%M")
    elif task.get("status") not in CLOSE_STATUSES:
        task["closed_at"] = None

    _splice_block(path, idx, task_to_block(task))
    print(json.dumps({
        "action": "update",
        "id": task["id"],
        "file": str(path.relative_to(VAULT_ROOT)),
        "status": task.get("status"),
        "closed_at": task.get("closed_at"),
    }, indent=2))


if __name__ == "__main__":
    main()
