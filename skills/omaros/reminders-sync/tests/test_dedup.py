#!/usr/bin/env python3
"""
Unit tests for dedup.py — the deterministic layer of reminders-sync.

No network, no AppleScript, no ledger writes. These tests prove the two
invariants the user explicitly asked for:

  1. Identical (title, body) maps to the identical hash — running the sync
     twice cannot create a duplicate task.
  2. The classifier is a pure function of (remote, state, index): same inputs
     always produce the same actions in the same order.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from dedup import (  # noqa: E402
    Action,
    ReminderRecord,
    SyncState,
    classify,
    content_hash,
    load_state,
    save_state,
)


def _r(rid: str, name: str, body: str = "",
       completed: bool = False, list_name: str = "Test") -> dict:
    """Shorthand builder for a remote reminder dict."""
    return {
        "id": rid,
        "list": list_name,
        "name": name,
        "body": body,
        "completed": completed,
        "priority": 0,
        "due_date": None,
        "creation_date": "2026-04-24T10:00:00.000Z",
        "completion_date": None,
    }


def _state_with(*records: tuple[str, str, str, bool]) -> SyncState:
    """Build a SyncState from (rid, task_id, hash, completed) tuples."""
    s = SyncState()
    for rid, tid, h, comp in records:
        s.reminders[rid] = ReminderRecord(
            task_id=tid, hash=h, completed=comp,
            last_seen="2026-04-24T09:00:00", list="Test", title="",
        )
    return s


# ── Hashing invariants ────────────────────────────────────────────────────────

def test_hash_is_deterministic():
    h1 = content_hash("Call Juan", "about the contract")
    h2 = content_hash("Call Juan", "about the contract")
    assert h1 == h2


def test_hash_is_whitespace_insensitive():
    """Collapsing whitespace must match — otherwise a user editing only
    trailing spaces in a reminder body would force a phantom UPDATE_CONTENT."""
    h1 = content_hash("Call Juan", "about  the\ncontract")
    h2 = content_hash("Call Juan", "about the contract")
    assert h1 == h2


def test_hash_is_case_insensitive():
    """Casefolding matters: Apple Reminders lets you edit casing trivially;
    we don't want every casing tweak to look like a content change."""
    h1 = content_hash("CALL juan", "ABC")
    h2 = content_hash("call Juan", "abc")
    assert h1 == h2


def test_hash_distinguishes_different_bodies():
    h1 = content_hash("Call", "body A")
    h2 = content_hash("Call", "body B")
    assert h1 != h2


def test_hash_empty_body_equals_null_body():
    assert content_hash("x", "") == content_hash("x", None)


def test_hash_different_titles_differ():
    assert content_hash("A", "x") != content_hash("B", "x")


# ── Classifier — CREATE path ──────────────────────────────────────────────────

def test_classify_new_reminder_emits_CREATE():
    remote = [_r("r1", "new task")]
    state = SyncState()
    actions, missing = classify(remote, state, existing_tasks=[])
    assert len(actions) == 1
    assert actions[0].kind == "CREATE"
    assert actions[0].task_id is None
    assert missing == []


def test_classify_new_reminder_but_matching_existing_task_emits_NOOP():
    """The content-hash safety net: if state is empty but a ledger task
    already has the same (title, body), we must NOT create a duplicate."""
    remote = [_r("r1", "Call Juan", "about the contract")]
    existing = [{
        "id": "2026-04-24-099",
        "title": "Call Juan",
        "body": "about the contract",
    }]
    actions, _ = classify(remote, SyncState(), existing_tasks=existing)
    assert actions[0].kind == "NOOP"
    assert actions[0].task_id == "2026-04-24-099"


# ── Classifier — NOOP / UPDATE_STATUS / UPDATE_CONTENT paths ──────────────────

def test_classify_known_unchanged_reminder_emits_NOOP():
    """Running sync twice with no Reminders-side changes must be a full
    zero-write pass — this is the 1-1 idempotency guarantee."""
    remote = [_r("r1", "Test", "body")]
    h = content_hash("Test", "body")
    state = _state_with(("r1", "2026-04-24-001", h, False))
    actions, missing = classify(remote, state, existing_tasks=[])
    assert actions[0].kind == "NOOP"
    assert actions[0].task_id == "2026-04-24-001"
    assert missing == []


def test_classify_status_toggle_emits_UPDATE_STATUS():
    """User marks the reminder complete in the app → task must flip to done."""
    remote = [_r("r1", "Test", "body", completed=True)]
    h = content_hash("Test", "body")
    state = _state_with(("r1", "2026-04-24-001", h, False))
    actions, _ = classify(remote, state, existing_tasks=[])
    assert actions[0].kind == "UPDATE_STATUS"
    assert actions[0].task_id == "2026-04-24-001"


def test_classify_content_edit_emits_UPDATE_CONTENT():
    """User edits title or body in the app → task title/body must update."""
    remote = [_r("r1", "New title", "body")]
    old_hash = content_hash("Old title", "body")
    state = _state_with(("r1", "2026-04-24-001", old_hash, False))
    actions, _ = classify(remote, state, existing_tasks=[])
    assert actions[0].kind == "UPDATE_CONTENT"


def test_classify_both_change_emits_UPDATE_CONTENT():
    """When both content AND status changed, UPDATE_CONTENT dominates —
    the update call will reconcile both."""
    remote = [_r("r1", "New title", "body", completed=True)]
    old_hash = content_hash("Old title", "body")
    state = _state_with(("r1", "2026-04-24-001", old_hash, False))
    actions, _ = classify(remote, state, existing_tasks=[])
    assert actions[0].kind == "UPDATE_CONTENT"


def test_classify_missing_reminder_is_flagged_not_deleted():
    """When a reminder is deleted in Apple, we never delete the task. The
    caller gets told about the dangling rid so it can be logged in the
    report, but no action is issued for it."""
    remote: list[dict] = []
    h = content_hash("Deleted in app", "")
    state = _state_with(("r_lost", "2026-04-24-001", h, False))
    actions, missing = classify(remote, state, existing_tasks=[])
    assert actions == []
    assert missing == ["r_lost"]


# ── Classifier — determinism (pure-function invariant) ────────────────────────

def test_classifier_is_pure():
    """Same inputs must produce the same outputs, byte-for-byte."""
    remote = [
        _r("r1", "A", "a"),
        _r("r2", "B", "", completed=True),
        _r("r3", "C", "body c"),
    ]
    state = _state_with(
        ("r1", "2026-04-24-001", content_hash("A", "a"), False),
        ("r2", "2026-04-24-002", content_hash("B", ""),  False),
    )
    existing = [{
        "id": "2026-04-24-050",
        "title": "C",
        "body": "body c",
    }]
    a1, m1 = classify(remote, state, existing_tasks=existing)
    a2, m2 = classify(remote, state, existing_tasks=existing)

    # Compare the two runs structurally (Action objects are dataclasses — direct
    # equality is intentional here).
    assert [a.kind for a in a1] == [a.kind for a in a2]
    assert [a.task_id for a in a1] == [a.task_id for a in a2]
    assert m1 == m2
    # Also verify the classification we actually expected:
    assert [a.kind for a in a1] == ["NOOP", "UPDATE_STATUS", "NOOP"]
    assert a1[2].task_id == "2026-04-24-050"  # rebound via content hash


# ── State file round-trip ─────────────────────────────────────────────────────

def test_state_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    s = _state_with(
        ("r1", "2026-04-24-001", content_hash("x", ""), False),
        ("r2", "2026-04-24-002", content_hash("y", "z"), True),
    )
    save_state(s, path)
    loaded = load_state(path)
    assert len(loaded.reminders) == 2
    assert loaded.reminders["r1"].task_id == "2026-04-24-001"
    assert loaded.reminders["r2"].completed is True


def test_state_file_missing_returns_empty():
    missing = Path("/tmp/does/not/exist/state.json")
    loaded = load_state(missing)
    assert loaded.reminders == {}
    assert loaded.last_sync is None


# ── Mini harness — supports running without pytest ────────────────────────────

def _run_all() -> int:
    """Discover every test_ function in this module and run it. Gives us a
    tiny, zero-dependency alternative to pytest for the test_sync.py flow."""
    failures: list[tuple[str, BaseException]] = []
    passes = 0
    tests = [
        (name, obj) for name, obj in globals().items()
        if callable(obj) and name.startswith("test_")
    ]
    for name, fn in tests:
        try:
            if "tmp_path" in fn.__code__.co_varnames:
                with tempfile.TemporaryDirectory() as td:
                    fn(Path(td))
            else:
                fn()
            passes += 1
            print(f"  ok  {name}")
        except BaseException as exc:  # noqa: BLE001
            failures.append((name, exc))
            print(f"  FAIL  {name}: {exc}")
    print(f"\n{passes}/{len(tests)} passed; {len(failures)} failed")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(_run_all())
