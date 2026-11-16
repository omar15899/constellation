"""Receive complete research documents locally, with verifiable provenance.

The source Git repository remains authoritative. A private write-ahead intent
repairs interrupted imports without overwriting edits outside this service.
This module never commits, pushes, or executes imported documentation.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import secrets
import shutil
import stat
import string
import subprocess
import sys
from typing import Any, Iterable, Iterator
import unicodedata
from urllib.parse import quote, unquote, urlsplit


DOCUMENTS = "11_Documents_and_Reports/Research_Repositories"
ATTACHMENTS = "90_Attachments/Research_Repositories"
DASHBOARD = "17_Dashboards/Research_Repositories.md"
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_REPOSITORY_BYTES = 128 * 1024 * 1024
MAX_BUNDLE_BYTES = 200 * 1024 * 1024
MAX_DOCUMENTS = 10_000
TEXT_EXTENSIONS = {".md", ".rst", ".txt", ".tex", ".bib"}
ASSET_EXTENSIONS = {".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".svg", ".webp"}
DEPENDENCY_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".svg", ".webp"}
DOCUMENT_DIRECTORIES = {"docs", "doc", "documentation", "reports", "research", "papers", "notes", "figures"}
DENIED_DIRECTORIES = {
    "vendor", "vendors", "third_party", "thirdparty", "third-party", "node_modules", "build", "dist", "archive", "archives",
    "sessions", "logs", "transcripts", "conversations", "prompts", "data", "datasets", "raw",
    "private", "secrets", "tests", "fixtures", "docs-vault",
}
DENIED_NAMES = {"agents.md", "claude.md", "skill.md", "review.md", "cmakelists.txt"}
DENIED_WORDS = ("conversation", "transcript", "rollout", "auth", "credentials", "secrets")
ALIAS = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
LOCAL_NAME = re.compile(r"(?:report|diagnostics|sleeve_diagnostics|comparison_\d{4}-\d{2}-\d{2})\.md\Z", re.I)
GIT_CHILD = "import os,sys;os.fchdir(int(sys.argv[1]));os.execvpe(sys.argv[2],sys.argv[2:],os.environ)"
PINNED_ROOTS: ContextVar[dict[Path, int]] = ContextVar("omaros_knowledge_roots", default={})
WRITE_EXPECTATION: ContextVar[tuple[Path, bytes | None, Path | None] | None] = ContextVar(
    "omaros_knowledge_write_expectation", default=None)
ASCII_PUNCTUATION = frozenset(string.punctuation)


class KnowledgeError(ValueError):
    """An import cannot preserve authorization, provenance, or existing files."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def _json_bytes(value: Any) -> bytes:
    return _canonical(value) + b"\n"


def _object(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - (optional or set()):
        raise KnowledgeError("Invalid object fields")
    return value


def _no_symlinks(path: Path) -> None:
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise KnowledgeError("Paths must not traverse symlinks")


@contextmanager
def _directory(path: Path, *, create: bool = False) -> Iterator[int]:
    """Hold each directory component without following replaceable symlinks."""
    if not path.is_absolute():
        raise KnowledgeError("Expected an absolute directory")
    ancestors = [(root, descriptor) for root, descriptor in PINNED_ROOTS.get().items() if path.is_relative_to(root)]
    if ancestors:
        root, pinned = max(ancestors, key=lambda item: len(item[0].parts))
        descriptor = os.dup(pinned)
        parts = path.relative_to(root).parts
    else:
        descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        parts = path.parts[1:]
    try:
        try:
            for part in parts:
                try:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                except FileNotFoundError:
                    if not create:
                        raise
                    try:
                        os.mkdir(part, 0o700, dir_fd=descriptor)
                        os.fsync(descriptor)
                    except FileExistsError:
                        pass
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
        except FileNotFoundError:
            raise
        except OSError as error:
            raise KnowledgeError("Directory traversal must not cross symlinks or non-directories") from error
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def _pinned_root(root: Path) -> Iterator[None]:
    with _directory(root) as descriptor:
        token = PINNED_ROOTS.set({**PINNED_ROOTS.get(), root: descriptor})
        try:
            yield
        finally:
            PINNED_ROOTS.reset(token)


def _lstat(path: Path) -> os.stat_result | None:
    if path in PINNED_ROOTS.get():
        return os.fstat(PINNED_ROOTS.get()[path])
    try:
        with _directory(path.parent) as parent:
            return os.stat(path.name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _read(path: Path, limit: int) -> bytes | None:
    try:
        with _directory(path.parent) as parent:
            return _read_at(parent, path.name, limit)
    except FileNotFoundError:
        return None


def _read_at(parent: int, name: str, limit: int) -> bytes | None:
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise KnowledgeError(f"Cannot safely read {name}") from error
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise KnowledgeError("Only regular files may be read")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise KnowledgeError("File exceeds its size limit")
    return data


def _parse(data: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise KnowledgeError("Duplicate JSON keys are forbidden")
            result[key] = value
        return result

    def constant(_: str) -> Any:
        raise KnowledgeError("Invalid JSON constant")

    try:
        value = json.loads(data, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise KnowledgeError("Invalid JSON input") from error
    if not isinstance(value, dict):
        raise KnowledgeError("JSON input must be an object")
    return value


def _read_json(path: Path, limit: int) -> dict[str, Any]:
    data = _read(path, limit)
    if data is None:
        raise KnowledgeError(f"Required file is absent: {path.name}")
    return _parse(data)


def _relative(value: Any, *, allow_root: bool = False) -> str:
    if allow_root and value == ".":
        return "."
    if (not isinstance(value, str) or not value or "\\" in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise KnowledgeError("Paths must be normalized relative POSIX paths")
    if any(part in {"", ".", ".."} for part in value.split("/")) or PurePosixPath(value).is_absolute():
        raise KnowledgeError("Paths must be normalized relative POSIX paths")
    return value


def _fold_path(value: str) -> str:
    return unicodedata.normalize("NFC", unicodedata.normalize("NFC", value).casefold())


def _validate_paths(names: Iterable[str]) -> None:
    """Reject file/directory aliases on case-insensitive and NFC filesystems."""
    prefixes: dict[str, tuple[str, bool]] = {}
    for name in names:
        parts = _relative(name).split("/")
        for index in range(1, len(parts) + 1):
            original = "/".join(parts[:index])
            folded = _fold_path(original)
            value = (original, index == len(parts))
            if folded in prefixes and prefixes[folded] != value:
                raise KnowledgeError("Document paths or file/directory prefixes collide under NFC and case folding")
            prefixes[folded] = value


def _root(value: Any) -> Path:
    if not isinstance(value, str):
        raise KnowledgeError("Repository roots must be canonical absolute paths")
    path = Path(value)
    _no_symlinks(path)
    if not path.is_absolute() or str(path.resolve()) != value or not path.is_dir():
        raise KnowledgeError("Repository roots must be canonical absolute paths")
    return path


def _git(root: Path, *args: str, input: bytes | None = None) -> bytes:
    # Repository selectors inherited from a hook must not override -C.
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
    try:
        executable = shutil.which("git")
        if executable is None:
            raise KnowledgeError("Git executable is unavailable")
        executable = str(Path(executable).resolve(strict=True))
        # fchdir pins the already opened directory across rename/symlink races.
        # A fixed isolated helper avoids unsafe preexec_fn in threaded callers.
        with _directory(root) as directory:
            process = subprocess.run(
                [sys.executable, "-I", "-S", "-c", GIT_CHILD, str(directory),
                 executable, "--no-optional-locks", "--no-replace-objects", *args],
                input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
                env=environment, pass_fds=(directory,), check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise KnowledgeError("Git verification failed") from error
    if process.returncode:
        raise KnowledgeError("Git verification failed: " + process.stderr.decode("utf-8", "replace").strip()[:500])
    return process.stdout


def _git_owner(path: Path) -> Path:
    return Path(os.fsdecode(_git(path, "rev-parse", "--show-toplevel")).strip()).resolve()


def _check_owner(root: Path, path: Path) -> None:
    if not path.is_relative_to(root):
        raise KnowledgeError("Document path must remain inside its repository")
    # The entry point verifies the root with Git. Descendants can introduce
    # another owner only through a nested Git marker; reject any such marker.
    with _directory(root) as anchor:
        descriptor = os.dup(anchor)
        try:
            for part in path.relative_to(root).parts:
                try:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                except FileNotFoundError:
                    return
                except OSError as error:
                    raise KnowledgeError("Document parents must remain regular directories") from error
                os.close(descriptor)
                descriptor = child
                try:
                    os.stat(".git", dir_fd=descriptor, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise KnowledgeError("Document path belongs to another Git repository")
        finally:
            os.close(descriptor)


def _denied(name: str, *, explicit: bool = False) -> bool:
    parts = PurePosixPath(name).parts
    lower = [part.casefold() for part in parts]
    if (lower[-1] in DENIED_NAMES or any(word in part for part in lower for word in DENIED_WORDS)
            or re.fullmatch(r"(?:requirements|constraints).*\.txt", lower[-1])
            or re.search(r"(?:^|[\W_])prompts?(?:[\W_]|$)", lower[-1])
            or any(part in DENIED_DIRECTORIES for part in lower[:-1])
            or any(a == "docs" and b == "vault" for a, b in zip(lower, lower[1:]))):
        return True
    if parts[-1].startswith(".") and not explicit:
        return True
    hidden = [index for index, part in enumerate(parts[:-1]) if part.startswith(".")]
    if hidden:
        authorized_hidden = explicit and hidden == [0] and (
            parts[0] == ".codex" or parts[:2] == (".claude", "docs"))
        if not authorized_hidden:
            return True
    return False


def _eligible(name: str, *, explicit: bool = False) -> bool:
    if _denied(name, explicit=explicit):
        return False
    path = PurePosixPath(name)
    return path.suffix.casefold() in TEXT_EXTENSIONS or (
        path.suffix.casefold() in ASSET_EXTENSIONS
        and (explicit or any(part.casefold() in DOCUMENT_DIRECTORIES for part in path.parts[:-1])))


def _within(name: str, prefixes: list[str]) -> bool:
    return any(prefix == "." or name.startswith(prefix + "/") for prefix in prefixes)


def _policy(root: Path, path: Path) -> dict[str, Any]:
    policy = _read_json(path.absolute(), 1024 * 1024)
    _object(policy, {"schema_version", "hub_root", "target_root", "sources"})
    if type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        raise KnowledgeError("Unsupported policy schema")
    target = _root(policy["target_root"])
    hub = _root(policy["hub_root"])
    consent = path.absolute().resolve()
    if consent.is_relative_to(hub) or consent.is_relative_to(target):
        raise KnowledgeError("Knowledge authorization must be stored outside source and target repositories")
    if root != target or _git_owner(target) != target or _git_owner(hub) != hub:
        raise KnowledgeError("Policy must identify exact Git repository roots")
    from project_registry import for_hub
    registry = for_hub(hub)
    if (type(registry.get("schema_version")) is not int or registry["schema_version"] != 1
            or not isinstance(registry.get("repositories"), list)):
        raise KnowledgeError("Invalid repository registry")
    native: set[Path] = set()
    for entry in registry["repositories"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise KnowledgeError("Invalid repository registration")
        name = _relative(entry["path"], allow_root=True)
        if entry.get("management") == "native":
            native.add((hub / name).resolve())
    if not isinstance(policy["sources"], list):
        raise KnowledgeError("Policy sources must be a list")
    aliases: set[str] = set()
    roots: set[Path] = set()
    for source in policy["sources"]:
        _object(source, {"root", "alias", "classification"}, {"local_paths", "include_paths"})
        origin = _root(source["root"])
        alias = source["alias"]
        if not isinstance(alias, str) or not ALIAS.fullmatch(alias) or alias in aliases or origin in roots:
            raise KnowledgeError("Source aliases and roots must be unique and exact")
        if not isinstance(source["classification"], str) or source["classification"] not in {"personal", "work"}:
            raise KnowledgeError("Source classification must be explicitly personal or work")
        if origin not in native or not origin.is_relative_to(hub) or _git_owner(origin) != origin or origin == target:
            raise KnowledgeError("Source must be explicitly registered as a native repository")
        for field in ("local_paths", "include_paths"):
            values = source.get(field, [])
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values) or len(values) != len(set(values)):
                raise KnowledgeError("Explicit source paths must be a unique list")
            for value in values:
                _relative(value, allow_root=field == "local_paths")
                if field == "include_paths" and not _eligible(value, explicit=True):
                    raise KnowledgeError("Explicit inclusion cannot authorize forbidden documents")
                if field == "local_paths" and value != "." and _denied(value + "/report.md"):
                    raise KnowledgeError("Local source paths cannot authorize forbidden directories")
        aliases.add(alias)
        roots.add(origin)
    return policy


def _tree(root: Path, revision: str) -> dict[str, tuple[str, str, int]]:
    records: dict[str, tuple[str, str, int]] = {}
    for record in _git(root, "ls-tree", "-r", "-l", "-z", "--full-tree", revision).split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_name = record.split(b"\t", 1)
            mode, kind, oid, size = metadata.split()
            name = raw_name.decode("utf-8")
            _relative(name)
            records[name] = (mode.decode("ascii"), oid.decode("ascii"), int(size) if kind == b"blob" else -1)
        except (ValueError, UnicodeError) as error:
            raise KnowledgeError("Unsupported Git tree path or object") from error
    return records


def _blobs(root: Path, selected: dict[str, tuple[str, str, int]]) -> dict[str, bytes]:
    """Verify one framed Git batch against the exact tree object IDs and sizes."""
    sizes = {oid: size for _, oid, size in selected.values()}
    if not sizes:
        return {}
    output = _git(root, "cat-file", "--batch", input=("\n".join(sizes) + "\n").encode("ascii"))
    offset = 0
    contents: dict[str, bytes] = {}
    for oid, expected_size in sizes.items():
        end = output.find(b"\n", offset)
        if end < 0:
            raise KnowledgeError("Git batch has an incomplete object header")
        try:
            actual_oid, kind, size_text = output[offset:end].decode("ascii").split(" ")
            size = int(size_text)
        except (ValueError, UnicodeError) as error:
            raise KnowledgeError("Git batch has an invalid object header") from error
        if actual_oid != oid or kind != "blob" or size != expected_size or size < 0 or size > MAX_FILE_BYTES:
            raise KnowledgeError("Git batch object identity, type, or size differs from the source tree")
        start = end + 1
        offset = start + size + 1
        if offset > len(output) or output[offset - 1:offset] != b"\n":
            raise KnowledgeError("Git batch object bytes are truncated")
        contents[oid] = output[start:offset - 1]
    if offset != len(output):
        raise KnowledgeError("Git batch contains unexpected trailing bytes")
    return contents


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


def _local_files(root: Path, source: dict[str, Any], tree: dict[str, Any]) -> tuple[dict[str, bytes], set[str]]:
    prefixes = source.get("local_paths", [])
    reports: dict[str, bytes] = {}
    total = 0
    def walk(descriptor: int, parent: str) -> None:
        nonlocal total
        for item in sorted(os.scandir(descriptor), key=lambda entry: entry.name):
            relative = _relative(f"{parent}/{item.name}" if parent else item.name)
            if _denied(relative):
                continue
            info = item.stat(follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                if not _denied(relative + "/report.md"):
                    raise KnowledgeError("Local report trees must not contain symlinks")
                continue
            if stat.S_ISDIR(info.st_mode):
                if _denied(relative + "/report.md"):
                    continue
                _check_owner(root, root / relative)
                child = os.open(item.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                try:
                    walk(child, relative)
                finally:
                    os.close(child)
            elif relative not in tree and relative not in reports and LOCAL_NAME.fullmatch(item.name):
                if not stat.S_ISREG(info.st_mode):
                    raise KnowledgeError("Local reports must be regular files")
                _check_owner(root, (root / relative).parent)
                data = _read(root / relative, MAX_FILE_BYTES)
                if data is None:
                    raise KnowledgeError("Local report disappeared while collecting the bundle")
                total += len(data)
                if total > MAX_REPOSITORY_BYTES or len(reports) >= MAX_DOCUMENTS:
                    raise KnowledgeError("Local reports exceed the repository limits")
                reports[relative] = data

    for prefix in prefixes:
        directory = root / prefix
        info = _lstat(directory)
        if info is None:
            continue
        if not stat.S_ISDIR(info.st_mode):
            raise KnowledgeError("Local paths must designate regular directories")
        _check_owner(root, directory)
        with _directory(directory) as descriptor:
            walk(descriptor, "" if prefix == "." else prefix)
    dependencies: dict[str, bytes] = {}
    tracked_dependencies: set[str] = set()
    for name, content in reports.items():
        try:
            text = content.decode("utf-8")
        except UnicodeError as error:
            raise KnowledgeError("Markdown reports must be UTF-8") from error
        for destination in _inline_destinations(text):
            try:
                link = urlsplit(destination)
                if link.scheme or link.netloc:
                    continue
                reference = unquote(link.path, errors="strict")
                if not reference or reference.startswith("/") or "\\" in reference or any(ord(c) < 32 for c in reference):
                    continue
                relative = _relative(posixpath.normpath(posixpath.join(posixpath.dirname(name), reference)))
            except (KnowledgeError, UnicodeError, ValueError):
                continue
            path = PurePosixPath(relative)
            suffix = path.suffix.casefold()
            if (not _within(relative, prefixes) or _denied(relative)
                    or not (suffix in DEPENDENCY_EXTENSIONS
                            or suffix == ".md" and "tables" in [p.casefold() for p in path.parts[:-1]])):
                continue
            if relative in tree:
                tracked_dependencies.add(relative)
                continue
            if relative in reports or relative in dependencies:
                continue
            candidate = root / relative
            if _lstat(candidate) is None:
                continue
            _check_owner(root, candidate.parent)
            data = _read(candidate, MAX_FILE_BYTES)
            if data is not None:
                total += len(data)
                if total > MAX_REPOSITORY_BYTES or len(reports) + len(dependencies) >= MAX_DOCUMENTS:
                    raise KnowledgeError("Local dependencies exceed the repository limits")
                dependencies[relative] = data
    return {**reports, **dependencies}, tracked_dependencies


def _bundle(root: Path, policy: dict[str, Any], bundle: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bytes]]:
    _object(bundle, {"schema_version", "source", "documents", "bundle_hash"})
    if type(bundle["schema_version"]) is not int or bundle["schema_version"] != 1:
        raise KnowledgeError("Unsupported bundle schema")
    try:
        payload = _canonical({key: value for key, value in bundle.items() if key != "bundle_hash"})
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise KnowledgeError("Bundle must contain canonical JSON data") from error
    if len(payload) > MAX_BUNDLE_BYTES or not isinstance(bundle["bundle_hash"], str) or _digest(payload) != bundle["bundle_hash"]:
        raise KnowledgeError("Bundle hash or size is invalid")
    identity = _object(bundle["source"], {"root", "alias", "revision"})
    source = next((item for item in policy["sources"]
                   if item["root"] == identity["root"] and item["alias"] == identity["alias"]), None)
    if source is None:
        raise KnowledgeError("Source root and alias are not authorized together")
    origin = Path(source["root"])
    revision = identity["revision"]
    if (not isinstance(revision, str) or not REVISION.fullmatch(revision)
            or _git(origin, "rev-parse", "HEAD").decode().strip() != revision):
        raise KnowledgeError("Bundle revision must be the current exact source HEAD")
    tree = _tree(origin, revision)
    included = set(source.get("include_paths", []))
    if included - tree.keys():
        raise KnowledgeError("Explicitly included documents must exist in the source revision")
    selected = {name: item for name, item in tree.items() if _eligible(name, explicit=name in included)}
    local, tracked_dependencies = _local_files(origin, source, tree)
    selected.update({name: tree[name] for name in tracked_dependencies})
    if any(mode not in {"100644", "100755"} or size < 0 for mode, _, size in selected.values()):
        raise KnowledgeError("Git documents must be regular blobs, never symlinks or submodules")
    if any(size > MAX_FILE_BYTES for _, _, size in selected.values()):
        raise KnowledgeError("Git document exceeds its size limit")
    if sum(size for _, _, size in selected.values()) + sum(map(len, local.values())) > MAX_REPOSITORY_BYTES:
        raise KnowledgeError("Selected document bytes exceed the repository limit")
    for name in selected:
        _check_owner(origin, (origin / name).parent)
    blobs = _blobs(origin, selected)
    documents = bundle["documents"]
    if not isinstance(documents, list) or len(documents) > MAX_DOCUMENTS or len(selected) + len(local) > MAX_DOCUMENTS:
        raise KnowledgeError("Document count exceeds its limit")
    expected = set(selected) | set(local)
    _validate_paths(expected)
    contents: dict[str, bytes] = {}
    names: list[str] = []
    collisions: set[str] = set()
    total = 0
    for document in documents:
        _object(document, {"path", "sha256", "content", "origin"})
        name = _relative(document["path"])
        folded = _fold_path(name)
        if folded in collisions:
            raise KnowledgeError("Document names collide under NFC and case folding")
        collisions.add(folded)
        names.append(name)
        encoded = document["content"]
        if not isinstance(encoded, str) or len(encoded) > ((MAX_FILE_BYTES + 2) // 3) * 4:
            raise KnowledgeError("Encoded document exceeds its limit")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise KnowledgeError("Document content is not strict base64") from error
        if len(data) > MAX_FILE_BYTES or document["sha256"] != _digest(data):
            raise KnowledgeError("Document digest or size is invalid")
        if name in selected and document["origin"] == "git":
            _, oid, size = selected[name]
            if len(data) != size or blobs[oid] != data:
                raise KnowledgeError("Document bytes do not match the regular Git blob")
        elif name in local and document["origin"] == "local":
            if local[name] != data:
                raise KnowledgeError("Local document differs from its current authorized file")
        else:
            raise KnowledgeError("Document path or origin is not selected by the policy")
        if PurePosixPath(name).suffix.casefold() == ".md":
            try:
                data.decode("utf-8")
            except UnicodeError as error:
                raise KnowledgeError("Markdown documents must be UTF-8") from error
        total += len(data)
        if total > MAX_REPOSITORY_BYTES:
            raise KnowledgeError("Repository document bytes exceed their limit")
        contents[name] = data
    if names != sorted(names) or set(names) != expected:
        raise KnowledgeError("Bundle must include the complete sorted authorized document set")
    return source, contents


def _state_directory(root: Path) -> Path:
    value = Path(os.fsdecode(_git(root, "rev-parse", "--git-path", "omaros-knowledge")).strip())
    path = value if value.is_absolute() else root / value
    _no_symlinks(path)
    return path


def _destination(root: Path, name: str) -> Path:
    _relative(name)
    if name != DASHBOARD:
        valid = False
        for prefix in (DOCUMENTS, ATTACHMENTS):
            if name.startswith(prefix + "/"):
                tail = name[len(prefix) + 1:].split("/")
                valid = bool(tail and ALIAS.fullmatch(tail[0])) and (
                    prefix == DOCUMENTS and tail[1:] == ["README.md"]
                    or len(tail) >= 3 and tail[1] == "files")
                break
        if not valid:
            raise KnowledgeError("Private state contains an unauthorized destination")
    path = root / name
    _no_symlinks(path)
    for parent in path.parents:
        if parent == root:
            break
        if parent.exists() and not parent.is_dir():
            raise KnowledgeError("Destination parent must be a directory")
    _check_owner(root, path.parent)
    return path


def _empty_manifest() -> dict[str, Any]:
    return {"schema_version": 1, "entries": {}, "managed": {}}


def _manifest(root: Path, directory: Path) -> dict[str, Any]:
    data = _read(directory / "manifest.json", MAX_BUNDLE_BYTES)
    value = _empty_manifest() if data is None else _parse(data)
    return _validate_manifest(root, value)


def _validate_manifest(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    _object(value, {"schema_version", "entries", "managed"})
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1
            or not isinstance(value["entries"], dict) or not isinstance(value["managed"], dict)):
        raise KnowledgeError("Invalid private knowledge manifest; preserve it for recovery")
    _validate_paths(value["managed"])
    for name, digest in value["managed"].items():
        _destination(root, name)
        if not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise KnowledgeError("Invalid managed destination digest")
    for alias, entry in value["entries"].items():
        if not isinstance(alias, str) or not ALIAS.fullmatch(alias) or not isinstance(entry, dict):
            raise KnowledgeError("Invalid private source entry")
        _object(entry, {"root", "classification", "revision", "bundle_hash", "created_at", "received_at", "documents"})
        if (not isinstance(entry["root"], str) or not Path(entry["root"]).is_absolute()
                or not isinstance(entry["classification"], str) or entry["classification"] not in {"personal", "work"}
                or not isinstance(entry["revision"], str) or not REVISION.fullmatch(entry["revision"])
                or not isinstance(entry["bundle_hash"], str) or not HASH.fullmatch(entry["bundle_hash"])
                or any(not isinstance(entry[key], str) or not re.fullmatch(
                    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", entry[key]) for key in ("created_at", "received_at"))):
            raise KnowledgeError("Invalid private source provenance")
        if not isinstance(entry["documents"], dict):
            raise KnowledgeError("Invalid private document index")
        for name, item in entry["documents"].items():
            _relative(name)
            _object(item, {"sha256", "origin", "active"})
            if (not isinstance(item["sha256"], str) or not HASH.fullmatch(item["sha256"])
                    or not isinstance(item["origin"], str) or item["origin"] not in {"git", "local"}
                    or type(item["active"]) is not bool):
                raise KnowledgeError("Invalid private document provenance")
    return value


def _fsync_directory(path: Path) -> None:
    with _directory(path) as descriptor:
        os.fsync(descriptor)


def _atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    with _directory(path.parent, create=True) as parent:
        expectation = WRITE_EXPECTATION.get()
        if expectation is not None and expectation[0] == path:
            _, expected, owner = expectation
        else:
            expected, owner = _read_at(parent, path.name, MAX_BUNDLE_BYTES), None
        if _read_at(parent, path.name, MAX_BUNDLE_BYTES) != expected:
            raise KnowledgeError("Destination changed before its atomic write; preserve it and retry")
        temporary = ".knowledge-" + secrets.token_hex(16)
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, mode, dir_fd=parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fchmod(stream.fileno(), mode)
                os.fsync(stream.fileno())
            if owner is not None:
                _check_owner(owner, path.parent)
            # Observe content again after preparing durable bytes. This preserves
            # an edit seen during preparation; rename is not a filesystem CAS
            # against editors writing after this final observation.
            if _read_at(parent, path.name, MAX_BUNDLE_BYTES) != expected:
                raise KnowledgeError("Destination changed while preparing its atomic write; preserve it and retry")
            os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
            os.fsync(parent)
        finally:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass


def _checked_write(path: Path, data: bytes, mode: int, expected: bytes | None,
                   owner: Path | None = None) -> None:
    token = WRITE_EXPECTATION.set((path, expected, owner))
    try:
        _atomic_write(path, data, mode)
    finally:
        WRITE_EXPECTATION.reset(token)


@contextmanager
def _lock(directory: Path) -> Iterator[None]:
    with _directory(directory, create=True) as parent:
        descriptor = os.open("lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise KnowledgeError("Knowledge lock must be a regular private file")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _frontmatter(title: str, domain: str, created: str, updated: str, *, kind: str = "reference",
                 provenance: dict[str, Any] | None = None) -> bytes:
    fields: dict[str, Any] = {
        "title": title, "note_type": kind, "domain": domain, "subdomain": "Research_Repositories",
        "tags": ["research", "repository_documentation"], "status": "active", "created": created[:10],
        "updated": updated[:10], "author": "Omar", "source": "Constellation knowledge receiver",
    }
    if provenance is not None:
        fields["provenance"] = provenance
    return ("---\n" + "\n".join(key + ": " + json.dumps(value, ensure_ascii=True) for key, value in fields.items())
            + "\n---\n\n").encode("utf-8")


def _visible(alias: str, name: str) -> str:
    return f"{DOCUMENTS}/{alias}/files/{name}"


def _raw(alias: str, name: str) -> str:
    return f"{ATTACHMENTS}/{alias}/files/{name}.source"


def _catalog(alias: str, entry: dict[str, Any]) -> bytes:
    lines = [f"# {alias}", "", "Recepción **LOCAL**; no acredita commit, publicación remota ni revisión intelectual.",
             "", f"Clasificación: {entry['classification']}. Revisión Git: {entry['revision']}.",
             f"Bundle SHA-256: {entry['bundle_hash']}.", "",
             "Se conservan los documentos completos y sus rutas relativas. La fuente Git conserva la autoridad.",
             "Los enlaces externos, código, datos y otras dependencias no seleccionadas pueden faltar en la copia.",
             "Las dependencias locales incorporadas se limitan a imágenes/PDF y tablas Markdown referenciados "
             "directamente por los informes y autorizados por la política; no se descargan enlaces externos.", "",
             "## Documentos activos", ""]
    for name, item in sorted(entry["documents"].items()):
        if item["active"]:
            lines.append(f"- [{name.replace('[', '').replace(']', '')}]({quote('files/' + name, safe='/')}) "
                         f"— {item['origin']}, SHA-256 {item['sha256']}")
    lines.extend(["", "## Retirados de la fuente (archived)", "", "Las copias retiradas se conservan sin borrar ni reescribir.", ""])
    for name, item in sorted(entry["documents"].items()):
        if not item["active"]:
            lines.append(f"- [{name.replace('[', '').replace(']', '')}]({quote('files/' + name, safe='/')}) "
                         f"— SHA-256 {item['sha256']}")
    return _frontmatter(f"Research repository: {alias}", "11_Documents_and_Reports", entry["created_at"],
                        entry["received_at"], kind="index") + ("\n".join(lines) + "\n").encode("utf-8")


def _dashboard(policy: dict[str, Any], manifest: dict[str, Any]) -> bytes:
    entries = manifest["entries"]
    created = min((item["created_at"] for item in entries.values()), default="1970-01-01")
    updated = max((item["received_at"] for item in entries.values()), default=created)
    lines = ["# Research repositories", "", "Constellation centraliza aquí documentación completa de las fuentes autorizadas.",
             "La recepción es **LOCAL**: no afirma commit, publicación remota ni revisión intelectual.", "",
             "Los repositorios fuente conservan la autoridad. Código, datos, enlaces externos y otras dependencias "
             "no seleccionadas pueden faltar; los catálogos detallan el alcance documental.", ""]
    for source in sorted(policy["sources"], key=lambda item: item["alias"]):
        alias = source["alias"]
        entry = entries.get(alias)
        if entry is not None and entry["root"] != source["root"]:
            raise KnowledgeError("A received alias cannot be reassigned to another source")
        if entry is None:
            lines.append(f"- {alias} ({source['classification']}): **pending**; todavía no recibido.")
        else:
            count = sum(item["active"] for item in entry["documents"].values())
            link = "../" + DOCUMENTS + "/" + alias + "/README.md"
            lines.append(f"- [{alias}]({link}) ({source['classification']}): **RECEIVED_LOCAL**, "
                         f"{count} documentos, revisión {entry['revision']}; {entry['received_at']}.")
    return _frontmatter("Research repositories", "17_Dashboards", created, updated, kind="dashboard") + (
        "\n".join(lines) + "\n").encode("utf-8")


def _plan(root: Path, policy: dict[str, Any], source: dict[str, Any], bundle: dict[str, Any],
          contents: dict[str, bytes], manifest: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    alias = source["alias"]
    previous = manifest["entries"].get(alias)
    revision = bundle["source"]["revision"]
    if previous is not None:
        if previous["root"] != source["root"]:
            raise KnowledgeError("A received alias cannot be reassigned to another source")
        if previous["revision"] != revision:
            _git(Path(source["root"]), "merge-base", "--is-ancestor", previous["revision"], revision)
    unchanged = previous is not None and previous["bundle_hash"] == bundle["bundle_hash"]
    now = previous["received_at"] if unchanged else datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    documents = deepcopy(previous["documents"]) if previous else {}
    _validate_paths(documents.keys() | contents.keys())
    for item in documents.values():
        item["active"] = False
    for item in bundle["documents"]:
        documents[item["path"]] = {"sha256": item["sha256"], "origin": item["origin"], "active": True}
    entry = {"root": source["root"], "classification": source["classification"], "revision": revision,
             "bundle_hash": bundle["bundle_hash"], "created_at": previous["created_at"] if previous else now,
             "received_at": now, "documents": documents}
    proposed = deepcopy(manifest)
    proposed["entries"][alias] = entry
    rendered: dict[str, bytes] = {}
    for name, data in contents.items():
        visible = _visible(alias, name)
        if PurePosixPath(name).suffix.casefold() == ".md":
            raw = _raw(alias, name)
            provenance = {"repository": alias, "path": name, "revision": revision,
                          "sha256": documents[name]["sha256"], "origin": documents[name]["origin"]}
            raw_link = quote(posixpath.relpath(raw, posixpath.dirname(visible)), safe="/")
            prefix = _frontmatter(f"{alias}: {name}", "11_Documents_and_Reports", entry["created_at"], now,
                                  provenance=provenance)
            prefix += (f"> Fuente: {alias}/{name} · Git {revision} · "
                       f"SHA-256 {documents[name]['sha256']} · origen {documents[name]['origin']}.\n"
                       f"> [Bytes originales]({raw_link}). Recepción LOCAL; la fuente conserva la autoridad.\n\n").encode("utf-8")
            rendered[raw] = data
            rendered[visible] = prefix + data
        else:
            rendered[visible] = data
    rendered[f"{DOCUMENTS}/{alias}/README.md"] = _catalog(alias, entry)
    rendered[DASHBOARD] = _dashboard(policy, proposed)
    _validate_paths(proposed["managed"].keys() | rendered.keys())
    for name, data in rendered.items():
        proposed["managed"][name] = _digest(data)
    receipt = {"schema_version": 1, "status": "RECEIVED_LOCAL", "bundle_hash": bundle["bundle_hash"],
               "alias": alias, "revision": revision, "count": len(contents), "changed": [], "at": now}
    return rendered, proposed, receipt


def _preflight(root: Path, rendered: dict[str, bytes], manifest: dict[str, Any]) -> dict[str, bytes | None]:
    previous: dict[str, bytes | None] = {}
    for name in rendered:
        path = _destination(root, name)
        data = _read(path, MAX_BUNDLE_BYTES)
        expected = manifest["managed"].get(name)
        if expected is None and data is not None:
            raise KnowledgeError("Destination is not owned by this receiver; existing content is preserved")
        if expected is not None and (data is None or _digest(data) != expected):
            raise KnowledgeError("Managed destination changed manually; existing content is preserved")
        previous[name] = data
    return previous


def _snapshot(data: bytes | None, mode: int = 0o644) -> dict[str, Any] | None:
    return None if data is None else {"sha256": _digest(data), "content": base64.b64encode(data).decode("ascii"), "mode": mode}


def _snapshot_bytes(value: Any) -> bytes | None:
    if value is None:
        return None
    _object(value, {"sha256", "content", "mode"})
    if not isinstance(value["content"], str) or len(value["content"]) > MAX_BUNDLE_BYTES * 2:
        raise KnowledgeError("Invalid recovery content")
    try:
        data = base64.b64decode(value["content"], validate=True)
    except (ValueError, binascii.Error) as error:
        raise KnowledgeError("Invalid recovery bytes") from error
    if _digest(data) != value["sha256"] or type(value["mode"]) is not int or value["mode"] & ~0o777:
        raise KnowledgeError("Invalid recovery digest or file mode")
    return data


def _pending(root: Path, directory: Path, policy: dict[str, Any], *, apply: bool) -> dict[str, Any] | None:
    data = _read(directory / "pending.json", 1024 * 1024 * 1024)
    if data is None:
        return None
    pending = _parse(data)
    _object(pending, {"schema_version", "writes", "manifest_before", "manifest_after", "receipt", "policy_hash"})
    if type(pending["schema_version"]) is not int or pending["schema_version"] != 1 or not isinstance(pending["writes"], list):
        raise KnowledgeError("Invalid interrupted knowledge transaction")
    if pending["policy_hash"] != _digest(_canonical(policy)):
        raise KnowledgeError("Policy changed during an interrupted import; preserve the intent for explicit recovery")
    actual_manifest = _read(directory / "manifest.json", MAX_BUNDLE_BYTES)
    expected_manifest = _snapshot_bytes(pending["manifest_before"])
    after_manifest = _snapshot_bytes(pending["manifest_after"])
    if after_manifest is None or actual_manifest not in (expected_manifest, after_manifest):
        raise KnowledgeError("Manifest changed outside the interrupted transaction; preserve it for recovery")
    proposed = _validate_manifest(root, _parse(after_manifest))
    prior = _validate_manifest(root, _parse(expected_manifest)) if expected_manifest is not None else _empty_manifest()
    writes: list[tuple[Path, bytes | None, bytes, int]] = []
    seen: set[str] = set()
    for item in pending["writes"]:
        _object(item, {"path", "before", "after"})
        name = item["path"]
        path = _destination(root, name)
        if name in seen:
            raise KnowledgeError("Duplicate recovery destination")
        seen.add(name)
        before = _snapshot_bytes(item["before"])
        after = _snapshot_bytes(item["after"])
        actual = _read(path, MAX_BUNDLE_BYTES)
        if (after is None or actual not in (before, after)
                or proposed["managed"].get(name) != _digest(after)
                or prior["managed"].get(name) != (_digest(before) if before is not None else None)):
            raise KnowledgeError("Interrupted destination has a third, manual state; all content is preserved")
        writes.append((path, before, after, item["after"]["mode"]))
    if apply:
        for path, before, after, mode in writes:
            actual = _read(path, MAX_BUNDLE_BYTES)
            if actual not in (before, after):
                raise KnowledgeError("Destination changed during recovery; preserve it and retry")
            if actual != after:
                _checked_write(path, after, mode, before, root)
        if actual_manifest != after_manifest:
            _checked_write(directory / "manifest.json", after_manifest, 0o600, actual_manifest)
        with _directory(directory) as descriptor:
            os.unlink("pending.json", dir_fd=descriptor)
            os.fsync(descriptor)
    return proposed


def _prepare(root: Path, policy_path: Path, bundle: dict[str, Any]) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, bytes]]:
    root = _root(str(root))
    policy = _policy(root, policy_path)
    source, contents = _bundle(root, policy, bundle)
    return root, policy, source, contents


@contextmanager
def _authorized_scope(root: Path, policy_path: Path, bundle: dict[str, Any]) -> Iterator[None]:
    """Pin the source, hub, and vault before their authorization checks."""
    root = _root(str(root))
    policy = _read_json(policy_path.absolute(), 1024 * 1024)
    _object(policy, {"schema_version", "hub_root", "target_root", "sources"})
    identity = _object(bundle.get("source") if isinstance(bundle, dict) else None, {"root", "alias", "revision"})
    if not isinstance(policy["sources"], list) or not any(
            isinstance(item, dict) and item.get("root") == identity["root"] and item.get("alias") == identity["alias"]
            for item in policy["sources"]):
        raise KnowledgeError("Source root and alias require explicit consent before opening")
    hub = _root(policy["hub_root"])
    target = _root(policy["target_root"])
    source = _root(identity["root"])
    if target != root:
        raise KnowledgeError("Policy authorizes a different vault")
    with ExitStack() as stack:
        for directory in (root, hub, source):
            stack.enter_context(_pinned_root(directory))
        yield


def planned_paths(root: Path, policy_path: Path, bundle: dict[str, Any]) -> list[str]:
    """Return potential public destinations without creating files or locks."""
    with _authorized_scope(root, policy_path, bundle):
        return _planned_paths(root, policy_path, bundle)


def _planned_paths(root: Path, policy_path: Path, bundle: dict[str, Any]) -> list[str]:
    root, policy, source, contents = _prepare(root, policy_path, bundle)
    directory = _state_directory(root)
    recovered = _pending(root, directory, policy, apply=False)
    manifest = recovered if recovered is not None else _manifest(root, directory)
    rendered, _, _ = _plan(root, policy, source, bundle, contents, manifest)
    # Interrupted writes are validated against both snapshots by _pending.
    # Actual import completes that intent before applying this new plan.
    if recovered is None:
        _preflight(root, rendered, manifest)
    pending_data = _read(directory / "pending.json", 1024 * 1024 * 1024)
    recovery_paths = {item["path"] for item in _parse(pending_data)["writes"]} if pending_data is not None else set()
    return sorted(rendered.keys() | recovery_paths)


def import_bundle(root: Path, policy_path: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    """Receive one complete authorized source under a global recoverable lock."""
    with _authorized_scope(root, policy_path, bundle):
        return _import_bundle(root, policy_path, bundle)


def _import_bundle(root: Path, policy_path: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    root = _root(str(root))
    policy = _policy(root, policy_path)
    directory = _state_directory(root)
    with _lock(directory):
        if _policy(root, policy_path) != policy:
            raise KnowledgeError("Policy changed while waiting for the receiver lock")
        source, contents = _bundle(root, policy, bundle)
        _pending(root, directory, policy, apply=True)
        manifest = _manifest(root, directory)
        rendered, proposed, receipt = _plan(root, policy, source, bundle, contents, manifest)
        previous = _preflight(root, rendered, manifest)
        changed = sorted(name for name, data in rendered.items() if previous[name] != data)
        receipt["changed"] = changed
        if not changed and proposed == manifest:
            return receipt
        # Recheck live permission and source bytes before making intent durable.
        if _policy(root, policy_path) != policy:
            raise KnowledgeError("Policy changed while preparing the import")
        _bundle(root, policy, bundle)
        writes = []
        for name in changed:
            target = _destination(root, name)
            info = _lstat(target)
            mode = stat.S_IMODE(info.st_mode) if info is not None else 0o644
            writes.append({"path": name, "before": _snapshot(previous[name], mode),
                           "after": _snapshot(rendered[name], mode)})
        pending = {"schema_version": 1, "writes": writes,
                   "manifest_before": _snapshot(_read(directory / "manifest.json", MAX_BUNDLE_BYTES), 0o600),
                   "manifest_after": _snapshot(_json_bytes(proposed), 0o600), "receipt": receipt,
                   "policy_hash": _digest(_canonical(policy))}
        _checked_write(directory / "pending.json", _json_bytes(pending), 0o600, None)
        _pending(root, directory, policy, apply=True)
        return receipt


def _status(root: Path, policy_path: Path) -> dict[str, Any]:
    root = _root(str(root))
    policy = _policy(root, policy_path)
    directory = _state_directory(root)
    manifest = _manifest(root, directory)
    return {"schema_version": 1, "scope": "LOCAL", "pending_recovery": (directory / "pending.json").exists(),
            "sources": [{"alias": source["alias"], "classification": source["classification"],
                         "status": "RECEIVED_LOCAL" if source["alias"] in manifest["entries"] else "pending",
                         "revision": manifest["entries"].get(source["alias"], {}).get("revision"),
                         "count": sum(item["active"] for item in manifest["entries"].get(
                             source["alias"], {}).get("documents", {}).values())} for source in policy["sources"]]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=Path.home() / "OmarOS")
    parser.add_argument("command", choices=("paths", "import", "status"))
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result: Any = _status(args.root, args.policy)
        else:
            data = sys.stdin.buffer.read(MAX_BUNDLE_BYTES + 1)
            if len(data) > MAX_BUNDLE_BYTES:
                raise KnowledgeError("Bundle JSON exceeds its bounded input limit")
            bundle = _parse(data)
            result = (planned_paths(args.root, args.policy, bundle) if args.command == "paths"
                      else import_bundle(args.root, args.policy, bundle))
        sys.stdout.buffer.write(_json_bytes(result))
        return 0
    except (KnowledgeError, OSError) as error:
        print(f"knowledge import: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
