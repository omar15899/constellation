#!/usr/bin/env python3
"""Tests for render.py: schema parsing, wrapper stripping, secret redaction."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import render  # noqa: E402


def _line(**kw) -> str:
    return json.dumps(kw)


def _synthetic() -> list[str]:
    return [
        _line(type="worktree-state", sessionId="abc123"),
        _line(type="ai-title", aiTitle="Build the thing", sessionId="abc123"),
        # harness-injected meta turn -> must be dropped
        _line(
            type="user",
            isMeta=True,
            sessionId="abc123",
            timestamp="2026-05-31T10:00:00Z",
            cwd="/Users/omarkhalil/OmarOS",
            gitBranch="main",
            version="2.1.0",
            message={"role": "user", "content": "<local-command-caveat>noise</local-command-caveat>"},
        ),
        _line(
            type="user",
            sessionId="abc123",
            timestamp="2026-05-31T10:00:05Z",
            cwd="/Users/omarkhalil/OmarOS",
            gitBranch="main",
            version="2.1.0",
            message={"role": "user", "content": "Hello, my key is sk-abcdef0123456789ABCDEFGHIJK please hide it"},
        ),
        _line(
            type="assistant",
            sessionId="abc123",
            timestamp="2026-05-31T10:00:10Z",
            cwd="/Users/omarkhalil/OmarOS",
            gitBranch="main",
            version="2.1.0",
            message={"role": "assistant", "content": [
                {"type": "thinking", "thinking": "secret reasoning"},
                {"type": "text", "text": "Sure, here goes."},
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "foo.py"}},
            ]},
        ),
        _line(
            type="assistant",
            sessionId="abc123",
            timestamp="2026-05-31T10:00:12Z",
            message={"role": "assistant", "content": [
                {"type": "tool_result", "content": "line1\nline2\nline3"},
            ]},
        ),
    ]


def test_parse_counts_and_meta():
    meta, turns = render.parse(_synthetic(), project="OmarOS")
    assert meta.title == "Build the thing"
    assert meta.session_id == "abc123"
    assert meta.cwd == "/Users/omarkhalil/OmarOS"
    assert meta.git_branch == "main"
    # the isMeta user turn is dropped; one real user turn remains
    assert meta.n_user == 1
    # two consecutive assistant lines merge into a single turn
    assert sum(1 for t in turns if t.role == "assistant") == 1


def test_thinking_omitted_by_default():
    md, _, _ = render.render_markdown(_synthetic(), project="OmarOS")
    assert "secret reasoning" not in md
    assert "💭" not in md


def test_thinking_included_on_flag():
    md, _, _ = render.render_markdown(_synthetic(), project="OmarOS", include_thinking=True)
    assert "secret reasoning" in md


def test_secret_redaction():
    md, _, redacted = render.render_markdown(_synthetic(), project="OmarOS")
    assert redacted is True
    assert "sk-abcdef0123456789" not in md
    assert "REDACTED" in md


def test_wrapper_stripped():
    md, meta, _ = render.render_markdown(_synthetic(), project="OmarOS")
    assert "local-command-caveat" not in md


def test_tool_use_collapsed():
    md, _, _ = render.render_markdown(_synthetic(), project="OmarOS")
    assert "🔧 **Edit**" in md
    assert "foo.py" in md
    assert "result: 3 line(s)" in md


def test_filename():
    meta, _ = render.parse(_synthetic(), project="OmarOS")
    fname = render.rendered_filename(meta)
    assert fname == "2026-05-31_abc123_build_the_thing.md"


def test_empty_transcript():
    meta, turns = render.parse([], project="x")
    assert meta.n_user == 0 and turns == []


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
