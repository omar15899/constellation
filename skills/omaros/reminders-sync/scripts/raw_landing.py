#!/usr/bin/env python3
"""
Raw landing zone for Apple Reminders.

Every sync writes two artefacts before any task is created or updated:

  1. ``09_Data_Sources/Apple_Reminders/snapshots/YYYY-MM-DD_HHMMSS.json``
     A timestamped, immutable, byte-for-byte JSON dump of the entire fetch
     output. This is the audit trail — the canonical evidence of what Apple
     told us at sync time. Snapshots accumulate; old ones are never modified.

  2. ``09_Data_Sources/Apple_Reminders/by_reminder/<UUID>.json``
     One file per reminder, overwritten on every sync. Holds the latest
     properties dict plus a ``synced_at`` timestamp. This is the per-item
     "current truth" view — handy for grep, fast lookup, and as the bridge
     between a vault task and its source-of-truth reminder.

  3. ``09_Data_Sources/Apple_Reminders/index.json``
     Aggregated roll-up: reminder_id → {by_reminder_path, list, name, completed}.
     Re-written every sync. Lets external consumers (queries, dashboards,
     repair scripts) walk the corpus without scanning the file system.

  4. ``09_Data_Sources/Apple_Reminders/README.md``
     Created on first run with a short explanation of the layout.

The functions here are pure I/O — no business logic. Called from sync.py
*before* any classification or ledger write so that, even if the sync
crashes mid-run, the raw landing zone always reflects the latest fetch.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

VAULT = Path("/Users/omarkhalil/OmarOS")
LANDING = Path(
    os.environ.get(
        "REMINDERS_LANDING_DIR", VAULT / "09_Data_Sources" / "Apple_Reminders"
    )
)
SNAPSHOTS = LANDING / "snapshots"
BY_REMINDER = LANDING / "by_reminder"
INDEX = LANDING / "index.json"
README = LANDING / "README.md"

# x-apple-reminder://UUID  →  UUID
_UUID_RE = re.compile(r"x-apple-reminder://([0-9A-F-]+)", re.I)


def _safe_filename(reminder_id: str) -> str:
    """Reduce an Apple reminder URI to its UUID, fall back to a slug."""
    m = _UUID_RE.match(reminder_id)
    if m:
        return m.group(1)
    return re.sub(r"[^A-Za-z0-9_-]", "_", reminder_id)[:120]


def _ensure_layout() -> None:
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    BY_REMINDER.mkdir(parents=True, exist_ok=True)
    if not README.exists():
        README.write_text(_README_TEXT, encoding="utf-8")


_README_TEXT = """\
---
title: Apple Reminders — Raw Landing Zone
note_type: data_source_index
domain: 09_Data_Sources
subdomain: Apple_Reminders
status: active
ai_generated: true
ai_reviewed: false
tags: [data_source, apple_reminders, landing_zone]
---

# Apple Reminders — Raw Landing Zone

This folder is the verbatim cache of every reminder that has ever been seen
by the `reminders-sync` skill. It is **the source of truth** for what Apple
returned on each sync, before any normalisation, hashing, or task-marshal
processing.

## Layout

```
09_Data_Sources/Apple_Reminders/
├── README.md            ← this file
├── index.json           ← {reminder_id: {path, list, name, completed}}
├── snapshots/           ← one immutable JSON per sync
│   └── YYYY-MM-DD_HHMMSS.json
└── by_reminder/         ← one JSON per reminder, latest values
    └── <UUID>.json
```

* **`snapshots/`** is immutable history. Each file is the full fetch output
  at a moment in time. Useful for audit and reconstructing past state.
* **`by_reminder/`** is the live mirror. Every sync overwrites the per-id
  file. The `synced_at` field tells you when it was last refreshed.
* **`index.json`** is the lightweight roll-up. Use it as the entry point
  when you need to know *what reminders exist* without scanning the dir.

## Relationship to the task ledger

A task in `02_Tasks_and_Execution/Ledger/Daily/*.md` that originates from a
reminder carries the tag `reminders_app` and a `reminder_<list>` tag. The
binding from reminder UUID → task id lives in
`02_Tasks_and_Execution/Ledger/.sync_state/reminders.json` (NOT here).

This folder is purely the data-source side; the ledger is purely the
semantic side. The sync_state file is the bridge between them.

## Do not edit by hand

These files are regenerated on every sync. Manual edits will be lost.
"""


def write_snapshot(reminders: list[dict]) -> Path:
    """Write a timestamped immutable snapshot of the full fetch output."""
    _ensure_layout()
    name = datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".json"
    path = SNAPSHOTS / name
    path.write_text(
        json.dumps(reminders, indent=2, ensure_ascii=False, sort_keys=False),
        encoding="utf-8",
    )
    return path


def write_per_reminder(reminders: list[dict]) -> int:
    """Overwrite one ``<UUID>.json`` per reminder with the latest values."""
    _ensure_layout()
    now = datetime.now().isoformat(timespec="seconds")
    written = 0
    for r in reminders:
        rid = r.get("id", "")
        if not rid:
            continue
        fname = _safe_filename(rid) + ".json"
        path = BY_REMINDER / fname
        payload = dict(r)
        payload["_synced_at"] = now
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        written += 1
    return written


def write_index(reminders: list[dict]) -> Path:
    """Write the lightweight roll-up index.json."""
    _ensure_layout()
    idx: dict[str, dict] = {}
    for r in reminders:
        rid = r.get("id", "")
        if not rid:
            continue
        fname = _safe_filename(rid) + ".json"
        idx[rid] = {
            "by_reminder_path": str((BY_REMINDER / fname).relative_to(VAULT)),
            "list": r.get("list", ""),
            "name": (r.get("name") or "").strip()[:200],
            "completed": bool(r.get("completed")),
        }
    INDEX.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "count": len(idx),
                "reminders": idx,
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return INDEX


def land(reminders: list[dict]) -> dict:
    """Run all three writers; return a small summary dict."""
    snap = write_snapshot(reminders)
    n = write_per_reminder(reminders)
    idx = write_index(reminders)
    return {
        "snapshot": str(snap.relative_to(VAULT)),
        "per_reminder_files": n,
        "index": str(idx.relative_to(VAULT)),
    }


def main() -> None:
    """CLI: read a reminders dump from stdin or a file and land it."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dump", nargs="?", default="-",
                    help="JSON file with reminders array (default: stdin).")
    args = ap.parse_args()
    if args.dump == "-":
        data = json.load(sys.stdin)
    else:
        data = json.loads(Path(args.dump).read_text(encoding="utf-8"))
    summary = land(data)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
