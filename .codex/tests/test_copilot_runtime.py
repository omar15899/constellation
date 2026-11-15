"""Focused Copilot adapter checks against the real shared evidence engine.

Fixture identities below are synthetic and never claim native review execution.
"""

from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(SOURCE / "ecosystem/tests"))

from ecosystem import core
from helpers import DEFAULT_PROFILE, Scenario, check_definition, requirement

SPEC = importlib.util.spec_from_file_location("copilot_profile_runtime", SOURCE / "profiles/copilot/runtime.py")
assert SPEC and SPEC.loader
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class CopilotRuntimeTests(unittest.TestCase):
    def scenario(self, **options: object) -> Scenario:
        scenario = Scenario(**options)
        self.addCleanup(scenario.cleanup)
        return scenario

    def event(self, scenario: Scenario, event: str, **fields: object) -> dict:
        return runtime.handle_event(core, scenario.state_dir, event, {
            "sessionId": scenario.session, "cwd": str(scenario.root), **fields})

    def test_read_only_session_needs_no_contract_and_ignores_private_fields(self):
        scenario = self.scenario()
        private = "private prompt that must never be retained"
        context = self.event(scenario, "sessionStart", initialPrompt=private,
                             transcriptPath=private)
        self.assertIn(scenario.session, context["additionalContext"])
        self.assertNotIn(private, str(context))
        self.assertEqual(self.event(scenario, "agentStop"), {})
        self.assertEqual(self.event(scenario, "preToolUse", toolName="view"), {})
        self.assertFalse((scenario.state_dir / "ecosystem.sqlite3").exists())
        home_store = scenario.root / ".copilot/constellation/state"
        home_event = {"sessionId": scenario.session, "cwd": str(scenario.root)}
        self.assertIn("additionalContext", runtime.handle_event(core, home_store, "sessionStart", home_event))
        self.assertEqual(runtime.handle_event(core, home_store, "agentStop", home_event), {})
        denied = self.event(scenario, "preToolUse", toolName="create", toolArgs={"path": "new.py"})
        self.assertEqual(denied["permissionDecision"], "deny")

    def test_native_edit_requires_exact_safe_path_and_one_active_contract(self):
        scenario = self.scenario()
        scenario.plan()
        for arguments in ({"path": "result.md"}, '{"path":"result.md"}',
                          {"path": str(scenario.root / "result.md")}):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.event(scenario, "preToolUse", toolName="edit",
                                            toolArgs=arguments), {})
        for path in ("other.py", "../outside.py", str(scenario.base / "outside.py"), ""):
            with self.subTest(path=path):
                denied = self.event(scenario, "preToolUse", toolName="edit", toolArgs={"path": path})
                self.assertEqual(denied["permissionDecision"], "deny")
        second = core.Engine(scenario.root, scenario.state_dir)
        second.execute("plan", {**scenario.contract, "session_id": scenario.session,
                                "task_id": "fixture-other-task", "agent_id": "fixture-other-coordinator",
                                "expected_revision": 0})
        denied = self.event(scenario, "preToolUse", toolName="edit", toolArgs={"path": "result.md"})
        self.assertEqual(denied["permissionDecision"], "deny")

    def test_stop_rechecks_failed_pending_and_stale_evidence_without_consuming_continuations(self):
        scenario = self.scenario()
        scenario.plan()
        for _ in range(3):
            self.assertEqual(self.event(scenario, "agentStop")["decision"], "block")
        self.assertEqual(scenario.call("status")["stop_attempts"], 0)
        (scenario.root / "result.md").write_text("incorrect result\n", encoding="utf-8")
        self.assertEqual(scenario.check()["status"], "failed")
        self.assertEqual(self.event(scenario, "agentStop")["decision"], "block")
        (scenario.root / "result.md").write_text("verified result\n", encoding="utf-8")
        scenario.approve()
        self.assertEqual(self.event(scenario, "agentStop")["decision"], "block")
        scenario.close()
        self.assertEqual(self.event(scenario, "agentStop"), {})
        (scenario.root / "result.md").write_text("changed after review\n", encoding="utf-8")
        self.assertEqual(self.event(scenario, "agentStop")["decision"], "block")

    def test_partial_handoff_and_child_stop_do_not_certify_parent_completion(self):
        scenario = self.scenario()
        scenario.plan()
        self.assertEqual(self.event(scenario, "agentStop", agentId="fixture-native-child"), {})
        scenario.close("partial")
        self.assertEqual(self.event(scenario, "agentStop"), {})
        self.assertFalse(scenario.call("status")["closure_current"])
        denied = self.event(scenario, "preToolUse", toolName="create", toolArgs={"path": "result.md"})
        self.assertEqual(denied["permissionDecision"], "deny")

    def test_only_current_complete_successor_covering_every_older_path_supersedes_history(self):
        earlier = self.scenario(task="fixture-earlier-outcome")
        (earlier.root / "other.md").write_text("verified result\n", encoding="utf-8")
        deliverables = [{"path": name, "profiles": [DEFAULT_PROFILE]}
                        for name in ("result.md", "other.md")]
        earlier.plan(deliverables=deliverables,
                     requirements=[{**requirement(), "deliverables": ["result.md", "other.md"]}])
        earlier.approve()
        earlier.close()
        (earlier.root / "result.md").write_text("verified result\n\n", encoding="utf-8")

        unrelated = self.scenario(task="fixture-unrelated-outcome", root=earlier.root,
                                  state_dir=earlier.state_dir)
        (earlier.root / "unrelated.md").write_text("verified result\n", encoding="utf-8")
        unrelated.argv = [argument.replace("result.md", "unrelated.md") for argument in unrelated.argv]
        unrelated.plan(deliverables=[{"path": "unrelated.md", "profiles": [DEFAULT_PROFILE]}],
                       requirements=[requirement(path="unrelated.md")],
                       checks=[check_definition("c1", unrelated.argv)])
        unrelated.approve()
        unrelated.close()
        self.assertEqual(self.event(earlier, "agentStop")["decision"], "block")

        successor = self.scenario(task="fixture-later-outcome", root=earlier.root,
                                  state_dir=earlier.state_dir)
        successor.plan()
        self.assertEqual(self.event(earlier, "agentStop")["decision"], "block")
        successor.close("partial")
        self.assertEqual(self.event(earlier, "agentStop")["decision"], "block")
        successor.plan()
        successor.approve()
        successor.close()
        self.assertTrue(successor.call("status")["closure_current"])
        self.assertEqual(self.event(earlier, "agentStop")["decision"], "block")

        successor.plan(deliverables=deliverables,
                       requirements=[{**requirement(), "deliverables": ["result.md", "other.md"]}])
        successor.approve()
        successor.close()
        self.assertEqual(self.event(earlier, "agentStop"), {})
        (earlier.root / "result.md").write_text("unreviewed edit\n", encoding="utf-8")
        self.assertEqual(self.event(earlier, "agentStop")["decision"], "block")

    def test_malformed_input_linked_lookup_and_project_state_are_rejected(self):
        scenario = self.scenario()
        for raw in (b'{"cwd":"a","cwd":"b"}', b'{"value":NaN}', b'[]', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(runtime.AdapterError):
                runtime.read_object(io.BytesIO(raw))
        for payload in ({"sessionId": "bad id", "cwd": str(scenario.root)},
                        {"sessionId": scenario.session, "cwd": "relative"},
                        {"sessionId": scenario.session, "cwd": str(scenario.root),
                         "stop_hook_active": "true"}):
            with self.subTest(payload=payload), self.assertRaises(runtime.AdapterError):
                runtime.handle_event(core, scenario.state_dir, "agentStop", payload)
        with self.assertRaises(runtime.AdapterError):
            runtime.validate_location(core, scenario.root / "state", scenario.root)
        if not core.platform.IS_WINDOWS:
            alias = scenario.base / "alias"
            alias.symlink_to(scenario.root, target_is_directory=True)
            with self.assertRaises(runtime.AdapterError):
                runtime.handle_event(core, scenario.state_dir, "agentStop", {
                    "sessionId": scenario.session, "cwd": str(alias)})


if __name__ == "__main__":
    unittest.main()
