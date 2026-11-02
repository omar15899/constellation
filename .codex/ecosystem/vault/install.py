"""Enroll a vault's Git guards and retire its tracked local Codex skill discovery.

The stable entry verifies the installed release and holds its exclusive lock
through enrollment. A complete immutable guard generation becomes effective
with one Git configuration change. Previously selected generations are kept so
in-flight Git operations can finish. Re-running enrollment repairs partial
native skill exclusions without changing the project's documents or index.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import os
import re
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile

from .. import platform_support as ps
from ..hooks import check_vault_registration
from ..native import NativeClient, NativeError, _Rpc, _configured_exclusions, _skill_snapshot


class EnrollmentError(ValueError):
    """The vault cannot be enrolled without changing someone else's controls."""


EVENTS = ("pre-commit", "post-commit", "pre-push")
# Last versioned vault Git guards, checked against both index and working tree.
LEGACY = {
    "pre-commit": "9eef269054623fb6cbb8f9f6f919abf8e0c73995c98b253c93cabb2080cc3613",
    "post-commit": "f1ba1dc564f929fa99db4b501278b37ac5fe2fb0e47dcb5b0d4f7dc6ec1146ca",
    "pre-push": "cd4dedc8d93a92cd2fb58d0263771251383b47c107aa15d36fe29c892affcd0a",
}


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=25)
    if result.returncode:
        raise EnrollmentError("Cannot inspect or configure the vault's Git guards")
    return result.stdout.rstrip("\n")


def tracked(root: Path, pattern: str) -> list[Path]:
    return [Path(item) for item in git(root, "ls-files", "-z", "--", pattern).split("\0") if item]


def legacy_guard(path: Path) -> None:
    """Allow migration only from the shipped guard definitions."""
    if path.name not in LEGACY:
        raise EnrollmentError("Foreign files in the legacy Git guards directory")
    if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise EnrollmentError("The legacy Git guard is not a regular executable")
    if hashlib.sha256(path.read_bytes()).hexdigest() != LEGACY[path.name]:
        raise EnrollmentError("Modified legacy Git guard; preserve and review it before enrollment")


def verify_generation(target: Path) -> None:
    ps.verify_access(target, private=True)
    if {item.name for item in target.iterdir()} != {*EVENTS, "guard.config"}:
        raise EnrollmentError("The configured Git guard generation contains unknown files")
    for name in EVENTS:
        path = target / name
        ps.verify_access(path)
        if (stat.S_IMODE(path.stat().st_mode) != 0o700
                or hashlib.sha256(path.read_bytes()).hexdigest() != target.name):
            raise EnrollmentError("The configured Git guard generation was modified")

    config = target / "guard.config"
    ps.verify_access(config)
    if stat.S_IMODE(config.stat().st_mode) != 0o600 or config.read_bytes() != _guard_config(target):
        raise EnrollmentError("The generated vault Git configuration was modified")


def verify_guard(project_root: Path, codex_home: Path) -> dict[str, str | bool]:
    """Check the active canonical Git guards for an already enrolled checkout.

    Callers use the verified installed release while its shared installation
    lock is held. The result describes the current root, registration and Git
    configuration without creating workflow state or changing any settings.
    """
    home = ps.validate_lookup(codex_home)
    binding = check_vault_registration(home, str(project_root), require_bound=True)
    root = Path(binding["root"])
    expected = home / "constellation-vault-guards" / hashlib.sha256(_redirector(root, home)).hexdigest()

    def active() -> Path:
        return ps.validate_lookup(Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks")))

    if active() != expected:
        raise EnrollmentError("The enrolled checkout is not using its canonical Constellation Git guards")
    verify_generation(expected)
    if check_vault_registration(home, str(root), require_bound=True) != binding or active() != expected:
        raise EnrollmentError("The enrolled checkout or its Git guards changed during verification")
    return {"verified": True, "root": str(root), "hooks": str(expected)}


def guard_destination(root: Path, home: Path) -> Path:
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise EnrollmentError("Vault enrollment requires the exact canonical Git root")
    base = ps.validate_lookup(home / "constellation-vault-guards")
    effective = ps.validate_lookup(Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks")))
    configured = subprocess.run(["git", "config", "--show-scope", "--get", "core.hooksPath"], cwd=root,
                                capture_output=True, text=True, timeout=25)
    if configured.returncode not in (0, 1):
        raise EnrollmentError("Cannot determine the effective Git hooks setting")
    if configured.returncode == 0 and configured.stdout.partition("\t")[0] in {"command", "worktree"}:
        raise EnrollmentError("A higher-precedence Git hooks setting would prevent enrollment")
    if effective.parent == base:
        verify_generation(effective)
    elif effective == root / ".codex/git-hooks":
        if effective.is_dir():
            for path in effective.iterdir():
                legacy_guard(path)
        for relative in tracked(root, ".codex/git-hooks"):
            stage = git(root, "ls-files", "--stage", "--", str(relative)).split()
            if (len(stage) != 4 or stage[0] != "100755" or stage[2] != "0"
                    or relative.name not in LEGACY or relative.parent != Path(".codex/git-hooks")):
                raise EnrollmentError("Foreign or conflicted guard in the Git index")
            blob = subprocess.check_output(["git", "cat-file", "blob", stage[1]], cwd=root, timeout=25)
            if hashlib.sha256(blob).hexdigest() != LEGACY[relative.name]:
                raise EnrollmentError("Modified legacy Git guard in the index")
    elif configured.returncode == 0 or (effective.exists()
            and any(not file.name.endswith(".sample") for file in effective.iterdir())):
        raise EnrollmentError("Existing Git hook configuration would be replaced")
    return base


def _redirector(root: Path, home: Path) -> bytes:
    # Git interprets only this installer-owned script. Workspace content and
    # repository-controlled Python imports never select the executable.
    q = shlex.quote
    return (
        "#!/bin/sh\n"
        'actual=$(git rev-parse --show-toplevel) || exit 2\n'
        f'[ "$actual" = {q(str(root))} ] || {{ echo "Constellation: unexpected Git root" >&2; exit 2; }}\n'
        f'export CODEX_HOME={q(str(home))}\n'
        f'approval=$({q(str(home / "constellation/run"))} '
        f'vault --project-root {q(str(root))} git-hook "${{0##*/}}") || exit $?\n'
        '[ "$approval" = "{}" ] || { echo "Constellation: Git guard did not approve this event" >&2; exit 2; }\n'
    ).encode("utf-8")


def _git_quote(value: str) -> str:
    if any(ord(char) < 32 for char in value):
        raise EnrollmentError("Git guard paths cannot contain control characters")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _guard_config(target: Path) -> bytes:
    return f"[core]\n\thooksPath = {_git_quote(str(target))}\n".encode()


def prepare_guards(base: Path, root: Path, home: Path) -> Path:
    """Prepare and validate all executable events before Git can select them."""
    script = _redirector(root, home)
    ps.secure_mkdir(base, mode=0o700, parents=True, exist_ok=True)
    destination = base / hashlib.sha256(script).hexdigest()
    if destination.exists() or destination.is_symlink():
        verify_generation(destination)
        return destination
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=base) as staging:
        prepared = Path(staging) / "guards"
        prepared.mkdir(mode=0o700)
        for name in EVENTS:
            path = prepared / name
            with path.open("xb") as stream:
                stream.write(script)
                stream.flush()
                os.fchmod(stream.fileno(), 0o700)
                os.fsync(stream.fileno())
        config = prepared / "guard.config"
        with config.open("xb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(_guard_config(destination))
            stream.flush()
            os.fsync(stream.fileno())
        ps.sync_directory(prepared)
        ps.promote_directory(prepared, destination)
    ps.sync_directory(base)
    verify_generation(destination)
    return destination


def exclude_local_skills(root: Path, home: Path, codex: str, install_lock_fd: int) -> int:
    """Disable tracked local skill definitions via native exact-path settings.

    Explicit user enablement is a conflict. A failed native write leaves prior
    confirmed exclusions in place for an idempotent retry.
    """
    candidates = set()
    for relative in tracked(root, ".agents/skills/*/SKILL.md"):
        if len(relative.parts) == 4 and relative.name == "SKILL.md":
            path = ps.validate_lookup(root / relative)
            if path.is_file():
                candidates.add(str(path))
    if not candidates:
        return 0
    client = NativeClient(home, executable=codex, cwd=root)
    try:
        with closing(_Rpc(client)) as reader:
            before = _skill_snapshot(reader, root)
            config = reader.call("config/read", {"cwd": str(root), "includeLayers": False})["config"]
        if not candidates.issubset(before):
            raise EnrollmentError("Native discovery did not identify all tracked local skills")
        names = {path: before[path]["name"] for path in candidates}

        def configured() -> set[str]:
            return _configured_exclusions(home, root / ".codex", candidates, names_by_path=names)

        excluded = configured()
        if any(before[path]["enabled"] for path in excluded):
            raise EnrollmentError("A configured skill exclusion conflicts with effective native discovery")
        pending = sorted(candidates - excluded)
        pending_names = {names[path] for path in pending}
        for value in (config.get("skills") or {}).get("config", []) or []:
            if value.get("enabled", True) and (value.get("path") in pending or value.get("name") in pending_names):
                raise EnrollmentError("Explicit user skill enablement conflicts with central-only discovery")
        if pending:
            # Only the writer receives the exclusive bootstrap lock. Its
            # inherited open file description survives an interrupted parent.
            with client.inherit_install_lock(install_lock_fd), closing(_Rpc(client, mutating=True)) as writer:
                for path in pending:
                    if path in configured():
                        continue
                    result = writer.call("skills/config/write", {"path": path, "enabled": False})
                    if result.get("effectiveEnabled") is not False:
                        raise EnrollmentError("Native skill exclusion was not confirmed; retry enrollment")
        with closing(_Rpc(client)) as verifier:
            after = _skill_snapshot(verifier, root)
        if not candidates.issubset(configured()) or any(
                row["enabled"] for path, row in after.items() if path in candidates):
            raise EnrollmentError("Local skill exclusions are not fully effective; retry enrollment")
    except (KeyError, TypeError, AttributeError, NativeError) as exc:
        raise EnrollmentError("Cannot verify native skill settings; retry enrollment") from exc
    return len(candidates)


def _hook_settings(root: Path) -> tuple[bytes, bytes]:
    """Capture the direct setting and the complete, ordered effective selection."""
    def values(*options: str) -> bytes:
        result = subprocess.run(["git", "config", *options, "--null", "--get-all", "core.hooksPath"],
                                cwd=root, capture_output=True, timeout=25)
        if result.returncode not in (0, 1):
            raise EnrollmentError("Cannot determine the effective Git hooks setting")
        return result.stdout

    local = values("--local", "--no-includes")
    if local.count(b"\0") > 1:
        raise EnrollmentError("Conflicting local Git hook settings must be preserved")
    return local, values("--includes", "--show-origin", "--show-scope")


def _updated_config(original: bytes, destination: Path, git_dir: Path) -> bytes:
    """Append one include restricted to this literal Git directory, at EOF.

    Git evaluates the include in place. Keeping every original setting intact
    preserves other checkouts and relative includes. A previous generated
    block for this same directory can move to EOF or select a new generation;
    modified managed blocks require explicit reconciliation.
    """
    literal = "".join("\\" + char if char in "\\*?[" else char for char in str(git_dir))
    header = ("\n# Constellation vault guard\n[includeIf "
              + _git_quote("gitdir:" + literal) + "]\n").encode()
    trailer = b"# End Constellation vault guard\n"
    block = header + b"\tpath = " + _git_quote(str(destination / "guard.config")).encode() + b"\n" + trailer
    prefix, found, rest = original.partition(header)
    if found:
        body, closed, suffix = rest.partition(trailer)
        directory = _git_quote(str(destination.parent) + "/")[:-1].encode()
        field = rb"\tpath = " + re.escape(directory) + rb'[a-f0-9]{64}/guard\.config"\n'
        if not closed or header in suffix or not re.fullmatch(field, body):
            raise EnrollmentError("Modified or ambiguous Constellation vault include; preserving configuration")
        original = prefix + suffix
    return original + block


def _common_dir(root: Path) -> Path:
    return ps.validate_lookup(Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")))


def _same_owner(root: Path, home: Path, binding: dict, common_fd: int) -> None:
    if (check_vault_registration(home, str(root), require_bound=False) != binding
            or not os.path.samestat(os.fstat(common_fd), _common_dir(root).stat())):
        raise EnrollmentError("The vault or its Git directory changed during enrollment")


def activate_guards(root: Path, home: Path, binding: dict, common_fd: int,
                    previous: tuple[bytes, bytes], destination: Path, *, validate_only: bool = False) -> None:
    """Commit one Git-config update under the same lock used by native Git.

    The original common Git directory stays open even if the checkout is
    renamed or replaced. All config-file operations use that descriptor.
    Concurrent Git writers either finish before the lock, in which case their
    changes are preserved, or acquire it after this transaction.
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    try:
        lock_fd = os.open("config.lock", flags, 0o600, dir_fd=common_fd)
    except FileExistsError as exc:
        raise EnrollmentError("Git configuration is locked by another operation; retry enrollment") from exc
    locked = os.fstat(lock_fd)
    try:
        _same_owner(root, home, binding, common_fd)
        if _hook_settings(root) != previous:
            raise EnrollmentError("Concurrent Git hook configuration change preserved; retry enrollment")
        guard_destination(root, home)
        with os.fdopen(os.open("config", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=common_fd), "rb") as src:
            old = os.fstat(src.fileno())
            if not stat.S_ISREG(old.st_mode) or old.st_nlink != 1:
                raise EnrollmentError("The Git configuration must be a single regular file")
            original = src.read()
        git_dir = ps.validate_lookup(Path(git(root, "rev-parse", "--absolute-git-dir")))
        updated = _updated_config(original, destination, git_dir)
        with os.fdopen(lock_fd, "wb", closefd=False) as staged:
            os.fchmod(lock_fd, stat.S_IMODE(old.st_mode))
            staged.write(updated)
            staged.flush()
            os.fsync(lock_fd)
        # Read the actual candidate from the original config's directory. Git
        # resolves relative and conditional includes exactly as after promotion.
        candidate = _common_dir(root) / "config.lock"
        value = git(root, "config", "--file", str(candidate), "--includes", "--show-origin",
                    "--get", "core.hooksPath")
        if value != f"file:{destination / 'guard.config'}\t{destination}":
            raise EnrollmentError("Git cannot select the enrolled checkout's requested hooks")
        _same_owner(root, home, binding, common_fd)
        current = os.stat("config", dir_fd=common_fd, follow_symlinks=False)
        if (not os.path.samestat(old, current)
                or (old.st_size, old.st_mtime_ns, old.st_ctime_ns) != (current.st_size, current.st_mtime_ns, current.st_ctime_ns)
                or not os.path.samestat(locked, os.stat("config.lock", dir_fd=common_fd, follow_symlinks=False))):
            raise EnrollmentError("Git configuration changed outside its lock; preserving the change")
        # Included, worktree and higher-scope settings can change without taking
        # the common config.lock. Recheck their order, origin and value here.
        if _hook_settings(root) != previous:
            raise EnrollmentError("Concurrent Git hook configuration change preserved; retry enrollment")
        if not validate_only and original != updated:
            os.replace("config.lock", "config", src_dir_fd=common_fd, dst_dir_fd=common_fd)
            os.fsync(common_fd)
    finally:
        try:
            # After successful promotion Git may already have its own new lock.
            # Never release a lock belonging to another writer.
            if os.path.samestat(locked, os.stat("config.lock", dir_fd=common_fd, follow_symlinks=False)):
                os.unlink("config.lock", dir_fd=common_fd)
        except FileNotFoundError:
            pass
        finally:
            os.close(lock_fd)


def entrypoint(project_root: Path, codex_home: Path, *, codex: str = "codex",
               expected_binding: dict | None = None, install_lock_fd: int) -> int:
    """Activate a complete guard generation for the owner selected by the bootstrap."""
    if sys.version_info < (3, 11) or not Path(sys.executable).is_absolute():
        raise EnrollmentError("Vault enrollment requires a known Python 3.11+ interpreter")
    try:
        import yaml  # The vault workflow imports PyYAML to validate published metadata.
    except ImportError as exc:
        raise EnrollmentError("Install PyYAML in the Python environment used for the vault") from exc
    root = ps.validate_lookup(project_root)
    home = ps.validate_lookup(codex_home)
    binding = expected_binding or check_vault_registration(home, str(root), require_bound=False)
    common_fd = os.open(_common_dir(root), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        _same_owner(root, home, binding, common_fd)
        previous = _hook_settings(root)
        base = guard_destination(root, home)
        destination = prepare_guards(base, root, home)
        activate_guards(root, home, binding, common_fd, previous, destination, validate_only=True)
        exclude_local_skills(root, home, codex, install_lock_fd)
        activate_guards(root, home, binding, common_fd, previous, destination)
        _same_owner(root, home, binding, common_fd)
        active = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "hooks"))
        if active != destination:
            raise EnrollmentError("A higher-precedence Git setting prevented guard activation")
        return 0
    finally:
        os.close(common_fd)
