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


UPSTREAM = "https://github.com/omar15899/constellation.git"
METHODS = ("coding", "mathematics", "quant-research", "writter")
SOURCE_PATHS = (".codex/ecosystem", ".codex/skills")
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
        return {"receipt_schema": 4, "python": state["python"], "launcher": str(home / "constellation/run"),
                "launcher_sha256": digest}


def _published_source(work: Path, revision: str | None) -> tuple[Path, str]:
    """Export only the two engine trees from a fresh, pinned upstream snapshot."""
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
                name == PurePosixPath(".codex") or any(name.is_relative_to(p) for p in SOURCE_PATHS)
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


def synchronize(revision: str | None, home: Path, *, vault_root: Path | None, check: bool,
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
    with tempfile.TemporaryDirectory(prefix="constellation-release-") as temporary:
        work = Path(temporary).resolve()
        source, published = _published_source(work, revision)
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
        result = preflight if check else json.loads(_run([*installer, "--expected-receipt-sha256", expected_receipt], cwd=work))
        result.update(revision=published, bundle_sha256=bundle_sha)
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
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    release = parser.add_mutually_exclusive_group(required=True)
    release.add_argument("--revision", help="approved full Git SHA at upstream main")
    release.add_argument("--latest", action="store_true", help="promote the current main of the canonical upstream")
    parser.add_argument("--codex-home", type=Path,
                        default=Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser())
    profile = parser.add_mutually_exclusive_group(required=True)
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
        result = synchronize(args.revision, args.codex_home, vault_root=args.vault_root,
                             check=args.check, language=args.language, codex=args.codex,
                             workspace_root=args.workspace_root)
        print(json.dumps(result, sort_keys=True))
    except (SyncError, OSError, ValueError, tarfile.TarError) as exc:
        parser.exit(1, f"Sync failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
