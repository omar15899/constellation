"""Bind private learning capture to the centrally configured OmarOS Git owner."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

PROJECTS = Path(__file__).resolve().parents[1] / "profiles/projects.json"


class HookError(ValueError):
    """The selected vault cannot be established from the central profile."""


def vault_binding(root: Path) -> dict[str, Any]:
    """Return the identity of a canonical Git owner without inherited Git overrides.

    Args:
        root: Absolute canonical path of the vault, not a nested directory.

    Returns:
        Root path and filesystem identities for the owner and Git directory.

    Raises:
        HookError: A symlink, non-owner directory, or invalid Git root is selected.
    """
    if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir():
        raise HookError("The vault must be a canonical absolute directory")
    marker = root / ".git"
    if marker.is_symlink() or not marker.exists():
        raise HookError("The vault must have a real Git owner")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(PATH=os.defpath, GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "rev-parse", "--show-toplevel", "--absolute-git-dir"],
                            cwd=root, env=env, capture_output=True, text=True, timeout=5)
    lines = result.stdout.splitlines()
    if result.returncode or len(lines) != 2 or Path(lines[0]) != root:
        raise HookError("The vault must be its own Git owner")
    git_dir = Path(lines[1])
    if git_dir.resolve(strict=True) != git_dir or not git_dir.is_dir():
        raise HookError("The Git directory must be canonical")
    owner, git = root.stat(), git_dir.stat()
    return {"schema": 1, "root": str(root), "owner": [owner.st_dev, owner.st_ino],
            "git_dir": [git.st_dev, git.st_ino]}


def check_profile_binding(profile: Path, name: str) -> dict[str, Any]:
    """Check the selected root and identity against one explicit profile file.

    This function is separate so fixtures can use their own central profiles.
    The production entry always supplies PROJECTS, never caller environment data.
    """
    if profile.is_symlink() or not stat.S_ISREG(profile.stat().st_mode):
        raise HookError("The central project profile must be a regular file")
    with profile.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise HookError("The project profile is too large")
    projects = json.loads(raw)["projects"]
    candidates = [p for p in projects if p.get("id") == "omaros"]
    if len(candidates) != 1 or candidates[0].get("root") != name:
        raise HookError("Private capture requires the centrally configured OmarOS root")
    binding = vault_binding(Path(name))
    expected = candidates[0].get("filesystem_identity")
    if expected != {key: binding[key] for key in ("owner", "git_dir")}:
        raise HookError("The registered vault filesystem identity changed")
    return binding


def check_vault_registration(home: Path, name: str, *, require_bound: bool) -> dict[str, Any]:
    """Validate the central profile; home is retained only for the skill API.

    CODEX_HOME and project-controlled files cannot select another private vault.
    """
    return check_profile_binding(PROJECTS, name)
