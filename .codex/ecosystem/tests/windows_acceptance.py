#!/usr/bin/env python3
"""Run isolated backend acceptance for a native Windows Claude distribution.

The probe uses synthetic projects, temporary homes and local metadata commands.
It never starts a model conversation, reads corporate projects or modifies a real
Claude home. It does not impose a network sandbox on the native executable.
Direct hook replays do not establish native client event dispatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

sys.dont_write_bytecode = True
PLUGIN_PLACEHOLDER = chr(36) + "{CLAUDE_PLUGIN_ROOT}"
UNEXERCISED_CHECKS = {
    "git_workflow_acceptance": "not_exercised",
    "powershell_roundtrip": "not_exercised",
}


class ProbeError(RuntimeError):
    """A bounded operational failure without native output or private content."""

    def __init__(self, stage: str, reason: str, *, output: bytes = b""):
        super().__init__(reason)
        self.stage = stage
        self.reason = reason
        self.output_sha256 = hashlib.sha256(output).hexdigest()


def _run(argv: list[str], *, cwd: Path, environment: dict[str, str],
         stage: str, payload: dict[str, Any] | None = None,
         timeout: int = 90) -> subprocess.CompletedProcess[bytes]:
    """Run an argument vector and keep all native output out of the report."""
    try:
        result = subprocess.run(
            argv, cwd=cwd, env=environment, shell=False,
            input=None if payload is None else json.dumps(payload).encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError(stage, type(exc).__name__) from None
    if result.returncode:
        raise ProbeError(stage, "command_failed",
                         output=result.stdout + result.stderr)
    return result


def _object(result: subprocess.CompletedProcess[bytes], stage: str) -> dict[str, Any]:
    try:
        value = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise ProbeError(stage, "invalid_json", output=result.stdout) from None
    if not isinstance(value, dict):
        raise ProbeError(stage, "expected_json_object")
    return value


def _snapshot(root: Path) -> dict[str, tuple[str, int]]:
    """Measure contents and modes, excluding changing access timestamps."""
    return {
        path.relative_to(root).as_posix():
            (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mode)
        for path in root.rglob("*") if path.is_file()
    }


def _environment(root: Path) -> dict[str, str]:
    """Keep Windows launch essentials; omit credentials and real user profiles."""
    names = ("PATH", "PATHEXT", "SystemRoot", "WINDIR", "COMSPEC")
    result = {name: os.environ[name] for name in names if name in os.environ}
    result.update({
        "TEMP": str(root / "temporary"),
        "TMP": str(root / "temporary"),
        "USERPROFILE": str(root / "profile"),
        "APPDATA": str(root / "profile/AppData/Roaming"),
        "LOCALAPPDATA": str(root / "profile/AppData/Local"),
        "CLAUDE_CONFIG_DIR": str(root / "native metadata home"),
        "CODEX_HOME": str(root / "unused codex home"),
        "CONSTELLATION_STATE_DIR": str(root / "portable state"),
        "PYTHONDONTWRITEBYTECODE": "1",
        # Official controls scoped only to these synthetic child processes:
        # https://code.claude.com/docs/en/env-vars
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL": "1",
    })
    for name in ("TEMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
                 "CLAUDE_CONFIG_DIR"):
        Path(result[name]).mkdir(parents=True, exist_ok=True)
    return result


def _executable(value: str, environment: dict[str, str], stage: str) -> Path:
    """Require a real Windows executable, rather than a shell or npm shim."""
    found = shutil.which(value, path=environment.get("PATH"))
    if found is None:
        raise ProbeError(stage, "native_executable_not_found")
    supplied = Path(found).absolute()
    from platform_support import is_reparse

    current = Path(supplied.anchor)
    for part in supplied.parts[1:]:
        current /= part
        if is_reparse(current):
            raise ProbeError(stage, "executable_lookup_contains_reparse_point")
    if supplied.suffix.casefold() != ".exe" or not supplied.is_file():
        raise ProbeError(stage, "real_exe_required")
    return supplied


_SUITE_SCRIPT = r"""
import contextlib, json, sys, unittest
class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed = []
    def startTest(self, test):
        self.executed.append(test.id())
        super().startTest(test)
suite = unittest.defaultTestLoader.discover(sys.argv[1], pattern=sys.argv[2])
with contextlib.redirect_stdout(sys.stderr):
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2,
                                     resultclass=RecordedResult).run(suite)
print(json.dumps({"tests": result.testsRun, "executed": result.executed,
                  "skipped": [test.id() for test, _ in result.skipped]}))
raise SystemExit(0 if result.wasSuccessful() else 1)
"""

_POSIX_ONLY_SKIPS = frozenset({
    "test_platform_support.FilesystemContractTests.test_failed_posix_exclusive_rename_preserves_source_and_absence",
    "test_platform_support.FilesystemContractTests.test_concurrent_empty_target_is_preserved_by_atomic_posix_promotion",
    "test_platform_support.FilesystemContractTests.test_identity_swap_is_rejected_before_truncation",
    "test_platform_support.ArtifactIdentityTests.test_posix_colon_and_backslash_names_keep_their_existing_meaning",
    "test_platform_support.NativeLinuxPromotionTests.test_native_linux_exclusive_promotion_and_collision",
    "test_windows_claude.ReplacementPrimitiveTests.test_windows_state_validation_checks_original_ancestor_before_resolve",
    "test_windows_claude.PortableEvidenceBoundaryTests.test_prospective_windows_case_aliases_are_rejected_before_files_exist",
})


def _suite(bundle: Path, pattern: str, root: Path,
           environment: dict[str, str]) -> dict[str, Any]:
    """Require native cases, allowing only explicitly named non-Windows tests."""
    stage = "suite:" + pattern
    result = _run(
        [sys.executable, "-I", "-B", "-c", _SUITE_SCRIPT,
         str(bundle / "ecosystem/tests"), pattern],
        cwd=root, environment=environment, stage=stage, timeout=300,
    )
    values = _object(result, stage)
    executed, skipped = values.get("executed"), values.get("skipped")
    count = values.get("tests")
    if (type(count) is not int or count < 1 or not isinstance(executed, list)
            or not all(isinstance(item, str) for item in executed)
            or not isinstance(skipped, list)
            or not all(isinstance(item, str) for item in skipped)):
        raise ProbeError(stage, "invalid_test_execution_report")
    unexpected = set(skipped) - _POSIX_ONLY_SKIPS
    if unexpected:
        raise ProbeError(stage, "required_windows_tests_were_skipped",
                         output=result.stdout + result.stderr)
    required_class, minimum = {
        "test_platform_support.py": ("NativeWindowsContractTests", 7),
        "test_windows_claude.py": ("NativeWindowsClaudeTests", 9),
    }[pattern]
    native = {item for item in executed
              if "." + required_class + "." in item and item not in skipped}
    if len(native) < minimum:
        raise ProbeError(stage, "native_windows_cases_not_executed")
    return {"tests": count, "native_windows_tests": len(native),
            "intentional_posix_skips": sorted(skipped)}


def run_probe(bundle: Path, claude: str) -> dict[str, Any]:
    """Exercise this package, with every writable path under one temporary root."""
    source = Path(__file__).absolute().parents[2]
    if bundle.absolute().resolve() != source.resolve():
        raise ProbeError("bundle", "probe_must_belong_to_the_bundle_being_tested")
    sys.path.insert(0, str(source / "ecosystem"))
    import build
    from platform_support import secure_mkdir
    from validate import validate

    manifest = build.verify_bundle(source)
    if validate(source):
        raise ProbeError("bundle", "structural_validation_failed")
    native_hooks = json.loads(
        (source / "ecosystem/claude-hooks.json").read_text(encoding="utf-8"))
    for event, groups in native_hooks["hooks"].items():
        hook = groups[0]["hooks"][0]
        if hook.get("command") != "python" or hook.get("args") != [
                "-I", PLUGIN_PLACEHOLDER + "/ecosystem/claude_hooks.py", event]:
            raise ProbeError("bundle", "windows_claude_exec_form_required")

    with tempfile.TemporaryDirectory(prefix="constellation-windows-acceptance-") as temporary:
        root = Path(temporary) / "Isolated workspace \u03a9 with spaces"
        secure_mkdir(root, mode=0o700)
        environment = _environment(root)
        native = _executable(claude, environment, "claude_executable")
        version = _run([str(native), "--version"], cwd=root,
                       environment=environment, stage="claude_version")
        version_match = re.search(rb"\b\d+\.\d+\.\d+\b", version.stdout)
        if version_match is None:
            raise ProbeError("claude_version", "unrecognised_version")

        home = root / "installed Claude home"
        secure_mkdir(home, mode=0o700)
        settings = home / "settings.json"
        settings.write_text('{"theme":"dark"}\n', encoding="utf-8")
        unrelated = home / "unrelated.txt"
        unrelated.write_text("Synthetic independently owned data.\n", encoding="utf-8")
        installer = source / "ecosystem/claude.py"
        arguments = [sys.executable, "-I", "-B", str(installer), "install",
                     "--bundle", str(source), "--claude-home", str(home)]
        before = _snapshot(home)
        preflight = _object(_run(arguments + ["--check"], cwd=root,
                                 environment=environment, stage="preflight"), "preflight")
        if preflight.get("status") != "checked" or _snapshot(home) != before:
            raise ProbeError("preflight", "preflight_modified_the_home")
        fresh = _object(_run(arguments, cwd=root, environment=environment,
                             stage="fresh_install"), "fresh_install")
        if fresh.get("status") != "installed":
            raise ProbeError("fresh_install", "expected_new_installation")
        repeated = _object(_run(arguments, cwd=root, environment=environment,
                                stage="repeat_install"), "repeat_install")
        if repeated.get("status") != "unchanged":
            raise ProbeError("repeat_install", "repeat_was_not_idempotent")
        installed = home / "skills/constellation"
        _run([str(native), "plugin", "validate", "--strict", "--json", str(installed)],
             cwd=root, environment=environment, stage="claude_plugin_schema")

        updated_source = root / "synthetic same-version update"
        shutil.copytree(source, updated_source)
        changed = updated_source / "ecosystem/README.md"
        changed.write_text(changed.read_text(encoding="utf-8") +
                           "\nSynthetic acceptance-only update.\n", encoding="utf-8")
        updated_manifest = json.loads(
            (updated_source / "bundle.json").read_text(encoding="utf-8"))
        updated_manifest["files"]["ecosystem/README.md"]["sha256"] = hashlib.sha256(
            changed.read_bytes()).hexdigest()
        (updated_source / "bundle.json").write_text(
            json.dumps(updated_manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        build.verify_bundle(updated_source)
        update_arguments = [sys.executable, "-I", "-B", str(installer), "install",
                            "--bundle", str(updated_source), "--claude-home", str(home)]
        updated = _object(_run(update_arguments, cwd=root, environment=environment,
                               stage="same_version_update"), "same_version_update")
        if (updated.get("status") != "updated" or
                (installed / "ecosystem/README.md").read_bytes() != changed.read_bytes()):
            raise ProbeError("same_version_update", "updated_bytes_not_installed")
        directory_sync = updated.get("directory_sync")
        if directory_sync not in {"supported", "unsupported"}:
            raise ProbeError("same_version_update", "directory_sync_result_missing")
        if (settings.read_text(encoding="utf-8") != '{"theme":"dark"}\n' or
                unrelated.read_text(encoding="utf-8") != "Synthetic independently owned data.\n"):
            raise ProbeError("settings_preservation", "independently_owned_files_changed")
        before = _snapshot(home)
        _run([sys.executable, "-I", "-B", str(installer), "verify",
              "--claude-home", str(home)], cwd=root, environment=environment,
             stage="installed_integrity")
        if _snapshot(home) != before:
            raise ProbeError("installed_integrity", "verification_modified_the_home")

        receiver = root / "project \u00e9 with spaces"
        receiver.mkdir()
        native_session = "acceptance-native-session"
        session = "claude-" + native_session
        check_argv = [sys.executable, "-I", "-B", "-c",
                      "from pathlib import Path; assert Path('allowed.txt').read_text(encoding='utf-8') == 'verified\\n'"]
        check_digest = hashlib.sha256(json.dumps(
            check_argv, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        plan = {
            "session_id": session, "task_id": "acceptance-task",
            "agent_id": "acceptance-coordinator", "expected_revision": 0,
            "requirements": [{
                "id": "scope", "text": "Only the declared synthetic artifact is writable.",
                "deliverables": ["allowed.txt"], "checks": ["content"],
                "acceptance": "behavior",
            }],
            "deliverables": [{"path": "allowed.txt", "profiles": [manifest["modules"][0]]}],
            "checks": [{"id": "content", "kind": "behavior",
                        "definition_sha256": check_digest}],
            "inputs": [], "depends_on": [], "risk": "quick",
            "agents": [{"agent_id": "acceptance-worker", "role": "worker"}],
        }
        cli = installed / "ecosystem/cli.py"
        _object(_run(
            [sys.executable, "-I", "-B", str(cli), "--root", str(receiver),
             "--state-dir", environment["CONSTELLATION_STATE_DIR"], "plan"],
            cwd=receiver, environment=environment, stage="synthetic_contract", payload=plan,
        ), "synthetic_contract")

        event_environment = {**environment, "CLAUDE_PLUGIN_ROOT": str(installed)}
        for filename, denied in (("allowed.txt", False), ("undeclared.txt", True)):
            event = {
                "hook_event_name": "PreToolUse", "session_id": native_session,
                "cwd": str(receiver), "tool_name": "Write",
                "tool_input": {"file_path": str(receiver / filename)},
            }
            hook = native_hooks["hooks"]["PreToolUse"][0]["hooks"][0]
            executable = _executable(hook["command"], event_environment, "hook_interpreter")
            argv = [str(executable), *[value.replace(PLUGIN_PLACEHOLDER, str(installed))
                                      for value in hook["args"]]]
            decision = _object(_run(argv, cwd=receiver, environment=event_environment,
                                    stage="direct_hook_replay", payload=event),
                               "direct_hook_replay")
            is_denied = decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
            if is_denied != denied:
                raise ProbeError("direct_hook_replay", "scope_decision_did_not_match_contract")
        # The replay does not execute a native Write tool. This local write only
        # supplies the declared synthetic artifact for the engine's content check.
        (receiver / "allowed.txt").write_text("verified\n", encoding="utf-8")
        check = {
            "session_id": session, "task_id": "acceptance-task",
            "agent_id": "acceptance-coordinator", "expected_revision": 1,
            "id": "content", "argv": check_argv,
        }
        checked = _object(_run(
            [sys.executable, "-I", "-B", str(cli), "--root", str(receiver),
             "--state-dir", environment["CONSTELLATION_STATE_DIR"], "check"],
            cwd=receiver, environment=environment, stage="synthetic_content_check", payload=check,
        ), "synthetic_content_check")
        if checked.get("status") != "passed":
            raise ProbeError("synthetic_content_check", "content_check_failed")
        suites = {
            pattern: _suite(source, pattern, root, environment)
            for pattern in ("test_platform_support.py", "test_windows_claude.py")
        }
        return {
            **UNEXERCISED_CHECKS,
            "schema": 1, "status": "passed",
            "isolated_backend_acceptance": "passed",
            "platform": "native_windows", "resources": len(manifest["files"]),
            "claude_version": version_match[0].decode("ascii"),
            "installation": "fresh_repeat_same_version_update_verified",
            "settings_and_foreign_data": "preserved", "preflight": "read_only",
            "directory_sync": directory_sync,
            "direct_hook_replays": {"declared": "allowed", "undeclared": "denied"},
            "native_claude_event_dispatch": "pending_manual_check",
            "native_model_quality": "not_evaluated",
            "provider_or_model_requests_issued": 0,
            "network_confinement": "not_enforced_by_this_probe",
            "real_user_home_modified": False, "windows_suites": suites,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--claude", default="claude",
                        help="Native Claude .exe path or a name resolving to a real .exe")
    args = parser.parse_args(argv)
    if os.name != "nt" or sys.platform != "win32" or sys.version_info < (3, 11):
        print(json.dumps({**UNEXERCISED_CHECKS, "schema": 1, "status": "pending", "stage": "platform",
                          "reason": "native_windows_and_python_3_11_required",
                          "native_claude_event_dispatch": "not_executed"}))
        return 2
    try:
        result = run_probe(args.bundle, args.claude)
    except ProbeError as exc:
        print(json.dumps({**UNEXERCISED_CHECKS, "schema": 1, "status": "failed", "stage": exc.stage,
                          "reason": exc.reason, "output_sha256": exc.output_sha256}))
        return 2
    except Exception as exc:
        print(json.dumps({**UNEXERCISED_CHECKS, "schema": 1, "status": "failed", "stage": "acceptance",
                          "reason": type(exc).__name__}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
