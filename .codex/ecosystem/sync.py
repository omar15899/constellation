#!/usr/bin/env python3
"""Install the selected published Constellation main revision into one device's Codex home."""
from __future__ import annotations

import argparse
from collections.abc import Iterable
from contextlib import contextmanager
import hashlib
import importlib.util
from itertools import islice
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib


UPSTREAM = "https://github.com/omar15899/constellation.git"
METHODS = ("coding", "mathematics", "quant-research", "writter")
SOURCE_PATHS = (".codex/ecosystem", ".codex/skills", "AGENTS.md", ".codex/profiles/install.py")
DEVICE_TOOL_PATH = os.pathsep.join((os.defpath, "/usr/local/bin", "/opt/homebrew/bin", "/opt/local/bin"))
# Run the immutable candidate's verifier in a fresh interpreter. It locks the
# installation and authenticates the installed entry before loading its runtime.
DISPATCH_INSTALLED = (
    "from pathlib import Path\n"
    "import runpy, sys\n"
    "dispatch = runpy.run_path(sys.argv[1])['dispatch_installed']\n"
    "raise SystemExit(dispatch(Path(sys.argv[2]), sys.argv[3], sys.argv[4:]))"
)



class SyncError(Exception):
    """A release could not be verified or promoted."""


def _run(argv: list[str], *, cwd: Path, env: dict[str, str] | None = None, timeout: int = 300) -> str:
    try:
        result = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SyncError(f"Could not complete {Path(argv[0]).name}") from exc
    if result.returncode:
        # Never echo raw Git transport errors, which can contain credentials.
        diagnostic = ""
        if argv[0] != "git":
            diagnostic = result.stderr.strip()[-600:]
            if not diagnostic:
                try:
                    failure = json.loads(result.stdout)
                except (ValueError, TypeError):
                    failure = {}
                if isinstance(failure, dict) and isinstance(failure.get("error"), str):
                    diagnostic = failure["error"][-600:]
        raise SyncError(f"{Path(argv[0]).name} exited with {result.returncode} {diagnostic}".strip())
    return result.stdout


def _git_environment(work: Path) -> dict[str, str]:
    """Use a neutral directory and an allowlist. Git repository/config overrides are rejected."""
    forbidden = {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_EXEC_PATH",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_SSL_NO_VERIFY"}
    if forbidden.intersection(os.environ) or any(k.startswith("GIT_CONFIG") for k in os.environ):
        raise SyncError("Clear inherited Git repository, configuration or transport overrides before release sync")
    inherited = ("HOME", "XDG_CONFIG_HOME", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS",
                 "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT", "LOCALAPPDATA")
    env = {k: os.environ[k] for k in inherited if k in os.environ}
    env.update(PATH=DEVICE_TOOL_PATH, GIT_TERMINAL_PROMPT="0", GIT_CEILING_DIRECTORIES=str(work.parent))
    return env


def _user_git_setting(work: Path, env: dict[str, str], name: str) -> str:
    """Read a URL-matched setting without executing it or inheriting the caller's repository."""
    try:
        query = subprocess.run(["git", "config", "--get-urlmatch", name, UPSTREAM], cwd=work, env=env,
                               stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SyncError("Could not read the device Git transport settings") from exc
    if query.returncode not in (0, 1):
        raise SyncError("Cannot validate the device Git transport settings")
    return query.stdout.strip()


def _approved_helper(setting: str) -> str | None:
    """Retain familiar configured helpers. Never interpret arbitrary shell helper bodies."""
    if setting in {"osxkeychain", "manager", "manager-core", "libsecret", "cache", "store"}:
        return setting
    if setting.startswith("!"):
        try:
            command = shlex.split(setting[1:])
        except ValueError:
            return None
        gh = shutil.which("gh", path=DEVICE_TOOL_PATH)
        if (gh and len(command) == 3 and command[1:] == ["auth", "git-credential"]
                and command[0] in {"gh", gh, str(Path(gh).resolve())}):
            return f"!{shlex.quote(os.path.abspath(gh))} auth git-credential"
    return None


def _transport(work: Path) -> tuple[list[str], dict[str, str]]:
    """Reject URL rewrites, then fetch with independent frozen HTTPS-only configuration."""
    probe = _git_environment(work)
    # --get-url exits without connecting or executing any transport/helper.
    if _run(["git", "ls-remote", "--get-url", "--", UPSTREAM], cwd=work, env=probe).strip() != UPSTREAM:
        raise SyncError("Git rewrites the canonical Constellation HTTPS origin; remove the rewrite before syncing")
    ssl = _user_git_setting(work, probe, "http.sslVerify").lower()
    if ssl in {"0", "false", "no", "off"}:
        raise SyncError("Git disables TLS certificate verification for the canonical release origin")
    helper = _approved_helper(_user_git_setting(work, probe, "credential.helper"))
    env = {**probe, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_ALLOW_PROTOCOL": "https", "GIT_NO_REPLACE_OBJECTS": "1"}
    git = ["git", "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
           "-c", "http.followRedirects=false", "-c", "http.sslVerify=true", "-c", "credential.helper="]
    if helper:
        git.extend(["-c", f"credential.helper={helper}"])
    if _run([*git, "ls-remote", "--get-url", "--", UPSTREAM], cwd=work, env=env).strip() != UPSTREAM:
        raise SyncError("Isolated Git transport did not resolve the expected release origin")
    return git, env


def published_head() -> str:
    """Probe the canonical published main using the same protected transport as installation."""
    with tempfile.TemporaryDirectory(prefix="constellation-head-") as temporary:
        work = Path(temporary).resolve()
        git, env = _transport(work)
        output = _run([*git, "ls-remote", "--refs", "--exit-code", "--", UPSTREAM,
                       "refs/heads/main"], cwd=work, env=env, timeout=30).strip()
        matched = re.fullmatch(r"([0-9a-f]{40})\trefs/heads/main", output)
        if not matched:
            raise SyncError("Cannot establish a single published main revision")
        return matched[1]


@contextmanager
def _managed_directory(home: Path):
    flags = os.O_DIRECTORY | os.O_RDONLY | os.O_NOFOLLOW
    parent = os.open(home, flags)
    try:
        managed = os.open("constellation", flags, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        yield managed
    finally:
        os.close(managed)


@contextmanager
def _regular_at(directory: int, name: str):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(name, flags, dir_fd=directory), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise SyncError("A managed installation resource is not a regular file")
        yield stream


def _receipt_digest(home: Path) -> str:
    """Snapshot the current regular receipt before fetching for the installer's locked CAS."""
    try:
        with _managed_directory(home) as managed, _regular_at(managed, "receipt.json") as receipt:
            return hashlib.file_digest(receipt, "sha256").hexdigest()
    except FileNotFoundError:
        return "absent"


def _confirm_active(home: Path, bundle_sha: str, modules: tuple[str, ...]) -> dict:
    """Return receipt and stable launcher evidence at a shared-lock linearization point."""
    import fcntl
    with _managed_directory(home) as managed, _regular_at(managed, ".install.lock") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SyncError("Installation busy during final verification; re-evaluate the active release") from exc
        with _regular_at(managed, "receipt.json") as receipt:
            state = json.load(receipt)
        if (state.get("modules") != list(modules)
                or state.get("cache", {}).get("bundle.json", {}).get("sha256") != bundle_sha):
            raise SyncError("The active release changed during sync; re-evaluate the installed revision")
        if state.get("schema") != 4 or state.get("python") != os.path.abspath(sys.executable):
            raise SyncError("The active launcher receipt does not identify the selected Python environment")
        with _regular_at(managed, "run") as launcher:
            mode = stat.S_IMODE(os.fstat(launcher.fileno()).st_mode)
            digest = hashlib.file_digest(launcher, "sha256").hexdigest()
            if mode != 0o700 or state.get("launcher") != {"mode": mode, "sha256": digest}:
                raise SyncError("The stable launcher differs from the active receipt")
        agents = []
        if state.get("agents"):
            directory = os.open(home / "agents", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                for name, expected in sorted(state["agents"].items()):
                    if not re.fullmatch(r"constellation-[a-z-]+\.toml", name):
                        raise SyncError("Invalid installed agent projection")
                    with _regular_at(directory, name) as profile:
                        content = profile.read()
                        actual = {"mode": stat.S_IMODE(os.fstat(profile.fileno()).st_mode),
                                  "sha256": hashlib.sha256(content).hexdigest()}
                    if actual != expected:
                        raise SyncError("Installed agent differs from its receipt")
                    role = tomllib.loads(content.decode("utf-8")).get("name")
                    if not isinstance(role, str):
                        raise SyncError("Installed agent has no native role name")
                    agents.append({"name": role, "path": str(home / "agents" / name),
                                   "sha256": actual["sha256"], "status": "installed_verified"})
            finally:
                os.close(directory)
        return {"receipt_schema": 4, "python": state["python"], "launcher": str(home / "constellation/run"),
                "launcher_sha256": digest, "installed_agents": agents,
                "agent_loading": "Personal agent profiles for a fresh Codex client; current-session loading is unverified"}


def _published_source(work: Path, revision: str | None) -> tuple[Path, str]:
    """Export engine and global instruction sources from one pinned snapshot."""
    if revision is not None and not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SyncError("Supply the full lowercase 40-character SHA of reviewed main")
    repository = work / "objects.git"
    git, env = _transport(work)
    _run([*git, "clone", "--template=", "--bare", "--single-branch", "--branch", "main", "--depth=1",
          "--no-local", "--no-tags", "--filter=blob:none", "--", UPSTREAM, str(repository)], cwd=work, env=env)
    found = _run([*git, "--git-dir", str(repository), "rev-parse", "--verify",
                  "refs/heads/main^{commit}"], cwd=work, env=env).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", found):
        raise SyncError("Could not resolve an exact published main commit")
    if revision is not None and found != revision:
        raise SyncError(f"Published main is {found}; requested {revision}. Nothing installed")
    archive = work / "source.tar"
    _run([*git, "--git-dir", str(repository), "archive", "--format=tar",
          "--output", str(archive), found, "--", *SOURCE_PATHS], cwd=work, env=env)
    snapshot = work / "source"
    snapshot.mkdir(mode=0o700)
    # No symlinks, hardlinks, filters or checkout hooks enter the executable tree.
    with tarfile.open(archive, "r:") as tar:
        for item in tar:
            name = PurePosixPath(item.name)
            if name.is_absolute() or ".." in name.parts or not (
                any(name.is_relative_to(p) for p in SOURCE_PATHS)
                or item.isdir() and any(PurePosixPath(p).is_relative_to(name) for p in SOURCE_PATHS)
            ):
                raise SyncError("Unexpected path in release source archive")
            target = snapshot / name
            if item.isdir():
                target.mkdir(exist_ok=True)
            elif item.isfile():
                data = tar.extractfile(item)
                if data is None:
                    raise SyncError("Unreadable release source member")
                with data, target.open("xb") as output:
                    shutil.copyfileobj(data, output)
                target.chmod(0o755 if item.mode & 0o111 else 0o644)
            else:
                raise SyncError("Release source must contain only regular files and directories")
    return snapshot / ".codex", found


def _protected_names(values: Iterable[str]) -> tuple[str, ...]:
    """Bound historical state before it is used as native command arguments."""
    if isinstance(values, (str, bytes, dict)):
        raise SyncError("Protected exclusions must be an iterable of bare skill names")
    try:
        names = tuple(islice(values, 129))
    except TypeError as exc:
        raise SyncError("Protected exclusions must be an iterable of bare skill names") from exc
    if (len(names) > 128 or any(not isinstance(name, str)
            or not re.fullmatch(r"[a-z][a-z0-9-]{0,127}", name) for name in names)
            or len(names) != len(set(names))):
        raise SyncError("Protected exclusions must contain at most 128 distinct valid skill names")
    return tuple(sorted(names))


def _instruction_command(source: Path, home: Path, revision: str) -> list[str]:
    return [sys.executable, "-I", "-B", str(source / "profiles/install.py"),
            "--instructions-only", "--source-root", str(source.parent),
            "--codex-home", str(home), "--revision", revision]


def _vault_preflight(source: Path, home: Path, root: Path) -> dict:
    """Reject an obsolete enrollment before either installation can change."""
    script = ("import json,sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
              "from ecosystem.hooks import check_vault_registration; "
              "print(json.dumps(check_vault_registration(Path(sys.argv[2]),sys.argv[3],require_bound=False)))")
    return json.loads(_run([sys.executable, "-I", "-B", "-c", script, str(source), str(home), str(root)], cwd=source))


def _tree_records(root: Path) -> dict[str, dict]:
    """Bind a retained regular-file recovery tree, including its permissions."""
    if root.is_symlink() or not root.is_dir():
        raise SyncError("Recovery tree requires a real directory")
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        if any((Path(directory) / name).is_symlink() for name in dirs):
            raise SyncError("Recovery tree contains an unsafe directory")
        for name in files:
            path = Path(directory) / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise SyncError("Recovery tree requires regular singly linked files")
            result[path.relative_to(root).as_posix()] = {
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": stat.S_IMODE(info.st_mode)}
    return result


def _save_recovery(path: Path, manifest: dict) -> None:
    """Publish one complete private recovery record across process interruption."""
    # Keep a killed writer's temporary outside the immutable payload inventory.
    descriptor, temporary = tempfile.mkstemp(prefix=".recovery-", dir=path.parent.parent)
    pending = Path(temporary)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(manifest, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        pending.unlink(missing_ok=True)


def _instruction_digest(home: Path) -> str:
    try:
        with os.fdopen(os.open(home / "AGENTS.md", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise SyncError("Global instructions are not a regular file")
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except FileNotFoundError:
        return "absent"


def _instruction_receipt_digest(home: Path) -> str:
    path = home / "docs/maintenance/instructions.json"
    try:
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise SyncError("Instruction receipt is not a regular file")
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except FileNotFoundError:
        return "absent"


def _retain_previous(source: Path, home: Path, revision: str, bundle_sha: str,
                     modules: tuple[str, ...], instruction_sha: str,
                     expected_instruction_sha: str, expected_instruction_receipt_sha: str) -> Path | None:
    """Keep a verified prior bundle and global instructions for explicit recovery.

    Existing installer receipts validate the copied bundle again at restoration.
    The snapshot stays outside the replaceable distribution and contains no
    client settings, account data, conversations or project state.
    """
    previous = home / "constellation/catalog/plugins/constellation"
    if previous.is_symlink():
        raise SyncError("Installed bundle must not be a symbolic link")
    if not previous.is_dir():
        return None
    def unchanged_instructions() -> None:
        if (_instruction_digest(home) != expected_instruction_sha
                or _instruction_receipt_digest(home) != expected_instruction_receipt_sha
                or stat.S_IMODE((home / "AGENTS.md").stat().st_mode) != 0o644):
            raise SyncError("Global instructions changed before recovery snapshot; preserve the local edit")

    unchanged_instructions()
    parent = home / "docs/maintenance/updates"
    if any(path.is_symlink() for path in (parent, *parent.parents)):
        raise SyncError("Recovery directory must not contain symbolic links")
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="release-", dir=parent))
    shutil.copytree(previous, destination / "bundle", symlinks=True)
    shutil.copy2(source / "profiles/install.py", destination / "instructions-install.py")
    shutil.copy2(source / "ecosystem/sync.py", destination / "sync.py")
    instructions = home / "AGENTS.md"
    if instructions.is_symlink() or not instructions.is_file():
        raise SyncError("An update requires existing regular global instructions")
    shutil.copy2(instructions, destination / "AGENTS.md")
    unchanged_instructions()
    if hashlib.sha256((destination / "AGENTS.md").read_bytes()).hexdigest() != expected_instruction_sha:
        raise SyncError("Global instructions changed while capturing recovery; preserve the local edit")
    prior_revision = None
    prior_receipt = home / "docs/maintenance/instructions.json"
    if prior_receipt.is_file():
        if prior_receipt.is_symlink():
            raise SyncError("Global instruction receipt must not be a symbolic link")
        captured_receipt = prior_receipt.read_bytes()
        if hashlib.sha256(captured_receipt).hexdigest() != expected_instruction_receipt_sha:
            raise SyncError("Global instruction receipt changed while capturing recovery")
        prior_revision = json.loads(captured_receipt).get("revision")
    elif expected_instruction_receipt_sha != "absent":
        raise SyncError("Global instruction receipt disappeared while capturing recovery")
    with _managed_directory(home) as managed, _regular_at(managed, "receipt.json") as receipt:
        previous_installation = json.load(receipt)
    manifest = {"schema": 1, "target_revision": revision, "previous_revision": prior_revision,
                "files": _tree_records(destination), "active_receipt_sha256": _receipt_digest(home),
                "active_instruction_sha256": expected_instruction_sha,
                "target_bundle_sha256": bundle_sha, "target_modules": list(modules),
                "previous_bundle_sha256": hashlib.sha256((previous / "bundle.json").read_bytes()).hexdigest(),
                "previous_modules": previous_installation["modules"],
                "target_instruction_sha256": instruction_sha}
    record = destination / "recovery.json"
    for directory, _, files in os.walk(destination, topdown=False):
        for name in files:
            with (Path(directory) / name).open("rb") as stream:
                os.fsync(stream.fileno())
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    _save_recovery(record, manifest)
    return destination


def _restore(recovery: Path, home: Path, *, codex: str = "codex") -> dict:
    """Restore a retained previous bundle and instructions without network access.

    Recovery is explicit and refuses a changed active installation or locally
    edited instructions. The native installer still owns cache and registration.
    """
    recovery, home = recovery.expanduser().absolute(), home.expanduser().absolute()
    expected_parent = home / "docs/maintenance/updates"
    if recovery.parent != expected_parent or any(path.is_symlink() for path in (recovery, *recovery.parents)):
        raise SyncError("Select the retained recovery directory under this Codex home")
    record = recovery / "recovery.json"
    if record.is_symlink() or not record.is_file() or stat.S_IMODE(record.stat().st_mode) != 0o600:
        raise SyncError("Recovery record must be a private regular file")
    manifest = json.loads(record.read_bytes())
    actual = _tree_records(recovery)
    actual.pop("recovery.json", None)
    if manifest.get("schema") != 1 or actual != manifest.get("files"):
        raise SyncError("Recovery files or active installation changed; preserve both for inspection")
    observed_receipt = _receipt_digest(home)
    if manifest.get("active_receipt_sha256") != observed_receipt:
        # A process may die after the native installer commits but before the
        # outer journal checkpoints its receipt. Only this intent's exact
        # target generation can bridge that gap; later unrelated updates fail.
        try:
            _confirm_active(home, manifest["target_bundle_sha256"], tuple(manifest["target_modules"]))
        except SyncError:
            # The symmetric interruption can happen after restoring the prior
            # native generation and before recording its successful receipt.
            _confirm_active(home, manifest["previous_bundle_sha256"], tuple(manifest["previous_modules"]))
    observed_instructions = _instruction_digest(home)
    admitted_instructions = {manifest["active_instruction_sha256"], manifest["target_instruction_sha256"],
                             manifest["files"]["AGENTS.md"]["sha256"], "absent"}
    if observed_instructions not in admitted_instructions:
        raise SyncError("Global instructions changed; preserve the local edit before recovery")
    python = [sys.executable, "-I", "-B"]
    installer = [*python, str(recovery / "bundle/ecosystem/install.py"), "--bundle", str(recovery / "bundle"),
                 "--codex-home", str(home), "--codex", codex]
    # Refuse a local instruction edit before touching the installed package.
    revision = manifest.get("previous_revision") or "unknown"
    instructions = [*python, str(recovery / "instructions-install.py"), "--instructions-only",
                    "--source-root", str(recovery), "--codex-home", str(home), "--revision", revision,
                    "--expected-sha256", observed_instructions, "--recover-sha256", observed_instructions]
    _run(instructions, cwd=recovery)
    _run([*installer, "--check"], cwd=recovery)
    installed = json.loads(_run([*installer, "--expected-receipt-sha256", observed_receipt], cwd=recovery))
    manifest["active_receipt_sha256"] = _receipt_digest(home)
    _save_recovery(record, manifest)
    try:
        instruction_result = json.loads(_run([*instructions, "--apply"], cwd=recovery))
    except SyncError as exc:
        raise SyncError("Previous bundle restored; instruction recovery remains pending. Preserve recovery files") from exc
    return {"status": "restored", "installation": installed, "instructions": instruction_result,
            "previous_revision": manifest.get("previous_revision"), "recovery": str(recovery)}


def _synchronize(revision: str | None, home: Path, *, vault_root: Path | None, check: bool,
                language: str, codex: str, workspace_root: Path | None = None,
                protect_exclusions: Iterable[str] = ()) -> dict:
    """Verify and install a published release. A binding error leaves the install intact."""
    protected = _protected_names(protect_exclusions)
    if protected and workspace_root is None:
        raise SyncError("Protected source exclusions require the corresponding workspace root")
    home = home.expanduser().absolute()
    if home.is_symlink():
        raise SyncError("Codex home must be a real directory")
    if codex != "codex":
        selected_cli = shutil.which(codex)
        if selected_cli is None:
            raise SyncError("The selected Codex executable is unavailable")
        codex = os.path.abspath(selected_cli)
    if vault_root is not None:
        vault_root = vault_root.expanduser()
        if not vault_root.is_absolute() or not vault_root.is_dir():
            raise SyncError("Supply an existing absolute OmarOS project root")
        if importlib.util.find_spec("yaml") is None:
            raise SyncError("The OmarOS profile needs PyYAML in the Python environment")
    if workspace_root is not None:
        workspace_root = workspace_root.expanduser()
        if not workspace_root.is_absolute():
            raise SyncError("Supply the absolute Constellation source checkout root")
    modules = (*METHODS, "omaros") if vault_root is not None else METHODS
    expected_receipt = _receipt_digest(home)
    if expected_receipt != "absent":
        with _managed_directory(home) as managed, _regular_at(managed, "receipt.json") as receipt:
            existing_modules = json.load(receipt).get("modules")
        if isinstance(existing_modules, list) and existing_modules != list(modules):
            raise SyncError("Release sync preserves the installed module selection; migrate profiles explicitly before updating")
    with tempfile.TemporaryDirectory(prefix="constellation-release-") as temporary:
        work = Path(temporary).resolve()
        source, published = _published_source(work, revision)
        instructions = _instruction_command(source, home, published)
        instruction_preflight = json.loads(_run(instructions, cwd=work))
        binding_preflight = _vault_preflight(source, home, vault_root) if vault_root is not None else None
        bundle = work / "bundle"
        python = [sys.executable, "-I", "-B"]
        _run([*python, str(source / "ecosystem/build.py"), "--output", str(bundle),
              "--language", language, "--modules", *modules], cwd=work)
        bundle_sha = hashlib.sha256((bundle / "bundle.json").read_bytes()).hexdigest()
        workspace_command: list[str] = []
        if workspace_root is not None:
            workspace_command = [*python, str(bundle / "ecosystem/native.py"), "--codex-home", str(home),
                                 "--codex", codex, "--cwd", str(workspace_root),
                                 "--exclude-source-root", str(workspace_root / ".codex")]
            # A name formerly managed by A need not be present in B's immutable
            # module selection. B alone interprets and verifies its preference policy.
            retained = [name for name in protected if (bundle / "skills" / name / "SKILL.md").is_file()]
            for name in retained:
                workspace_command.extend(["--protect-exclusion", name])
            if retained:
                preference = json.loads(_run([*workspace_command, "--check-protected-only"], cwd=work))
                if not isinstance(preference, dict) or preference.get("status") != "protected":
                    raise SyncError("The selected release did not confirm protected workspace preferences")
        installer = [*python, str(bundle / "ecosystem/install.py"), "--bundle", str(bundle),
                     "--codex-home", str(home), "--codex", codex]
        preflight = json.loads(_run([*installer, "--check"], cwd=work))
        recovery = _retain_previous(source, home, published, bundle_sha, modules,
                                    instruction_preflight["sha256"], instruction_preflight["current_sha256"],
                                    instruction_preflight["current_receipt_sha256"]) if not check else None
        result = preflight if check else json.loads(_run([*installer, "--expected-receipt-sha256", expected_receipt], cwd=work))
        result.update(revision=published, bundle_sha256=bundle_sha)
        result["instructions"] = instruction_preflight
        if binding_preflight is not None:
            result["binding_preflight"] = binding_preflight
        if recovery is not None:
            record = recovery / "recovery.json"
            manifest = json.loads(record.read_bytes())
            manifest["active_receipt_sha256"] = _receipt_digest(home)
            _save_recovery(record, manifest)
            result["recovery"] = str(recovery)
        if not check:
            try:
                result["instructions"] = json.loads(_run([*instructions, "--apply", "--expected-sha256",
                                                         instruction_preflight["current_sha256"]], cwd=work))
                if recovery is not None:
                    manifest["active_instruction_sha256"] = result["instructions"]["sha256"]
                    _save_recovery(recovery / "recovery.json", manifest)
            except SyncError as exc:
                if recovery is not None:
                    try:
                        _restore(recovery, home, codex=codex)
                    except (SyncError, OSError, ValueError) as repair:
                        raise SyncError(f"Instruction update failed; recovery needs attention at {recovery}: {repair}") from exc
                    raise SyncError("Instruction update failed; previous package and instructions restored") from exc
                raise SyncError("Package installed but instruction setup failed; retry the same revision") from exc
        if vault_root is not None and not check:
            try:
                setup = [*python, "-c", DISPATCH_INSTALLED, str(bundle / "ecosystem/hook_entry.py"),
                         str(home), "install-vault", "--project-root", str(vault_root)]
                if codex != "codex":
                    setup.extend(["--codex", codex])
                setup.extend(["--expected-bundle-sha256", bundle_sha])
                binding = json.loads(_run(setup, cwd=work, env={**os.environ, "CODEX_HOME": str(home)}))
                if not isinstance(binding, dict) or binding.get("registered") is not True:
                    raise SyncError("The verified installer did not confirm vault registration")
                result["binding"] = binding
            except (SyncError, ValueError) as exc:
                raise SyncError(f"Release {published} installed. Vault setup failed: {exc}. "
                                "Correct the project root or Python environment and retry") from exc
        if workspace_root is not None and not check:
            try:
                if not workspace_root.is_dir():
                    raise SyncError("The specified source checkout is missing")
                exclusion = json.loads(_run(
                    [*workspace_command, "--expected-bundle-sha256", bundle_sha], cwd=work))
                if (not isinstance(exclusion, dict) or exclusion.get("status") != "excluded"
                        or exclusion.get("bundle_sha256") != bundle_sha):
                    raise SyncError("Native source exclusion was not confirmed")
                result["workspace"] = exclusion
            except (SyncError, ValueError) as exc:
                completed = " and vault configured" if "binding" in result else ""
                raise SyncError(f"Release {published} installed{completed}. Workspace source exclusion "
                                f"remains pending: {exc}. Preserve local work, compare the checkout's "
                                "sources with the installed revision and retry the same selection") from exc
        if not check:
            result.update(_confirm_active(home, bundle_sha, modules))
            try:
                metadata = json.loads(_run([*python, str(bundle / "ecosystem/native.py"), "--codex-home", str(home),
                                           "--codex", codex, "--cwd", str(vault_root or home), "--capabilities"], cwd=work))
                result["native"] = {key: metadata.get(key) for key in ("surface", "status", "agents", "hooks", "checks")}
            except (SyncError, ValueError):
                result["native"] = {"status": "unavailable", "hooks": "Check /hooks in a fresh Codex client"}
        return result


@contextmanager
def _release_lock(home: Path):
    """Serialize complete sync/recovery cycles independently of installer locks."""
    import fcntl
    directory = home.expanduser().absolute() / "docs/maintenance"
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        raise SyncError("Release lock directory must not contain symbolic links")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(directory / ".release-sync.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(descriptor, "r+b") as lock:
        info = os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
            raise SyncError("Release lock must be a private singly linked regular file")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield


def synchronize(revision: str | None, home: Path, *, vault_root: Path | None, check: bool,
                language: str, codex: str, workspace_root: Path | None = None,
                protect_exclusions: Iterable[str] = ()) -> dict:
    """Verify or update a single revision under the complete release lock."""
    options = dict(vault_root=vault_root, check=check, language=language, codex=codex,
                   workspace_root=workspace_root, protect_exclusions=protect_exclusions)
    if check:
        return _synchronize(revision, home, **options)
    with _release_lock(home):
        return _synchronize(revision, home, **options)


def restore(recovery: Path, home: Path, *, codex: str = "codex") -> dict:
    """Restore an admitted prior release while excluding simultaneous updates."""
    with _release_lock(home):
        return _restore(recovery, home, codex=codex)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    release = parser.add_mutually_exclusive_group(required=True)
    release.add_argument("--revision", help="approved full Git SHA at upstream main")
    release.add_argument("--latest", action="store_true", help="promote the current main of the canonical upstream")
    release.add_argument("--restore", type=Path, help="restore a retained previous release without network access")
    parser.add_argument("--codex-home", type=Path,
                        default=Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser())
    profile = parser.add_mutually_exclusive_group()
    profile.add_argument("--vault-root", type=Path, help="install personal skills and bind the OmarOS Git root")
    profile.add_argument("--general", action="store_true", help="select the four general methods")
    parser.add_argument("--workspace-root", type=Path, help="exclude equivalent native skill sources in this checkout")
    parser.add_argument("--language", choices=("es", "en"), default="es")
    parser.add_argument("--check", action="store_true", help="verify and preflight without installing or binding")
    parser.add_argument("--codex", default="codex", help="native Codex executable")
    args = parser.parse_args(argv)
    try:
        if sys.version_info < (3, 11) or os.name != "posix":
            raise SyncError("Codex release sync requires POSIX and Python 3.11 or later")
        if args.restore is not None:
            if args.vault_root or args.general or args.workspace_root or args.check:
                raise SyncError("Restore only takes --codex-home and --codex")
            result = restore(args.restore, args.codex_home, codex=args.codex)
        elif not args.general and args.vault_root is None:
            raise SyncError("Select --general or --vault-root")
        else:
            result = synchronize(args.revision, args.codex_home, vault_root=args.vault_root,
                             check=args.check, language=args.language, codex=args.codex,
                             workspace_root=args.workspace_root)
        print(json.dumps(result, sort_keys=True))
    except (SyncError, OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, f"Sync failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
