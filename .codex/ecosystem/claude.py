#!/usr/bin/env python3
"""Install one owned, relocatable Claude plugin without changing user settings."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from typing import Iterator

sys.dont_write_bytecode = True
if __package__:
    from .build import BUNDLE_MANIFEST, INSTALL_RECEIPT, BundleError, verify_bundle, verify_owned_bundle
    from .install import InstallError, _read_object, _replace_bytes
    from . import platform_support as platform
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build import BUNDLE_MANIFEST, INSTALL_RECEIPT, BundleError, verify_bundle, verify_owned_bundle
    from install import InstallError, _read_object, _replace_bytes
    import platform_support as platform

PLUGIN_ID = "constellation@skills-dir"
OWNER = "constellation-claude-skills-dir"
LOCK_PATH = "constellation/.install.lock"
STAGING_NAME = ".constellation-next"
BACKUP_NAME = ".constellation-previous"


def _anchor(path: Path) -> Path:
    """Inspect the original lookup before resolving away linked ancestors."""
    path = Path(path).expanduser()
    if platform.IS_WINDOWS:
        try:
            path = platform.validate_lookup(path)
        except platform.PlatformError as exc:
            raise InstallError("Managed Windows path contains a symbolic link, reparse point or unsafe component") from exc
    path = path.absolute()
    if ".." in path.parts:
        raise InstallError("Managed paths cannot contain parent traversal")
    if platform.IS_WINDOWS:
        if not path.drive or path.drive.startswith("\\\\"):
            raise InstallError("Managed Windows paths require a local absolute drive")
        try:
            for part in path.parts[1:]:
                platform.validate_windows_relative(part)
        except platform.PlatformError as exc:
            raise InstallError("Managed Windows path contains an unsafe component") from exc
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if platform.is_reparse(current):
            raise InstallError("Managed path contains a symbolic link or reparse point")
        if not stat.S_ISDIR(metadata.st_mode):
            raise InstallError("Managed path contains a non-directory")
    return path


def _regular(path: Path) -> os.stat_result:
    metadata = path.lstat()
    if platform.is_reparse(path) or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise InstallError("Managed resource must be a regular, singly linked file")
    return metadata


def _single_links(root: Path) -> None:
    for directory, subdirs, files in os.walk(root, followlinks=False):
        for name in subdirs:
            metadata = (Path(directory) / name).lstat()
            if platform.is_reparse(Path(directory) / name) or not stat.S_ISDIR(metadata.st_mode):
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
        try:
            if platform.logical_mode(marker, expected=0o600) != 0o600:
                raise InstallError("Installation receipt permissions changed")
            platform.verify_access(marker, private=True)
        except platform.PlatformError as exc:
            raise InstallError("Installation receipt permissions changed") from exc
        receipt = _read_object(marker)
        _single_links(root)
        manifest = verify_owned_bundle(root, installation=True)
        if type(receipt.get("schema")) is not int or receipt != _receipt(root, manifest):
            raise InstallError("Installation ownership receipt differs from the verified release")
        return {"manifest": manifest, "receipt": receipt}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, InstallError):
            raise
        raise InstallError("Claude installation is unowned, incomplete or modified") from exc


def _verify_managed_boundaries(home: Path) -> None:
    """Reject mutable known parents without changing independently owned ACLs."""
    administrative = _anchor(home / "constellation")
    boundaries = (home, _anchor(home / "skills"),
                  _anchor(home / "skills/constellation"), administrative)
    for boundary in boundaries:
        if boundary.exists():
            try:
                platform.verify_access(boundary, private=boundary == administrative)
            except platform.PlatformError as exc:
                raise InstallError("Claude managed directory permissions are unsafe; preserve its contents") from exc


@contextmanager
def installation_lock(claude_home: Path, *, exclusive: bool, create: bool = False) -> Iterator[None]:
    """Hold a real reader/writer lock across verification and payload use."""
    home = _anchor(claude_home)
    _verify_managed_boundaries(home)
    managed = _anchor(home / "constellation")
    path = managed / ".install.lock"
    if create:
        platform.secure_mkdir(managed, mode=0o700, parents=True, exist_ok=True)
    if path.exists() or platform.is_reparse(path):
        before = _regular(path)
        try:
            if platform.logical_mode(path, expected=0o600) != 0o600:
                raise InstallError("Installation lock changed while opening")
            platform.verify_access(path, private=True)
        except platform.PlatformError as exc:
            raise InstallError("Installation lock changed while opening") from exc
    elif not create:
        raise InstallError("Installation lock is missing; no package code was approved")
    else:
        before = None
    flags = os.O_RDWR | (os.O_CREAT if create else 0)
    try:
        descriptor = platform.open_regular(path, flags, 0o600, private=True)
    except platform.PlatformError as exc:
        raise InstallError("Installation lock changed while opening") from exc
    try:
        opened = os.fstat(descriptor)
        current = _regular(path)
        if (opened.st_nlink != 1 or not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
                or (before is not None and (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino))):
            raise InstallError("Installation lock changed while opening")
        with ExitStack() as acquired:
            try:
                acquired.enter_context(platform.file_lock(descriptor, exclusive=exclusive, blocking=False))
            except BlockingIOError as exc:
                raise InstallError("A Constellation installation or hook is running; retry after it finishes") from exc
            yield
    finally:
        os.close(descriptor)


def _is_managed_root(root: Path) -> bool:
    """Keep Windows case variants inside the installed receipt/lock boundary."""
    name, parent = root.name, root.parent.name
    if platform.IS_WINDOWS:
        name, parent = name.casefold(), parent.casefold()
    return name == "constellation" and parent == "skills"


@contextmanager
def verified_installation(plugin_root: Path) -> Iterator[dict]:
    """Keep an installed payload stable while a trusted caller uses its engine."""
    root = _anchor(plugin_root)
    if _is_managed_root(root):
        with installation_lock(root.parent.parent, exclusive=False):
            yield verify_installation(root)["manifest"]
    else:
        # Explicit --plugin-dir supports a verified distribution before install.
        yield verify_bundle(root)


def _disabled(home: Path) -> None:
    settings = home / "settings.json"
    if not settings.exists() and not platform.is_reparse(settings):
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
    skills = _anchor(home / "skills")
    target = _anchor(skills / "constellation")
    _verify_managed_boundaries(home)
    _disabled(home)
    for name in (STAGING_NAME, BACKUP_NAME):
        pending = skills / name
        if pending.exists() or platform.is_reparse(pending):
            raise InstallError("A previous installation has pending staging or backup files; "
                               "preserve those copies and inspect them before retrying")
    current = verify_installation(target) if target.exists() else None
    return target, current


def _require_owned_payload(path: Path, identity: tuple[int, int] | None,
                           receipt: dict) -> dict:
    """Verify the exact directory created by this attempt before removing it."""
    metadata = path.lstat()
    if (identity is None or platform.is_reparse(path) or not stat.S_ISDIR(metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino) != identity):
        raise InstallError("Staged payload identity changed; preserve this directory for inspection")
    installed = verify_installation(path)
    if installed["receipt"] != receipt:
        raise InstallError("Staged payload ownership changed; preserve this directory for inspection")
    return installed


def _sync_directory(path: Path) -> bool:
    """Flush directory metadata when the operating system supports it."""
    return platform.sync_directory(path)


def _sync_tree(root: Path) -> bool:
    supported = True
    for directory, _, files in os.walk(root, topdown=False):
        for name in files:
            flags = os.O_RDWR if platform.IS_WINDOWS else os.O_RDONLY
            descriptor = platform.open_regular(Path(directory) / name, flags, private=False)
            try:
                platform.sync_file(descriptor)
            finally:
                os.close(descriptor)
        supported = _sync_directory(Path(directory)) and supported
    return supported


def _runtime_preflight(bundle: Path) -> None:
    """Require a real native Python executable for the Windows exec-form hook.

    This runs before any destination creation. It neither selects accounts nor
    modifies PATH, settings, hook trust or the interpreter installation.
    """
    data = _read_object(bundle / "ecosystem/claude-hooks.json")
    commands = {hook.get("command") for groups in data.get("hooks", {}).values()
                for group in groups for hook in group.get("hooks", [])}
    if not platform.IS_WINDOWS:
        if commands != {"python3"}:
            raise InstallError("This Windows Claude package must be installed on native Windows")
        return
    if commands != {"python"}:
        raise InstallError("Native Windows requires the windows-claude package target")
    executable = shutil.which("python")
    if (not executable or Path(executable).suffix.lower() != ".exe"
            or platform.is_reparse(Path(executable))):
        raise InstallError("Native Windows needs a real Python 3.11+ executable named python on PATH")
    code = "import json,os,sys;print(json.dumps([os.name,list(sys.version_info[:2])]))"
    try:
        result = subprocess.run([executable, "-I", "-B", "-c", code],
                                capture_output=True, timeout=10, check=False)
        identity = json.loads(result.stdout.decode("ascii"))
    except (OSError, subprocess.TimeoutExpired, UnicodeError, ValueError) as exc:
        raise InstallError("Cannot verify Claude's native Windows Python interpreter") from exc
    if (result.returncode or not isinstance(identity, list) or len(identity) != 2
            or identity[0] != "nt" or not isinstance(identity[1], list)
            or len(identity[1]) != 2 or not all(type(v) is int for v in identity[1])
            or tuple(identity[1]) < (3, 11)):
        raise InstallError("Claude's python command must select native Windows Python 3.11 or newer")


def _result(status: str, target: Path, receipt: dict, *,
            directory_sync: bool | None = None) -> dict:
    return {"status": status, "plugin": str(target), "plugin_id": PLUGIN_ID,
            "version": receipt["version"], "modules": receipt["modules"],
            "bundle_sha256": receipt["bundle_sha256"], "integrity": "verified",
            "activation": "requires-new-session", "live_execution": "not_verified",
            "directory_sync": ("supported" if directory_sync else "unsupported")
                if directory_sync is not None else "not_measured"}


def install_bundle(bundle: Path, claude_home: Path, *, check: bool = False) -> dict:
    """Deploy verified code only, refusing unowned payloads and preserving settings."""
    source = _anchor(bundle)
    manifest = verify_bundle(source)
    _runtime_preflight(source)
    desired = _receipt(source, manifest)
    home = _anchor(claude_home)
    target = _anchor(home / "skills/constellation")
    administrative = _anchor(home / "constellation")
    if any(source == managed or managed in source.parents or source in managed.parents
           for managed in (target, administrative)):
        raise InstallError("Bundle and installation directory must not overlap")
    target, current = _preflight(home)
    if check:
        return _result("checked", target, desired)
    with installation_lock(home, exclusive=True, create=True):
        target, current = _preflight(home)
        if current is not None and current["receipt"] == desired:
            return _result("unchanged", target, desired)
        platform.secure_mkdir(target.parent, mode=0o755, parents=True, exist_ok=True)
        stage, backup = target.parent / STAGING_NAME, target.parent / BACKUP_NAME
        replaced = False
        staged = False
        staged_identity: tuple[int, int] | None = None
        promoted = False
        directory_sync = True
        try:
            # Stage beside the destination so every rename stays on one filesystem.
            platform.secure_mkdir(stage, mode=0o755)
            staged = True
            created = stage.lstat()
            staged_identity = (created.st_dev, created.st_ino)
            shutil.copytree(source, stage, symlinks=True, dirs_exist_ok=True)
            marker = (json.dumps(desired, sort_keys=True, indent=2) + "\n").encode()
            _replace_bytes(stage / INSTALL_RECEIPT, marker, 0o600)
            verify_installation(stage)
            directory_sync = bool(_sync_tree(stage))
            if current is not None:
                # Detect edits made after preflight before moving the owned copy.
                if verify_installation(target)["receipt"] != current["receipt"]:
                    raise InstallError("Installed release changed while staging")
                platform.promote_directory(target, backup)
                replaced = True
                directory_sync = _sync_directory(target.parent) and directory_sync
            # Promotion is exclusive on both platforms. Windows itself rejects
            # an existing destination; POSIX uses an empty-directory claim.
            platform.promote_directory(stage, target)
            staged = False
            promoted = True
            directory_sync = _sync_directory(target.parent) and directory_sync
            installed = _require_owned_payload(target, staged_identity, desired)
            if installed["receipt"] != desired:
                raise InstallError("Installed release differs from staged release")
        except Exception as failure:
            try:
                if replaced:
                    if promoted:
                        _require_owned_payload(target, staged_identity, desired)
                        shutil.rmtree(target)
                    platform.promote_directory(backup, target)
                    _sync_directory(target.parent)
                elif promoted:
                    _require_owned_payload(target, staged_identity, desired)
                    shutil.rmtree(target)
                if staged and (stage.exists() or platform.is_reparse(stage)):
                    # Partial or externally changed copies are ambiguous user
                    # work. Retain them instead of deleting by pathname alone.
                    _require_owned_payload(stage, staged_identity, desired)
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
            directory_sync = _sync_directory(target.parent) and directory_sync
        return _result("updated" if current else "installed", target, desired,
                       directory_sync=directory_sync)


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
