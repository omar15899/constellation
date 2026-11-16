"""Tests for the run-once idempotency state."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import state  # noqa: E402


def test_already_ran_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_FILE", tmp_path / "newslab_daily_reports.json")
    importlib.reload  # no-op reference; STATE_FILE patched directly

    assert state.load_state() == {}
    state.save_state({"last_run_date": "2026-06-01"})

    st = state.load_state()
    assert state.already_ran(st, "2026-06-01") is True
    assert state.already_ran(st, "2026-06-02") is False


def test_save_is_atomic_and_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_FILE", tmp_path / "s.json")
    state.save_state({"last_run_date": "2026-06-01"})
    state.save_state({"last_run_date": "2026-06-02"})
    assert state.load_state()["last_run_date"] == "2026-06-02"
    assert not (tmp_path / "s.json.tmp").exists()
