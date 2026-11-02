#!/usr/bin/env python3
"""Stable, installer-owned entry for native hooks, CLI operations and device setup.

Only standard-library code runs before the installed receipt and complete
release are verified. Hooks and CLI operations pin their release under a shared
lock. Enrollment holds the exclusive lock through configuration. Self-update
uses verified standalone bytes so its installer can acquire the lock.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import signal
import shlex
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True
EVENTS = frozenset({"UserPromptSubmit", "PreToolUse", "SubagentStart", "SubagentStop", "Stop"})
PLUGIN_DIRECTORY = "plugins/constellation"
CATALOG_MANIFEST = ".agents/plugins/marketplace.json"
CHECK_SECONDS = 1.0
CONSTELLATION_CLI_API = 1


# BEGIN CONSTELLATION CURRENT INVENTORY
# Generated from build.allowed_files; do not maintain a second inventory.
_CURRENT_COMMON_FILES = frozenset((
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    "agents/researcher.md",
    "agents/reviewer.md",
    "agents/security-reviewer.md",
    "agents/verifier.md",
    "ecosystem/README.md",
    "ecosystem/__init__.py",
    "ecosystem/agents/researcher.toml",
    "ecosystem/agents/reviewer.toml",
    "ecosystem/agents/security-reviewer.toml",
    "ecosystem/agents/verifier.toml",
    "ecosystem/build.py",
    "ecosystem/claude-hooks.json",
    "ecosystem/claude.py",
    "ecosystem/claude_hooks.py",
    "ecosystem/cli.py",
    "ecosystem/core.py",
    "ecosystem/docs/architecture.md",
    "ecosystem/docs/compatibility.md",
    "ecosystem/docs/evaluation.md",
    "ecosystem/docs/migrations.md",
    "ecosystem/docs/progress.md",
    "ecosystem/docs/updates.md",
    "ecosystem/docs/windows.md",
    "ecosystem/evals/cases.json",
    "ecosystem/evals/rubric.json",
    "ecosystem/hook_entry.py",
    "ecosystem/hooks.json",
    "ecosystem/hooks.py",
    "ecosystem/install.py",
    "ecosystem/install_recovery.py",
    "ecosystem/native.py",
    "ecosystem/platform_support.py",
    "ecosystem/references/protocol.md",
    "ecosystem/requirements-dev.txt",
    "ecosystem/runtime/__init__.py",
    "ecosystem/runtime/agent_policy.py",
    "ecosystem/runtime/dispatch.py",
    "ecosystem/runtime/progress.py",
    "ecosystem/runtime/review-policy.json",
    "ecosystem/runtime/review_gate.py",
    "ecosystem/runtime/workflow.py",
    "ecosystem/runtime/workspace.py",
    "ecosystem/storage.py",
    "ecosystem/sync.py",
    "ecosystem/tests/helpers.py",
    "ecosystem/tests/native_claude_probe.py",
    "ecosystem/tests/test_capabilities.py",
    "ecosystem/tests/test_claude_hooks.py",
    "ecosystem/tests/test_claude_install.py",
    "ecosystem/tests/test_claude_package.py",
    "ecosystem/tests/test_core.py",
    "ecosystem/tests/test_hook_entry.py",
    "ecosystem/tests/test_hooks.py",
    "ecosystem/tests/test_install_recovery.py",
    "ecosystem/tests/test_install_upgrade.py",
    "ecosystem/tests/test_package.py",
    "ecosystem/tests/test_platform_support.py",
    "ecosystem/tests/test_progress.py",
    "ecosystem/tests/test_progress_core.py",
    "ecosystem/tests/test_sync.py",
    "ecosystem/tests/test_updates.py",
    "ecosystem/tests/test_validation.py",
    "ecosystem/tests/test_windows_claude.py",
    "ecosystem/tests/windows_acceptance.py",
    "ecosystem/updates.py",
    "ecosystem/validate.py",
))
_CURRENT_MODULE_FILES = {
    "coding": frozenset((
        "agents/coder.md",
        "ecosystem/agents/coder.toml",
        "skills/coding/SKILL.md",
        "skills/coding/agents/openai.yaml",
        "skills/coding/references/workflow.md",
    )),
    "mathematics": frozenset((
        "agents/counterexample.md",
        "agents/mathematician.md",
        "ecosystem/agents/counterexample.toml",
        "ecosystem/agents/mathematician.toml",
        "ecosystem/references/ontology-examples.md",
        "ecosystem/references/ontology.md",
        "skills/mathematics/SKILL.md",
        "skills/mathematics/agents/openai.yaml",
        "skills/mathematics/references/workflow.md",
    )),
    "quant-research": frozenset((
        "agents/coder.md",
        "agents/counterexample.md",
        "agents/mathematician.md",
        "ecosystem/agents/coder.toml",
        "ecosystem/agents/counterexample.toml",
        "ecosystem/agents/mathematician.toml",
        "skills/quant-research/SKILL.md",
        "skills/quant-research/agents/openai.yaml",
        "skills/quant-research/references/workflow.md",
    )),
    "writter": frozenset((
        "agents/coder.md",
        "agents/editor.md",
        "agents/mathematician.md",
        "ecosystem/agents/coder.toml",
        "ecosystem/agents/editor.toml",
        "ecosystem/agents/mathematician.toml",
        "ecosystem/references/ontology-examples.md",
        "ecosystem/references/ontology.md",
        "skills/writter/SKILL.md",
        "skills/writter/agents/openai.yaml",
        "skills/writter/references/workflow.md",
    )),
    "omaros": frozenset((
        "ecosystem/tests/test_omaros_package.py",
        "ecosystem/tests/test_vault_install.py",
        "ecosystem/tests/test_vault_profile.py",
        "ecosystem/vault/README.md",
        "ecosystem/vault/__init__.py",
        "ecosystem/vault/dispatch.py",
        "ecosystem/vault/install.py",
        "ecosystem/vault/progress_journal.py",
        "ecosystem/vault/review-policy.json",
        "ecosystem/vault/review_gate.py",
        "ecosystem/vault/skill_run.py",
        "ecosystem/vault/workflow.py",
        "skills/brainteasers-quant-notes/SKILL.md",
        "skills/brainteasers-quant-notes/agents/openai.yaml",
        "skills/brainteasers-quant-notes/references/editorial.md",
        "skills/brainteasers-quant-notes/references/tikz.md",
        "skills/brainteasers-quant-notes/scripts/context.py",
        "skills/brainteasers-quant-notes/tests/test_context.py",
        "skills/brainteasers-quant/SKILL.md",
        "skills/brainteasers-quant/agents/openai.yaml",
        "skills/brainteasers-quant/references/course-engine.json",
        "skills/brainteasers-quant/references/production_protocol.md",
        "skills/brainteasers-quant/references/visual_contract.md",
        "skills/brainteasers-quant/scripts/course_engine.py",
        "skills/brainteasers-quant/scripts/production.py",
        "skills/brainteasers-quant/tests/test_course_engine.py",
        "skills/brainteasers-quant/tests/test_production.py",
        "skills/engie-learning/SKILL.md",
        "skills/engie-learning/agents/openai.yaml",
        "skills/engie-learning/references/capture_contract.md",
        "skills/engie-learning/scripts/learning.py",
        "skills/engie-learning/tests/test_learning.py",
        "skills/fast-finder/SKILL.md",
        "skills/fast-finder/agents/openai.yaml",
        "skills/fast-finder/references/query.md",
        "skills/fast-finder/scripts/query.py",
        "skills/fast-finder/scripts/search.py",
        "skills/fast-finder/tests/test_query.py",
        "skills/fast-finder/tests/test_search.py",
        "skills/gs-interface-editor/SKILL.md",
        "skills/gs-interface-editor/agents/openai.yaml",
        "skills/scholar/SKILL.md",
        "skills/scholar/agents/openai.yaml",
        "skills/scholar/references/reader_test.md",
        "skills/teach-from-first-principles/SKILL.md",
        "skills/teach-from-first-principles/agents/openai.yaml",
        "skills/teach-from-first-principles/references/adversarial-self-containment.md",
        "skills/teach-from-first-principles/references/course-construction.md",
        "skills/teach-from-first-principles/references/learner-calibration.md",
    )),
}


def _current_files(modules):
    """Return the active trusted inventory without importing package code."""
    if (not isinstance(modules, (list, tuple)) or not modules
            or not all(isinstance(module, str) for module in modules)
            or len(set(modules)) != len(modules)
            or not set(modules) <= set(_CURRENT_MODULE_FILES)):
        raise ValueError("Invalid current package modules")
    return set(_CURRENT_COMMON_FILES).union(
        *(_CURRENT_MODULE_FILES[module] for module in modules))
# END CONSTELLATION CURRENT INVENTORY


class EntryError(ValueError):
    """The installed release cannot safely be selected."""


def _relative(relative: str) -> Path:
    parts = Path(relative)
    if (not relative or parts.is_absolute() or parts.as_posix() != relative
            or any(part in (".", "..") for part in parts.parts)):
        raise EntryError("invalid installed path")
    return parts


def _path(root: Path, relative: str) -> Path:
    parts = _relative(relative)
    current = root
    for part in parts.parts:
        current /= part
        if current.is_symlink():
            raise EntryError("linked installation path")
    return current


def _record(path: Path) -> dict:
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode):
        raise EntryError("installation file is not regular")
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": stat.S_IMODE(mode)}


def _records(value: object) -> dict:
    if not isinstance(value, dict) or not value:
        raise EntryError("invalid installed inventory")
    for relative, record in value.items():
        if (not isinstance(relative, str) or not isinstance(record, dict)
                or set(record) != {"sha256", "mode"}
                or not isinstance(record["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                or type(record["mode"]) is not int or record["mode"] not in (0o644, 0o755)):
            raise EntryError("invalid installed record")
        _relative(relative)
    return value


def _object(path: Path) -> dict:
    if not stat.S_ISREG(path.stat().st_mode):
        raise EntryError("installation metadata is not regular")

    def unique(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise EntryError("duplicate installation metadata")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise EntryError("invalid installation metadata")
    return value


def _inventory(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise EntryError("installation directory is missing or linked")
    result = {}
    for directory, subdirs, names in os.walk(root, followlinks=False):
        for name in subdirs + names:
            if (Path(directory) / name).is_symlink():
                raise EntryError("linked installed resource")
        for name in names:
            path = Path(directory) / name
            result[path.relative_to(root).as_posix()] = _record(path)
    return result


# The first interpreter starts without site initialisation. It re-executes the
# same physical binary with the venv spelling as argv[0]. Framework Pythons on
# macOS also use PYTHONEXECUTABLE when locating the venv. The alias is never
# used as an executable target.
_VENV_HANDOFF = """import os, sys
target, alias, verifier, entry, digest, *args = sys.argv[1:]
env = os.environ.copy()
if args and args[0] in ("PreToolUse", "UserPromptSubmit", "SubagentStart", "SubagentStop", "Stop"):
    env = {k: v for k, v in env.items() if not k.startswith("GIT_")}
    env["GIT_TERMINAL_PROMPT"] = "0"
env["PYTHONEXECUTABLE"] = alias
os.execve(target, [alias, "-I", "-c", verifier, entry, digest, *args], env)
"""

# This program is embedded in the installer-owned launcher along with its
# expected digest. Never import the stable entry to ask it whether it is safe.
_VERIFY_ENTRY = """import hashlib, os, stat, sys
entry, expected, *args = sys.argv[1:]
flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
with os.fdopen(os.open(entry, flags), "rb") as stream:
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o644 or info.st_nlink != 1:
        raise SystemExit("Unverified Constellation bootstrap identity or mode")
    source = stream.read(2 * 1024 * 1024 + 1)
if len(source) > 2 * 1024 * 1024 or hashlib.sha256(source).hexdigest() != expected:
    raise SystemExit("Unverified Constellation bootstrap contents")
sys.argv = [entry, *args]
namespace = {"__name__": "__main__", "__file__": entry, "__constellation_loaded_sha256__": expected}
exec(compile(source, entry, "exec"), namespace)
"""


def launcher_bytes(python: str, home: Path, python_target: str, hook_sha256: str) -> bytes:
    """Generate the native entry for exactly this interpreter, installation and release.

    The shell can report a valid denial when Python is unavailable. A verified
    bootstrap executes the same bytes it hashed. Operator commands retain stdin,
    their working directory and exit status.
    """
    for path in (python, python_target, str(home)):
        if (not isinstance(path, str) or not Path(path).is_absolute() or str(Path(path)) != path
                or ".." in Path(path).parts or any(ord(c) < 32 or ord(c) == 127 for c in path)):
            raise EntryError("invalid installation interpreter or home")
    if not isinstance(hook_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", hook_sha256):
        raise EntryError("invalid installation bootstrap digest")
    denied = json.dumps(_failure("PreToolUse", "installed interpreter or bootstrap is unavailable or unverified"),
                        separators=(",", ":"))
    warned = json.dumps(_failure("Stop", "installed interpreter or bootstrap is unavailable or unverified"),
                        separators=(",", ":"))
    parts = (python_target, "-I", "-S", "-c", _VENV_HANDOFF, python_target, python, _VERIFY_ENTRY,
             str(home / "constellation/hook.py"), hook_sha256)
    command = " ".join(shlex.quote(arg) for arg in parts) + ' "$@"'
    alias, target = shlex.quote(python), shlex.quote(python_target)
    lines = [
        "#!/bin/sh",
        "export CODEX_HOME=" + shlex.quote(str(home)),
        "unset PYTHONEXECUTABLE __PYVENV_LAUNCHER__",
        f"ready() {{ [ -f {target} ] && [ ! -L {target} ] && [ -x {target} ] && [ {alias} -ef {target} ]; }}",
        "invoke() { exec " + command + "; }",
        'case "$1" in',
        "  PreToolUse|UserPromptSubmit|SubagentStart|SubagentStop|Stop) export PATH=" + shlex.quote(os.defpath) + " ;;",
        '  *) if ready; then invoke "$@"; fi',
        "     printf '%s\\n' 'Constellation interpreter is unavailable or changed' >&2; exit 2 ;;",
        "esac",
        'if ready && response=$(invoke "$@" 2>/dev/null) && [ -n "$response" ]; then',
        "  printf '%s\\n' \"$response\"",
        "  exit 0",
        "fi",
        'case "$1" in',
        "  PreToolUse) printf '%s\\n' " + shlex.quote(denied) + " ;;",
        "  *) printf '%s\\n' " + shlex.quote(warned) + " ;;",
        "esac",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _verified_hook(home: Path, entry: Path) -> Path:
    receipt = _object(_path(home, "constellation/receipt.json"))
    if (set(receipt) != {"schema", "modules", "version", "catalog", "cache", "agents", "hook", "python", "python_target", "launcher"}
            or type(receipt["schema"]) is not int or receipt["schema"] != 4):
        raise EntryError("installation requires a stable-entry receipt")
    launcher = _path(home, "constellation/run")
    launch = launcher_bytes(receipt["python"], home, receipt["python_target"], receipt["hook"]["sha256"])
    expected = {"mode": 0o700, "sha256": hashlib.sha256(launch).hexdigest()}
    if (receipt["launcher"] != expected or _record(launcher) != expected
            or launcher.stat().st_nlink != 1):
        raise EntryError("installed launcher or interpreter binding differs from its receipt")
    modules = receipt["modules"]
    if (not isinstance(modules, list) or not modules
            or not all(isinstance(module, str) for module in modules)
            or len(set(modules)) != len(modules)
            or not set(modules) <= set(_CURRENT_MODULE_FILES)):
        raise EntryError("invalid installed modules")
    version = receipt["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", version):
        raise EntryError("invalid installed version")
    catalog_records = _records(receipt["catalog"])
    cache_records = _records(receipt["cache"])
    if set(cache_records) != _current_files(modules) | {"bundle.json"}:
        raise EntryError("installed inventory differs from the active layout")
    expected_agents = {
        "constellation-" + Path(relative).name: {
            "sha256": cache_records[relative]["sha256"], "mode": 0o644}
        for relative in sorted(_current_files(modules))
        if relative.startswith("ecosystem/agents/")
    }
    # Validate names before even interpreting receipt-supplied agent paths.
    # Native profiles normalize source permissions while retaining source bytes.
    if (not isinstance(receipt["agents"], dict)
            or set(receipt["agents"]) != set(expected_agents)):
        raise EntryError("native agent receipt differs from the current projection")
    agent_records = _records(receipt["agents"])
    if agent_records != expected_agents:
        raise EntryError("native agent receipt differs from the current projection")
    _records({"hook.py": receipt["hook"]})
    if receipt["hook"] != _record(entry) or receipt["hook"]["mode"] != 0o644:
        raise EntryError("stable entry differs from its receipt")
    source_record = cache_records.get("ecosystem/hook_entry.py", {})
    if receipt["hook"]["sha256"] != source_record.get("sha256"):
        raise EntryError("stable entry differs from its release")
    expected_catalog = {f"{PLUGIN_DIRECTORY}/{name}": record for name, record in cache_records.items()}
    expected_catalog[CATALOG_MANIFEST] = catalog_records.get(CATALOG_MANIFEST)
    if catalog_records != expected_catalog:
        raise EntryError("catalog and cache receipts differ")
    catalog = _path(home, "constellation/catalog")
    cache = _path(home, f"plugins/cache/constellation/constellation/{version}")
    if _inventory(catalog) != catalog_records or _inventory(cache) != cache_records:
        raise EntryError("installed release is incomplete or modified")
    root = catalog / PLUGIN_DIRECTORY
    manifest = _object(root / "bundle.json")
    if (set(manifest) != {"schema", "modules", "files"}
            or type(manifest["schema"]) is not int or manifest["schema"] != 1
            or manifest["modules"] != modules
            or manifest["files"] != {name: record for name, record in cache_records.items()
                                     if name != "bundle.json"}):
        raise EntryError("bundle and receipt differ")
    plugin = _object(root / ".codex-plugin/plugin.json")
    if plugin.get("name") != "constellation" or plugin.get("version") != version:
        raise EntryError("plugin and receipt differ")
    for name, expected in expected_agents.items():
        try:
            if _record(_path(home, "agents/" + name)) != expected:
                raise EntryError("owned native agent projection was modified")
        except OSError as exc:
            raise EntryError("owned native agent projection is missing or unsafe") from exc
    hook = _path(root, "ecosystem/hooks.py")
    if "ecosystem/hooks.py" not in cache_records:
        raise EntryError("installed hook is unrecorded")
    return hook


def _failure(event: str, reason: str) -> dict:
    message = f"Constellation INCOMPLETE: {reason}. No task closure was approved; inspect the installation."
    if event == "PreToolUse":
        return {"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "deny",
                                       "permissionDecisionReason": message}}
    # Installation failures have no validated task state with which to bound a
    # Stop retry. Report incompleteness without creating an endless stop loop.
    return {"systemMessage": message}


def _deadline(_signum: int, _frame: object) -> None:
    raise EntryError("installation verification exceeded its internal deadline")


@contextmanager
def _locked_package(home: Path, entry: Path, *, exclusive: bool):
    """Pin and verify this device's installed release through the caller's operation.

    Registration and setup use the exclusive lock to serialize changes to the
    binding and the project. Hooks and long-running CLI operations use shared
    locks, including while their runtime imports modules on demand.
    """
    if sys.version_info < (3, 11):
        raise EntryError("Python 3.11 or newer is required")
    if home.is_symlink() or not home.is_absolute() or entry != _path(home, "constellation/hook.py"):
        raise EntryError("stable entry is outside the installation")
    lock = _path(home, "constellation/.install.lock")
    descriptor = os.open(lock, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise EntryError("installation lock is not regular")
        try:
            fcntl.flock(descriptor, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise EntryError("installation is busy; retry after the current operation finishes") from exc
        loaded_digest = globals().get("__constellation_loaded_sha256__")
        if loaded_digest is not None and loaded_digest != _record(entry)["sha256"]:
            raise EntryError("stable entry changed after it was read; retry using the installed version")
        yield _verified_hook(home, entry).parents[1], descriptor
    finally:
        os.close(descriptor)


@contextmanager
def verified_package(home: Path, entry: Path, *, exclusive: bool = False):
    """Expose the verified package path while holding the installation lock."""
    with _locked_package(home, entry, exclusive=exclusive) as (package, _descriptor):
        yield package


def _command(package: Path, home: Path, command: str, args: list[str], *,
             install_lock_fd: int | None = None) -> int:
    # Only paths in the installation verified above may provide executable code.
    sys.path.insert(0, str(package))
    if command == "cli":
        from ecosystem.cli import main as cli_main
        return cli_main(args, installation_home=home)

    if command not in ("vault", "register-vault", "install-vault"):
        raise EntryError("unknown entry point")
    if len(args) < 2 or args[0] != "--project-root":
        raise EntryError("supply --project-root and the absolute Git owner")
    codex = "codex"
    if command == "install-vault":
        options = dict(zip(args[2::2], args[3::2]))
        if len(args) != 2 + 2 * len(options) or set(options) - {"--codex", "--expected-bundle-sha256"}:
            raise EntryError("invalid or duplicate vault setup options")
        if "--codex" in options:
            codex = options["--codex"]
            if not Path(codex).is_absolute():
                raise EntryError("--codex requires an absolute executable path")
        if "--expected-bundle-sha256" in options:
            expected = options["--expected-bundle-sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", expected) or _record(package / "bundle.json")["sha256"] != expected:
                raise EntryError("installed bundle differs from the requested vault setup release")
    elif command == "register-vault" and len(args) != 2:
        raise EntryError("unexpected vault registration arguments")
    if not (package / "ecosystem/vault/workflow.py").is_file():
        raise EntryError("install the omaros module to use this command")

    from ecosystem.hooks import check_vault_registration, save_vault_registration
    try:
        binding = check_vault_registration(home, args[1], require_bound=(command == "vault"))
        root = Path(binding["root"])
    except (OSError, ValueError) as exc:
        raise EntryError("vault root or binding is invalid or belongs to another project") from exc
    if command == "vault":
        from ecosystem.vault.workflow import entrypoint
        return entrypoint(args[2:], project_root=root)
    if command == "install-vault":
        from ecosystem.vault.install import entrypoint as install_vault
        if install_lock_fd is None:
            raise EntryError("vault setup requires the dispatcher's exclusive installation lock")
        status = install_vault(root, home, codex=codex, expected_binding=binding,
                               install_lock_fd=install_lock_fd)
        if status:
            return status
    save_vault_registration(home, binding)
    print(json.dumps({"registered": True, "root": str(root)}))
    return 0


def dispatch_installed(home: Path, mode: str, args: list[str]) -> int:
    """Run an operator command from an explicitly verified installation home."""
    if mode not in ("cli", "vault", "register-vault", "install-vault"):
        raise EntryError("unknown operator command")
    exclusive = mode in ("register-vault", "install-vault")
    with _locked_package(home, home / "constellation/hook.py", exclusive=exclusive) as (package, descriptor):
        # Only the enrollment's actual native writer may inherit this already
        # locked open-file description. Readers and other commands get no fd.
        return _command(package, home, mode, args,
                        install_lock_fd=descriptor if mode == "install-vault" else None)


def _standalone_snapshot(package: Path, records: dict, name: str) -> bytes:
    """Capture exactly the receipt-backed bytes that will execute after unlocking."""
    relative = "ecosystem/" + name
    expected = records[relative]
    path = _path(package, relative)
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != expected["mode"]:
            raise EntryError("standalone update program has an invalid identity or mode")
        data = stream.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected["sha256"]:
        raise EntryError("standalone update program differs from its receipt")
    return data


def _run_updates(code: bytes, sync_source: bytes, verifier_source: bytes, args: list[str], home: Path) -> int:
    """Execute the verified snapshot after releasing the lock its installer needs.

    The scheduler receives the synchronizer and verifier as immutable bytes.
    A subsequent update can therefore select a new release while this operation
    finishes using the programs it actually authenticated.
    """
    module = ModuleType("_constellation_verified_updates")
    filename = "<verified Constellation updates>"
    module.__file__ = filename
    sys.modules[module.__name__] = module
    try:
        exec(compile(code, filename, "exec"), module.__dict__)
        return module.run(args, home=home, sync_source=sync_source, verifier_source=verifier_source)
    finally:
        sys.modules.pop(module.__name__, None)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    native = mode in EVENTS
    previous_handler = None
    try:
        if native:
            previous_handler = signal.signal(signal.SIGALRM, _deadline)
            signal.setitimer(signal.ITIMER_REAL, CHECK_SECONDS)
        entry = Path(__file__).absolute()
        home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").absolute()
        if not native and mode != "updates":
            if entry != _path(home, "constellation/hook.py"):
                raise EntryError("stable entry is outside the installation")
            return dispatch_installed(home, mode, sys.argv[2:])
        with verified_package(home, entry) as package:
            if native:
                interpreter = _object(_path(home, "constellation/receipt.json"))["python"]
                if sys.executable != interpreter:
                    raise EntryError("native events require the interpreter selected at installation")
                hook = package / "ecosystem/hooks.py"
                sys.argv[0] = str(hook)
                runpy.run_path(str(hook), run_name="__main__")
                return 0
            records = _object(_path(home, "constellation/receipt.json"))["cache"]
            code, sync_source, verifier_source = (
                _standalone_snapshot(package, records, name) for name in ("updates.py", "sync.py", "hook_entry.py"))
        return _run_updates(code, sync_source, verifier_source, sys.argv[2:], home)
    except EntryError as exc:
        reason = str(exc)
    except Exception:
        reason = "installation or registered operation could not be verified"
    finally:
        if previous_handler is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
    if not native:
        print(f"Constellation: {reason}.", file=sys.stderr)
        return 2
    print(json.dumps(_failure(mode, reason), ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
