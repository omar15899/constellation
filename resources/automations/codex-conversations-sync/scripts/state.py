#!/usr/bin/env python3
"""Private incremental state for the Codex conversation mirror."""
from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(
    os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS"))
).resolve()
STATE_FILE = (
    REPO_ROOT
    / "02_Tasks_and_Execution"
    / "Ledger"
    / ".sync_state"
    / "codex_conversations.json"
)


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(tmp, 0o600)
    tmp.replace(STATE_FILE)


def is_unchanged(state: dict, key: str, mtime: float, size: int) -> bool:
    record = state.get(key)
    if not record:
        return False
    return (
        int(record.get("size", -1)) == size
        and abs(float(record.get("mtime", -1.0)) - mtime) < 1e-6
    )
