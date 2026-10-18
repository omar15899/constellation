"""Exercise real Git boundaries against disposable local bare remotes."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "workflow.py"
RUNTIME = MODULE.parent / "ecosystem/runtime"
sys.path.insert(0, str(MODULE.parent))
from ecosystem.runtime import workflow as w


def copy_runtime(destination: Path) -> None:
    """Install the compatibility entry point and its single implementation."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MODULE, destination)
    shutil.copytree(RUNTIME.parent, destination.parent / "ecosystem", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))


def native_hook_command(event: str, runtime: Path) -> list[str]:
    """Exercise legacy payload handling, independently of native hook loading."""
    events = {"UserPromptSubmit": "prompt", "PreToolUse": "pre-tool",
              "SubagentStart": "subagent-start", "Stop": "stop"}
    return [sys.executable, str(runtime), "hook", events[event]]


class GitFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {"CODEX_HOME": str(self.base / "codex-home")})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.remote = self.base / "remote.git"
        self.root = self.base / "vault"
        self.other = self.base / "other"
        # Publication tests isolate Git controls from the independently tested
        # review policy. These recipients deliberately retain external policy.
        registry = self.base / ".codex/repositories.json"
        registry.parent.mkdir()
        registry.write_text(json.dumps({"schema_version": 1, "repositories": [
            {"path": name, "management": "external"} for name in ("vault", "other")]}))
        subprocess.run(["git", "init", "--bare", "-q", str(self.remote)], check=True)
        subprocess.run(["git", "clone", "-q", str(self.remote), str(self.root)], check=True, capture_output=True)
        for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                           ("core.hooksPath", str(self.root / ".git/hooks")), ("commit.gpgsign", "false")):
            w.git(self.root, "config", key, value)
        w.git(self.root, "checkout", "-b", "main")
        (self.root / "README.md").write_text("seed\n")
        self.commit("seed")
        w.git(self.root, "push", "-u", "origin", "main")
        subprocess.run(["git", "clone", "-q", "-b", "main", str(self.remote), str(self.other)], check=True)
        for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid"), ("commit.gpgsign", "false")):
            w.git(self.other, "config", key, value)
        self.flow = w.Workflow(self.root, "test-session")

    def tearDown(self):
        self.temp.cleanup()

    def commit(self, message, root=None):
        root = root or self.root
        w.git(root, "add", "--all")
        w.git(root, "commit", "-m", message)

    def advance_remote(self):
        (self.other / "remote.md").write_text("new cloud data\n")
        self.commit("remote change", self.other)
        w.git(self.other, "push")

    def task(self, path="answer.md"):
        self.flow.begin("t1")
        self.flow.plan({"requirements": ["answer is present"], "paths": [path]})
        (self.root / path).write_text("answer\n")
        self.flow.review({"answer is present": f"Read {path}: contains the requested answer."})

    def test_clean_remote_ahead_fast_forwards(self):
        self.advance_remote()
        result = w.sync(self.root)
        self.assertEqual(result["behind"], 0)
        self.assertEqual((self.root / "remote.md").read_text(), "new cloud data\n")

    def test_dirty_tree_blocks_pull_without_touching_work(self):
        self.advance_remote()
        (self.root / "README.md").write_text("user work\n")
        with self.assertRaisesRegex(w.Blocked, "dirty"):
            w.sync(self.root)
        self.assertEqual((self.root / "README.md").read_text(), "user work\n")
        self.assertFalse((self.root / "remote.md").exists())

    def test_divergence_does_not_rebase(self):
        self.advance_remote()
        (self.root / "local.md").write_text("local\n")
        self.commit("local")
        head = w.git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(w.Blocked, "diverged"):
            w.sync(self.root)
        self.assertEqual(w.git(self.root, "rev-parse", "HEAD"), head)

    def test_fetch_failure_prevents_write_plan(self):
        w.git(self.root, "remote", "set-url", "origin", str(self.base / "missing"))
        state = self.flow.begin("offline")
        self.assertIn("sync_error", state)
        with self.assertRaises(w.Blocked):
            self.flow.plan({"requirements": ["write"], "paths": ["answer.md"]})

    def test_existing_dirty_file_requires_owned_change_explanation(self):
        (self.root / "README.md").write_text("user work\n")
        self.flow.begin("dirty")
        with self.assertRaisesRegex(w.Blocked, "adopt_existing"):
            self.flow.plan({"requirements": ["edit"], "paths": ["README.md"]})

    def test_review_invalidates_when_artifact_changes(self):
        self.task()
        (self.root / "answer.md").write_text("changed after review\n")
        with self.assertRaisesRegex(w.Blocked, "stale review"):
            self.flow.commit(["answer.md"], "Add answer")

    def test_all_requirements_need_evidence(self):
        self.flow.begin("t1")
        self.flow.plan({"requirements": ["a", "b"], "paths": []})
        with self.assertRaisesRegex(w.Blocked, "every requirement"):
            self.flow.review({"a": "done"})

    def test_code_needs_passing_check_for_current_version(self):
        self.flow.begin("t1")
        self.flow.plan({"requirements": ["works"], "paths": ["tool.py"]})
        (self.root / "tool.py").write_text("print('works')\n")
        with self.assertRaisesRegex(w.Blocked, "passing check"):
            self.flow.review({"works": "executed"})
        import sys
        with patch("sys.stdout", new=io.StringIO()):
            self.flow.check([sys.executable, "tool.py"])
        self.flow.review({"works": "The command printed works and exited zero."})
        (self.root / "tool.py").write_text("print('changed')\n")
        with self.assertRaisesRegex(w.Blocked, "passing check"):
            self.flow.review({"works": "old evidence"})

    def test_configuration_and_javascript_require_checks(self):
        for name in ("settings.toml", "app.ts", "schema.sql"):
            with self.subTest(path=name):
                self.flow.begin("config")
                self.flow.plan({"requirements": ["works"], "paths": [name]})
                (self.root / name).write_text("fixture\n")
                with self.assertRaisesRegex(w.Blocked, "passing check"):
                    self.flow.review({"works": "Read the configuration."})

    def test_later_check_failure_supersedes_success_on_identical_artifacts(self):
        import sys
        self.flow.begin("checks")
        self.flow.plan({"requirements": ["works"], "paths": ["app.py"]})
        (self.root / "app.py").write_text("pass\n")
        flag = self.base / "flag"
        command = [sys.executable, "-c", "import pathlib,sys;sys.exit(pathlib.Path(sys.argv[1]).exists())", str(flag)]
        with patch("sys.stdout", new=io.StringIO()):
            self.flow.check(command)
            flag.touch()
            with self.assertRaisesRegex(w.Blocked, "Check failed"):
                self.flow.check(command)
            with self.assertRaisesRegex(w.Blocked, "still failing"):
                self.flow.review({"works": "Old success must not count."})
            flag.unlink()
            self.flow.check(command)
        self.flow.review({"works": "The same check now passes."})

    def test_unlaunchable_check_is_recorded_as_failure(self):
        self.flow.begin("launch")
        self.flow.plan({"requirements": ["works"], "paths": ["app.py"]})
        (self.root / "app.py").write_text("pass\n")
        with patch("sys.stderr", new=io.StringIO()):
            with self.assertRaisesRegex(w.Blocked, "Check failed"):
                self.flow.check([str(self.base / "missing-executable")])
        self.assertEqual(self.flow.load()["checks"][-1]["exit_code"], -1)

    def test_check_timeout_is_bounded_and_recorded(self):
        self.flow.begin("bounded checks")
        self.flow.plan({"requirements": ["works"], "paths": []})
        for timeout in (0, 3601, True):
            with self.assertRaisesRegex(w.Blocked, "timeout must"):
                self.flow.check(["git", "diff", "--check"], timeout=timeout)
        with patch("sys.stdout", new=io.StringIO()):
            record = self.flow.check(["git", "diff", "--check"], timeout=10)
        self.assertEqual(record["timeout_seconds"], 10)

    def test_non_utf8_failure_cannot_reuse_previous_success(self):
        import sys
        self.flow.begin("binary output")
        self.flow.plan({"requirements": ["works"], "paths": ["app.py"]})
        (self.root / "app.py").write_text("pass\n")
        flag = self.base / "binary-failure"
        command = [sys.executable, "-c",
                   "import pathlib,sys; fail=pathlib.Path(sys.argv[1]).exists(); "
                   "sys.stdout.buffer.write(bytes([255]) if fail else b'ok'); sys.exit(int(fail))", str(flag)]
        with patch("sys.stdout", new=io.StringIO()):
            self.flow.check(command)
            self.flow.review({"works": "The check passed."})
            flag.touch()
            with self.assertRaisesRegex(w.Blocked, "Check failed"):
                self.flow.check(command)
        state = self.flow.load()
        self.assertIsNone(state["review"])
        self.assertEqual(state["checks"][-1]["exit_code"], 1)
        self.assertEqual(state["checks"][-1]["output_sha256"], w.digest(bytes([255])))
        with self.assertRaisesRegex(w.Blocked, "still failing"):
            self.flow.review({"works": "Old success is not valid."})

    def test_unsafe_artifact_after_check_cannot_revive_previous_success(self):
        import sys
        self.flow.begin("unsafe output")
        self.flow.plan({"requirements": ["works"], "paths": ["app.py"]})
        path = self.root / "app.py"
        path.write_text("pass\n")
        flag = self.base / "unsafe-failure"
        command = [sys.executable, "-c",
                   "import pathlib,sys; p=pathlib.Path('app.py'); fail=pathlib.Path(sys.argv[1]).exists(); "
                   "p.unlink() if fail else None; p.symlink_to(sys.argv[1]) if fail else None; sys.exit(int(fail))",
                   str(flag)]
        with patch("sys.stdout", new=io.StringIO()):
            self.flow.check(command)
            self.flow.review({"works": "Check passed."})
            flag.touch()
            with self.assertRaisesRegex(w.Blocked, "Check failed"):
                self.flow.check(command)
        path.unlink()
        path.write_text("pass\n")
        self.assertTrue(self.flow.load()["checks"][-1]["changed_during_check"])
        with self.assertRaisesRegex(w.Blocked, "still failing"):
            self.flow.review({"works": "Restored bytes do not revive a failed run."})

    def test_snapshot_executable_mode_matches_git_owner_bit(self):
        self.flow.begin("git modes")
        self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        path = self.root / "answer.md"
        path.write_text("answer\n")
        for mode in (0o654, 0o744):
            path.chmod(mode)
            w.git(self.root, "add", "answer.md")
            self.assertEqual(w.snapshot(self.root, ["answer.md"]), w.stored_snapshot(self.root, ["answer.md"]))

    def test_permission_change_invalidates_review(self):
        self.task()
        (self.root / "answer.md").chmod(0o755)
        with self.assertRaisesRegex(w.Blocked, "stale review"):
            self.flow.commit(["answer.md"], "Change reviewed permissions")

    def test_independent_gate_blocks_review_and_publication(self):
        engine = w.review_engine()
        self.flow.begin("independent")
        self.flow.plan({"requirements": ["answer is present"], "paths": ["answer.md"]})
        (self.root / "answer.md").write_text("answer\n")
        with patch.object(engine, "validate", side_effect=engine.ReviewError("Open independent finding")):
            with self.assertRaisesRegex(w.Blocked, "Open independent"):
                self.flow.review({"answer is present": "Read it."})
        self.flow.review({"answer is present": "Read it."})
        head = w.git(self.root, "rev-parse", "HEAD")
        with patch.object(engine, "validate", side_effect=engine.ReviewError("Stale independent review")):
            with self.assertRaisesRegex(w.Blocked, "Stale independent"):
                self.flow.commit(["answer.md"], "Add answer")
        self.assertEqual(w.git(self.root, "rev-parse", "HEAD"), head)

    def test_primary_session_cannot_review_or_verify_its_own_task(self):
        engine = w.review_engine()
        policy = json.loads((RUNTIME / "review-policy.json").read_text())
        self.flow.begin("identities")
        self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        (self.root / "answer.md").write_text("answer\n")
        with patch.object(engine, "policy_for", return_value=policy):
            context = self.flow.review_operation("start")
            report = {"token": context["token"], "reviewer": "test-session", "role": "reviewer",
                      "focus": ["correctness"], "paths": ["answer.md"],
                      "summary": "0 findings", "evidence": "Inspected the declared answer.", "findings": []}
            self.assertEqual(self.flow.load()["author"], "test-session")
            with self.assertRaisesRegex(w.Blocked, "differ.*author"):
                self.flow.review_operation("report", report)
            report["reviewer"] = "independent-reviewer"
            report["findings"] = [{"id": "answer-defect", "path": "answer.md", "line": 1,
                                   "severity": "medium", "origin": "introduced", "scenario": "Empty answer.",
                                   "consequence": "Missing requested content.", "evidence": "Inspected first line."}]
            self.flow.review_operation("report", report)
            with self.assertRaisesRegex(w.Blocked, "distinct.*author"):
                self.flow.review_operation("resolve", {"token": context["token"], "id": "answer-defect",
                                                       "verifier": "test-session", "disposition": "dismissed",
                                                       "evidence": "The author cannot verify this."})

    def test_review_author_cli_forwards_payload_and_invalidates_review(self):
        self.task()
        state = self.flow.load()
        state["finished"] = {"head": w.git(self.root, "rev-parse", "HEAD")}
        self.flow.save(state)
        engine = w.review_engine()
        policy = json.loads((RUNTIME / "review-policy.json").read_text())
        payload = {"author": "native-worker-id", "paths": ["answer.md"]}
        argv = [str(MODULE), "--root", str(self.root), "--session", "test-session", "review-author"]
        with patch.object(engine, "author", wraps=engine.author) as register, \
                patch.object(engine, "policy_for", return_value=policy), \
                patch("sys.argv", argv), patch("sys.stdin", io.StringIO(json.dumps(payload))), \
                patch("sys.stdout", new=io.StringIO()) as output:
            self.assertEqual(w.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), {"registered": "native-worker-id",
                                                       "paths": ["answer.md"], "unchanged": False})
        self.assertEqual(register.call_args.args[0], self.root.resolve())
        self.assertEqual(register.call_args.args[2], payload)
        self.assertIsNone(self.flow.load()["review"])
        self.assertIsNone(self.flow.load()["finished"])

    def test_review_author_rejection_preserves_existing_contract(self):
        self.task()
        before = self.flow.path.read_bytes()
        engine = w.review_engine()
        with patch.object(engine, "author", side_effect=engine.ReviewError("Undeclared author path"), create=True):
            with self.assertRaisesRegex(w.Blocked, "Undeclared author path"):
                self.flow.review_operation("author", {"author": "worker", "paths": ["other.md"]})
        self.assertEqual(self.flow.path.read_bytes(), before)

    def test_review_budget_cli_preserves_evidence_and_replan_preserves_budget(self):
        engine = w.review_engine()
        policy = json.loads((RUNTIME / "review-policy.json").read_text())
        self.flow.begin("adaptive budget")
        spec = {"requirements": ["answer is present"], "paths": ["answer.md"]}
        self.flow.plan(spec)
        (self.root / "answer.md").write_text("answer\n")
        with patch.object(engine, "policy_for", return_value=policy):
            context = self.flow.review_operation("start")
            self.assertEqual(context["budget"], {"revision": 0, "deadline_at": None, "status": "unknown"})
            self.flow.review_operation("report", {
                "token": context["token"], "reviewer": "independent-reviewer", "role": "reviewer",
                "focus": ["correctness"], "paths": ["answer.md"], "summary": "Answer satisfies its requirement.",
                "evidence": "Read the declared file and checked its content.", "findings": [],
            })
            self.flow.review({"answer is present": "Read the declared answer."})
            state = self.flow.load()
            state["finished"] = {"head": w.git(self.root, "rev-parse", "HEAD")}
            self.flow.save(state)
            before = self.flow.load()
            payload = {"expected_budget_revision": 0, "deadline_at": "9999-01-01T00:00:00Z",
                       "reason": "Continue the bounded independent review."}
            argv = ["--root", str(self.root), "--session", "test-session", "review-budget"]
            with patch("sys.stdin", io.StringIO(json.dumps(payload))), patch("sys.stdout", new=io.StringIO()) as output:
                self.assertEqual(w.main(argv), 0)
            self.assertEqual(json.loads(output.getvalue())["budget"]["revision"], 1)
            updated = self.flow.load()
            budget = updated.pop("review_budget")
            self.assertEqual(updated, before)
            self.assertEqual(self.flow.review_operation("prepare")["token"], context["token"])
            self.flow.independent_reviewed(self.flow.load())
            replanned = self.flow.plan(spec)
            self.assertEqual(replanned["review_budget"], budget)
            self.assertEqual(replanned["review_gate"], before["review_gate"])

    def test_review_budget_rejects_stale_or_malformed_updates_without_saving(self):
        engine = w.review_engine()
        policy = json.loads((RUNTIME / "review-policy.json").read_text())
        self.task()
        payload = {"expected_budget_revision": 0, "deadline_at": "9999-01-01T00:00:00Z",
                   "reason": "Declare the available review time."}
        with patch.object(engine, "policy_for", return_value=policy):
            self.flow.review_operation("budget", payload)
            before = self.flow.path.read_bytes()
            self.assertTrue(self.flow.review_operation("budget", payload)["unchanged"])
            self.assertEqual(self.flow.path.read_bytes(), before)
            for invalid in ({**payload, "reason": "A competing update with stale revision."},
                            {**payload, "expected_budget_revision": True},
                            {**payload, "expected_budget_revision": 1, "deadline_at": None},
                            {**payload, "expected_budget_revision": 1, "extra": "ignored?"}, []):
                with self.subTest(payload=invalid), self.assertRaises(w.Blocked):
                    self.flow.review_operation("budget", invalid)
                self.assertEqual(self.flow.path.read_bytes(), before)

    def test_review_budget_requires_coordinator_and_does_not_reassign_frozen_author(self):
        self.task()
        state = self.flow.load()
        state["author"] = "another-coordinator"
        self.flow.save(state)
        before = self.flow.path.read_bytes()
        with self.assertRaisesRegex(w.Blocked, "frozen coordinator"):
            self.flow.review_operation("budget", {"expected_budget_revision": 0,
                "deadline_at": "9999-01-01T00:00:00Z", "reason": "A worker cannot choose the budget."})
        self.assertEqual(self.flow.path.read_bytes(), before)
        frozen = {"author": self.flow.key, "review_budget": {"revision": 1}}
        self.flow.identify_author(frozen)
        self.assertEqual(frozen["author"], self.flow.key)

    def test_review_start_cli_forwards_continuation_and_rejects_partial_pair(self):
        self.task()
        engine = w.review_engine()
        argv = ["--root", str(self.root), "--session", "test-session", "review-start"]
        with patch.object(engine, "start", return_value={"token": "reviewed-version"}) as start, \
                patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(w.main(argv + ["--continuation-reason", "Resolve the remaining finding.",
                                           "--continuation-next-action", "Inspect the corrected failure case."]), 0)
        self.assertEqual(start.call_args.kwargs["continuation"], {
            "reason": "Resolve the remaining finding.", "next_action": "Inspect the corrected failure case."})
        before = self.flow.path.read_bytes()
        for flag in ("--continuation-reason", "--continuation-next-action"):
            with self.subTest(flag=flag), patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit) as exc:
                w.main(argv + [flag, "Incomplete continuation"])
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual(self.flow.path.read_bytes(), before)

    def test_review_retries_after_deadline_preserve_evidence_and_completion(self):
        engine = w.review_engine()
        policy = json.loads((RUNTIME / "review-policy.json").read_text())
        self.flow.begin("review retry")
        self.flow.plan({"requirements": ["answer is present"], "paths": ["answer.md"]})
        (self.root / "answer.md").write_text("answer\n")
        author = {"author": "native-worker", "paths": ["answer.md"]}
        with patch.object(engine, "policy_for", return_value=policy):
            self.flow.review_operation("author", author)
            context = self.flow.review_operation("start")
            report = {"token": context["token"], "reviewer": "independent-reviewer", "role": "reviewer",
                      "focus": ["correctness"], "paths": ["answer.md"], "summary": "Check the answer's content.",
                      "evidence": "Read the complete declared file.", "findings": [{
                          "id": "answer-content", "path": "answer.md", "line": 1, "severity": "medium",
                          "origin": "introduced", "scenario": "A reader could interpret the answer as missing.",
                          "consequence": "The requested content would be absent.",
                          "evidence": "Inspect the exact first line against the requirement."}]}
            self.flow.review_operation("report", report)
            resolution = {"token": context["token"], "id": "answer-content", "verifier": "independent-verifier",
                          "disposition": "dismissed", "evidence": "The declared answer is present on the first line."}
            self.flow.review_operation("resolve", resolution)
            self.flow.review({"answer is present": "Read the answer and its independent verification."})
            state = self.flow.load()
            state["finished"] = {"head": w.git(self.root, "rev-parse", "HEAD")}
            self.flow.save(state)
            self.flow.review_operation("budget", {"expected_budget_revision": 0,
                "deadline_at": "2000-01-01T00:00:00Z", "reason": "The review time has ended."})
            before = self.flow.path.read_bytes()
            for operation, payload in (("start", None), ("report", report), ("resolve", resolution), ("author", author)):
                with self.subTest(operation=operation):
                    self.assertTrue(self.flow.review_operation(operation, payload)["unchanged"])
                    self.assertEqual(self.flow.path.read_bytes(), before)
            self.flow.independent_reviewed(self.flow.load())

    def test_unrelated_staged_work_is_preserved(self):
        self.task()
        (self.root / "other.md").write_text("not ours\n")
        w.git(self.root, "add", "other.md")
        with self.assertRaisesRegex(w.Blocked, "Index already"):
            self.flow.commit(["answer.md"], "Add answer")
        self.assertEqual(w.git(self.root, "diff", "--cached", "--name-only"), "other.md")

    def test_commit_push_verify_and_stop(self):
        self.task()
        result = self.flow.commit(["answer.md"], "Add answer")
        self.assertEqual(result["head"], w.git(self.root, "rev-parse", "origin/main"))
        self.assertTrue(self.flow.finish()["completed"])
        self.assertEqual(self.flow.stop(), {})

    def test_push_rejection_is_not_completion(self):
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        self.task()
        with self.assertRaises(w.Blocked):
            self.flow.commit(["answer.md"], "Add answer")
        self.assertEqual(len(self.flow.load()["commits"]), 1)
        self.assertEqual(self.flow.stop()["decision"], "block")
        self.assertIsNone(self.flow.load().get("finished"))

    def test_remote_change_during_finish_invalidates_review(self):
        self.task()
        self.flow.commit(["answer.md"], "Add answer")
        w.git(self.other, "pull", "--ff-only")
        (self.other / "answer.md").write_text("different answer from remote\n")
        self.commit("change answer remotely", self.other)
        w.git(self.other, "push")
        with self.assertRaisesRegex(w.Blocked, "stale review"):
            self.flow.finish()
        self.assertIsNone(self.flow.load().get("finished"))

    def test_failed_finish_invalidates_prior_completion(self):
        self.task()
        self.flow.commit(["answer.md"], "Add answer")
        self.flow.finish()
        w.git(self.root, "remote", "set-url", "origin", str(self.base / "missing"))
        with self.assertRaises(w.Blocked):
            self.flow.finish()
        self.assertEqual(self.flow.stop()["decision"], "block")

    def test_new_remote_does_not_inherit_another_remotes_privacy_authorization(self):
        path = self.root / "09_Data_Sources/Codex_Conversations/rendered/fixture.md"
        path.parent.mkdir(parents=True)
        path.write_text("synthetic private fixture\n")
        self.commit("accidental fixture")
        w.git(self.root, "update-ref", "refs/remotes/another/main", "HEAD")
        with self.assertRaisesRegex(w.Blocked, "private data"):
            w.outgoing_gate(self.root, "HEAD", "0" * 40)

    def test_unscoped_file_blocks_finish(self):
        self.task()
        self.flow.commit(["answer.md"], "Add answer")
        (self.root / "forgotten.md").write_text("part of task?\n")
        with self.assertRaisesRegex(w.Blocked, "scope review"):
            self.flow.finish()

    def test_unscoped_file_after_finish_blocks_native_stop(self):
        self.task()
        self.flow.commit(["answer.md"], "Add answer")
        self.flow.finish()
        (self.root / "forgotten.md").write_text("created after finish\n")
        result = self.flow.stop()
        self.assertEqual(result["decision"], "block")
        self.assertIn("scope review", result["reason"])

    def test_file_created_during_publication_blocks_finish(self):
        self.task()
        self.flow.commit(["answer.md"], "Add answer")
        publish = self.flow.publish

        def concurrent_publish():
            result = publish()
            (self.root / "late.md").write_text("concurrent write\n")
            return result

        with patch.object(self.flow, "publish", side_effect=concurrent_publish):
            with self.assertRaisesRegex(w.Blocked, "scope review"):
                self.flow.finish()
        self.assertIsNone(self.flow.load().get("finished"))

    def test_symlink_replacement_invalidates_review_before_reading(self):
        self.task()
        (self.base / "private.md").write_text("synthetic private fixture\n")
        (self.root / "answer.md").unlink()
        (self.root / "answer.md").symlink_to(self.base / "private.md")
        with self.assertRaisesRegex(w.Blocked, "Private or external"):
            self.flow.reviewed(self.flow.load())

    def native_hook(self, event, payload, cwd=None):
        """Execute the compatibility entry point using a disposable runtime."""
        runtime = self.root / ".codex/workflow.py"
        runtime.parent.mkdir(exist_ok=True)
        copy_runtime(runtime)
        (runtime.parent / "profile.json").write_text('{"mode":"native"}\n')
        payload = {"hook_event_name": event, "turn_id": "fixture-turn",
                   "session_id": "test-session", "cwd": str(cwd or self.root), **payload}
        return subprocess.run(native_hook_command(event, runtime), cwd=cwd or self.root,
                              input=json.dumps(payload), capture_output=True,
                              text=True, timeout=15)

    def test_prompt_does_not_start_or_synchronize_a_task_from_subfolder(self):
        self.advance_remote()
        before = w.git(self.root, "rev-parse", "HEAD")
        runtime = self.root / ".codex/workflow.py"
        runtime.parent.mkdir()
        copy_runtime(runtime)
        w.git(self.root, "config", "--add", "core.excludesFile", str(self.base / "ignore"))
        (self.base / "ignore").write_text(".codex/\n")
        payload = {"session_id": "native", "turn_id": "one", "cwd": str(runtime.parent),
                   "prompt": "SYNTHETIC_PRIVATE_PROMPT"}
        result = self.native_hook("UserPromptSubmit", payload, cwd=runtime.parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(w.git(self.root, "rev-parse", "HEAD"), before)
        self.assertFalse((self.root / "remote.md").exists())
        self.assertEqual(list(self.flow.home.iterdir()), [])

    def test_installed_patch_resolves_paths_against_payload_cwd(self):
        folder = self.root / "nested folder"
        folder.mkdir()
        self.flow.begin("t1")
        self.flow.plan({"requirements": ["nested answer"], "paths": ["nested folder/answer.md"]})
        payload = {"session_id": "test-session", "cwd": str(folder),
                   "tool_name": "apply_patch", "tool_input": {"input": "*** Begin Patch\n*** Add File: answer.md\n+answer\n*** End Patch"}}
        result = self.native_hook("PreToolUse", payload, cwd=folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload["tool_input"]["input"] = "*** Begin Patch\n*** Add File: ../answer.md\n+answer\n*** End Patch"
        result = self.native_hook("PreToolUse", payload, cwd=folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_legacy_patch_payload_accepts_qualified_tool_names(self):
        self.flow.begin("qualified patches")
        self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        for tool_name in ("apply_patch", "functions.apply_patch", "tools.apply_patch", "functions:apply_patch",
                          "native_tools.functions.apply_patch"):
            with self.subTest(tool_name=tool_name):
                payload = {"session_id": "test-session", "cwd": str(self.root), "tool_name": tool_name,
                           "tool_input": {"input": "*** Begin Patch\n*** Add File: answer.md\n+answer\n*** End Patch"}}
                self.assertEqual(self.native_hook("PreToolUse", payload).returncode, 0)
                payload["tool_input"]["input"] = payload["tool_input"]["input"].replace("answer.md", "other.md")
                rejected = self.native_hook("PreToolUse", payload)
                self.assertEqual(rejected.returncode, 0, rejected.stderr)
                self.assertEqual(json.loads(rejected.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_subagent_start_without_parent_contract_creates_no_state(self):
        self.flow.home.rmdir()  # Empty temporary fixture directory, not user state.
        payload = {"session_id": "parent-session", "agent_id": "native-child-id", "cwd": str(self.root),
                   "prompt": "SYNTHETIC_PRIVATE_WORKER_PROMPT", "transcript_path": "/private/worker-transcript"}
        result = self.native_hook("SubagentStart", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertNotIn(payload["prompt"], result.stdout)
        self.assertNotIn(payload["transcript_path"], result.stdout)
        self.assertFalse(self.flow.home.exists())

    def test_subagent_start_supplies_active_contract_context_without_mutation(self):
        self.flow.begin("parent")
        self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        before = self.flow.path.read_bytes()
        result = self.native_hook("SubagentStart", {"agent_id": "native-child-id"})
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SubagentStart")
        self.assertIn("parent session is 'test-session'", output["additionalContext"])
        self.assertIn("native-child-id", output["additionalContext"])
        self.assertIn("Do not commit or push", output["additionalContext"])
        self.assertIn("review-author", output["additionalContext"])
        self.assertEqual(self.flow.path.read_bytes(), before)

    def test_subagent_start_preserves_finished_parent_and_workspace_bytes(self):
        self.flow.begin("parent")
        self.flow.plan({"requirements": ["parent answer"], "paths": ["answer.md"]})
        state = self.flow.load()
        state["finished"] = {"head": w.git(self.root, "rev-parse", "HEAD")}
        self.flow.save(state)
        manifest = self.flow.home / f"workspace-{self.flow.key}.json"
        manifest.write_text('{"finished":{"at":"fixture"},"opaque":"preserve"}\n')
        before = {path.name: path.read_bytes() for path in self.flow.home.iterdir()}
        result = self.native_hook("SubagentStart", {"session_id": "test-session", "agent_id": "worker", "cwd": str(self.root)})
        self.assertEqual(result.returncode, 0, result.stderr)
        after = {path.name: path.read_bytes() for path in self.flow.home.iterdir()}
        self.assertEqual(before, after)
        self.assertFalse((self.flow.home / "workflow.lock").exists())
        self.assertFalse((self.flow.home / "history").exists())

    def test_subagent_start_cannot_redirect_lifecycle_to_neighbor(self):
        result = self.native_hook("SubagentStart", {"session_id": "parent", "agent_id": "worker", "cwd": str(self.other)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertFalse((self.other / ".git/constellation").exists())

    def test_patch_rejects_symlink_parent_added_after_plan(self):
        self.flow.begin("t1")
        self.flow.plan({"requirements": ["answer"], "paths": ["alias/answer.md"]})
        (self.root / "actual").mkdir()
        (self.root / "alias").symlink_to(self.root / "actual", target_is_directory=True)
        payload = {"tool_input": "*** Begin Patch\n*** Add File: alias/answer.md\n+answer\n*** End Patch"}
        with self.assertRaisesRegex(w.Blocked, "regular files"):
            self.flow.guard_patch(payload, self.root)

    def test_stop_without_registered_contract_creates_no_state(self):
        result = self.native_hook("Stop", {"session_id": "no-contract", "cwd": str(self.root)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(list(self.flow.home.iterdir()), [])

    def test_stop_retries_are_bounded_and_labeled_incomplete(self):
        self.flow.begin("t1")
        self.assertEqual(self.flow.stop()["decision"], "block")
        self.assertEqual(self.flow.stop()["decision"], "block")
        final = self.flow.stop()
        self.assertFalse(final["continue"])
        self.assertIn("INCOMPLETE", final["systemMessage"])

    def test_stop_event_replay_does_not_spend_another_continuation(self):
        self.flow.begin("stop-event")
        self.assertEqual(self.flow.stop(request_id="event-1")["decision"], "block")
        before = self.flow.path.read_bytes()
        replay = self.flow.stop(request_id="event-1")
        self.assertFalse(replay["continue"])
        self.assertIn("INCOMPLETE", replay["systemMessage"])
        self.assertEqual(self.flow.path.read_bytes(), before)
        self.assertEqual(self.flow.load()["stop_attempts"], 1)
        self.assertEqual(self.flow.stop(request_id="event-2")["decision"], "block")
        self.assertEqual(self.flow.load()["stop_attempts"], 2)

    def test_completed_stop_event_replay_preserves_state(self):
        self.task()
        self.flow.commit(["answer.md"], "Publish fixture answer")
        self.flow.finish()
        self.assertEqual(self.flow.stop(request_id="completed-event"), {})
        before = self.flow.path.read_bytes()
        self.assertEqual(self.flow.stop(request_id="completed-event"), {})
        self.assertEqual(self.flow.path.read_bytes(), before)
        (self.root / "forgotten.md").write_text("new pending work\n")
        self.assertEqual(self.flow.stop(request_id="next-event")["decision"], "block")

    def test_inspection_does_not_create_operational_state(self):
        directory = self.other / ".git/constellation"
        self.assertFalse(directory.exists())
        flow = w.Workflow(self.other, "inspection", create_state=False)
        self.assertFalse(flow.path.exists())
        self.assertFalse(directory.exists())

    def test_sessions_have_separate_contracts(self):
        self.flow.begin("one")
        other = w.Workflow(self.root, "other-session")
        other.begin("two")
        self.assertNotEqual(other.path, self.flow.path)
        self.assertEqual(self.flow.load()["turn"], "one")


    def test_push_detects_private_content_in_earlier_unpushed_commit(self):
        path = self.root / "09_Data_Sources/Codex_Conversations/rendered/private.md"
        path.parent.mkdir(parents=True)
        path.write_text("private fixture\n")
        self.commit("accidental archive")
        path.unlink()
        self.commit("remove archive")
        with self.assertRaisesRegex(w.Blocked, "private data"):
            w.outgoing_gate(self.root, "HEAD", w.git(self.root, "rev-parse", "origin/main"))

    def test_git_hooks_do_not_deadlock_inside_workflow(self):
        runtime = self.root / ".codex/workflow.py"
        runtime.parent.mkdir()
        copy_runtime(runtime)
        self.commit("install runtime fixture")
        w.git(self.root, "push")
        import sys
        for event in ("pre-commit", "post-commit", "pre-push"):
            hook = self.root / f".git/hooks/{event}"
            hook.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{runtime}" git-hook {event}\n')
            hook.chmod(0o755)
        self.task()
        with self.flow.lock():
            result = self.flow.commit(["answer.md"], "Add answer with hooks")
        self.assertEqual(result["head"], w.git(self.root, "rev-parse", "origin/main"))

    def test_prompt_hook_does_not_persist_prompt_or_transcript(self):
        private_state = w.Workflow(self.root, "native")
        private_state.begin("explicit-task")
        private_state.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        before = private_state.path.read_bytes()
        payload = {"session_id": "native", "turn_id": "one", "cwd": str(self.root),
                   "prompt": "UNIQUE_PRIVATE_PROMPT", "transcript_path": "/private/transcript.jsonl"}
        result = self.native_hook("UserPromptSubmit", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        contents = private_state.path.read_text() + (private_state.home / "events.jsonl").read_text()
        self.assertEqual(private_state.path.read_bytes(), before)
        self.assertNotIn("UNIQUE_PRIVATE_PROMPT", contents)
        self.assertNotIn("transcript.jsonl", contents)

    def test_steered_prompt_preserves_unfinished_requirements(self):
        self.task()
        before = self.flow.path.read_bytes()
        payload = {"session_id": "test-session", "turn_id": "two", "cwd": str(self.root), "prompt": "Also explain the example"}
        result = self.native_hook("UserPromptSubmit", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.flow.load()
        self.assertEqual(state["requirements"], ["answer is present"])
        self.assertEqual(state["paths"], ["answer.md"])
        self.assertEqual(self.flow.path.read_bytes(), before)



    def test_declared_file_deletion_commits_and_publishes(self):
        self.flow.begin("delete")
        self.flow.plan({"requirements": ["remove obsolete file"], "paths": ["README.md"], "deletions": ["README.md"]})
        with self.assertRaisesRegex(w.Blocked, "still exists"):
            self.flow.review({"remove obsolete file": "not yet removed"})
        (self.root / "README.md").unlink()
        self.flow.review({"remove obsolete file": "Tracked obsolete file has been removed."})
        self.flow.commit(["README.md"], "Remove obsolete file")
        self.assertTrue(self.flow.finish()["completed"])
        self.assertFalse(w.git(self.root, "ls-tree", "HEAD", "README.md"))

    def test_declared_symlink_deletion_never_reads_its_target(self):
        target = self.base / "private-target"
        target.mkdir()
        (self.root / "legacy").symlink_to(target, target_is_directory=True)
        self.commit("add old symlink")
        self.flow.begin("delete link")
        self.flow.plan({"requirements": ["remove legacy link"], "paths": ["legacy"], "deletions": ["legacy"]})
        with self.assertRaisesRegex(w.Blocked, "still exists"):
            self.flow.review({"remove legacy link": "not yet removed"})
        (self.root / "legacy").unlink()
        with patch("sys.stdout", new=io.StringIO()):
            self.flow.check(["git", "diff", "--check"])
        self.flow.review({"remove legacy link": "Only the tracked symlink was removed."})
        self.flow.commit(["legacy"], "Remove old link")
        self.assertTrue(self.flow.finish()["completed"])
        self.assertTrue(target.is_dir())

    def test_recreated_deleted_artifact_invalidates_review(self):
        self.flow.begin("delete")
        self.flow.plan({"requirements": ["remove"], "paths": ["README.md"], "deletions": ["README.md"]})
        (self.root / "README.md").unlink()
        self.flow.review({"remove": "File removed."})
        (self.root / "README.md").write_text("new work")
        with self.assertRaisesRegex(w.Blocked, "stale review"):
            self.flow.commit(["README.md"], "Remove file")

    def test_deletions_must_name_tracked_declared_files(self):
        self.flow.begin("delete")
        with self.assertRaisesRegex(w.Blocked, "subset"):
            self.flow.plan({"requirements": ["remove"], "paths": [], "deletions": ["README.md"]})
        with self.assertRaises(w.Blocked):
            self.flow.plan({"requirements": ["remove"], "paths": ["missing.md"], "deletions": ["missing.md"]})

    def test_command_wrapped_patch_still_enforces_declared_scope(self):
        self.flow.begin("patch")
        self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        payload = {"session_id": "test-session", "cwd": str(self.root), "tool_name": "apply_patch",
                   "tool_input": {"command": "*** Begin Patch\n*** Add File: answer.md\n+answer\n*** End Patch"}}
        result = self.native_hook("PreToolUse", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload["tool_input"]["command"] = payload["tool_input"]["command"].replace("answer.md", "other.md")
        result = self.native_hook("PreToolUse", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_hook_ignores_neighbor_without_native_profile(self):
        result = self.native_hook("UserPromptSubmit", {}, cwd=self.other)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertFalse((self.other / ".git/constellation").exists())

    def test_all_hooks_ignore_hostile_runtime_in_neighbor_cwd(self):
        hostile = self.other / ".codex"
        hostile.mkdir()
        (hostile / "workflow.py").write_text(
            "from pathlib import Path\n"
            "Path(__file__).with_name('executed').write_text('UNTRUSTED_RUNTIME_EXECUTED')\n"
            "print('UNTRUSTED_RUNTIME_EXECUTED')\n")
        nested = self.other / "nested folder"
        nested.mkdir()
        for mode in ("external", "native"):
            (hostile / "profile.json").write_text(json.dumps({"mode": mode}))
            for event in ("UserPromptSubmit", "PreToolUse", "SubagentStart", "Stop"):
                for explicit_cwd in (False, True):
                    with self.subTest(mode=mode, event=event, explicit_cwd=explicit_cwd):
                        payload = {"session_id": "hostile-neighbor", "agent_id": "worker"}
                        if explicit_cwd:
                            payload["cwd"] = str(nested)
                        result = self.native_hook(event, payload, cwd=nested)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertNotIn("UNTRUSTED_RUNTIME_EXECUTED", result.stdout + result.stderr)
                        self.assertEqual(json.loads(result.stdout), {})
                        self.assertFalse((hostile / "executed").exists())
                        self.assertFalse((self.other / ".git/constellation").exists())
        self.assertEqual(list(self.flow.home.iterdir()), [])

    def test_private_archive_and_execution_records_cannot_be_published(self):
        for path in [".codex_NOTUSE/MANIFEST.json", ".claude/run/fixture.json", ".codex/sessions/fixture.json", "conversations/manifest.json", "rollout-fixture.json"]:
            with self.subTest(path=path):
                self.assertTrue(w.private_path(path))
                self.assertTrue(w.validate_blob(self.root, path, b"synthetic private data"))

    def test_check_does_not_persist_command_or_output_text(self):
        import sys
        self.flow.begin("check privacy")
        self.flow.plan({"requirements": ["check"], "paths": []})
        with patch("sys.stdout", new=io.StringIO()):
            self.flow.check([sys.executable, "-c", "print('SYNTHETIC_PRIVATE_COMMAND_OUTPUT')"])
        self.assertNotIn("SYNTHETIC_PRIVATE_COMMAND_OUTPUT", self.flow.path.read_text())
        self.assertIn("command_sha256", self.flow.path.read_text())

    def test_staged_private_file_cannot_be_hidden_by_working_copy(self):
        path = self.root / "auth.json"
        path.write_text("synthetic private fixture")
        w.git(self.root, "add", "auth.json")
        path.unlink()
        with self.assertRaisesRegex(w.Blocked, "Private path"):
            w.staged_gate(self.root)


    def test_declared_symlink_deletion_cannot_authorize_update_or_move_target(self):
        outside = self.base / "outside.md"
        outside.write_text("synthetic private fixture")
        link = self.root / "legacy"
        link.symlink_to(outside)
        self.commit("add old link")
        self.flow.begin("delete link")
        self.flow.plan({"requirements": ["remove link"], "paths": ["legacy", "README.md"], "deletions": ["legacy"]})
        for header in ["*** Update File: legacy", "*** Add File: legacy", "*** Update File: README.md\n*** Move to: legacy"]:
            with self.subTest(header=header), self.assertRaisesRegex(w.Blocked, "only authorizes Delete File"):
                self.flow.guard_patch({"tool_input": "*** Begin Patch\n" + header + "\n*** End Patch"}, self.root)
        self.flow.guard_patch({"tool_input": "*** Begin Patch\n*** Delete File: legacy\n*** End Patch"}, self.root)
        self.assertEqual(outside.read_text(), "synthetic private fixture")

    def test_malformed_patch_payload_is_rejected_explicitly(self):
        self.flow.begin("patch")
        self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        for inputs in [None, [], {"command": ["not a patch"]}]:
            with self.subTest(inputs=inputs), self.assertRaisesRegex(w.Blocked, "Unrecognized patch"):
                self.flow.guard_patch({"tool_input": inputs}, self.root)


    def test_failed_fetch_does_not_persist_stderr_or_argv(self):
        original = subprocess.run
        sentinel = "SYNTHETIC_PRIVATE_FETCH_STDERR"
        def fake_run(args, **kwargs):
            if args[:2] == ("git", "fetch"):
                return subprocess.CompletedProcess(args, 128, "", sentinel)
            return original(args, **kwargs)
        with patch.object(subprocess, "run", side_effect=fake_run):
            state = self.flow.begin("failure privacy")
        self.assertIn("git fetch failed (128)", state["sync_error"])
        stored = self.flow.path.read_text() + (self.flow.home / "events.jsonl").read_text()
        self.assertNotIn(sentinel, stored)

    def test_fetch_timeout_does_not_persist_command_arguments(self):
        original = subprocess.run
        sentinel = "SYNTHETIC_PRIVATE_TIMEOUT_ARG"
        def fake_run(args, **kwargs):
            if args[:2] == ("git", "fetch"):
                raise subprocess.TimeoutExpired(["git", "fetch", sentinel], 25)
            return original(args, **kwargs)
        with patch.object(subprocess, "run", side_effect=fake_run):
            state = self.flow.begin("timeout privacy")
        self.assertIn("git fetch timed out", state["sync_error"])
        self.assertNotIn(sentinel, self.flow.path.read_text())


    def test_commit_treats_filenames_as_literal_not_git_patterns(self):
        name = ":(glob)*.md"
        (self.root / "unrelated.md").write_text("user work")
        self.task(name)
        self.flow.commit([name], "Add literal filename")
        self.assertNotIn("unrelated.md", w.git(self.root, "ls-tree", "-r", "--name-only", "HEAD"))
        self.assertIn(name, w.git(self.root, "ls-tree", "-r", "--name-only", "HEAD"))
        self.assertTrue(self.flow.finish()["completed"])

    def test_hook_payload_cannot_redirect_lifecycle_to_neighbor(self):
        payload = {"session_id": "neighbor", "cwd": str(self.other), "prompt": "synthetic"}
        result = self.native_hook("UserPromptSubmit", payload, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertFalse((self.other / ".git/constellation").exists())

    def test_hook_ignores_local_profile_metadata_without_starting_task(self):
        import sys
        runtime = self.root / ".codex/workflow.py"
        runtime.parent.mkdir()
        copy_runtime(runtime)
        marker = runtime.parent / "profile.json"
        payload = json.dumps({"session_id": "invalid-marker", "cwd": str(self.root),
                              "hook_event_name": "UserPromptSubmit", "turn_id": "fixture-turn"})
        for content in ['{"mode":"projected"}', '{}']:
            marker.write_text(content)
            result = subprocess.run([sys.executable, str(runtime), "hook", "prompt"], input=payload, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {})
            self.assertFalse((self.root / ".git/constellation/" / (w.digest(b"invalid-marker")[:24]+".json")).exists())
        marker.unlink()
        marker.symlink_to(self.base / "outside.json")
        result = subprocess.run([sys.executable, str(runtime), "hook", "prompt"], input=payload, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertFalse((self.base / "outside.json").exists())


if __name__ == "__main__":
    unittest.main()
