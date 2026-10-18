"""Independent review rejects stale, incomplete and self-attested approvals."""
from __future__ import annotations

from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "ecosystem/runtime/review_gate.py"
sys.path.insert(0, str(MODULE.parents[2]))
from ecosystem.runtime import review_gate as gate

DEFAULT_POLICY = json.loads(MODULE.with_name("review-policy.json").read_text())
# Minimal quorums isolate each engine invariant; shipped quorums have dedicated
# end-to-end cases below and remain independent of these small fixtures.
MINIMAL_POLICY = {**DEFAULT_POLICY, "modes": {
    "quick": {"reviewers": 1, "focus": {"correctness": 1}},
    "standard": {"reviewers": 1, "focus": {"correctness": 1}},
    "deep": {"reviewers": 2, "focus": {"correctness": 1, "security": 1}},
}}


class ReviewFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.policy_path = self.base / "policy.json"
        self.policy_path.write_text(json.dumps(MINIMAL_POLICY))
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

    def quick_code(self, reason="Only the empty-input return value changes; its boundary regression passes."):
        return gate.start(self.root, self.state, policy_path=self.policy_path,
                          quick_code_reason=reason)

    def test_quick_code_declaration_permits_one_reviewer_and_is_idempotent(self):
        self.policy_path.write_text(json.dumps(DEFAULT_POLICY))
        context = self.quick_code()
        self.assertEqual((context["mode"], context["required_reviewers"]), ("quick", 1))
        self.assertIn("empty-input", context["quick_code_reason"])
        self.assertTrue(self.quick_code()["unchanged"])
        self.assertTrue(self.start()["unchanged"])
        self.call("report", self.payload())
        self.call("validate")

    def test_quick_code_requires_explicit_policy_consent(self):
        for consent in (None, False):
            with self.subTest(consent=consent):
                policy = deepcopy(DEFAULT_POLICY)
                policy.pop("allow_quick_code", None)
                if consent is not None:
                    policy["allow_quick_code"] = consent
                self.policy_path.write_text(json.dumps(policy))
                before = deepcopy(self.state)
                with self.assertRaisesRegex(gate.ReviewError, "policy"):
                    self.quick_code()
                self.assertEqual(self.state, before)
                self.assertEqual(self.call("prepare")["mode"], "standard")
        self.start()
        self.call("report", self.payload())
        self.call("report", self.payload("reviewer-b"))
        self.call("report", self.payload("reviewer-c"))
        self.call("validate")

    def test_quick_code_policy_consent_uses_and_and_rejects_malformed_values(self):
        allowed = {**DEFAULT_POLICY, "allow_quick_code": True}
        old = {key: value for key, value in DEFAULT_POLICY.items() if key != "allow_quick_code"}
        for other in (old, {**allowed, "allow_quick_code": False}):
            self.assertFalse(gate._policy_floor(allowed, other)["allow_quick_code"])
            self.assertFalse(gate._policy_floor(other, allowed)["allow_quick_code"])
        for invalid in (None, 0, 1, "true", [], {}):
            with self.subTest(invalid=invalid):
                self.policy_path.write_text(json.dumps({**allowed, "allow_quick_code": invalid}))
                with self.assertRaises(gate.ReviewError):
                    self.call("prepare")

    def test_quick_code_local_legacy_policy_withholds_permission(self):
        policy = {key: value for key, value in DEFAULT_POLICY.items() if key != "allow_quick_code"}
        config = self.root / ".codex"
        config.mkdir()
        (config / "review-policy.json").write_text(json.dumps(policy))
        self.assertFalse(gate.policy_for(self.root)["allow_quick_code"])
        with self.assertRaisesRegex(gate.ReviewError, "policy"):
            gate.start(self.root, self.state, quick_code_reason="Only a constant return value changes.")
        self.assertEqual(gate.start(self.root, self.state)["required_reviewers"], 3)

    def test_quick_code_cannot_be_declared_late_or_replace_its_reason(self):
        before = deepcopy(self.state)
        for reason in ("", "  ", 17, False, "a" * 1001):
            with self.subTest(reason=reason):
                with self.assertRaises(gate.ReviewError):
                    self.quick_code(reason)
                self.assertEqual(self.state, before)
        self.quick_code()
        with self.assertRaisesRegex(gate.ReviewError, "declaration"):
            self.quick_code("A different justification.")
        self.state = before
        self.start()
        with self.assertRaisesRegex(gate.ReviewError, "first"):
            self.quick_code()
        self.assertEqual(self.call("prepare")["mode"], "standard")

    def test_quick_code_never_lowers_semantic_or_active_risk_floor(self):
        self.state["review_risk"] = "standard"
        self.assertEqual(self.quick_code()["mode"], "standard")
        self.assertTrue(self.quick_code()["unchanged"])
        self.state["review_risk"] = "quick"
        self.assertEqual(self.call("prepare")["mode"], "standard")
        self.state["review_risk"] = "deep"
        self.assertEqual(self.start()["mode"], "deep")

    def test_quick_code_rejects_sensitive_artifacts_and_documentation(self):
        for name, mode in (("auth.py", "deep"), ("AGENTS.md", "deep"), ("guide.md", "quick")):
            with self.subTest(name=name):
                self.state["paths"] = [name]
                (self.root / name).write_text("content\n")
                with self.assertRaises(gate.ReviewError):
                    self.quick_code()
                self.assertEqual(self.call("prepare")["mode"], mode)
                self.assertNotIn("review_gate", self.state)
        self.state["review_risk"] = "standard"
        with self.assertRaises(gate.ReviewError):
            self.quick_code()

    def test_quick_code_declaration_is_bound_to_complete_review_snapshot(self):
        original = deepcopy(self.state)
        for mutation in ("content", "scope", "requirements", "author", "contributors", "policy", "context", "task", "repository"):
            with self.subTest(mutation=mutation):
                self.state = deepcopy(original)
                self.policy_path.write_text(json.dumps(DEFAULT_POLICY))
                (self.root / "tool.py").write_text("print('works')\n")
                self.quick_code()
                if mutation == "content":
                    (self.root / "tool.py").write_text("print('changed')\n")
                elif mutation == "scope":
                    (self.root / "other.py").write_text("pass\n")
                    self.state["paths"].append("other.py")
                elif mutation == "requirements":
                    self.state["requirements"].append("Another requirement")
                elif mutation == "author":
                    self.state["author"] = "another-author"
                elif mutation == "contributors":
                    self.state["review_authors"] = {"worker": ["tool.py"]}
                elif mutation == "policy":
                    policy = deepcopy(DEFAULT_POLICY)
                    policy["max_rounds"] = 2
                    self.policy_path.write_text(json.dumps(policy))
                elif mutation == "context":
                    self.state["review_context_sha256"] = "a" * 64
                elif mutation == "task":
                    self.state["started"] = "another-task"
                elif mutation == "repository":
                    other = self.base / "other"
                    other.mkdir(exist_ok=True)
                    (other / "tool.py").write_text("print('works')\n")
                    context = gate.prepare(other, self.state, policy_path=self.policy_path)
                    self.assertEqual(context["mode"], "standard")
                    continue
                self.assertEqual(self.call("prepare")["mode"], "standard")
                with self.assertRaises(gate.ReviewError):
                    self.quick_code()
                if mutation != "author":
                    self.assertEqual(self.start()["mode"], "standard")

    def test_quick_code_stale_round_cannot_replay_declaration_after_revert(self):
        original = (self.root / "tool.py").read_text()
        self.quick_code()
        (self.root / "tool.py").write_text("pass\n")
        self.assertEqual(self.start()["mode"], "standard")
        (self.root / "tool.py").write_text(original)
        self.assertEqual(self.call("prepare")["mode"], "standard")
        with self.assertRaises(gate.ReviewError):
            self.quick_code()

    def test_quick_code_scope_change_to_documentation_still_requires_standard(self):
        self.quick_code()
        (self.root / "guide.md").write_text("Replacement scope\n")
        self.state["paths"] = ["guide.md"]
        self.assertEqual(self.call("prepare")["mode"], "standard")
        self.assertEqual(self.start()["mode"], "standard")

    def test_quick_code_malformed_stored_declaration_fails_closed(self):
        self.quick_code()
        declaration = self.state["review_gate"]["quick_code_declaration"]
        for malformed in ({}, {**declaration, "reason": ""}, {**declaration, "snapshot_sha256": "bad"},
                          {**declaration, "unknown": True}):
            self.state["review_gate"]["quick_code_declaration"] = malformed
            with self.assertRaises(gate.ReviewError):
                self.call("prepare")

    def test_quick_code_cli_wrappers_forward_reason_and_preserve_risk(self):
        from ecosystem.runtime import workflow, workspace

        config = self.root / ".codex"
        config.mkdir()
        (config / "repositories.json").write_text(json.dumps({"schema_version": 1,
            "repositories": [{"path": ".", "management": "native"}]}))
        remote = self.base / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        for key, value in (("user.name", "Fixture"), ("user.email", "fixture@example.invalid"),
                           ("commit.gpgsign", "false"), ("core.hooksPath", str(self.root / ".git/hooks"))):
            workflow.git(self.root, "config", key, value)
        workflow.git(self.root, "add", "tool.py", ".codex/repositories.json")
        workflow.git(self.root, "commit", "-m", "Seed fixture")
        workflow.git(self.root, "remote", "add", "origin", str(remote))
        workflow.git(self.root, "push", "-u", "origin", "main")
        session = "fixture-adaptive-review"
        coordinator = workspace.Workspace(self.root, session)
        coordinator.plan({"requirements": ["The constant result is correct"], "paths": ["tool.py"]})
        (self.root / "tool.py").write_text("def answer(): return 42\n")
        prefix = ["--root", str(self.root), "--session", session]
        reason = "Only the constant return value changes; an independent reviewer checks that premise."
        output = io.StringIO()
        with patch("sys.stdout", output):
            workspace.main([*prefix, "review-start", "--repo", ".", "--quick-code-reason", reason])
        context = json.loads(output.getvalue())
        self.assertEqual(context["mode"], "quick")
        self.assertEqual(context["quick_code_reason"], reason)
        output = io.StringIO()
        with patch("sys.stdout", output):
            workflow.main([*prefix, "review-start", "--quick-code-reason", reason])
        self.assertTrue(json.loads(output.getvalue())["unchanged"])
        with patch("sys.stdout", io.StringIO()):
            workflow.main([*prefix, "review-start", "--risk", "deep"])
        self.assertEqual(coordinator.review_operation(".", "prepare")["mode"], "deep")
        with self.assertRaisesRegex(workflow.Blocked, "cannot be lowered"):
            workflow.main([*prefix, "review-start", "--risk", "quick"])

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

    def test_conflicting_finding_content_rejected_atomically(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        for field in ["scenario", "consequence", "evidence", "severity"]:
            with self.subTest(field=field):
                value = "critical" if field == "severity" else "A distinct defect in the same artifact."
                before = deepcopy(self.state)
                with self.assertRaisesRegex(gate.ReviewError, "conflicting semantic content"):
                    self.call("report", self.payload("reviewer-b", findings=[
                        self.finding("another-finding"), self.finding(**{field: value})]))
                self.assertEqual(self.state, before)

    def test_finding_line_moves_only_between_review_revisions(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        before = deepcopy(self.state)
        with self.assertRaisesRegex(gate.ReviewError, "line can move only"):
            self.call("report", self.payload("reviewer-b", findings=[self.finding(line=2)]))
        self.assertEqual(self.state, before)
        (self.root / "tool.py").write_text("# New preamble\nprint('works')\n")
        self.start()
        self.call("report", self.payload("reviewer-b", findings=[self.finding(line=2)]))
        finding = self.state["review_gate"]["findings"]["empty-input"]
        self.assertEqual(finding["line"], 2)
        self.assertEqual(finding["discoverers"], ["reviewer-a", "reviewer-b"])
        self.call("report", self.payload("reviewer-c", findings=[self.finding(line=2)]))
        before = deepcopy(self.state)
        with self.assertRaisesRegex(gate.ReviewError, "line can move only"):
            self.call("report", self.payload("reviewer-d", findings=[self.finding(line=3)]))
        self.assertEqual(self.state, before)

    def test_author_registration_is_cumulative_idempotent_and_revision_bound(self):
        self.state["paths"].append("other.py")
        (self.root / "other.py").write_text("pass\n")
        self.complete()
        old_token = self.call("prepare")["token"]
        ledger = deepcopy(self.state["review_gate"])
        self.state.update(review={"complete": True}, finished="done")
        result = self.call("author", {"author": "implementer", "paths": ["tool.py"]})
        self.assertFalse(result["unchanged"])
        self.assertIsNone(self.state["review"])
        self.assertIsNone(self.state["finished"])
        self.assertEqual(self.state["review_gate"], ledger)
        context = self.call("prepare")
        self.assertNotEqual(context["token"], old_token)
        self.assertEqual(context["requirements"], self.state["requirements"])
        self.assertEqual(context["author"], "author-session")
        self.assertEqual(context["review_authors"], {"implementer": ["tool.py"]})
        with self.assertRaisesRegex(gate.ReviewError, "stale"):
            self.call("validate")
        before = deepcopy(self.state)
        self.assertTrue(self.call("author", {"author": "implementer", "paths": ["tool.py"]})["unchanged"])
        self.assertEqual(self.state, before)
        self.call("author", {"author": "implementer", "paths": ["other.py"]})
        self.assertEqual(self.state["review_authors"], {"implementer": ["other.py", "tool.py"]})
        self.state["paths"] = ["other.py"]
        self.assertTrue(self.call("author", {"author": "implementer", "paths": ["other.py"]})["unchanged"])
        self.assertEqual(self.state["review_authors"], {"implementer": ["other.py", "tool.py"]})
        self.assertEqual(self.start()["round"], 2)

    def test_invalid_author_registration_is_atomic(self):
        self.start()
        for payload in [{"author": "", "paths": ["tool.py"]},
                        {"author": "implementer", "paths": []},
                        {"author": "implementer", "paths": ["tool.py", "tool.py"]},
                        {"author": "implementer", "paths": ["undeclared.py"]},
                        {"author": "implementer", "paths": ["tool.py"], "remove": True}]:
            with self.subTest(payload=payload):
                before = deepcopy(self.state)
                with self.assertRaises(gate.ReviewError):
                    self.call("author", payload)
                self.assertEqual(self.state, before)

    def test_contributing_author_can_review_only_disjoint_artifacts(self):
        self.state["paths"].append("other.py")
        (self.root / "other.py").write_text("pass\n")
        self.call("author", {"author": "implementer", "paths": ["tool.py"]})
        self.start()
        before = deepcopy(self.state)
        with self.assertRaisesRegex(gate.ReviewError, "artifacts they contributed"):
            self.call("report", self.payload("implementer"))
        self.assertEqual(self.state, before)
        self.call("report", self.payload("implementer", paths=["other.py"]))
        self.call("report", self.payload("reviewer-b", paths=["tool.py"]))
        self.call("validate")

    def test_later_fix_author_cannot_resolve_their_own_finding(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        self.call("author", {"author": "fixer", "paths": ["tool.py"]})
        self.assertEqual(self.start()["round"], 2)
        before = deepcopy(self.state)
        with self.assertRaisesRegex(gate.ReviewError, "cannot independently resolve"):
            self.call("resolve", self.resolution(verifier="fixer"))
        self.assertEqual(self.state, before)
        self.call("resolve", self.resolution())
        self.call("report", self.payload("independent-reviewer"))
        self.call("validate")

    def test_later_authorship_reopens_prior_self_resolution(self):
        self.start()
        self.call("report", self.payload(findings=[self.finding()]))
        self.call("resolve", self.resolution())
        self.call("author", {"author": "verifier-c", "paths": ["tool.py"]})
        self.start()
        self.call("report", self.payload("independent-reviewer"))
        with self.assertRaisesRegex(gate.ReviewError, "Unresolved"):
            self.call("validate")
        self.call("resolve", self.resolution(verifier="verifier-d"))
        self.call("validate")

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

    def test_project_path_validator_rejects_before_any_artifact_read(self):
        self.state["paths"].append("z_blocked.py")
        (self.root / "z_blocked.py").write_text("pass\n")
        calls = []

        def reject_blocked(root, name):
            calls.append((root, name))
            if name == "z_blocked.py":
                raise PermissionError("Project path denied")

        for name, args in [("prepare", ()), ("start", ()), ("author", ({},)),
                           ("report", ({},)), ("resolve", ({},)), ("validate", ())]:
            with self.subTest(operation=name):
                calls.clear()
                before = deepcopy(self.state)
                with patch.object(Path, "read_bytes", side_effect=AssertionError("must not read artifacts")):
                    with self.assertRaisesRegex(PermissionError, "Project path denied"):
                        getattr(gate, name)(self.root, self.state, *args,
                                            policy_path=self.policy_path, path_validator=reject_blocked)
                self.assertEqual(calls, [(self.root.resolve(), "tool.py"),
                                         (self.root.resolve(), "z_blocked.py")])
                self.assertEqual(self.state, before)

    def test_project_path_validator_return_value_does_not_replace_artifact(self):
        calls = []

        def accept_path(root, name):
            calls.append((root, name))
            return self.base / "outside-and-missing.py"

        expected = self.call("prepare")
        actual = gate.prepare(self.root, self.state, policy_path=self.policy_path,
                              path_validator=accept_path)
        self.assertEqual(actual, expected)
        self.assertEqual(calls, [(self.root.resolve(), "tool.py")])

    def test_permissive_project_validator_cannot_bypass_common_path_guards(self):
        secret = self.base / "private.txt"
        secret.write_text("local-only content")
        (self.root / "link.py").symlink_to(secret)
        (self.root / "dir").symlink_to(self.base, target_is_directory=True)

        def accept_path(root, name):
            return root / "tool.py"

        for name in ["link.py", "dir/private.txt", "../private.txt", ".env", "conversations/file.md"]:
            with self.subTest(name=name):
                self.state["paths"] = [name]
                before = deepcopy(self.state)
                with patch.object(Path, "read_bytes", side_effect=AssertionError("must not read contents")):
                    with self.assertRaises(gate.ReviewError):
                        gate.prepare(self.root, self.state, policy_path=self.policy_path,
                                     path_validator=accept_path)
                self.assertEqual(self.state, before)

    def test_policy_change_during_review_fails_closed(self):
        self.complete()
        policy = deepcopy(MINIMAL_POLICY)
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
        policy = deepcopy(MINIMAL_POLICY)
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
        lower_count = deepcopy(MINIMAL_POLICY)
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
        policy = deepcopy(MINIMAL_POLICY)
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

    def test_focus_quorum_applies_to_each_artifact(self):
        policy = deepcopy(MINIMAL_POLICY)
        policy["modes"]["standard"] = {"reviewers": 2, "focus": {"correctness": 2}}
        policy["modes"]["deep"]["focus"]["correctness"] = 2
        self.policy_path.write_text(json.dumps(policy))
        self.state["paths"].append("other.py")
        (self.root / "other.py").write_text("pass\n")
        self.start()
        self.call("report", self.payload(paths=["tool.py"]))
        self.call("report", self.payload("reviewer-b", paths=["other.py"]))
        with self.assertRaisesRegex(gate.ReviewError, "2 distinct reviewers per artifact"):
            self.call("validate")
        self.call("report", self.payload("reviewer-c", paths=["tool.py"]))
        with self.assertRaisesRegex(gate.ReviewError, "per artifact: other.py"):
            self.call("validate")
        self.call("report", self.payload("reviewer-d", paths=["other.py"]))
        self.call("validate")

    def test_shipped_policy_requires_three_correctness_reviews(self):
        self.policy_path.write_text(json.dumps(DEFAULT_POLICY))
        context = self.start()
        self.assertEqual(context["required_reviewers"], 3)
        self.assertEqual(context["required_focus"], {"correctness": 3})
        for reviewer in ["reviewer-a", "reviewer-b"]:
            self.call("report", self.payload(reviewer))
            with self.assertRaisesRegex(gate.ReviewError, "3 distinct reviewers"):
                self.call("validate")
        self.call("report", self.payload("reviewer-c"))
        self.call("validate")

    def test_shipped_deep_policy_requires_security_quorum_per_artifact(self):
        self.policy_path.write_text(json.dumps(DEFAULT_POLICY))
        self.state["review_risk"] = "deep"
        self.state["paths"].append("other.py")
        (self.root / "other.py").write_text("pass\n")
        context = self.start()
        self.assertEqual(context["required_reviewers"], 5)
        self.assertEqual(context["required_focus"], {"correctness": 3, "security": 2})
        for reviewer in ["reviewer-a", "reviewer-b", "reviewer-c"]:
            self.call("report", self.payload(reviewer))
        self.call("report", self.payload("security-a", focus=["security"], paths=["tool.py"]))
        self.call("report", self.payload("security-b", focus=["security"], paths=["other.py"]))
        with self.assertRaisesRegex(gate.ReviewError, "2 distinct reviewers per artifact"):
            self.call("validate")
        self.call("report", self.payload("security-c", focus=["security"]))
        self.call("validate")

    def test_shipped_deep_policy_counts_distinct_reviewers_per_artifact(self):
        self.policy_path.write_text(json.dumps(DEFAULT_POLICY))
        self.state["review_risk"] = "deep"
        self.state["paths"].append("other.py")
        (self.root / "other.py").write_text("pass\n")
        self.start()
        for reviewer in ["reviewer-a", "reviewer-b", "reviewer-c"]:
            self.call("report", self.payload(reviewer, focus=["correctness", "security"]))
        for reviewer in ["other-reviewer-d", "other-reviewer-e"]:
            self.call("report", self.payload(reviewer, paths=["other.py"]))
        with self.assertRaisesRegex(gate.ReviewError, "5 distinct reviewers per artifact: tool.py"):
            self.call("validate")
        for reviewer in ["tool-reviewer-d", "tool-reviewer-e"]:
            self.call("report", self.payload(reviewer, paths=["tool.py"]))
        self.call("validate")

    def test_non_git_directory_uses_bundled_policy_without_git_scaffolding(self):
        self.assertEqual(gate.policy_for(self.root), DEFAULT_POLICY)
        context = gate.prepare(self.root, self.state)
        self.assertTrue(context["enabled"])
        self.assertEqual(context["mode"], "standard")
        self.assertEqual(context["required_reviewers"], 3)
        self.assertFalse((self.root / ".git").exists())
        self.assertFalse((self.root / ".codex").exists())

    def test_standalone_git_repository_uses_bundled_policy_without_scaffolding(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.assertEqual(gate.policy_for(self.root), DEFAULT_POLICY)
        context = gate.start(self.root, self.state)
        self.assertTrue(context["enabled"])
        self.assertEqual(context["mode"], "standard")
        self.assertEqual(context["required_reviewers"], 3)
        with self.assertRaisesRegex(gate.ReviewError, "distinct reviewers"):
            gate.validate(self.root, self.state)
        for reviewer in ["reviewer-a", "reviewer-b", "reviewer-c"]:
            gate.report(self.root, self.state, {
                "token": context["token"], "reviewer": reviewer, "role": "reviewer",
                "focus": ["correctness"], "paths": ["tool.py"],
                "summary": "Checked the standalone implementation and its boundary behavior.",
                "evidence": "The declared artifact preserves the requested behavior.",
                "findings": [],
            })
        gate.validate(self.root, self.state)
        self.assertFalse((self.root / ".codex").exists())

    def test_standalone_local_policy_tightens_without_registry(self):
        config = self.root / ".codex"
        config.mkdir()
        strict = deepcopy(DEFAULT_POLICY)
        strict["max_rounds"] = 2
        strict["deep_patterns"].append("tool.py")
        (config / "review-policy.json").write_text(json.dumps(strict))
        for git_owner in (False, True):
            with self.subTest(git_owner=git_owner):
                if git_owner:
                    subprocess.run(["git", "init", "-q", str(self.root)], check=True)
                context = gate.prepare(self.root, self.state)
                self.assertEqual(context["mode"], "deep")
                self.assertEqual(context["max_rounds"], 2)
                self.assertFalse((config / "repositories.json").exists())

    def test_standalone_local_policy_cannot_weaken_packaged_minimums(self):
        config = self.root / ".codex"
        config.mkdir()
        weakened = deepcopy(MINIMAL_POLICY)
        weakened["max_rounds"] = 10
        weakened["documentation_extensions"].append(".py")
        (config / "review-policy.json").write_text(json.dumps(weakened))
        context = gate.prepare(self.root, self.state)
        self.assertEqual(context["mode"], "standard")
        self.assertEqual(context["required_reviewers"], 3)
        self.assertEqual(context["max_rounds"], 3)

    def test_standalone_rejects_invalid_or_linked_local_policy(self):
        config = self.root / ".codex"
        config.mkdir()
        local_policy = config / "review-policy.json"
        local_policy.write_text("{}")
        with self.subTest(policy="malformed"):
            with self.assertRaises(gate.ReviewError):
                gate.policy_for(self.root)
        local_policy.unlink()
        local_policy.symlink_to(self.base / "missing.json")
        with self.subTest(policy="symlink"):
            with self.assertRaisesRegex(gate.ReviewError, "regular local file"):
                gate.policy_for(self.root)

    def test_native_registration_requires_actual_owner_and_floors_workspace_override(self):
        config = self.root / ".codex"
        config.mkdir()
        (config / "repositories.json").write_text(json.dumps({"repositories": [{"path": ".", "management": "native"}]}))
        (config / "review-policy.json").write_text(json.dumps(MINIMAL_POLICY))
        with self.assertRaisesRegex(gate.ReviewError, "owner"):
            gate.policy_for(self.root)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.assertEqual(gate.policy_for(self.root)["modes"], DEFAULT_POLICY["modes"])
        (config / "review-policy.json").unlink()
        self.assertEqual(gate.policy_for(self.root), DEFAULT_POLICY)
        (config / "review-policy.json").write_text("{}")
        with self.assertRaises(gate.ReviewError):
            gate.policy_for(self.root)

    def test_registered_child_discovers_workspace_policy_from_its_root(self):
        config = self.root / ".codex"
        config.mkdir()
        (config / "repositories.json").write_text(json.dumps({"repositories": [{"path": "child", "management": "native"}]}))
        (config / "review-policy.json").write_text(json.dumps(MINIMAL_POLICY))
        child = self.root / "child"
        child.mkdir()
        subprocess.run(["git", "init", "-q", str(child)], check=True)
        self.assertEqual(gate.policy_for(child)["modes"], DEFAULT_POLICY["modes"])

    def test_external_and_unregistered_children_keep_their_own_policy(self):
        config = self.root / ".codex"
        config.mkdir()
        (config / "repositories.json").write_text(json.dumps({"repositories": [{"path": "external", "management": "external"}]}))
        (config / "review-policy.json").write_text(json.dumps(DEFAULT_POLICY))
        for name in ["external", "unregistered"]:
            with self.subTest(name=name):
                child = self.root / name
                child.mkdir()
                subprocess.run(["git", "init", "-q", str(child)], check=True)
                self.assertIsNone(gate.policy_for(child))
                self.assertEqual(gate.prepare(child, self.state), {"enabled": False})
                gate.validate(child, self.state)


class ReviewPolicyDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.hub = Path(self.temp.name)
        self.root = self.hub / "child"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "tool.py").write_text("pass\n")
        self.state = {"requirements": ["Change the declared artifact"], "paths": ["tool.py"],
                      "author": "author-session", "started": "task-start"}
        self.register(self.hub, [{"path": "child", "management": "native"}])

    def tearDown(self):
        self.temp.cleanup()

    def register(self, root, entries, policy=None):
        config = root / ".codex"
        config.mkdir(exist_ok=True)
        (config / "repositories.json").write_text(json.dumps({"repositories": entries}))
        if policy is not None:
            (config / "review-policy.json").write_text(json.dumps(policy))

    def test_nested_external_registry_cannot_disable_ancestor_native_review(self):
        self.register(self.root, [{"path": ".", "management": "external"}])
        self.assertTrue(gate.prepare(self.root, self.state)["enabled"])
        with self.assertRaisesRegex(gate.ReviewError, "Start an independent review"):
            gate.validate(self.root, self.state)
        context = gate.start(self.root, self.state)
        gate.report(self.root, self.state, {
            "token": context["token"], "reviewer": "reviewer-a", "role": "reviewer",
            "focus": ["correctness"], "paths": ["tool.py"],
            "summary": "Checked the artifact and boundary behavior.",
            "evidence": "The implementation satisfies the declared behavior.", "findings": [],
        })
        with self.assertRaisesRegex(gate.ReviewError, "3 distinct reviewers"):
            gate.validate(self.root, self.state)

    def test_nested_unregistered_registry_cannot_disable_ancestor_native_review(self):
        self.register(self.root, [])
        self.assertTrue(gate.prepare(self.root, self.state)["enabled"])
        with self.assertRaises(gate.ReviewError):
            gate.validate(self.root, self.state)

    def test_implicit_policy_cannot_reduce_packaged_quorums_or_raise_round_limit(self):
        weakened = deepcopy(MINIMAL_POLICY)
        weakened["max_rounds"] = 10
        self.register(self.hub, [{"path": "child", "management": "native"}], weakened)
        context = gate.prepare(self.root, self.state)
        self.assertEqual(context["required_reviewers"], 3)
        self.assertEqual(context["required_focus"], {"correctness": 3})
        self.assertEqual(context["max_rounds"], 3)
        self.state["review_risk"] = "deep"
        context = gate.prepare(self.root, self.state)
        self.assertEqual(context["required_reviewers"], 5)
        self.assertEqual(context["required_focus"], {"correctness": 3, "security": 2})

    def test_implicit_policy_cannot_reclassify_code_as_documentation(self):
        weakened = deepcopy(DEFAULT_POLICY)
        weakened["documentation_extensions"].append(".py")
        weakened["documentation_names"].append("tool.py")
        self.register(self.hub, [{"path": "child", "management": "native"}], weakened)
        self.assertEqual(gate.prepare(self.root, self.state)["mode"], "standard")

    def test_implicit_policy_cannot_remove_packaged_sensitive_paths(self):
        weakened = deepcopy(DEFAULT_POLICY)
        weakened["deep_patterns"] = ["custom-sensitive/**"]
        self.register(self.hub, [{"path": "child", "management": "native"}], weakened)
        self.state["paths"] = ["auth.py"]
        (self.root / "auth.py").write_text("pass\n")
        self.assertEqual(gate.prepare(self.root, self.state)["mode"], "deep")

    def test_nested_native_registry_retains_stricter_ancestor_policy(self):
        strict = deepcopy(DEFAULT_POLICY)
        strict["max_rounds"] = 2
        strict["modes"]["quick"] = {"reviewers": 2, "focus": {"correctness": 2}}
        strict["modes"]["standard"] = {"reviewers": 4, "focus": {"correctness": 4}}
        strict["modes"]["deep"] = {"reviewers": 6, "focus": {"correctness": 4, "security": 2}}
        strict["documentation_extensions"].remove(".txt")
        strict["deep_patterns"].append("sensitive.py")
        self.register(self.hub, [{"path": "child", "management": "native"}], strict)
        self.register(self.root, [{"path": ".", "management": "native"}], MINIMAL_POLICY)
        context = gate.prepare(self.root, self.state)
        self.assertEqual(context["required_reviewers"], 4)
        self.assertEqual(context["required_focus"], {"correctness": 4})
        self.assertEqual(context["max_rounds"], 2)
        for name, mode, reviewers in [("guide.md", "quick", 2), ("guide.txt", "standard", 4),
                                      ("sensitive.py", "deep", 6)]:
            with self.subTest(name=name):
                (self.root / name).write_text("Content\n")
                self.state["paths"] = [name]
                context = gate.prepare(self.root, self.state)
                self.assertEqual(context["mode"], mode)
                self.assertEqual(context["required_reviewers"], reviewers)

    def test_native_registry_does_not_hide_invalid_ancestor_registry(self):
        self.register(self.root, [{"path": ".", "management": "native"}])
        (self.hub / ".codex/repositories.json").write_text("{}")
        with self.assertRaisesRegex(gate.ReviewError, "registry"):
            gate.policy_for(self.root)

    def test_external_child_can_explicitly_adopt_its_own_native_policy(self):
        self.register(self.hub, [{"path": "child", "management": "external"}])
        strict = deepcopy(DEFAULT_POLICY)
        strict["max_rounds"] = 2
        self.register(self.root, [{"path": ".", "management": "native"}], strict)
        context = gate.prepare(self.root, self.state)
        self.assertTrue(context["enabled"])
        self.assertEqual(context["required_reviewers"], 3)
        self.assertEqual(context["max_rounds"], 2)

    def test_unrelated_nested_workspace_policy_does_not_apply_to_owner(self):
        intermediate = self.hub / "intermediate"
        intermediate.mkdir()
        nested = intermediate / "child"
        self.root.rename(nested)
        self.root = nested
        self.register(self.hub, [{"path": "intermediate/child", "management": "native"}])
        self.register(intermediate, [])
        (intermediate / ".codex/review-policy.json").write_text("{}")
        context = gate.prepare(self.root, self.state)
        self.assertTrue(context["enabled"])
        self.assertEqual(context["required_reviewers"], 3)

    def test_registered_child_policy_can_tighten_without_own_registry(self):
        config = self.root / ".codex"
        config.mkdir()
        strict = deepcopy(DEFAULT_POLICY)
        strict["max_rounds"] = 2
        strict["deep_patterns"].append("tool.py")
        (config / "review-policy.json").write_text(json.dumps(strict))
        context = gate.prepare(self.root, self.state)
        self.assertEqual(context["mode"], "deep")
        self.assertEqual(context["max_rounds"], 2)
        self.assertFalse((config / "repositories.json").exists())

    def test_ancestor_policy_does_not_apply_to_nonmatching_native_owner(self):
        strict = deepcopy(DEFAULT_POLICY)
        strict["max_rounds"] = 1
        self.register(self.hub, [{"path": "other", "management": "native"}], strict)
        self.register(self.root, [{"path": ".", "management": "native"}])
        self.assertEqual(gate.prepare(self.root, self.state)["max_rounds"], 3)

    def test_shadowed_native_registration_still_requires_exact_git_root(self):
        nested = self.root / "nested"
        nested.mkdir()
        self.register(self.hub, [{"path": "child/nested", "management": "native"}])
        self.register(nested, [{"path": ".", "management": "external"}])
        with self.assertRaisesRegex(gate.ReviewError, "actual Git repository root"):
            gate.policy_for(nested)

    def test_registered_child_rejects_invalid_or_linked_local_policy(self):
        config = self.root / ".codex"
        config.mkdir()
        local_policy = config / "review-policy.json"
        local_policy.write_text("{}")
        with self.assertRaises(gate.ReviewError):
            gate.policy_for(self.root)
        local_policy.unlink()
        local_policy.symlink_to(self.hub / "missing.json")
        with self.assertRaisesRegex(gate.ReviewError, "regular local file"):
            gate.policy_for(self.root)

    def test_local_policy_does_not_enroll_external_or_unregistered_owner(self):
        self.register(self.hub, [{"path": "child", "management": "external"}])
        config = self.root / ".codex"
        config.mkdir()
        (config / "review-policy.json").write_text("{}")
        self.assertIsNone(gate.policy_for(self.root))
        self.register(self.hub, [])
        self.assertIsNone(gate.policy_for(self.root))

    def test_explicit_policy_injection_retains_embedded_engine_contract(self):
        injected = self.hub / "explicit-policy.json"
        injected.write_text(json.dumps(MINIMAL_POLICY))
        context = gate.prepare(self.root, self.state, policy_path=injected)
        self.assertEqual(context["required_reviewers"], 1)
        self.assertEqual(context["required_focus"], {"correctness": 1})


if __name__ == "__main__":
    unittest.main()
