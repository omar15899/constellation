#!/usr/bin/env python3
"""Render a Claude Code ``.jsonl`` transcript into readable markdown.

Each line of the transcript is a JSON object. The lines that matter for a
human-readable conversation are ``user`` and ``assistant`` message records; the
rest (``system``, ``file-history-snapshot``, ``worktree-state``,
``queue-operation``, ``ai-title``, ``last-prompt``…) carry session metadata or
internal bookkeeping. ``ai-title`` gives the session title.

The renderer:
  * merges consecutive same-role messages into one section,
  * collapses tool calls / tool results to compact one-liners,
  * omits ``thinking`` blocks unless asked,
  * strips the local-command / system-reminder wrappers injected by the harness,
  * redacts obvious secrets before the markdown is committed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# --- secret redaction ------------------------------------------------------

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[\"']?[A-Za-z0-9._\-]{16,}"),
    re.compile(r"(?i)(secret\s*[:=]\s*)[\"']?[A-Za-z0-9._\-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def redact_secrets(text: str) -> tuple[str, bool]:
    """Return (redacted_text, did_redact)."""
    redacted = False
    for pat in _SECRET_PATTERNS:
        if pat.search(text):
            redacted = True
            text = pat.sub(lambda m: _mask(m), text)
    return text, redacted


def _mask(m: re.Match) -> str:
    g = m.group(0)
    # Preserve a leading "key=" / "Bearer " prefix when the pattern captured one.
    if m.groups():
        prefix = m.group(1)
        return f"{prefix}***REDACTED***"
    head = g[:3]
    return f"{head}***REDACTED***"


# --- wrapper stripping ------------------------------------------------------

_WRAPPER_BLOCKS = [
    re.compile(r"<local-command-caveat>.*?</local-command-caveat>", re.DOTALL),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL),
    re.compile(r"<command-message>.*?</command-message>", re.DOTALL),
    re.compile(r"<command-name>.*?</command-name>", re.DOTALL),
    re.compile(r"<command-args>.*?</command-args>", re.DOTALL),
    re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.DOTALL),
]


def strip_wrappers(text: str) -> str:
    for pat in _WRAPPER_BLOCKS:
        text = pat.sub("", text)
    return text.strip()


# --- model -----------------------------------------------------------------

@dataclass
class SessionMeta:
    session_id: str = ""
    cwd: str = ""
    git_branch: str = ""
    version: str = ""
    title: str = ""
    started: str = ""
    ended: str = ""
    n_user: int = 0
    n_assistant: int = 0
    project: str = ""


@dataclass
class Turn:
    role: str
    timestamp: str
    parts: list[str] = field(default_factory=list)


def _blocks(content) -> list[dict]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def _tool_brief(inp) -> str:
    if not isinstance(inp, dict):
        return ""
    for key in ("file_path", "path", "command", "pattern", "query",
                "prompt", "url", "description", "notebook_path"):
        if key in inp and isinstance(inp[key], str):
            val = inp[key].replace("\n", " ").strip()
            return val[:120]
    return ""


def _render_block(block: dict, include_thinking: bool) -> str | None:
    btype = block.get("type")
    if btype == "text":
        return strip_wrappers(block.get("text", ""))
    if btype == "thinking":
        if not include_thinking:
            return None
        return f"> 💭 _thinking_\n>\n> {block.get('thinking', '').strip()}"
    if btype == "tool_use":
        name = block.get("name", "tool")
        brief = _tool_brief(block.get("input"))
        return f"> 🔧 **{name}**" + (f" — `{brief}`" if brief else "")
    if btype == "tool_result":
        content = block.get("content")
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = " ".join(
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        n_lines = text.count("\n") + 1 if text else 0
        flag = " ⚠️ error" if block.get("is_error") else ""
        return f"> ↳ _result: {n_lines} line(s){flag}_"
    return None


def parse(
    lines: list[str], project: str = "", include_thinking: bool = False
) -> tuple[SessionMeta, list[Turn]]:
    meta = SessionMeta(project=project)
    turns: list[Turn] = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        ltype = obj.get("type")

        if ltype == "ai-title":
            meta.title = obj.get("aiTitle", meta.title)
            continue
        if ltype not in ("user", "assistant"):
            # capture session identity from any line that carries it
            meta.session_id = meta.session_id or obj.get("sessionId", "")
            continue
        if obj.get("isMeta"):
            # harness-injected turn (caveats, command echoes); skip from prose
            meta.session_id = meta.session_id or obj.get("sessionId", "")
            continue

        meta.session_id = meta.session_id or obj.get("sessionId", "")
        meta.cwd = obj.get("cwd", meta.cwd)
        meta.git_branch = obj.get("gitBranch", meta.git_branch)
        meta.version = obj.get("version", meta.version)
        ts = obj.get("timestamp", "")
        if ts:
            meta.started = meta.started or ts
            meta.ended = ts

        message = obj.get("message", {})
        if not isinstance(message, dict):
            continue
        role = message.get("role", ltype)
        blocks = _blocks(message.get("content"))
        parts: list[str] = []
        for block in blocks:
            rendered = _render_block(block, include_thinking=include_thinking)
            if rendered:
                parts.append(rendered)
        # drop messages that were pure wrappers / empty after stripping
        if not any(p.strip() for p in parts):
            continue

        # A user-role message carrying only tool_result blocks is the CLI's way
        # of feeding a tool's output back to the model — it is part of the
        # assistant's action flow, not a human turn. Fold it into the assistant
        # stream so the transcript reads naturally.
        is_tool_result_only = bool(blocks) and all(
            b.get("type") == "tool_result" for b in blocks
        )
        effective_role = "assistant" if (role == "user" and is_tool_result_only) else role

        if effective_role == "user":
            meta.n_user += 1
        elif role == "assistant":
            meta.n_assistant += 1

        if turns and turns[-1].role == effective_role:
            turns[-1].parts.extend(parts)
        else:
            turns.append(Turn(role=effective_role, timestamp=ts, parts=parts))

    return meta, turns


def _slugify(text: str, maxlen: int = 48) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.ASCII).strip().lower()
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:maxlen].strip("_") or "untitled"


def _date_of(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return "0000-00-00"


def rendered_filename(meta: SessionMeta) -> str:
    date = _date_of(meta.started)
    sid8 = (meta.session_id or "00000000")[:8]
    title = _slugify(meta.title) if meta.title else "untitled"
    return f"{date}_{sid8}_{title}.md"


def render_markdown(
    lines: list[str],
    *,
    project: str = "",
    redact: bool = True,
    include_thinking: bool = False,
) -> tuple[str, SessionMeta, bool]:
    """Return (markdown, meta, redacted)."""
    meta, turns = parse(lines, project, include_thinking=include_thinking)

    created = _date_of(meta.started)
    updated = _date_of(meta.ended) if meta.ended else created
    fm = [
        "---",
        f"title: {json.dumps(meta.title or 'Untitled Claude session', ensure_ascii=False)}",
        "note_type: conversation",
        "status: active",
        f"created: {created}",
        f"updated: {updated}",
        "author: Omar",
        "domain: 09_Data_Sources",
        f"project: {meta.project or 'unknown'}",
        f"session_id: {meta.session_id}",
        f"cwd: {meta.cwd}",
        f"git_branch: {meta.git_branch}",
        f"cli_version: {meta.version}",
        f"turns_user: {meta.n_user}",
        f"turns_assistant: {meta.n_assistant}",
        "tags: [claude_conversation, transcript]",
        "ai_generated: true",
        "ai_reviewed: false",
        "---",
        "",
    ]
    body = [f"# {meta.title or 'Claude session ' + meta.session_id[:8]}", ""]
    if meta.started:
        body.append(f"_{meta.started} → {meta.ended}_  ·  `{meta.cwd}`  ·  `{meta.git_branch}`")
        body.append("")

    for turn in turns:
        header = "## 👤 User" if turn.role == "user" else "## 🤖 Assistant"
        body.append(header)
        body.append("")
        body.append("\n\n".join(p for p in turn.parts if p.strip()))
        body.append("")

    md = "\n".join(fm) + "\n".join(body) + "\n"

    redacted = False
    if redact:
        md, redacted = redact_secrets(md)
    return md, meta, redacted


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a Claude .jsonl transcript to markdown")
    ap.add_argument("jsonl", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--no-redact", action="store_true")
    ap.add_argument("--include-thinking", action="store_true")
    args = ap.parse_args()

    lines = args.jsonl.read_text(errors="replace").splitlines()
    md, meta, redacted = render_markdown(
        lines,
        redact=not args.no_redact,
        include_thinking=args.include_thinking,
    )
    if args.out:
        args.out.write_text(md)
        print(f"wrote {args.out} ({meta.n_user}u/{meta.n_assistant}a, "
              f"redacted={redacted})")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
