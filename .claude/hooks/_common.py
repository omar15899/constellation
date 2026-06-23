"""hooks/_common.py — shared utilities for constellation-level hooks.

Hooks live one-per-file. This module gives them a common shape:

- locate_hub()       → resolve ~/GitHub/.claude/ regardless of CWD
- registry_path()    → absolute path of registry/repos.yaml
- iter_repos()       → yield (name, path) for every git repo on disk
- log()              → tagged print to stderr; never silent
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator

GITHUB_ROOT = Path.home() / "GitHub"
HUB = GITHUB_ROOT / ".claude"


def locate_hub() -> Path:
    if not HUB.exists():
        raise RuntimeError(f"constellation hub missing: {HUB}")
    return HUB


def registry_path() -> Path:
    p = HUB / "registry" / "repos.yaml"
    if not p.exists():
        raise RuntimeError(f"registry not found: {p}")
    return p


def iter_repos() -> Iterator[tuple[str, Path]]:
    """Yield (name, path) for every git repo under ~/GitHub/."""
    if not GITHUB_ROOT.exists():
        return
    for child in sorted(GITHUB_ROOT.iterdir()):
        if child.name.startswith("."):
            continue
        if not child.is_dir():
            continue
        if (child / ".git").exists():
            yield child.name, child


def log(tag: str, msg: str) -> None:
    sys.stderr.write(f"[constellation:{tag}] {msg}\n")
    sys.stderr.flush()


def env_flag(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, "").strip().lower()
    if not v:
        return default
    return v not in ("0", "false", "no", "off")
