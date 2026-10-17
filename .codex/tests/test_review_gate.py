"""Independent review rejects stale, incomplete and self-attested approvals."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "review_gate.py"
spec = importlib.util.spec_from_file_location("review_gate_test_module", MODULE)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
DEFAULT_POLICY = json.loads(MODULE.with_name("review-policy.json").read_text())


class ReviewFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.policy_path = self.base / "policy.json"
        self.policy_path.write_text(json.dumps(DEFAULT_POLICY))
        self.state = {"requirements": ["The requested behavior works"], "paths": ["tool.py"],
                      "deletions": [], "author": "author-session", "started": "task-start"}
        (self.root / "tool.py").write_text("print('works')\n")

    def tearDown(self):
        self.temp.cleanup()

    def call(self, name, *args):
        return getattr(gate, name)(self.root, self.state, *args, policy_path=self.policy_path)

    def start(self):
        return self.call("start")

    def payload(self, reviewer="reviewer-a", findings=None, **changes):
        return {"token": self.call("prepare")["token"], "reviewer": reviewer, "role": "reviewer",
                "focus": ["correctness"], "paths": list(self.state["paths"]),
                "summary": "Checked boundary conditions and the changed behavior.",
                "evidence": "The empty-input branch preserves its declared result type.",
                "findings": findings or [], **changes}

    def finding(self, identifier="empty-input", **changes):
        return {"id": identifier, "path": "tool.py", "line": 1, "severity": "high",
                "origin": "introduced", "scenario": "An empty input reaches the changed branch.",
                "consequence": "The caller receives the wrong result type.",
                "evidence": "The branch returns None while the caller iterates over its result.", **changes}

    def resolution(self, identifier="empty-input", **changes):
        return {"token": self.call("prepare")["token"], "id": identifier,
                "verifier": "verifier-c", "disposition": "fixed",
                "evidence": "The corrected branch returns an empty list and its regression test passes.", **changes}

    def complete(self):
        self.start()
        self.call("report", self.payload())
        self.call("validate")

    def test_standard_review_requires_fresh_independent_report(self):
        context = self.start()
        self.assertEqual(context["mode"], "standard")
        with self.assertRaisesRegex(gate.ReviewError, "distinct reviewers"):
            self.call("validate")
        self.call("report", self.payload())
        self.call("validate")

    def test_quick_docs_require_correctness_and_scope_cannot_be_withdrawn(self):
        self.state["paths"] = ["guide.md"]
        (self.root / "guide.md").write_text("Documentation\n")
        self.assertEqual(self.start()["mode"], "quick")
        self.call("report", self.payload())
        self.call("validate")
        self.state["paths"] = []
        with self.assertRaisesRegex(gate.ReviewError, "withdrawing"):
            self.call("validate")

    def test_readonly_task_needs_no_independent_review(self):
        self.state["paths"] = []
        self.assertEqual(self.start(), {"enabled": False, "reason": "read-only scope"})
        self.call("validate")

    def test_every_required_focus_covers_the_complete_scope(self):
        self.state["review_risk"] = "deep"
        self.state["paths"].append("other.py")
        (self.root / "other.py").write_text("pass\n")
        self.start()
        self.call("report", self.payload(paths=["tool.py"]))
        self.call("report", self.payload("security-reviewer", focus=["security"]))
        with self.assertRaisesRegex(gate.ReviewError, "correctness reports do not cover"):
            self.call("validate")
        self.call("report", self.payload("reviewer-c", paths=["other.py"]))
        self.call("validate")

    def test_deep_review_needs_distinct_reviewers_and_security(self):
        self.state["paths"] = [".codex/tool.py"]
        (self.root / ".codex").mkdir()
        (self.root / ".codex/tool.py").write_text("pass\n")
        self.assertEqual(self.start()["mode"], "deep")
        self.call("report", self.payload())
        with self.assertRaisesRegex(gate.ReviewError, "2 distinct reviewers"):
            self.call("validate")
        self.call("report", self.payload("reviewer-b"))
        with self.assertRaisesRegex(gate.ReviewError, "security"):
            self.call("validate")
        self.call("report", self.payload("reviewer-c", focus=["security"]))
        self.call("validate")

    def test_sensitive_documentation_overrides_quick_classification(self):
        for name in ["AGENTS.md", "REVIEW.md", ".github/README.md", "src/auth/README.md", "install.sh"]:
            with self.subTest(name=name):
                self.state["paths"] = [name]
                target = self.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("content\n")
                self.assertEqual(self.call("prepare")["mode"], "deep")

    def test_author_and_duplicate_report_do_not_supply_independence(self):
        self.start()
        with self.assertRaisesRegex(gate.ReviewError, "frozen task author"):
            self.call("report", self.payload("author-session"))
        payload = self.payload()
        self.call("report", payload)
        self.assertTrue(self.call("report", payload)["unchanged"])
        with self.assertRaisesRegex(gate.ReviewError, "different report"):
            self.call("report", {**payload, "summary": "Changed the conclusion."})
        self.assertEqual(len(self.state["review_gate"]["rounds"][0]["reports"]), 1)

    def test_declared_coverage_must_be_complete(self):
        self.state["paths"].append("other.py")
        (self.root / "other.py").write_text("pass\n")
        self.start()
        self.call("report", self.payload(paths=["tool.py"]))
        with self.assertRaisesRegex(gate.ReviewError, "cover every"):
            self.call("validate")
        self.call("report", self.payload("reviewer-b", paths=["other.py"]))
        self.call("validate")

    def test_stale_report_and_validation_reject_modified_artifact(self):
        self.complete()
        old = self.payload("reviewer-b")
        (self.root / "tool.py").write_text("print('changed')\n")
        with self.assertRaisesRegex(gate.ReviewError, "stale"):
            self.call("validate")
        self.start()
        with self.assertRaisesRegex(gate.ReviewError, "stale"):
            self.call("report", old)

    def test_mode_change_invalidates_review(self):
        self.complete()
        (self.root / "tool.py").chmod(0o755)
        with self.assertRaisesRegex(gate.ReviewError, "stale"):
            self.call("validate")

    def test_git_mode_uses_owner_execute_bit_only(self):
        target = self.root / "tool.py"
        self.complete()
        target.chmod(0o654)
        self.assertEqual(self.call("prepare")["artifacts"]["tool.py"]["mode"], "100644")
        self.call("validate")
        target.chmod(0o744)
        self.assertEqual(self.call("prepare")["artifacts"]["tool.py"]["mode"], "100755")
        with self.assertRaisesRegex(gate.ReviewError, "stale"):
            self.call("validate")

    def test_spaced_filename_evidence_binds_literal_file_and_finding(self):
        self.state["paths"] = ["tool.py "]
        target = self.root / "tool.py "
        target.write_text("print('literal spaced file')\n")
        context = self.start()
        self.assertEqual(context["paths"], ["tool.py "])
        self.assertEqual(set(context["artifacts"]), {"tool.py "})
        self.call("report", self.payload(findings=[self.finding(path="tool.py ")]))
        ledger = self.state["review_gate"]
        self.assertEqual(ledger["rounds"][-1]["reports"]["reviewer-a"]["paths"], ["tool.py "])
        self.assertEqual(ledger["findings"]["empty-input"]["path"], "tool.py ")
        self.call("resolve", self.resolution())
        (self.root / "tool.py").write_text("print('unrelated unspaced file changed')\n")
        self.call("validate")
        target.write_text("print('reviewed spaced file changed')\n")
        with self.assertRaisesRegex(gate.ReviewError, "stale"):
            self.call("validate")

    def test_spaced_and_unspaced_filenames_remain_distinct_scope_entries(self):
        self.state["paths"] = ["tool.py", "tool.py "]
        (self.root / "tool.py ").write_text("print('different file')\n")
        context = self.start()
        self.assertEqual(set(context["artifacts"]), {"tool.py", "tool.py "})
        self.assertNotEqual(context["artifacts"]["tool.py"], context["artifacts"]["tool.py "])
        self.call("report", self.payload())
        self.call("validate")

    def test_spaced_deletion_never_targets_unspaced_file(self):
        self.state["paths"] = ["tool.py "]
        self.state["deletions"] = ["tool.py "]
        target = self.root / "tool.py "
        target.write_text("delete this exact file\n")
        with self.assertRaisesRegex(gate.ReviewError, "Complete"):
            self.start()
        target.unlink()
        context = self.start()
        self.assertEqual(context["deletions"], ["tool.py "])
        self.assertEqual(context["artifacts"], {"tool.py ": None})
        self.call("report", self.payload())
        self.call("validate")
        self.assertTrue((self.root / "tool.py").is_file())

    def test_token_binds_requirement_scope_task_and_repository(self):
        original = self.call("prepare")["token"]
        for key, value in [("requirements", ["A different contract"]), ("author", "different-author"),
                           ("started", "different-task"), ("initial_head", "another-start")]:
            with self.subTest(key=key):
                state = {**self.state, key: value}
                self.assertNotEqual(gate.prepare(self.root, state, policy_path=self.policy_path)["token"], original)
        other = self.base / "other"
        other.mkdir()
        (other / "tool.py").write_text((self.root / "tool.py").read_text())
        self.assertNotEqual(gate.prepare(other, self.state, policy_path=self.policy_path)["token"], original)

    def test_successful_git_commit_does_not_invalidate_review(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.complete()
        subprocess.run(["git", "add", "tool.py"], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "Add tool"],
                       cwd=self.root, check=True)
        self.call("validate")

    def test_round_start_is_idempotent_and_replan_cannot_reset_cap(self):
        self.assertEqual(self.start()["round"], 1)
        self.assertTrue(self.start()["unchanged"])
        for number in (2, 3):
            self.state["requirements"] = [f"Contract revision {number}"]
            self.assertEqual(self.start()["round"], number)
        self.state["requirements"] = ["Contract revision 4"]
        before = deepcopy(self.state)
        with self.assertRaisesRegex(gate.ReviewError, "round limit"):
            self.start()
        self.assertEqual(self.state, before)

    def test_open_findings_survive_clean_report_and_replan(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        self.state["requirements"] = ["Extended contract"]
        self.start()
        self.call("report", self.payload("reviewer-b"))
        with self.assertRaisesRegex(gate.ReviewError, "empty-input"):
            self.call("validate")
        self.call("resolve", self.resolution())
        self.call("validate")

    def test_preexisting_findings_also_require_explicit_disposition(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding(origin="preexisting")]))
        with self.assertRaisesRegex(gate.ReviewError, "Unresolved"):
            self.call("validate")
        self.call("resolve", self.resolution(disposition="dismissed", evidence="The documented API explicitly permits this preexisting behavior."))
        self.call("validate")

    def test_resolution_requires_current_distinct_verifier_and_evidence(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        for changes in [{"verifier": "author-session"}, {"verifier": "reviewer-a"},
                        {"token": "stale"}, {"evidence": " "}, {"disposition": "ignored"}]:
            with self.subTest(changes=changes):
                before = deepcopy(self.state)
                with self.assertRaises(gate.ReviewError):
                    self.call("resolve", self.resolution(**changes))
                self.assertEqual(self.state, before)
        self.call("resolve", self.resolution())
        self.assertTrue(self.call("resolve", self.resolution())["unchanged"])
        self.call("validate")

    def test_repeated_finding_tracks_all_discoverers_without_duplication(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        self.call("report", self.payload("reviewer-b", findings=[self.finding()]))
        self.assertEqual(len(self.state["review_gate"]["findings"]), 1)
        with self.assertRaisesRegex(gate.ReviewError, "every finding discoverer"):
            self.call("resolve", self.resolution(verifier="reviewer-b"))

    def test_fixed_finding_reopens_if_its_file_changes(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        self.call("resolve", self.resolution())
        (self.root / "tool.py").write_text("print('another implementation')\n")
        self.start()
        self.call("report", self.payload())
        with self.assertRaisesRegex(gate.ReviewError, "empty-input"):
            self.call("validate")
        self.call("resolve", self.resolution())
        self.assertEqual(len(self.state["review_gate"]["findings"]["empty-input"]["resolutions"]), 2)
        self.call("validate")

    def test_resolved_finding_remains_closed_when_only_other_file_changes(self):
        self.state["paths"].append("other.py")
        (self.root / "other.py").write_text("pass\n")
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        self.call("resolve", self.resolution())
        (self.root / "other.py").write_text("print('other change')\n")
        self.start()
        self.call("report", self.payload())
        self.call("validate")

    def test_malformed_report_is_atomic_and_style_findings_rejected(self):
        self.start()
        for change in [{"severity": "nit"}, {"line": True}, {"line": 0}, {"path": "undeclared.py"},
                       {"id": "not stable id"}, {"evidence": ""}, {"origin": "unknown"}]:
            with self.subTest(change=change):
                before = deepcopy(self.state)
                with self.assertRaises(gate.ReviewError):
                    self.call("report", self.payload(findings=[self.finding("first"), self.finding("second", **change)]))
                self.assertEqual(self.state, before)

    def test_resolved_duplicate_rejection_is_atomic(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        self.call("resolve", self.resolution())
        before = deepcopy(self.state)
        with self.assertRaisesRegex(gate.ReviewError, "resolved finding"):
            self.call("report", self.payload("reviewer-b", findings=[self.finding("new"), self.finding()]))
        self.assertEqual(self.state, before)

    def test_report_fields_are_strict(self):
        self.start()
        for changes in [{"role": "author"}, {"focus": ["style"]}, {"paths": ["tool.py", "tool.py"]},
                        {"findings": None}, {"summary": True}, {"prompt": "should never be retained"}]:
            with self.subTest(changes=changes):
                before = deepcopy(self.state)
                with self.assertRaises(gate.ReviewError):
                    self.call("report", {**self.payload(), **changes})
                self.assertEqual(self.state, before)

    def test_missing_artifact_and_incomplete_deletion_block_start(self):
        self.state["paths"] = ["missing.py"]
        with self.assertRaisesRegex(gate.ReviewError, "Complete"):
            self.start()
        self.state["paths"] = ["tool.py"]
        self.state["deletions"] = ["tool.py"]
        with self.assertRaisesRegex(gate.ReviewError, "Complete"):
            self.start()
        (self.root / "tool.py").unlink()
        self.complete()

    def test_symlink_and_private_paths_rejected_without_reading_target(self):
        secret = self.base / "private.txt"
        secret.write_text("local-only content")
        (self.root / "link.py").symlink_to(secret)
        (self.root / "dir").symlink_to(self.base, target_is_directory=True)
        for name in ["link.py", "dir/private.txt", "../private.txt", ".env", "conversations/file.md", "rollout-private.md"]:
            with self.subTest(name=name):
                self.state["paths"] = [name]
                with patch.object(Path, "read_bytes", side_effect=AssertionError("must not read contents")):
                    with self.assertRaises(gate.ReviewError):
                        self.call("prepare")

    def test_policy_change_during_review_fails_closed(self):
        self.complete()
        policy = deepcopy(DEFAULT_POLICY)
        policy["modes"]["standard"]["reviewers"] = 2
        policy["modes"]["deep"]["reviewers"] = 3
        self.policy_path.write_text(json.dumps(policy))
        with self.assertRaisesRegex(gate.ReviewError, "policy changed"):
            self.call("validate")
        self.assertEqual(self.start()["round"], 2)
        self.call("report", self.payload())
        with self.assertRaisesRegex(gate.ReviewError, "2 distinct reviewers"):
            self.call("validate")
        self.call("report", self.payload("reviewer-b"))
        self.call("validate")

    def test_policy_downgrade_cannot_weaken_active_task_or_reset_findings(self):
        policy = deepcopy(DEFAULT_POLICY)
        policy["modes"]["standard"]["reviewers"] = 2
        self.policy_path.write_text(json.dumps(policy))
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        policy["modes"]["standard"]["reviewers"] = 1
        policy["max_rounds"] = 10
        policy["documentation_extensions"].append(".py")
        self.policy_path.write_text(json.dumps(policy))
        context = self.start()
        self.assertEqual(context["required_reviewers"], 2)
        self.assertEqual(context["max_rounds"], 3)
        self.assertEqual(context["mode"], "standard")
        self.assertEqual(self.state["review_gate"]["findings"]["empty-input"]["status"], "open")

    def test_semantic_risk_floor_raises_classification_and_cannot_fall(self):
        self.state["review_risk"] = "deep"
        self.assertEqual(self.start()["mode"], "deep")
        self.state["review_risk"] = "quick"
        self.assertEqual(self.call("prepare")["mode"], "deep")
        self.state["review_risk"] = "invalid"
        with self.assertRaisesRegex(gate.ReviewError, "Review risk"):
            self.call("prepare")

    def test_invalid_policy_never_turns_review_off(self):
        cases = [None, {}, {**DEFAULT_POLICY, "schema_version": True}, {**DEFAULT_POLICY, "max_rounds": True},
                 {**DEFAULT_POLICY, "max_rounds": 0}, {**DEFAULT_POLICY, "unknown": 1}]
        no_security = deepcopy(DEFAULT_POLICY)
        no_security["modes"]["deep"]["focus"] = {"correctness": 1}
        cases.append(no_security)
        lower_count = deepcopy(DEFAULT_POLICY)
        lower_count["modes"]["standard"]["reviewers"] = 3
        cases.append(lower_count)
        for value in cases:
            with self.subTest(value=value):
                self.policy_path.write_text(json.dumps(value))
                with self.assertRaises(gate.ReviewError):
                    self.call("prepare")
        self.policy_path.unlink()
        with self.assertRaises(gate.ReviewError):
            self.call("prepare")

    def test_focus_quorum_counts_distinct_agents(self):
        policy = deepcopy(DEFAULT_POLICY)
        policy["modes"]["standard"] = {"reviewers": 2, "focus": {"correctness": 2}}
        policy["modes"]["deep"]["focus"]["correctness"] = 2
        self.policy_path.write_text(json.dumps(policy))
        self.start()
        self.call("report", self.payload())
        self.call("report", self.payload("reviewer-b", focus=["security"]))
        with self.assertRaisesRegex(gate.ReviewError, "2 distinct reviewers with correctness"):
            self.call("validate")
        self.call("report", self.payload("reviewer-c"))
        self.call("validate")

    def test_outside_repository_has_no_implicit_policy(self):
        with patch.object(gate, "_read_json", side_effect=AssertionError("must not read central policy")):
            self.assertIsNone(gate.policy_for(self.root))
            self.assertEqual(gate.prepare(self.root, self.state), {"enabled": False})
            gate.validate(self.root, self.state)

    def test_native_registration_requires_actual_owner_and_installed_policy(self):
        config = self.root / ".codex"
        config.mkdir()
        (config / "repositories.json").write_text(json.dumps({"repositories": [{"path": ".", "management": "native"}]}))
        (config / "review-policy.json").write_text(json.dumps(DEFAULT_POLICY))
        with patch.object(gate, "__file__", str(config / "review_gate.py")):
            with self.assertRaisesRegex(gate.ReviewError, "owner"):
                gate.policy_for(self.root)
            subprocess.run(["git", "init", "-q", str(self.root)], check=True)
            self.assertEqual(gate.policy_for(self.root), DEFAULT_POLICY)
            (config / "review-policy.json").unlink()
            with self.assertRaisesRegex(gate.ReviewError, "must exist"):
                gate.policy_for(self.root)

    def test_external_and_unregistered_children_keep_their_own_policy(self):
        config = self.root / ".codex"
        config.mkdir()
        (config / "repositories.json").write_text(json.dumps({"repositories": [{"path": "external", "management": "external"}]}))
        with patch.object(gate, "__file__", str(config / "review_gate.py")):
            self.assertIsNone(gate.policy_for(self.root / "external"))
            self.assertIsNone(gate.policy_for(self.root / "unregistered"))


if __name__ == "__main__":
    unittest.main()
