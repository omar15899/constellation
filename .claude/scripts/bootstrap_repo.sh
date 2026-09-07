#!/usr/bin/env bash
# bootstrap_repo.sh — create missing constellation scaffold files.
# Usage: bootstrap_repo.sh <repo_path> [--variant quantos|adjacent] [--apply]
# Dry-run is the default. Existing files are preserved; templates need local configuration.
set -euo pipefail

exec python3 - "$0" "$@" <<'PY'
from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path
import stat
import subprocess
import sys

HUB = Path(sys.argv[1]).resolve().parents[1]
DIRECTORIES = (
    ".claude", ".claude/agents", ".claude/commands", ".claude/skills",
    ".claude/hooks", ".claude/registry",
)


class BootstrapError(Exception):
    """A precondition failed; do not silently omit part of the scaffold."""


def repo_root(value: str) -> Path:
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise BootstrapError(f"not a directory: {root}")
    # Ambient Git routing must not make an unrelated directory look like a root.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, timeout=10, env=env,
    )
    if result.returncode or Path(result.stdout.rstrip("\n")).resolve() != root:
        raise BootstrapError(f"expected a Git repository or worktree root: {root}")
    return root


def exists(path: Path) -> bool:
    return os.path.lexists(path)


def validate_destination(root: Path, relative: str, directory: bool) -> bool:
    """Reject symlinks, type conflicts and nested repositories before any writes."""
    parts = Path(relative).parts
    current = root
    for index, part in enumerate(parts):
        current = current / part
        if not exists(current):
            continue
        mode = current.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise BootstrapError(f"symlink destination is not supported: {current}")
        is_directory = index < len(parts) - 1 or directory
        if is_directory:
            if not stat.S_ISDIR(mode):
                raise BootstrapError(f"expected a directory: {current}")
            if exists(current / ".git"):
                raise BootstrapError(f"destination crosses another Git root: {current}")
        elif not stat.S_ISREG(mode):
            raise BootstrapError(f"expected a regular file: {current}")
    return exists(root / relative)


def source_bytes(source: Path) -> bytes:
    if not exists(source) or not stat.S_ISREG(source.lstat().st_mode):
        raise BootstrapError(f"required source is missing or not a regular file: {source}")
    return source.read_bytes()


@contextmanager
def parent_directory(root_fd: int, relative: str) -> Iterator[tuple[int, str]]:
    """Open each ancestor without following symlinks, including during apply."""
    descriptor = os.dup(root_fd)
    try:
        for component in Path(relative).parts[:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            try:
                os.stat(".git", dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise BootstrapError(f"destination crosses another Git root: {relative}")
        yield descriptor, Path(relative).name
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog=Path(sys.argv[1]).name,
        description="Create missing constellation scaffold files; dry-run by default.",
    )
    parser.add_argument("repo_path")
    parser.add_argument("--variant", choices=("quantos", "adjacent"), default="adjacent")
    parser.add_argument("--apply", action="store_true", help="Apply the displayed plan.")
    args = parser.parse_args(sys.argv[2:])
    root = repo_root(args.repo_path)

    directories = list(DIRECTORIES)
    sources = {
        "CLAUDE.md": HUB / "templates/CLAUDE.md.template",
        ".claude/registry/peers.yaml.snapshot": HUB / "registry/repos.yaml",
    }
    if args.variant == "quantos":
        directories += [".claude/tests", ".github", ".github/workflows"]
        sources.update({
            ".importlinter": HUB / "templates/importlinter.template",
            ".github/workflows/lint.yml": HUB / "templates/lint.yml.template",
        })

    # Preflight every destination and load every needed source before mutation.
    planned_directories = [
        name for name in directories if not validate_destination(root, name, directory=True)
    ]
    planned_files: dict[str, bytes] = {}
    for name, source in sources.items():
        if validate_destination(root, name, directory=False):
            continue
        content = source_bytes(source)
        if name.endswith("peers.yaml.snapshot"):
            content = (
                "# peers.yaml.snapshot — mirror of the constellation registry\n"
                "# Refresh with ~/GitHub/.claude/hooks/peer_sync.py.\n"
                "# The repository's own peers.yaml remains authoritative.\n\n"
            ).encode() + content
        planned_files[name] = content

    print(f"Repo: {root}\nVariant: {args.variant}")
    print(f"Planned actions ({len(planned_directories) + len(planned_files)}):")
    for name in planned_directories:
        print(f"  mkdir {name}")
    for name in planned_files:
        print(f"  create {name}")
    if not args.apply:
        print("Dry-run: no writes. Pass --apply to execute this plan.")
        return 0

    # The same plan drives apply. Exclusive creation never replaces existing work.
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in planned_directories:
            with parent_directory(root_fd, name) as (parent_fd, leaf):
                os.mkdir(leaf, dir_fd=parent_fd)
        for name, content in planned_files.items():
            with parent_directory(root_fd, name) as (parent_fd, leaf):
                fd = os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o644, dir_fd=parent_fd)
                with os.fdopen(fd, "wb") as output:
                    output.write(content)
    finally:
        os.close(root_fd)
    print("Applied scaffold plan." if planned_directories or planned_files else "No changes needed.")
    if planned_files:
        print("Copied templates are drafts: configure their repo-specific placeholders before use.")
    return 0


try:
    raise SystemExit(main())
except (BootstrapError, OSError, subprocess.TimeoutExpired) as error:
    print(f"Bootstrap refused or incomplete: {error}", file=sys.stderr)
    raise SystemExit(2)
PY
