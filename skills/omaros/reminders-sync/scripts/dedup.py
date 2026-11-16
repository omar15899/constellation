#!/usr/bin/env python3
"""
Pure, deterministic dedup library for the reminders → task-marshal pipeline.

Two dedup layers, applied in this order:

1.  **Reminder ID** (primary key). Each Apple reminder has a stable UUID-like
    id (`x-apple-reminder://<uuid>`). The sync state file maps
    `reminder_id → task_id`. This is the authoritative 1-1 binding.

2.  **Content hash** `sha256(norm(title) | norm(body))` — a safety net for the
    cases where the primary key is lost:
      • state file deleted / corrupted → rebuild the mapping against existing
        tasks instead of re-creating everything.
      • reminder was deleted + recreated with the same content → treat as the
        same task, don't dupe.
      • user manually logged a task with the same content before the first
        sync → don't dupe.

The caller (`sync.py`) uses this module in three roles:
  - hashing: `content_hash(title, body)` — canonical, whitespace-normalised.
  - state I/O: `load_state(path)`, `save_state(state, path)`.
  - diff:     `classify(remote, state, index)` → per-reminder Action.

Nothing here shells out. Nothing talks to Apple. Nothing writes Daily files.
The only side effects are reading `_index.json` (optional) and reading/writing
the JSON state file. This makes the module trivially unit-testable.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

ActionKind = Literal["CREATE", "UPDATE_STATUS", "UPDATE_CONTENT", "NOOP", "MISSING"]

STATE_VERSION = 1

_WS = re.compile(r"\s+")


# ── hashing & normalisation ────────────────────────────────────────────────────

def _norm(s: str | None) -> str:
    """Canonicalise a string for content-hash comparison.

    Rules:
      • None / empty → ``""``.
      • Unicode NFC (combine combining marks) so that accented chars compare
        equal regardless of input form.
      • Strip leading/trailing whitespace.
      • Collapse runs of whitespace (tabs, newlines, multiple spaces) to a
        single space — so a reminder whose body was edited only to change
        trailing whitespace still matches.
      • Casefold — reminder "Call Juan" and "call juan" are the same task.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = _WS.sub(" ", s).strip()
    return s.casefold()


def content_hash(title: str | None, body: str | None) -> str:
    """Deterministic hash of (title, body) after normalisation.

    The ``\\x1f`` separator is the ASCII Unit Separator, chosen because it
    cannot appear in normalised text (``_norm`` collapses all whitespace to
    a single space and ``\\x1f`` is neither printable nor whitespace).
    """
    payload = f"{_norm(title)}\x1f{_norm(body)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ── state file schema ─────────────────────────────────────────────────────────

@dataclass
class ReminderRecord:
    """One entry in the state file — represents a known Apple reminder ↔ task
    mapping."""
    task_id: str
    hash: str
    completed: bool
    last_seen: str        # ISO timestamp
    list: str             # Apple Reminders list name at last sync
    # Kept purely for debugging / inspection — never load-bearing:
    title: str = ""


@dataclass
class SyncState:
    version: int = STATE_VERSION
    last_sync: str | None = None
    reminders: dict[str, ReminderRecord] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "last_sync": self.last_sync,
            "reminders": {
                rid: {
                    "task_id": r.task_id,
                    "hash": r.hash,
                    "completed": r.completed,
                    "last_seen": r.last_seen,
                    "list": r.list,
                    "title": r.title,
                }
                for rid, r in self.reminders.items()
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SyncState":
        return cls(
            version=d.get("version", STATE_VERSION),
            last_sync=d.get("last_sync"),
            reminders={
                rid: ReminderRecord(**{**entry, "title": entry.get("title", "")})
                for rid, entry in d.get("reminders", {}).items()
            },
        )


def load_state(path: Path) -> SyncState:
    if not path.exists():
        return SyncState()
    data = json.loads(path.read_text(encoding="utf-8"))
    return SyncState.from_dict(data)


def save_state(state: SyncState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state.last_sync = datetime.now().isoformat(timespec="seconds")
    path.write_text(
        json.dumps(state.to_dict(), indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


# ── classification of a single remote reminder ────────────────────────────────

@dataclass
class Action:
    kind: ActionKind
    reminder: dict                     # the remote reminder dict
    task_id: str | None = None         # target task id, if known
    new_hash: str = ""                 # computed once, re-used by the caller
    reason: str = ""                   # human-readable, for the sync report


def _index_existing_tasks(tasks: list[dict]) -> dict[str, str]:
    """Return ``{content_hash: task_id}`` over existing ledger tasks."""
    idx: dict[str, str] = {}
    for t in tasks:
        h = content_hash(t.get("title"), t.get("body"))
        # First write wins — stable and deterministic.
        idx.setdefault(h, t["id"])
    return idx


def classify(
    remote: list[dict],
    state: SyncState,
    existing_tasks: list[dict] | None = None,
) -> tuple[list[Action], list[str]]:
    """Decide, for every remote reminder, what to do.

    Returns:
        actions: list of :class:`Action` per remote reminder, in input order.
        missing_ids: list of state.reminders keys that were NOT present in
                     remote — typically a reminder the user deleted in the
                     Reminders app. We never delete tasks; the caller just
                     logs this.
    """
    index = _index_existing_tasks(existing_tasks or [])
    actions: list[Action] = []

    seen_remote_ids: set[str] = set()
    for r in remote:
        rid = r["id"]
        seen_remote_ids.add(rid)
        h = content_hash(r.get("name"), r.get("body"))
        known = state.reminders.get(rid)

        if known is None:
            # Primary key unknown. Safety-net: check if some existing task has
            # the same content → bind to it, no new task.
            if h in index:
                actions.append(Action(
                    kind="NOOP",
                    reminder=r,
                    task_id=index[h],
                    new_hash=h,
                    reason="rebound to existing task by content hash",
                ))
            else:
                actions.append(Action(
                    kind="CREATE",
                    reminder=r,
                    task_id=None,
                    new_hash=h,
                    reason="new reminder, no content match in ledger",
                ))
            continue

        # Primary key known. Decide whether anything material changed.
        new_completed = bool(r.get("completed"))
        content_changed = h != known.hash
        status_changed = new_completed != known.completed

        if content_changed and status_changed:
            actions.append(Action(
                kind="UPDATE_CONTENT",
                reminder=r,
                task_id=known.task_id,
                new_hash=h,
                reason="title/body edited AND completion toggled",
            ))
        elif content_changed:
            actions.append(Action(
                kind="UPDATE_CONTENT",
                reminder=r,
                task_id=known.task_id,
                new_hash=h,
                reason="title/body edited in Reminders",
            ))
        elif status_changed:
            actions.append(Action(
                kind="UPDATE_STATUS",
                reminder=r,
                task_id=known.task_id,
                new_hash=h,
                reason=f"completion toggled → {new_completed}",
            ))
        else:
            actions.append(Action(
                kind="NOOP",
                reminder=r,
                task_id=known.task_id,
                new_hash=h,
                reason="unchanged since last sync",
            ))

    missing = [rid for rid in state.reminders if rid not in seen_remote_ids]
    return actions, missing


# ── small CLI so this module can be exercised standalone ───────────────────────

def _cli() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Dedup-classify a reminders dump.")
    p.add_argument("dump", type=Path, help="JSON file from fetch_reminders.py")
    p.add_argument("--state", type=Path, required=True,
                   help="sync state file (created if missing)")
    p.add_argument("--index", type=Path, default=None,
                   help="ledger _index.json for safety-net dedup")
    args = p.parse_args()

    remote = json.loads(args.dump.read_text(encoding="utf-8"))
    state = load_state(args.state)
    tasks = []
    if args.index and args.index.exists():
        tasks = json.loads(args.index.read_text(encoding="utf-8"))

    actions, missing = classify(remote, state, tasks)
    summary: dict[str, int] = {}
    for a in actions:
        summary[a.kind] = summary.get(a.kind, 0) + 1
    summary["_missing_from_remote"] = len(missing)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    _cli()
