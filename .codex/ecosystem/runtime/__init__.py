"""Shared Constellation orchestration; repositories supply context, never code."""
from __future__ import annotations

from pathlib import Path


DEFAULT_POLICY = Path(__file__).resolve().with_name("review-policy.json")


def workspace_root(start: Path | None = None) -> Path | None:
    """Locate an explicit workspace registry without importing project code.

    A standalone project needs no registry. The caller still verifies real Git
    ownership and the registry before performing any workspace operation.
    """
    current = (start or Path.cwd()).resolve()
    if not current.is_dir():
        current = current.parent
    for candidate in (current, *current.parents):
        registry = candidate / ".codex/repositories.json"
        if registry.exists() or registry.is_symlink():
            return candidate
    return None
