#!/usr/bin/env python3
"""Authenticate an explicitly selected teaching toolchain before it runs.

The release supplies a reviewed inventory. A private operator-owned policy
can select a newer reviewed inventory on this device. Neither the engine
directory, its Git configuration nor course material is an authority for
that decision. Subprocesses and Python imports consume only the private copy.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any, Iterator

DEFAULT_MANIFEST = Path(__file__).resolve().parents[1] / "references/course-engine.json"
POLICY = "brainteasers-engine.json"
MAX_FILES = 1024
MAX_BYTES = 64 * 1024 * 1024
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


class EngineTrustError(ValueError):
    """The selected engine does not match an explicitly authorized inventory."""


@dataclass(frozen=True)
class Engine:
    """Separate the enduring source location from the attested executable copy."""

    source: Path
    path: Path
    digest: str


def _identity(manifest: dict) -> str:
    content = json.dumps(manifest, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise EngineTrustError("Duplicate engine policy field")
        result[key] = value
    return result


def _manifest(value: Any) -> dict:
    if (not isinstance(value, dict) or set(value) != {"schema", "tree", "files"}
            or type(value["schema"]) is not int or value["schema"] != 1
            or not isinstance(value["tree"], str) or not re.fullmatch("[0-9a-f]{40}", value["tree"])):
        raise EngineTrustError("Invalid course engine policy header")
    files = value["files"]
    if not isinstance(files, dict) or not 0 < len(files) <= MAX_FILES:
        raise EngineTrustError("Invalid course engine inventory")
    total = 0
    for name, record in files.items():
        path = PurePosixPath(name)
        if (not path.parts or path.is_absolute() or str(path) != name or "\\" in name
                or any(part.startswith(".") or part == "__pycache__" for part in path.parts)
                or any(ord(char) < 32 or ord(char) == 127 for char in name)
                or any(parent.as_posix() in files for parent in path.parents)):
            raise EngineTrustError("Invalid or conflicting course engine path")
        if (not isinstance(record, dict) or set(record) != {"sha256", "size", "mode"}
                or not isinstance(record["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", record["sha256"])
                or record["mode"] not in ("100644", "100755")
                or type(record["size"]) is not int or record["size"] < 0):
            raise EngineTrustError("Invalid course engine file record")
        total += record["size"]
    if total > MAX_BYTES:
        raise EngineTrustError("Course engine exceeds its size budget")
    return value


def _canonical(path: Path) -> Path:
    path = path.absolute()
    if ".." in path.parts or path != path.resolve(strict=True):
        raise EngineTrustError("Course engine paths must be canonical and cannot traverse links")
    return path


def _safe_directory(path: Path) -> Path:
    """An unrelated account must not be able to replace a snapshot or trust policy."""
    for current in (path, *path.parents):
        attrs = current.stat()
        if (not stat.S_ISDIR(attrs.st_mode) or attrs.st_uid not in (0, os.getuid())
                or (attrs.st_mode & 0o022 and not attrs.st_mode & stat.S_ISVTX)):
            raise EngineTrustError("Course engine storage requires trusted directory ownership and permissions")
    return path


def _load_policy() -> dict:
    home = Path(os.environ.get("CONSTELLATION_COURSE_CONFIG_DIR") or
                (Path(__file__).resolve().parents[4] / "resources"))
    if not home.is_absolute() or ".." in home.parts or home != home.resolve():
        raise EngineTrustError("The course configuration directory must be canonical")
    policy = home / POLICY
    try:
        policy.lstat()
    except FileNotFoundError:
        return _manifest(json.loads(DEFAULT_MANIFEST.read_bytes(), object_pairs_hook=_pairs))
    _safe_directory(_canonical(home))
    if home.stat().st_uid != os.getuid() or home.stat().st_mode & 0o022:
        raise EngineTrustError("The engine policy needs an operator-owned configuration directory")
    with os.fdopen(os.open(policy, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW), "rb") as stream:
        attrs = os.fstat(stream.fileno())
        if (not stat.S_ISREG(attrs.st_mode) or stat.S_IMODE(attrs.st_mode) != 0o600
                or attrs.st_uid != os.getuid() or attrs.st_nlink != 1 or attrs.st_size > 1024 * 1024):
            raise EngineTrustError("The course engine policy must be a private user-owned regular file (0600)")
        data = stream.read(1024 * 1024 + 1)
        if len(data) != attrs.st_size:
            raise EngineTrustError("The course engine policy changed during its read")
        return _manifest(json.loads(data, object_pairs_hook=_pairs))


def _discarded_cache(parent: int) -> None:
    """Allow ordinary bytecode caches in the checkout; none enters the snapshot."""
    cache = os.open("__pycache__", DIR_FLAGS, dir_fd=parent)
    try:
        for name in os.listdir(cache):
            attrs = os.stat(name, dir_fd=cache, follow_symlinks=False)
            if not name.endswith(".pyc") or not stat.S_ISREG(attrs.st_mode) or attrs.st_nlink != 1:
                raise EngineTrustError("Unrecognized entry in course engine bytecode cache")
    finally:
        os.close(cache)


def _copy(source: Path, manifest: dict, destination: Path) -> None:
    files = manifest["files"]
    directories = {str(parent) for name in files for parent in PurePosixPath(name).parents}
    seen: set[str] = set()

    def visit(parent: int, prefix: PurePosixPath) -> None:
        for name in os.listdir(parent):
            path = prefix / name
            key = str(path)
            output = destination / key
            if name == "__pycache__":
                _discarded_cache(parent)
            elif key in directories:
                child = os.open(name, DIR_FLAGS, dir_fd=parent)
                try:
                    output.mkdir()
                    visit(child, path)
                finally:
                    os.close(child)
            elif key in files:
                record = files[key]
                fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
                with os.fdopen(fd, "rb") as stream:
                    attrs = os.fstat(fd)
                    mode = "100755" if attrs.st_mode & 0o111 else "100644"
                    if (not stat.S_ISREG(attrs.st_mode) or attrs.st_nlink != 1 or attrs.st_mode & 0o7000
                            or attrs.st_size != record["size"] or mode != record["mode"]):
                        raise EngineTrustError(f"Unapproved engine file type, permissions or size: {key}")
                    data = stream.read(record["size"] + 1)
                if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
                    raise EngineTrustError(f"Engine bytes differ from the approved inventory: {key}")
                output.write_bytes(data)
                output.chmod(0o755 if mode == "100755" else 0o644)
                seen.add(key)
            else:
                attrs = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if not stat.S_ISDIR(attrs.st_mode):
                    raise EngineTrustError(f"Unapproved course engine entry: {key}")
                # Git does not represent empty template/build directories.
                # Permit them only while empty and never project them.
                child = os.open(name, DIR_FLAGS, dir_fd=parent)
                try:
                    if os.listdir(child):
                        raise EngineTrustError(f"Unapproved course engine directory: {key}")
                finally:
                    os.close(child)
    fd = os.open(source, DIR_FLAGS)
    try:
        visit(fd, PurePosixPath())
    finally:
        os.close(fd)
    if seen != set(files):
        raise EngineTrustError("The course engine is missing approved files")


@contextmanager
def trusted_engine(system: Path) -> Iterator[Engine]:
    """Yield an authenticated private snapshot; keep its source path for evidence."""
    source = _canonical(system)
    manifest = _load_policy()
    temporary_parent = _safe_directory(Path(tempfile.gettempdir()).resolve(strict=True))
    with tempfile.TemporaryDirectory(prefix="brainteasers-engine-", dir=temporary_parent) as temporary:
        snapshot = Path(temporary).resolve() / "_sistema"
        snapshot.mkdir(mode=0o700)
        _copy(source, manifest, snapshot)
        yield Engine(source, snapshot, _identity(manifest))


def verify_engine_source(system: Path) -> str:
    """Check the selected policy and current source bytes without executing them."""
    with trusted_engine(system) as engine:
        return engine.digest


def _git_id(kind: str, data: bytes) -> str:
    return hashlib.sha1(f"{kind} {len(data)}\0".encode() + data).hexdigest()


def _git_tree(members: dict) -> str:
    """Rebuild the Git tree ID from verified blob IDs and relative names."""
    rows = []
    for name, member in members.items():
        directory = isinstance(member, dict)
        mode, oid = ("40000", _git_tree(member)) if directory else member
        label = name.encode("utf-8")
        key = label + (b"/" if directory else b"")
        rows.append((key, mode.encode() + b" " + label + b"\0" + bytes.fromhex(oid)))
    return _git_id("tree", b"".join(row for _, row in sorted(rows)))


def candidate_inventory(repository: Path, tree: str) -> dict:
    """Render a candidate from an independently selected local Git tree object.

    This read-only operation neither authorizes the result nor runs hooks,
    filters, project programs or network fetches. The caller must establish
    the trusted provenance of the full tree ID before adopting a new policy.
    """
    if not re.fullmatch("[0-9a-f]{40}", tree):
        raise EngineTrustError("Select an independently verified full Git tree object ID")
    repository = _canonical(repository)
    env = {"PATH": os.defpath, "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_NO_LAZY_FETCH": "1", "GIT_ALLOW_PROTOCOL": "", "GIT_TERMINAL_PROMPT": "0"}

    def git(*args: str) -> bytes:
        result = subprocess.run(["git", "--no-replace-objects", "-C", str(repository), *args],
                                env=env, capture_output=True, timeout=30)
        if result.returncode:
            raise EngineTrustError("Git could not read the selected engine object locally")
        return result.stdout

    if git("cat-file", "-t", tree) != b"tree\n":
        raise EngineTrustError("The approved object must be the toolchain tree itself")
    entries = git("ls-tree", "-r", "-l", "-z", tree).split(b"\0")[:-1]
    if not 0 < len(entries) <= MAX_FILES:
        raise EngineTrustError("Unsupported engine tree size")
    files: dict = {}
    hierarchy: dict = {}
    total = 0
    for raw in entries:
        metadata, name = raw.split(b"\t", 1)
        mode, kind, oid, size = metadata.split()
        if kind != b"blob" or mode not in (b"100644", b"100755") or not size.isdigit():
            raise EngineTrustError("Only regular files can enter the approved engine")
        total += int(size)
        if total > MAX_BYTES:
            raise EngineTrustError("Course engine exceeds its size budget")
        data = git("cat-file", "blob", oid.decode("ascii"))
        blob = oid.decode("ascii")
        if len(data) != int(size) or _git_id("blob", data) != blob:
            raise EngineTrustError("Local Git blob bytes differ from their object ID")
        branch = hierarchy
        segments = name.decode("utf-8").split("/")
        for part in segments[:-1]:
            branch = branch.setdefault(part, {})
        branch[segments[-1]] = (mode.decode("ascii"), blob)
        files[name.decode("utf-8")] = {"sha256": hashlib.sha256(data).hexdigest(),
                                      "size": len(data), "mode": mode.decode("ascii")}
    if _git_tree(hierarchy) != tree:
        raise EngineTrustError("Local Git entries differ from the approved tree object")
    return _manifest({"schema": 1, "tree": tree, "files": files})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    inventory = commands.add_parser("inventory", help="Print a candidate inventory from a reviewed tree")
    inventory.add_argument("--repository", required=True, type=Path)
    inventory.add_argument("--tree", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(candidate_inventory(args.repository, args.tree), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Course engine inventory failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
