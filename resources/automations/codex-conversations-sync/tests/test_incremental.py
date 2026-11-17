#!/usr/bin/env python3
"""Incrementality and local-only implementation tests."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import scan  # noqa: E402
import state  # noqa: E402
import sync  # noqa: E402


def test_unchanged_detection() -> None:
    current = {"/p/a.jsonl": {"mtime": 100.0, "size": 50}}
    assert state.is_unchanged(current, "/p/a.jsonl", 100.0, 50)
    assert not state.is_unchanged(current, "/p/a.jsonl", 100.0, 99)
    assert not state.is_unchanged(current, "/p/a.jsonl", 200.0, 50)


def test_recursive_scan_and_uuid_extraction() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        session = root / "2026" / "07" / "30" / (
            "rollout-2026-07-30T10-00-00-"
            "abc12300-0000-0000-0000-000000000000.jsonl"
        )
        session.parent.mkdir(parents=True)
        session.write_text("{}\n", encoding="utf-8")
        with patch.multiple(
            scan, SESSIONS_DIR=root, ARCHIVED_SESSIONS_DIR=root / "absent"
        ):
            sources = scan.scan()
        assert len(sources) == 1
        assert sources[0].session_id == "abc12300-0000-0000-0000-000000000000"


def test_scan_includes_archived_sessions_without_an_active_store() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        archived = root / "archived_sessions"
        archived.mkdir()
        session = archived / "archived.jsonl"
        session.write_text("{}\n", encoding="utf-8")
        with patch.multiple(
            scan, SESSIONS_DIR=root / "sessions", ARCHIVED_SESSIONS_DIR=archived
        ):
            sources = scan.scan()
        assert [source.path for source in sources] == [session]


def test_forked_sessions_keep_distinct_lossless_archives() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sources = root / "sessions"
        sources.mkdir()
        expected: dict[str, bytes] = {}
        for name in ("fork-one", "fork-two"):
            records = [
                {"type": "session_meta", "payload": {"id": name, "cwd": "/p"}},
                {"type": "session_meta", "payload": {"id": "shared-ancestor"}},
                {"type": "event_msg", "payload": {"type": "user_message", "message": name}},
            ]
            content = "".join(json.dumps(record) + "\n" for record in records).encode()
            (sources / f"{name}.jsonl").write_bytes(content)
            expected[name] = content
        manifest_path = root / "manifest.json"
        with (
            patch.multiple(scan, SESSIONS_DIR=sources, ARCHIVED_SESSIONS_DIR=root / "absent"),
            patch.multiple(
                sync, REPO_ROOT=root, RAW_DIR=root / "raw",
                RENDERED_DIR=root / "rendered", MANIFEST=manifest_path,
            ),
            patch.object(state, "STATE_FILE", root / "state.json"),
            patch.object(sys, "argv", ["sync.py"]),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            assert sync.main() == 0
            manifest = json.loads(manifest_path.read_text())
            assert set(manifest) == set(expected)
            for name, content in expected.items():
                entry = manifest[name]
                assert Path(entry["raw_path"]).read_bytes() == content
                assert (root / entry["rendered_path"]).is_file()
                assert (sources / f"{name}.jsonl").read_bytes() == content
            assert len({entry["rendered_path"] for entry in manifest.values()}) == 2
            assert sync.main() == 0
            assert json.loads(manifest_path.read_text()) == manifest


def test_private_atomic_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        text_path = root / "rendered" / "one.md"
        assert sync.write_if_changed(text_path, "hello\n")
        assert not sync.write_if_changed(text_path, "hello\n")
        assert (text_path.stat().st_mode & 0o777) == 0o600

        source = root / "source.jsonl"
        source.write_bytes(b'{"x":1}\n')
        raw = root / "raw" / "one.jsonl"
        sync.mirror_raw(source, raw)
        assert raw.read_bytes() == source.read_bytes()
        assert (raw.stat().st_mode & 0o777) == 0o600


def test_obsolete_rendered_cleanup_stays_inside_private_corpus() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        original_repo = sync.REPO_ROOT
        original_rendered = sync.RENDERED_DIR
        sync.REPO_ROOT = root
        sync.RENDERED_DIR = root / "rendered"
        stale = sync.RENDERED_DIR / "project" / "old.md"
        stale.parent.mkdir(parents=True)
        stale.write_text("old\n", encoding="utf-8")
        try:
            removed = sync.remove_obsolete_rendered(
                {"rendered/project/old.md"}, set()
            )
            assert removed == 1
            assert not stale.exists()
            try:
                sync.remove_obsolete_rendered({"../outside.md"}, set())
            except ValueError:
                pass
            else:
                raise AssertionError("outside-corpus cleanup was not rejected")
        finally:
            sync.REPO_ROOT = original_repo
            sync.RENDERED_DIR = original_rendered


def test_sync_has_no_git_or_upload_path() -> None:
    source = (SCRIPTS / "sync.py").read_text(encoding="utf-8")
    assert "git_commit" not in source
    assert "git add" not in source
    assert "git push" not in source
    assert "requests." not in source
    assert "urllib" not in source


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} passed")
