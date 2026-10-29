"""Synthetic native payloads exercise real shared Git and portable evidence gates.

These checks do not establish interactive Claude trust, model behaviour or native
event dispatch. All state, repositories, remotes and event content are fixtures.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(SOURCE.parent))
from ecosystem import claude_hooks as adapter, hooks
from helpers import Scenario


NATIVE = "fixture-claude-session"
SESSION = "claude-" + NATIVE
PRIVATE = "SYNTHETIC-PRIVATE-CLAUDE-EVENT-4f538"


class ClaudeAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="claude-native-adapter-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "project with spaces"
        self.root.mkdir()
        self.state = self.base / "isolated-state"
        self.environment = mock.patch.dict(os.environ, {"CONSTELLATION_HOOK_OWNER": "shared"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def payload(self, event: str, **changes: object) -> dict:
        value = {"hook_event_name": event, "session_id": NATIVE, "cwd": str(self.root),
                 "prompt": PRIVATE, "transcript_path": PRIVATE, "last_assistant_message": PRIVATE,
                 "agent_transcript_path": PRIVATE, "tool_input": {"file_path": "result.md", "content": PRIVATE},
                 "tool_name": "Write", "agent_id": "fixture-native-worker", "stop_hook_active": False}
        value.update(changes)
        return value

    def handle(self, event: str, **changes: object) -> dict:
        return adapter.handle_event(self.payload(event, **changes), self.state, event)

    def denied(self, result: dict) -> None:
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def scenario(self) -> Scenario:
        scenario = Scenario(root=self.root, state_dir=self.state, session=SESSION)
        self.addCleanup(scenario.cleanup)
        scenario.plan()
        return scenario

    def test_bootstrap_is_relocatable_and_does_not_create_a_task(self) -> None:
        relocated = self.base / "a different laptop" / "research centre"
        result = adapter.handle_event(self.payload("SessionStart"), self.state, "SessionStart",
                                      package_root=relocated)
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn(str(relocated / "ecosystem/cli.py"), context)
        self.assertIn("--session " + SESSION, context)
        self.assertIn("actual native author/reviewer identity", context)
        self.assertNotIn(PRIVATE, json.dumps(result))
        self.assertFalse(self.state.exists())
        self.assertFalse((self.root / ".codex").exists())

    def test_unregistered_events_remain_proportional_and_do_not_create_state(self) -> None:
        for event in sorted(adapter.EVENTS):
            with self.subTest(event=event):
                result = self.handle(event)
                if event in {"SessionStart", "UserPromptSubmit"}:
                    self.assertEqual(result["hookSpecificOutput"]["hookEventName"], event)
                else:
                    self.assertEqual(result, {})
        self.assertFalse(self.state.exists())

    def test_shared_method_guidance_does_not_infer_scope_from_private_prompt(self) -> None:
        class StructuralOnly(dict):
            def get(self, key, default=None):
                if key in {"prompt", "transcript_path", "last_assistant_message"}:
                    raise AssertionError("Private content must not select methods")
                return super().get(key, default)

        for event in ("SessionStart", "UserPromptSubmit"):
            result = adapter.handle_event(StructuralOnly(self.payload(event)), self.state, event)
            context = result["hookSpecificOutput"]["additionalContext"]
            self.assertEqual(context.count(hooks.METHOD_GUIDANCE), 1)
            self.assertIn("native Skill tool", context)
            self.assertNotIn(PRIVATE, context)
        self.assertFalse(self.state.exists())
        scenario = self.scenario()
        before = scenario.call("status")
        context = self.handle("UserPromptSubmit")["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(context.count(hooks.METHOD_GUIDANCE), 1)
        self.assertEqual(scenario.call("status"), before)
        self.denied(self.handle("PreToolUse", tool_input={"file_path": "undeclared.md"}))

    def test_only_structural_fields_reach_shared_dispatch(self) -> None:
        for tool, field in adapter.FILE_TOOLS.items():
            with self.subTest(tool=tool), mock.patch.object(hooks, "handle_event", return_value={}) as dispatch:
                result = self.handle("PreToolUse", tool_name=tool,
                                     tool_input={field: "result.md", "content": PRIVATE, "edits": PRIVATE})
                self.assertEqual(result, {})
                clean = dispatch.call_args.args[0]
                self.assertEqual(set(clean), {"hook_event_name", "session_id", "cwd", "turn_id", "tool_name", "tool_input"})
                self.assertEqual(clean["session_id"], SESSION)
                self.assertEqual(clean["turn_id"], "claude-native")
                self.assertEqual(clean["tool_name"], "apply_patch")
                self.assertNotIn(PRIVATE, json.dumps(clean))
                self.assertIn(str(self.root / "result.md"), clean["tool_input"])

    def test_portable_file_guards_cover_all_native_editors(self) -> None:
        self.scenario()
        for tool, field in adapter.FILE_TOOLS.items():
            with self.subTest(tool=tool):
                self.assertEqual(self.handle("PreToolUse", tool_name=tool, tool_input={field: "result.md"}), {})
                self.denied(self.handle("PreToolUse", tool_name=tool, tool_input={field: "undeclared.md"}))
                self.denied(self.handle("PreToolUse", tool_name=tool,
                                        tool_input={field: str(self.base / "outside.md")}))

    def test_traversal_controls_and_symlink_components_are_rejected(self) -> None:
        self.scenario()
        for name in ("../result.md", "nested/../result.md", "result.md\n*** Update File: other.md", "\x00bad", " result.md"):
            with self.subTest(name=name), self.assertRaises(adapter.AdapterError):
                self.handle("PreToolUse", tool_input={"file_path": name})
        (self.root / "alias").symlink_to(self.base, target_is_directory=True)
        self.denied(self.handle("PreToolUse", tool_input={"file_path": "alias/result.md"}))

    def test_native_agent_observation_preserves_real_identity_and_private_content(self) -> None:
        scenario = self.scenario()
        self.handle("SubagentStart")
        state = scenario.call("status")
        self.assertEqual(state["observed_agents"], {"fixture-native-worker": "start"})
        self.handle("SubagentStop")
        state = scenario.call("status")
        self.assertEqual(state["observed_agents"], {"fixture-native-worker": "stop"})
        for path in self.state.iterdir():
            if path.is_file():
                self.assertNotIn(PRIVATE.encode(), path.read_bytes())

    def test_other_native_sessions_do_not_inherit_registered_paths(self) -> None:
        scenario = self.scenario()
        before = scenario.call("status")
        self.assertEqual(self.handle("PreToolUse", session_id="unregistered-native-session",
                                     tool_input={"file_path": "other.md"}), {})
        self.assertEqual(scenario.call("status"), before)

    def test_stop_replay_is_bounded_and_completed_task_stays_closed(self) -> None:
        scenario = self.scenario()
        self.assertEqual(self.handle("Stop")["decision"], "block")
        self.assertNotEqual(self.handle("Stop").get("decision"), "block")
        scenario.call("status")
        scenario.approve()
        scenario.close()
        self.assertEqual(self.handle("Stop"), {})
        self.assertEqual(scenario.call("status")["status"], "complete")

    def test_project_owner_bypasses_shared_import_and_malformed_payload(self) -> None:
        with mock.patch.dict(os.environ, {"CONSTELLATION_HOOK_OWNER": "project"}), mock.patch.object(hooks, "handle_event") as dispatch:
            self.assertEqual(adapter.handle_event(None, self.state), {})
            dispatch.assert_not_called()
        self.assertFalse(self.state.exists())

    def test_malformed_native_metadata_is_rejected(self) -> None:
        invalid = ({"session_id": "../outside"}, {"session_id": "x" * 122}, {"cwd": "relative"},
                   {"hook_event_name": "Stop"}, {"session_id": None})
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(adapter.AdapterError):
                self.handle("PreToolUse", **changes)
        with self.assertRaises(adapter.AdapterError):
            self.handle("Stop", stop_hook_active="yes")

    def git_plan(self):
        from ecosystem.runtime.workflow import Workflow
        remote = self.base / "remote.git"
        def git(*args: str) -> None:
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        git("init", "--bare", "-q", str(remote))
        git("init", "-q", "-b", "main")
        git("config", "user.name", "Synthetic Claude fixture")
        git("config", "user.email", "fixture@example.invalid")
        git("config", "core.hooksPath", str(self.root / ".git/hooks"))
        git("config", "commit.gpgsign", "false")
        (self.root / "result.md").write_text("fixture\n")
        git("add", "result.md")
        git("commit", "-qm", "Create synthetic fixture")
        git("remote", "add", "origin", str(remote))
        git("push", "-qu", "origin", "main")
        flow = Workflow(self.root, SESSION)
        flow.begin("synthetic-setup")
        flow.plan({"requirements": ["Synthetic result is checked"], "paths": ["result.md"]})
        return flow

    def test_real_git_contract_is_shared_without_project_code_import(self) -> None:
        flow = self.git_plan()
        self.assertEqual(self.handle("PreToolUse"), {})
        self.denied(self.handle("PreToolUse", tool_input={"file_path": "undeclared.md"}))
        self.assertIn(SESSION, self.handle("UserPromptSubmit")["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.handle("Stop")["decision"], "block")
        self.assertFalse(flow.load().get("finished"))
        self.assertFalse(self.state.exists())


class ClaudeLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="claude-verified-loader-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()

    def release(self, *, installed: bool = False) -> Path:
        root = self.base / "home" / "skills" / "constellation" if installed else self.base / "bundle"
        resources = {
            "ecosystem/claude_hooks.py": (SOURCE / "claude_hooks.py").read_bytes(),
            ".claude-plugin/plugin.json": json.dumps({"name": "constellation", "version": "1.3.0"}).encode(),
            ".codex-plugin/plugin.json": json.dumps({"name": "constellation", "version": "1.3.0"}).encode(),
            "ecosystem/hooks.py": b"raise RuntimeError('synthetic unimported package')\n",
        }
        records = {}
        for relative, content in resources.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(0o644)
            records[relative] = {"sha256": hashlib.sha256(content).hexdigest(), "mode": 0o644}
        manifest = {"schema": 1, "modules": ["coding"], "files": records}
        (root / "bundle.json").write_text(json.dumps(manifest))
        (root / "bundle.json").chmod(0o644)
        if installed:
            receipt = {"schema": 1, "owner": "constellation-claude-skills-dir", "plugin_id": "constellation@skills-dir",
                       "version": "1.3.0", "modules": ["coding"],
                       "bundle_sha256": hashlib.sha256((root / "bundle.json").read_bytes()).hexdigest()}
            (root / adapter.MARKER).write_text(json.dumps(receipt))
            (root / adapter.MARKER).chmod(0o600)
            lock = root.parent.parent / "constellation/.install.lock"
            lock.parent.mkdir()
            lock.write_bytes(b"")
            lock.chmod(0o600)
        return root

    def test_stdlib_verifier_accepts_relocated_bundle_and_installed_receipt(self) -> None:
        root = self.release()
        moved = self.base / "relocated laptop" / "bundle"
        moved.parent.mkdir()
        shutil.move(str(root), str(moved))
        with adapter.verified_release(moved) as manifest:
            self.assertEqual(manifest["modules"], ["coding"])
        installed = self.release(installed=True)
        with adapter.verified_release(installed) as manifest:
            self.assertEqual(manifest["modules"], ["coding"])

    def test_tamper_unexpected_files_links_and_missing_receipt_are_rejected(self) -> None:
        root = self.release(installed=True)
        module = root / "ecosystem/hooks.py"
        original = module.read_bytes()
        module.write_bytes(original + b"# altered\n")
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("tampered package accepted")
        module.write_bytes(original)
        extra = root / "unexpected.py"
        extra.write_text("fixture\n")
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("unexpected resource accepted")
        extra.unlink()
        outside = self.base / "outside.py"
        outside.write_bytes(original)
        module.unlink()
        module.symlink_to(outside)
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("linked resource accepted")
        module.unlink()
        module.write_bytes(original)
        (root / adapter.MARKER).unlink()
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("unowned installation accepted")

    def test_exclusive_installer_lock_blocks_hook_without_importing_package(self) -> None:
        root = self.release(installed=True)
        with (root.parent.parent / "constellation/.install.lock").open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                with adapter.verified_release(root):
                    self.fail("installer race accepted")

    def test_malformed_native_release_identity_is_rejected(self) -> None:
        root = self.release()
        manifest = json.loads((root / "bundle.json").read_text())
        for relative in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            path = root / relative
            path.write_text(json.dumps({"name": "constellation"}))
            manifest["files"][relative]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (root / "bundle.json").write_text(json.dumps(manifest))
        with self.assertRaises(adapter.AdapterError):
            with adapter.verified_release(root):
                self.fail("missing native versions accepted")

    def invoke(self, root: Path, event: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        environment = dict(os.environ)
        environment.pop("CONSTELLATION_HOOK_OWNER", None)
        if env:
            environment.update(env)
        return subprocess.run([sys.executable, "-I", str(root / "ecosystem/claude_hooks.py"), event],
                              input=json.dumps({"hook_event_name": event, "session_id": NATIVE,
                                                "cwd": str(self.base), "prompt": PRIVATE}),
                              text=True, capture_output=True, env=environment, timeout=15)

    def test_operational_failure_denies_tools_and_blocks_prompt_with_no_private_output(self) -> None:
        root = self.release()
        # Package code would raise if imported; a corrupt hash must reject it first.
        marker = self.base / "unverified-package-imported"
        (root / "ecosystem/hooks.py").write_text(
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('synthetic import ran')\n"
            "raise RuntimeError('LEAK-IMPORT-SENTINEL')\n")
        tool = self.invoke(root, "PreToolUse")
        self.assertEqual(tool.returncode, 0)
        self.assertEqual(json.loads(tool.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        prompt = self.invoke(root, "UserPromptSubmit")
        self.assertEqual(prompt.returncode, 2)
        self.assertNotIn("LEAK-IMPORT-SENTINEL", tool.stdout + tool.stderr + prompt.stdout + prompt.stderr)
        self.assertNotIn(PRIVATE, tool.stdout + tool.stderr + prompt.stdout + prompt.stderr)
        self.assertFalse(marker.exists())

    def test_unsupported_python_rejects_without_loading_runtime_or_reading_event(self) -> None:
        for event in sorted(adapter.EVENTS):
            output, errors = io.StringIO(), io.StringIO()
            private_input = mock.Mock()
            private_input.buffer.read.side_effect = AssertionError("Private input must remain unread")
            with self.subTest(event=event), \
                    mock.patch.dict(os.environ, {"CONSTELLATION_HOOK_OWNER": "shared"}), \
                    mock.patch.object(adapter.sys, "version_info", (3, 9, 6)), \
                    mock.patch.object(adapter.sys, "stdin", private_input), \
                    mock.patch.object(adapter, "verified_release") as verify, \
                    mock.patch.object(adapter, "handle_event") as dispatch, \
                    redirect_stdout(output), redirect_stderr(errors):
                code = adapter.main([event])
            verify.assert_not_called()
            dispatch.assert_not_called()
            private_input.buffer.read.assert_not_called()
            combined = output.getvalue() + errors.getvalue()
            self.assertIn("Python 3.11", combined)
            self.assertIn("PATH", combined)
            self.assertNotIn(PRIVATE, combined)
            if event == "UserPromptSubmit":
                self.assertEqual(code, 2)
                self.assertEqual(output.getvalue(), "")
            else:
                self.assertEqual(code, 0)
                response = json.loads(output.getvalue())
                if event == "PreToolUse":
                    self.assertEqual(response["hookSpecificOutput"]["permissionDecision"], "deny")
                else:
                    self.assertEqual(set(response), {"systemMessage"})
                self.assertNotIn("additionalContext", combined)

    def test_project_owned_cli_needs_no_package_import_or_manifest(self) -> None:
        root = self.release()
        (root / "bundle.json").unlink()
        result = self.invoke(root, "SessionStart", env={"CONSTELLATION_HOOK_OWNER": "project"})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {})


if __name__ == "__main__":
    unittest.main()
