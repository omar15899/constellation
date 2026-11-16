#!/usr/bin/env python3
"""Enumerate every Claude Code transcript under ~/.claude/projects.

A transcript is one ``<sessionId>.jsonl`` file inside a per-project directory
whose name encodes the original cwd (``-Users-omarkhalil-OmarOS`` etc.). The
scan is cheap: it only stats files, never reads them, so the daemon can run it
on every tick.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECTS_DIR = Path.home() / ".claude" / "projects"
HOME_PREFIX = "-Users-omarkhalil-"


@dataclass
class Source:
    path: Path
    project: str
    session_id: str
    mtime: float
    size: int

    @property
    def key(self) -> str:
        return str(self.path)


def project_slug(project_dir_name: str) -> str:
    """Turn a ~/.claude/projects directory name into a human project key."""
    name = project_dir_name
    if name.startswith(HOME_PREFIX):
        name = name[len(HOME_PREFIX):]
    return name or "home"


def scan() -> list[Source]:
    if not PROJECTS_DIR.exists():
        return []
    out: list[Source] = []
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        slug = project_slug(project_dir.name)
        for jsonl in sorted(project_dir.glob("*.jsonl")):
            try:
                st = jsonl.stat()
            except OSError:
                continue
            out.append(
                Source(
                    path=jsonl,
                    project=slug,
                    session_id=jsonl.stem,
                    mtime=st.st_mtime,
                    size=st.st_size,
                )
            )
    return out


if __name__ == "__main__":
    import collections

    sources = scan()
    by_project: dict[str, int] = collections.Counter(s.project for s in sources)
    total_bytes = sum(s.size for s in sources)
    print(f"{len(sources)} transcripts across {len(by_project)} projects, "
          f"{total_bytes / 1e6:.0f} MB")
    for proj, n in sorted(by_project.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {proj}")
