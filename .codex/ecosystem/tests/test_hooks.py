"""Subprocess contract tests for the optional lifecycle adapter.

All identities, artifacts and event text below are synthetic fixtures. These
tests execute the installed script with JSON stdin/stdout; they do not install
hooks, grant native trust or certify the client's event dispatch. The patch
guard has deliberately limited coverage: shell and MCP writes remain outside it.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from typing import Any

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE.parent))
from ecosystem.core import Engine, Error  # noqa: E402
from ecosystem import hooks  # noqa: E402
from helpers import AVAILABLE_PROFILES, DEFAULT_PROFILE  # noqa: E402


SESSION = "synthetic-hook-session"
COORDINATOR = "synthetic-fixture-coordinator"
REVIEWER = "synthetic-fixture-reviewer"
PRIVATE_TEXT = "SYNTHETIC-PRIVATE-HOOK-CONTENT-9e4cd4"
EVENTS = {"UserPromptSubmit", "PreToolUse", "SubagentStart", "SubagentStop", "Stop"}


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def patch(name: str) -> str:
    return f"*** Begin Patch\n*** Update File: {name}\n@@\n-before\n+after\n*** End Patch"


class HookProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="synthetic-constellation-hooks-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.root = self.directory / "project"
        self.root.mkdir()
        self.state = self.directory / "state"
        self.private = self.directory / "synthetic-private-file"
        self.private.write_text(PRIVATE_TEXT)
        self.private.chmod(0o600)
        self.env = {
            "PATH": os.defpath,
            "HOME": str(self.directory / "home"),
            "CODEX_HOME": str(self.directory / "codex-home"),
            "XDG_CACHE_HOME": str(self.directory / "cache"),
        }
        self.engine = Engine(self.root, self.state)
        self.argv = [sys.executable, "-I", "-B", "-c", "raise SystemExit(0)"]

    def payload(self, event: str, **fields: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
            "session_id": SESSION,
            "cwd": str(self.root),
            "hook_event_name": event,
            "turn_id": "synthetic-turn-1",
            "transcript_path": str(self.private),
        }
        if event == "UserPromptSubmit":
            data["prompt"] = PRIVATE_TEXT
        if event == "PreToolUse":
            data.update(tool_name="apply_patch", tool_use_id="synthetic-tool-1",
                        tool_input={"command": patch("result.md")})
        if event in {"SubagentStart", "SubagentStop"}:
            data.update(agent_id="synthetic-native-worker", agent_type="ecosystem_coder")
        if event in {"Stop", "SubagentStop"}:
            data.update(stop_hook_active=False, last_assistant_message=PRIVATE_TEXT)
        if event == "SubagentStop":
            data["agent_transcript_path"] = str(self.private)
        data.update(fields)
        return data

    def run_hook(self, event: str, *, payload: dict[str, Any] | None = None,
                 raw: bytes | None = None, env: dict[str, str] | None = None,
                 state: Path | None = None, audit: bool = False,
                 audit_git: bool = False) -> dict[str, Any]:
        command = [sys.executable, "-I", "-B", str(SOURCE / "hooks.py"), event,
                   "--state-dir", str(state or self.state)]
        if audit or audit_git:
            # Audit the actual script in a fresh interpreter. A swallowed access
            # error still fails this harness, proving the forbidden attempt did
            # not merely disappear behind the adapter's exception handler.
            wrapper = """
import os, pathlib, runpy, sys
script, private, allow_git, *arguments = sys.argv[1:]
violations = []
def audit(event, values):
    forbidden = event in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.spawn'}
    if event == 'subprocess.Popen' and allow_git == 'yes':
        command = values[1]
        if isinstance(command, (list, tuple)) and len(command) > 1 and command[0] == 'git':
            readonly = {'rev-parse', 'symbolic-ref', 'remote', 'status', 'diff', 'check-ignore',
                        'ls-files', 'ls-tree', 'diff-tree', 'merge-base'}
            forbidden = command[1] not in readonly
            if command[1] == 'config':
                forbidden = len(command) < 3 or command[2] not in {'--get', '--get-all'}
    if event == 'open' and isinstance(values[0], (str, bytes, os.PathLike)):
        forbidden = forbidden or pathlib.Path(os.fsdecode(values[0])).resolve() == pathlib.Path(private)
    if forbidden:
        violations.append(event)
        raise RuntimeError('synthetic forbidden access')
sys.addaudithook(audit)
sys.argv = [script, *arguments]
try:
    runpy.run_path(script, run_name='__main__')
finally:
    if violations:
        raise SystemExit(91)
"""
            command = [sys.executable, "-I", "-B", "-c", wrapper,
                       str(SOURCE / "hooks.py"), str(self.private), "yes" if audit_git else "no", event,
                       "--state-dir", str(state or self.state)]
        content = raw if raw is not None else json.dumps(
            payload if payload is not None else self.payload(event)).encode()
        process = subprocess.run(command, input=content, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, cwd=self.root,
                                 env=env or self.env, timeout=15, check=False)
        self.assertEqual(process.returncode, 0, process.stderr.decode(errors="replace"))
        self.assertEqual(process.stderr, b"")
        result = json.loads(process.stdout)
        self.assertIsInstance(result, dict)
        self.assertNotIn(PRIVATE_TEXT.encode(), process.stdout)
        self.assertNotIn(PRIVATE_TEXT.encode(), process.stderr)
        return result

    def plan(self, task: str = "task", *, profiles: tuple[str, ...] | None = None,
             name: str = "result.md", argv: list[str] | None = None) -> None:
        (self.root / name).parent.mkdir(parents=True, exist_ok=True)
        (self.root / name).write_text("before\n")
        self.engine.execute("plan", {
            "session_id": SESSION, "task_id": task, "agent_id": COORDINATOR,
            "expected_revision": 0,
            "requirements": [{"id": "r1", "text": "Synthetic fixture is checked",
                              "deliverables": [name], "checks": ["c1"],
                              "acceptance": "editorial"}],
            "deliverables": [{"path": name, "profiles": list(profiles or (DEFAULT_PROFILE,))}],
            "checks": [{"id": "c1", "kind": "editorial",
                        "definition_sha256": canonical_digest(argv or self.argv)}],
            "inputs": [], "depends_on": [], "risk": "quick",
            "agents": [{"agent_id": REVIEWER, "role": "reviewer"}],
        })

    def status(self, task: str = "task") -> dict[str, Any]:
        return self.engine.execute("status", {
            "session_id": SESSION, "task_id": task, "agent_id": COORDINATOR,
        })

    def mutate(self, operation: str, *, task: str = "task", actor: str = COORDINATOR,
               **fields: Any) -> dict[str, Any]:
        return self.engine.execute(operation, {
            "session_id": SESSION, "task_id": task, "agent_id": actor,
            "expected_revision": self.status(task)["revision"], **fields,
        })

    def reviewed(self, *, findings: list[dict[str, Any]] | None = None) -> None:
        self.mutate("author", author=COORDINATOR, paths=["result.md"])
        check = self.mutate("check", id="c1", argv=self.argv)
        self.assertEqual(check["status"], "passed")
        token = self.mutate("review-start")["token"]
        self.mutate("review-report", actor=REVIEWER, token=token, reviewer=REVIEWER,
                    role="reviewer", focus=["correctness"], paths=["result.md"],
                    summary="Synthetic fixture assessment", evidence="Synthetic test fixture only",
                    findings=findings or [], assessments=[{
                        "requirement_id": "r1", "verdict": "satisfied", "support": "editorial",
                        "evidence": "Synthetic fixture has its expected contents",
                    }])

    def assert_warning(self, result: dict[str, Any]) -> None:
        self.assertEqual(set(result), {"systemMessage"})
        self.assertIsInstance(result["systemMessage"], str)
        self.assertTrue(result["systemMessage"])

    def assert_denied(self, result: dict[str, Any]) -> None:
        self.assertIn("hookSpecificOutput", result)
        output = result["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertNotIn("updatedInput", output)

    def test_manifest_filters_are_event_specific(self) -> None:
        manifest = json.loads((SOURCE / "hooks.json").read_text())
        self.assertEqual(set(manifest["hooks"]), EVENTS)
        for event, groups in manifest["hooks"].items():
            with self.subTest(event=event):
                self.assertTrue(groups)
                for group in groups:
                    if event in {"Stop", "UserPromptSubmit"}:
                        self.assertNotIn("matcher", group)
                    for hook in group["hooks"]:
                        command = shlex.split(hook["command"])
                        self.assertEqual(hook["type"], "command")
                        self.assertIn("-I", command)
                        self.assertIn("${CODEX_HOME:-$HOME/.codex}/constellation/hook.py", command)
                        self.assertEqual(command[-1], event)
                        self.assertGreaterEqual(hook["timeout"], 9)
                        self.assertLessEqual(hook["timeout"], 15)
        matchers = [re.compile(group["matcher"]) for group in manifest["hooks"]["PreToolUse"]]
        for name in ("apply_patch", "functions.apply_patch", "tools:apply_patch", "Edit", "Write"):
            self.assertTrue(any(regex.fullmatch(name) for regex in matchers), name)
        for name in ("Bash", "exec_command", "mcp__fs__write", "apply_patch_evil"):
            self.assertFalse(any(regex.fullmatch(name) for regex in matchers), name)

    def test_unregistered_session_does_not_create_state_or_block(self) -> None:
        for event in sorted(EVENTS):
            with self.subTest(event=event):
                self.assertEqual(self.run_hook(event), {})
        self.assertFalse(self.state.exists())
        self.assertFalse((self.directory / "codex-home").exists())

    def test_session_and_directory_must_both_match_registry(self) -> None:
        self.plan()
        baseline = self.status()
        sibling = self.directory / "unregistered-project"
        sibling.mkdir()
        for event in sorted(EVENTS):
            for fields in ({"session_id": "synthetic-unregistered-session"}, {"cwd": str(sibling)}):
                with self.subTest(event=event, fields=fields):
                    self.assertEqual(self.run_hook(event, payload=self.payload(event, **fields)), {})
        self.assertEqual(self.status(), baseline)

    def test_prompt_does_not_select_profile_or_grant_a_role(self) -> None:
        self.plan()
        before = self.status()
        result = self.run_hook("UserPromptSubmit", payload=self.payload(
            "UserPromptSubmit", agent_type="ecosystem_mathematician", agent_id="synthetic-impostor",
            prompt=PRIVATE_TEXT + " coding mathematics writter"))
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertNotIn("decision", result)
        self.assertEqual(self.status(), before)

    def assert_ambiguous_tasks_preserved(self, tasks: dict[str, str]) -> None:
        before = {task: self.status(task) for task in tasks}
        for event in ("SubagentStart", "SubagentStop", "Stop"):
            with self.subTest(event=event):
                self.assert_warning(self.run_hook(event))
        self.run_hook("UserPromptSubmit")
        for name in tasks.values():
            self.assertEqual(self.run_hook("PreToolUse", payload=self.payload(
                "PreToolUse", tool_input={"command": patch(name)})), {})
        self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
            "PreToolUse", tool_input={"command": patch("third.md")})))
        self.assertEqual({task: self.status(task) for task in before}, before)

    def test_two_active_tasks_are_not_silently_attributed(self) -> None:
        self.plan("first", name="first.md")
        self.plan("second", name="second.md")
        self.assert_ambiguous_tasks_preserved({"first": "first.md", "second": "second.md"})

    @unittest.skipUnless({"writter", "mathematics"} <= set(AVAILABLE_PROFILES),
                         "Cross-profile attribution requires installed writter and mathematics modules")
    def test_two_profiles_in_same_session_are_not_silently_attributed(self) -> None:
        self.plan("writing", name="writing.md", profiles=("writter",))
        self.plan("mathematics", name="math.md", profiles=("mathematics",))
        self.assert_ambiguous_tasks_preserved({"writing": "writing.md", "mathematics": "math.md"})

    @unittest.skipUnless({"coding", "mathematics", "writter"} <= set(AVAILABLE_PROFILES),
                         "Mixed-profile task requires all three installed modules")
    def test_mixed_profile_task_is_one_task_with_no_inferred_identity(self) -> None:
        self.plan(profiles=("coding", "mathematics", "writter"))
        result = self.run_hook("Stop")
        self.assertEqual(result["decision"], "block")
        state = self.status()
        self.assertEqual(state["stop_attempts"], 1)
        self.assertEqual(state["observed_agents"], {})
        self.assertEqual(set(state["agents"]), {COORDINATOR, REVIEWER})

    def test_native_subagent_observation_is_idempotent_and_not_authorization(self) -> None:
        self.plan()
        start = self.payload("SubagentStart")
        result = self.run_hook("SubagentStart", payload=start)
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "SubagentStart")
        state = self.status()
        self.assertEqual(state["observed_agents"], {"synthetic-native-worker": "start"})
        self.assertNotIn("synthetic-native-worker", state["agents"])
        self.run_hook("SubagentStart", payload=start)
        self.assertEqual(self.status(), state)
        self.assertEqual(self.run_hook("SubagentStop"), {})
        self.assertEqual(self.status()["observed_agents"], {"synthetic-native-worker": "stop"})
        self.assertEqual(self.status()["stop_attempts"], 0)

    def test_missing_subagent_identity_does_not_invent_one(self) -> None:
        self.plan()
        baseline = self.status()
        for event in ("SubagentStart", "SubagentStop"):
            payload = self.payload(event)
            del payload["agent_id"]
            self.assert_warning(self.run_hook(event, payload=payload))
        self.assertEqual(self.status(), baseline)

    def test_qualified_patch_names_guard_exact_paths(self) -> None:
        self.plan()
        baseline = self.status()
        for name in ("apply_patch", "functions.apply_patch", "tools:apply_patch"):
            with self.subTest(tool=name):
                self.assertEqual(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", tool_name=name)), {})
                self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", tool_name=name, tool_input={"command": patch("outside.md")})))
        self.assertEqual((self.root / "result.md").read_text(), "before\n")
        self.assertFalse((self.root / "outside.md").exists())
        self.assertEqual(self.status(), baseline)

    def test_native_patch_input_representations_have_the_same_guard(self) -> None:
        self.plan()
        for value in (patch("result.md"), {"input": patch("result.md")},
                      {"patch": patch("result.md")}, {"command": patch("result.md")}):
            with self.subTest(input_type=type(value).__name__, value=value):
                self.assertEqual(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", tool_input=value)), {})
        for value in ({"input": patch("result.md"), "command": patch("outside.md")},
                      {"file_path": "result.md", "content": "unsupported Write payload"}):
            self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
                "PreToolUse", tool_input=value)))

    def test_patch_rename_checks_both_endpoints(self) -> None:
        self.plan()
        rename = "*** Begin Patch\n*** Update File: result.md\n*** Move to: other.md\n*** End Patch"
        self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
            "PreToolUse", tool_input={"command": rename})))
        source = rename.replace("Update File: result.md", "Update File: other.md").replace(
            "Move to: other.md", "Move to: result.md")
        self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
            "PreToolUse", tool_input={"command": source})))

    def test_traversal_and_undeclared_symlink_aliases_are_denied(self) -> None:
        self.plan()
        outside = self.directory / "outside.md"
        outside.write_text("outside fixture\n")
        (self.root / "alias.md").symlink_to(self.root / "result.md")
        for name in ("../outside.md", "sub/../../outside.md", str(outside), "alias.md"):
            with self.subTest(path=name):
                self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", tool_input={"command": patch(name)})))
        self.assertEqual(outside.read_text(), "outside fixture\n")

    def symlink_parent_escape(self) -> tuple[Path, Path]:
        outside = self.directory / "outside"
        (outside / "nested").mkdir(parents=True)
        target = outside / "result.md"
        target.write_text("outside fixture\n")
        (self.root / "alias").symlink_to(outside / "nested", target_is_directory=True)
        escaped = self.root / "alias" / ".." / "result.md"
        self.assertEqual(escaped.resolve(strict=True), target)
        self.assertEqual(Path(os.path.abspath(escaped)), self.root / "result.md")
        return escaped, target

    def test_symlink_before_parent_component_cannot_redirect_patch(self) -> None:
        self.plan()
        escaped, target = self.symlink_parent_escape()
        for name in ("alias/../result.md", "alias/./../result.md", str(escaped)):
            with self.subTest(path=name):
                self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", tool_input={"command": patch(name)})))
        self.assertEqual(target.read_text(), "outside fixture\n")
        self.assertEqual((self.root / "result.md").read_text(), "before\n")

    def test_rename_endpoints_preserve_symlink_components_before_dotdot(self) -> None:
        self.plan()
        escaped, target = self.symlink_parent_escape()
        for unsafe in ("alias/../result.md", str(escaped)):
            for source, destination in ((unsafe, "result.md"), ("result.md", unsafe)):
                with self.subTest(source=source, destination=destination):
                    command = (f"*** Begin Patch\n*** Update File: {source}\n"
                               f"*** Move to: {destination}\n*** End Patch")
                    self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
                        "PreToolUse", tool_input={"command": command})))
        self.assertEqual(target.read_text(), "outside fixture\n")

    def test_cancelled_components_must_be_real_directories(self) -> None:
        self.plan()
        (self.root / "ordinary-file").write_text("not a directory\n")
        for name in ("missing-directory/../result.md", "ordinary-file/../result.md"):
            with self.subTest(path=name):
                self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", tool_input={"command": patch(name)})))

    def test_parent_components_through_real_directories_are_allowed(self) -> None:
        self.plan()
        nested = self.root / "nested"
        nested.mkdir()
        cases = ((self.root, "nested/../result.md"),
                 (self.root, str(nested / ".." / "result.md")),
                 (nested, "../result.md"))
        for cwd, name in cases:
            with self.subTest(cwd=cwd, path=name):
                self.assertEqual(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", cwd=str(cwd), tool_input={"command": patch(name)})), {})

    def test_declared_file_replaced_by_symlink_is_denied(self) -> None:
        self.plan()
        destination = self.root / "result.md"
        destination.unlink()
        destination.symlink_to(self.private)
        self.assert_denied(self.run_hook("PreToolUse", audit=True))
        self.assertEqual(self.private.read_text(), PRIVATE_TEXT)

    def test_shell_and_mcp_are_explicitly_outside_patch_guard(self) -> None:
        self.plan()
        before = self.status()
        for tool in ("Bash", "functions.exec_command", "mcp__fs__write", "apply_patch_evil"):
            with self.subTest(tool=tool):
                self.assertEqual(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", tool_name=tool, tool_input={"command": patch("outside.md")})), {})
        self.assertEqual(self.status(), before)

    def test_malformed_patch_is_denied_for_registered_task(self) -> None:
        self.plan()
        for tool_input in (None, [], {}, {"command": ""}, {"command": "not a patch"},
                           {"command": "*** Begin Patch\n*** Move to: result.md\n*** End Patch"}):
            with self.subTest(tool_input=tool_input):
                self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", tool_input=tool_input)))

    def test_stop_is_bounded_across_distinct_turns_and_replays(self) -> None:
        self.plan()
        baseline = self.status()
        for index in range(1, 6):
            payload = self.payload("Stop", turn_id=f"synthetic-turn-{index}", stop_hook_active=index > 1)
            result = self.run_hook("Stop", payload=payload, audit=True)
            if index <= 2:
                self.assertEqual(result["decision"], "block")
            else:
                self.assert_warning(result)
            after = self.status()
            self.assertEqual(after["stop_attempts"], min(index, 2))
            self.assertEqual(after["status"], "active")
            self.assertIsNone(after["closure"])
            self.assertEqual(after["checks"], {})
            self.assertEqual(after["agents"], baseline["agents"])
            self.assertEqual(after["gate"], baseline["gate"])
            self.assertTrue(after["pending"])
            self.assert_warning(self.run_hook("Stop", payload=payload))
            self.assertEqual(self.status(), after)

    def test_missing_turn_metadata_does_not_consume_continuation(self) -> None:
        self.plan()
        baseline = self.status()
        payload = self.payload("Stop")
        del payload["turn_id"]
        self.assert_warning(self.run_hook("Stop", payload=payload))
        self.assertEqual(self.status(), baseline)

    def test_partial_closure_exits_hooks_but_remains_unapproved(self) -> None:
        self.plan()
        self.mutate("close", mode="partial")
        result = self.run_hook("Stop")
        self.assertEqual(result, {})
        state = self.status()
        self.assertEqual(state["status"], "partial")
        self.assertIsNone(state["closure"])
        self.assertTrue(state["pending"])
        self.assertEqual(state["stop_attempts"], 0)
        with self.assertRaises(Error):
            self.mutate("close", mode="complete")

    def test_stop_does_not_launch_declared_checks_or_other_processes(self) -> None:
        marker = self.root / "check-was-launched"
        argv = [sys.executable, "-I", "-B", "-c",
                "from pathlib import Path; Path('check-was-launched').write_text('unexpected')"]
        self.plan(argv=argv)
        self.assertEqual(self.run_hook("Stop", audit=True)["decision"], "block")
        self.assertFalse(marker.exists())
        self.assertEqual(self.status()["checks"], {})

    def test_current_explicit_completion_allows_stop(self) -> None:
        self.plan()
        self.reviewed()
        self.mutate("close", mode="complete")
        self.assertEqual(self.run_hook("Stop", audit=True), {})
        self.assertEqual(self.status()["pending"], [])
        self.assertEqual(self.status()["stop_attempts"], 0)

    def test_closed_tasks_do_not_expand_new_task_scope_or_create_ambiguity(self) -> None:
        self.plan()
        self.reviewed()
        self.mutate("close", mode="complete")
        self.plan("partial", name="partial.md")
        self.mutate("close", task="partial", mode="partial")
        closed = {task: self.status(task) for task in ("task", "partial")}
        self.plan("next", name="next.md")
        self.assertEqual(self.run_hook("Stop")["decision"], "block")
        self.assertEqual(self.status("next")["stop_attempts"], 1)
        for name in ("result.md", "partial.md"):
            with self.subTest(closed_path=name):
                self.assert_denied(self.run_hook("PreToolUse", payload=self.payload(
                    "PreToolUse", tool_input={"command": patch(name)})))
        self.assertEqual(self.run_hook("PreToolUse", payload=self.payload(
            "PreToolUse", tool_input={"command": patch("next.md")})), {})
        self.run_hook("SubagentStart")
        self.assertEqual(self.status("next")["observed_agents"], {"synthetic-native-worker": "start"})
        self.assertEqual({task: self.status(task) for task in closed}, closed)

    def test_evidence_without_explicit_closure_cannot_complete_via_stop(self) -> None:
        self.plan()
        self.reviewed()
        self.assertEqual(self.status()["pending"], [])
        self.assertEqual(self.run_hook("Stop")["decision"], "block")
        self.assertEqual(self.status()["status"], "active")
        self.assertIsNone(self.status()["closure"])

    def test_changed_artifact_invalidates_active_review_evidence(self) -> None:
        self.plan()
        self.reviewed()
        (self.root / "result.md").write_text("changed after review\n")
        self.assertEqual(self.run_hook("Stop")["decision"], "block")
        self.assertTrue(self.status()["pending"])
        with self.assertRaises(Error):
            self.mutate("close", mode="complete")

    def test_latest_failed_check_blocks_after_prior_success(self) -> None:
        argv = [sys.executable, "-I", "-B", "-c",
                "from pathlib import Path; raise SystemExit(int(Path('fail-check').exists()))"]
        self.argv = argv
        self.plan(argv=argv)
        self.reviewed()
        (self.root / "fail-check").write_text("synthetic failure switch\n")
        self.assertEqual(self.mutate("check", id="c1", argv=argv)["status"], "failed")
        self.assertEqual(self.run_hook("Stop")["decision"], "block")
        self.assertEqual(self.status()["checks"]["c1"]["status"], "failed")
        self.assertIsNone(self.status()["closure"])

    def test_open_finding_blocks_even_with_positive_assessment(self) -> None:
        self.plan()
        self.reviewed(findings=[{
            "id": "synthetic-open-finding", "path": "result.md", "line": 1,
            "severity": "high", "origin": "introduced", "scenario": "Synthetic failing scenario",
            "consequence": "Synthetic acceptance remains blocked", "evidence": "Synthetic counterexample",
        }])
        self.assertEqual(self.run_hook("Stop")["decision"], "block")
        self.assertTrue(self.status()["pending"])
        with self.assertRaises(Error):
            self.mutate("close", mode="complete")

    def test_private_event_fields_are_neither_read_nor_persisted(self) -> None:
        self.plan()
        for event in ("UserPromptSubmit", "SubagentStart", "SubagentStop", "PreToolUse", "Stop"):
            with self.subTest(event=event):
                self.run_hook(event, audit=True)
        self.assertEqual(self.private.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.private.read_text(), PRIVATE_TEXT)
        for path in self.state.rglob("*"):
            if path.is_file():
                self.assertNotIn(PRIVATE_TEXT.encode(), path.read_bytes())
                self.assertNotIn(str(self.private).encode(), path.read_bytes())
        database = self.state / "ecosystem.sqlite3"
        self.assertEqual(database.stat().st_mode & 0o077, 0)
        self.assertEqual(self.state.stat().st_mode & 0o077, 0)
        self.assertFalse((self.directory / "codex-home").exists())

    def test_payload_and_cwd_cannot_select_executable_engine(self) -> None:
        self.plan()
        marker = self.root / "injected-engine-ran"
        malicious = "from pathlib import Path\nPath('injected-engine-ran').write_text('unexpected')\n"
        (self.root / "core.py").write_text(malicious)
        (self.root / "hooks.py").write_text(malicious)
        module = self.root / "ecosystem"
        module.mkdir()
        (module / "__init__.py").write_text(malicious)
        (module / "core.py").write_text(malicious)
        environment = {**self.env, "PYTHONPATH": str(self.root),
                       "CONSTELLATION_ENGINE": str(self.root / "core.py")}
        data = self.payload("Stop", engine_path=str(self.root / "core.py"),
                            executable=str(self.root / "hooks.py"),
                            command=[sys.executable, str(self.root / "hooks.py")])
        self.assertEqual(self.run_hook("Stop", payload=data, env=environment, audit=True)["decision"], "block")
        self.assertFalse(marker.exists())

    def test_malformed_oversized_and_mismatched_events_do_not_mutate(self) -> None:
        self.plan()
        baseline = self.status()
        cases = [b"{", b"[]", b"null", b"\xff", b'{"session_id":"a","session_id":"b"}',
                 b'{"number":NaN}', b" " * (1024 * 1024 + 1), b"[" * 2000 + b"]" * 2000]
        for raw in cases:
            with self.subTest(size=len(raw), prefix=raw[:20]):
                self.assert_warning(self.run_hook("Stop", raw=raw))
                self.assert_denied(self.run_hook("PreToolUse", raw=raw))
        self.assert_warning(self.run_hook("Stop", payload=self.payload("SubagentStart")))
        self.assert_warning(self.run_hook("Stop", payload=self.payload("UnknownEvent")))
        self.assert_denied(self.run_hook("PreToolUse", payload=self.payload("UnknownEvent")))
        self.assertEqual(self.status(), baseline)

    def test_corrupt_or_symlinked_state_never_signals_completion(self) -> None:
        corrupt = self.directory / "corrupt-state"
        corrupt.mkdir(mode=0o700)
        database = corrupt / "ecosystem.sqlite3"
        database.write_bytes(b"synthetic invalid database")
        self.assert_warning(self.run_hook("Stop", state=corrupt))
        self.assert_denied(self.run_hook("PreToolUse", state=corrupt))
        database.unlink()
        database.symlink_to(self.private)
        self.assert_warning(self.run_hook("Stop", state=corrupt, audit=True))
        self.assert_denied(self.run_hook("PreToolUse", state=corrupt, audit=True))
        self.assertEqual(self.private.read_text(), PRIVATE_TEXT)

    def make_git(self, root: Path | None = None) -> Any:
        """Create a real disposable Git recipient; never install any native hooks."""
        from ecosystem.runtime.workflow import Workflow

        root = root or self.root
        root.mkdir(parents=True, exist_ok=True)
        remote = self.directory / (root.name + "-remote.git")
        def git(*arguments: str) -> None:
            subprocess.run(["git", *arguments], cwd=root, env=self.env,
                           capture_output=True, check=True)
        git("init", "--bare", "-q", str(remote))
        git("init", "-q", "-b", "main")
        git("config", "user.name", "Synthetic hook fixture")
        git("config", "user.email", "hook-fixture@example.invalid")
        git("config", "core.hooksPath", str(root / ".git/hooks"))
        git("config", "commit.gpgsign", "false")
        (root / "result.md").write_text("before\n")
        git("add", "result.md")
        git("commit", "-qm", "Create synthetic fixture")
        git("remote", "add", "origin", str(remote))
        git("push", "-qu", "origin", "main")
        return Workflow(root, SESSION, create_state=False)

    def git_plan(self, root: Path | None = None) -> Any:
        flow = self.make_git(root)
        flow.home.mkdir(mode=0o700)
        flow.begin("synthetic-setup-turn")
        flow.plan({"requirements": ["Synthetic result is checked"], "paths": ["result.md"]})
        return flow

    def large_git_snapshot(self, state: dict[str, Any]) -> dict[str, Any]:
        paths = ["result.md"] + [
            f"11_Documents_and_Reports/Research_Repositories/synthetic/files/docs/report-{index:04}.md"
            for index in range(3799)
        ]
        snapshot = {name: "0" * 64 for name in paths}
        return {**state, "paths": paths, "checks": [
            {"status": "passed", "snapshot": snapshot} for _ in range(2)
        ]}

    def assert_large_git_scope(self, root: Path, path: Path, state: dict[str, Any]) -> None:
        baseline = path.read_bytes()
        self.assertGreater(len(baseline), hooks.MAX_INPUT_BYTES)
        self.assertLessEqual(len(baseline), hooks.MAX_GIT_STATE_BYTES)
        for name in (state["paths"][0], state["paths"][-1]):
            with self.subTest(path=name):
                self.assertEqual(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
                    "PreToolUse", tool_input={"command": patch(str(root / name))})), {})
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
            "PreToolUse", tool_input={"command": patch(str(root / "undeclared.md"))})))
        self.assertEqual(path.read_bytes(), baseline)

    def test_large_git_contract_keeps_exact_patch_scope(self) -> None:
        flow = self.git_plan()
        state = self.large_git_snapshot(flow.load())
        flow.save(state)
        self.assert_large_git_scope(self.root, flow.path, state)

    def test_large_legacy_peer_contract_keeps_exact_patch_scope(self) -> None:
        self.git_plan()
        root, path, state = self.legacy_peer()
        state = self.large_git_snapshot(state)
        path.write_text(json.dumps(state, indent=2))
        self.assert_large_git_scope(root, path, state)

    def test_git_metadata_has_a_separate_bounded_strict_json_budget(self) -> None:
        path = self.directory / "synthetic-metadata.json"
        prefix, suffix = b'{"padding":"', b'"}'
        raw = prefix + b" " * (hooks.MAX_GIT_STATE_BYTES - len(prefix) - len(suffix)) + suffix
        self.assertEqual(len(raw), hooks.MAX_GIT_STATE_BYTES)
        path.write_bytes(raw)
        self.assertEqual(hooks._git_state(path), {"padding": " " * (
            hooks.MAX_GIT_STATE_BYTES - len(prefix) - len(suffix))})
        path.write_bytes(raw + b" ")
        with mock.patch.object(hooks.json, "loads") as parser:
            with self.assertRaisesRegex(hooks.HookError, "Git lifecycle metadata exceeds the byte limit"):
                hooks._git_state(path)
            parser.assert_not_called()
        cases = (
            (b'{"key":1,"key":2}', "contains duplicate JSON keys"),
            (b'{"nested":{"key":1,"key":2}}', "contains duplicate JSON keys"),
            (b'{"number":NaN}', "contains a nonfinite JSON number"),
            (b"[]", "must be a JSON object"),
            (b"\xff", "is not strict UTF-8 JSON"),
        )
        for payload, reason in cases:
            with self.subTest(reason=reason, payload=payload):
                path.write_bytes(b" " * hooks.MAX_INPUT_BYTES + payload)
                with self.assertRaisesRegex(hooks.HookError, "Git lifecycle metadata " + reason):
                    hooks._git_state(path)

    def test_large_git_metadata_does_not_expand_standard_input_limit(self) -> None:
        flow = self.git_plan()
        state = self.large_git_snapshot(flow.load())
        flow.save(state)
        baseline = flow.path.read_bytes()
        for event in ("PreToolUse", "Stop"):
            with self.subTest(event=event):
                raw = json.dumps(self.payload(event)).encode()
                raw += b" " * (hooks.MAX_INPUT_BYTES + 1 - len(raw))
                self.assertEqual(len(raw), hooks.MAX_INPUT_BYTES + 1)
                result = self.run_hook(event, raw=raw)
                if event == "PreToolUse":
                    self.assert_denied(result)
                    diagnostic = result["hookSpecificOutput"]["permissionDecisionReason"]
                else:
                    self.assert_warning(result)
                    diagnostic = result["systemMessage"]
                self.assertIn("hook input exceeds the byte limit", diagnostic)
        self.assertEqual(flow.path.read_bytes(), baseline)

    def legacy_peer(self) -> tuple[Path, Path, dict[str, Any]]:
        root = self.directory / "legacy-peer"
        flow = self.git_plan(root)
        state = flow.load()
        directory = flow.home.parent / "omaros"
        directory.mkdir(mode=0o700)
        path = directory / flow.path.name
        path.write_text(json.dumps(state))
        flow.path.unlink()
        return root, path, state

    def test_independent_git_peer_requires_its_own_active_contract(self) -> None:
        self.git_plan()
        peer = self.directory / "git-peer"
        flow = self.git_plan(peer)
        payload = self.payload("PreToolUse", tool_input={"command": patch(str(peer / "result.md"))})
        self.assertEqual(self.run_hook("PreToolUse", payload=payload, audit_git=True), {})
        state = flow.load()
        state["finished"] = {"at": "synthetic-closed-fixture"}
        flow.save(state)
        self.assert_denied(self.run_hook("PreToolUse", payload=payload, audit_git=True))

    def test_legacy_peer_permits_only_same_session_exact_declared_paths(self) -> None:
        self.git_plan()
        peer, path, _state = self.legacy_peer()
        baseline = path.read_bytes()
        payload = self.payload("PreToolUse", tool_input={"command": patch(str(peer / "result.md"))})
        self.assertEqual(self.run_hook("PreToolUse", payload=payload, audit_git=True), {})
        self.assertEqual(path.read_bytes(), baseline)
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
            "PreToolUse", tool_input={"command": patch(str(peer / "undeclared.md"))})))
        other = path.with_name(hashlib.sha256(b"synthetic-other-session").hexdigest()[:24] + ".json")
        path.rename(other)
        self.assert_denied(self.run_hook("PreToolUse", payload=payload, audit_git=True))
        self.assertEqual(other.read_bytes(), baseline)

    def test_legacy_peer_rejects_changed_target_failed_sync_and_malformed_state(self) -> None:
        self.git_plan()
        peer, path, state = self.legacy_peer()
        payload = self.payload("PreToolUse", tool_input={"command": patch(str(peer / "result.md"))})
        for fields in ({"target": {**state["target"], "branch": "synthetic-wrong-branch"}},
                       {"sync_error": "synthetic sync failure"}, {"sync": {}},
                       {"sync": {**state["sync"], "behind": 1}},
                       {"sync": {**state["sync"], "remote": "synthetic-other-remote"}},
                       {"paths": "result.md"},
                       {"requirements": "not a requirements list"}, {"finished": {"at": "closed"}}):
            with self.subTest(fields=fields):
                path.write_text(json.dumps({**state, **fields}))
                self.assert_denied(self.run_hook("PreToolUse", payload=payload, audit_git=True))
        path.write_text("{invalid")
        self.assert_denied(self.run_hook("PreToolUse", payload=payload, audit_git=True))
        path.unlink()
        path.symlink_to(self.private)
        self.assert_denied(self.run_hook("PreToolUse", payload=payload, audit_git=True))

    def test_legacy_peer_preserves_private_and_symlink_boundaries(self) -> None:
        self.git_plan()
        peer, path, state = self.legacy_peer()
        private_name = "09_data_sources/email_exports/index.json"
        path.write_text(json.dumps({**state, "paths": ["result.md", private_name]}))
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
            "PreToolUse", tool_input={"command": patch(str(peer / private_name))})))
        (peer / "result.md").unlink()
        (peer / "result.md").symlink_to(self.private)
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
            "PreToolUse", tool_input={"command": patch(str(peer / "result.md"))})))

    def test_mixed_patch_rejects_any_undeclared_external_endpoint(self) -> None:
        flow = self.git_plan()
        peer, path, _state = self.legacy_peer()
        baseline, peer_baseline = flow.path.read_bytes(), path.read_bytes()
        command = ("*** Begin Patch\n*** Update File: result.md\n@@\n-before\n+after\n"
                   f"*** Update File: {peer / 'result.md'}\n*** Move to: {peer / 'outside.md'}\n*** End Patch")
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
            "PreToolUse", tool_input={"command": command})))
        self.assertEqual(flow.path.read_bytes(), baseline)
        self.assertEqual(path.read_bytes(), peer_baseline)
        self.assertEqual((self.root / "result.md").read_text(), "before\n")
        self.assertEqual((peer / "result.md").read_text(), "before\n")

    def test_minimal_git_project_needs_no_scaffold_or_hook_state(self) -> None:
        flow = self.make_git()
        for event in sorted(EVENTS):
            self.assertEqual(self.run_hook(event, audit_git=True), {})
        self.assertFalse(flow.home.exists())
        self.assertFalse(self.state.exists())
        self.assertFalse((self.root / ".codex").exists())

    def test_git_prompt_and_subagent_events_are_read_only(self) -> None:
        flow = self.git_plan()
        before = {path.name: path.read_bytes() for path in flow.home.iterdir() if path.is_file()}
        for event in ("UserPromptSubmit", "SubagentStart", "SubagentStop"):
            result = self.run_hook(event, audit_git=True)
            if event != "SubagentStop":
                self.assertEqual(result["hookSpecificOutput"]["hookEventName"], event)
        after = {path.name: path.read_bytes() for path in flow.home.iterdir() if path.is_file()}
        self.assertEqual(after, before)
        self.assertFalse(self.state.exists())
        self.assertFalse((self.directory / "codex-home").exists())

    def test_git_guard_checks_scope_upstream_and_original_components(self) -> None:
        flow = self.git_plan()
        self.assertEqual(self.run_hook("PreToolUse", audit_git=True), {})
        self.symlink_parent_escape()
        for name in ("outside.md", "alias/../result.md", "missing/../result.md"):
            self.assert_denied(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
                "PreToolUse", tool_input={"input": patch(name)})))
        rename = "*** Begin Patch\n*** Update File: result.md\n*** Move to: outside.md\n*** End Patch"
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
            "PreToolUse", tool_input={"patch": rename})))
        state = flow.load()
        state["target"]["branch"] = "synthetic-other-branch"
        flow.save(state)
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True))

    def test_git_stop_is_bounded_idempotent_and_never_publishes(self) -> None:
        flow = self.git_plan()
        self.assertEqual(self.run_hook("Stop", audit_git=True)["decision"], "block")
        self.assertEqual(flow.load()["stop_attempts"], 1)
        replay = self.run_hook("Stop", audit_git=True)
        self.assertNotEqual(replay.get("decision"), "block")
        self.assertIn("INCOMPLETE", replay.get("systemMessage", ""))
        self.assertEqual(flow.load()["stop_attempts"], 1)
        self.assertEqual(self.run_hook("Stop", audit_git=True, payload=self.payload(
            "Stop", stop_hook_active=True))["decision"], "block")
        result = self.run_hook("Stop", audit_git=True, payload=self.payload(
            "Stop", turn_id="synthetic-second-turn"))
        self.assertNotEqual(result.get("decision"), "block")
        self.assertEqual(flow.load()["stop_attempts"], 3)
        self.assertFalse(flow.load().get("finished"))

    @unittest.skipUnless(hasattr(signal, "setitimer"), "POSIX internal hook deadline")
    def test_busy_git_lifecycle_denies_with_deadline_diagnostic(self) -> None:
        flow = self.git_plan()
        before = flow.path.read_bytes()
        with flow.lock():
            result = self.run_hook("PreToolUse", audit_git=True)
        self.assert_denied(result)
        self.assertIn("deadline", result["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertEqual(flow.path.read_bytes(), before)

    def test_finished_git_contracts_do_not_reopen_on_new_prompt(self) -> None:
        flow = self.git_plan()
        state = flow.load()
        state["finished"] = {"at": "synthetic-completed-fixture"}
        flow.save(state)
        baseline = flow.path.read_bytes()
        for event in sorted(EVENTS):
            self.assertEqual(self.run_hook(event, audit_git=True), {})
        self.assertEqual(flow.path.read_bytes(), baseline)

    def test_git_portable_conflict_is_explicit_and_never_falls_back(self) -> None:
        flow = self.git_plan()
        self.plan()
        before_git, before_portable = flow.path.read_bytes(), self.status()
        for event in sorted(EVENTS):
            result = self.run_hook(event, audit_git=True)
            if event == "PreToolUse":
                self.assert_denied(result)
            else:
                self.assert_warning(result)
        self.assertEqual(flow.path.read_bytes(), before_git)
        self.assertEqual(self.status(), before_portable)

    def test_corrupt_or_symlinked_git_state_rejects_guarded_edits(self) -> None:
        flow = self.git_plan()
        flow.path.write_text("{invalid")
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True))
        self.assert_warning(self.run_hook("Stop", audit_git=True))
        flow.path.unlink()
        flow.path.symlink_to(self.private)
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True))
        self.assert_warning(self.run_hook("Stop", audit_git=True))

    def test_git_project_cannot_supply_executable_hook_modules(self) -> None:
        self.git_plan()
        marker = self.root / "injected-engine-ran"
        malicious = "from pathlib import Path\nPath('injected-engine-ran').write_text('unexpected')\n"
        (self.root / ".codex").mkdir()
        for name in ("workflow.py", ".codex/workflow.py", "workspace.py", "review_gate.py"):
            (self.root / name).write_text(malicious)
        self.assertEqual(self.run_hook("PreToolUse", audit_git=True), {})
        self.assertEqual(self.run_hook("Stop", audit_git=True)["decision"], "block")
        self.assertFalse(marker.exists())

    def test_workspace_routes_from_participant_without_duplicate_lifecycle(self) -> None:
        from ecosystem.runtime.workspace import Workspace

        self.make_git()
        child = self.root / "child"
        self.make_git(child)
        unrelated = self.root / "unrelated"
        self.make_git(unrelated)
        (self.root / ".codex").mkdir()
        (self.root / ".codex/repositories.json").write_text(json.dumps({
            "schema_version": 1, "repositories": [
                {"path": name, "management": "native"} for name in (".", "child", "unrelated")],
        }))
        workspace = Workspace(self.root, SESSION)
        workspace.plan({"requirements": ["Synthetic child result is checked"],
                        "paths": ["child/result.md"]})
        before = workspace.path.read_bytes()
        for location in (self.root, child):
            with self.subTest(cwd=location):
                result = self.run_hook("UserPromptSubmit", audit_git=True, payload=self.payload(
                    "UserPromptSubmit", cwd=str(location)))
                self.assertIn("workspace", result["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(workspace.path.read_bytes(), before)
        self.assertEqual(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
            "PreToolUse", cwd=str(child))), {})
        self.assert_denied(self.run_hook("PreToolUse", audit_git=True, payload=self.payload(
            "PreToolUse", cwd=str(child), tool_input={"command": patch("../result.md")})))
        for event in sorted(EVENTS):
            self.assertEqual(self.run_hook(event, audit_git=True, payload=self.payload(
                event, cwd=str(unrelated))), {})
        stopped = self.run_hook("Stop", audit_git=True, payload=self.payload("Stop", cwd=str(child)))
        self.assertEqual(stopped["decision"], "block")
        self.assertEqual(workspace.load()["stop_attempts"], 1)

    def test_child_only_workspace_does_not_hide_independent_hub_contract(self) -> None:
        from ecosystem.runtime.workspace import Workspace

        flow = self.git_plan()
        self.make_git(self.root / "child")
        (self.root / ".codex").mkdir()
        (self.root / ".codex/repositories.json").write_text(json.dumps({
            "schema_version": 1, "repositories": [
                {"path": name, "management": "native"} for name in (".", "child")],
        }))
        workspace = Workspace(self.root, SESSION)
        workspace.plan({"requirements": ["Independent child result is checked"],
                        "paths": ["child/result.md"]})
        before = (flow.path.read_bytes(), workspace.path.read_bytes())
        for event in sorted(EVENTS):
            result = self.run_hook(event, audit_git=True)
            if event == "PreToolUse":
                self.assert_denied(result)
            else:
                self.assert_warning(result)
        self.assertEqual((flow.path.read_bytes(), workspace.path.read_bytes()), before)

    @unittest.skipUnless(hasattr(signal, "setitimer"), "POSIX internal hook deadline")
    def test_stalled_stdin_returns_warning_within_native_timeout(self) -> None:
        # Leave stdin open: successful termination must come from the adapter's
        # real deadline, not from EOF or a synthetic signal/mocked timer.
        started = time.monotonic()
        process = subprocess.Popen(
            [sys.executable, "-I", "-B", str(SOURCE / "hooks.py"), "Stop",
             "--state-dir", str(self.state)], cwd=self.root, env=self.env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            process.wait(timeout=12)
            self.assertEqual(process.returncode, 0)
            self.assertGreater(time.monotonic() - started, 5)
            self.assert_warning(json.loads(process.stdout.read()))
            self.assertEqual(process.stderr.read(), b"")
            self.assertFalse(self.state.exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()


if __name__ == "__main__":
    unittest.main()
