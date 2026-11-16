"""Validate the enrolled Notes/Reminders automation's exact local commit.

This gate preserves native ``git commit --only`` and its private recovery
receipt. It grants no review record or remote publication authorization.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any

from .git import GitError, _git_dir, _run, _text


PATHS = (
    '00_Inbox/Apple_Notes_Monitor/notes_history.json',
    '02_Tasks_and_Execution/Monitor/reminders_history.json',
    '17_Dashboards/Tasks/notes_reminders_monitor.md',
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_size,
            metadata.st_mtime_ns, metadata.st_ctime_ns)


def _regular(path: Path) -> os.stat_result:
    """Require a regular file reached without any symlink component."""
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise GitError('Monitor state cannot traverse symlinks')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise GitError('Monitor state must contain regular files')
    return info


def _read_receipt(path: Path) -> tuple[bytes, tuple[int, ...]]:
    """Read a bounded private receipt without following replaced files."""
    metadata = _regular(path)
    if metadata.st_mode & 0o077 or metadata.st_size > 1024 * 1024:
        raise GitError('Monitor receipt must be private and bounded')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        if _identity(os.fstat(stream.fileno())) != _identity(metadata):
            raise GitError('Monitor receipt changed while opening')
        data = stream.read(1024 * 1024 + 1)
        if (len(data) > 1024 * 1024 or _identity(os.fstat(stream.fileno())) != _identity(metadata)
                or _identity(_regular(path)) != _identity(metadata)):
            raise GitError('Monitor receipt changed while reading')
    return data, _identity(metadata)


def _enrolled(root: Path, git_dir: Path, registry: Path | None) -> None:
    """Select the enrolled vault; a marker cannot enable an arbitrary repo."""
    registry = registry or Path(__file__).resolve().parents[1] / 'profiles/projects.json'
    matches = [project for project in json.loads(registry.read_text())['projects']
               if project.get('id') == 'omaros' and project.get('management') == 'native'
               and Path(project['root']).expanduser().resolve() == root]
    if len(matches) != 1:
        raise GitError('Monitor snapshot requires the enrolled OmarOS owner')
    expected = matches[0].get('filesystem_identity', {})
    for name, path in (('owner', root), ('git_dir', git_dir)):
        info = path.stat()
        if expected.get(name) != [info.st_dev, info.st_ino]:
            raise GitError('Monitor owner identity differs from enrollment')


def _owned_signature(root: Path, parent: str) -> str:
    rows = _run(root, 'ls-tree', '-z', parent, '--', *PATHS).split(b'\0')
    signature = b''
    names: set[str] = set()
    for row in filter(None, rows):
        metadata, name = row.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        decoded = name.decode()
        if mode != b'100644' or kind != b'blob' or decoded not in PATHS:
            raise GitError('Monitor baseline must contain regular tracked outputs')
        names.add(decoded)
        signature += b'H ' + mode + b' ' + oid + b' 0\t' + name + b'\0'
    if names != set(PATHS):
        raise GitError('Monitor baseline must contain all three outputs')
    return _sha(signature)


def _snapshot_hashes(root: Path, index: Path) -> dict[str, str]:
    """Hash only the three exact staged blobs, never unrelated staged contents."""
    result = {}
    rows = _run(root, 'ls-files', '--stage', '-z', '--', *PATHS, index=index).split(b'\0')
    for row in filter(None, rows):
        metadata, name = row.split(b'\t', 1)
        mode, oid, stage = metadata.split()
        decoded = name.decode()
        if mode != b'100644' or stage != b'0' or decoded not in PATHS or decoded in result:
            raise GitError('Monitor candidate contains ambiguous or nonregular output')
        result[decoded] = _sha(_run(root, 'cat-file', 'blob', oid.decode()))
    if set(result) != set(PATHS):
        raise GitError('Monitor candidate must contain all three output files')
    return result


def _write_proof(path: Path, receipt: dict[str, Any], original: tuple[bytes, tuple[int, ...]]) -> None:
    """Write only the guard receipt, preserving unrelated receipt fields."""
    descriptor, temporary = tempfile.mkstemp(prefix='.monitor-proof-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode())
            stream.flush()
            os.fsync(stream.fileno())
        if _read_receipt(path) != original:
            raise GitError('Monitor receipt changed during validation')
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def allow_snapshot(root: str | Path, *, registry: Path | None = None) -> bool:
    """Allow an enrolled automation's exact native partial commit, or fail closed.

    Args:
        root: The Git owner invoking its pre-commit hook.
        registry: Explicit fixture registry for isolated tests; normal hooks use
            the canonical registry. No environment override is accepted.

    Returns:
        False for an absent marker; True after exact receipt/index validation.

    Raises:
        GitError: A marked operation has absent, stale, or unsafe evidence.
    """
    marker = os.environ.get('OMAROS_MONITOR_SNAPSHOT')
    if marker is None:
        return False
    if re.fullmatch(r'[0-9a-f]{64}', marker) is None:
        raise GitError('Invalid monitor snapshot marker')
    try:
        root = Path(root).resolve()
        git_dir = _git_dir(root)
        _enrolled(root, git_dir, registry)
        if Path(_text(root, 'rev-parse', '--show-toplevel')).resolve() != root:
            raise GitError('Monitor root must be the exact Git owner')
        storage = git_dir / 'notes-reminders-monitor'
        receipt_path = storage / 'commit_attempt.json'
        if storage.is_symlink() or not storage.is_dir() or storage.stat().st_mode & 0o077:
            raise GitError('Monitor receipt requires a private directory')
        original = _read_receipt(receipt_path)
        receipt = json.loads(original[0])
        if (not isinstance(receipt, dict) or type(receipt.get('schema_version')) is not int
                or receipt['schema_version'] != 1 or receipt.get('snapshot_id') != marker
                or ('guarded_snapshot' in receipt and receipt['guarded_snapshot'] != marker)):
            raise GitError('Invalid monitor snapshot receipt')
        expected = receipt.get('expected')
        if (not isinstance(expected, dict) or set(expected) != set(PATHS)
                or any(not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{64}', value) is None
                       for value in expected.values())
                or _sha(json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()) != marker):
            raise GitError('Monitor snapshot digest or scope differs from receipt')
        parent, branch = _text(root, 'rev-parse', 'HEAD'), _text(root, 'symbolic-ref', '--quiet', 'HEAD')
        if receipt.get('parent') != parent or receipt.get('branch') != branch:
            raise GitError('Monitor HEAD or branch changed before commit')
        real_index, reservation = git_dir / 'index', git_dir / 'index.lock'
        candidate_name = os.environ.get('GIT_INDEX_FILE')
        if not candidate_name:
            raise GitError('Monitor requires the native partial-commit index')
        candidate = Path(candidate_name)
        candidate = candidate if candidate.is_absolute() else root / candidate
        _regular(candidate)
        if candidate.parent.resolve() != git_dir or candidate.resolve() in (real_index, reservation):
            raise GitError('Monitor requires its owner temporary index')
        reserved = {path: _identity(_regular(path)) for path in (real_index, reservation, candidate)}
        rows = [row for row in _run(root, 'ls-files', '--stage', '-v', '-z', index=real_index).split(b'\0') if row]
        own = [row for row in rows if row.split(b'\t', 1)[1].decode() in PATHS]
        foreign = [row for row in rows if row.split(b'\t', 1)[1].decode() not in PATHS]
        own_hash = _sha(b''.join(row + b'\0' for row in own))
        if own_hash != receipt.get('own_index_sha256') or own_hash != _owned_signature(root, parent):
            raise GitError('Monitor paths have concurrent staged work or index flags')
        if _sha(b'\0'.join(foreign)) != receipt.get('index_fingerprint'):
            raise GitError('Foreign staged entries changed after snapshot preparation')
        changed = {name.decode() for name in _run(root, 'diff', '--cached', '--name-only',
                    '--no-renames', '-z', parent, index=candidate).split(b'\0') if name}
        if not changed or not changed <= set(PATHS):
            raise GitError('Monitor candidate changes paths outside its exact outputs')
        if _snapshot_hashes(root, candidate) != expected:
            raise GitError('Monitor staged snapshot differs from prepared bytes')
        for name in PATHS:
            output = root / name
            info = _regular(output)
            if info.st_mode & 0o111 or _sha(output.read_bytes()) != expected[name]:
                raise GitError('Monitor output changed after snapshot preparation')
        if (any(_identity(_regular(path)) != identity for path, identity in reserved.items())
                or _text(root, 'rev-parse', 'HEAD') != parent
                or _text(root, 'symbolic-ref', '--quiet', 'HEAD') != branch):
            raise GitError('Monitor Git reservation changed during validation')
        if _read_receipt(receipt_path) != original:
            raise GitError('Monitor receipt changed during validation')
        if receipt.get('guarded_snapshot') != marker:
            receipt['guarded_snapshot'] = marker
            _write_proof(receipt_path, receipt, original)
        return True
    except (OSError, ValueError, UnicodeError, KeyError, TypeError) as exc:
        raise GitError('Invalid or unsafe monitor snapshot state') from exc
