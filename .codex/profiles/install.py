#!/usr/bin/env python3
"""Install the curated Codex and Claude home profiles on macOS or Linux.

The default invocation only reports changes. ``--apply`` writes the allowlisted
instructions, guides and documentation helper; ``--backup-existing`` additionally
permits replacing unowned or locally edited copies after preserving their bytes.
Client settings, accounts, plugins, conversations and runtime state are outside
this installer's ownership.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Callable, Iterator

sys.dont_write_bytecode = True

OWNER = "constellation-home-profiles"
RECEIPT = ".codex/docs/maintenance/profiles.json"
MAPPING = {
    ".codex/AGENTS.md": "AGENTS.md",
    ".claude/CLAUDE.md": ".codex/profiles/claude/CLAUDE.md",
    ".claude/README.md": ".codex/profiles/claude/README.md",
    ".claude/docs/README.md": ".codex/profiles/claude/docs.md",
    ".codex/docs/README.md": ".codex/profiles/codex/docs.md",
    ".claude/tools/official_docs.py": ".codex/profiles/official_docs.py",
    ".codex/tools/official_docs.py": ".codex/profiles/official_docs.py",
}
MAX_BYTES = 8 * 1024 * 1024


class ProfileError(Exception):
    """An unsafe path, conflicting edit or incomplete installation was found."""


@dataclass(frozen=True)
class FileState:
    """A regular file's bytes, permissions and identity at a particular instant."""

    data: bytes
    mode: int
    identity: tuple[int, int, int, int]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass(frozen=True)
class DesiredFile:
    """An allowlisted rendered destination and its original source digest."""

    source: str
    data: bytes
    source_sha256: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


def absolute(path: Path) -> Path:
    """Expand a path without hiding traversal or resolving symbolic links."""
    expanded = path.expanduser()
    if ".." in expanded.parts:
        raise ProfileError("Parent traversal is not allowed in managed paths")
    return expanded.absolute()


def check_directory(path: Path, *, create: bool = False) -> None:
    """Reject symbolic links and non-directories in every existing component."""
    for part in reversed((path, *path.parents)):
        try:
            info = part.lstat()
        except FileNotFoundError:
            if create:
                part.mkdir(mode=0o700)
            continue
        if not stat.S_ISDIR(info.st_mode):
            raise ProfileError("Managed directory contains a symbolic link or non-directory")


def read_file(path: Path) -> FileState | None:
    """Read only regular, singly linked files, without following a leaf link."""
    check_directory(path.parent)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ProfileError("Managed file is not regular and singly linked")
        if info.st_size > MAX_BYTES:
            raise ProfileError("Managed file exceeds the profile size limit")
        data = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
    if (len(data) > MAX_BYTES or (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
        raise ProfileError("Managed file changed while being read")
    return FileState(data, stat.S_IMODE(info.st_mode),
                     (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns))


def _same_state(expected: FileState | None, current: FileState | None) -> bool:
    return expected == current


def _source_files(source_root: Path) -> dict[str, DesiredFile]:
    check_directory(source_root)
    result = {}
    for destination, source in MAPPING.items():
        state = read_file(source_root / source)
        if state is None:
            raise ProfileError(f"Required profile source is missing: {source}")
        data = state.data
        if source.endswith(".md"):
            data = data.decode("utf-8").replace("{{SOURCE_ROOT}}", str(source_root)).encode("utf-8")
        result[destination] = DesiredFile(source, data, state.sha256)
    return result


def _read_receipt(state: FileState | None) -> dict:
    if state is None:
        return {}
    if state.mode != 0o600:
        raise ProfileError("Profile receipt permissions changed; expected private mode 0600")
    try:
        receipt = json.loads(state.data)
        if (set(receipt) != {"schema", "owner", "source_root", "files"}
                or type(receipt["schema"]) is not int or receipt["schema"] != 1
                or receipt["owner"] != OWNER or not isinstance(receipt["source_root"], str)
                or not isinstance(receipt["files"], dict) or set(receipt["files"]) != set(MAPPING)):
            raise ValueError
        for name, record in receipt["files"].items():
            if (set(record) != {"source", "source_sha256", "installed_sha256", "mode"}
                    or record["source"] != MAPPING[name] or type(record["mode"]) is not int
                    or record["mode"] != 0o644
                    or any(not isinstance(record[key], str) or not re.fullmatch(r"[a-f0-9]{64}", record[key])
                           for key in ("source_sha256", "installed_sha256"))):
                raise ValueError
        return receipt
    except (TypeError, ValueError, KeyError) as exc:
        raise ProfileError("Profile receipt is invalid; preserve it and inspect before retrying") from exc


def _desired_receipt(source_root: Path, desired: dict[str, DesiredFile]) -> bytes:
    receipt = {"schema": 1, "owner": OWNER, "source_root": str(source_root),
               "files": {name: {"source": entry.source, "source_sha256": entry.source_sha256,
                                "installed_sha256": entry.sha256, "mode": 0o644}
                         for name, entry in desired.items()}}
    return (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _preflight(home: Path, desired: dict[str, DesiredFile], *, backup_existing: bool) -> tuple[dict, dict]:
    check_directory(home)
    receipt_state = read_file(home / RECEIPT)
    receipt = _read_receipt(receipt_state)
    states = {name: read_file(home / name) for name in desired}
    states[RECEIPT] = receipt_state
    actions = {}
    conflicts = []
    for name, entry in desired.items():
        current = states[name]
        if current is not None and current.data == entry.data and current.mode == 0o644:
            actions[name] = "unchanged"
            continue
        owned = (current is not None and name in receipt.get("files", {})
                 and current.sha256 == receipt["files"][name]["installed_sha256"]
                 and current.mode == receipt["files"][name]["mode"])
        if current is not None and not owned and not backup_existing:
            conflicts.append(name)
        actions[name] = "replace" if current is not None else "create"
    if conflicts:
        raise ProfileError("Unowned or locally edited profile files require --backup-existing: "
                           + ", ".join(conflicts))
    return states, actions


def _stage_file(path: Path, data: bytes, mode: int) -> tuple[Path, FileState]:
    """Write a same-directory staging file without touching the destination."""
    check_directory(path.parent, create=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".profile-next-", dir=path.parent)
    pending = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            info = os.fstat(stream.fileno())
            staged = FileState(data, mode, (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns))
        return pending, staged
    except BaseException:
        if pending.exists():
            pending.unlink()
        raise


def _restore_captured(captured: Path, destination: Path) -> bool:
    """Restore a copy only into an absent name; retain the captured inode.

    A writer may still hold the captured original open. Keeping that inode in
    recovery also preserves writes that happen after this copy is restored.
    """
    original = read_file(captured)
    if original is None:
        raise ProfileError(f"Captured original is missing; inspect recovery: {captured}")
    pending, _ = _stage_file(destination, original.data, original.mode)
    try:
        check_directory(destination.parent)
        try:
            os.link(pending, destination, follow_symlinks=False)
        except FileExistsError:
            return False
        return True
    finally:
        pending.unlink()


def _capture_file(path: Path, expected: FileState, recovery: Path) -> Path:
    """Move the actual destination into unique, private, retained recovery.

    POSIX has no compare-and-swap replacement for arbitrary writers. Capturing
    before checking preserves the file actually displaced by the rename instead
    of trusting a stat taken before staging. Recovery must share its filesystem;
    an unsupported cross-device rename fails without displacing the destination.
    """
    check_directory(path.parent)
    check_directory(recovery, create=True)
    container = Path(tempfile.mkdtemp(prefix=path.name + "-", dir=recovery))
    captured = container / "original"
    os.rename(path, captured)
    try:
        current = read_file(captured)
        if not _same_state(expected, current):
            _restore_captured(captured, path)
            raise ProfileError(f"Destination changed during staging; captured bytes preserved at: {captured}")
    except BaseException:
        # A changed file, symlink or other unexpected object remains captured.
        # Never overwrite a new destination that another writer has created.
        raise
    return captured


def replace_file(path: Path, data: bytes, mode: int, *, expected: FileState | None = None,
                 recovery: Path | None = None,
                 on_replace: Callable[[FileState], None] | None = None) -> FileState:
    """Capture an existing file, then publish staged bytes without clobbering.

    Existing destinations require their observed state and a recovery directory.
    The captured original is retained even on success, because an open descriptor
    can still write to its inode. Publication uses an exclusive hard link: a new
    destination created after capture is preserved rather than replaced.
    """
    pending, staged = _stage_file(path, data, mode)
    captured = None
    try:
        if expected is not None:
            if recovery is None:
                raise ProfileError("Replacing an existing profile requires retained recovery")
            captured = _capture_file(path, expected, recovery)
        check_directory(path.parent)
        try:
            os.link(pending, path, follow_symlinks=False)
        except BaseException as failure:
            if captured is not None:
                _restore_captured(captured, path)
                raise ProfileError(f"Promotion failed; captured original preserved at: {captured}") from failure
            raise
        if on_replace is not None:
            on_replace(staged)
    finally:
        pending.unlink()
    result = read_file(path)
    if result is None or result.data != data or result.mode != mode:
        raise ProfileError("Installed profile file differs from the staged bytes")
    return result


@contextmanager
def _lock(home: Path) -> Iterator[None]:
    parent = home / Path(RECEIPT).parent
    check_directory(parent, create=True)
    path = parent / ".profiles.lock"
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(descriptor, "r+b") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ProfileError("Profile installation lock is not a regular singly linked file")
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def install(source_root: Path, home: Path, *, apply: bool = False, backup_existing: bool = False) -> dict:
    """Plan or install only the seven curated profile destinations.

    All inputs and destinations are checked before any write. Replacements retain
    originals under ``.codex/backups/profiles``, including the actual inode moved
    out of the destination. Promotion never replaces a newly created name. Failed
    attempts restore copies only into absent names; concurrent edits stay at their
    destination or in retained recovery. This is preservation, not a filesystem
    compare-and-swap guarantee against arbitrary writers.

    Args:
        source_root: Repository containing the checked-in profile sources.
        home: Home containing the independent native ``.codex`` and ``.claude``.
        apply: Write the planned changes; false is a completely read-only preview.
        backup_existing: Explicitly adopt conflicting files after preserving them.

    Returns:
        JSON-compatible actions, receipt location and optional recovery directory.

    Raises:
        ProfileError: Paths, ownership, observed bytes or rollback are unsafe.
        OSError: An installation operation fails; previous files are restored
            when their current identity still belongs to this attempt.
    """
    source_root, home = absolute(source_root), absolute(home)
    desired = _source_files(source_root)
    states, actions = _preflight(home, desired, backup_existing=backup_existing)
    result = {"status": "planned", "home": str(home), "actions": actions,
              "receipt": str(home / RECEIPT), "backup": None}
    if not apply:
        return result
    with _lock(home):
        # The read-only preview may precede a concurrent installation.
        states, actions = _preflight(home, desired, backup_existing=backup_existing)
        result["actions"] = actions
        receipt_data = _desired_receipt(source_root, desired)
        receipt_changed = states[RECEIPT] is None or states[RECEIPT].data != receipt_data
        writes = [(name, desired[name].data, 0o644) for name in desired if actions[name] != "unchanged"]
        if receipt_changed:
            writes.append((RECEIPT, receipt_data, 0o600))
        if not writes:
            result["status"] = "unchanged"
            return result
        backup = None

        def recovery_for(name: str) -> Path:
            nonlocal backup
            if backup is None:
                parent = home / ".codex/backups/profiles"
                check_directory(parent, create=True)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
                backup = Path(tempfile.mkdtemp(prefix=stamp, dir=parent))
                result["backup"] = str(backup)
            return backup / "captured" / Path(name).parent

        originals = {name: states[name] for name, _, _ in writes if states[name] is not None}
        if originals:
            recovery_for(next(iter(originals)))
            assert backup is not None
            for name, original in originals.items():
                assert original is not None
                replace_file(backup / name, original.data, original.mode)
        written: dict[str, FileState] = {}
        try:
            for name, data, mode in writes:
                if not _same_state(states[name], read_file(home / name)):
                    raise ProfileError("Profile destination changed after preflight; preserve recovery copies")
                replace_file(home / name, data, mode, expected=states[name],
                             recovery=recovery_for(name) if states[name] is not None else None,
                             on_replace=lambda state, key=name: written.__setitem__(key, state))
        except BaseException as failure:
            preserved = []
            for name, installed in reversed(tuple(written.items())):
                path = home / name
                try:
                    if not _same_state(installed, read_file(path)):
                        preserved.append(name)
                        continue
                    original = states[name]
                    if original is None:
                        _capture_file(path, installed, recovery_for(name))
                    else:
                        replace_file(path, original.data, original.mode, expected=installed,
                                     recovery=recovery_for(name))
                except (OSError, ProfileError):
                    preserved.append(name)
            if preserved:
                raise ProfileError("Installation failed with concurrent or unrecoverable changes; "
                                   "preserve recovery copies and inspect: " + ", ".join(preserved)) from failure
            raise
        result["status"] = "installed"
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--source-root", type=Path, default=Path(__file__).absolute().parents[2])
    parser.add_argument("--apply", action="store_true", help="Write the checked profile destinations")
    parser.add_argument("--backup-existing", action="store_true", help="Preserve and adopt unowned or edited profile files")
    args = parser.parse_args()
    try:
        result = install(args.source_root, args.home, apply=args.apply, backup_existing=args.backup_existing)
    except (OSError, ValueError, ProfileError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
