#!/usr/bin/env python3
"""Run-once idempotency state for newslab-daily-reports.

State lives at ``02_Tasks_and_Execution/Ledger/.sync_state/newslab_daily_reports.json``
(same convention as claude-conversations-sync / calendar-sync). It records the
``as_of`` date of the last successful run so a double-fire on the same day — e.g.
launchd coalescing a missed 07:00 onto wake — is a no-op rather than a duplicate
report and a duplicate commit.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path("/Users/omarkhalil/OmarOS")
STATE_FILE = (
    REPO_ROOT
    / "02_Tasks_and_Execution"
    / "Ledger"
    / ".sync_state"
    / "newslab_daily_reports.json"
)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True))
    tmp.replace(STATE_FILE)


def already_ran(state: dict, as_of: str) -> bool:
    return state.get("last_run_date") == as_of
