#!/usr/bin/env python3
"""Check an installed Copilot profile without starting a model conversation.

The temporary protocol exercise uses explicitly synthetic identities. Replaying
hook commands proves their local behavior, not that Copilot dispatches those
hooks or runs independent reviewers. Native discovery remains a separate check.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from types import ModuleType
from typing import Any

sys.dont_write_bytecode = True

NATIVE_WINDOWS = os.name == "nt" and sys.platform == "win32"
MAX_BYTES = 32 * 1024 * 1024
EVENTS = ("sessionStart", "subagentStart", "preToolUse", "agentStop")
PROFILE_FILES = {
    "copilot-instructions.md", "docs/README.md", "tools/official_docs.py",
    "skills/human-coding/SKILL.md", "hooks/constellation.json",
    "constellation/profile/README.md", "constellation/profile/runtime.py",
    "constellation/profile/acceptance.py",
    *(f"agents/{name}.agent.md" for name in (
        "implementer", "correctness-reviewer", "readability-reviewer", "robustness-reviewer")),
}


class AcceptanceError(ValueError):
    """A fixed diagnostic that never embeds native output or private paths."""

    def __init__(self, stage: str, reason: str):
        super().__init__(reason)
        self.stage = stage
        self.reason = reason


class PendingAcceptance(AcceptanceError):
    """A required platform capability or native dependency is unavailable."""


def safe_path(path: Path) -> Path:
    """Reject linked ancestors before inspecting a local installed resource."""
    path = path.expanduser().absolute()
    for component in (*reversed(path.parents), path):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise AcceptanceError("installation", "linked_or_reparse_lookup")
    return path


def read_regular(path: Path) -> bytes:
    """Read bounded regular bytes, checking identity before and after opening.

    Args:
        path: A local installation resource beneath a checked directory.

    Returns:
        The file's bytes without exposing them in a report.

    Raises:
        AcceptanceError: The lookup is linked, nonregular, unstable or too large.
        OSError: The file is missing or cannot be read.
    """
    path = safe_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_BYTES:
        raise AcceptanceError("installation", "unsafe_or_oversized_resource")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read(MAX_BYTES + 1)
    after = path.lstat()
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if identity(before) != identity(opened) or identity(before) != identity(after) or len(data) > MAX_BYTES:
        raise AcceptanceError("installation", "resource_changed_during_read")
    return data


def json_value(raw: bytes, stage: str) -> Any:
    """Decode strict UTF-8 JSON without retaining or echoing malformed input."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for name, item in items:
            if name in value:
                raise ValueError("duplicate key")
            value[name] = item
        return value

    def constant(_name: str) -> None:
        raise ValueError("nonfinite number")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError):
        raise AcceptanceError(stage, "invalid_json") from None


def load_checked_module(name: str, path: Path, data: bytes) -> ModuleType:
    """Execute already checked local bytes, avoiding a second path lookup."""
    module = ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


def verify_installation(home: Path) -> tuple[Path, ModuleType, dict, dict]:
    """Verify managed resources, pinned hooks and shared-engine access rules.

    Additional native files are allowed: this profile does not own the whole
    Copilot home. The receipt's managed inventory must match the profile and
    verified core exactly. Its hashes establish local integrity, not authorship.

    Args:
        home: User home containing the installed ``.copilot`` directory.

    Returns:
        Copilot home, loaded shared core, native hooks and verified receipt.

    Raises:
        AcceptanceError: Managed bytes, inventory, hooks or access are invalid.
    """
    root = safe_path(home / ".copilot")
    receipt = json_value(read_regular(root / "constellation/profile-receipt.json"), "receipt")
    if (not isinstance(receipt, dict) or set(receipt) != {"schema", "core_source_commit", "files"}
            or receipt["schema"] != 1 or not isinstance(receipt["files"], dict)
            or re.fullmatch(r"[0-9a-f]{40}", str(receipt["core_source_commit"])) is None):
        raise AcceptanceError("receipt", "unsupported_receipt")
    contents = {}
    for name, expected in receipt["files"].items():
        if (not isinstance(name, str) or not name or PurePosixPath(name).is_absolute()
                or "\\" in name or any(part in ("", ".", "..") or ":" in part for part in name.split("/"))
                or re.fullmatch(r"[0-9a-f]{64}", str(expected)) is None
                or not (name in PROFILE_FILES or name.startswith(("constellation/bundle/", "docs/official/")))):
            raise AcceptanceError("receipt", "unsafe_inventory")
        contents[name] = read_regular(root / name)
        if hashlib.sha256(contents[name]).hexdigest() != expected:
            raise AcceptanceError("receipt", "managed_resource_hash_mismatch")
    if not PROFILE_FILES <= contents.keys():
        raise AcceptanceError("receipt", "incomplete_profile")
    platform_name = "constellation/bundle/ecosystem/platform_support.py"
    if platform_name not in contents:
        raise AcceptanceError("receipt", "platform_support_missing")
    platform = load_checked_module("copilot_acceptance_platform", root / platform_name,
                                   contents[platform_name])
    # Check replacement rights before importing the adapter or engine from disk.
    # Matching bytes do not suffice if another account can replace their parent.
    managed_paths = {root, root / "constellation/profile-receipt.json"}
    for name in contents:
        resource = root / name
        managed_paths.add(resource)
        managed_paths.update(parent for parent in resource.parents if parent.is_relative_to(root))
    for resource in managed_paths:
        platform.verify_access(resource, private=False)
    runtime_path = root / "constellation/profile/runtime.py"
    runtime = load_checked_module("copilot_acceptance_runtime", runtime_path,
                                  contents["constellation/profile/runtime.py"])
    bundle = root / "constellation/bundle"
    core = runtime.load_bundle(bundle)
    builder = sys.modules["ecosystem.build"]
    manifest = builder.verify_bundle(bundle)
    expected = PROFILE_FILES | {"constellation/bundle/bundle.json"} | {
        "constellation/bundle/" + name for name in manifest["files"]}
    if "docs/official/manifest.json" in contents:
        docs = load_checked_module("copilot_acceptance_docs", root / "tools/official_docs.py",
                                   contents["tools/official_docs.py"])
        docs.verify(home, "copilot")
        expected |= {"docs/official/" + name for name in (*docs.sources("copilot"), "manifest.json", "INDEX.md")}
    if contents.keys() != expected:
        raise AcceptanceError("receipt", "managed_inventory_mismatch")
    state = safe_path(root / "constellation/state")
    if not state.is_dir():
        raise AcceptanceError("state_access", "private_state_directory_missing")
    core.platform.verify_access(state, private=True)
    for suffix in ("", "-journal", "-wal", "-shm"):
        resource = state / ("ecosystem.sqlite3" + suffix)
        if resource.exists() or core.platform.is_reparse(resource):
            core.platform.verify_access(resource, private=True,
                                        inherited_from=state if suffix else None)
    hooks = json_value(contents["hooks/constellation.json"], "hooks")
    if (not isinstance(hooks, dict) or set(hooks) != {"version", "hooks"}
            or hooks["version"] != 1 or not isinstance(hooks["hooks"], dict)
            or set(hooks["hooks"]) != set(EVENTS)):
        raise AcceptanceError("hooks", "unexpected_hook_events")
    for event in EVENTS:
        entries = hooks["hooks"][event]
        if (not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict)
                or not isinstance(entries[0].get("exec"), str)):
            raise AcceptanceError("hooks", "unexpected_hook_definition")
        interpreter = Path(entries[0]["exec"])
        if not interpreter.is_absolute() or not interpreter.is_file():
            raise AcceptanceError("hooks", "pinned_python_interpreter_unavailable")
        expected_hook = {"type": "command", "exec": str(interpreter),
                         "args": ["-I", "-B", str(runtime_path), "--bundle", str(bundle),
                                  "--state-dir", str(state), "hook", "--event", event], "timeoutSec": 30}
        if hooks["hooks"][event] != [expected_hook]:
            raise AcceptanceError("hooks", "hook_command_or_interpreter_mismatch")
    return root, core, hooks, receipt


def run_command(argv: list[str], *, cwd: Path, environment: dict[str, str],
                stage: str, payload: dict | None = None, timeout: int = 45) -> bytes:
    """Run a fixed argument vector without inheriting interactive input.

    Args:
        argv: Explicit executable and arguments; no shell interpretation occurs.
        cwd: Temporary working directory for the child process.
        environment: Launch essentials with credential variables omitted.
        stage: Fixed public diagnostic label used on failure.
        payload: Optional JSON hook input; metadata commands receive EOF.
        timeout: Maximum execution time in seconds.

    Returns:
        Captured output for local validation, never raw report content.

    Raises:
        AcceptanceError: Execution fails, times out or returns excessive output.
    """
    try:
        result = subprocess.run(argv, cwd=cwd, env=environment, shell=False,
                                input=b"" if payload is None else json.dumps(payload).encode("utf-8"),
                                capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        raise AcceptanceError(stage, "command_unavailable_or_timed_out") from None
    if result.returncode or len(result.stdout) > MAX_BYTES:
        raise AcceptanceError(stage, "command_failed_or_output_too_large")
    return result.stdout


def child_environment(home: Path) -> dict[str, str]:
    """Retain launch essentials while excluding tokens from child environments."""
    names = ("PATH", "PATHEXT", "SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP",
             "APPDATA", "LOCALAPPDATA", "COPILOT_HOME")
    environment = {name: os.environ[name] for name in names if name in os.environ}
    environment.update({"USERPROFILE": str(home), "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1"})
    return environment


def protocol_probe(root: Path, core: ModuleType, hooks: dict, temporary: Path,
                   environment: dict[str, str]) -> dict:
    """Exercise installed hook vectors with a temporary synthetic evidence store.

    Only the state argument is redirected to the temporary store. Interpreter,
    adapter, bundle and event arguments are exactly the checked installed values.
    Synthetic reviewer reports test gate mechanics and never count as native
    independent review of a real project.
    """
    helper_path = root / "constellation/bundle/ecosystem/tests/helpers.py"
    helpers = load_checked_module("copilot_acceptance_fixtures", helper_path, read_regular(helper_path))
    project = temporary / "Synthetic project \u03a9 with spaces"
    state = temporary / "Synthetic evidence state"
    with helpers.Scenario(root=project, state_dir=state) as fixture:
        interpreters = {entries[0]["exec"] for entries in hooks["hooks"].values()}
        for interpreter in interpreters:
            raw = run_command([interpreter, "-I", "-B", "-c",
                               "import json,sys; print(json.dumps(list(sys.version_info[:3])))"],
                              cwd=project, environment=environment, stage="hook_interpreter")
            version = json_value(raw, "hook_interpreter")
            if (not isinstance(version, list) or len(version) != 3
                    or not all(type(value) is int for value in version)
                    or version[:2] < [3, 11]):
                raise AcceptanceError("hook_interpreter", "python_3_11_required")
        def hook(event: str, **fields: Any) -> dict:
            entry = hooks["hooks"][event][0]
            arguments = [*entry["args"]]
            arguments[arguments.index("--state-dir") + 1] = str(state)
            raw = run_command([entry["exec"], *arguments], cwd=project, environment=environment,
                              stage="hook_replay", payload={"sessionId": fixture.session,
                                                           "cwd": str(project), **fields},
                              timeout=entry["timeoutSec"])
            value = json_value(raw, "hook_replay")
            if not isinstance(value, dict):
                raise AcceptanceError("hook_replay", "expected_decision_object")
            return value

        def require(condition: bool, reason: str) -> None:
            if not condition:
                raise AcceptanceError("protocol", reason)

        require(fixture.session in hook("sessionStart").get("additionalContext", ""), "missing_session_context")
        require(hook("preToolUse", toolName="edit", toolArgs={"path": "result.md"}).get(
            "permissionDecision") == "deny", "unplanned_edit_not_denied")
        fixture.plan()
        require(hook("preToolUse", toolName="edit", toolArgs={"path": "result.md"}) == {}, "planned_edit_denied")
        require(hook("preToolUse", toolName="create", toolArgs={"path": "other.py"}).get(
            "permissionDecision") == "deny", "undeclared_edit_not_denied")
        require(hook("agentStop").get("decision") == "block", "unfinished_task_not_blocked")
        fixture.approve()
        require(hook("agentStop").get("decision") == "block", "unclosed_task_not_blocked")
        fixture.close()
        require(hook("agentStop") == {}, "current_complete_task_blocked")
        (project / "result.md").write_text("Unreviewed synthetic edit.\n", encoding="utf-8")
        require(hook("agentStop").get("decision") == "block", "stale_evidence_not_blocked")
        core.platform.verify_access(state, private=True)
    return {"installed_hook_replays": "passed", "hook_interpreter": "verified",
            "temporary_private_state": "passed",
            "synthetic_gate_reviews": "fixture_only", "synthetic_project": "spaces_and_unicode"}


def native_executable(name: str, environment: dict[str, str]) -> str:
    """Resolve a fixed executable through absolute PATH entries, never the cwd.

    Windows' default search can prepend the caller's working directory. This
    lookup excludes implicit/current-directory entries and aliases directly back
    to the caller directory. Explicit absolute PATH entries remain a trusted
    user setting. Winget links may resolve to their installed executable target.
    """
    filename = name + ".exe" if NATIVE_WINDOWS else name
    current = Path.cwd().resolve()
    for entry in environment.get("PATH", "").split(os.pathsep):
        directory = Path(entry.strip('"'))
        if not entry or not directory.is_absolute() or directory.resolve() == current:
            continue
        try:
            candidate = (directory / filename).resolve(strict=True)
            safe_path(candidate)
            if candidate.parent != current and candidate.is_file():
                return str(candidate)
        except (OSError, AcceptanceError):
            continue
    raise PendingAcceptance("dependencies", "native_" + name + "_executable_required")


def native_metadata(root: Path, temporary: Path, environment: dict[str, str]) -> dict:
    """Check versions and native instruction/skill discovery without an agent.

    Args:
        root: Checked installed Copilot home whose resources must be discovered.
        temporary: Synthetic cwd; project-specific overrides are not evaluated.
        environment: Credential-free child environment retaining profile lookup.

    Returns:
        Sanitized versions and discovery states. Effective instruction enablement
        and hook configuration still require a real native session check.

    Raises:
        PendingAcceptance: A dependency, resource or known listing format is absent.
        AcceptanceError: A fixed metadata command cannot be validated.
    """
    executables = {}
    for name in ("git", "pwsh", "copilot"):
        executables[name] = native_executable(name, environment)
    commands = {
        "git": [executables["git"], "--version"],
        "powershell": [executables["pwsh"], "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
                       "$PSVersionTable.PSVersion.ToString()"],
        "copilot": [executables["copilot"], "--no-auto-update", "--version"],
    }
    versions = {"python": ".".join(map(str, sys.version_info[:3]))}
    for name, argv in commands.items():
        raw = run_command(argv, cwd=temporary, environment=environment, stage="version:" + name)
        match = re.search(rb"\b(\d+)\.(\d+)(?:\.(\d+))?\b", raw)
        if match is None or (name == "powershell" and int(match[1]) < 7):
            raise PendingAcceptance("dependencies", "unsupported_" + name + "_version")
        versions[name] = match[0].decode("ascii")
    rows = {}
    for resource in ("instruction", "skill"):
        raw = run_command([executables["copilot"], "--no-auto-update", resource, "list", "--json"],
                          cwd=temporary, environment=environment, stage="discovery:" + resource)
        rows[resource] = json_value(raw, "discovery:" + resource)
        if not isinstance(rows[resource], list) or not all(isinstance(row, dict) for row in rows[resource]):
            raise PendingAcceptance("discovery", "unknown_native_listing_format")
    instructions = root / "copilot-instructions.md"
    skill = root / "skills/human-coding/SKILL.md"
    if not any(isinstance(row.get("sourcePath"), str)
               and Path(row["sourcePath"]).resolve() == instructions.resolve() for row in rows["instruction"]):
        raise PendingAcceptance("discovery", "personal_instructions_not_discovered")
    # CLI versions may identify a skill by its file or containing skill folder.
    # Both identify this exact hash-verified resource; name-only matches do not.
    skill_locations = {skill.resolve(), skill.parent.resolve()}
    if not any(row.get("name") == "human-coding" and row.get("enabled") is True
               and isinstance(row.get("path"), str) and Path(row["path"]).resolve() in skill_locations
               for row in rows["skill"]):
        raise PendingAcceptance("discovery", "installed_coding_skill_not_enabled")
    return {"native_dependencies": "passed", "versions": versions,
            "native_resource_discovery": "personal_instruction_path_and_enabled_skill_verified",
            "native_configuration": "pending_manual_check",
            "personal_instruction_effective_enablement": "pending_manual_check"}


def run_acceptance(home: Path, *, portable_check: bool = False) -> dict:
    """Return curated evidence with separate mechanical and live-client states.

    Args:
        home: User home containing the installed profile.
        portable_check: Permit a mechanics-only run without native prerequisites.

    Returns:
        A JSON-compatible report. A portable pass always leaves native Windows,
        event dispatch, parallel review and code-quality acceptance pending.
    """
    report = {"schema": 1, "status": "pending", "mechanical_profile_acceptance": "pending",
              "native_windows_acceptance": "pending", "native_copilot_dispatch": "pending_manual_check",
              "native_parallel_review": "pending_manual_check", "native_code_quality": "not_evaluated",
              "model_conversations_started": 0, "network_confinement": "not_enforced_by_this_probe",
              "real_project_files_modified": False, "native_metadata_scope": "synthetic_working_directory"}
    if sys.version_info < (3, 11) or (not NATIVE_WINDOWS and not portable_check):
        return {**report, "stage": "platform", "reason": "native_windows_and_python_3_11_required"}
    try:
        home = safe_path(home).resolve(strict=True)
        root, core, hooks, receipt = verify_installation(home)
        report.update(installed_integrity="verified", managed_resources=len(receipt["files"]),
                      core_source_commit=receipt["core_source_commit"],
                      official_documentation="verified" if "docs/official/manifest.json" in receipt["files"] else "not_included")
        with tempfile.TemporaryDirectory(prefix="copilot-acceptance-") as directory:
            temporary = Path(directory).resolve()
            environment = child_environment(home)
            if not portable_check:
                report.update(native_metadata(root, temporary, environment))
            else:
                report.update(native_dependencies="not_exercised", native_resource_discovery="not_exercised")
            report.update(protocol_probe(root, core, hooks, temporary, environment))
        report.update(status="passed", mechanical_profile_acceptance="passed")
        if NATIVE_WINDOWS and not portable_check:
            report["native_windows_acceptance"] = "passed"
    except PendingAcceptance as exc:
        report.update(stage=exc.stage, reason=exc.reason)
    except AcceptanceError as exc:
        report.update(status="failed", stage=exc.stage, reason=exc.reason)
    except Exception:
        # Filesystem/provider exceptions can contain private paths or output.
        report.update(status="failed", stage="acceptance", reason="local_validation_failed")
    return report


def main(argv: list[str] | None = None) -> int:
    """Print one report and optionally create a new report file without replacing it."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if callable(getattr(stream, "reconfigure", None)):
            stream.reconfigure(encoding="utf-8", errors="strict")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--portable-check", action="store_true", help="Run only portable mechanics; native acceptance remains pending")
    parser.add_argument("--report", type=Path, help="New JSON output outside the installed profile; never overwritten")
    args = parser.parse_args(argv)
    report = run_acceptance(args.home, portable_check=args.portable_check)
    raw = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    if args.report is not None:
        try:
            output = safe_path(args.report).resolve(strict=False)
            if (output.is_relative_to(safe_path(args.home / ".copilot").resolve(strict=False))
                    or output.is_relative_to(Path(__file__).resolve().parent)):
                raise AcceptanceError("report", "report_must_be_outside_installed_profile")
            with output.open("xb") as stream:
                stream.write(raw)
        except (AcceptanceError, OSError):
            print(json.dumps({"schema": 1, "status": "failed", "stage": "report",
                              "reason": "new_external_report_path_required"}))
            return 2
    print(raw.decode("utf-8"), end="")
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
