#!/usr/bin/env python3
"""Schema, privacy, and fallback tests for the Codex renderer."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import render  # noqa: E402


def line(record_type: str, payload: dict, timestamp: str) -> str:
    return json.dumps({"timestamp": timestamp, "type": record_type, "payload": payload})


def synthetic() -> list[str]:
    return [
        line(
            "session_meta",
            {
                "id": "abc12300-0000-0000-0000-000000000000",
                "cwd": "/Users/omarkhalil/OmarOS",
                "model_provider": "openai",
                "cli_version": "0.146.0",
                "originator": "codex_cli_rs",
                "timestamp": "2026-07-30T10:00:00Z",
            },
            "2026-07-30T10:00:00Z",
        ),
        line(
            "turn_context",
            {"model": "gpt-5.6-sol", "cwd": "/Users/omarkhalil/OmarOS"},
            "2026-07-30T10:00:01Z",
        ),
        line(
            "event_msg",
            {
                "type": "user_message",
                "message": "Guarda estas conversaciones; key=sk-proj-abcdefghijklmnopqrstuvwxyz",
                "text_elements": [],
            },
            "2026-07-30T10:00:02Z",
        ),
        line(
            "response_item",
            {"type": "reasoning", "encrypted_content": "must-never-render"},
            "2026-07-30T10:00:03Z",
        ),
        line(
            "event_msg",
            {"type": "agent_message", "message": "Archivado local.", "phase": "final_answer"},
            "2026-07-30T10:00:04Z",
        ),
    ]


def test_native_schema_and_metadata() -> None:
    meta, turns = render.parse(synthetic())
    assert meta.session_id == "abc12300-0000-0000-0000-000000000000"
    assert meta.cwd == "/Users/omarkhalil/OmarOS"
    assert meta.project == "omaros"
    assert meta.model == "gpt-5.6-sol"
    assert meta.n_user == 1 and meta.n_assistant == 1
    assert [turn.role for turn in turns] == ["user", "assistant"]


def test_redaction_and_reasoning_omission() -> None:
    markdown, _, redacted = render.render_markdown(synthetic())
    assert redacted is True
    assert "sk-proj-abcdefghijklmnopqrstuvwxyz" not in markdown
    assert "REDACTED" in markdown
    assert "must-never-render" not in markdown


def test_local_only_frontmatter_and_filename() -> None:
    markdown, meta, _ = render.render_markdown(synthetic())
    assert "tags: [codex_conversation, transcript, local_only]" in markdown
    assert "source: codex_local_session" in markdown
    assert render.rendered_filename(meta).startswith(
        "2026-07-30_abc12300-0000-0000-0000-000000000000_"
    )


def test_filename_distinguishes_time_ordered_uuid_prefix_collisions() -> None:
    first = render.SessionMeta(
        session_id="019f71c1-2245-7423-9f4c-988791100a25",
        started="2026-07-17T20:25:10Z",
        title="Same title",
    )
    second = render.SessionMeta(
        session_id="019f71c1-2247-7791-87ba-a6e49ff8d1c0",
        started="2026-07-17T20:25:10Z",
        title="Same title",
    )
    assert render.rendered_filename(first) != render.rendered_filename(second)


def test_response_item_fallback() -> None:
    records = [
        line(
            "response_item",
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Hello"}]},
            "2026-07-30T10:00:00Z",
        ),
        line(
            "response_item",
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hi"}]},
            "2026-07-30T10:00:01Z",
        ),
    ]
    meta, turns = render.parse(records, source_session_id="fallback")
    assert meta.n_user == 1 and meta.n_assistant == 1
    assert turns[0].parts == ["Hello"] and turns[1].parts == ["Hi"]


def test_inherited_metadata_cannot_replace_session_identity() -> None:
    records = synthetic() + [
        line(
            "session_meta",
            {
                "id": "ancestor-session",
                "cwd": "/another/project",
                "timestamp": "2026-01-01T00:00:00Z",
            },
            "2026-07-30T10:00:05Z",
        ),
    ]
    meta, _ = render.parse(records, source_session_id="fork-session")
    assert meta.session_id == "fork-session"
    assert meta.cwd == "/Users/omarkhalil/OmarOS"
    assert meta.started == "2026-07-30T10:00:00Z"

    without_source, _ = render.parse(records)
    assert without_source.session_id == "abc12300-0000-0000-0000-000000000000"


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"\n{len(tests)} passed")
