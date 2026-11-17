#!/usr/bin/env python3
"""Render a native Codex rollout JSONL as a private readable transcript.

The raw mirror is the lossless authority. This renderer deliberately keeps only
human-visible user and assistant messages plus compact tool-call markers. It
never emits encrypted reasoning and redacts common credential shapes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_SECRET_PATTERNS = [
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[\"']?[A-Za-z0-9._\-]{16,}"),
    re.compile(r"(?i)(secret\s*[:=]\s*)[\"']?[A-Za-z0-9._\-]{16,}"),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL,
    ),
]


def _mask(match: re.Match) -> str:
    if match.groups():
        return f"{match.group(1)}***REDACTED***"
    value = match.group(0)
    if value.startswith("-----BEGIN"):
        return "-----BEGIN PRIVATE KEY-----\n***REDACTED***\n-----END PRIVATE KEY-----"
    return f"{value[:3]}***REDACTED***"


def redact_secrets(text: str) -> tuple[str, bool]:
    redacted = False
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            redacted = True
            text = pattern.sub(_mask, text)
    return text, redacted


@dataclass
class SessionMeta:
    session_id: str = ""
    cwd: str = ""
    model: str = ""
    provider: str = ""
    cli_version: str = ""
    originator: str = ""
    title: str = ""
    started: str = ""
    ended: str = ""
    n_user: int = 0
    n_assistant: int = 0
    project: str = "unknown"


@dataclass
class Turn:
    role: str
    timestamp: str
    parts: list[str] = field(default_factory=list)


def project_slug(cwd: str) -> str:
    if not cwd:
        return "unknown"
    path = Path(cwd)
    name = path.name or "home"
    return _slugify(name, maxlen=64)


def _append_turn(turns: list[Turn], role: str, timestamp: str, text: str) -> None:
    text = text.strip()
    if not text:
        return
    if turns and turns[-1].role == role:
        turns[-1].parts.append(text)
    else:
        turns.append(Turn(role=role, timestamp=timestamp, parts=[text]))


def _content_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"input_text", "output_text", "text"}:
            value = item.get("text")
            if isinstance(value, str):
                parts.append(value)
    return "\n\n".join(parts)


def _tool_brief(payload: dict) -> str:
    name = str(payload.get("name", "tool"))
    raw = payload.get("input", "")
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            decoded = raw
    else:
        decoded = raw
    brief = ""
    if isinstance(decoded, dict):
        for key in (
            "cmd", "command", "path", "file_path", "query", "prompt",
            "target", "description", "url",
        ):
            value = decoded.get(key)
            if isinstance(value, str):
                brief = value
                break
    elif isinstance(decoded, str):
        brief = decoded
    brief = re.sub(r"\s+", " ", brief).strip()[:140]
    return f"> 🔧 **{name}**" + (f" — `{brief}`" if brief else "")


def _fallback_response_turns(records: list[dict]) -> list[Turn]:
    turns: list[Turn] = []
    for obj in records:
        if obj.get("type") != "response_item":
            continue
        payload = obj.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "message":
            continue
        role = payload.get("role")
        if role not in {"user", "assistant"}:
            continue
        text = _content_text(payload.get("content"))
        _append_turn(turns, role, str(obj.get("timestamp", "")), text)
    return turns


def parse(lines: list[str], source_session_id: str = "") -> tuple[SessionMeta, list[Turn]]:
    meta = SessionMeta(session_id=source_session_id)
    turns: list[Turn] = []
    records: list[dict] = []
    first_user = ""
    session_meta_seen = False

    for raw in lines:
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(obj, dict):
            continue
        records.append(obj)
        timestamp = str(obj.get("timestamp", ""))
        if timestamp:
            meta.started = meta.started or timestamp
            meta.ended = timestamp

        record_type = obj.get("type")
        payload = obj.get("payload")
        if not isinstance(payload, dict):
            continue

        if record_type == "session_meta":
            # Forks can embed an ancestor's metadata later in the rollout.
            # The source filename identifies the archived file; only its first
            # metadata envelope describes this session rather than its history.
            if session_meta_seen:
                continue
            session_meta_seen = True
            meta.session_id = str(
                source_session_id or payload.get("id") or payload.get("session_id") or ""
            )
            meta.cwd = str(payload.get("cwd") or meta.cwd)
            meta.provider = str(payload.get("model_provider") or meta.provider)
            meta.cli_version = str(payload.get("cli_version") or meta.cli_version)
            meta.originator = str(payload.get("originator") or meta.originator)
            meta.started = str(payload.get("timestamp") or meta.started)
            continue

        if record_type == "turn_context":
            meta.model = str(payload.get("model") or meta.model)
            meta.cwd = str(payload.get("cwd") or meta.cwd)
            continue

        if record_type != "event_msg":
            continue
        event_type = payload.get("type")
        message = payload.get("message")
        if event_type == "user_message" and isinstance(message, str):
            meta.n_user += 1
            first_user = first_user or message.strip()
            _append_turn(turns, "user", timestamp, message)
        elif event_type == "agent_message" and isinstance(message, str):
            meta.n_assistant += 1
            _append_turn(turns, "assistant", timestamp, message)

    if not turns:
        turns = _fallback_response_turns(records)
        meta.n_user = sum(turn.role == "user" for turn in turns)
        meta.n_assistant = sum(turn.role == "assistant" for turn in turns)
        first_user = next(
            (turn.parts[0] for turn in turns if turn.role == "user" and turn.parts),
            "",
        )

    meta.project = project_slug(meta.cwd)
    if first_user:
        first_line = next((line.strip() for line in first_user.splitlines() if line.strip()), "")
        meta.title = re.sub(r"^[#>*\-\s]+", "", first_line)[:120].strip()
    return meta, turns


def _slugify(text: str, maxlen: int = 48) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.ASCII).strip().lower()
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:maxlen].strip("_") or "untitled"


def _date_of(timestamp: str) -> str:
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return "0000-00-00"


def _filename_session_id(session_id: str) -> str:
    """Return a filesystem-safe identifier without collapsing distinct sessions."""
    value = session_id or "unknown-session"
    safe = re.sub(r"[^A-Za-z0-9-]", "_", value).strip("_-")
    if len(safe) <= 80:
        return safe or "unknown-session"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{safe[:48]}-{digest}"


def rendered_filename(meta: SessionMeta) -> str:
    return (
        f"{_date_of(meta.started)}_"
        f"{_filename_session_id(meta.session_id)}_"
        f"{_slugify(meta.title)}.md"
    )


def render_markdown(
    lines: list[str], *, source_session_id: str = "", redact: bool = True
) -> tuple[str, SessionMeta, bool]:
    meta, turns = parse(lines, source_session_id=source_session_id)
    created = _date_of(meta.started)
    updated = _date_of(meta.ended) if meta.ended else created
    title = meta.title or f"Codex session {(meta.session_id or 'unknown')[:8]}"
    frontmatter = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        "note_type: conversation",
        "status: active",
        f"created: {created}",
        f"updated: {updated}",
        "author: Omar",
        "domain: 09_Data_Sources",
        "subdomain: Codex_Conversations",
        f"project: {json.dumps(meta.project, ensure_ascii=False)}",
        f"session_id: {json.dumps(meta.session_id)}",
        f"cwd: {json.dumps(meta.cwd, ensure_ascii=False)}",
        f"model: {json.dumps(meta.model)}",
        f"model_provider: {json.dumps(meta.provider)}",
        f"cli_version: {json.dumps(meta.cli_version)}",
        f"turns_user: {meta.n_user}",
        f"turns_assistant: {meta.n_assistant}",
        "source: codex_local_session",
        "tags: [codex_conversation, transcript, local_only]",
        "ai_generated: true",
        "ai_reviewed: false",
        "---",
        "",
    ]
    body = [f"# {title}", ""]
    if meta.started:
        body.extend([
            f"_{meta.started} → {meta.ended}_  ·  `{meta.cwd}`  ·  `{meta.model}`",
            "",
        ])
    for turn in turns:
        body.extend([
            "## 👤 User" if turn.role == "user" else "## 🤖 Assistant",
            "",
            "\n\n".join(part for part in turn.parts if part.strip()),
            "",
        ])
    markdown = "\n".join(frontmatter + body) + "\n"
    redacted = False
    if redact:
        markdown, redacted = redact_secrets(markdown)
    return markdown, meta, redacted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("-o", "--out", type=Path)
    parser.add_argument("--no-redact", action="store_true")
    args = parser.parse_args()
    lines = args.jsonl.read_text(encoding="utf-8", errors="replace").splitlines()
    markdown, meta, redacted = render_markdown(
        lines,
        source_session_id=args.jsonl.stem,
        redact=not args.no_redact,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        args.out.write_text(markdown, encoding="utf-8")
        os.chmod(args.out, 0o600)
        print(
            f"wrote {args.out} ({meta.n_user}u/{meta.n_assistant}a, "
            f"redacted={redacted})"
        )
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
