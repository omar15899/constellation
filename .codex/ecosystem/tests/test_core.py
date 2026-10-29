"""Adversarial acceptance tests for the real portable coordination engine.

Fixture identities below are deliberately synthetic, not actual review claims.
Portable cases require no Git repository, server, third-party package or network.
Git lifecycle cases create disposable repositories and local bare remotes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from helpers import (AVAILABLE_PROFILES, CODEX_DIR, COORDINATOR, DEFAULT_PROFILE,
                     PYTHON, REVIEWERS, SOURCE_DIR, WORKER,
                     Scenario, check_definition, finish_request, requirement, start_request)
from ecosystem.core import Engine, RevisionConflict, default_state_dir, gate
from ecosystem.storage import Error


def finding() -> dict:
    return {"id": "fixture-missing-boundary", "path": "result.md", "line": 1,
            "severity": "high", "origin": "introduced",
            "scenario": "The result omits the boundary case required by the fixture.",
            "consequence": "The asserted result is not established for the full declared domain.",
            "evidence": "The fixture result contains only the interior case."}


class FixtureCase(unittest.TestCase):
    def scenario(self, **options: object) -> Scenario:
        scenario = Scenario(**options)
        self.addCleanup(scenario.cleanup)
        return scenario

    def ready(self, **plan: object) -> Scenario:
        scenario = self.scenario()
        scenario.plan(**plan)
        scenario.approve()
        return scenario

    def rejected_close(self, scenario: Scenario) -> None:
        with self.assertRaises(Error):
            scenario.close()
        status = scenario.call("status")
        self.assertTrue(status["pending"], "Rejected completion must explain its pending obligations")

    def isolated_runtime(self, scenario: Scenario,
                         profiles: tuple[str, ...] = AVAILABLE_PROFILES):
        """Copy only shipped inputs so resource mutations cannot affect other writers."""
        runtime = scenario.base / "runtime"
        package = runtime / "ecosystem"
        package.mkdir(parents=True)
        for source in SOURCE_DIR.glob("*.py"):
            shutil.copyfile(source, package / source.name)
        manifest = SOURCE_DIR / "manifests/codex-plugin.json"
        destination = package / "manifests/codex-plugin.json"
        if not manifest.is_file():
            manifest = CODEX_DIR / ".codex-plugin/plugin.json"
            destination = runtime / ".codex-plugin/plugin.json"
        destination.parent.mkdir(parents=True)
        shutil.copyfile(manifest, destination)
        for directory in ("references", "agents", "runtime"):
            shutil.copytree(SOURCE_DIR / directory, package / directory)
        for profile in profiles:
            for name in ("SKILL.md", "agents/openai.yaml", "references/workflow.md"):
                destination = runtime / "skills" / profile / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(CODEX_DIR / "skills" / profile / name, destination)
        module_name = "fixture_isolated_ecosystem_" + str(id(scenario))
        spec = importlib.util.spec_from_file_location(module_name, package / "__init__.py",
                                                      submodule_search_locations=[str(package)])
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        core = importlib.import_module(module_name + ".core")

        def unload() -> None:
            for name in tuple(sys.modules):
                if name == module_name or name.startswith(module_name + "."):
                    del sys.modules[name]

        self.addCleanup(unload)
        scenario.engine = core.Engine(scenario.root, scenario.state_dir)
        return runtime, core


class CoreTests(FixtureCase):
    def test_review_budget_requires_coordinator_exact_fields_and_current_revisions(self):
        scenario = self.scenario()
        scenario.plan()
        original = scenario.call("status")
        token = scenario.call("review-context")["token"]
        self.assertEqual(original["budget"], {"revision": 0, "deadline_at": None, "status": "unknown"})
        fields = {"expected_budget_revision": 0, "deadline_at": "2099-01-01T00:00:00Z",
                  "reason": "Reserve time for the declared independent checks."}
        for actor in (WORKER, REVIEWERS[0]):
            with self.subTest(actor=actor), self.assertRaisesRegex(Error, "frozen coordinator"):
                scenario.call("review-budget", actor=actor, **fields)
        malformed = [
            {name: value for name, value in fields.items() if name != required}
            for required in fields
        ] + [
            {**fields, "unrecognized": True},
            {**fields, "expected_budget_revision": True},
            {**fields, "expected_budget_revision": -1},
            {**fields, "deadline_at": "2099-01-01T00:00:00"},
            {**fields, "deadline_at": "2099-01-01T00:00:00+01:00"},
            {**fields, "deadline_at": "2099-02-30T00:00:00Z"},
            {**fields, "reason": " "},
            {**fields, "reason": False},
        ]
        for payload in malformed:
            with self.subTest(payload=payload), self.assertRaises(Error):
                scenario.call("review-budget", **payload)
        self.assertEqual(scenario.call("status"), original)
        updated = scenario.call("review-budget", request_id="fixture-budget-update", **fields)
        self.assertEqual(updated["budget"], {"revision": 1, "deadline_at": fields["deadline_at"],
                                           "status": "available"})
        self.assertEqual(updated["revision"], original["revision"] + 1)
        self.assertEqual(scenario.call("review-context")["token"], token)
        replayed = scenario.call("review-budget", request_id="fixture-budget-update", **fields)
        self.assertTrue(replayed["replayed"])
        self.assertEqual(replayed["revision"], updated["revision"])
        retried = scenario.call("review-budget", **fields)
        self.assertTrue(retried["unchanged"])
        self.assertEqual(retried["budget"], updated["budget"])
        for payload in ({**fields, "deadline_at": "2099-01-02T00:00:00Z"},
                        {**fields, "expected_budget_revision": 1,
                         "request_id": "fixture-budget-update"}):
            with self.subTest(payload=payload), self.assertRaises(Error):
                scenario.call("review-budget", **payload)
        status = scenario.call("status")
        self.assertEqual(status["revision"], retried["revision"])
        record = status["gate"]["review_budget"]
        self.assertEqual(record["author"], COORDINATOR)
        self.assertEqual(len(record["history"]), 1)
        self.assertEqual(record["history"][0]["reason"], fields["reason"])

    def test_review_budget_preserves_evidence_and_expiry_only_blocks_new_versions(self):
        scenario = self.ready()
        original = scenario.call("status")
        token = scenario.call("review-context")["token"]
        with patch.object(gate, "_utc_now", return_value=datetime(2030, 1, 1, tzinfo=timezone.utc)):
            updated = scenario.call("review-budget", expected_budget_revision=0,
                                    deadline_at="2030-01-02T00:00:00+00:00",
                                    reason="Allow one more day for verification.")
            self.assertEqual(updated["budget"]["status"], "available")
            self.assertEqual(updated["budget"]["deadline_at"], "2030-01-02T00:00:00Z")
        with patch.object(gate, "_utc_now", return_value=datetime(2030, 1, 2, tzinfo=timezone.utc)):
            current = scenario.call("status")
            self.assertEqual(current["budget"]["status"], "exhausted")
            self.assertEqual(current["revision"], updated["revision"])
            self.assertEqual(current["checks"], original["checks"])
            self.assertEqual(current["gate"]["review_gate"], original["gate"]["review_gate"])
            self.assertEqual(scenario.call("review-context")["token"], token)
            self.assertTrue(scenario.start()["unchanged"])
            self.assertEqual(scenario.close()["status"], "complete")
            scenario.plan()
            self.assertEqual(scenario.call("status")["gate"]["review_budget"], current["gate"]["review_budget"])
            scenario.check()
            with self.assertRaises(Error):
                scenario.call("review-start", continuation={
                    "reason": "Recheck the current evidence after replanning.",
                    "next_action": "Inspect the changed check generation."})
            renewed = scenario.call("review-budget", expected_budget_revision=1,
                                    deadline_at="2030-01-03T00:00:00Z",
                                    reason="Renew the review window for the pending version.")
            self.assertEqual(renewed["budget"]["revision"], 2)
            self.assertEqual(scenario.call("review-start", continuation={
                "reason": "The renewed window permits the pending review.",
                "next_action": "Review the new check generation."})["round"], 2)
            self.rejected_close(scenario)

    def test_review_continuation_requires_coordinator_and_valid_current_checks(self):
        scenario = self.scenario()
        scenario.plan()
        continuation = {"reason": "Review the declared boundary conditions.",
                        "next_action": "Inspect the current artifact and check evidence."}
        with self.assertRaisesRegex(Error, "Review cannot start"):
            scenario.call("review-start", continuation=continuation)
        scenario.check()
        with self.assertRaisesRegex(Error, "frozen coordinator"):
            scenario.call("review-start", actor=WORKER, continuation=continuation)
        before = scenario.call("status")
        for malformed in (False, "continue", {}, {"reason": "Only a reason"},
                          {**continuation, "unexpected": True}, {**continuation, "next_action": " "}):
            with self.subTest(continuation=malformed), self.assertRaises(Error):
                scenario.call("review-start", continuation=malformed)
        self.assertEqual(scenario.call("status"), before)
        first = scenario.start()
        self.assertEqual(first["budget"]["status"], "unknown")
        self.assertEqual(first["round"], 1)
        scenario.check()
        with self.assertRaises(Error):
            scenario.start()
        self.assertEqual(scenario.call("review-start", continuation=continuation)["round"], 2)

    def test_review_budget_can_change_after_closure_without_reopening_task(self):
        for mode in ("complete", "partial"):
            with self.subTest(mode=mode):
                scenario = self.ready()
                scenario.close(mode)
                original = scenario.call("status")
                token = scenario.call("review-context")["token"]
                scenario.call("review-budget", expected_budget_revision=0,
                              deadline_at="2099-01-01T00:00:00Z",
                              reason="Record the remaining review window without reopening the task.")
                updated = scenario.call("status")
                for field in ("status", "closure", "closure_current", "checks", "pending"):
                    self.assertEqual(updated[field], original[field])
                self.assertEqual(updated["gate"]["review_gate"], original["gate"]["review_gate"])
                self.assertEqual(scenario.call("review-context")["token"], token)
                with self.assertRaisesRegex(Error, "Task is closed"):
                    scenario.start()

    def test_quick_code_embedded_api_respects_current_receiver_consent(self):
        for consent in ("absent", False, "tightened-after-report"):
            with self.subTest(consent=consent):
                scenario = self.scenario()
                (scenario.root / "result.py").write_text("def answer(): return 42\n")
                scenario.plan(requirements=[requirement(path="result.py", acceptance="behavior")],
                              deliverables=[{"path": "result.py", "profiles": [DEFAULT_PROFILE]}])
                scenario.check()
                reason = "Only the constant return value changes; the declared check passes."
                policy = json.loads((SOURCE_DIR / "runtime/review-policy.json").read_text())
                config = scenario.root / ".codex"
                config.mkdir()
                if consent == "tightened-after-report":
                    original = scenario.call("review-start", quick_code_reason=reason)
                    scenario.report()
                if consent == "absent":
                    policy.pop("allow_quick_code", None)
                else:
                    policy["allow_quick_code"] = False
                (config / "review-policy.json").write_text(json.dumps(policy))
                with self.assertRaises(Error):
                    scenario.call("review-start", quick_code_reason=reason)
                if consent == "tightened-after-report":
                    current = scenario.call("review-context")
                    self.assertNotEqual(current["token"], original["token"])
                    self.assertEqual(current["mode"], "standard")
                    self.rejected_close(scenario)

    def test_quick_code_declaration_is_forwarded_and_remains_version_bound(self):
        scenario = self.scenario()
        (scenario.root / "result.py").write_text("def answer(): return 42\n")
        scenario.argv = [PYTHON, "-I", "-B", "-c", "from pathlib import Path; assert '42' in Path('result.py').read_text()"]
        scenario.plan(requirements=[requirement(path="result.py", acceptance="behavior")],
                      deliverables=[{"path": "result.py", "profiles": [DEFAULT_PROFILE]}],
                      checks=[check_definition("c1", scenario.argv, "behavior")])
        scenario.check()
        reason = "Only the constant return value changes; the declared boundary check passes."
        with self.assertRaises(Error):
            scenario.call("review-start", actor=WORKER, quick_code_reason=reason)
        for malformed in ("", " ", True, 42, "a" * 1001):
            with self.assertRaises(Error):
                scenario.call("review-start", quick_code_reason=malformed)
        context = scenario.call("review-start", quick_code_reason=reason)
        self.assertEqual((context["mode"], context["required_reviewers"]), ("quick", 1))
        self.assertEqual(context["quick_code_reason"], reason)
        self.assertTrue(scenario.call("review-start", quick_code_reason=reason)["unchanged"])
        scenario.report()
        self.assertEqual(scenario.close()["status"], "complete")
        scenario.plan()
        (scenario.root / "result.py").write_text("def answer(): return 42 + 1\n")
        scenario.check()
        self.assertEqual(scenario.call("review-context")["mode"], "standard")
        with self.assertRaises(Error):
            scenario.call("review-start", quick_code_reason=reason)
        self.assertEqual(scenario.start()["required_reviewers"], 3)
        scenario.report()
        self.rejected_close(scenario)

    def test_quick_code_embedded_api_retains_receiver_quorum_and_sensitive_paths(self):
        for sensitive in (False, True):
            with self.subTest(sensitive=sensitive):
                scenario = self.scenario()
                (scenario.root / "result.py").write_text("def answer(): return 42\n")
                scenario.plan(requirements=[requirement(path="result.py", acceptance="behavior")],
                              deliverables=[{"path": "result.py", "profiles": [DEFAULT_PROFILE]}])
                scenario.check()
                policy = json.loads((SOURCE_DIR / "runtime/review-policy.json").read_text())
                policy["modes"]["quick"] = {"reviewers": 2, "focus": {"correctness": 2}}
                if sensitive:
                    policy["deep_patterns"].append("result.py")
                config = scenario.root / ".codex"
                config.mkdir()
                (config / "review-policy.json").write_text(json.dumps(policy))
                reason = "Only the constant return value changes; the declared check passes."
                if sensitive:
                    with self.assertRaises(Error):
                        scenario.call("review-start", quick_code_reason=reason)
                else:
                    context = scenario.call("review-start", quick_code_reason=reason)
                    self.assertEqual((context["mode"], context["required_reviewers"]), ("quick", 2))
                    scenario.report()
                    self.rejected_close(scenario)
                    scenario.report(1)
                    self.assertEqual(scenario.close()["status"], "complete")

    def test_complete_workflow_runs_with_git_unavailable(self):
        with patch.dict(os.environ, {"PATH": ""}):
            scenario = self.ready()
            result = scenario.close()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["pending"], [])
        self.assertFalse((scenario.root / ".git").exists())
        self.assertEqual(scenario.call("status")["closure"]["version"], result["version"])

    def test_failure_after_success_cannot_reuse_old_check_or_review(self):
        scenario = self.scenario()
        scenario.argv = [PYTHON, "-I", "-B", "-c",
                         "from pathlib import Path; assert not Path('fail.flag').exists()"]
        scenario.plan(checks=[check_definition("c1", scenario.argv)])
        scenario.approve()
        original = scenario.close()["token"]
        scenario.plan()
        (scenario.root / "fail.flag").write_text("fail the same command")
        failed = scenario.check()
        self.assertEqual(failed["status"], "failed")
        self.rejected_close(scenario)
        (scenario.root / "fail.flag").unlink()
        passed = scenario.check()
        self.assertEqual(passed["status"], "passed")
        self.assertGreater(passed["generation"], failed["generation"])
        self.assertNotEqual(scenario.call("review-context")["token"], original)
        self.rejected_close(scenario)
        scenario.start()
        scenario.report()
        self.assertEqual(scenario.close()["status"], "complete")

    def test_changed_content_or_executable_mode_invalidates_evidence(self):
        for mutation in ("content", "mode"):
            with self.subTest(mutation=mutation):
                scenario = self.ready()
                previous = scenario.close()["token"]
                artifact = scenario.root / "result.md"
                if mutation == "content":
                    artifact.write_text("a different result\n")
                else:
                    artifact.chmod(0o755)
                self.assertNotEqual(scenario.call("review-context")["token"], previous)
                self.rejected_close(scenario)
                with self.assertRaises(Error):
                    scenario.start()

    def test_changed_input_invalidates_check_and_review(self):
        scenario = self.scenario()
        input_path = scenario.root / "observations.dat"
        input_path.write_bytes(b"original observation")
        scenario.plan(inputs=[{"path": "observations.dat",
                               "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest()}])
        scenario.approve()
        original = scenario.close()["token"]
        input_path.write_bytes(b"changed observation")
        self.assertNotEqual(scenario.call("review-context")["token"], original)
        self.rejected_close(scenario)
        with self.assertRaises(Error):
            scenario.start()

    def test_input_execute_permission_change_invalidates_closure_and_dependents(self):
        provider = self.scenario(task="fixture-executable-provider")
        executable = provider.root / "verify.sh"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        input_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
        provider.argv = ["./verify.sh"]
        provider.plan(checks=[check_definition("c1", provider.argv)],
                      inputs=[{"path": "verify.sh", "sha256": input_hash}])
        provider.approve()
        closure = provider.close()
        self.assertTrue(provider.call("status")["closure_current"])

        consumer = self.scenario(task="fixture-executable-consumer", root=provider.root,
                                 state_dir=provider.state_dir)
        consumer.plan(depends_on=[{"session_id": provider.session, "task_id": provider.task,
                                   "version": closure["version"]}])
        consumer.approve()
        consumer.close()
        self.assertTrue(consumer.call("status")["closure_current"])

        executable.chmod(0o644)
        self.assertEqual(hashlib.sha256(executable.read_bytes()).hexdigest(), input_hash)
        self.assertFalse(provider.call("status")["closure_current"])
        self.assertNotEqual(provider.call("review-context")["token"], closure["token"])
        self.rejected_close(provider)
        self.assertFalse(consumer.call("status")["closure_current"])
        self.rejected_close(consumer)
        provider.plan()
        with self.assertRaises(Error):
            provider.start()
        self.assertEqual(provider.check()["status"], "launch_failed")
        consumer.plan()
        with self.assertRaises(Error):
            consumer.check()

    def test_revised_requirement_profile_or_check_definition_needs_fresh_evidence(self):
        for change in ("requirement", "profile", "check"):
            with self.subTest(change=change):
                if change == "profile" and len(AVAILABLE_PROFILES) < 2:
                    self.skipTest("Profile expansion requires two distributed profiles.")
                scenario = self.ready()
                original = scenario.close()["token"]
                if change == "requirement":
                    scenario.plan(requirements=[requirement(text="The result also identifies its assumptions.")])
                elif change == "profile":
                    scenario.plan(deliverables=[{"path": "result.md", "profiles": list(AVAILABLE_PROFILES)}])
                else:
                    old_argv = scenario.argv
                    scenario.argv = [PYTHON, "-I", "-B", "-c", "assert 6 * 7 == 42"]
                    scenario.plan(checks=[check_definition("c1", scenario.argv)])
                    with self.assertRaises(Error):
                        scenario.check(argv=old_argv)
                self.assertNotEqual(scenario.call("review-context")["token"], original)
                self.rejected_close(scenario)
                with self.assertRaises(Error):
                    scenario.start()
                scenario.approve()
                self.assertEqual(scenario.close()["status"], "complete")

    def test_coordinator_and_contributors_cannot_review_their_artifacts(self):
        scenario = self.scenario()
        scenario.plan()
        scenario.call("author", author=REVIEWERS[0], paths=["result.md"])
        scenario.check()
        scenario.start()
        for actor in (COORDINATOR, WORKER, REVIEWERS[0]):
            with self.subTest(actor=actor), self.assertRaises(Error):
                scenario.report(actor)
        scenario.report(1)
        self.assertEqual(scenario.close()["status"], "complete")

    def test_actor_cannot_impersonate_a_registered_reviewer(self):
        scenario = self.scenario()
        scenario.plan()
        scenario.check()
        token = scenario.start()["token"]
        with self.assertRaises(Error):
            scenario.call("review-report", actor=REVIEWERS[0], token=token,
                          reviewer=REVIEWERS[1], role="reviewer", focus=["correctness"],
                          paths=["result.md"], summary="Fixture review", evidence="Fixture inspection",
                          findings=[], assessments=scenario.assessments())
        self.rejected_close(scenario)

    def test_open_finding_needs_a_third_independent_verifier(self):
        scenario = self.scenario()
        scenario.plan()
        scenario.call("author", author=REVIEWERS[1], paths=["result.md"])
        scenario.check()
        token = scenario.start()["token"]
        scenario.report(0, findings=[finding()])
        self.rejected_close(scenario)
        for actor in (COORDINATOR, WORKER, REVIEWERS[0], REVIEWERS[1]):
            with self.subTest(actor=actor), self.assertRaises(Error):
                scenario.call("review-resolve", actor=actor, token=token,
                              id=finding()["id"], verifier=actor, disposition="dismissed",
                              evidence="The independently inspected boundary is already included.")
        scenario.call("review-resolve", actor=REVIEWERS[2], token=token,
                      id=finding()["id"], verifier=REVIEWERS[2], disposition="dismissed",
                      evidence="Independent fixture inspection confirms the boundary is in scope and present.")
        self.assertEqual(scenario.close()["status"], "complete")
        scenario.plan()
        scenario.check()
        scenario.start()
        scenario.report(3)
        self.rejected_close(scenario)
        ledger = scenario.call("status")["gate"]["review_gate"]
        self.assertEqual(ledger["findings"][finding()["id"]]["status"], "open")
        self.assertEqual(len(ledger["findings"][finding()["id"]]["resolutions"]), 1)

    def test_substantive_assessments_cover_every_requirement(self):
        scenario = self.scenario()
        scenario.plan(requirements=[requirement(), requirement("r2", text="State the result's limitations.")])
        scenario.check()
        scenario.start()
        scenario.report(0, assessments=scenario.assessments()[:1])
        self.rejected_close(scenario)
        scenario.report(1, assessments=scenario.assessments()[1:])
        self.assertEqual(scenario.close()["status"], "complete")

    def test_deep_requires_three_correctness_and_two_security_per_artifact(self):
        scenario = self.scenario()
        (scenario.root / "second.md").write_text("A second fixture artifact\n")
        scenario.plan(risk="deep", requirements=[requirement(), requirement("r2", "second.md")],
                      deliverables=[{"path": name, "profiles": [DEFAULT_PROFILE]}
                                    for name in ("result.md", "second.md")])
        scenario.check()
        context = scenario.start()
        self.assertEqual(context["required_reviewers"], 5)
        self.assertEqual(context["required_focus"], {"correctness": 3, "security": 2})
        for actor in range(3):
            scenario.report(actor)
        self.rejected_close(scenario)
        scenario.report(3, focus=["security"], assessments=[])
        scenario.report(4, focus=["security"], paths=["result.md"], assessments=[])
        self.rejected_close(scenario)
        scenario.report(5, focus=["security"], assessments=[])
        self.assertEqual(scenario.close()["status"], "complete")

    def test_adaptive_rounds_preserve_budget_and_findings_across_replanning(self):
        scenario = self.scenario()
        scenario.plan()
        scenario.call("review-budget", expected_budget_revision=0,
                      deadline_at="2099-01-01T00:00:00Z",
                      reason="Allow the declared multi-round verification.")
        scenario.check()
        self.assertEqual(scenario.start()["round"], 1)
        scenario.report(0, findings=[finding()])
        self.assertTrue(scenario.start()["unchanged"])
        for number in (2, 3, 4):
            scenario.check()
            context = scenario.call("review-start", continuation={
                "reason": "The boundary finding still needs a verified correction.",
                "next_action": f"Check the boundary evidence for fixture version {number}."})
            self.assertEqual(context["round"], number)
        previous = scenario.call("status")["gate"]
        scenario.plan(requirements=[requirement(text="The same result with explicit assumptions.")], risk="quick")
        replanned = scenario.call("status")["gate"]
        self.assertEqual(replanned["review_budget"], previous["review_budget"])
        self.assertEqual(replanned["review_gate"], previous["review_gate"])
        scenario.check()
        context = scenario.call("review-start", continuation={
            "reason": "Explicit assumptions need independent examination.",
            "next_action": "Review the updated requirement and its boundary evidence."})
        self.assertEqual(context["round"], 5)
        ledger = scenario.call("status")["gate"]["review_gate"]
        self.assertEqual(len(ledger["rounds"]), 5)
        self.assertEqual(ledger["findings"][finding()["id"]]["status"], "open")
        self.rejected_close(scenario)

    def test_numeric_evidence_cannot_discharge_a_proof_obligation(self):
        scenario = self.scenario()
        scenario.plan(requirements=[requirement(acceptance="proof")],
                      deliverables=[{"path": "result.md", "profiles": [DEFAULT_PROFILE]}],
                      checks=[check_definition("c1", scenario.argv, "numeric")])
        scenario.check()
        scenario.start()
        experimental = [{"requirement_id": "r1", "verdict": "satisfied", "support": "experimental",
                         "evidence": "All finitely sampled numeric examples passed."}]
        scenario.report(0, assessments=experimental)
        self.rejected_close(scenario)
        with self.assertRaises(Error):
            scenario.report(1, assessments=[{**experimental[0], "verdict": "proved"}])
        partial = scenario.close("partial")
        self.assertEqual(partial["status"], "partial")
        self.assertTrue(partial["pending"])
        scenario.plan()
        scenario.check()
        scenario.start()
        scenario.report(2)
        self.assertEqual(scenario.close()["status"], "complete")

    def test_declared_decision_can_close_with_rigorously_reviewed_refutation(self):
        scenario = self.scenario()
        obligation = {**requirement(acceptance="proof"), "accepted_verdicts": ["proved", "refuted"]}
        scenario.plan(requirements=[obligation],
                      deliverables=[{"path": "result.md", "profiles": [DEFAULT_PROFILE]}],
                      checks=[check_definition("c1", scenario.argv, "numeric")])
        scenario.check()
        scenario.start()
        assessment = {"requirement_id": "r1", "verdict": "refuted", "support": "experimental",
                      "evidence": "A synthetic counterexample was checked against every hypothesis."}
        with self.assertRaises(Error):
            scenario.report(0, assessments=[assessment])
        scenario.report(0, assessments=[{**assessment, "support": "proof_review"}])
        self.assertEqual(scenario.close()["status"], "complete")

    def test_conflicting_proof_and_refutation_do_not_close_a_decision(self):
        scenario = self.scenario()
        scenario.plan(requirements=[{**requirement(acceptance="proof"),
                                     "accepted_verdicts": ["proved", "refuted"]}])
        scenario.check()
        scenario.start()
        scenario.report(0)
        scenario.report(1, assessments=[{**scenario.assessments()[0], "verdict": "refuted"}])
        self.rejected_close(scenario)

    def test_replanning_cannot_weaken_proof(self):
        scenario = self.scenario()
        scenario.plan(requirements=[requirement(acceptance="proof")])
        attempts = [
            {"requirements": [requirement(acceptance="editorial")]},
            {"requirements": [{**requirement(acceptance="proof"), "accepted_verdicts": ["refuted"]}]},
        ]
        for changes in attempts:
            with self.subTest(changes=changes), self.assertRaises(Error):
                scenario.plan(**changes)

    @unittest.skipUnless(len(AVAILABLE_PROFILES) >= 2, "Profile removal requires two distributed profiles.")
    def test_replanning_cannot_remove_an_existing_profile(self):
        scenario = self.scenario()
        scenario.plan(deliverables=[{"path": "result.md", "profiles": list(AVAILABLE_PROFILES)}])
        with self.assertRaises(Error):
            scenario.plan(deliverables=[{"path": "result.md", "profiles": [DEFAULT_PROFILE]}])

    def test_proof_cannot_declare_conjecture_or_conditional_as_completion(self):
        for verdict in ("conjecture", "conditional"):
            with self.subTest(verdict=verdict):
                scenario = self.scenario()
                with self.assertRaises(Error):
                    scenario.plan(requirements=[{**requirement(acceptance="proof"),
                                                 "accepted_verdicts": [verdict]}])

    def test_formal_assessment_requires_a_declared_formal_check(self):
        scenario = self.scenario()
        scenario.plan(requirements=[requirement(acceptance="proof")],
                      checks=[check_definition("c1", scenario.argv, "numeric")])
        scenario.check()
        scenario.start()
        formal = [{**scenario.assessments()[0], "support": "formal"}]
        with self.assertRaises(Error):
            scenario.report(0, assessments=formal)
        scenario.plan(checks=[check_definition("c1", scenario.argv, "formal")])
        scenario.check()
        scenario.call("review-start", continuation={
            "reason": "The formal assessment now has its required declared check.",
            "next_action": "Review the proof and the newly formal check evidence."})
        scenario.report(0, assessments=formal)
        self.assertEqual(scenario.close()["status"], "complete")

    def test_conflicting_or_conditional_assessments_leave_open_obligations(self):
        for verdict in ("conditional", "conjecture", "refuted"):
            with self.subTest(verdict=verdict):
                scenario = self.ready()
                scenario.report(1, assessments=[{**scenario.assessments()[0], "verdict": verdict}])
                self.rejected_close(scenario)

    @unittest.skipUnless({"coding", "mathematics", "writter"} <= set(AVAILABLE_PROFILES),
                         "Mixed delivery requires coding, mathematics and writter.")
    def test_mixed_profiles_preserve_separate_acceptance_obligations(self):
        scenario = self.scenario()
        requirements = [requirement("behavior", acceptance="behavior"),
                        requirement("proof", acceptance="proof"),
                        requirement("editorial", acceptance="editorial")]
        scenario.plan(requirements=requirements,
                      deliverables=[{"path": "result.md", "profiles": ["coding", "mathematics", "writter"]}],
                      checks=[check_definition("c1", scenario.argv, "behavior")])
        scenario.check()
        scenario.start()
        assessments = scenario.assessments()
        scenario.report(0, assessments=[assessments[0], assessments[2]])
        self.rejected_close(scenario)
        scenario.report(1, assessments=[assessments[1]])
        self.assertEqual(scenario.close()["status"], "complete")

    @unittest.skipUnless({"coding", "mathematics", "writter"} <= set(AVAILABLE_PROFILES),
                         "Simultaneous profiles require coding, mathematics and writter.")
    def test_distinct_profiles_can_complete_simultaneously_in_one_state_store(self):
        first = self.scenario(task="fixture-coding")
        scenarios = [first] + [self.scenario(task=f"fixture-{profile}", root=first.root,
                                            state_dir=first.state_dir)
                               for profile in ("mathematics", "writter")]
        for scenario, profile, acceptance, kind in zip(
                scenarios, ("coding", "mathematics", "writter"),
                ("behavior", "proof", "editorial"), ("behavior", "numeric", "editorial")):
            scenario.plan(requirements=[requirement(acceptance=acceptance)],
                          deliverables=[{"path": "result.md", "profiles": [profile]}],
                          checks=[check_definition("c1", scenario.argv, kind)])
        self.assertEqual(len(first.call("active-tasks")["tasks"]), 3)
        for scenario in scenarios:
            scenario.approve()
            self.assertEqual(scenario.close()["status"], "complete")
        self.assertEqual(first.call("active-tasks")["tasks"], [])

    def test_same_task_name_is_isolated_between_sessions(self):
        first = self.ready()
        first_version = first.close()["version"]
        second = self.scenario(session="fixture-other-session", root=first.root, state_dir=first.state_dir)
        second.plan()
        self.rejected_close(second)
        self.assertEqual(first.call("status")["closure"]["version"], first_version)
        self.assertEqual([row["session_id"] for row in second.call("active-tasks")["tasks"]],
                         [second.session])

    def test_partial_provider_and_stale_provider_version_block_consumers(self):
        provider = self.scenario(task="fixture-provider")
        provider.plan()
        self.assertEqual(provider.close("partial")["status"], "partial")
        consumer = self.scenario(task="fixture-consumer", root=provider.root, state_dir=provider.state_dir)
        dependency = {"session_id": provider.session, "task_id": provider.task, "version": "0" * 64}
        consumer.plan(depends_on=[dependency])
        with self.assertRaises(Error):
            consumer.check()
        self.rejected_close(consumer)
        provider.plan()
        provider.approve()
        dependency["version"] = provider.close()["version"]
        consumer.plan(depends_on=[dependency])
        consumer.approve()
        self.assertEqual(consumer.close()["status"], "complete")
        provider.plan()
        provider.check()
        self.rejected_close(consumer)
        with self.assertRaises(Error):
            consumer.check()

    def test_discovered_requirement_is_persistent_and_blocks_old_completion(self):
        scenario = self.ready()
        scenario.call("discover", actor=REVIEWERS[1],
                      requirement=requirement("boundary", text="The boundary case must also be justified."))
        self.rejected_close(scenario)
        with self.assertRaises(Error):
            scenario.plan()
        self.assertIn("boundary", {row["id"] for row in scenario.call("status")["contract"]["requirements"]})

    def test_stale_mutations_raise_typed_conflict_without_changing_state(self):
        scenario = self.scenario()
        scenario.plan()
        stale = scenario.payload(registered_agent_id="fixture-stale", role="worker")
        scenario.call("register-agent", registered_agent_id="fixture-current", role="worker")
        before = scenario.call("status")
        with self.assertRaises(RevisionConflict):
            scenario.engine.execute("register-agent", stale)
        self.assertEqual(scenario.call("status"), before)
        self.assertNotIn("fixture-stale", before["agents"])

    def test_request_id_replay_is_exact_and_does_not_consume_another_revision(self):
        scenario = self.scenario()
        scenario.plan()
        payload = scenario.payload(registered_agent_id="fixture-extra", role="worker", request_id="fixture-idempotency")
        original = scenario.engine.execute("register-agent", payload)
        replay = scenario.engine.execute("register-agent", payload)
        self.assertEqual(original["revision"], replay["revision"])
        self.assertTrue(replay["replayed"])
        with self.assertRaises(Error):
            scenario.engine.execute("register-agent", {**payload, "registered_agent_id": "fixture-different"})

    def test_installed_profile_resource_changes_invalidate_existing_evidence(self):
        scenario = self.scenario()
        runtime, core = self.isolated_runtime(scenario)
        scenario.plan()
        scenario.approve()
        token = scenario.close()["token"]
        resource = runtime / "skills" / DEFAULT_PROFILE / "references/workflow.md"
        resource.write_text(resource.read_text() + "\nA newly required substantive fixture obligation.\n")
        self.assertNotEqual(scenario.call("review-context")["token"], token)
        self.assertTrue(scenario.call("status")["pending"])
        with self.assertRaises(core.Error):
            scenario.close()
        scenario.plan()
        with self.assertRaises(core.Error):
            scenario.start()
        scenario.approve()
        self.assertEqual(scenario.close()["status"], "complete")

    @unittest.skipUnless("writter" in AVAILABLE_PROFILES, "Standalone writter requires its distributed profile.")
    def test_standalone_writter_tracks_its_technical_agents_and_resource_catalog(self):
        for relative in ("ecosystem/agents/coder.toml", "ecosystem/agents/mathematician.toml",
                         "ecosystem/build.py", "ecosystem/hook_entry.py"):
            with self.subTest(resource=relative):
                scenario = self.scenario()
                runtime, core = self.isolated_runtime(scenario, profiles=("writter",))
                self.assertFalse((runtime / "skills/coding").exists())
                self.assertFalse((runtime / "skills/mathematics").exists())
                scenario.plan()
                scenario.approve()
                token = scenario.close()["token"]
                resource = runtime / relative
                resource.write_text(resource.read_text() + "\n# Revised installed fixture resource.\n")
                self.assertNotEqual(scenario.call("review-context")["token"], token)
                self.assertTrue(scenario.call("status")["pending"])
                with self.assertRaises(core.Error):
                    scenario.close()
                scenario.plan()
                with self.assertRaises(core.Error):
                    scenario.start()
                scenario.approve()
                self.assertEqual(scenario.close()["status"], "complete")

    def test_policy_change_preserves_adaptive_history_and_established_quorum(self):
        scenario = self.scenario()
        runtime, core = self.isolated_runtime(scenario)
        scenario.plan(risk="deep")
        for number in (1, 2):
            scenario.check()
            context = scenario.call("review-start", continuation={
                "reason": "The current version requires complete Deep coverage.",
                "next_action": f"Inspect fixture version {number} with the retained quorum."})
            self.assertEqual(context["round"], number)
        policy_path = runtime / "ecosystem/runtime/review-policy.json"
        policy = json.loads(policy_path.read_text())
        policy["modes"]["standard"] = {"reviewers": 1, "focus": {"correctness": 1}}
        policy["modes"]["deep"] = {"reviewers": 2, "focus": {"correctness": 1, "security": 1}}
        policy_path.write_text(json.dumps(policy))
        scenario.check()
        context = scenario.call("review-start", continuation={
            "reason": "The changed policy must retain the established quorum.",
            "next_action": "Review the new resource snapshot with the original Deep coverage."})
        self.assertEqual(context["round"], 3)
        self.assertNotIn("max_rounds", context)
        self.assertEqual(context["required_focus"], {"correctness": 3, "security": 2})
        self.assertEqual(context["required_reviewers"], 5)
        scenario.check()
        with self.assertRaises(core.Error):
            scenario.start()
        continued = scenario.call("review-start", continuation={
            "reason": "The fourth version still needs the declared independent review.",
            "next_action": "Inspect the updated checks and collect the full Deep quorum."})
        self.assertEqual(continued["round"], 4)
        self.assertEqual(continued["required_focus"], context["required_focus"])


class GatePolicyTests(unittest.TestCase):
    def test_current_policy_optional_context_changes_token_and_retired_inputs_are_rejected(self):
        policy = {"schema_version": 2,
                  "modes": {"quick": {"reviewers": 1, "focus": {"correctness": 1}},
                            "standard": {"reviewers": 3, "focus": {"correctness": 3}},
                            "deep": {"reviewers": 5, "focus": {"correctness": 3, "security": 2}}},
                  "documentation_extensions": [".md"], "documentation_names": ["README"],
                  "deep_patterns": ["sensitive/**"]}
        state = {"requirements": ["The fixture result is correct."], "paths": ["result.md"],
                 "deletions": [], "author": "fixture-author", "started": "2000-01-01T00:00:00Z",
                 "initial_head": None}
        artifacts = {"result.md": {"sha256": "a" * 64, "mode": "100644"}}
        with tempfile.TemporaryDirectory() as directory:
            policy_path = Path(directory) / "policy.json"
            policy_path.write_text(json.dumps(policy))
            with patch.object(gate, "_artifacts", return_value=artifacts):
                current = gate.prepare(Path("/fixture/portable-review"), state, policy_path=policy_path)
                self.assertNotIn("review_context_sha256", current)
                state["review_context_sha256"] = "b" * 64
                changed = gate.prepare(Path("/fixture/portable-review"), state, policy_path=policy_path)
                self.assertNotEqual(changed["token"], current["token"])
                self.assertEqual(changed["review_context_sha256"], "b" * 64)
                for invalid in (None, "", "A" * 64, "f" * 63, 42):
                    with self.subTest(invalid=invalid), self.assertRaises(gate.ReviewError):
                        gate.prepare(Path("/fixture/portable-review"), {**state, "review_context_sha256": invalid},
                                     policy_path=policy_path)
                for rejected in ({**policy, "schema_version": 1},
                                 {**policy, "schema_version": 1, "max_rounds": 3},
                                 {**policy, "max_rounds": 3}):
                    policy_path.write_text(json.dumps(rejected))
                    before = json.loads(json.dumps(state))
                    with self.assertRaises(gate.ReviewError):
                        gate.prepare(Path("/fixture/portable-review"), state, policy_path=policy_path)
                    self.assertEqual(state, before)


class ConcurrencyTests(FixtureCase):
    """Real separate processes exercise transactions and late completions."""

    def wait_for(self, predicate, *, timeout: float = 8) -> object:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = predicate()
            if result:
                return result
            time.sleep(0.02)
        self.fail("Timed out waiting for a subprocess fixture rendezvous")

    def process(self, scenario: Scenario, operation: str, payload: dict) -> subprocess.Popen:
        process = start_request(scenario, operation, payload)

        def cleanup() -> None:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

        self.addCleanup(cleanup)
        return process

    def blocking_command(self, scenario: Scenario, marker: str, release: str) -> list[str]:
        return [PYTHON, "-I", "-B", "-c",
                "from pathlib import Path; import time; "
                f"Path({str(scenario.base / marker)!r}).write_text('started'); "
                f"end=time.monotonic()+10\nwhile not Path({str(scenario.base / release)!r}).exists():\n"
                " if time.monotonic()>end: raise SystemExit(9)\n time.sleep(.02)\n"
                f"Path({str(scenario.base / (marker + '.done'))!r}).write_text('finished')\n"]

    def test_two_processes_with_same_revision_have_one_winner(self):
        scenario = self.scenario()
        scenario.plan()
        revision = scenario.revision
        processes = [self.process(scenario, "register-agent", scenario.payload(
            expected_revision=revision, registered_agent_id=f"fixture-racer-{number}", role="worker"))
            for number in range(2)]
        results = [finish_request(process) for process in processes]
        self.assertEqual(sum(result["ok"] for result in results), 1, results)
        status = scenario.call("status")
        self.assertEqual(status["revision"], revision + 1)
        self.assertEqual(sum(name.startswith("fixture-racer-") for name in status["agents"]), 1)

    def test_checks_run_outside_transaction_and_do_not_overwrite_other_mutations(self):
        scenario = self.scenario()
        scenario.argv = self.blocking_command(scenario, "started", "release")
        scenario.plan(checks=[check_definition("c1", scenario.argv)])
        process = self.process(scenario, "check", scenario.payload(id="c1", argv=scenario.argv))
        self.wait_for(lambda: (scenario.base / "started").exists())
        self.assertEqual(scenario.call("status")["checks"]["c1"]["status"], "running")
        writer = self.process(scenario, "register-agent", scenario.payload(
            registered_agent_id="fixture-during-check", role="worker"))
        mutation = finish_request(writer, timeout=3)
        self.assertTrue(mutation["ok"], mutation)
        self.assertIsNone(process.poll(), "The first subprocess must still be blocked at the rendezvous")
        (scenario.base / "release").write_text("continue")
        checked = finish_request(process)
        self.assertEqual(checked["value"]["status"], "passed")
        status = scenario.call("status")
        self.assertIn("fixture-during-check", status["agents"])
        self.assertEqual(status["checks"]["c1"]["status"], "passed")

    def test_different_checks_finish_without_lost_updates(self):
        scenario = self.scenario()
        first = self.blocking_command(scenario, "first-started", "first-release")
        second = self.blocking_command(scenario, "second-started", "second-release")
        scenario.plan(checks=[check_definition("c1", first), check_definition("c2", second)])
        one = self.process(scenario, "check", scenario.payload(id="c1", argv=first))
        self.wait_for(lambda: (scenario.base / "first-started").exists())
        scenario.call("status")
        two = self.process(scenario, "check", scenario.payload(id="c2", argv=second))
        self.wait_for(lambda: (scenario.base / "second-started").exists())
        (scenario.base / "second-release").write_text("continue")
        self.assertEqual(finish_request(two)["value"]["status"], "passed")
        (scenario.base / "first-release").write_text("continue")
        self.assertEqual(finish_request(one)["value"]["status"], "passed")
        self.assertEqual({name: item["status"] for name, item in scenario.call("status")["checks"].items()},
                         {"c1": "passed", "c2": "passed"})

    def test_changed_artifact_while_check_runs_is_stale(self):
        scenario = self.scenario()
        scenario.argv = self.blocking_command(scenario, "started", "release")
        scenario.plan(checks=[check_definition("c1", scenario.argv)])
        process = self.process(scenario, "check", scenario.payload(id="c1", argv=scenario.argv))
        self.wait_for(lambda: (scenario.base / "started").exists())
        (scenario.root / "result.md").write_text("changed during execution")
        (scenario.base / "release").write_text("continue")
        result = finish_request(process)
        self.assertEqual(result["value"]["status"], "stale")
        scenario.call("status")
        self.rejected_close(scenario)

    def test_abandoned_attempt_cannot_resurrect_after_late_completion(self):
        scenario = self.scenario()
        scenario.argv = self.blocking_command(scenario, "started", "release")
        scenario.plan(checks=[check_definition("c1", scenario.argv)])
        process = self.process(scenario, "check", scenario.payload(id="c1", argv=scenario.argv))
        self.wait_for(lambda: (scenario.base / "started").exists())
        attempt = scenario.call("status")["checks"]["c1"]
        self.rejected_close(scenario)
        scenario.call("recover-check", id="c1", attempt_id=attempt["attempt_id"])
        (scenario.base / "release").write_text("continue")
        self.assertEqual(finish_request(process)["value"]["status"], "superseded")
        status = scenario.call("status")
        self.assertEqual(status["checks"]["c1"]["status"], "abandoned")
        self.rejected_close(scenario)
        self.assertEqual(scenario.check()["status"], "passed")
        scenario.start()
        scenario.report()
        self.assertEqual(scenario.close()["status"], "complete")

    def test_crashed_driver_preserves_running_attempt_until_explicit_recovery(self):
        scenario = self.scenario()
        scenario.argv = self.blocking_command(scenario, "started", "release")
        scenario.plan(checks=[check_definition("c1", scenario.argv)])
        process = self.process(scenario, "check", scenario.payload(id="c1", argv=scenario.argv))
        self.wait_for(lambda: (scenario.base / "started").exists())
        process.kill()
        process.communicate(timeout=5)
        (scenario.base / "release").write_text("release the orphaned bounded child")
        self.wait_for(lambda: (scenario.base / "started.done").exists())
        restarted = Engine(scenario.root, scenario.state_dir)
        scenario.engine = restarted
        attempt = scenario.call("status")["checks"]["c1"]
        self.assertEqual(attempt["status"], "running")
        with self.assertRaises(Error):
            scenario.check()
        self.rejected_close(scenario)
        scenario.call("recover-check", id="c1", attempt_id=attempt["attempt_id"])
        self.assertEqual(scenario.check()["status"], "passed")

    def test_old_completion_cannot_overwrite_a_new_successful_attempt(self):
        scenario = self.scenario()
        scenario.argv = self.blocking_command(scenario, "started", "release")
        scenario.plan(checks=[check_definition("c1", scenario.argv)])
        process = self.process(scenario, "check", scenario.payload(id="c1", argv=scenario.argv))
        self.wait_for(lambda: (scenario.base / "started").exists())
        original = scenario.call("status")["checks"]["c1"]
        scenario.call("recover-check", id="c1", attempt_id=original["attempt_id"])
        scenario.argv = [PYTHON, "-I", "-B", "-c", "assert 6 * 7 == 42"]
        scenario.plan(checks=[check_definition("c1", scenario.argv)])
        newer = scenario.check()
        self.assertEqual(newer["status"], "passed")
        self.assertGreater(newer["generation"], original["generation"])
        (scenario.base / "release").write_text("release the superseded subprocess")
        self.assertEqual(finish_request(process)["value"]["status"], "superseded")
        current = scenario.call("status")["checks"]["c1"]
        self.assertEqual(current["attempt_id"], newer["attempt_id"])
        self.assertEqual(current["status"], "passed")
        scenario.start()
        scenario.report()
        self.assertEqual(scenario.close()["status"], "complete")

    def test_timeout_and_launch_failure_are_recorded_and_fail_closed(self):
        for argv, expected in (([PYTHON, "-I", "-B", "-c", "import time; time.sleep(5)"], "timeout"),
                               (["/nonexistent/fixture-executable"], "launch_failed")):
            with self.subTest(expected=expected):
                scenario = self.scenario()
                scenario.argv = argv
                scenario.plan(checks=[check_definition("c1", argv)])
                result = scenario.check(timeout=0.1)
                self.assertEqual(result["status"], expected)
                self.assertEqual(scenario.call("status")["checks"]["c1"]["status"], expected)
                self.rejected_close(scenario)


class StateBoundaryTests(FixtureCase):
    def test_default_state_location_retains_defaults_and_allows_process_override(self):
        scenario = self.scenario()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(default_state_dir(), Path.home() / ".codex/constellation/state")
        codex_home = scenario.base / "codex-home"
        with patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}, clear=True):
            self.assertEqual(default_state_dir(), codex_home / "constellation/state")
            with patch.dict(os.environ, {"CONSTELLATION_STATE_DIR": ""}):
                self.assertEqual(default_state_dir(), codex_home / "constellation/state")
            with patch.dict(os.environ, {"CONSTELLATION_STATE_DIR": str(scenario.state_dir)}):
                self.assertEqual(default_state_dir(), scenario.state_dir)

    def test_cli_and_hooks_share_environment_state_without_global_writes(self):
        scenario = self.scenario()
        codex_home = scenario.base / "unused-codex-home"
        payload_state = scenario.base / "ignored-payload-state"
        environment = {**os.environ, "CODEX_HOME": str(codex_home),
                       "CONSTELLATION_STATE_DIR": str(scenario.state_dir)}

        def run(script: str, arguments: list[str], payload: dict) -> dict:
            result = subprocess.run(
                [PYTHON, "-I", "-B", str(SOURCE_DIR / script), *arguments],
                input=json.dumps(payload), text=True, capture_output=True,
                cwd=scenario.root, env=environment, timeout=15, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual(result.stderr, "")
            return json.loads(result.stdout)

        plan = run("cli.py", ["--root", str(scenario.root), "plan"],
                   scenario.payload(**scenario.contract))
        self.assertTrue(plan["planned"])
        self.assertTrue((scenario.state_dir / "ecosystem.sqlite3").is_file())
        event = {"session_id": scenario.session, "cwd": str(scenario.root),
                 "hook_event_name": "SubagentStart", "turn_id": "fixture-state-override-turn",
                 "agent_id": "fixture-env-observed-worker", "state_dir": str(payload_state)}
        observed = run("hooks.py", ["SubagentStart"], event)
        self.assertIn("observed this native subagent", observed["hookSpecificOutput"]["additionalContext"])
        current = run("cli.py", ["--root", str(scenario.root), "status"], scenario.payload())
        self.assertEqual(current["observed_agents"], {event["agent_id"]: "start"})
        self.assertEqual(current["revision"], plan["revision"] + 1)
        explicit_state = scenario.base / "explicit-cli-state"
        run("cli.py", ["--root", str(scenario.root), "--state-dir", str(explicit_state), "plan"],
            scenario.payload(**scenario.contract))
        self.assertTrue((explicit_state / "ecosystem.sqlite3").is_file())
        self.assertEqual(scenario.call("status")["revision"], current["revision"])
        self.assertFalse(codex_home.exists())
        self.assertFalse(payload_state.exists())

    def test_environment_state_override_retains_store_safety_checks(self):
        scenario = self.scenario()
        codex_home = scenario.base / "unused-codex-home"
        target = scenario.base / "real-state"
        target.mkdir()
        linked = scenario.base / "linked-state"
        linked.symlink_to(target, target_is_directory=True)
        environment = {**os.environ, "CODEX_HOME": str(codex_home),
                       "CONSTELLATION_STATE_DIR": str(linked)}
        result = subprocess.run(
            [PYTHON, "-I", "-B", str(SOURCE_DIR / "cli.py"), "--root", str(scenario.root), "plan"],
            input=json.dumps(scenario.payload(**scenario.contract)), text=True, capture_output=True,
            cwd=scenario.root, env=environment, timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("symbolic links", json.loads(result.stdout)["error"])
        self.assertFalse((target / "ecosystem.sqlite3").exists())
        self.assertFalse(codex_home.exists())

    def test_state_override_does_not_relocate_progress_authorization_policy(self):
        scenario = self.scenario()
        codex_home = scenario.base / "codex-home"
        codex_home.mkdir()
        policy = {"fixture_authorization_source": "codex-home"}
        (codex_home / "progress-journal.json").write_text(json.dumps(policy))
        environment = {"CODEX_HOME": str(codex_home),
                       "CONSTELLATION_STATE_DIR": str(scenario.base / "isolated/nested/state")}
        with patch.dict(os.environ, environment), patch.object(
                scenario.engine, "_execute", return_value={"acknowledged": True}) as operation:
            result = scenario.engine.execute("progress-ack", scenario.payload())
        self.assertTrue(result["acknowledged"])
        self.assertEqual(operation.call_args.kwargs["progress_policy"], policy)
        self.assertFalse((scenario.base / "isolated").exists())
        self.assertFalse((codex_home / "constellation").exists())

    def test_private_payloads_commands_and_outputs_are_not_persisted(self):
        scenario = self.scenario()
        sentinel = "PRIVATE-FIXTURE-SENTINEL-DO-NOT-PERSIST"
        scenario.argv = [PYTHON, "-I", "-B", "-c",
                         "import sys; print(sys.argv[1]); print(sys.argv[1], file=sys.stderr)", sentinel]
        scenario.plan(checks=[check_definition("c1", scenario.argv)])
        for field in ("prompt", "tool_input", "output", "transcript"):
            with self.subTest(field=field), self.assertRaises(Error):
                scenario.call("register-agent", registered_agent_id="fixture-private", role="worker", **{field: sentinel})
        result = scenario.check(request_id="fixture-private-check")
        self.assertEqual(result["status"], "passed")
        self.assertNotIn(sentinel, json.dumps(scenario.call("status")))
        for path in scenario.state_dir.rglob("*"):
            if path.is_file():
                self.assertNotIn(sentinel.encode(), path.read_bytes(), path.name)
        database = scenario.state_dir / "ecosystem.sqlite3"
        with sqlite3.connect(database) as connection:
            self.assertNotIn(sentinel, "\n".join(connection.iterdump()))

    def test_path_escape_private_paths_and_symlinks_are_rejected(self):
        scenario = self.scenario()
        outside = scenario.base / "outside.md"
        outside.write_text("outside")
        (scenario.root / "linked.md").symlink_to(outside)
        (scenario.root / "linked-directory").symlink_to(scenario.base, target_is_directory=True)
        paths = ("../outside.md", str(outside), "linked.md", "linked-directory/outside.md",
                 ".env", "conversations/private.md", "rollout-fixture.md", "result.md/../outside.md")
        for name in paths:
            with self.subTest(path=name), self.assertRaises(Error):
                scenario.engine.validate_path(name)
        self.assertEqual(scenario.engine.validate_path("result.md"), scenario.root / "result.md")

    def test_state_directory_cannot_be_a_deliverable_or_symlink(self):
        scenario = self.scenario()
        overlap = Engine(scenario.root, scenario.root / "state")
        with self.assertRaises(Error):
            overlap.validate_path("state/result.md")
        actual = scenario.base / "actual-state"
        actual.mkdir()
        linked = scenario.base / "linked-state"
        linked.symlink_to(actual, target_is_directory=True)
        unsafe = Engine(scenario.root, linked)
        with self.assertRaises(Error):
            unsafe.execute("plan", scenario.payload(**scenario.contract))

    def test_corrupt_database_is_rejected_without_reinitializing_it(self):
        scenario = self.scenario()
        scenario.plan()
        database = scenario.state_dir / "ecosystem.sqlite3"
        corrupt = b"This is deliberately not a SQLite database."
        database.write_bytes(corrupt)
        for operation in ("status", "plan"):
            with self.subTest(operation=operation), self.assertRaises(Error):
                scenario.call(operation, **(scenario.contract if operation == "plan" else {}))
        self.assertEqual(database.read_bytes(), corrupt)

    def test_truncated_or_missing_state_tables_are_not_silently_reinitialized(self):
        for corruption in ("zero-bytes", "missing-tasks-table"):
            with self.subTest(corruption=corruption):
                scenario = self.scenario()
                scenario.plan()
                database = scenario.state_dir / "ecosystem.sqlite3"
                if corruption == "zero-bytes":
                    database.write_bytes(b"")
                else:
                    with sqlite3.connect(database) as connection:
                        connection.execute("DROP TABLE tasks")
                before = database.read_bytes()
                with self.assertRaises(Error):
                    scenario.call("plan", expected_revision=0, **scenario.contract)
                self.assertEqual(database.read_bytes(), before)

    def test_structurally_corrupted_task_state_is_rejected(self):
        scenario = self.scenario()
        scenario.plan()
        database = scenario.state_dir / "ecosystem.sqlite3"
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE tasks SET state = ?", (json.dumps({"revision": scenario.revision}),))
        with self.assertRaises(Error):
            scenario.call("status")

    def test_schema_corruption_and_state_symlink_are_fail_closed(self):
        scenario = self.scenario()
        scenario.plan()
        database = scenario.state_dir / "ecosystem.sqlite3"
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE metadata SET version = 999")
        with self.assertRaises(Error):
            scenario.call("status")
        saved = scenario.base / "saved-state.sqlite3"
        database.rename(saved)
        database.symlink_to(saved)
        with self.assertRaises(Error):
            scenario.call("status")



@unittest.skipUnless(shutil.which("git"), "Git lifecycle checks require Git.")
class GitCheckResolutionTests(unittest.TestCase):
    """Exercise retained failures and independent replacement evidence on real Git."""

    def setUp(self):
        import io
        from ecosystem.runtime import workflow as runtime
        self.runtime = runtime
        self.output = io
        temporary = tempfile.TemporaryDirectory(prefix="constellation-check-resolution-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root, self.remote = self.base / "receiver", self.base / "remote.git"
        self.root.mkdir()
        configuration = patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1",
                                                "GIT_CONFIG_GLOBAL": os.devnull,
                                                "GIT_TERMINAL_PROMPT": "0"})
        configuration.start()
        self.addCleanup(configuration.stop)
        self.git("init", "--bare", "--initial-branch=main", str(self.remote), cwd=self.base)
        self.git("init", "--initial-branch=main", str(self.root), cwd=self.base)
        self.git("config", "user.name", "Synthetic Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        hooks = self.base / "empty-hooks"
        hooks.mkdir()
        self.git("config", "core.hooksPath", str(hooks))
        self.git("config", "core.autocrlf", "false")
        (self.root / "README.md").write_text("initial fixture\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-m", "Create isolated fixture")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "main")
        self.flow = runtime.Workflow(self.root, "test-session")
        self.failed_command = [sys.executable, "-c", "raise SystemExit(7)", "PRIVATE_ARGUMENT"]
        self.replacement_command = [sys.executable, ".codex/tool.py"]

    def git(self, *args, cwd=None):
        result = subprocess.run(["git", *args], cwd=cwd or self.root, check=True,
                                capture_output=True, text=True, encoding="utf-8", timeout=25)
        return result.stdout.rstrip("\n")

    def check(self, command, **kwargs):
        with patch("sys.stdout", new=self.output.StringIO()), patch("sys.stderr", new=self.output.StringIO()):
            return self.flow.check(command, **kwargs)

    def prepare(self):
        self.flow.begin("repair-invocation")
        self.flow.plan({"requirements": ["result is correct"], "paths": [".codex/tool.py", "answer.md"]})
        (self.root / ".codex").mkdir()
        (self.root / ".codex/tool.py").write_text("print('verified result')\n")
        (self.root / "answer.md").write_text("verified result\n")
        self.flow.review_operation("author", {"author": "writer", "paths": [".codex/tool.py"]})
        with self.assertRaises(self.runtime.Blocked):
            self.check(self.failed_command)
        self.check(self.replacement_command)
        return self.flow.review_operation("start")

    def report(self, context, identity, focus, paths=None):
        self.flow.review_operation("report", {
            "token": context["token"], "reviewer": identity, "role": "reviewer",
            "focus": focus, "paths": paths or context["paths"], "findings": [],
            "summary": "Checked the exact artifacts and the mistaken check invocation.",
            "evidence": "The replacement exercises the intended result using the current originals; the first invocation used the wrong arguments."})

    def approve(self, context):
        self.assertEqual(context["required_reviewers"], 5)
        for index in range(5):
            self.report(context, f"independent-{index}", ["correctness" if index < 3 else "security"])

    def payload(self, context, **changes):
        return {"token": context["token"], "failed_check": 0, "replacement_check": 1,
                "verifier": "independent-0", "reason": "Correct a mistaken command invocation.",
                "evidence": "Independently compared both check records and confirmed the successful replacement covers the intended behavior.", **changes}

    def test_resolution_preserves_history_index_and_publication_and_is_idempotent(self):
        (self.root / "README.md").write_text("unrelated staged user work\n")
        self.runtime.git(self.root, "add", "README.md")
        context = self.prepare()
        with self.assertRaisesRegex(self.runtime.Blocked, "distinct reviewers"):
            self.flow.check_resolve(self.payload(context))
        self.approve(context)
        with self.assertRaisesRegex(self.runtime.Blocked, "still failing"):
            self.flow.review({"result is correct": "The replacement passed."})
        state = self.flow.load()
        history = json.dumps(state["checks"], sort_keys=True).encode()
        index_path = self.root / ".git/index"
        index = index_path.read_bytes()
        unrelated = self.runtime.git(self.root, "diff", "--cached", "--binary", "--", "README.md")
        head = self.runtime.git(self.root, "rev-parse", "HEAD")
        self.assertFalse(self.flow.check_resolve(self.payload(context))["unchanged"])
        self.assertEqual(json.dumps(self.flow.load()["checks"], sort_keys=True).encode(), history)
        self.assertEqual(index_path.read_bytes(), index)
        self.assertEqual(self.runtime.git(self.root, "rev-parse", "HEAD"), head)
        self.assertEqual(self.runtime.git(self.remote, "rev-parse", "refs/heads/main"), head)
        self.assertEqual(self.flow.review_operation("prepare")["token"], context["token"])
        self.flow.review({"result is correct": "Read the actual result and verified the independent equivalence evidence."})
        before = self.flow.path.read_bytes()
        self.assertTrue(self.flow.check_resolve(self.payload(context))["unchanged"])
        self.assertEqual(self.flow.path.read_bytes(), before)
        self.assertNotIn("PRIVATE_ARGUMENT", self.flow.path.read_text())
        self.flow.commit(context["paths"], "Add independently checked result", preserve_index=True)
        self.assertEqual(self.runtime.git(self.root, "diff", "--cached", "--binary", "--", "README.md"), unrelated)
        self.assertEqual(self.runtime.git(self.root, "diff", "--cached", "--name-only"), "README.md")
        self.assertTrue(self.flow.finish()["completed"])
        self.assertEqual(self.runtime.git(self.remote, "rev-parse", "refs/heads/main"), self.runtime.git(self.root, "rev-parse", "HEAD"))

    def test_resolution_rejects_nonindependent_partial_or_unreported_verifiers_and_bad_indices(self):
        context = self.prepare()
        self.approve(context)
        self.report(context, "partial", ["correctness"], ["answer.md"])
        for verifier in ("test-session", "writer", "unreported", "independent-3", "partial"):
            with self.subTest(verifier=verifier), self.assertRaises(self.runtime.Blocked):
                self.flow.check_resolve(self.payload(context, verifier=verifier))
        for changes in ({"failed_check": True}, {"replacement_check": False}, {"failed_check": -1},
                        {"replacement_check": 20}, {"token": "stale"}, {"reason": " "},
                        {"evidence": "x" * 12001}, {"extra": "unsupported"}):
            with self.subTest(changes=tuple(changes)), self.assertRaises(self.runtime.Blocked):
                self.flow.check_resolve(self.payload(context, **changes))
        self.assertNotIn("check_resolutions", self.flow.load())

    def test_failed_mutating_and_interrupted_attempts_cannot_replace_a_check(self):
        self.prepare()
        with self.assertRaises(self.runtime.Blocked):
            self.check([sys.executable, "-c", "raise SystemExit(2)"])
        with self.assertRaises(self.runtime.Blocked):
            self.check([sys.executable, "-c", "from pathlib import Path; Path('answer.md').write_text('changed\\n')"])
        context = self.flow.review_operation("start")
        self.approve(context)
        for index in (2, 3):
            with self.subTest(replacement=index), self.assertRaisesRegex(self.runtime.Blocked, "Replacement check"):
                self.flow.check_resolve(self.payload(context, replacement_check=index))
        interrupted = [sys.executable, "-c", "pass"]
        original_run = self.runtime.subprocess.run

        def interrupt(command, **kwargs):
            if command == interrupted:
                raise KeyboardInterrupt
            return original_run(command, **kwargs)

        with patch.object(self.runtime.subprocess, "run", side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.check(interrupted)
        with self.assertRaises(self.runtime.Blocked):
            self.check([sys.executable, "-c", "import time; time.sleep(2)"], timeout=1)
        with self.assertRaises(self.runtime.Blocked):
            self.check([sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"])
        records = self.flow.load()["checks"]
        self.assertEqual(records[5]["exit_code"], -1)
        self.assertLess(records[6]["exit_code"], 0)
        self.check(self.replacement_command)
        context = self.flow.review_operation("start")
        self.approve(context)
        for index in (3, 4, 5, 6):
            with self.subTest(failed=index), self.assertRaisesRegex(self.runtime.Blocked, "completed failed"):
                self.flow.check_resolve(self.payload(context, failed_check=index, replacement_check=7))
        self.assertNotIn("check_resolutions", self.flow.load())

    def test_new_attempt_requires_fresh_reports_and_new_append_only_receipt(self):
        context = self.prepare()
        self.approve(context)
        self.flow.check_resolve(self.payload(context))
        old = self.flow.load()["check_resolutions"][0]
        self.flow.review({"result is correct": "Verified the current result."})
        with self.assertRaises(self.runtime.Blocked):
            self.check(self.failed_command)
        self.check(self.replacement_command)
        fresh = self.flow.review_operation("start")
        self.approve(fresh)
        with self.assertRaisesRegex(self.runtime.Blocked, "current independent review token"):
            self.flow.check_resolve(self.payload(context))
        with self.assertRaisesRegex(self.runtime.Blocked, "latest attempt"):
            self.flow.check_resolve(self.payload(fresh))
        with self.assertRaisesRegex(self.runtime.Blocked, "still failing"):
            self.flow.review({"result is correct": "An old receipt must not conceal the new failure."})
        self.flow.check_resolve(self.payload(fresh, failed_check=2, replacement_check=3))
        self.assertEqual(self.flow.load()["check_resolutions"][0], old)
        self.assertEqual(len(self.flow.load()["check_resolutions"]), 2)
        self.flow.review({"result is correct": "The new failed attempt has a fresh independent resolution."})

    def test_full_snapshot_and_receipts_are_revalidated_by_reviewed(self):
        context = self.prepare()
        self.approve(context)
        self.flow.check_resolve(self.payload(context))
        self.flow.review({"result is correct": "Verified current artifacts and equivalence."})
        state = self.flow.load()
        state["check_resolutions"][0]["replacement_check_sha256"] = "0" * 64
        with self.assertRaisesRegex(self.runtime.Blocked, "still failing"):
            self.flow.reviewed(state)
        state = self.flow.load()
        state["check_resolutions"][0]["reason"] = "A changed resolution needs semantic review again."
        with self.assertRaisesRegex(self.runtime.Blocked, "check resolutions changed"):
            self.flow.reviewed(state)
        (self.root / "answer.md").write_text("a new document version\n")
        fresh = self.flow.review_operation("start")
        self.approve(fresh)
        with self.assertRaisesRegex(self.runtime.Blocked, "Replacement check"):
            self.flow.check_resolve(self.payload(fresh))
        with self.assertRaisesRegex(self.runtime.Blocked, "still failing"):
            self.flow.review({"result is correct": "The earlier snapshot covered code but not this document revision."})


    def test_original_windows_root_is_checked_before_resolving_or_running_git(self):
        from ecosystem.runtime import workspace
        for constructor in (self.runtime.Workflow, workspace.Workspace):
            with self.subTest(constructor=constructor.__name__), \
                    patch.object(self.runtime.ps, "IS_WINDOWS", True), \
                    patch.object(self.runtime.ps, "validate_lookup",
                                 side_effect=self.runtime.ps.PlatformError("unsafe original lookup")) as validate, \
                    patch.object(self.runtime, "git") as git:
                with self.assertRaises(self.runtime.ps.PlatformError):
                    constructor(Path("C:/unsafe-link"), "synthetic")
                validate.assert_called_once()
                git.assert_not_called()

    def test_windows_unsafe_relative_names_fail_before_filesystem_lookup(self):
        from ecosystem.runtime import workspace, review_gate
        invalid = ["C:relative.md", "C:/absolute.md", "/root.md", "report.md:stream",
                   "CON.txt", "aux", "LPT1.log", "trailing. ", "folder/../escape.md",
                   "folder\\\\escape.md", "file. ", "\\\\server\\\\share\\\\x.md"]
        with patch.object(self.runtime.ps, "IS_WINDOWS", True):
            for name in invalid:
                with self.subTest(name=name), self.assertRaises((self.runtime.Blocked, review_gate.ReviewError)):
                    self.runtime.safe_path(self.root, name)
                with self.subTest(workspace=name), self.assertRaises(self.runtime.Blocked):
                    workspace.relative(name)
                with self.subTest(review=name), self.assertRaises(review_gate.ReviewError):
                    review_gate._path(self.root, name)

    def test_existing_case_alias_is_rejected_without_globally_folding_linux_names(self):
        (self.root / "Report.md").write_text("one physical artifact", encoding="utf-8")
        with self.assertRaises(self.runtime.Blocked):
            self.runtime._windows_case_path(self.root, "report.md")
        self.runtime._windows_case_path(self.root, "Report.md")

    @unittest.skipUnless(os.name == "nt", "Native Windows ACL acceptance is unexecuted on POSIX.")
    def test_windows_state_is_private_utf8_and_acl_changes_invalidate_review(self):
        self.flow.begin("native-windows-state")
        self.flow.plan({"requirements": ["preserve Unicode"], "paths": ["Résumé.md"]})
        artifact = self.root / "Résumé.md"
        artifact.write_text("Synthetic café and 中文.\n", encoding="utf-8")
        self.flow.log("synthetic_unicode", label="café 中文")
        self.runtime.ps.verify_access(self.flow.home, private=True)
        self.runtime.ps.verify_access(self.flow.path, private=True)
        self.assertIn("café 中文", (self.flow.home / "events.jsonl").read_text(encoding="utf-8"))
        before = self.flow.review_operation("prepare")["token"]
        self.runtime.ps.set_access(artifact, 0o600)
        after = self.flow.review_operation("prepare")["token"]
        self.assertNotEqual(before, after)

    @unittest.skipUnless(os.name == "nt", "Native Windows Git logical-mode acceptance is unexecuted on POSIX.")
    def test_windows_git_index_mode_changes_the_artifact_snapshot(self):
        before = self.runtime.snapshot(self.root, ["README.md"])
        self.git("update-index", "--chmod=+x", "README.md")
        after = self.runtime.snapshot(self.root, ["README.md"])
        self.assertNotEqual(before, after)
        self.assertTrue(after["README.md"].startswith("100755:"))



    def test_existing_hardlink_aliases_cannot_form_two_artifacts(self):
        from ecosystem.runtime import review_gate
        self.flow.begin("physical-aliases")
        first, second = self.root / "one.md", self.root / "two.md"
        first.write_text("one physical artifact\n", encoding="utf-8")
        os.link(first, second)
        with self.assertRaises(self.runtime.Blocked):
            self.flow.plan({"requirements": ["distinct outputs"], "paths": ["one.md", "two.md"]})
        state = {"requirements": ["distinct outputs"], "paths": ["one.md", "two.md"],
                 "author": "coordinator", "started": "2026-10-29T00:00:00Z",
                 "initial_head": self.git("rev-parse", "HEAD")}
        with self.assertRaises(review_gate.ReviewError):
            review_gate.prepare(self.root, state)

    def test_real_distinct_case_sensitive_artifacts_remain_allowed(self):
        first, second = self.root / "Report.md", self.root / "report.md"
        first.write_text("first", encoding="utf-8")
        if second.exists():
            self.skipTest("This filesystem aliases the two case variants.")
        second.write_text("second", encoding="utf-8")
        self.flow.begin("distinct-case-sensitive-artifacts")
        self.flow.plan({"requirements": ["distinct outputs"], "paths": ["Report.md", "report.md"],
                        "adopt_existing": {"Report.md": "Synthetic fixture input.",
                                           "report.md": "A distinct synthetic fixture."}})
        version = self.runtime.snapshot(self.root, ["Report.md", "report.md"])
        self.assertEqual(set(version), {"Report.md", "report.md"})
        self.assertNotEqual(version["Report.md"], version["report.md"])

    def test_withdrawn_author_alias_cannot_self_review_or_resolve(self):
        self.flow.begin("physical-authorship")
        self.flow.plan({"requirements": ["correct result"], "paths": ["old.md"]})
        (self.root / "old.md").write_text("same artifact", encoding="utf-8")
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        os.link(self.root / "old.md", self.root / "new.md")
        self.flow.plan({"requirements": ["correct result"], "paths": ["new.md"]})
        if os.name == "nt":
            with self.assertRaises((self.runtime.Blocked, self.runtime.ps.PlatformError)):
                self.flow.review_operation("start")
            return
        context = self.flow.review_operation("start")
        self.assertEqual(context["artifact_authors"]["writer"], ["new.md"])
        with self.assertRaisesRegex(self.runtime.Blocked, "contributed"):
            self.report(context, "writer", ["correctness"])
        introduced = {"id": "physical-alias-finding", "path": "new.md", "line": 1,
                      "severity": "low", "origin": "introduced", "scenario": "Synthetic missing case.",
                      "consequence": "Synthetic incomplete result.", "evidence": "Fixture observation."}
        self.flow.review_operation("report", {
            "token": context["token"], "reviewer": "discoverer", "role": "reviewer",
            "focus": ["correctness"], "paths": ["new.md"], "findings": [introduced],
            "summary": "One synthetic finding.", "evidence": "Read the isolated fixture."})
        with self.assertRaisesRegex(self.runtime.Blocked, "contributing author"):
            self.flow.review_operation("resolve", {"token": context["token"],
                "id": introduced["id"], "verifier": "writer", "disposition": "fixed",
                "evidence": "This author cannot independently attest."})
        with self.assertRaisesRegex(self.runtime.Blocked, "independent"):
            self.flow._check_resolution(self.flow.load(), self.payload(context, verifier="writer"), context)

    def test_new_author_alias_invalidates_an_older_independent_report(self):
        self.flow.begin("late-alias")
        self.flow.plan({"requirements": ["correct outputs"], "paths": ["old.md", "new.md"]})
        (self.root / "old.md").write_text("earlier authored file", encoding="utf-8")
        (self.root / "new.md").write_text("a separate output", encoding="utf-8")
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        context = self.flow.review_operation("start")
        self.report(context, "writer", ["correctness"], ["new.md"])
        (self.root / "old.md").unlink()
        os.link(self.root / "new.md", self.root / "old.md")
        with self.assertRaises((self.runtime.Blocked, self.runtime.ps.PlatformError)):
            self.flow.review_operation("prepare")
        with self.assertRaises((self.runtime.Blocked, self.runtime.ps.PlatformError)):
            self.flow.independent_reviewed(self.flow.load())

    def test_git_state_original_symlink_is_rejected_before_state_creation(self):
        from ecosystem.runtime import workspace
        self.flow.home.rmdir()
        target = self.base / "foreign-empty-state"
        target.mkdir()
        try:
            self.flow.home.symlink_to(target, target_is_directory=True)
        except OSError as error:
            if os.name == "nt":
                self.skipTest("Native symlink privilege unavailable: " + type(error).__name__)
            raise
        for constructor in (self.runtime.Workflow, workspace.Workspace):
            with self.subTest(controller=constructor.__name__), self.assertRaises(
                    (self.runtime.Blocked, self.runtime.ps.PlatformError)):
                constructor(self.root, "blocked-state-alias")
        self.assertEqual(list(target.iterdir()), [])
        self.assertTrue(self.flow.home.is_symlink())

    def test_git_state_lookup_accepts_a_real_linked_worktree(self):
        worktree = self.base / "linked-receiver"
        self.git("worktree", "add", "-b", "synthetic-linked", str(worktree))
        other = self.runtime.Workflow(worktree, "linked-owner")
        self.assertFalse(other.home.is_relative_to(worktree))
        self.assertEqual(other.home, Path(self.git("rev-parse", "--path-format=absolute",
                                                  "--git-path", "constellation", cwd=worktree)))
        with other.lock():
            self.assertTrue(other.home.is_dir())



    def test_existing_case_alias_cannot_split_artifact_scope(self):
        from ecosystem.runtime import review_gate
        self.flow.begin("existing-case-alias")
        (self.root / "Report.md").write_text("one artifact", encoding="utf-8")
        if not (self.root / "report.md").exists():
            self.skipTest("Filesystem keeps the two case variants distinct.")
        with self.assertRaises(self.runtime.Blocked):
            self.flow.plan({"requirements": ["one artifact"], "paths": ["Report.md", "report.md"]})
        state = {"requirements": ["one artifact"], "paths": ["Report.md", "report.md"],
                 "author": "coordinator", "started": "2026-10-29T00:00:00Z",
                 "initial_head": self.git("rev-parse", "HEAD")}
        with self.assertRaises(review_gate.ReviewError):
            review_gate.prepare(self.root, state)

    def test_existing_case_alias_preserves_cumulative_author_independence(self):
        self.flow.begin("case-alias-authorship")
        self.flow.plan({"requirements": ["one artifact"], "paths": ["Report.md"]})
        (self.root / "Report.md").write_text("one artifact", encoding="utf-8")
        if not (self.root / "report.md").exists():
            self.skipTest("Filesystem keeps the two case variants distinct.")
        self.flow.review_operation("author", {"author": "writer", "paths": ["Report.md"]})
        if os.name == "nt":
            with self.assertRaises(self.runtime.Blocked):
                self.flow.plan({"requirements": ["one artifact"], "paths": ["report.md"]})
            return
        self.flow.plan({"requirements": ["one artifact"], "paths": ["report.md"]})
        context = self.flow.review_operation("start")
        self.assertEqual(context["artifact_authors"]["writer"], ["report.md"])
        with self.assertRaisesRegex(self.runtime.Blocked, "contributed"):
            self.report(context, "writer", ["correctness"])

    @unittest.skipUnless(os.name == "nt", "Prospective native Windows case handling is unexecuted on POSIX.")
    def test_windows_prospective_case_aliases_are_rejected_by_plan(self):
        self.flow.begin("future-case-alias")
        with self.assertRaises(self.runtime.Blocked):
            self.flow.plan({"requirements": ["distinct future artifacts"],
                            "paths": ["Future.md", "future.md"]})



    def test_actual_destination_change_invalidates_a_check_resolution(self):
        context = self.prepare()
        self.approve(context)
        self.flow.check_resolve(self.payload(context))
        self.git("config", "remote.origin.url", str(self.base / "different-unowned-remote.git"))
        with self.assertRaises(self.runtime.Blocked):
            self.flow.review({"result is correct": "A changed destination must remain blocked."})
        with self.assertRaises(self.runtime.Blocked):
            self.flow.resolved_checks(self.flow.load())


    def test_git_state_windows_namespaces_fail_before_filesystem_probe(self):
        invalid = ["C:relative-state", chr(92) + "root-relative-state",
                   chr(92) * 2 + "server" + chr(92) + "share" + chr(92) + "state"]
        for value in invalid:
            with self.subTest(value=value), patch.object(self.runtime.ps, "IS_WINDOWS", True), \
                    patch.object(self.runtime, "git", return_value=value), \
                    patch.object(self.runtime.ps, "is_reparse",
                                 side_effect=AssertionError("Unsafe lookup must not be probed.")):
                with self.assertRaises(self.runtime.Blocked):
                    self.runtime.git_state_home(self.root)


    def test_short_name_metadata_alias_is_rejected_without_reading_private_contents(self):
        from ecosystem.runtime import review_gate
        private = self.root / "conversations"
        private.mkdir()
        secret = private / "manifest.json"
        secret.write_text("synthetic private fixture", encoding="utf-8")
        alias = self.root / "CONVER~1"
        alias_file = alias / "MANIFE~1.JSO"
        actual_stat, actual_lstat = Path.stat, Path.lstat

        def mapped(path):
            if path == alias:
                return private
            if path == alias_file:
                return secret
            return path

        def metadata_stat(path, *args, **kwargs):
            return actual_stat(mapped(path), *args, **kwargs)

        def metadata_lstat(path, *args, **kwargs):
            return actual_lstat(mapped(path), *args, **kwargs)

        name = "CONVER~1/MANIFE~1.JSO"
        self.assertFalse(self.runtime.private_path(name))
        with patch.object(Path, "stat", new=metadata_stat), \
                patch.object(Path, "lstat", new=metadata_lstat), \
                patch.object(self.runtime.ps, "IS_WINDOWS", True), \
                patch.object(Path, "read_bytes", side_effect=AssertionError("No content read.")) as reads, \
                patch.object(Path, "read_text", side_effect=AssertionError("No content read.")) as texts, \
                patch.object(Path, "open", side_effect=AssertionError("No content read.")) as opens:
            with self.assertRaises(self.runtime.Blocked):
                self.runtime._windows_case_path(self.root, name)
            with self.assertRaises(self.runtime.Blocked):
                self.runtime.safe_path(self.root, name)
            with self.assertRaises(review_gate.ReviewError):
                review_gate._path(self.root, name)
            self.assertEqual((reads.call_count, texts.call_count, opens.call_count), (0, 0, 0))

    def test_literal_tilde_and_missing_prospective_components_remain_allowed(self):
        from ecosystem.runtime import review_gate
        (self.root / "literal~1.txt").write_text("public fixture", encoding="utf-8")
        with patch.object(self.runtime.ps, "IS_WINDOWS", True):
            self.assertEqual(self.runtime.safe_path(self.root, "literal~1.txt"), "literal~1.txt")
            self.assertEqual(review_gate._path(self.root, "literal~1.txt"), self.root / "literal~1.txt")
            self.assertEqual(self.runtime.safe_path(self.root, "future~1/new.md"), "future~1/new.md")
            self.assertEqual(review_gate._path(self.root, "future~1/new.md"), self.root / "future~1/new.md")

    def test_trusted_root_short_spelling_is_not_classified_as_a_scoped_component(self):
        short_root = self.base / "TRUSTE~1"
        actual_stat, actual_iterdir = Path.stat, Path.iterdir

        def metadata_stat(path, *args, **kwargs):
            return actual_stat(self.root if path == short_root else path, *args, **kwargs)

        def directory_entries(path):
            return actual_iterdir(self.root if path == short_root else path)

        with patch.object(Path, "stat", new=metadata_stat), \
                patch.object(Path, "iterdir", new=directory_entries):
            self.runtime._windows_case_path(short_root, "README.md")

    @unittest.skipUnless(os.name == "nt", "Native NTFS8.3 acceptance is unexecuted on POSIX.")
    def test_native_windows_short_private_path_is_rejected_without_content_reads(self):
        import ctypes
        from ctypes import wintypes
        private = self.root / "conversations"
        private.mkdir()
        secret = private / "manifest.json"
        secret.write_text("synthetic private fixture", encoding="utf-8")
        operation = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
        operation.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        operation.restype = wintypes.DWORD

        def short_path(path):
            buffer = ctypes.create_unicode_buffer(32768)
            count = operation(str(path), buffer, len(buffer))
            if not count or count >= len(buffer):
                self.skipTest("NTFS short-path lookup is unavailable; native8.3 proof remains pending.")
            return Path(buffer.value)

        short_root, short_file = short_path(self.root), short_path(secret)
        relative = short_file.relative_to(short_root).as_posix()
        if relative.casefold() == "conversations/manifest.json" or self.runtime.private_path(relative):
            self.skipTest("The volume exposes no privacy-obscuring8.3 alias; that native case remains pending.")
        self.runtime._windows_case_path(short_root, "README.md")
        with patch.object(Path, "read_bytes", side_effect=AssertionError("No private content read.")) as reads, \
                patch.object(Path, "read_text", side_effect=AssertionError("No private content read.")) as texts:
            with self.assertRaises(self.runtime.Blocked):
                self.runtime.safe_path(short_root, relative)
            self.assertEqual((reads.call_count, texts.call_count), (0, 0))

    def test_renamed_then_unlinked_author_cannot_review_the_new_name(self):
        self.flow.begin("renamed-authored-artifact")
        self.flow.plan({"requirements": ["correct output"], "paths": ["old.md"]})
        (self.root / "old.md").write_text("authored output", encoding="utf-8")
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        os.link(self.root / "old.md", self.root / "new.md")
        (self.root / "old.md").unlink()
        self.flow.plan({"requirements": ["correct output"], "paths": ["new.md"]})
        context = self.flow.review_operation("start")
        self.assertEqual(context["review_authors"]["writer"], ["old.md"])
        self.assertEqual(context["artifact_authors"]["writer"], ["new.md"])
        with self.assertRaisesRegex(self.runtime.Blocked, "unresolved"):
            self.report(context, "writer", ["correctness"])

    def test_missing_withdrawn_contribution_excludes_all_current_artifacts_and_keeps_receipts(self):
        context = self.prepare()
        self.approve(context)
        self.flow.check_resolve(self.payload(context))
        previous = self.flow.load()
        receipt = json.loads(json.dumps(previous["check_resolutions"]))
        checks = json.loads(json.dumps(previous["checks"]))
        tool = self.root / ".codex/tool.py"
        new_tool = self.root / ".codex/renamed_tool.py"
        os.link(tool, new_tool)
        tool.unlink()
        self.flow.plan({"requirements": ["result is correct"],
                        "paths": [".codex/renamed_tool.py", "answer.md"]})
        context = self.flow.review_operation("start")
        self.assertEqual(context["artifact_authors"]["writer"], [".codex/renamed_tool.py", "answer.md"])
        self.assertEqual(self.flow.load()["review_authors"]["writer"], [".codex/tool.py"])
        self.assertEqual(self.flow.load()["check_resolutions"], receipt)
        self.assertEqual(self.flow.load()["checks"], checks)
        with self.assertRaises(self.runtime.Blocked):
            self.report(context, "writer", ["correctness"], ["answer.md"])

    def test_current_in_scope_disjoint_contributor_can_review(self):
        self.flow.begin("current-disjoint-contribution")
        self.flow.plan({"requirements": ["correct outputs"], "paths": ["old.md", "new.md"]})
        (self.root / "old.md").write_text("current contribution", encoding="utf-8")
        (self.root / "new.md").write_text("independent current output", encoding="utf-8")
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        context = self.flow.review_operation("start")
        self.assertEqual(context["artifact_authors"]["writer"], ["old.md"])
        self.report(context, "writer", ["correctness"], ["new.md"])

    def test_planned_deletion_keeps_its_named_authorship_without_claiming_disjoint_outputs(self):
        old = self.root / "old.md"
        old.write_text("tracked old artifact", encoding="utf-8")
        self.git("add", "old.md")
        self.git("commit", "-m", "Track synthetic deletion")
        self.git("push", "origin", "main")
        self.flow.begin("explicit-deletion")
        self.flow.plan({"requirements": ["delete old and create unrelated output"],
                        "paths": ["old.md", "new.md"], "deletions": ["old.md"]})
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        (self.root / "new.md").write_text("unrelated current artifact", encoding="utf-8")
        self.assertNotEqual(old.stat().st_ino, (self.root / "new.md").stat().st_ino)
        old.unlink()
        context = self.flow.review_operation("start")
        self.assertEqual(context["artifact_authors"]["writer"], ["old.md"])
        self.report(context, "writer", ["correctness"], ["new.md"])

    def windows_snapshot_metadata(self, permission):
        original = self.runtime.snapshot

        def version(root, paths, deletions=()):
            actual = original(root, paths, deletions)
            result = {}
            for name, value in actual.items():
                if isinstance(value, str) and value.startswith(("100644:", "100755:")):
                    fields = value.split(":")
                    result[name] = fields[0] + ":" + fields[1] + ":" + permission["value"]
                else:
                    result[name] = value
            return result
        return version

    def test_git_projection_accepts_only_recognized_snapshot_formats(self):
        digest, acl = "a" * 64, "b" * 64
        version = {"plain": "100644:" + digest, "executable": "100755:" + digest + ":" + acl,
                   "link": "symlink:" + digest, "deleted": None}
        expected = {"plain": "100644:" + digest, "executable": "100755:" + digest,
                    "link": "symlink:" + digest, "deleted": None}
        before = dict(version)
        self.assertEqual(self.runtime.git_representable_snapshot(version), expected)
        self.assertEqual(version, before)
        malformed = [True, 123, "", "100600:" + digest, "100644:" + digest + ":arbitrary",
                     "100644:" + digest + ":" + acl + ":extra", "100644:" + digest + ":",
                     "100644:" + digest[:-1], "100644:" + digest.upper(),
                     "symlink:" + digest + ":" + acl]
        for value in malformed:
            with self.subTest(value=value), self.assertRaises(self.runtime.Blocked):
                self.runtime.git_representable_snapshot({"bad": value})

    def test_windows_metadata_projection_allows_real_git_commit_and_recovery_preserving_index(self):
        permission = {"value": "b" * 64}
        with patch.object(self.runtime, "snapshot", side_effect=self.windows_snapshot_metadata(permission)):
            (self.root / "README.md").write_text("unrelated staged user work", encoding="utf-8")
            self.git("add", "README.md")
            context = self.prepare()
            self.approve(context)
            self.flow.check_resolve(self.payload(context))
            self.flow.review({"result is correct": "Synthetic Windows metadata with reviewed bytes."})
            preserved = self.git("diff", "--cached", "--binary", "--", "README.md")
            self.flow.commit(context["paths"], "Commit reviewed fixture", preserve_index=True)
            self.assertEqual(self.git("diff", "--cached", "--binary", "--", "README.md"), preserved)
            state = self.flow.load()
            state["publication_blocker"] = "Synthetic recovered-publication check."
            self.flow.save(state)
            head = self.git("rev-parse", "HEAD")
            self.assertTrue(self.flow.recover(head)["recovered"])
            self.assertEqual(self.git("diff", "--cached", "--binary", "--", "README.md"), preserved)

    def test_windows_metadata_acl_drift_still_blocks_before_git_staging(self):
        permission = {"value": "b" * 64}
        with patch.object(self.runtime, "snapshot", side_effect=self.windows_snapshot_metadata(permission)):
            context = self.prepare()
            self.approve(context)
            self.flow.check_resolve(self.payload(context))
            self.flow.review({"result is correct": "Synthetic Windows metadata with reviewed bytes."})
            permission["value"] = "c" * 64
            before = (self.root / ".git/index").read_bytes()
            with self.assertRaises(self.runtime.Blocked):
                self.flow.commit(context["paths"], "Must remain blocked")
            self.assertEqual((self.root / ".git/index").read_bytes(), before)

    def test_windows_projection_does_not_accept_git_eol_normalization(self):
        permission = {"value": "b" * 64}
        with patch.object(self.runtime, "snapshot", side_effect=self.windows_snapshot_metadata(permission)):
            self.flow.begin("strict-byte-contract")
            self.flow.plan({"requirements": ["literal reviewed bytes"], "paths": ["answer.md"]})
            (self.root / "answer.md").write_bytes(b"reviewed literal bytes\r\n")
            self.git("config", "core.autocrlf", "true")
            context = self.flow.review_operation("start")
            self.report(context, "independent", ["correctness"])
            self.flow.review({"literal reviewed bytes": "Literal bytes remain authoritative."})
            head = self.git("rev-parse", "HEAD")
            with self.assertRaisesRegex(self.runtime.Blocked, "Staged content differs"):
                self.flow.commit(["answer.md"], "Must not normalize reviewed bytes")
            self.assertEqual(self.git("rev-parse", "HEAD"), head)

    @unittest.skipUnless(os.name == "nt", "Native Windows commit/index acceptance is unexecuted on POSIX.")
    def test_native_windows_commit_preserves_acl_evidence_and_foreign_index(self):
        (self.root / "README.md").write_text("unrelated staged work", encoding="utf-8")
        self.git("add", "README.md")
        preserved = self.git("diff", "--cached", "--binary", "--", "README.md")
        context = self.prepare()
        self.approve(context)
        self.flow.check_resolve(self.payload(context))
        self.flow.review({"result is correct": "Native Windows reviewed ACL and byte evidence."})
        self.flow.commit(context["paths"], "Commit native Windows fixture", preserve_index=True)
        self.assertEqual(self.git("diff", "--cached", "--binary", "--", "README.md"), preserved)
        self.assertEqual(self.git("rev-parse", "HEAD"),
                         self.git("rev-parse", "refs/heads/main", cwd=self.remote))


    def test_reused_withdrawn_author_name_cannot_restore_independence(self):
        self.flow.begin("reused-historical-name")
        self.flow.plan({"requirements": ["correct output"], "paths": ["old.md"]})
        old, new = self.root / "old.md", self.root / "new.md"
        old.write_text("the writer authored these bytes", encoding="utf-8")
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        old.rename(new)
        old.write_text("an independent replacement at the old name", encoding="utf-8")
        self.assertNotEqual((old.stat().st_dev, old.stat().st_ino),
                            (new.stat().st_dev, new.stat().st_ino))
        self.flow.plan({"requirements": ["correct output"], "paths": ["new.md"],
                        "unrelated": {"old.md": "Independent replacement preserved outside the output scope."}})
        context = self.flow.review_operation("start")
        self.assertEqual(context["review_authors"]["writer"], ["old.md"])
        with self.assertRaisesRegex(self.runtime.Blocked, "contributed|unresolved"):
            self.report(context, "writer", ["correctness"])


    def test_existing_withdrawn_name_does_not_prove_historical_independence(self):
        self.flow.begin("existing-withdrawn-contribution")
        self.flow.plan({"requirements": ["correct output"], "paths": ["old.md"]})
        (self.root / "old.md").write_text("earlier contribution", encoding="utf-8")
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        (self.root / "new.md").write_text("different live file", encoding="utf-8")
        self.flow.plan({"requirements": ["correct output"], "paths": ["new.md"],
                        "unrelated": {"old.md": "Historical artifact preserved outside the current output."}})
        context = self.flow.review_operation("start")
        self.assertEqual(context["review_authors"]["writer"], ["old.md"])
        self.assertEqual(context["artifact_authors"]["writer"], ["new.md"])
        with self.assertRaisesRegex(self.runtime.Blocked, "unresolved"):
            self.report(context, "writer", ["correctness"])


    def test_in_scope_old_name_reuse_cannot_hide_the_authored_original(self):
        self.flow.begin("in-scope-name-reuse")
        self.flow.plan({"requirements": ["correct outputs"], "paths": ["old.md", "new.md"]})
        old, new = self.root / "old.md", self.root / "new.md"
        old.write_text("the original authored object", encoding="utf-8")
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        old.rename(new)
        old.write_text("an independent replacement", encoding="utf-8")
        context = self.flow.review_operation("start")
        with self.assertRaisesRegex(self.runtime.Blocked, "contributed|unresolved"):
            self.report(context, "writer", ["correctness"], ["new.md"])

    def test_planned_deletion_cannot_drop_a_renamed_original_author(self):
        old, new = self.root / "old.md", self.root / "new.md"
        old.write_text("the original authored object", encoding="utf-8")
        self.git("add", "old.md")
        self.git("commit", "-m", "Track synthetic original")
        self.git("push", "origin", "main")
        self.flow.begin("declared-deletion-name-reuse")
        self.flow.plan({"requirements": ["correct outputs"], "paths": ["old.md", "new.md"],
                        "deletions": ["old.md"]})
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        old.rename(new)
        context = self.flow.review_operation("start")
        with self.assertRaisesRegex(self.runtime.Blocked, "contributed|unresolved"):
            self.report(context, "writer", ["correctness"], ["new.md"])


    def fresh_bound_current_outputs(self):
        self.flow.begin("bound-current-outputs")
        self.flow.plan({"requirements": ["correct outputs"], "paths": ["one.md", "two.md"]})
        (self.root / "one.md").write_text("current contribution", encoding="utf-8")
        (self.root / "two.md").write_text("independent output", encoding="utf-8")
        self.flow.review_operation("author", {"author": "writer", "paths": ["one.md"]})

    def test_author_binding_registration_is_idempotent_and_appends_new_objects(self):
        self.fresh_bound_current_outputs()
        before = self.flow.load()["review_author_bindings"]["writer"]
        self.assertEqual(len(before), 1)
        self.assertIsNotNone(before[0]["identity"])
        self.assertTrue(self.flow.review_operation("author", {"author": "writer",
                                                            "paths": ["one.md"]})["unchanged"])
        self.assertEqual(self.flow.load()["review_author_bindings"]["writer"], before)
        replacement = self.root / "replacement.tmp"
        replacement.write_text("new object contributed later", encoding="utf-8")
        replacement.replace(self.root / "one.md")
        uncertain = self.flow.review_operation("prepare")
        self.assertEqual(uncertain["artifact_authors"]["writer"], ["one.md", "two.md"])
        self.assertFalse(self.flow.review_operation("author", {"author": "writer",
                                                             "paths": ["one.md"]})["unchanged"])
        after = self.flow.load()["review_author_bindings"]["writer"]
        self.assertEqual(after[:len(before)], before)
        self.assertEqual(len(after), 2)
        context = self.flow.review_operation("start")
        self.assertEqual(context["artifact_authors"]["writer"], ["one.md"])
        self.report(context, "writer", ["correctness"], ["two.md"])

    def test_current_unobserved_author_history_stays_conservative_and_noncontributors_can_close(self):
        self.fresh_bound_current_outputs()
        state = self.flow.load()
        state.pop("review_author_bindings")
        self.flow.save(state)
        unobserved = self.flow.review_operation("prepare")
        self.assertEqual(unobserved["artifact_authors"]["writer"], ["one.md", "two.md"])
        self.assertNotIn("review_author_bindings", self.flow.load())
        self.flow.review_operation("author", {"author": "writer", "paths": ["one.md"]})
        records = self.flow.load()["review_author_bindings"]["writer"]
        self.assertIsNone(records[0]["identity"])
        self.assertIsNotNone(records[1]["identity"])
        context = self.flow.review_operation("start")
        self.assertEqual(context["artifact_authors"]["writer"], ["one.md", "two.md"])
        with self.assertRaisesRegex(self.runtime.Blocked, "unresolved"):
            self.report(context, "writer", ["correctness"], ["two.md"])
        self.report(context, "fresh-independent", ["correctness"])
        self.flow.review({"correct outputs": "Fresh noncontributor checked the exact artifacts."})
        self.flow.commit(context["paths"], "Close synthetic contract with unobserved history")
        self.assertTrue(self.flow.finish()["completed"])

    def test_unknown_observation_cannot_be_erased_by_later_known_registration(self):
        self.flow.begin("unknown-observation")
        self.flow.plan({"requirements": ["correct outputs"], "paths": ["one.md", "two.md"]})
        self.flow.review_operation("author", {"author": "writer", "paths": ["one.md"]})
        initial = self.flow.load()["review_author_bindings"]["writer"]
        self.assertEqual(initial, [{"path": "one.md", "identity": None}])
        (self.root / "one.md").write_text("now observable", encoding="utf-8")
        (self.root / "two.md").write_text("another output", encoding="utf-8")
        before = self.flow.review_operation("prepare")
        self.flow.review_operation("author", {"author": "writer", "paths": ["one.md"]})
        records = self.flow.load()["review_author_bindings"]["writer"]
        self.assertEqual(records[:len(initial)], initial)
        self.assertEqual(len(records), 2)
        after = self.flow.review_operation("prepare")
        self.assertEqual(before["artifact_authors"], after["artifact_authors"])
        self.assertNotEqual(before["token"], after["token"])
        self.assertTrue(self.flow.review_operation("author", {"author": "writer",
                                                            "paths": ["one.md"]})["unchanged"])
        self.assertEqual(self.flow.load()["review_author_bindings"]["writer"], records)

    def test_author_binding_history_rejects_malformed_or_reassigned_records(self):
        from copy import deepcopy
        from ecosystem.runtime import review_gate
        self.fresh_bound_current_outputs()
        original = self.flow.load()
        record = original["review_author_bindings"]["writer"][0]
        cases = []
        for update in ({"device": True}, {"device": -1}, {"inode": 0},
                       {"inode": False}, {"kind": "symlink"}, {"extra": "unrecognized"}):
            state = deepcopy(original)
            state["review_author_bindings"]["writer"][0]["identity"].update(update)
            cases.append(state)
        for bad in ({"path": "other.md", "identity": record["identity"]},
                    {"path": "one.md", "identity": record["identity"], "extra": True}):
            state = deepcopy(original)
            state["review_author_bindings"]["writer"] = [bad]
            cases.append(state)
        duplicate = deepcopy(original)
        duplicate["review_author_bindings"]["writer"].append(deepcopy(record))
        cases.append(duplicate)
        reassigned = deepcopy(original)
        reassigned["review_author_bindings"]["unregistered"] = [deepcopy(record)]
        cases.append(reassigned)
        for state in cases:
            with self.subTest(binding=state["review_author_bindings"]), self.assertRaises(review_gate.ReviewError):
                review_gate.prepare(self.root, state)

    def test_retrying_a_known_missing_deletion_preserves_its_observation(self):
        old, new = self.root / "old.md", self.root / "new.md"
        old.write_text("tracked original", encoding="utf-8")
        self.git("add", "old.md")
        self.git("commit", "-m", "Track fixture deletion")
        self.git("push", "origin", "main")
        self.flow.begin("known-deletion-retry")
        self.flow.plan({"requirements": ["correct outputs"], "paths": ["old.md", "new.md"],
                        "deletions": ["old.md"]})
        new.write_text("independent current output", encoding="utf-8")
        self.flow.review_operation("author", {"author": "writer", "paths": ["old.md"]})
        records = self.flow.load()["review_author_bindings"]["writer"]
        old.unlink()
        self.assertTrue(self.flow.review_operation("author", {"author": "writer",
                                                            "paths": ["old.md"]})["unchanged"])
        self.assertEqual(self.flow.load()["review_author_bindings"]["writer"], records)
        context = self.flow.review_operation("start")
        self.assertEqual(context["artifact_authors"]["writer"], ["old.md"])
        self.report(context, "writer", ["correctness"], ["new.md"])

if __name__ == "__main__":
    unittest.main()
