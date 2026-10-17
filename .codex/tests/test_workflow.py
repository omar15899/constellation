"""Exercise real Git boundaries against disposable local bare remotes."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "workflow.py"
spec = importlib.util.spec_from_file_location("workflow", MODULE)
assert spec and spec.loader
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class GitFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.remote = self.base / "remote.git"
        self.root = self.base / "vault"
        self.other = self.base / "other"
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
        policy = json.loads((MODULE.parent / "review-policy.json").read_text())
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
        """Execute the exact installed shell definition, with realistic stdin."""
        runtime = self.root / ".codex/workflow.py"
        runtime.parent.mkdir(exist_ok=True)
        shutil.copyfile(MODULE, runtime)
        (runtime.parent / "profile.json").write_text('{"mode":"native"}\n')
        manifest = json.loads((MODULE.parent / "hooks.json").read_text())
        command = manifest["hooks"][event][0]["hooks"][0]["command"]
        return subprocess.run(command, shell=True, cwd=cwd or self.root,
                              input=json.dumps(payload), capture_output=True,
                              text=True, timeout=15)

    def test_installed_prompt_checks_remote_from_subfolder(self):
        self.advance_remote()
        # Keep fixture installation clean so the prompt can fast-forward.
        runtime = self.root / ".codex/workflow.py"
        runtime.parent.mkdir()
        shutil.copyfile(MODULE, runtime)
        w.git(self.root, "config", "--add", "core.excludesFile", str(self.base / "ignore"))
        (self.base / "ignore").write_text(".codex/\n")
        payload = {"session_id": "native", "turn_id": "one", "cwd": str(runtime.parent),
                   "prompt": "SYNTHETIC_PRIVATE_PROMPT"}
        result = self.native_hook("UserPromptSubmit", payload, cwd=runtime.parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Upstream checked", json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])
        self.assertEqual((self.root / "remote.md").read_text(), "new cloud data\n")

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
        self.assertEqual(result.returncode, 2)
        self.assertIn("Undeclared patch path", result.stderr)

    def test_patch_rejects_symlink_parent_added_after_plan(self):
        self.flow.begin("t1")
        self.flow.plan({"requirements": ["answer"], "paths": ["alias/answer.md"]})
        (self.root / "actual").mkdir()
        (self.root / "alias").symlink_to(self.root / "actual", target_is_directory=True)
        payload = {"tool_input": "*** Begin Patch\n*** Add File: alias/answer.md\n+answer\n*** End Patch"}
        with self.assertRaisesRegex(w.Blocked, "regular files"):
            self.flow.guard_patch(payload, self.root)

    def test_installed_stop_missing_contract_reports_incomplete(self):
        result = self.native_hook("Stop", {"session_id": "no-contract", "cwd": str(self.root)})
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertFalse(output["continue"])
        self.assertIn("INCOMPLETE", output["systemMessage"])

    def test_stop_retries_are_bounded_and_labeled_incomplete(self):
        self.flow.begin("t1")
        self.assertEqual(self.flow.stop()["decision"], "block")
        self.assertEqual(self.flow.stop()["decision"], "block")
        final = self.flow.stop()
        self.assertFalse(final["continue"])
        self.assertIn("INCOMPLETE", final["systemMessage"])

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
        shutil.copyfile(MODULE, runtime)
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
        import sys
        payload = {"session_id": "native", "turn_id": "one", "cwd": str(self.root),
                   "prompt": "UNIQUE_PRIVATE_PROMPT", "transcript_path": "/private/transcript.jsonl"}
        result = self.native_hook("UserPromptSubmit", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        private_state = w.Workflow(self.root, "native")
        contents = private_state.path.read_text() + (private_state.home / "events.jsonl").read_text()
        self.assertNotIn("UNIQUE_PRIVATE_PROMPT", contents)
        self.assertNotIn("transcript.jsonl", contents)

    def test_steered_prompt_preserves_unfinished_requirements(self):
        import sys
        self.task()
        payload = {"session_id": "test-session", "turn_id": "two", "cwd": str(self.root), "prompt": "Also explain the example"}
        result = self.native_hook("UserPromptSubmit", payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.flow.load()
        self.assertEqual(state["requirements"], ["answer is present"])
        self.assertEqual(state["paths"], ["answer.md"])
        self.assertIsNone(state["review"])



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
        self.assertEqual(result.returncode, 2)
        self.assertIn("Undeclared", result.stderr)

    def test_hook_ignores_neighbor_without_native_profile(self):
        command = json.loads((MODULE.parent / "hooks.json").read_text())["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        result = subprocess.run(command, shell=True, cwd=self.other, input="{}", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse((self.other / ".git/constellation").exists())

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

    def test_hook_rejects_invalid_or_symlinked_native_marker(self):
        import sys
        runtime = self.root / ".codex/workflow.py"
        runtime.parent.mkdir()
        shutil.copyfile(MODULE, runtime)
        marker = runtime.parent / "profile.json"
        payload = json.dumps({"session_id": "invalid-marker", "cwd": str(self.root)})
        for content in ['{"mode":"projected"}', '{}']:
            marker.write_text(content)
            result = subprocess.run([sys.executable, str(runtime), "hook", "prompt"], input=payload, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse((self.root / ".git/constellation/" / (w.digest(b"invalid-marker")[:24]+".json")).exists())
        marker.unlink()
        marker.symlink_to(self.base / "outside.json")
        result = subprocess.run([sys.executable, str(runtime), "hook", "prompt"], input=payload, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("regular local file", result.stderr)


if __name__ == "__main__":
    unittest.main()
