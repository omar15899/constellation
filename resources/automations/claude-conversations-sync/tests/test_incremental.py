#!/usr/bin/env python3
"""Test the incremental state contract: an unchanged source is skipped."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import state  # noqa: E402


def test_unchanged_detection():
    st = {"/p/a.jsonl": {"mtime": 100.0, "size": 50}}
    assert state.is_unchanged(st, "/p/a.jsonl", 100.0, 50) is True


def test_size_change_invalidates():
    st = {"/p/a.jsonl": {"mtime": 100.0, "size": 50}}
    assert state.is_unchanged(st, "/p/a.jsonl", 100.0, 99) is False


def test_mtime_change_invalidates():
    st = {"/p/a.jsonl": {"mtime": 100.0, "size": 50}}
    assert state.is_unchanged(st, "/p/a.jsonl", 200.0, 50) is False


def test_unknown_key():
    assert state.is_unchanged({}, "/p/new.jsonl", 1.0, 1) is False


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
