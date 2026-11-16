#!/usr/bin/env python3
"""Enumerate local Codex rollout transcripts without reading their content."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
SESSIONS_DIR = CODEX_HOME / "sessions"
ARCHIVED_SESSIONS_DIR = CODEX_HOME / "archived_sessions"
_UUID = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Source:
    path: Path
    session_id: str
    mtime: float
    size: int

    @property
    def key(self) -> str:
        return str(self.path)


def session_id_from_path(path: Path) -> str:
    match = _UUID.search(path.stem)
    return match.group(1) if match else path.stem


def scan() -> list[Source]:
    """Return rollouts from both active and archived local session stores."""
    out: list[Source] = []
    for directory in (SESSIONS_DIR, ARCHIVED_SESSIONS_DIR):
        if not directory.exists():
            continue
        for jsonl in sorted(directory.rglob("*.jsonl")):
            if not jsonl.is_file():
                continue
            try:
                stat = jsonl.stat()
            except OSError:
                continue
            out.append(
                Source(
                    path=jsonl,
                    session_id=session_id_from_path(jsonl),
                    mtime=stat.st_mtime,
                    size=stat.st_size,
                )
            )
    return out


if __name__ == "__main__":
    sources = scan()
    total_bytes = sum(source.size for source in sources)
    print(f"{len(sources)} Codex transcript(s), {total_bytes / 1e6:.1f} MB")
