"""One private write-ahead intent for a Constellation installation.

All operations run under the device's exclusive installation lock. Before the
first native or live-filesystem mutation, prepare() publishes the verified
catalogs, both receipts and the intended launcher inode together. A lost
process is recovered against these exact bytes. The Codex registry and cache
are changed only by Codex itself.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from uuid import uuid4

if __package__:
    from . import platform_support as platform
    from .build import file_record
else:
    import platform_support as platform
    from build import file_record


class RecoveryError(ValueError):
    """The installation intent cannot be settled without risking other data."""


NAME = ".transition"
PLUGIN = "plugins/constellation"
PLUGIN_ID = "constellation@constellation"


def _known_dir(path: Path) -> None:
    if not path.is_dir() or path.is_symlink():
        raise RecoveryError(f"Expected a regular directory at {path}")


def _identity(path: Path) -> tuple[int, int] | None:
    if not path.exists() and not path.is_symlink():
        return None
    info = path.lstat()
    return info.st_dev, info.st_ino


def _regular(path: Path, mode: int | None = None) -> bytes:
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or mode is not None and stat.S_IMODE(info.st_mode) != mode
                or not os.path.samestat(info, path.lstat())):
            raise RecoveryError(f"Unsafe installation intent resource: {path}")
        return stream.read()


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: bytes, mode: int = 0o600) -> None:
    with path.open("xb") as stream:
        os.fchmod(stream.fileno(), mode)
        stream.write(data)
        stream.flush()
        platform.sync_file(stream.fileno())


def _receipt_bytes(receipt: dict) -> bytes:
    return (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()


def _parents(records: dict) -> set[str]:
    return {parent.as_posix() for name in records for parent in Path(name).parents if parent != Path(".")}


def _inspect_tree(root: Path, *admitted: dict, exact: bool = True) -> None:
    """Check all names including empty directories before a tree can be replaced."""
    _known_dir(root)
    allowed_dirs = set.union(*(_parents(record) for record in admitted))
    files: dict[str, dict] = {}
    for parent, dirs, names in os.walk(root, followlinks=False, onerror=_raise):
        for name in dirs:
            path = Path(parent) / name
            if path.is_symlink() or path.relative_to(root).as_posix() not in allowed_dirs:
                raise RecoveryError(f"Independent directory preserved at {path}")
        for name in names:
            path = Path(parent) / name
            relative = path.relative_to(root).as_posix()
            if (not any(relative in record for record in admitted) or path.is_symlink()
                    or not stat.S_ISREG(path.lstat().st_mode)):
                raise RecoveryError(f"Independent file preserved at {path}")
            record = file_record(path)
            if not any(expected.get(relative) == record for expected in admitted):
                raise RecoveryError(f"Changed file preserved at {path}")
            files[relative] = record
    if exact and files not in admitted:
        raise RecoveryError(f"Incomplete catalog preserved at {root}")


def _raise(error: OSError) -> None:
    raise error


def _copy_catalog(source: Path, destination: Path, records: dict) -> None:
    _inspect_tree(source, records)
    shutil.copytree(source, destination, symlinks=True)
    _inspect_tree(destination, records)


def _sync_tree(root: Path) -> None:
    """Persist the complete immutable copy before making its intent visible."""
    for parent, _, names in os.walk(root, topdown=False):
        for name in names:
            with (Path(parent) / name).open("rb") as stream:
                platform.sync_file(stream.fileno())
        platform.sync_directory(Path(parent))


def pending(home: Path) -> bool:
    path = home / "constellation" / NAME
    return path.is_symlink() or path.exists()


def _projections(home: Path, root: Path, side: str, receipt: dict | None) -> dict:
    """Only receipt-owned native roles and the stable Python entry may be switched."""
    if receipt is None:
        return {}
    payload = root / f"{side}-catalog" / PLUGIN
    files = {name: (home / "agents" / name, record,
                    payload / "ecosystem/agents" / name.removeprefix("constellation-"))
             for name, record in receipt["agents"].items()}
    files["hook.py"] = (home / "constellation/hook.py", receipt["hook"], payload / "ecosystem/hook_entry.py")
    return files


def _stage_projections(home: Path, root: Path, previous: dict | None, desired: dict) -> dict:
    before = _projections(home, root, "old", previous)
    after = _projections(home, root, "new", desired)
    identities = {}
    for name in sorted(before.keys() | after.keys()):
        live = (before.get(name) or after[name])[0]
        if live.parent.is_symlink() or live.is_symlink():
            raise RecoveryError(f"Independent alias preserved at {live}")
        old_id = _identity(live)
        if name in before:
            if old_id is None or file_record(live) != before[name][1] or _identity(live) != old_id:
                raise RecoveryError(f"Previous projection changed at {live}")
        elif old_id is not None:
            raise RecoveryError(f"Independent destination already exists at {live}")
        slot = root / "projections" / name
        if name in after:
            _, record, source = after[name]
            _write(slot, source.read_bytes(), record["mode"])
            if file_record(slot) != record:
                raise RecoveryError(f"Projected file differs from its authorized catalog: {name}")
        identities[name] = [old_id, _identity(slot)]
    return identities


def _valid_identity(value: object) -> bool:
    return (isinstance(value, list) and len(value) == 2
            and all(type(n) is int and n >= 0 for n in value))


def _read_intent(path: Path) -> dict:
    _known_dir(path)
    info = path.lstat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise RecoveryError(f"Untrusted transition directory: {path}")
    raw = _regular(path / "intent.json", 0o600)
    fields = {"schema", "home", "old_sha", "new_sha", "old_run", "new_run", "old_catalog",
              "old_receipt", "new_receipt", "projections"}
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise RecoveryError("Malformed installation intent; preserve it for inspection") from error
    if not isinstance(data, dict) or set(data) != fields or type(data["schema"]) is not int or data["schema"] != 1:
        raise RecoveryError("Unknown installation intent; preserve it for inspection")
    for name in ("home", "old_run", "new_run", "old_catalog", "old_receipt", "new_receipt"):
        value = data[name]
        if value is None and name in {"old_run", "old_catalog", "old_receipt"}:
            continue
        if not _valid_identity(value):
            raise RecoveryError(f"Invalid identity in installation intent: {name}")
    return data


@dataclass(frozen=True)
class Transition:
    home: Path
    path: Path
    old: dict | None
    new: dict
    old_id: tuple[int, int] | None
    new_id: tuple[int, int]
    old_catalog: tuple[int, int] | None
    old_receipt_id: tuple[int, int] | None
    new_receipt_id: tuple[int, int]
    projections: dict
    switch_file: Callable[..., None]

    @property
    def catalog(self) -> Path:
        return self.home / "constellation/catalog"

    def _admitted_catalogs(self) -> list[dict]:
        return [self.new["catalog"], *([self.old["catalog"]] if self.old else [])]

    def _hold_directory(self, live: Path) -> Path:
        """Move the name exclusively first. Check the *displaced* object before cleanup."""
        held = self.path / "held" / uuid4().hex
        platform.promote_directory(live, held)
        platform.sync_directory(live.parent)
        platform.sync_directory(held.parent)
        try:
            _inspect_tree(held, *self._admitted_catalogs())
        except (OSError, ValueError) as error:
            raise RecoveryError(f"Conflicting catalog retained at {held}; installation requires attention") from error
        return held

    def _switch_catalog(self, side: str) -> None:
        receipt = self.old if side == "old" else self.new
        live = self.catalog
        if live.exists() or live.is_symlink():
            try:
                if receipt is not None:
                    _inspect_tree(live, receipt["catalog"])
                    return
            except RecoveryError:
                pass
            self._hold_directory(live)
        if receipt is None:
            return
        # A completed snapshot stays immutable for replay, even if the process
        # dies between displacement and exclusive promotion to the live name.
        temporary = Path(tempfile.mkdtemp(prefix="stage-", dir=self.path / "work"))
        candidate = temporary / "catalog"
        _copy_catalog(self.path / f"{side}-catalog", candidate, receipt["catalog"])
        _sync_tree(candidate)
        try:
            platform.promote_directory(candidate, live)
        except FileExistsError as exc:
            raise RecoveryError(f"Concurrent catalog preserved at {live}") from exc
        platform.sync_directory(live.parent)
        temporary.rmdir()

    def publish_catalog(self) -> None:
        """Publish the target catalog after verifying the old owner survived staging."""
        if _identity(self.catalog) != self.old_catalog:
            raise RecoveryError(f"Catalog identity changed before promotion: {self.catalog}")
        self._switch_catalog("new")

    def inspect_cache(self) -> None:
        parent = self.home / "plugins/cache/constellation/constellation"
        for ancestor in (self.home / "plugins", self.home / "plugins/cache", parent.parent, parent):
            if ancestor.is_symlink():
                raise RecoveryError(f"Independent cache alias preserved at {ancestor}")
        if not parent.exists():
            return
        _known_dir(parent)
        for version in parent.iterdir():
            records = [receipt["cache"] for receipt in (self.old, self.new)
                       if receipt and receipt["version"] == version.name]
            if not records:
                raise RecoveryError(f"Independent native cache retained at {version}")
            _inspect_tree(version, *records, exact=False)

    def _switch_files(self, forward: bool | None) -> None:
        """Use the same inode switch for a native role, stable hook or device receipt."""
        old = _projections(self.home, self.path, "old", self.old)
        new = _projections(self.home, self.path, "new", self.new)
        directory = self.path / "projections"
        _known_dir(directory)
        if any(item.name not in self.projections for item in directory.iterdir()):
            raise RecoveryError(f"Independent projection data retained at {directory}")
        for name, (before_id, after_id) in sorted(self.projections.items()):
            live = (old.get(name) or new[name])[0]
            if live.parent.is_symlink():
                raise RecoveryError(f"Independent projection directory retained at {live.parent}")
            if forward is not None:
                live.parent.mkdir(parents=True, exist_ok=True)
            prior = (tuple(before_id), old[name][1]) if before_id is not None else None
            candidate = (tuple(after_id), new[name][1]) if after_id is not None else None
            self.switch_file(live, directory / name, prior, candidate, forward=forward, allow_linked=True)

    def publish_files(self) -> None:
        """Switch admitted native role and hook generations to the verified release."""
        self._switch_files(None)
        self._switch_files(True)

    def rollback(self, backend, *, preflight, restore_launcher, registered, disabled) -> None:
        """Return to the validated prior installation using only admitted native effects."""
        if disabled(self.home):
            raise RecoveryError("The plugin has been disabled; preserve that decision before retrying")
        self._validate_held()
        self.inspect_cache()
        self._switch_files(None)
        # Native remove may need a readable, owned catalog even on the first install.
        self._switch_catalog("old" if self.old else "new")
        is_registered, plugin = registered(backend, self.catalog)
        if plugin and plugin.get("version") not in {r["version"] for r in (self.old, self.new) if r}:
            raise RecoveryError("Unrelated native registration retained")
        if self.old:
            if not is_registered:
                backend.add_marketplace(self.catalog)
            cache = self.home / "plugins/cache/constellation/constellation"
            previous = cache / self.old["version"]
            old_cache = False
            if cache.is_dir() and {p.name for p in cache.iterdir()} == {previous.name}:
                try:
                    _inspect_tree(previous, self.old["cache"])
                    old_cache = True
                except RecoveryError:
                    pass
            if not old_cache or not plugin or plugin.get("version") != self.old["version"]:
                self.inspect_cache()
                backend.add_plugin()
        else:
            cache = self.home / "plugins/cache/constellation/constellation"
            if plugin:
                self.inspect_cache()
                backend.remove_plugin()
            elif cache.exists() and any(cache.iterdir()):
                # A native process may have created a partial cache before publishing the
                # registry entry. Re-register this exact candidate, then remove it natively.
                if not is_registered:
                    backend.add_marketplace(self.catalog)
                    is_registered = True
                self.inspect_cache()
                backend.add_plugin()
                self.inspect_cache()
                backend.remove_plugin()
            if is_registered:
                backend.remove_marketplace()
            self._switch_catalog("old")
        self._switch_files(False)
        restore_launcher(self.home, self.path, self.old, self.new, self.old_id, self.new_id,
                         self.old_receipt_id, self.new_receipt_id)
        if self.old:
            preflight(self.home, tuple(self.old["modules"]), backend)
        else:
            is_registered, plugin = registered(backend, self.catalog)
            if is_registered or plugin:
                raise RecoveryError("First-install native rollback remains incomplete")
            self.inspect_cache()
            cache = self.home / "plugins/cache/constellation/constellation"
            if cache.exists() and any(cache.iterdir()):
                raise RecoveryError("First-install native rollback left cache resources")
        self.close()

    def settle(self, backend, *, preflight, restore_launcher, registered, disabled) -> str:
        """Complete a fully committed release or restore the prior one before retrying."""
        if disabled(self.home):
            raise RecoveryError("The plugin has been disabled; pending installation preserved")
        receipt = self.home / "constellation/receipt.json"
        identity = _identity(receipt)
        if identity not in (self.old_receipt_id, self.new_receipt_id):
            raise RecoveryError("An independently replaced receipt is preserved without reading its contents")
        current = _regular(receipt) if identity is not None else None
        if current == _regular(self.path / "new-receipt.json", 0o600):
            if _identity(receipt) != self.new_receipt_id:
                raise RecoveryError("A different live receipt inode has the target bytes; preserve it")
            preflight(self.home, tuple(self.new["modules"]), backend)
            self.close()
            return "completed"
        prior = _regular(self.path / "old-receipt.json", 0o600) if self.old else None
        if current != prior or _identity(receipt) != self.old_receipt_id:
            raise RecoveryError("Live receipt belongs to neither side; installation preserved")
        self.rollback(backend, preflight=preflight, restore_launcher=restore_launcher,
                      registered=registered, disabled=disabled)
        return "restored"

    def _validate_held(self) -> None:
        """An independently modified displaced catalog remains recoverable data."""
        _known_dir(self.path / "held")
        for directory in (self.path / "held").iterdir():
            _inspect_tree(directory, *self._admitted_catalogs())

    def _validate_partial_copy(self, root: Path) -> None:
        """copytree may stop after any prefix in its private, unpromoted output."""
        _known_dir(root)
        for side, receipt in (("old", self.old), ("new", self.new)):
            if receipt is None:
                continue
            source = self.path / f"{side}-catalog"
            records = receipt["catalog"]
            directories = _parents(records)
            matches = True
            for parent, dirs, names in os.walk(root, followlinks=False, onerror=_raise):
                if any((Path(parent) / name).is_symlink()
                       or (Path(parent) / name).relative_to(root).as_posix() not in directories
                       for name in dirs):
                    matches = False
                    break
                for name in names:
                    copied = Path(parent) / name
                    relative = copied.relative_to(root).as_posix()
                    if relative not in records or not (source / relative).read_bytes().startswith(_regular(copied)):
                        matches = False
                        break
                if not matches:
                    break
            if matches:
                return
        raise RecoveryError(f"Independent staging data retained at {root}")

    def _validate_discard(self) -> None:
        """Inspect names and content including private staging remnants before retirement."""
        expected = {"intent.json", "new-receipt.json", "new-catalog", "work", "held", "projections"}
        if self.old:
            expected.update(("old-receipt.json", "old-catalog"))
        names = {p.name for p in self.path.iterdir()}
        if names - {"launcher-image", "receipt-image"} != expected:
            raise RecoveryError(f"Unrecognized data retained at {self.path}")
        header = _read_intent(self.path)
        for side, receipt in (("old", self.old), ("new", self.new)):
            if receipt is not None:
                raw = _regular(self.path / f"{side}-receipt.json", 0o600)
                if json.loads(raw) != receipt or _digest(raw) != header[side + "_sha"]:
                    raise RecoveryError("Changed receipt snapshot retained")
                _inspect_tree(self.path / f"{side}-catalog", receipt["catalog"])
        for name in ("work", "held", "projections"):
            _known_dir(self.path / name)
        self._validate_held()
        self._switch_files(None)
        for item in (self.path / "work").iterdir():
            if item.name.startswith("stage-") and not item.is_symlink() and item.is_dir():
                contents = list(item.iterdir())
                if not contents:
                    continue
                if len(contents) == 1 and contents[0].name == "catalog":
                    self._validate_partial_copy(contents[0])
                    continue
            raise RecoveryError(f"Unrecognized staging data retained at {item}")
        old_launcher = (self.old_id, self.old["launcher"]) if self.old_id is not None else None
        old_receipt = ((self.old_receipt_id, file_record(self.path / "old-receipt.json"))
                       if self.old is not None else None)
        self.switch_file(self.home / "constellation/run", self.path / "launcher-image", old_launcher,
                         (self.new_id, self.new["launcher"]), forward=None)
        self.switch_file(self.home / "constellation/receipt.json", self.path / "receipt-image", old_receipt,
                         (self.new_receipt_id, file_record(self.path / "new-receipt.json")), forward=None)

    def close(self) -> None:
        """Unpublish an entire intent before cleaning its owned, privately detached tree."""
        self._validate_discard()
        detached = Path(tempfile.mkdtemp(prefix=".constellation-retired-", dir=self.home))
        retired = detached / "transaction"
        platform.promote_directory(self.path, retired)
        platform.sync_directory(self.path.parent)
        try:
            replace(self, path=retired)._validate_discard()
        except (OSError, ValueError) as error:
            raise RecoveryError(f"Unexpected data preserved in detached transition at {retired}") from error
        # Only completely verified copies are recursively removed, under a private
        # pathname. A hostile same-user writer holding private directory descriptors
        # is outside this device-local ownership boundary.
        shutil.rmtree(detached)


def prepare(home: Path, previous: dict | None, desired: dict, catalog_stage: Path, launcher: bytes,
            *, validate_receipt: Callable[[Path, Path], dict | None], switch_file: Callable) -> Transition:
    """Persist complete verified inputs and their identities before changing live state."""
    if pending(home):
        raise RecoveryError("Resolve the pending device transition first")
    with tempfile.TemporaryDirectory(prefix=".constellation-prepare-", dir=home) as scratch:
        root = Path(scratch) / "transaction"
        root.mkdir(mode=0o700)
        for name in ("held", "projections", "work"):
            (root / name).mkdir(mode=0o700)
        _copy_catalog(catalog_stage, root / "new-catalog", desired["catalog"])
        old_catalog = home / "constellation/catalog"
        old_bytes = None
        if previous:
            _copy_catalog(old_catalog, root / "old-catalog", previous["catalog"])
            old_bytes = _regular(home / "constellation/receipt.json")
            if json.loads(old_bytes) != previous:
                raise RecoveryError("Prior receipt changed before preparation")
            _write(root / "old-receipt.json", old_bytes)
        new_bytes = _receipt_bytes(desired)
        _write(root / "new-receipt.json", new_bytes)
        _write(root / "receipt-image", new_bytes)
        _write(root / "launcher-image", launcher, 0o700)
        if file_record(root / "launcher-image") != desired["launcher"]:
            raise RecoveryError("Launcher image differs from its approved receipt")
        header = {"schema": 1, "home": _identity(home), "old_sha": _digest(old_bytes) if old_bytes else None,
                  "new_sha": _digest(new_bytes), "old_run": _identity(home / "constellation/run"),
                  "new_run": _identity(root / "launcher-image"), "old_catalog": _identity(old_catalog),
                  "old_receipt": _identity(home / "constellation/receipt.json"),
                  "new_receipt": _identity(root / "receipt-image"),
                  "projections": _stage_projections(home, root, previous, desired)}
        _write(root / "intent.json", _receipt_bytes(header))
        _sync_tree(root)
        platform.promote_directory(root, home / "constellation" / NAME)
        platform.sync_directory(home / "constellation")
    return load(home, validate_receipt=validate_receipt, switch_file=switch_file)


def load(home: Path, *, validate_receipt: Callable[[Path, Path], dict | None], switch_file: Callable) -> Transition:
    """Validate the immutable snapshots at fixed names, without importing their contents."""
    path = home / "constellation" / NAME
    header = _read_intent(path)
    if tuple(header["home"]) != _identity(home):
        raise RecoveryError("Device identity differs from the existing installation intent")
    receipts = {}
    for side in ("old", "new"):
        record = path / f"{side}-receipt.json"
        if side == "old" and header["old_sha"] is None:
            if record.exists() or record.is_symlink() or (path / "old-catalog").exists():
                raise RecoveryError("Unexpected prior release in a first-install intent")
            receipts[side] = None
            continue
        raw = _regular(record, 0o600)
        if _digest(raw) != header[side + "_sha"]:
            raise RecoveryError("Pending receipt changed; preserve its intent")
        parsed = validate_receipt(record, home)
        if parsed is None:
            raise RecoveryError("Pending receipt is absent")
        _inspect_tree(path / f"{side}-catalog", parsed["catalog"])
        receipts[side] = parsed
    names = {"intent.json", "new-receipt.json", "new-catalog", "work", "held", "projections", "launcher-image", "receipt-image"}
    if receipts["old"]:
        names |= {"old-receipt.json", "old-catalog"}
    if any(item.name not in names for item in path.iterdir()):
        raise RecoveryError("Independent files in pending installation preserved")
    for dirname in ("work", "held", "projections"):
        _known_dir(path / dirname)
    before = _projections(home, path, "old", receipts["old"])
    after = _projections(home, path, "new", receipts["new"])
    projected = header["projections"]
    if not isinstance(projected, dict) or set(projected) != before.keys() | after.keys():
        raise RecoveryError("Unrecognized installation projection identities; preserve the intent")
    for name, ids in projected.items():
        if (not isinstance(ids, list) or len(ids) != 2
                or any(not (_valid_identity(value) if name in expected else value is None)
                       for value, expected in zip(ids, (before, after)))):
            raise RecoveryError("Invalid installation projection generation")
    return Transition(home, path, receipts["old"], receipts["new"],
                      tuple(header["old_run"]) if header["old_run"] else None, tuple(header["new_run"]),
                      tuple(header["old_catalog"]) if header["old_catalog"] else None,
                      tuple(header["old_receipt"]) if header["old_receipt"] else None, tuple(header["new_receipt"]),
                      projected, switch_file)
