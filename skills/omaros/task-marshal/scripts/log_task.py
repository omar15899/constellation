#!/usr/bin/env python3
"""Append one or more task blocks to the right Ledger/Daily/*.md file(s).

Input: JSON array on stdin. Each element is a task dict with any subset of the
schema fields. `title` is required. Fields absent from the input stay null.

The script:
  1. Routes each task by `when` (ISO date) or falls back to today.
  2. Ensures the Daily file exists with correct frontmatter.
  3. Assigns a deterministic id YYYY-MM-DD-NNN by scanning existing ids in that
     day's file.
  4. Stamps created_at (now) and default status=open if not given.
  5. Appends the task block(s) at the end of the Daily file.
  6. Bumps the file's `updated` frontmatter field.

Output (stdout): JSON summary
  {"tasks_created": N, "files": [path, ...], "ids": [id, ...]}

Exit codes:
  0  success
  2  bad payload
  3  validation failure (unknown enum, missing title, etc.)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

# Make the sibling parse module importable regardless of CWD.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from parse import (  # noqa: E402
    ENUMS,
    SCHEMA_FIELDS,
    read_daily,
    task_to_block,
    validate,
)
from classify_tags import classify as _classify_tags  # noqa: E402

VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
LEDGER = VAULT_ROOT / "02_Tasks_and_Execution" / "Ledger"
DAILY = LEDGER / "Daily"

_FRONTMATTER_BOUNDARY = re.compile(r"^---\s*$")


def _today() -> dt.date:
    return dt.date.today()


def _now_iso() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M")


def _bucket_date(task: dict) -> dt.date:
    w = task.get("when")
    if not w:
        return _today()
    try:
        return dt.date.fromisoformat(w)
    except ValueError:
        return _today()


def _iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _daily_path(d: dt.date) -> Path:
    return DAILY / f"{d.isoformat()}.md"


def _daily_frontmatter(d: dt.date) -> str:
    return (
        "---\n"
        f"title: \"Task ledger — {d.isoformat()}\"\n"
        "note_type: task_ledger_daily\n"
        f"date: {d.isoformat()}\n"
        f"week: {_iso_week(d)}\n"
        f"month: {d.strftime('%Y-%m')}\n"
        f"year: {d.year}\n"
        "status: active\n"
        "tags: [task, task_ledger, daily]\n"
        "author: Omar\n"
        "ai_generated: true\n"
        "ai_reviewed: false\n"
        f"created: {d.isoformat()}\n"
        f"updated: {_today().isoformat()}\n"
        "---\n\n"
        f"# Task ledger — {d.isoformat()}\n\n"
        "<!-- Each task is a fenced ```yaml task ...``` block. Do not hand-edit; use /task. -->\n\n"
    )


def _ensure_daily(d: dt.date) -> Path:
    DAILY.mkdir(parents=True, exist_ok=True)
    p = _daily_path(d)
    if not p.exists():
        p.write_text(_daily_frontmatter(d), encoding="utf-8")
    return p


def _bump_updated(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    today = _today().isoformat()
    new = re.sub(r"^updated:\s*.*$", f"updated: {today}", text, count=1, flags=re.MULTILINE)
    if new != text:
        path.write_text(new, encoding="utf-8")


def _next_id(d: dt.date, path: Path) -> str:
    existing = read_daily(path)
    prefix = d.isoformat() + "-"
    used = [t["id"] for t in existing if t.get("id", "").startswith(prefix)]
    nums = []
    for i in used:
        tail = i[len(prefix):]
        if tail.isdigit():
            nums.append(int(tail))
    nxt = max(nums, default=0) + 1
    return f"{prefix}{nxt:03d}"


def _normalise(task: dict) -> dict:
    out: dict = {k: None for k in SCHEMA_FIELDS}
    out["tags"] = []
    for k, v in task.items():
        if k in SCHEMA_FIELDS:
            out[k] = v
    # defaults
    if not out.get("status"):
        out["status"] = "open"
    if out.get("tags") is None:
        out["tags"] = []
    if not out.get("created_at"):
        out["created_at"] = _now_iso()
    # Auto-classify tags from title+body+references+project against the
    # taxonomy. User-provided tags are preserved (unioned on top).
    out["tags"] = _classify_tags(
        title=out.get("title"),
        body=out.get("body"),
        references=out.get("references"),
        project=out.get("project"),
        existing_tags=out.get("tags") or [],
    )
    return out


def _append_block(path: Path, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    text += "\n" + block + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"error: invalid JSON: {exc}\n")
        sys.exit(2)

    if not isinstance(payload, list):
        sys.stderr.write("error: stdin must be a JSON array of task dicts\n")
        sys.exit(2)

    created_ids: list[str] = []
    files_touched: set[Path] = set()

    for raw in payload:
        if not isinstance(raw, dict):
            sys.stderr.write("error: each task must be an object\n")
            sys.exit(2)

        task = _normalise(raw)
        errs = validate(task)
        if errs:
            sys.stderr.write("validation error: " + "; ".join(errs) + "\n")
            sys.exit(3)

        # Validate enum constraints beyond title/schema
        for f, allowed in ENUMS.items():
            v = task.get(f)
            if v is not None and v not in allowed:
                sys.stderr.write(f"error: {f}={v!r} not in {sorted(allowed)}\n")
                sys.exit(3)

        bucket = _bucket_date(task)
        path = _ensure_daily(bucket)
        task["id"] = _next_id(bucket, path)

        _append_block(path, task_to_block(task))
        _bump_updated(path)

        created_ids.append(task["id"])
        files_touched.add(path)

    # Auto-rollup: regenerate Weekly/Monthly/Yearly + _index.json.
    # Python-level write_text() does NOT trigger the PostToolUse hook
    # (which only sees Claude's own Write/Edit tool calls), so we invoke
    # aggregate inline to keep rollups in sync with every log.
    rollup_result: dict = {}
    try:
        import aggregate  # sibling module
        # aggregate.main() reads sys.argv — force it to "no args" so it does
        # a full deterministic rebuild regardless of how log_task was invoked.
        import io
        import contextlib
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
    except SystemExit:
        # aggregate.main() never exits unless argparse was unhappy — we shouldn't
        # get here since we forced clean argv above. Still, be defensive.
        pass
    except Exception as exc:
        rollup_result = {"error": str(exc)}

    print(json.dumps({
        "tasks_created": len(created_ids),
        "ids": created_ids,
        "files": sorted(str(p.relative_to(VAULT_ROOT)) for p in files_touched),
        "rollup": rollup_result,
    }, indent=2))


if __name__ == "__main__":
    main()
