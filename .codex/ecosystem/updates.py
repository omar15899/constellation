"""Check the canonical published main from an explicitly enrolled user timer.

The stable bootstrap supplies this module and sync.py as verified snapshots,
releasing its read lock before a promotion needs the installer's write lock.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import types
from contextlib import contextmanager


class UpdateError(Exception):
    """An update could not be completed without changing unrelated state."""


def _directory(path: Path) -> None:
    """Create the private timer state directory inside an existing managed home."""
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise UpdateError("Update state requires a canonical absolute directory")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise UpdateError("Update state must be a private directory owned by this user")


@contextmanager
def _timer_lock(path: Path):
    # Separate from the verified release's read/write lock. Duplicate timer
    # invocations can finish quietly while a previous one still owns the job.
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise UpdateError("Unsafe update lock")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
        else:
            yield True
    finally:
        os.close(descriptor)


def _receipt(home: Path) -> tuple[str, str, tuple[str, ...]]:
    """Bind the last promotion to the receipt now on disk, including its bundle."""
    path = home / "constellation" / "receipt.json"
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid()
                or info.st_mode & 0o022 or info.st_size > 8 * 1024 * 1024):
            raise UpdateError("Unsafe installation receipt")
        raw = stream.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise UpdateError("Installation receipt exceeds its size limit")
    record = json.loads(raw)
    skills = tuple(sorted(match[1] for key in record["cache"]
                          if (match := re.fullmatch(r"skills/([a-z][a-z0-9-]*)/SKILL[.]md", key))))
    return hashlib.sha256(raw).hexdigest(), record["cache"]["bundle.json"]["sha256"], skills


def _last(path: Path) -> dict:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return {}
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or info.st_mode & 0o077 or info.st_size > 32768):
            raise UpdateError("Unsafe release update marker")
        value = json.load(stream)
    if (not isinstance(value, dict) or set(value) not in (
            {"revision", "receipt", "profile"}, {"revision", "receipt", "profile", "workspace"},
            {"revision", "receipt", "profile", "workspace", "managed"})):
        raise UpdateError("Release update marker has an unsupported schema")
    if value.get("managed") is not None:
        history = value["managed"]
        if (not isinstance(history, dict) or set(history) != {"root", "names"}
                or not isinstance(history["root"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", history["root"])
                or not isinstance(history["names"], list) or len(history["names"]) > 128
                or not all(isinstance(n, str) and re.fullmatch(r"[a-z][a-z0-9-]{0,127}", n)
                           for n in history["names"])):
            raise UpdateError("Invalid source preference history in update marker")
    return value


def _mark(path: Path, value: dict) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(json.dumps(value, sort_keys=True).encode("utf-8") + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def _path_identity(root: Path, relative: str) -> tuple:
    """Observe only metadata, stopping at a missing or linked path component."""
    path = root
    components = relative.split("/")
    for i, component in enumerate(components):
        path /= component
        try:
            info = path.lstat()
        except FileNotFoundError:
            return ("absent", i)
        if i + 1 == len(components) or not stat.S_ISDIR(info.st_mode):
            return (i, info.st_dev, info.st_ino, info.st_mode, info.st_size,
                    info.st_mtime_ns, info.st_ctime_ns)
    raise UpdateError("Empty workspace observation")


def _workspace_state(home: Path, profile: dict, skills: tuple[str, ...]) -> str | None:
    """Detect new source aliases or changed settings without opening native discovery."""
    if not profile["workspace_root"]:
        return None
    root = Path(profile["workspace_root"])
    observed = {name: _path_identity(root, ".codex/skills/" + name + "/SKILL.md") for name in skills}
    observed["device_config"] = _path_identity(home, "config.toml")
    observed["project_config"] = _path_identity(root, ".codex/config.toml")
    return hashlib.sha256(json.dumps(observed, sort_keys=True).encode()).hexdigest()


# The bootstrap passed these bytes from its verified package under the read lock.
# Dispatch them in a fresh interpreter; the verifier reacquires a read lock for
# native discovery and validates the current receipt and expected bundle there.
_NATIVE_DISPATCH = """import sys, types
from pathlib import Path
module = types.ModuleType("_timer_verifier")
module.__file__ = "<verified device bootstrap>"
sys.modules[module.__name__] = module
exec(compile(sys.stdin.buffer.read(), module.__file__, "exec"), module.__dict__)
raise SystemExit(module.dispatch_installed(Path(sys.argv[1]), "cli", sys.argv[2:]))
"""


def _reconcile(home: Path, profile: dict, bundle: str, protect: set[str],
               verifier_source: bytes) -> dict:
    """Retain prior UI choices while reconciling newly present source paths."""
    if not verifier_source:
        raise UpdateError("Workspace reconciliation requires the verified bootstrap snapshot")
    root = Path(profile["workspace_root"])
    source = root / ".codex"
    command = [sys.executable, "-I", "-B", "-c", _NATIVE_DISPATCH, str(home), "native",
               "--codex-home", str(home), "--codex", profile["codex"], "--cwd", str(root),
               "--exclude-source-root", str(source), "--expected-bundle-sha256", bundle]
    for name in sorted(protect):
        command.extend(["--protect-exclusion", name])
    result = subprocess.run(command, input=verifier_source, capture_output=True, timeout=180,
                            env={**os.environ, "CODEX_HOME": str(home)}, check=False)
    if result.returncode:
        raise UpdateError("Unable to confirm workspace skill preferences against the installed release; "
                          "inspect native source exclusion for this checkout")
    return json.loads(result.stdout)


def _confirmed_sources(status: dict, root: Path, bundle: str, skills: tuple[str, ...]) -> set[str]:
    source = root / ".codex"
    if (not isinstance(status, dict) or status.get("status") != "excluded" or status.get("bundle_sha256") != bundle
            or status.get("source_root") != str(source) or not isinstance(status.get("paths"), list)):
        raise UpdateError("The native client did not confirm this checkout and installed release")
    names = set()
    for row in status["paths"]:
        name = row["name"]
        if (not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,127}", name)
                or row.get("verified") is not True or row.get("enabled") is not False
                or row.get("path") != str(source / "skills" / name / "SKILL.md")):
            raise UpdateError("Native source exclusion did not verify an exact selected path")
        names.add(name)
    if not names.issubset(skills):
        raise UpdateError("Native discovery returned unknown source names")
    return names


def _history(last: dict, root_id: str | None, skills: tuple[str, ...]) -> tuple[set[str], set[str]]:
    previous = last.get("managed")
    retained = set(previous["names"]) if previous is not None and previous["root"] == root_id else set()
    protection = retained.copy()
    if root_id is not None and "managed" not in last and last.get("workspace") is not None:
        # Older markers cannot establish which extant sources were once
        # suppressed. Require explicit resolution for those, and remember
        # only paths actually confirmed by native discovery.
        protection.update(skills)
    return retained, protection


def _confirm(home: Path, marker: Path, profile: dict, observed: str | None, retained: set[str],
             result: dict | None, receipt: tuple[str, str, tuple[str, ...]], value: dict) -> None:
    receipt_hash, bundle, skills = receipt
    managed = None
    if observed is not None:
        root = Path(profile["workspace_root"])
        confirmed = _confirmed_sources(result, root, bundle, skills)
        managed = {"root": hashlib.sha256(os.fsencode(root)).hexdigest(),
                   "names": sorted(retained | confirmed)}
    if _receipt(home)[:2] != (receipt_hash, bundle):
        raise UpdateError("Installation changed during workspace reconciliation; retry")
    # Use the observation from *before* native verification. Later changes to
    # config or checkout trigger a new check, including changes made by Codex.
    _mark(marker, {**value, "workspace": observed, "managed": managed})


def tick(home: Path, sync_source: bytes, profile: dict, *, verifier_source: bytes = b"") -> dict:
    """Check local source/config changes and then the canonical published revision.

    The timer marker binds a confirmed revision to one installation receipt,
    profile, suppressed source names and observation of the selected checkout.
    A source-only change uses the installed release. A promotion checks the
    workspace with the *new* candidate under its expected bundle digest.
    """
    state = home / "constellation" / "state" / "release-updates"
    _directory(state)
    with _timer_lock(state / "lock") as locked:
        if not locked:
            return {"status": "busy"}
        sync = types.ModuleType("_verified_release_sync")
        exec(compile(sync_source, "<verified Constellation release sync>", "exec"), sync.__dict__)
        profile_hash = hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest()
        receipt = _receipt(home)
        receipt_hash, bundle_hash, skills = receipt
        marker = state / "last.json"
        last = _last(marker)
        bound = last.get("receipt") == receipt_hash and last.get("profile") == profile_hash
        root_id = hashlib.sha256(os.fsencode(profile["workspace_root"])).hexdigest() if profile["workspace_root"] else None
        retained, protection = _history(last, root_id, skills)
        observed = _workspace_state(home, profile, skills)
        drift = "managed" not in last or last.get("workspace") != observed
        try:
            revision = sync.published_head()
        except sync.SyncError as exc:
            if bound and drift and root_id is not None:
                local = _reconcile(home, profile, bundle_hash, protection.intersection(skills), verifier_source)
                _confirm(home, marker, profile, observed, retained, local, receipt, last)
            raise UpdateError(str(exc)) from exc
        if bound and last["revision"] == revision:
            if not drift:
                return {"status": "current", "revision": revision}
            local = (_reconcile(home, profile, bundle_hash, protection.intersection(skills), verifier_source)
                     if root_id is not None else None)
            _confirm(home, marker, profile, observed, retained, local, receipt, last)
            return {"status": "reconciled", "revision": revision}

        kwargs = {**profile, "check": False, "protect_exclusions": tuple(sorted(protection))}
        for key in ("workspace_root", "vault_root"):
            kwargs[key] = Path(kwargs[key]) if kwargs[key] else None
        try:
            result = sync.synchronize(revision, home, **kwargs)
        except sync.SyncError as exc:
            raise UpdateError(str(exc)) from exc
        receipt = _receipt(home)
        receipt_hash, bundle_hash, _ = receipt
        if result.get("revision") != revision or result.get("bundle_sha256") != bundle_hash:
            raise UpdateError("The installation receipt differs from the synchronized bundle; retry")
        _confirm(home, marker, profile, observed, retained, result.get("workspace"), receipt,
                 {"revision": revision, "receipt": receipt_hash, "profile": profile_hash})
        return {"status": "synchronized", "revision": revision}


_JOB = "org.constellation.codex-update"


def _unit_word(value: str) -> str:
    """Quote one literal systemd word, including its specifier expansion."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def _schedule_file(fd: int, name: str, content: bytes) -> bool:
    """Return whether a single-link user-owned file already has these bytes."""
    try:
        file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    except FileNotFoundError:
        return False
    with os.fdopen(file_fd, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or metadata.st_nlink != 1 or metadata.st_mode & 0o077
                or stream.read(len(content) + 1) != content):
            raise ValueError(f"Existing scheduler definition differs or is unsafe: {name}")
    return True


def _install_definitions(user_home: Path, folder: Path, definitions: dict[str, str]) -> None:
    """Publish complete files exclusively through a pinned, checked directory."""
    components = folder.relative_to(user_home).parts
    if user_home.resolve() != user_home or ".." in components:
        raise ValueError("Scheduler directory must be within the real user home")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(user_home, flags)
    try:
        for component in (*components, None):
            meta = os.fstat(fd)
            if meta.st_uid != os.getuid() or meta.st_mode & 0o022:
                raise ValueError("Scheduler directories must be user-owned and not writable by others")
            if component is None:
                break
            try:
                os.mkdir(component, 0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        pending = {Path(path).name: text.encode() for path, text in definitions.items()
                   if not _schedule_file(fd, Path(path).name, text.encode())}
        for name, data in pending.items():
            temporary = ".constellation-stage-" + secrets.token_hex(12)
            tmpfd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o600, dir_fd=fd)
            try:
                with os.fdopen(tmpfd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd,
                            follow_symlinks=False)
                except FileExistsError:
                    if not _schedule_file(fd, name, data):
                        raise ValueError(f"Scheduler definition changed during enrollment: {name}")
            finally:
                os.unlink(temporary, dir_fd=fd)
    finally:
        os.close(fd)


def schedule(home: Path, tick_argv: list[str], *, install: bool) -> dict:
    """Render one hourly user job; optionally write its exact files without activating it."""
    home = Path(home)
    user_home = Path.home()
    arguments = [str(value) for value in tick_argv]
    if (not home.is_absolute() or ".." in home.parts or not arguments
            or not Path(arguments[0]).is_absolute() or any(
                any(ord(char) < 32 or ord(char) == 127 for char in item)
                for item in [str(home), str(user_home), *arguments])):
        raise ValueError("Scheduler paths and arguments must be explicit and free of control characters")
    # User managers usually supply a narrower PATH than interactive shells.
    # Include only selected tool directories, never persist credentials or the
    # entire enrollment environment in a plist or a systemd service.
    directories = []
    for executable in (arguments[0], shutil.which("git"), shutil.which("gh")):
        if executable and Path(executable).is_absolute():
            directory = str(Path(executable).parent)
            if os.pathsep in directory or any(ord(ch) < 32 for ch in directory):
                raise ValueError("Unsafe tool directory in scheduler PATH")
            directories.append(directory)
    search_path = os.pathsep.join(dict.fromkeys([*directories, *os.defpath.split(os.pathsep)]))
    environment = {"CODEX_HOME": str(home), "PATH": search_path}
    if sys.platform == "darwin":
        folder = user_home / "Library/LaunchAgents"
        job_file = str(folder / f"{_JOB}.plist")
        job = {"Label": _JOB, "ProgramArguments": arguments,
               "EnvironmentVariables": environment,
               "RunAtLoad": True, "StartInterval": 3600, "ProcessType": "Background"}
        definitions = {job_file: plistlib.dumps(job).decode()}
        domain = f"gui/{os.getuid()}"
        activate = [["launchctl", "bootstrap", domain, job_file]]
        deactivate = [["launchctl", "bootout", domain, job_file]]
    elif sys.platform.startswith("linux"):
        config_home = Path(os.environ.get("XDG_CONFIG_HOME") or user_home / ".config")
        if not config_home.is_relative_to(user_home) or ".." in config_home.parts:
            raise ValueError("XDG_CONFIG_HOME must be within the user home for scheduled enrollment")
        folder = config_home / "systemd/user"
        service = (
            "[Unit]\nDescription=Update verified Constellation release for Codex\n\n"
            "[Service]\nType=oneshot\nUMask=0077\n"
            + "".join("Environment=" + _unit_word(k + "=" + v) + "\n" for k, v in environment.items())
            + "ExecStart=" + " ".join(map(_unit_word, [":" + arguments[0], *arguments[1:]])) + "\n"
        )
        timer = (
            "[Unit]\nDescription=Check Constellation once per hour\n\n"
            "[Timer]\nOnStartupSec=1min\nOnUnitActiveSec=1h\n\n"
            "[Install]\nWantedBy=timers.target\n"
        )
        definitions = {str(folder / f"{_JOB}.service"): service,
                       str(folder / f"{_JOB}.timer"): timer}
        activate = [["systemctl", "--user", "daemon-reload"],
                    ["systemctl", "--user", "enable", "--now", f"{_JOB}.timer"]]
        deactivate = [["systemctl", "--user", "disable", "--now", f"{_JOB}.timer"]]
    else:
        raise ValueError("Native hourly schedule supports macOS launchd and Linux systemd user managers")
    if install:
        _install_definitions(user_home, folder, definitions)
    return {"definitions": definitions, "installed": install,
            "activate": activate, "deactivate": deactivate}



def run(args: list[str], *, home: Path, sync_source: bytes, verifier_source: bytes = b"") -> int:
    """Run the user-requested plan, enrollment or timer check."""
    parser = argparse.ArgumentParser(prog="Constellation updates")
    parser.add_argument("operation", choices=("plan", "enable", "tick"))
    roots = parser.add_mutually_exclusive_group(required=True)
    roots.add_argument("--vault-root", type=Path)
    roots.add_argument("--general", action="store_true")
    parser.add_argument("--workspace-root", type=Path)
    parser.add_argument("--language", choices=("es", "en"), default="es")
    parser.add_argument("--codex", default="codex")
    options = parser.parse_args(args)
    try:
        codex = shutil.which(options.codex)
        if codex is None:
            raise UpdateError("The selected Codex executable is unavailable")
        command = [str(home / "constellation/run"), "updates", "tick"]
        profile = {"codex": str(Path(codex).absolute()), "language": options.language}
        for key in ("vault_root", "workspace_root"):
            path = getattr(options, key)
            canonical = path.resolve(strict=True) if path else None
            if path:
                if not path.is_absolute() or not path.is_dir() or path != canonical:
                    raise UpdateError("Project roots must be canonical absolute directories")
                command.extend(["--" + key.replace("_", "-"), str(canonical)])
            profile[key] = str(canonical) if canonical else None
        if not options.vault_root:
            command.append("--general")
        command.extend(["--language", options.language, "--codex", profile["codex"]])
        if options.operation == "tick":
            result = tick(home, sync_source, profile, verifier_source=verifier_source)
            if result["status"] not in ("synchronized", "reconciled"):
                return 0
        else:
            result = schedule(home, command, install=options.operation == "enable")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (UpdateError, ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        print(f"Constellation release update: {exc}", file=sys.stderr)
        return 1
