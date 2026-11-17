#!/usr/bin/env python3
"""Incremental sync state for claude-conversations-sync.

State lives at ``02_Tasks_and_Execution/Ledger/.sync_state/claude_conversations.json``
(same convention as calendar-sync / reminders-sync) and maps each source
transcript path to the fingerprint of the last successful render. A transcript
is only re-rendered when its ``(mtime, size)`` changes, so a no-op tick writes
nothing.
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
    / "claude_conversations.json"
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


def is_unchanged(state: dict, key: str, mtime: float, size: int) -> bool:
    rec = state.get(key)
    if not rec:
        return False
    return (
        int(rec.get("size", -1)) == size
        and abs(float(rec.get("mtime", -1.0)) - mtime) < 1e-6
    )
