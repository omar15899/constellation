#!/usr/bin/env python3
"""Install one owned, relocatable Claude plugin without changing user settings."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Iterator

sys.dont_write_bytecode = True
if __package__:
    from .build import BUNDLE_MANIFEST, INSTALL_RECEIPT, BundleError, verify_bundle
    from .install import InstallError, _read_object, _replace_bytes
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build import BUNDLE_MANIFEST, INSTALL_RECEIPT, BundleError, verify_bundle
    from install import InstallError, _read_object, _replace_bytes

PLUGIN_ID = "constellation@skills-dir"
OWNER = "constellation-claude-skills-dir"
LOCK_PATH = "constellation/.install.lock"
STAGING_NAME = ".constellation-next"
BACKUP_NAME = ".constellation-previous"


def _anchor(path: Path) -> Path:
    """Inspect the original lookup before resolving away linked ancestors."""
    path = Path(path).expanduser().absolute()
    if ".." in path.parts:
        raise InstallError("Managed paths cannot contain parent traversal")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise InstallError("Managed path contains a symbolic link")
        if not stat.S_ISDIR(metadata.st_mode):
            raise InstallError("Managed path contains a non-directory")
    return path


def _regular(path: Path) -> os.stat_result:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise InstallError("Managed resource must be a regular, singly linked file")
    return metadata


def _single_links(root: Path) -> None:
    for directory, subdirs, files in os.walk(root, followlinks=False):
        for name in subdirs:
            metadata = (Path(directory) / name).lstat()
            if not stat.S_ISDIR(metadata.st_mode):
                raise InstallError("Installation contains a linked or invalid directory")
        for name in files:
            _regular(Path(directory) / name)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt(bundle: Path, manifest: dict) -> dict:
    plugin = _read_object(bundle / ".claude-plugin/plugin.json")
    return {"schema": 1, "owner": OWNER, "plugin_id": PLUGIN_ID,
            "version": plugin["version"], "modules": manifest["modules"],
            "bundle_sha256": _digest(bundle / BUNDLE_MANIFEST)}


def verify_installation(plugin_root: Path) -> dict:
    """Verify ownership and exact bytes; the caller controls any install lock."""
    root = _anchor(plugin_root)
    if not root.is_dir():
        raise InstallError("Claude Constellation installation is missing")
    marker = root / INSTALL_RECEIPT
    try:
        metadata = _regular(marker)
        if stat.S_IMODE(metadata.st_mode) != 0o600:
            raise InstallError("Installation receipt permissions changed")
        receipt = _read_object(marker)
        manifest = verify_bundle(root, installation=True)
        _single_links(root)
        if type(receipt.get("schema")) is not int or receipt != _receipt(root, manifest):
            raise InstallError("Installation ownership receipt differs from the verified release")
        return {"manifest": manifest, "receipt": receipt}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, InstallError):
            raise
        raise InstallError("Claude installation is unowned, incomplete or modified") from exc


@contextmanager
def installation_lock(claude_home: Path, *, exclusive: bool, create: bool = False) -> Iterator[None]:
    """Coordinate payload replacement with readers without changing hook trust."""
    home = _anchor(claude_home)
    managed = _anchor(home / "constellation")
    path = managed / ".install.lock"
    if create:
        managed.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        before = _regular(path)
    elif not create:
        raise InstallError("Installation lock is missing; no package code was approved")
    else:
        before = None
    flags = os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT if create else 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        opened = os.fstat(descriptor)
        current = _regular(path)
        if (opened.st_nlink != 1 or not stat.S_ISREG(opened.st_mode)
                or stat.S_IMODE(opened.st_mode) != 0o600
                or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
                or (before is not None and (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino))):
            raise InstallError("Installation lock changed while opening")
        try:
            fcntl.flock(descriptor, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise InstallError("A Constellation installation or hook is running; retry after it finishes") from exc
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


@contextmanager
def verified_installation(plugin_root: Path) -> Iterator[dict]:
    """Keep an installed payload stable while a trusted caller uses its engine."""
    root = _anchor(plugin_root)
    if root.name == "constellation" and root.parent.name == "skills":
        with installation_lock(root.parent.parent, exclusive=False):
            yield verify_installation(root)["manifest"]
    else:
        # Explicit --plugin-dir supports a verified distribution before install.
        yield verify_bundle(root)


def _disabled(home: Path) -> None:
    settings = home / "settings.json"
    if not settings.exists() and not settings.is_symlink():
        return
    try:
        _regular(settings)
        if settings.stat().st_size > 1024 * 1024:
            raise InstallError("User settings are too large to validate safely")
        value = _read_object(settings)
        enabled = value.get("enabledPlugins", {})
        if not isinstance(enabled, dict):
            raise InstallError("User plugin enablement settings are invalid")
        if enabled.get(PLUGIN_ID) is False:
            raise InstallError("Constellation is explicitly disabled; preserve that decision in Claude")
    except (OSError, ValueError) as exc:
        if isinstance(exc, InstallError):
            raise
        raise InstallError("Cannot safely inspect Claude plugin enablement") from exc


def _preflight(home: Path) -> tuple[Path, dict | None]:
    home = _anchor(home)
    _disabled(home)
    skills = _anchor(home / "skills")
    target = _anchor(skills / "constellation")
    for name in (STAGING_NAME, BACKUP_NAME):
        pending = skills / name
        if pending.exists() or pending.is_symlink():
            raise InstallError("A previous installation has pending staging or backup files; "
                               "preserve those copies and inspect them before retrying")
    current = verify_installation(target) if target.exists() else None
    return target, current


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sync_tree(root: Path) -> None:
    for directory, _, files in os.walk(root, topdown=False):
        for name in files:
            descriptor = os.open(Path(directory) / name, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        _sync_directory(Path(directory))


def _result(status: str, target: Path, receipt: dict) -> dict:
    return {"status": status, "plugin": str(target), "plugin_id": PLUGIN_ID,
            "version": receipt["version"], "modules": receipt["modules"],
            "bundle_sha256": receipt["bundle_sha256"], "integrity": "verified",
            "activation": "requires-new-session", "live_execution": "not_verified"}


def install_bundle(bundle: Path, claude_home: Path, *, check: bool = False) -> dict:
    """Deploy verified code only, refusing unowned payloads and preserving settings."""
    source = _anchor(bundle)
    manifest = verify_bundle(source)
    desired = _receipt(source, manifest)
    home = _anchor(claude_home)
    target, current = _preflight(home)
    administrative = home / "constellation"
    if any(source == managed or managed in source.parents or source in managed.parents
           for managed in (target, administrative)):
        raise InstallError("Bundle and installation directory must not overlap")
    if check:
        return _result("checked", target, desired)
    with installation_lock(home, exclusive=True, create=True):
        target, current = _preflight(home)
        if current is not None and current["receipt"] == desired:
            return _result("unchanged", target, desired)
        target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        stage, backup = target.parent / STAGING_NAME, target.parent / BACKUP_NAME
        replaced = False
        staged = False
        claimed = False
        promoted = False
        try:
            # Stage beside the destination so every rename stays on one filesystem.
            stage.mkdir(mode=0o755)
            staged = True
            shutil.copytree(source, stage, symlinks=True, dirs_exist_ok=True)
            marker = (json.dumps(desired, sort_keys=True, indent=2) + "\n").encode()
            _replace_bytes(stage / INSTALL_RECEIPT, marker, 0o600)
            verify_installation(stage)
            _sync_tree(stage)
            if current is not None:
                # Detect edits made after preflight before moving the owned copy.
                if verify_installation(target)["receipt"] != current["receipt"]:
                    raise InstallError("Installed release changed while staging")
                target.rename(backup)
                replaced = True
                _sync_directory(target.parent)
            # Refuse a destination that appeared during staging. Claiming an
            # empty directory also prevents rename from replacing foreign data.
            target.mkdir(mode=0o755)
            claimed = True
            stage.rename(target)
            staged = False
            claimed = False
            promoted = True
            _sync_directory(target.parent)
            installed = verify_installation(target)
            if installed["receipt"] != desired:
                raise InstallError("Installed release differs from staged release")
        except Exception as failure:
            try:
                if replaced:
                    if promoted:
                        verify_installation(target)
                        shutil.rmtree(target)
                    elif claimed:
                        target.rmdir()
                    backup.rename(target)
                    _sync_directory(target.parent)
                elif promoted:
                    verify_installation(target)
                    shutil.rmtree(target)
                elif claimed:
                    target.rmdir()
                if staged and stage.exists():
                    shutil.rmtree(stage)
            except (OSError, ValueError) as recovery:
                raise InstallError("Installation failed; owned staging or previous copies were retained "
                                   "and need inspection before retrying") from recovery
            raise InstallError("Installation failed; previous owned payload was restored") from failure
        if replaced:
            # A concurrently edited backup is unique user work, not disposable cache.
            if verify_installation(backup)["receipt"] != current["receipt"]:
                raise InstallError("Updated release is verified; preserve the modified previous copy")
            shutil.rmtree(backup)
            _sync_directory(target.parent)
        return _result("updated" if current else "installed", target, desired)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    install = subparsers.add_parser("install", help="Install one verified portable Claude plugin")
    install.add_argument("--bundle", required=True, type=Path)
    install.add_argument("--claude-home", type=Path, default=Path(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")))
    install.add_argument("--check", "--dry-run", action="store_true")
    verify = subparsers.add_parser("verify", aliases=["doctor"], help="Verify the owned installed payload")
    verify.add_argument("--claude-home", type=Path, default=Path(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")))
    arguments = parser.parse_args(argv)
    try:
        if arguments.operation == "install":
            result = install_bundle(arguments.bundle, arguments.claude_home, check=arguments.check)
        else:
            home = _anchor(arguments.claude_home)
            target, _ = _preflight(home)
            with verified_installation(target):
                receipt = verify_installation(target)["receipt"]
            result = _result("verified", target, receipt)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (InstallError, BundleError, OSError, ValueError) as exc:
        parser.exit(1, f"Claude installation rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
