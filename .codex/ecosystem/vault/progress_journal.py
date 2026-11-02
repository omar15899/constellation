"""Import deliberately curated progress into the vault without publishing it.

The local policy and explicit source-root argument identify the authorized
personal source. An envelope's content hash detects drift, not authorship.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
from typing import Any, Callable, Iterator


POLICY_PATH = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "progress-journal.json"
DASHBOARD_PATH = "17_Dashboards/Constellation.md"


class JournalError(ValueError):
    """The import cannot preserve scope, provenance, or existing vault content."""


def read_policy(path: Path) -> dict[str, Any]:
    path = path.absolute()
    with Directory.open(path.parent) as owner:
        version = owner.read(path.name, max_bytes=1024 * 1024)
        if version is None:
            raise JournalError("An explicit local progress policy is required")
        owner.verify()
        value = json.loads(version.content)
    if not isinstance(value, dict):
        raise JournalError("Progress policy must be a JSON object")
    return value


def _component(name: str) -> None:
    if not isinstance(name, str) or not name or name in {".", ".."} or "/" in name or "\x00" in name:
        raise JournalError("Journal operations require a single path component.")


def _directory_fd(path: Path, *, create: bool = False) -> int:
    """Open every directory from the filesystem root without following links."""
    if os.name != "posix" or path.anchor != "/" or ".." in path.parts:
        raise JournalError("Journal directories require normalized, absolute POSIX paths.")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open("/", flags)
    try:
        for name in path.parts[1:]:
            try:
                child = os.open(name, flags, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(name, 0o755, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
                child = os.open(name, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _identity(info: os.stat_result) -> list[int]:
    return [info.st_dev, info.st_ino]


def _observation(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


@dataclass(frozen=True)
class FileVersion:
    """One stable regular-file observation for the private transaction record."""
    content: bytes
    token: dict[str, int | str]


@lru_cache(maxsize=2)
def _rename_api(platform: str):
    """Bind a dirfd-relative atomic rename; missing support is a hard failure."""
    symbol = {"darwin": "renameatx_np", "linux": "renameat2"}.get(platform)
    if symbol is None:
        raise JournalError("Atomic journal promotion is unsupported on this platform.")
    try:
        function = getattr(ctypes.CDLL(None, use_errno=True), symbol)
    except AttributeError:
        raise JournalError("The system library lacks atomic journal promotion.") from None
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    return function


def _rename_at(src_fd: int, source: str, dst_fd: int, target: str, *, exchange: bool) -> None:
    _component(source)
    _component(target)
    if type(exchange) is not bool:
        raise JournalError("Invalid journal promotion operation.")
    platform = sys.platform
    function = _rename_api(platform)
    flag = 2 if exchange else (4 if platform == "darwin" else 1)
    if function(src_fd, os.fsencode(source), dst_fd, os.fsencode(target), flag):
        code = ctypes.get_errno()
        if code == errno.EXDEV:
            raise JournalError("Atomic journal writes require the vault and private Git state on the same filesystem.")
        if code in {errno.EEXIST, errno.ENOENT}:
            raise JournalError("Journal promotion found an unexpected existing or missing file.")
        raise JournalError("The filesystem rejected atomic journal promotion.")


@dataclass(frozen=True)
class Directory:
    """A held directory object's operations are independent of renames of its path."""
    fd: int
    path: Path
    identity: list[int]

    @classmethod
    @contextmanager
    def open(cls, path: Path, *, create: bool = False) -> Iterator["Directory"]:
        try:
            fd = _directory_fd(path, create=create)
        except OSError:
            raise JournalError("Cannot open a journal directory without following aliases.") from None
        try:
            directory = cls(fd, path, _identity(os.fstat(fd)))
            directory.verify()
            yield directory
        finally:
            os.close(fd)

    def verify(self) -> None:
        """Check whether the canonical name still reaches this held directory."""
        try:
            current = _directory_fd(self.path)
            try:
                if _identity(os.fstat(current)) == self.identity:
                    return
            finally:
                os.close(current)
        except OSError:
            pass
        raise JournalError("Journal directory was replaced or detached; preserve the pending transaction.")

    def read(self, name: str, *, max_bytes: int | None = None) -> FileVersion | None:
        """Read through the held object, including during recovery after detachment."""
        _component(name)
        try:
            before = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        except OSError:
            raise JournalError("Cannot inspect a journal file.") from None
        if max_bytes is not None and before.st_size > max_bytes:
            raise JournalError("Journal file exceeds its allowed size")
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise JournalError("Journal files must be regular and singly linked.")
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        try:
            with os.fdopen(os.open(name, flags, dir_fd=self.fd), "rb") as stream:
                opened = os.fstat(stream.fileno())
                if _observation(opened) != _observation(before):
                    raise JournalError("Journal file changed while it was opened.")
                content = stream.read(before.st_size + 1)
                after = os.fstat(stream.fileno())
                named = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
                if (len(content) != before.st_size or _observation(after) != _observation(before)
                        or _observation(named) != _observation(before)):
                    raise JournalError("Journal file changed during the read.")
        except OSError:
            raise JournalError("Cannot read a stable journal file.") from None
        return FileVersion(content, {
            "dev": before.st_dev, "ino": before.st_ino, "mode": stat.S_IMODE(before.st_mode),
            "sha256": hashlib.sha256(content).hexdigest(),
        })

    def _private(self) -> None:
        info = os.fstat(self.fd)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise JournalError("Journal staging requires a private directory owned by the current user.")

    def stage(self, content: bytes, mode: int) -> tuple[str, FileVersion]:
        """Create and flush a recoverable private file before recording its inode."""
        self._private()
        self.verify()
        if type(mode) is not int or mode < 0 or mode > 0o777:
            raise JournalError("Invalid journal output permissions.")
        name = ".progress-" + secrets.token_hex(16)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            with os.fdopen(os.open(name, flags, 0o600, dir_fd=self.fd), "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fchmod(stream.fileno(), mode)
                os.fsync(stream.fileno())
                identity = _identity(os.fstat(stream.fileno()))
            os.fsync(self.fd)
        except OSError:
            raise JournalError("Private journal staging could not be completed.") from None
        version = self.read(name)
        if (version is None or version.content != content or version.token["mode"] != mode
                or [version.token["dev"], version.token["ino"]] != identity):
            raise JournalError("The staged journal object changed; preserve it for recovery.")
        self.verify()
        return name, version

    def unlink(self, name: str, expected: dict[str, int | str]) -> None:
        """Retire only an identified private spool object under the workflow lock."""
        self._private()
        self.verify()
        if re.fullmatch(r"\.progress-[0-9a-f]{32}", name) is None:
            raise JournalError("Refusing to remove a non-spool journal object.")
        version = self.read(name)
        if version is None:
            return
        if version.token != expected:
            raise JournalError("Private journal file changed; preserve it for recovery.")
        # Capture the entry under a fresh exclusive name before removing it.
        # A replacement raced into the original name remains there untouched.
        retired = ".progress-" + secrets.token_hex(16)
        _rename_at(self.fd, name, self.fd, retired, exchange=False)
        try:
            os.fsync(self.fd)
            self.verify()
            version = self.read(retired)
            if version is None or version.token != expected:
                raise JournalError("Private journal file changed during retirement.")
        except (JournalError, OSError):
            restore_pinned(self, retired, self, name, exchange=False)
            raise
        os.unlink(retired, dir_fd=self.fd)
        os.fsync(self.fd)


def restore_pinned(src: Directory, source_name: str, dst: Directory, dest_name: str, *, exchange: bool) -> None:
    """Promote or restore against already-held directories, even after detachment."""
    if src.identity == dst.identity and source_name == dest_name:
        raise JournalError("Journal promotion requires different entries.")
    _rename_at(src.fd, source_name, dst.fd, dest_name, exchange=exchange)
    os.fsync(dst.fd)
    if dst.identity != src.identity:
        os.fsync(src.fd)


def transplant(src: Directory, source_name: str, dst: Directory, dest_name: str, *, exchange: bool) -> None:
    """Install exclusively or exchange atomically, preserving the displaced object.

    An error after the syscall may mean it succeeded. Recovery observes both
    pinned entries and their recorded identities before taking another action.
    """
    src.verify()
    dst.verify()
    restore_pinned(src, source_name, dst, dest_name, exchange=exchange)
    src.verify()
    dst.verify()


def _token(version: FileVersion | None) -> dict[str, Any] | None:
    return version.token if version is not None else None


def _observed(directory: Directory, leaf: str) -> dict[str, Any] | None:
    return _token(directory.read(leaf))


def _same_parent(directory: Directory, expected: list[int]) -> None:
    directory.verify()
    if directory.identity != expected:
        raise JournalError("Journal directory changed since the intent was recorded; preserve it for recovery")


def _restore_if_ours(owner: Directory, leaf: str, private: Directory, plan: dict) -> None:
    """Restore a contested destination only while it still contains our own inode.

    Exchange preserves the displaced entry, even if an unrelated writer won the
    original rename race. A missing spool means an exclusive creation can move
    back to the private slot. Directory aliases are never resolved during undo.
    """
    if _observed(owner, leaf) != plan["after"]:
        return
    temp = plan["spool"]
    restore_pinned(owner, leaf, private, temp, exchange=plan["before"] is not None)
    if _observed(private, temp) != plan["after"]:
        raise JournalError("Another writer changed the journal during restoration; retain the pending evidence")


def _ready(owner: Directory, leaf: str, private: Directory, plan: dict) -> bool:
    """Check durable predecessor, successor and displaced-file evidence."""
    _same_parent(owner, plan["parent"])
    private.verify()
    actual = _observed(owner, leaf)
    if actual == plan["after"]:
        if plan["spool"] is not None:
            try:
                displaced = _observed(private, plan["spool"])
                if displaced is not None and displaced != plan["before"]:
                    raise JournalError("A concurrent journal file was displaced")
            except (JournalError, OSError):
                _restore_if_ours(owner, leaf, private, plan)
                raise
        return True
    if (actual != plan["before"] or plan["spool"] is None
            or _observed(private, plan["spool"]) != plan["after"]):
        raise JournalError("Journal file or private staging changed concurrently; preserve it and retry the same envelope")
    return False


def _publish_version(owner: Directory, leaf: str, private: Directory, plan: dict) -> None:
    if _ready(owner, leaf, private, plan):
        return
    try:
        transplant(private, plan["spool"], owner, leaf, exchange=plan["before"] is not None)
        if not _ready(owner, leaf, private, plan):
            raise JournalError("Journal promotion did not install the prepared version")
    except (JournalError, OSError) as exc:
        # A post-syscall identity check can fail after the exchange has already
        # completed. Undo through pinned descriptors where the new inode is ours.
        _restore_if_ours(owner, leaf, private, plan)
        if isinstance(exc, OSError) and exc.errno == errno.EXDEV:
            raise JournalError("Atomic journal writes require the vault and private Git state on the same filesystem") from exc
        raise


def _stage_plan(owner: Directory, existing: FileVersion | None, private: Directory,
                content: bytes, mode: int) -> dict[str, Any]:
    before = _token(existing)
    if existing is not None and existing.content == content and before["mode"] == mode:
        return {"parent": owner.identity, "before": before, "after": before, "spool": None}
    spool, version = private.stage(content, mode)
    return {"parent": owner.identity, "before": before, "after": version.token, "spool": spool}


def _cleanup(private: Directory, plan: dict) -> None:
    temp = plan["spool"]
    if temp is None:
        return
    displaced = _observed(private, temp)
    if displaced is not None:
        if displaced != plan["before"]:
            raise JournalError("Unexpected contents in the private journal slot; preserve them for recovery")
        private.unlink(temp, displaced)


def _write(path: Path, content: bytes, mode: int, *, staging_directory: Path | None = None,
           publication: tuple[Directory, Directory, dict] | None = None) -> None:
    """Write to a pinned owner and never discard an unexpectedly replaced entry."""
    if publication is not None:
        owner, private, plan = publication
        _publish_version(owner, path.name, private, plan)
        return
    with Directory.open(path.parent, create=True) as owner, Directory.open(staging_directory or path.parent) as private:
        existing = owner.read(path.name)
        plan = _stage_plan(owner, existing, private, content, mode)
        _publish_version(owner, path.name, private, plan)
        _cleanup(private, plan)


def _validate_plans(plans: Any, paths: list[str]) -> None:
    """Only private slots produced by this writer can be consulted or cleaned."""
    if not isinstance(plans, dict) or set(plans) != set(paths):
        raise JournalError("Invalid pending journal targets; retain the index for recovery")
    for plan in plans.values():
        if (not isinstance(plan, dict) or set(plan) != {"parent", "before", "after", "spool"}
                or not isinstance(plan["parent"], list) or len(plan["parent"]) != 2
                or any(type(n) is not int or n < 0 for n in plan["parent"])):
            raise JournalError("Invalid pending journal directory identity")
        for version in (plan["before"], plan["after"]):
            if version is None and version is plan["before"]:
                continue
            if (not isinstance(version, dict) or set(version) != {"dev", "ino", "mode", "sha256"}
                    or any(type(version[k]) is not int or version[k] < 0 for k in ("dev", "ino", "mode"))
                    or not isinstance(version["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", version["sha256"])):
                raise JournalError("Invalid pending journal file identity")
        if (plan["after"] is None or (plan["spool"] is None and plan["after"] != plan["before"])
                or (plan["spool"] is not None and (not isinstance(plan["spool"], str)
                    or not re.fullmatch(r"\.progress-[0-9a-f]{32}", plan["spool"])))):
            raise JournalError("Invalid private staging name in pending journal")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _read_index(version: FileVersion | None) -> dict[str, Any]:
    if version is None:
        return {"schema_version": 1, "entries": {}, "pending": None}
    value = json.loads(version.content)
    if (not isinstance(value, dict) or set(value) != {"schema_version", "entries", "pending"}
            or type(value["schema_version"]) is not int or value["schema_version"] != 1
            or not isinstance(value["entries"], dict)):
        raise JournalError("Invalid private journal index; preserve it for recovery")
    return value


def _save_index(private: Directory, expected: dict | None, data: dict) -> dict:
    leaf = "progress-journal.json"
    current = private.read(leaf)
    if _token(current) != expected:
        raise JournalError("Private journal index changed during this transaction")
    content = _json_bytes(data)
    plan = _stage_plan(private, current, private, content, 0o600)
    _write(private.path / leaf, content, 0o600, publication=(private, private, plan))
    _cleanup(private, plan)
    return plan["after"]


def authorized_paths(envelope: dict[str, Any], *, source_root: Path,
                     policy: dict[str, Any], progress: Any,
                     target_root: Path) -> tuple[dict[str, Any], list[str]]:
    envelope = progress.validate_envelope(envelope)
    progress.validate_policy(policy, source_root=source_root, source_alias=envelope["source_alias"])
    if envelope["target_root_hash"] != progress.target_root_hash(target_root):
        raise JournalError("Envelope is authorized for a different journal destination")
    if Path(policy["target"]["root"]) != target_root.resolve():
        raise JournalError("Local policy does not authorize this journal destination")
    return envelope, [envelope["note_path"], DASHBOARD_PATH]


def receive(workflow: Any, envelope: dict[str, Any], *, source_root: Path,
            policy: dict[str, Any], progress: Any,
            validate_path: Callable[[Path, str], str],
            validate_blob: Callable[[Path, str, bytes], list[str]]) -> dict[str, Any]:
    """Synchronize two declared notes under the caller's existing workflow lock.

    The private pending intent is durable before either note changes. Replaying
    the same envelope repairs a partial write, and a completed identical replay
    does not touch the notes, operational state, or Git index.
    """
    envelope, paths = authorized_paths(envelope, source_root=source_root, policy=policy, progress=progress,
                                       target_root=workflow.root)
    state = workflow.load()
    if state.get("sync_error"):
        raise JournalError(f"Resolve the workflow synchronization blocker before importing: {state['sync_error']}")
    workflow.ensure_target(state)
    if not set(paths) <= set(state.get("paths", [])):
        raise JournalError("Declare both journal paths in the active OmarOS plan before importing")
    for name in paths:
        validate_path(workflow.root, name)
    with Directory.open(workflow.home) as private:
        version = private.read("progress-journal.json")
        index_token = _token(version)
        index = _read_index(version)
        uid = envelope["task_uid"]
        content_hash = envelope["content_hash"]
        origin = str(source_root.resolve())
        entry = index["entries"].get(uid)
        dashboard_entry = progress.dashboard_entry(envelope)
        milestone_hashes = [hashlib.sha256(_json_bytes(item)).hexdigest() for item in envelope["milestones"]]
        snapshot_hash = hashlib.sha256(_json_bytes(envelope["snapshot"])).hexdigest()
        if entry is not None:
            if (not isinstance(entry, dict) or set(entry) != {
                    "source_root", "dashboard", "milestone_hashes", "snapshot_hash", "received_at"}
                    or not isinstance(entry["dashboard"], dict)
                    or not isinstance(entry["milestone_hashes"], list)):
                raise JournalError("Invalid private journal entry; preserve it for recovery")
            previous = entry["dashboard"]
            immutable = ("task_uid", "source_alias", "note_path", "created_at", "target_root_hash")
            if entry["source_root"] != origin or any(previous.get(key) != dashboard_entry[key] for key in immutable):
                raise JournalError("Task identity already belongs to another source, destination or creation date")
            previous_hashes = entry["milestone_hashes"]
            if (milestone_hashes[:len(previous_hashes)] != previous_hashes
                    or (len(milestone_hashes) == len(previous_hashes) and entry["snapshot_hash"] != snapshot_hash)):
                raise JournalError("Journal history cannot regress or replace an accepted milestone")
            if (len(milestone_hashes) == len(previous_hashes)
                    and previous["workflow_finished"] and not envelope["workflow_finished"]):
                raise JournalError("Reopening a finished task requires a new explicit checkpoint")
        pending = index["pending"]
        intent = {"task_uid": uid, "content_hash": content_hash, "source_root": origin}
        if pending is not None and (not isinstance(pending, dict)
                or set(pending) not in (set(intent), set(intent) | {"targets"})
                or any(pending.get(key) != value for key, value in intent.items())):
            raise JournalError("Replay the interrupted journal envelope before importing another milestone")
        proposed = dict(index["entries"])
        unchanged = entry is not None and entry["dashboard"]["content_hash"] == content_hash
        received_at = (entry["received_at"] if unchanged else
                       datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"))
        if received_at < envelope["milestones"][-1]["at"]:
            raise JournalError("Milestone timestamp is in the future; correct the source clock before importing")
        proposed[uid] = {"source_root": origin, "dashboard": dashboard_entry,
                         "milestone_hashes": milestone_hashes, "snapshot_hash": snapshot_hash,
                         "received_at": received_at}
        # Pin both public names before reading or rendering either existing file.
        # Private slots identify both sides of an atomic replacement across retries.
        with ExitStack() as handles:
            owners = {name: handles.enter_context(Directory.open((workflow.root / name).parent, create=True))
                      for name in paths}
            existing = {name: owner.read(Path(name).name) for name, owner in owners.items()}
            note, dashboard = (v.content.decode("utf-8") if v else None for v in existing.values())
            rendered = {
                paths[0]: progress.render_note(envelope, existing=note).encode(),
                paths[1]: progress.render_dashboard([item["dashboard"] for item in proposed.values()], existing=dashboard).encode(),
            }
            for name, content in rendered.items():
                errors = validate_blob(workflow.root, name, content)
                if errors:
                    raise JournalError("Journal metadata failed validation: " + "; ".join(errors))
            receipt = {"task_uid": uid, "content_hash": content_hash, "status": "RECEIVED_LOCAL",
                       "target_root_hash": envelope["target_root_hash"], "note_path": paths[0], "at": received_at}
            if pending is None and unchanged and all(existing[n] and existing[n].content == rendered[n] for n in paths):
                for name in paths:
                    owners[name].verify()
                    if _observed(owners[name], Path(name).name) != existing[name].token:
                        raise JournalError("Journal changed before confirming its local receipt")
                return receipt

            recovering = pending is not None and "targets" in pending
            if recovering:
                plans = pending["targets"]
            else:
                plans = {}
                try:
                    for name in paths:
                        before = existing[name]
                        mode = before.token["mode"] if before else 0o644
                        plans[name] = _stage_plan(owners[name], before, private, rendered[name], mode)
                except (JournalError, OSError):
                    for plan in plans.values():
                        if plan["spool"] is not None:
                            private.unlink(plan["spool"], plan["after"])
                    raise
            _validate_plans(plans, paths)
            prepared = {"schema_version": 1, "entries": proposed,
                        "pending": {**intent, "targets": plans}}
            # An interrupted import must first restore its authorized parent names
            # and present the identical envelope. Never overwrite a foreign worktree.
            for name in paths:
                if plans[name]["after"]["sha256"] != hashlib.sha256(rendered[name]).hexdigest():
                    raise JournalError("Journal rendering changed since the pending intent; preserve files for recovery")
                _ready(owners[name], Path(name).name, private, plans[name])
            if not recovering:
                index_token = _save_index(private, index_token, prepared)
            for name in paths:
                owner, plan = owners[name], plans[name]
                if _ready(owner, Path(name).name, private, plan):
                    continue
                workflow.ensure_target(state)
                validate_path(workflow.root, name)
                _write(workflow.root / name, rendered[name], plan["after"]["mode"],
                       staging_directory=workflow.home, publication=(owner, private, plan))

            workflow.ensure_target(state)
            for name in paths:
                validate_path(workflow.root, name)
                if not _ready(owners[name], Path(name).name, private, plans[name]):
                    raise JournalError("A journal target changed before receipt finalization")
            for name in paths:
                _cleanup(private, plans[name])
            prepared["pending"] = None
            index_token = _save_index(private, index_token, prepared)
            return receipt
