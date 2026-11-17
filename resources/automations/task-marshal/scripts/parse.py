"""Parser / serializer for task-marshal YAML task blocks.

Uses PyYAML when available (loaded from the skill's uv venv). Falls back to a
small handwritten subset-parser so the scripts still run in minimal environments
(CI, fresh clone before `uv sync`, etc.).

Public API:
    read_daily(path)          -> list[TaskDict]
    read_all(daily_dir)       -> list[TaskDict]  (each dict has extra `_source`)
    task_to_block(task)       -> str  (full ```yaml task ...``` fenced block)
    tasks_of(content)         -> list[TaskDict] extracted from a markdown str
    SCHEMA_FIELDS, ENUMS      -> constants
    validate(task)            -> list[str] error messages
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bootstrap: make the OmarOS root venv importable if present.
#
# Canonical venv lives at ~/.venvs/omaros/ (moved outside the vault so it
# is not tracked by git). When run through `uv run` (with UV_PROJECT_ENVIRONMENT
# set) we don't need this bootstrap — sys.path is already correct. The bootstrap
# only matters for raw `python3 script.py` fallback invocations.
# ---------------------------------------------------------------------------
_OMAROS_ROOT = Path(
    os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS"))
)
_VENV_CANDIDATES = [
    Path.home() / ".venvs" / "omaros",  # canonical location
    _OMAROS_ROOT / ".venv",             # legacy fallback
]
for _venv_root in _VENV_CANDIDATES:
    _site_root = _venv_root / "lib"
    if _site_root.exists():
        for _child in _site_root.iterdir():
            _sp = _child / "site-packages"
            if _sp.exists() and str(_sp) not in sys.path:
                sys.path.insert(0, str(_sp))
                break
        break

try:
    import yaml  # PyYAML
    _HAS_PYYAML = True
except ImportError:  # pragma: no cover — fallback path
    _HAS_PYYAML = False


# --- schema ---------------------------------------------------------------

SCHEMA_FIELDS: tuple[str, ...] = (
    "id", "title", "when", "time_of_day", "duration_min",
    "status", "priority", "project", "tags", "energy", "location",
    "created_at", "closed_at", "body", "references",
)

SCALAR_FIELDS: tuple[str, ...] = (
    "id", "title", "when", "time_of_day", "duration_min",
    "status", "priority", "project", "energy", "location",
    "created_at", "closed_at",
)
LIST_FIELDS: tuple[str, ...] = ("tags",)
BLOCK_FIELDS: tuple[str, ...] = ("body", "references")

ENUMS: dict[str, set[str]] = {
    "status": {"open", "done", "cancelled", "rolled_over", "blocked", "waiting"},
    "priority": {"P0", "P1", "P2", "P3"},
    "time_of_day": {"morning", "afternoon", "evening", "night"},
    "energy": {"low", "medium", "high"},
    "location": {"home", "office", "outside", "travel"},
}

_FENCE_OPEN = re.compile(r"^```yaml\s+task\s*$")
_FENCE_CLOSE = re.compile(r"^```\s*$")


# --- parsing --------------------------------------------------------------

def _normalise_task_dict(d: dict) -> dict:
    """Ensure every schema field is present (null if absent), cast types."""
    out: dict = {k: None for k in SCHEMA_FIELDS}
    out["tags"] = []
    for k, v in d.items():
        if k not in SCHEMA_FIELDS:
            continue
        out[k] = v
    # Coerce tags to list
    if out["tags"] is None:
        out["tags"] = []
    if not isinstance(out["tags"], list):
        out["tags"] = [str(out["tags"])]
    # Coerce duration_min to int
    if out["duration_min"] is not None and not isinstance(out["duration_min"], int):
        try:
            out["duration_min"] = int(out["duration_min"])
        except (TypeError, ValueError):
            out["duration_min"] = None
    # stringify any datetime-typed values so downstream comparators stay consistent
    for k in ("when", "created_at", "closed_at"):
        if out[k] is not None and not isinstance(out[k], str):
            out[k] = str(out[k])
    # PyYAML's `|` block scalar preserves a trailing newline. Drop it so the
    # fallback parser and pyyaml paths agree exactly.
    for k in BLOCK_FIELDS:
        if isinstance(out[k], str):
            out[k] = out[k].rstrip("\n") or None
    return out


def _parse_block_pyyaml(text: str) -> dict:
    """Parse a single task block body using PyYAML."""
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        return {k: None for k in SCHEMA_FIELDS} | {"tags": []}
    return _normalise_task_dict(data)


# --- fallback parser (used only if PyYAML absent) ------------------------

_SCALAR_LINE = re.compile(r"^([a-z_]+):\s*(.*)$")
_INLINE_LIST = re.compile(r"^\[(.*)\]$")


def _fallback_scalar(raw: str) -> Any:
    s = raw.strip()
    if s == "" or s.lower() == "null" or s == "~":
        return None
    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        return int(s)
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _fallback_inline_list(raw: str) -> list[str]:
    m = _INLINE_LIST.match(raw.strip())
    if not m:
        return []
    inner = m.group(1).strip()
    return [p.strip() for p in inner.split(",") if p.strip()] if inner else []


def _parse_block_fallback(text: str) -> dict:
    lines = text.splitlines()
    out: dict = {k: None for k in SCHEMA_FIELDS}
    out["tags"] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = _SCALAR_LINE.match(line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2)
        if key in BLOCK_FIELDS:
            if rest.strip() == "|":
                i += 1
                buf: list[str] = []
                indent = None
                while i < len(lines):
                    nxt = lines[i]
                    if nxt.strip() == "":
                        buf.append("")
                        i += 1
                        continue
                    lead = len(nxt) - len(nxt.lstrip(" "))
                    if indent is None:
                        indent = lead if lead > 0 else 2
                    if lead < indent and nxt.strip():
                        break
                    buf.append(nxt[indent:] if len(nxt) >= indent else nxt.lstrip(" "))
                    i += 1
                while buf and buf[-1] == "":
                    buf.pop()
                out[key] = "\n".join(buf) if buf else None
                continue
            out[key] = _fallback_scalar(rest)
        elif key in LIST_FIELDS:
            out[key] = _fallback_inline_list(rest) if rest.strip() else []
        elif key in SCALAR_FIELDS:
            out[key] = _fallback_scalar(rest)
        i += 1
    return out


def _parse_block(text: str) -> dict:
    if _HAS_PYYAML:
        try:
            return _parse_block_pyyaml(text)
        except yaml.YAMLError:
            # malformed block — fall through to tolerant fallback
            pass
    return _parse_block_fallback(text)


# --- top-level extraction -------------------------------------------------

def tasks_of(content: str) -> list[dict]:
    """Extract all task dicts from a markdown string."""
    out: list[dict] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        if _FENCE_OPEN.match(lines[i]):
            i += 1
            start = i
            while i < len(lines) and not _FENCE_CLOSE.match(lines[i]):
                i += 1
            block = "\n".join(lines[start:i])
            out.append(_parse_block(block))
            if i < len(lines):
                i += 1
        else:
            i += 1
    return out


def read_daily(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return tasks_of(path.read_text(encoding="utf-8"))


def read_all(daily_dir: Path) -> list[dict]:
    out: list[dict] = []
    if not daily_dir.exists():
        return out
    for p in sorted(daily_dir.glob("*.md")):
        for t in read_daily(p):
            t["_source"] = str(p)
            out.append(t)
    return out


# --- serialization --------------------------------------------------------

def _render_scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    s = str(v)
    needs_quote = (
        s != s.strip()
        or any(c in s for c in ["#", "[", "]", "{", "}", "'", "\""])
        or s.lower() in {"null", "true", "false"}
    )
    if needs_quote:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def task_to_block(task: dict) -> str:
    """Render a task dict as a fenced ```yaml task ...``` block.

    We write by hand (not via yaml.dump) to keep:
      - field order fixed (SCHEMA_FIELDS)
      - block-scalar style for body/references
      - no Python-None surprises
    This preserves deterministic output regardless of parser path.
    """
    lines = ["```yaml task"]
    for field in SCHEMA_FIELDS:
        v = task.get(field)
        if field in LIST_FIELDS:
            items = v or []
            lines.append(f"{field}: [" + ", ".join(str(x) for x in items) + "]")
        elif field in BLOCK_FIELDS:
            if v is None or v == "":
                lines.append(f"{field}: null")
            else:
                lines.append(f"{field}: |")
                for ln in str(v).splitlines():
                    lines.append("  " + ln if ln else "")
        else:
            lines.append(f"{field}: {_render_scalar(v)}")
    lines.append("```")
    return "\n".join(lines)


# --- validation -----------------------------------------------------------

def validate(task: dict) -> list[str]:
    errors: list[str] = []
    if not task.get("title"):
        errors.append("missing title")
    for field, allowed in ENUMS.items():
        v = task.get(field)
        if v is not None and v not in allowed:
            errors.append(f"{field}={v!r} not in {sorted(allowed)}")
    return errors


# --- self-test ------------------------------------------------------------

if __name__ == "__main__":
    import json

    mode = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if mode == "parse":
        print(json.dumps(tasks_of(sys.stdin.read()), indent=2, ensure_ascii=False))
    elif mode == "render":
        task = json.load(sys.stdin)
        print(task_to_block(task))
    else:
        sample = {
            "id": "2026-04-22-001", "title": "hello", "when": "2026-04-22",
            "time_of_day": "morning", "duration_min": 30, "status": "open",
            "priority": "P1", "project": None, "tags": ["a", "b"],
            "energy": None, "location": None,
            "created_at": "2026-04-22T10:00", "closed_at": None,
            "body": "line1\nline2", "references": None,
        }
        block = task_to_block(sample)
        print(block)
        print("---")
        back = tasks_of(block)
        assert len(back) == 1, back
        assert back[0]["title"] == "hello"
        assert back[0]["tags"] == ["a", "b"]
        assert back[0]["body"] == "line1\nline2"
        assert back[0]["duration_min"] == 30
        print(f"self-test OK (pyyaml={_HAS_PYYAML})")
