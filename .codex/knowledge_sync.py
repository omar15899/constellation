#!/usr/bin/env python3
"""Export committed Git documents and explicitly enrolled local research reports.

The policy is local consent, the repository registry is ownership metadata, and
the receiver's receipt confirms local delivery only. None implies publication.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from contextvars import ContextVar
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import posixpath
import re
import shutil
import stat
import string
import subprocess
import sys
import unicodedata
import uuid
from typing import Any, Iterator
from urllib.parse import unquote, urlsplit


MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_REPO_BYTES = 128 * 1024 * 1024
MAX_DOCUMENTS = 10_000
MAX_BUNDLE_BYTES = 200 * 1024 * 1024
TEXT_EXTENSIONS = {".md", ".rst", ".txt", ".tex", ".bib"}
ASSET_EXTENSIONS = {".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".svg", ".webp"}
DOCUMENT_DIRS = {"docs", "doc", "documentation", "reports", "research", "papers", "notes", "figures"}
DENIED_DIRS = {
    "vendor", "vendors", "third_party", "thirdparty", "third-party", "node_modules", ".venv", "build", "dist",
    "archives", "archive", "sessions", "logs", "transcripts", "conversations",
    "prompts", "data", "datasets", "raw", "private", "secrets", "tests", "fixtures", "docs-vault",
}
DENIED_NAMES = {"agents.md", "claude.md", "skill.md", "review.md", "cmakelists.txt"}
PRIVATE_NAMES = ("conversation", "transcript", "rollout", "auth", "credentials", "secrets")
ALIAS_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
REPORT_RE = re.compile(r"(?:report|diagnostics|sleeve_diagnostics|comparison_\d{4}-\d{2}-\d{2})\.md\Z", re.I)
LOCAL_ASSETS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".pdf"}
ASCII_PUNCTUATION = frozenset(string.punctuation)
DEFAULT_POLICY = Path.home() / ".codex" / "knowledge-sync.json"
GIT_HELPER = "import os,sys;os.fchdir(int(sys.argv[1]));os.execvpe(sys.argv[2],sys.argv[2:],os.environ)"
PINNED_ROOTS: ContextVar[dict[Path, int]] = ContextVar("knowledge_source_roots", default={})


class KnowledgeError(RuntimeError):
    """A document or configuration cannot be safely synchronized."""


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise KnowledgeError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_json(data: bytes) -> Any:
    try:
        return json.loads(data, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError) as exc:
        raise KnowledgeError("Invalid JSON") from exc


def _git(root: Path, *args: str, input: bytes | None = None) -> bytes:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        executable = shutil.which("git")
        if executable is None:
            raise KnowledgeError("Git executable is unavailable")
        git = str(Path(executable).resolve(strict=True))
        with _directory(root) as fd:
            # fchdir pins the already opened directory even if its pathname is
            # replaced. The fixed helper also works on macOS, unlike /dev/fd cwd.
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-c", GIT_HELPER, str(fd), git,
                 "--no-optional-locks", "--no-replace-objects", *args], input=input,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=120,
                check=False, pass_fds=(fd,),
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KnowledgeError(f"Git unavailable for {root}") from exc
    if result.returncode:
        raise KnowledgeError(f"Git {args[0]} failed for {root}")
    return result.stdout


def _canonical(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise KnowledgeError(f"{label} must be an absolute canonical path")
    path = Path(value)
    try:
        canonical = path.resolve()
    except (OSError, RuntimeError) as exc:
        raise KnowledgeError(f"Invalid {label}") from exc
    if not path.is_absolute() or str(path) != value or canonical != path:
        raise KnowledgeError(f"{label} must be absolute, canonical, and contain no symlinks")
    return path


def _relative(value: Any, *, directory: bool = False) -> str:
    if not isinstance(value, str) or not value or "\\" in value or any(ord(c) < 32 for c in value):
        raise KnowledgeError("Invalid relative document path")
    path = PurePosixPath(value)
    if value == "." and directory:
        return value
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")) or str(path) != value:
        raise KnowledgeError(f"Unsafe relative path: {value}")
    return value


def _denied(path: str, *, include_hidden: bool = False, directory: bool = False) -> bool:
    parts = PurePosixPath(path).parts
    directories = parts if directory else parts[:-1]
    folded = [part.casefold() for part in parts]
    if not directory and (re.fullmatch(r"(?:requirements|constraints).*\.txt", folded[-1])
                          or re.search(r"(?:^|[\W_])prompts?(?:[\W_]|$)", folded[-1])):
        return True
    if any(part in DENIED_DIRS for part in folded[:len(directories)]):
        return True
    hidden = [index for index, part in enumerate(directories) if part.startswith(".")]
    allowed_hidden = include_hidden and hidden == [0] and (
        directories[0] == ".codex" or len(directories) >= 2 and directories[:2] == (".claude", "docs")
    )
    if hidden and not allowed_hidden:
        return True
    if not directory and parts[-1].startswith(".") and not include_hidden:
        return True
    if any(folded[index:index + 2] == ["docs", "vault"] for index in range(len(folded) - 1)):
        return True
    return (bool(folded) and folded[-1] in DENIED_NAMES) or any(
        token in part for part in folded for token in PRIVATE_NAMES
    )


def _selected(path: str, includes: set[str]) -> bool:
    explicit = path in includes
    if _denied(path, include_hidden=explicit):
        return False
    suffix = PurePosixPath(path).suffix.casefold()
    return suffix in TEXT_EXTENSIONS or (suffix in ASSET_EXTENSIONS and (
        explicit or any(part.casefold() in DOCUMENT_DIRS for part in PurePosixPath(path).parts[:-1])
    ))


@contextmanager
def _directory(path: Path, *, create: bool = False) -> Iterator[int]:
    """Hold a directory without following a symlink in any component."""
    if not path.is_absolute():
        raise KnowledgeError("Expected absolute path")
    ancestors = [(root, fd) for root, fd in PINNED_ROOTS.get().items() if path.is_relative_to(root)]
    if ancestors:
        root, pinned_fd = max(ancestors, key=lambda item: len(item[0].parts))
        fd = os.dup(pinned_fd)
        parts = path.relative_to(root).parts
    else:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        parts = path.parts[1:]
    try:
        for part in parts:
            try:
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    except OSError as exc:
        raise KnowledgeError(f"Unsafe or inaccessible directory: {path}") from exc
    finally:
        os.close(fd)


@contextmanager
def _pinned_source(root: Path) -> Iterator[None]:
    """Keep one source identity across authorization, Git and local collection."""
    with _directory(root) as fd:
        token = PINNED_ROOTS.set({**PINNED_ROOTS.get(), root: fd})
        try:
            yield
        finally:
            PINNED_ROOTS.reset(token)


def _lstat(path: Path) -> os.stat_result | None:
    if path in PINNED_ROOTS.get():
        return os.fstat(PINNED_ROOTS.get()[path])
    try:
        with _directory(path.parent) as fd:
            return os.stat(path.name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except KnowledgeError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            return None
        raise


def _read_at(fd: int, name: str, limit: int) -> bytes:
    try:
        file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(file_fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise KnowledgeError(f"Not a regular file: {name}")
            if before.st_size > limit:
                raise KnowledgeError(f"File exceeds byte limit: {name}")
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            if len(data) > limit:
                raise KnowledgeError(f"File exceeds byte limit: {name}")
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
            ):
                raise KnowledgeError(f"File changed during read: {name}")
            return data
    except OSError as exc:
        raise KnowledgeError(f"Unsafe or inaccessible file: {name}") from exc


def _read(path: Path, limit: int) -> bytes:
    with _directory(path.parent) as fd:
        return _read_at(fd, path.name, limit)


def _exact_git_root(root: Path) -> None:
    if not root.is_dir() or Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel")).strip()).resolve() != root:
        raise KnowledgeError(f"Not an exact Git repository root: {root}")


def _validate_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "hub_root", "target_root", "sources"}:
        raise KnowledgeError("Policy requires schema_version, hub_root, target_root, sources")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise KnowledgeError("Unsupported policy schema_version")
    hub = _canonical(value["hub_root"], "hub_root")
    target = _canonical(value["target_root"], "target_root")
    if target == hub or target.is_relative_to(hub) or hub.is_relative_to(target):
        raise KnowledgeError("Source hub and target must be separate roots")
    _exact_git_root(hub)
    _exact_git_root(target)
    if not isinstance(value["sources"], list):
        raise KnowledgeError("sources must be a list")
    roots: set[str] = set()
    aliases: set[str] = set()
    for source in value["sources"]:
        if not isinstance(source, dict) or not {"root", "alias", "classification"} <= set(source) or set(source) - {
            "root", "alias", "classification", "local_paths", "include_paths"
        }:
            raise KnowledgeError("Invalid source policy fields")
        root = _canonical(source["root"], "source root")
        if not root.is_relative_to(hub):
            raise KnowledgeError("Source root must be inside hub_root")
        alias = source["alias"]
        if not isinstance(alias, str) or not ALIAS_RE.fullmatch(alias):
            raise KnowledgeError("Source alias must be a lowercase slug")
        if str(root) in roots or alias in aliases:
            raise KnowledgeError("Duplicate source root or alias")
        roots.add(str(root))
        aliases.add(alias)
        if not isinstance(source["classification"], str) or source["classification"] not in {"personal", "work"}:
            raise KnowledgeError("Source classification must be personal or work")
        for field in ("local_paths", "include_paths"):
            paths = source.get(field, [])
            if not isinstance(paths, list) or len(paths) != len(set(str(item) for item in paths)):
                raise KnowledgeError(f"{field} must be a list of unique paths")
            for item in paths:
                relative = _relative(item, directory=field == "local_paths")
                if relative != "." and _denied(relative, include_hidden=field == "include_paths", directory=field == "local_paths"):
                    raise KnowledgeError(f"Forbidden {field}: {relative}")
                if field == "include_paths" and not _selected(relative, {relative}):
                    raise KnowledgeError(f"include_paths requires documentary files: {relative}")
    return value


def load_policy(path: Path) -> dict[str, Any]:
    """Read explicit local consent; source availability is checked per source."""
    policy = _validate_policy(_parse_json(_read(path.absolute(), 1024 * 1024)))
    _policy_location(path, policy)
    return policy


def _policy_location(path: Path, policy: dict[str, Any]) -> None:
    location = _canonical(str(path.absolute()), "policy path")
    if any(location.is_relative_to(Path(policy[field])) for field in ("hub_root", "target_root")):
        raise KnowledgeError("The local consent policy must remain outside hub_root and target_root")


def _registry(hub: Path) -> list[dict[str, Any]]:
    registry = _parse_json(_read(hub / ".codex" / "repositories.json", 1024 * 1024))
    return _validate_registry_value(registry, hub)


def _validate_registry_value(registry: Any, hub: Path) -> list[dict[str, Any]]:
    if not isinstance(registry, dict) or registry.get("schema_version") != 1 or not isinstance(registry.get("repositories"), list):
        raise KnowledgeError("Invalid repository registry")
    seen: set[str] = set()
    for entry in registry["repositories"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("management"), str) or entry["management"] not in {"native", "external"}:
            raise KnowledgeError("Invalid repository registry entry")
        rel = _relative(entry.get("path"), directory=True)
        canonical = (hub / rel).resolve()
        if not canonical.is_relative_to(hub) or canonical != hub / rel or str(canonical) in seen:
            raise KnowledgeError("Noncanonical or duplicate repository registry path")
        seen.add(str(canonical))
    return registry["repositories"]


def _authorize(policy: dict[str, Any], source: dict[str, Any]) -> Path:
    _validate_policy(policy)
    if source not in policy["sources"]:
        raise KnowledgeError("Source has no explicit enrollment")
    root = Path(source["root"])
    hub = Path(policy["hub_root"])
    entries = _registry(hub)
    if not any(hub / entry["path"] == root and entry["management"] == "native" for entry in entries):
        raise KnowledgeError(f"Source is not a registered native repository: {root}")
    if any(entry["management"] == "external" and root.is_relative_to(hub / entry["path"]) for entry in entries):
        raise KnowledgeError("External repositories cannot be enrolled")
    _exact_git_root(root)
    return root


def _git_documents(root: Path, revision: str, includes: set[str]) -> tuple[list[tuple[str, str]], dict[str, tuple[str, str, str]]]:
    selected: list[tuple[str, str]] = []
    tracked: dict[str, tuple[str, str, str]] = {}
    for record in _git(root, "ls-tree", "-r", "-z", "--full-tree", revision).split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split(" ")
            path = _relative(raw_path.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise KnowledgeError("Invalid Git tree document path") from exc
        tracked[path] = (mode, kind, oid)
        if _selected(path, includes):
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise KnowledgeError(f"Document is not a regular Git blob: {path}")
            selected.append((path, oid))
    if not includes <= {path for path, _ in selected}:
        raise KnowledgeError("An explicitly included document is absent from HEAD or forbidden")
    if len(selected) > MAX_DOCUMENTS:
        raise KnowledgeError("Repository exceeds document count limit")
    return selected, tracked


def _local_documents(root: Path, local_paths: list[str], tracked: set[str],
                     tracked_dependencies: set[str] | None = None) -> Iterator[tuple[str, bytes]]:
    seen: set[str] = set()
    reports: list[tuple[str, bytes]] = []
    total = 0
    count = 0

    def bounded(item: tuple[str, bytes]) -> tuple[str, bytes]:
        nonlocal total, count
        total += len(item[1])
        count += 1
        if total > MAX_REPO_BYTES or count > MAX_DOCUMENTS:
            raise KnowledgeError("Local reports exceed repository limits")
        return item

    def walk(fd: int, relative: str) -> Iterator[tuple[str, bytes]]:
        try:
            entries = sorted(os.scandir(fd), key=lambda item: item.name)
            for entry in entries:
                path = f"{relative}/{entry.name}" if relative else entry.name
                _relative(path)
                if _denied(path):
                    continue
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    if not _denied(path, directory=True):
                        raise KnowledgeError(f"Symlink in enrolled local reports: {path}")
                    continue
                if stat.S_ISDIR(info.st_mode):
                    if _denied(path, directory=True):
                        continue
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        yield from walk(child, path)
                    finally:
                        os.close(child)
                elif REPORT_RE.fullmatch(entry.name) and path not in tracked and path not in seen:
                    if not stat.S_ISREG(info.st_mode):
                        raise KnowledgeError(f"Nonregular local report: {path}")
                    parent = root / PurePosixPath(path).parent
                    if Path(os.fsdecode(_git(parent, "rev-parse", "--show-toplevel")).strip()).resolve() != root:
                        raise KnowledgeError(f"Local report belongs to another Git repository: {path}")
                    seen.add(path)
                    yield path, _read_at(fd, entry.name, MAX_FILE_BYTES)
        except OSError as exc:
            raise KnowledgeError("Unable to safely enumerate local reports") from exc

    for relative in local_paths:
        path = root / relative
        if _lstat(path) is None:
            continue
        with _directory(path) as fd:
            for item in walk(fd, "" if relative == "." else relative):
                reports.append(item)
                yield bounded(item)
    # Only direct inline links from explicitly enrolled reports expand the local
    # snapshot. A link never authorizes a directory or a second repository.
    for report, content in reports:
        try:
            markdown = content.decode("utf-8")
        except UnicodeError as exc:
            raise KnowledgeError(f"Local report is not UTF-8 Markdown: {report}") from exc
        for path in _dependencies(report, markdown, local_paths):
            if path in seen:
                continue
            if path in tracked:
                if tracked_dependencies is not None:
                    tracked_dependencies.add(path)
                continue
            full = root / path
            if _lstat(full) is None:
                continue
            if Path(os.fsdecode(_git(full.parent, "rev-parse", "--show-toplevel")).strip()).resolve() != root:
                raise KnowledgeError(f"Local dependency belongs to another Git repository: {path}")
            seen.add(path)
            yield bounded((path, _read(full, MAX_FILE_BYTES)))


def _unescape_destination(text: str) -> str:
    """Decode Markdown escapes of ASCII punctuation, leaving other escapes intact."""
    result: list[str] = []
    index = 0
    while index < len(text):
        if text[index] == "\\" and index + 1 < len(text) and text[index + 1] in ASCII_PUNCTUATION:
            result.append(text[index + 1])
            index += 2
        else:
            result.append(text[index])
            index += 1
    return "".join(result)


def _inline_destinations(text: str) -> Iterator[str]:
    """Yield direct inline destinations with a monotone, bounded scanner."""
    size = len(text)
    index = 0

    def horizontal(position: int) -> int:
        while position < size and text[position] in " \t":
            position += 1
        return position

    while index < size:
        if text[index] != "[":
            index += 1
            continue

        index += 1
        while index < size and text[index] not in "[]\r\n":
            index += 1
        if index == size:
            return
        if text[index] != "]":
            continue

        index += 1
        if index == size:
            return
        if text[index] != "(":
            continue

        index = horizontal(index + 1)
        if index == size:
            return

        if text[index] == "<":
            index += 1
            start = index
            while index < size:
                char = text[index]
                if char == "\\" and index + 1 < size and text[index + 1] in ASCII_PUNCTUATION:
                    index += 2
                    continue
                if char in ">[\r\n":
                    break
                index += 1
            if index == size:
                return
            if text[index] != ">":
                continue
            end = index
            index += 1
        else:
            start = index
            depth = 0
            while index < size:
                char = text[index]
                if char == "\\" and index + 1 < size and text[index + 1] in ASCII_PUNCTUATION:
                    index += 2
                    continue
                if char in " \t[\r\n":
                    break
                if char == "(":
                    depth += 1
                elif char == ")":
                    if depth == 0:
                        break
                    depth -= 1
                index += 1
            end = index
            # Bare destinations cannot contain whitespace, even inside ().
            if depth:
                continue

        if index == size:
            return
        if start == end:
            continue

        if text[index] == ")":
            index += 1
            yield _unescape_destination(text[start:end])
            continue
        if text[index] not in " \t":
            continue

        index = horizontal(index)
        if index == size:
            return
        if text[index] == ")":
            index += 1
            yield _unescape_destination(text[start:end])
            continue

        opening = text[index]
        if opening not in "\"'(":
            continue
        closing = ")" if opening == "(" else opening
        index += 1

        while index < size:
            char = text[index]
            if char in "[\r\n" or char == closing:
                break
            if char == "\\":
                if index + 1 == size or text[index + 1] in "\r\n":
                    break
                index += 2
                continue
            if opening == "(" and char == "(":
                break
            index += 1

        if index == size:
            return
        if text[index] != closing:
            continue

        index = horizontal(index + 1)
        if index < size and text[index] == ")":
            index += 1
            yield _unescape_destination(text[start:end])


def _dependencies(report: str, markdown: str, local_paths: list[str]) -> list[str]:
    selected: set[str] = set()
    for destination in _inline_destinations(markdown):
        try:
            url = urlsplit(destination)
            if url.scheme or url.netloc or not url.path:
                continue
            decoded = unquote(url.path, errors="strict")
            if decoded.startswith("/") or "\\" in decoded or any(ord(c) < 32 for c in decoded):
                continue
            path = posixpath.normpath(posixpath.join(str(PurePosixPath(report).parent), decoded))
            _relative(path)
        except (ValueError, UnicodeError, KnowledgeError):
            continue
        if _denied(path) or not any(local == "." or PurePosixPath(path).is_relative_to(local) for local in local_paths):
            continue
        suffix = PurePosixPath(path).suffix.casefold()
        if suffix in LOCAL_ASSETS or (suffix == ".md" and "tables" in [part.casefold() for part in PurePosixPath(path).parts[:-1]]):
            selected.add(path)
    return sorted(selected)


def collect_bundle(policy: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic complete document snapshot without reading working Git files."""
    if not isinstance(source, dict) or not isinstance(policy, dict) or source not in policy.get("sources", []):
        raise KnowledgeError("Source has no explicit enrollment")
    root = _canonical(source.get("root"), "source root")
    with _pinned_source(root):
        return _collect_bundle(policy, source)


def _collect_bundle(policy: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    root = _authorize(policy, source)
    revision = os.fsdecode(_git(root, "rev-parse", "--verify", "HEAD^{commit}")).strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
        raise KnowledgeError("Invalid Git revision")
    selected, tracked = _git_documents(root, revision, set(source.get("include_paths", [])))
    tracked_dependencies: set[str] = set()
    local_documents = list(_local_documents(root, source.get("local_paths", []), set(tracked), tracked_dependencies))
    selected_paths = {path for path, _ in selected}
    for path in sorted(tracked_dependencies - selected_paths):
        mode, kind, oid = tracked[path]
        if mode not in {"100644", "100755"} or kind != "blob":
            raise KnowledgeError(f"Tracked report dependency is not a regular blob: {path}")
        selected.append((path, oid))
    if len(selected) + len(local_documents) > MAX_DOCUMENTS:
        raise KnowledgeError("Repository exceeds document count limit")
    documents: list[dict[str, str]] = []
    normalized: dict[str, tuple[str, bool]] = {}
    total = 0
    planned_total = sum(len(content) for _, content in local_documents)

    def add(path: str, content: bytes, origin: str) -> None:
        nonlocal total
        parts = PurePosixPath(path).parts
        for index in range(1, len(parts) + 1):
            original = "/".join(parts[:index])
            key = unicodedata.normalize("NFC", unicodedata.normalize("NFC", original).casefold())
            is_file = index == len(parts)
            previous = normalized.get(key)
            if previous is not None and (previous != (original, is_file) or is_file):
                raise KnowledgeError(f"Document path collision: {path}")
            normalized[key] = (original, is_file)
        if len(content) > MAX_FILE_BYTES:
            raise KnowledgeError(f"File exceeds byte limit: {path}")
        total += len(content)
        if total > MAX_REPO_BYTES or len(documents) >= MAX_DOCUMENTS:
            raise KnowledgeError("Repository exceeds document limits")
        documents.append({"path": path, "sha256": hashlib.sha256(content).hexdigest(),
                          "content": base64.b64encode(content).decode("ascii"), "origin": origin})

    # --batch-check bounds allocations before any blob content is materialized.
    if selected:
        requested = b"".join(oid.encode("ascii") + b"\n" for _, oid in selected)
        sizes = _git(root, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)", input=requested).splitlines()
        if len(sizes) != len(selected):
            raise KnowledgeError("Incomplete Git object size response")
        for (path, oid), row in zip(selected, sizes):
            try:
                response_oid, kind, size = row.decode("ascii").split()
                length = int(size)
            except (ValueError, UnicodeError) as exc:
                raise KnowledgeError("Invalid Git object size response") from exc
            if response_oid != oid or kind != "blob" or length < 0 or length > MAX_FILE_BYTES:
                raise KnowledgeError(f"Invalid or oversized Git document: {path}")
            planned_total += length
        if planned_total > MAX_REPO_BYTES:
            raise KnowledgeError("Repository exceeds byte limit")
        # One bounded batch avoids a subprocess for every document in large research repositories.
        payload = _git(root, "cat-file", "--batch", input=requested)
        offset = 0
        for path, oid in selected:
            end = payload.find(b"\n", offset)
            try:
                response_oid, kind, size = payload[offset:end].decode("ascii").split()
                length = int(size)
            except (ValueError, UnicodeError) as exc:
                raise KnowledgeError("Invalid Git object content response") from exc
            start = end + 1
            if end < 0 or response_oid != oid or kind != "blob" or payload[start + length:start + length + 1] != b"\n":
                raise KnowledgeError("Incomplete Git object content response")
            add(path, payload[start:start + length], "git")
            offset = start + length + 1
        if offset != len(payload):
            raise KnowledgeError("Unexpected trailing Git object content")
    for path, content in local_documents:
        add(path, content, "local")
    bundle: dict[str, Any] = {"schema_version": 1, "source": {"root": str(root), "alias": source["alias"], "revision": revision},
                              "documents": sorted(documents, key=lambda item: item["path"])}
    bundle["bundle_hash"] = hashlib.sha256(_json_bytes(bundle)).hexdigest()
    if len(_json_bytes(bundle)) > MAX_BUNDLE_BYTES:
        raise KnowledgeError("Bundle exceeds serialized byte limit")
    return bundle


def _state_dir(hub: Path) -> Path:
    raw = os.fsdecode(_git(hub, "rev-parse", "--git-path", "constellation/knowledge-sync")).strip()
    path = Path(raw)
    path = Path(os.path.abspath(path if path.is_absolute() else hub / path))
    with _directory(path, create=True):
        pass
    return path


@contextmanager
def _lock(hub: Path) -> Iterator[Path]:
    state = _state_dir(hub)
    with _directory(state) as fd:
        lock_fd = os.open("sync.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
        try:
            if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
                raise KnowledgeError("Synchronization lock must be a regular file")
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise KnowledgeError("Another knowledge synchronization is running") from exc
            yield state
        finally:
            os.close(lock_fd)


def _write(path: Path, content: bytes, *, expected_content: bytes | None = None,
           must_be_absent: bool = False) -> None:
    with _directory(path.parent, create=True) as fd:
        try:
            existing = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing and not stat.S_ISREG(existing.st_mode):
            raise KnowledgeError(f"Refusing symlink output: {path}")
        if must_be_absent and existing is not None:
            raise KnowledgeError(f"File appeared before creation; retry without overwriting it: {path}")
        temporary = f".{path.name}.{uuid.uuid4().hex}"
        temporary_fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            with os.fdopen(temporary_fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if expected_content is not None and _read_at(fd, path.name, 1024 * 1024) != expected_content:
                raise KnowledgeError(f"File changed before update; retry without overwriting it: {path}")
            if must_be_absent:
                try:
                    os.link(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
                except FileExistsError as exc:
                    raise KnowledgeError(f"File appeared before creation; retry without overwriting it: {path}") from exc
                os.unlink(temporary, dir_fd=fd)
            else:
                os.rename(temporary, path.name, src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=fd)
            except FileNotFoundError:
                pass


def _choose(policy: dict[str, Any], repo: str | None) -> list[dict[str, Any]]:
    if repo is None:
        return policy["sources"]
    hub = Path(policy["hub_root"])
    path = Path(repo)
    absolute = (path if path.is_absolute() else hub / path).resolve()
    result = [source for source in policy["sources"] if source["alias"] == repo or Path(source["root"]) == absolute]
    if len(result) != 1:
        raise KnowledgeError("Repository is not uniquely enrolled")
    return result


def _summary(bundle: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """Keep coverage limits visible without extending the receiver's wire format."""
    paths = {document["path"] for document in bundle["documents"]}
    documentary = 0
    for raw in _git(Path(source["root"]), "ls-tree", "-r", "-z", "--name-only", bundle["source"]["revision"]).split(b"\0"):
        if raw and PurePosixPath(raw.decode("utf-8")).suffix.casefold() in TEXT_EXTENSIONS | ASSET_EXTENSIONS:
            documentary += 1
    dependencies = 0
    absent = 0
    for document in bundle["documents"]:
        if document["origin"] == "local" and REPORT_RE.fullmatch(PurePosixPath(document["path"]).name):
            markdown = base64.b64decode(document["content"]).decode("utf-8")
            expected = _dependencies(document["path"], markdown, source.get("local_paths", []))
            dependencies += len(expected)
            absent += sum(path not in paths for path in expected)
    return {"schema_version": 1, "scope": "local", "bundle_hash": bundle["bundle_hash"],
            "documents": len(paths), "git_document_candidates": documentary,
            "git_document_candidates_omitted": documentary - sum(doc["origin"] == "git" for doc in bundle["documents"]),
            "local_inline_dependencies": dependencies, "local_inline_dependencies_not_copied": absent,
            "coverage": "Selected Git documents and authorized local reports; direct inline links only"}


def sync(policy_path: Path, *, repo: str | None = None) -> dict[str, Any]:
    """Deliver independently per source, retaining only validated local receipts."""
    policy_path = policy_path.absolute()
    policy = load_policy(policy_path)
    result: dict[str, Any] = {"schema_version": 1, "scope": "local", "receipts": [], "errors": []}
    with _lock(Path(policy["hub_root"])) as state:
        for enrolled in _choose(policy, repo):
            alias = enrolled["alias"]
            try:
                current = load_policy(policy_path)
                if current != policy:
                    raise KnowledgeError("Policy changed during synchronization; retry")
                bundle = collect_bundle(current, enrolled)
                _write(state / "summaries" / f"{alias}.json", _json_bytes(_summary(bundle, enrolled)) + b"\n")
                interpreter = Path.home() / ".venvs" / "omaros" / "bin" / "python"
                python = str(interpreter) if interpreter.is_file() else sys.executable
                receiver = Path(policy["target_root"]) / ".codex" / "knowledge_import.py"
                # Check the executable source path without reading arbitrary target files.
                with _directory(receiver.parent) as fd:
                    info = os.stat(receiver.name, dir_fd=fd, follow_symlinks=False)
                    if not stat.S_ISREG(info.st_mode):
                        raise KnowledgeError("Receiver must be a regular file")
                delivered = subprocess.run(
                    [python, str(receiver), "--policy", str(policy_path), "import"], input=_json_bytes(bundle),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, check=False,
                )
                if delivered.returncode:
                    raise KnowledgeError("OmarOS receiver rejected the bundle")
                if len(delivered.stdout) > 4 * 1024 * 1024:
                    raise KnowledgeError("Oversized receiver receipt")
                receipt = _parse_json(delivered.stdout)
                if not isinstance(receipt, dict) or type(receipt.get("schema_version")) is not int or type(receipt.get("count")) is not int or any(receipt.get(key) != expected for key, expected in {
                    "schema_version": 1, "status": "RECEIVED_LOCAL", "bundle_hash": bundle["bundle_hash"],
                    "alias": alias, "revision": bundle["source"]["revision"], "count": len(bundle["documents"]),
                }.items()):
                    raise KnowledgeError("Receiver receipt does not match the submitted bundle")
                _write(state / "receipts" / f"{alias}.json", _json_bytes(receipt) + b"\n")
                result["receipts"].append(receipt)
            except (KnowledgeError, OSError, subprocess.TimeoutExpired) as exc:
                result["errors"].append({"alias": alias, "error": str(exc)})
        _write(state / "last-run.json", _json_bytes(result) + b"\n")
    return result


def status(policy_path: Path, hub_root: Path | None = None) -> dict[str, Any]:
    policy = load_policy(policy_path) if policy_path.exists() else None
    hub = Path(policy["hub_root"]) if policy else (hub_root or Path(__file__).resolve().parent.parent).resolve()
    sources = {source["root"]: source for source in policy["sources"]} if policy else {}
    result: dict[str, Any] = {"schema_version": 1, "scope": "local", "policy": str(policy_path),
                              "registered": [], "enrolled": [], "pending": [], "external": [], "missing": []}
    state = _state_dir(hub)
    registry = _registry(hub)
    for entry in registry:
        root = hub / entry["path"]
        item = {"path": entry["path"], "root": str(root), "management": entry["management"]}
        result["registered"].append(item)
        if not root.is_dir():
            result["missing"].append(item)
        if entry["management"] == "external":
            result["external"].append(item)
        elif str(root) in sources:
            source = sources[str(root)]
            enrolled: dict[str, Any] = {**item, "alias": source["alias"], "classification": source["classification"], "exists": root.is_dir()}
            receipt = state / "receipts" / f"{source['alias']}.json"
            if receipt.exists():
                enrolled["receipt"] = _parse_json(_read(receipt, 4 * 1024 * 1024))
            summary = state / "summaries" / f"{source['alias']}.json"
            if summary.exists():
                enrolled["summary"] = _parse_json(_read(summary, 1024 * 1024))
            result["enrolled"].append(enrolled)
        else:
            result["pending"].append(item)
    registered = {str(hub / entry["path"]) for entry in registry}
    # Discovery exposes authorization gaps; it never enrolls or inventories worktrees.
    with _directory(hub) as fd:
        for entry in sorted(os.scandir(fd), key=lambda item: item.name):
            root = hub / entry.name
            if entry.name.startswith(".") or str(root) in registered or not entry.is_dir(follow_symlinks=False):
                continue
            child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                try:
                    marker = os.stat(".git", dir_fd=child, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if not (stat.S_ISDIR(marker.st_mode) or stat.S_ISREG(marker.st_mode)):
                    continue
                try:
                    _exact_git_root(root)
                except KnowledgeError:
                    continue
                result["pending"].append({"path": entry.name, "root": str(root), "management": "unregistered"})
            finally:
                os.close(child)
    for root, source in sources.items():
        if root not in registered:
            result["missing"].append({"root": root, "alias": source["alias"], "reason": "unregistered"})
    return result


def enroll(policy_path: Path, repo: str, classification: str, local_paths: list[str] | None = None,
           hub_root: Path | None = None, target_root: Path | None = None,
           include_paths: list[str] | None = None) -> dict[str, Any]:
    """Explicitly authorize one exact owned Git root, registering new roots safely."""
    if classification not in {"personal", "work"}:
        raise KnowledgeError("Explicit personal or work classification is required")
    relative = _relative(repo, directory=True)
    policy_existed = policy_path.exists()
    if policy_existed:
        policy = load_policy(policy_path)
        if hub_root and hub_root.resolve() != Path(policy["hub_root"]):
            raise KnowledgeError("--hub conflicts with the existing policy")
        if target_root and target_root.resolve() != Path(policy["target_root"]):
            raise KnowledgeError("--target conflicts with the existing policy")
    else:
        if target_root is None:
            raise KnowledgeError("A new policy requires explicit --target")
        hub = _canonical(str((hub_root or Path(__file__).resolve().parent.parent).absolute()), "hub_root")
        target = _canonical(str(target_root.absolute()), "target_root")
        policy = _validate_policy({"schema_version": 1, "hub_root": str(hub), "target_root": str(target), "sources": []})
    _policy_location(policy_path, policy)
    hub = Path(policy["hub_root"])
    root = _canonical(str(hub / relative), "source root")
    _exact_git_root(root)
    alias = "constellation" if relative == "." else re.sub(r"[^a-z0-9]+", "-", root.name.casefold()).strip("-")
    if not alias:
        raise KnowledgeError("Cannot derive a source alias")
    with _lock(hub):
        if policy_path.exists() != policy_existed:
            raise KnowledgeError("Policy changed during enrollment; retry")
        policy_bytes = None
        if policy_existed:
            policy_bytes = _read(policy_path.absolute(), 1024 * 1024)
            current = _validate_policy(_parse_json(policy_bytes))
            _policy_location(policy_path, current)
            if current != policy:
                raise KnowledgeError("Policy changed during enrollment; retry")
        registry_path = hub / ".codex" / "repositories.json"
        registry_bytes = _read(registry_path, 1024 * 1024)
        registry = _parse_json(registry_bytes)
        entries = _validate_registry_value(registry, hub)
        if any(entry["management"] == "external" and root.is_relative_to(hub / entry["path"]) for entry in entries):
            raise KnowledgeError("External repositories cannot be enrolled or reclassified")
        existing = next((source for source in policy["sources"] if source["root"] == str(root)), None)
        source = {"root": str(root), "alias": existing["alias"] if existing else alias, "classification": classification}
        if local_paths is not None:
            source["local_paths"] = local_paths
        elif existing and "local_paths" in existing:
            source["local_paths"] = existing["local_paths"]
        if include_paths is not None:
            source["include_paths"] = include_paths
        elif existing and "include_paths" in existing:
            source["include_paths"] = existing["include_paths"]
        policy["sources"] = [item for item in policy["sources"] if item["root"] != str(root)] + [source]
        policy["sources"].sort(key=lambda item: item["alias"])
        _validate_policy(policy)
        if not any(hub / entry["path"] == root for entry in entries):
            registry["repositories"].append({"path": relative, "management": "native"})
            _write(registry_path, json.dumps(registry, indent=2, ensure_ascii=False).encode() + b"\n",
                   expected_content=registry_bytes)
        _write(policy_path.absolute(), json.dumps(policy, indent=2, ensure_ascii=False).encode() + b"\n",
               expected_content=policy_bytes, must_be_absent=not policy_existed)
    return {"status": "ENROLLED_LOCAL", "source": source, "policy": str(policy_path)}


def install(policy_path: Path, interval: int = 600) -> dict[str, Any]:
    policy = load_policy(policy_path)
    if type(interval) is not int or interval < 60:
        raise KnowledgeError("Interval must be at least 60 seconds")
    state = _state_dir(Path(policy["hub_root"]))
    path = Path.home() / "Library" / "LaunchAgents" / "com.omar.constellation-knowledge-sync.plist"
    plist = {"Label": "com.omar.constellation-knowledge-sync", "ProgramArguments": [sys.executable,
             str(Path(__file__).resolve()), "--policy", str(policy_path.absolute()), "sync"],
             "StartInterval": interval, "RunAtLoad": True, "ProcessType": "Background",
             "StandardOutPath": str(state / "launch-agent.stdout.log"),
             "StandardErrorPath": str(state / "launch-agent.stderr.log")}
    _write(path, plistlib.dumps(plist))
    return {"status": "INSTALLED_NOT_LOADED", "path": str(path), "interval": interval}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--hub", type=Path)
    parser.add_argument("--target", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    export = commands.add_parser("export")
    export.add_argument("--repo", required=True)
    deliver = commands.add_parser("sync")
    deliver.add_argument("--repo")
    register = commands.add_parser("enroll")
    register.add_argument("--repo", required=True)
    register.add_argument("--classification", required=True, choices=["personal", "work"])
    register.add_argument("--local-path", action="append", default=None)
    register.add_argument("--include-path", action="append", default=None)
    register.add_argument("--target", type=Path, dest="enroll_target")
    timer = commands.add_parser("install")
    timer.add_argument("--interval", type=int, default=600)
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = status(args.policy, args.hub)
        elif args.command == "export":
            policy = load_policy(args.policy)
            result = collect_bundle(policy, _choose(policy, args.repo)[0])
        elif args.command == "sync":
            result = sync(args.policy, repo=args.repo)
        elif args.command == "enroll":
            result = enroll(args.policy, args.repo, args.classification, args.local_path, args.hub,
                            args.enroll_target or args.target, args.include_path)
        else:
            result = install(args.policy, args.interval)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 1 if result.get("errors") else 0
    except (KnowledgeError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
