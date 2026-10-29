"""Regression tests for repository ownership and fixed publication destinations."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("workflow_fixture", Path(__file__).with_name("test_workflow.py"))
assert SPEC and SPEC.loader
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)
w = fixture.w


class RepositoryBoundaries(unittest.TestCase):
    setUp = fixture.GitFixture.setUp
    tearDown = fixture.GitFixture.tearDown
    commit = fixture.GitFixture.commit
    task = fixture.GitFixture.task
    assert_unregistered_response = fixture.GitFixture.assert_unregistered_response

    def nested(self):
        child = self.root / "child"
        child.mkdir(exist_ok=True)
        subprocess.run(["git", "init", "-q", str(child)], check=True)
        return child.resolve()

    def another_destination(self):
        remote = self.base / "different.git"
        subprocess.run(["git", "clone", "--bare", "-q", str(self.remote), str(remote)], check=True)
        return remote

    def test_plan_rejects_files_owned_by_nested_repository(self):
        child = self.nested()
        (child / "answer.md").write_text("nested answer\n")
        self.flow.begin("nested")
        with self.assertRaisesRegex(w.Blocked, "nested repository"):
            self.flow.plan({"requirements": ["child answer"], "paths": ["child/answer.md"]})
        with self.assertRaisesRegex(w.Blocked, "nested repository"):
            w.safe_path(self.root, "child/missing.md", deletion=True)

    def test_owner_resolves_files_and_nonexistent_descendants(self):
        self.assertEqual(w.owner_root(self.root / "not-yet/a/b.md"), self.root.resolve())
        child = self.nested()
        self.assertEqual(w.owner_root(child / "not-yet/a.md"), child.resolve())

    def test_new_repository_boundary_invalidates_an_existing_review(self):
        (self.root / "child").mkdir()
        self.task("child/answer.md")
        self.nested()
        with self.assertRaisesRegex(w.Blocked, "nested repository"):
            self.flow.finish()
        self.assertIsNone(self.flow.load().get("finished"))

    def test_distinct_pushurl_is_blocked_before_transmission(self):
        destination = self.another_destination()
        old = w.git(self.root, "rev-parse", "HEAD")
        self.task()
        w.git(self.root, "remote", "set-url", "--push", "origin", str(destination))
        with self.assertRaisesRegex(w.Blocked, "identical fetch and push URL"):
            self.flow.commit(["answer.md"], "Add answer")
        self.assertEqual(w.git(self.root, "diff", "--cached", "--name-only"), "")
        self.assertEqual(w.git(destination, "rev-parse", "refs/heads/main"), old)
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), old)

    def test_multiple_pushurls_are_rejected_even_when_identical(self):
        w.git(self.root, "config", "--add", "remote.origin.pushurl", str(self.remote))
        w.git(self.root, "config", "--add", "remote.origin.pushurl", str(self.remote))
        state = self.flow.begin("multiple destinations")
        self.assertIn("multiple pushurl", state["sync_error"])
        with self.assertRaises(w.Blocked):
            self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})

    def test_changed_remote_url_cannot_reuse_review_or_plan(self):
        destination = self.another_destination()
        self.task()
        w.git(self.root, "remote", "set-url", "origin", str(destination))
        with self.assertRaisesRegex(w.Blocked, "destination changed"):
            self.flow.commit(["answer.md"], "Add answer")
        with self.assertRaisesRegex(w.Blocked, "destination changed"):
            self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        self.assertEqual(w.git(self.root, "diff", "--cached", "--name-only"), "")

    def test_changed_branch_and_upstream_ref_are_rejected(self):
        self.task()
        w.git(self.root, "checkout", "-b", "different", "--track", "origin/main")
        with self.assertRaisesRegex(w.Blocked, "destination changed"):
            self.flow.commit(["answer.md"], "Add answer")
        w.git(self.root, "checkout", "main")
        w.git(self.root, "config", "branch.main.merge", "refs/heads/different")
        with self.assertRaisesRegex(w.Blocked, "destination changed"):
            self.flow.ensure_target(self.flow.load())

    def test_target_change_after_finish_blocks_stop(self):
        destination = self.another_destination()
        self.task()
        self.flow.commit(["answer.md"], "Add answer")
        self.flow.finish()
        w.git(self.root, "remote", "set-url", "origin", str(destination))
        result = self.flow.stop()
        self.assertEqual(result["decision"], "block")
        self.assertIn("destination changed", result["reason"])

    def test_renewed_plan_pins_older_contract_without_losing_baseline(self):
        (self.root / "README.md").write_text("existing user work\n")
        self.flow.begin("existing contract")
        state = self.flow.load()
        state.pop("target")
        state["sync"].pop("url_sha256")
        self.flow.save(state)
        self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        renewed = self.flow.load()
        self.assertEqual(renewed["baseline_dirty"], ["README.md"])
        self.assertEqual(renewed["target"], w.publication_target(self.root))
        self.assertNotIn(str(self.remote), self.flow.path.read_text())

    def test_failed_begin_has_nonzero_cli_exit_code(self):
        w.git(self.root, "remote", "set-url", "origin", str(self.base / "missing.git"))
        result = subprocess.run([sys.executable, str(fixture.MODULE), "git", "--root", str(self.root),
                                 "--session", "cli-failure", "begin"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("sync_error", json.loads(result.stdout))

    def test_replan_retries_transient_fetch_failure_without_losing_baseline(self):
        (self.root / "README.md").write_text("existing work\n")
        original = w.git
        def unavailable(root, *args, **kwargs):
            if args and args[0] == "fetch":
                raise w.Blocked("Synthetic temporary network failure")
            return original(root, *args, **kwargs)
        with patch.object(w, "git", side_effect=unavailable):
            self.flow.begin("temporary failure")
        self.assertIn("sync_error", self.flow.load())
        self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})
        state = self.flow.load()
        self.assertNotIn("sync_error", state)
        self.assertEqual(state["baseline_dirty"], ["README.md"])
        self.assertEqual(state["turn"], "temporary failure")

    def test_fetch_recovery_cannot_change_the_frozen_destination(self):
        self.flow.begin("initial")
        state = self.flow.load()
        state["sync_error"] = "Synthetic network failure"
        self.flow.save(state)
        destination = self.another_destination()
        w.git(self.root, "remote", "set-url", "origin", str(destination))
        with self.assertRaisesRegex(w.Blocked, "destination changed"):
            self.flow.plan({"requirements": ["answer"], "paths": ["answer.md"]})

    def test_push_uses_audited_sha_when_head_moves_concurrently(self):
        self.task()
        original = w.git
        audited = []
        def race(root, *args, **kwargs):
            if args and args[0] == "push":
                audited.append(original(root, "rev-parse", "HEAD"))
                self.assertEqual(args[-1], f"{audited[0]}:refs/heads/main")
                (root / "other.md").write_text("concurrent unrelated commit\n")
                original(root, "add", "other.md")
                original(root, "commit", "-m", "Concurrent work")
            return original(root, *args, **kwargs)
        with patch.object(w, "git", side_effect=race):
            with self.assertRaisesRegex(w.Blocked, "Remote verification failed"):
                self.flow.commit(["answer.md"], "Add answer")
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), audited[0])
        self.assertNotEqual(w.git(self.root, "rev-parse", "HEAD"), audited[0])
        self.assertIsNone(self.flow.load().get("finished"))

    def test_edits_during_add_are_not_committed_or_published(self):
        self.task()
        before = w.git(self.root, "rev-parse", "HEAD")
        original = w.git
        def concurrent_edit(root, *args, **kwargs):
            if args[:2] == ("--literal-pathspecs", "add"):
                (root / "answer.md").write_text("not reviewed\n")
            return original(root, *args, **kwargs)
        with patch.object(w, "git", side_effect=concurrent_edit):
            with self.assertRaisesRegex(w.Blocked, "Staged content differs"):
                self.flow.commit(["answer.md"], "Add answer")
        self.assertEqual(w.git(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), before)
        self.assertEqual((self.root / "answer.md").read_text(), "not reviewed\n")

    def test_unrelated_work_staged_during_add_is_preserved_and_not_committed(self):
        self.task()
        before = w.git(self.root, "rev-parse", "HEAD")
        original = w.git
        def concurrent_stage(root, *args, **kwargs):
            if args[:2] == ("--literal-pathspecs", "add"):
                (root / "other.md").write_text("unrelated staged work\n")
                original(root, "add", "other.md")
            return original(root, *args, **kwargs)
        with patch.object(w, "git", side_effect=concurrent_stage):
            with self.assertRaisesRegex(w.Blocked, "unselected work"):
                self.flow.commit(["answer.md"], "Add answer")
        self.assertEqual(w.git(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), before)
        self.assertEqual(set(w.git(self.root, "diff", "--cached", "--name-only").splitlines()), {"answer.md", "other.md"})

    def test_hook_mutation_of_committed_blob_blocks_publication_and_retry(self):
        self.task()
        before = w.git(self.root, "rev-parse", "HEAD")
        hook = self.root / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nprintf 'not reviewed\\n' > answer.md\ngit add -- answer.md\nprintf 'answer\\n' > answer.md\n")
        hook.chmod(0o755)
        with self.assertRaisesRegex(w.Blocked, "local commit failed verification"):
            self.flow.commit(["answer.md"], "Add answer")
        self.assertNotEqual(w.git(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(w.git(self.root, "show", "HEAD:answer.md"), "not reviewed")
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), before)
        with self.assertRaisesRegex(w.Blocked, "local commit failed verification"):
            self.flow.publish()
        with self.assertRaisesRegex(w.Blocked, "local commit failed verification"):
            self.flow.commit(["answer.md"], "Retry cannot clear the publication blocker")

    def test_hook_adding_unselected_file_blocks_publication(self):
        self.task()
        before = w.git(self.root, "rev-parse", "HEAD")
        hook = self.root / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nprintf 'unrelated\\n' > other.md\ngit add -- other.md\n")
        hook.chmod(0o755)
        with self.assertRaisesRegex(w.Blocked, "local commit failed verification"):
            self.flow.commit(["answer.md"], "Add answer")
        self.assertEqual(w.git(self.root, "show", "HEAD:other.md"), "unrelated")
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), before)
        self.assertTrue(self.flow.load()["publication_blocker"])

    def test_interruption_after_git_commit_preserves_publication_blocker(self):
        self.task()
        before = w.git(self.root, "rev-parse", "HEAD")
        original = w.git
        def interrupted(root, *args, **kwargs):
            result = original(root, *args, **kwargs)
            if args and args[0] == "commit":
                raise OSError("Synthetic interruption after Git committed")
            return result
        with patch.object(w, "git", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.flow.commit(["answer.md"], "Add answer")
        self.assertNotEqual(w.git(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), before)
        with self.assertRaisesRegex(w.Blocked, "local commit failed verification"):
            self.flow.publish()

    def test_preserve_index_keeps_partially_staged_user_work(self):
        (self.root / "README.md").write_text("user staged version\n")
        w.git(self.root, "add", "README.md")
        (self.root / "README.md").write_text("user unstaged continuation\n")
        self.task()
        fingerprint = w.index_fingerprint(self.root, ["answer.md"])
        staged_diff = w.git(self.root, "diff", "--cached", "--binary")
        self.flow.commit(["answer.md"], "Add answer only", preserve_index=True)
        self.assertEqual(w.index_fingerprint(self.root, ["answer.md"]), fingerprint)
        self.assertEqual(w.git(self.root, "diff", "--cached", "--binary"), staged_diff)
        self.assertEqual((self.root / "README.md").read_text(), "user unstaged continuation\n")
        self.assertEqual(w.git(self.remote, "show", "refs/heads/main:README.md"), "seed")
        self.assertTrue(self.flow.finish()["completed"])

    def test_preserve_index_keeps_deletion_mode_and_private_addition_with_hooks(self):
        script = self.root / "tool.sh"
        script.write_text("#!/bin/sh\nexit 0\n")
        self.commit("Seed executable fixture")
        w.git(self.root, "push")
        script.chmod(0o755)
        (self.root / "README.md").unlink()
        (self.root / "auth.json").write_text('{"synthetic":"private staged fixture"}\n')
        w.git(self.root, "add", "tool.sh", "README.md", "auth.json")
        self.task()
        fingerprint = w.index_fingerprint(self.root, ["answer.md"])
        staged_diff = w.git(self.root, "diff", "--cached", "--binary")
        hook = self.root / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nprintf 'ran' > .git/hook-ran\nexec "
                        + shlex.quote(sys.executable) + " " + shlex.quote(str(fixture.MODULE))
                        + " git git-hook pre-commit\n")
        hook.chmod(0o755)
        self.flow.commit(["answer.md"], "Add answer with preserved index", preserve_index=True)
        self.assertEqual((self.root / ".git/hook-ran").read_text(), "ran")
        self.assertEqual(w.index_fingerprint(self.root, ["answer.md"]), fingerprint)
        self.assertEqual(w.git(self.root, "diff", "--cached", "--binary"), staged_diff)
        self.assertFalse((self.root / "README.md").exists())
        self.assertEqual(w.git(self.remote, "ls-tree", "refs/heads/main", "auth.json"), "")
        self.assertEqual(w.git(self.remote, "show", "refs/heads/main:README.md"), "seed")
        self.assertTrue(w.git(self.root, "ls-files", "--stage", "tool.sh").startswith("100755"))

    def test_preserve_index_rejects_selected_staged_paths(self):
        self.task()
        w.git(self.root, "add", "answer.md")
        before = w.git(self.root, "rev-parse", "HEAD")
        index = w.git(self.root, "ls-files", "--stage", "-z")
        with self.assertRaisesRegex(w.Blocked, "overlap existing staged work"):
            self.flow.commit(["answer.md"], "Cannot adopt staged task file", preserve_index=True)
        self.assertEqual(w.git(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(w.git(self.root, "ls-files", "--stage", "-z"), index)

    def test_preserve_index_hook_cannot_publish_an_unselected_staged_file(self):
        (self.root / "README.md").write_text("user staged version\n")
        w.git(self.root, "add", "README.md")
        (self.root / "README.md").write_text("user unstaged continuation\n")
        self.task()
        before = w.git(self.root, "rev-parse", "HEAD")
        fingerprint = w.index_fingerprint(self.root, ["answer.md"])
        hook = self.root / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\ngit add -- README.md\n")
        hook.chmod(0o755)
        with self.assertRaisesRegex(w.Blocked, "failed verification|without publication"):
            self.flow.commit(["answer.md"], "Hook tries to include another file", preserve_index=True)
        self.assertEqual(w.index_fingerprint(self.root, ["answer.md"]), fingerprint)
        self.assertEqual((self.root / "README.md").read_text(), "user unstaged continuation\n")
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), before)
        with self.assertRaisesRegex(w.Blocked, "local commit failed verification"):
            self.flow.publish()

    def test_preserve_index_cli_publishes_only_explicit_paths(self):
        (self.root / "README.md").write_text("unrelated staged work\n")
        w.git(self.root, "add", "README.md")
        self.task()
        result = subprocess.run([sys.executable, str(fixture.MODULE), "git", "--root", str(self.root),
                                 "--session", "test-session", "commit", "--preserve-index",
                                 "-m", "Add answer only", "answer.md"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(w.staged_paths(self.root), {"README.md"})
        self.assertEqual(w.git(self.remote, "show", "refs/heads/main:README.md"), "seed")

    def test_staged_paths_include_both_sides_of_a_rename(self):
        w.git(self.root, "mv", "README.md", "renamed.md")
        self.assertEqual(w.staged_paths(self.root), {"README.md", "renamed.md"})

    def nested_commit_case(self):
        (self.root / "README.md").write_text("user staged work\n")
        w.git(self.root, "add", "README.md")
        self.task()
        hook = self.root / ".git/hooks/post-commit"
        hook.write_text("#!/bin/sh\ncase \"$(git log -1 --format=%s)\" in synthetic-doc:*) exit 0;; esac\n"
                        "printf 'generated by hook\\n' > generated.md\ngit add -- generated.md\n"
                        "git commit -q -m 'synthetic-doc: nested hook commit'\n")
        hook.chmod(0o755)
        with self.assertRaisesRegex(w.Blocked, "without publication|failed verification"):
            self.flow.commit(["answer.md"], "Add answer", preserve_index=True)
        return w.git(self.root, "rev-parse", "HEAD^"), w.git(self.root, "rev-parse", "HEAD")

    def repair_fixture(self, intended):
        # Model an independently authorized repair, confined to this disposable
        # test repository. recover itself must never change HEAD or the index.
        w.git(self.root, "reset", "--soft", intended)
        w.git(self.root, "restore", "--staged", "--", "generated.md")

    def test_recover_cli_audits_repaired_head_without_changing_git(self):
        intended, invalid = self.nested_commit_case()
        self.assertIn(invalid, self.flow.load()["commits"])
        self.repair_fixture(intended)
        index_before = w.index_fingerprint(self.root, [])
        remote_before = w.git(self.remote, "rev-parse", "refs/heads/main")
        result = subprocess.run([sys.executable, str(fixture.MODULE), "git", "--root", str(self.root),
                                 "--session", "test-session", "recover", intended], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertTrue(output["recovered"])
        self.assertFalse(output["publication_verified"])
        self.assertEqual(self.flow.load()["commits"], [intended])
        self.assertNotIn("publication_blocker", self.flow.load())
        self.assertEqual(w.git(self.root, "rev-parse", "HEAD"), intended)
        self.assertEqual(w.index_fingerprint(self.root, []), index_before)
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), remote_before)
        self.assertEqual(w.staged_paths(self.root), {"README.md"})
        self.assertTrue((self.root / "generated.md").is_file())

    def test_recover_rejects_wrong_head_and_nested_hook_commit(self):
        intended, invalid = self.nested_commit_case()
        with self.assertRaisesRegex(w.Blocked, "exact full commit SHA"):
            self.flow.recover("HEAD")
        with self.assertRaisesRegex(w.Blocked, "does not match"):
            self.flow.recover(intended)
        with self.assertRaisesRegex(w.Blocked, "undeclared paths"):
            self.flow.recover(invalid)
        self.assertTrue(self.flow.load()["publication_blocker"])

    def test_recover_requires_existing_blocker(self):
        self.task()
        with self.assertRaisesRegex(w.Blocked, "no blocked publication"):
            self.flow.recover(w.git(self.root, "rev-parse", "HEAD"))

    def recovery_after_remote_fast_forward(self, *, retry_initial_sync=False, retry_target_check=False):
        fixture.GitFixture.advance_remote(self)
        synchronized_head = w.git(self.remote, "rev-parse", "refs/heads/main")
        if retry_initial_sync:
            with patch.object(w, "sync", side_effect=w.Blocked("Synthetic initial fetch failure")):
                self.flow.begin("initial sync retry")
            self.assertIn("sync_error", self.flow.load())
        elif retry_target_check:
            with patch.object(self.flow, "ensure_target", side_effect=w.Blocked("Synthetic initial target check failure")):
                self.flow.begin("initial target check retry")
            self.assertIn("sync_error", self.flow.load())
        else:
            self.flow.begin("initial fast-forward")
        self.flow.plan({"requirements": ["answer is present"], "paths": ["answer.md"]})
        (self.root / "answer.md").write_text("answer\n")
        self.flow.review({"answer is present": "Read answer.md and verified its contents."})
        original_log = self.flow.log

        def interrupt_after_commit(event, **fields):
            if event == "commit":
                raise OSError("Synthetic interruption after durable commit")
            return original_log(event, **fields)

        with patch.object(self.flow, "log", side_effect=interrupt_after_commit):
            with self.assertRaisesRegex(OSError, "after durable commit"):
                self.flow.commit(["answer.md"], "Add task answer")
        head = w.git(self.root, "rev-parse", "HEAD")
        index = w.index_fingerprint(self.root, [])
        self.assertTrue(self.flow.load()["publication_blocker"])
        recovered = self.flow.recover(head)
        self.assertEqual(recovered["audited_commits"], 1)
        self.assertFalse(recovered["publication_verified"])
        self.assertEqual(self.flow.load()["initial_head"], synchronized_head)
        self.assertEqual(self.flow.load()["commits"], [head])
        self.assertNotIn("publication_blocker", self.flow.load())
        self.assertEqual(w.git(self.root, "rev-parse", "HEAD"), head)
        self.assertEqual(w.index_fingerprint(self.root, []), index)
        self.assertEqual(w.git(self.remote, "rev-parse", "refs/heads/main"), synchronized_head)
        self.assertEqual((self.root / "remote.md").read_text(), "new cloud data\n")

    def test_recover_after_begin_fast_forward_audits_only_task_commits(self):
        self.recovery_after_remote_fast_forward()

    def test_recover_after_initial_sync_retry_audits_only_task_commits(self):
        self.recovery_after_remote_fast_forward(retry_initial_sync=True)

    def test_recover_after_initial_target_retry_audits_only_task_commits(self):
        self.recovery_after_remote_fast_forward(retry_target_check=True)

    def test_later_sync_retry_preserves_the_original_recovery_baseline(self):
        self.task()
        initial = self.flow.load()["initial_head"]
        self.flow.commit(["answer.md"], "Add answer")
        state = self.flow.load()
        state["sync_error"] = "Synthetic later fetch failure"
        self.flow.save(state)
        self.flow.plan({"requirements": ["answer is present"], "paths": ["answer.md"]})
        self.assertNotEqual(w.git(self.root, "rev-parse", "HEAD"), initial)
        self.assertEqual(self.flow.load()["initial_head"], initial)

    def test_recover_rejects_stale_working_content_after_repair(self):
        intended, _ = self.nested_commit_case()
        self.repair_fixture(intended)
        (self.root / "answer.md").write_text("not reviewed\n")
        with self.assertRaisesRegex(w.Blocked, "stale review"):
            self.flow.recover(intended)
        self.assertTrue(self.flow.load()["publication_blocker"])

    def test_recover_rejects_unreviewed_committed_blob_even_if_working_copy_matches(self):
        self.task()
        hook = self.root / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nprintf 'not reviewed\\n' > answer.md\ngit add -- answer.md\nprintf 'answer\\n' > answer.md\n")
        hook.chmod(0o755)
        with self.assertRaises(w.Blocked):
            self.flow.commit(["answer.md"], "Hook changes commit content")
        with self.assertRaisesRegex(w.Blocked, "does not contain the reviewed artifacts"):
            self.flow.recover(w.git(self.root, "rev-parse", "HEAD"))
        self.assertTrue(self.flow.load()["publication_blocker"])

    def test_recover_rejects_destination_change(self):
        intended, _ = self.nested_commit_case()
        self.repair_fixture(intended)
        replacement = self.another_destination()
        w.git(self.root, "remote", "set-url", "origin", str(replacement))
        with self.assertRaisesRegex(w.Blocked, "destination changed"):
            self.flow.recover(intended)
        self.assertTrue(self.flow.load()["publication_blocker"])

    def test_commit_owner_marker_is_scoped_to_commit_and_reaches_both_hooks(self):
        self.task()
        inherited = os.environ.get("CONSTELLATION_COMMIT_OWNER")
        for event in ("pre-commit", "post-commit"):
            hook = self.root / ".git/hooks" / event
            hook.write_text("#!/bin/sh\ntest \"$CONSTELLATION_COMMIT_OWNER\" = native || exit 9\n"
                            f"printf '%s' \"$CONSTELLATION_COMMIT_OWNER\" > .git/{event}-owner\n")
            hook.chmod(0o755)
        original = subprocess.run
        marked_commands = []
        def record(args, **kwargs):
            if args and args[0] == "git":
                marker = kwargs.get("env", os.environ).get("CONSTELLATION_COMMIT_OWNER")
                is_commit = args[1] == "commit" or args[1:3] == ("--literal-pathspecs", "commit")
                if is_commit:
                    self.assertEqual(marker, "native")
                    marked_commands.append(tuple(args))
                else:
                    self.assertEqual(marker, inherited)
            return original(args, **kwargs)
        with patch.object(subprocess, "run", side_effect=record):
            self.flow.commit(["answer.md"], "Add answer through intact hooks")
        self.assertEqual(len(marked_commands), 1)
        self.assertEqual(os.environ.get("CONSTELLATION_COMMIT_OWNER"), inherited)
        for event in ("pre-commit", "post-commit"):
            self.assertEqual((self.root / ".git" / f"{event}-owner").read_text(), "native")

    def workspace_command(self, *args, payload=None):
        return subprocess.run([sys.executable, str(self.root / ".codex/ecosystem/cli.py"), "workspace",
                               "--session", "hook-workspace", *args], cwd=self.root,
                              input=json.dumps(payload) if payload is not None else None,
                              capture_output=True, text=True, timeout=15)

    def native_workspace(self, *, include_hub=False):
        runtime = self.root / ".codex"
        runtime.mkdir()
        fixture.copy_runtime(runtime / "ecosystem/cli.py")
        (runtime / "profile.json").write_text('{"mode":"native"}\n')
        (runtime / "repositories.json").write_text(json.dumps({"schema_version": 1, "repositories": [
            {"path": ".", "management": "native"}, {"path": "child", "management": "native"}]}))
        (self.root / ".git/info/exclude").write_text(".codex/\nchild/\n")
        child = self.root / "child"
        subprocess.run(["git", "clone", "-q", "-b", "main", str(self.remote), str(child)], check=True)
        for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                           ("commit.gpgsign", "false"), ("core.hooksPath", str(child / ".git/hooks"))):
            w.git(child, "config", key, value)
        paths = ["child/answer.md"] + (["hub.md"] if include_hub else [])
        result = self.workspace_command("plan", payload={"requirements": ["workspace answer"], "paths": paths})
        self.assertEqual(result.returncode, 0, result.stderr)
        return child.resolve()

    def native_event(self, event, **fields):
        hook_name = {"prompt": "UserPromptSubmit", "pre-tool": "PreToolUse",
                     "subagent-start": "SubagentStart", "stop": "Stop"}[event]
        payload = {"session_id": "hook-workspace", "cwd": str(self.root),
                   "hook_event_name": hook_name, "turn_id": "fixture-turn",
                   "tool_name": "apply_patch", **fields}
        command = fixture.native_hook_command(hook_name, self.root / ".codex/ecosystem/cli.py")
        return subprocess.run(command,
                              cwd=self.root, input=json.dumps(payload), capture_output=True,
                              text=True, timeout=10)

    def test_native_workspace_patch_dispatches_before_taking_hub_lock(self):
        child = self.native_workspace(include_hub=True)
        document = (f"*** Begin Patch\n*** Add File: hub.md\n+hub\n"
                    f"*** Add File: {child / 'answer.md'}\n+child\n*** End Patch")
        result = self.native_event("pre-tool", tool_input={"command": document})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        result = self.native_event("pre-tool", tool_input={"command": document.replace("answer.md", "undeclared.md")})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn("Traceback", result.stderr)

    def test_native_prompt_preserves_child_only_workspace_without_hub_begin(self):
        self.native_workspace()
        key = w.digest(b"hook-workspace")[:24]
        directory = self.root / ".git/constellation"
        manifest = directory / f"workspace-{key}.json"
        before = manifest.read_bytes()
        result = self.native_event("prompt", prompt="SYNTHETIC_PRIVATE_STEERING_PROMPT", turn_id="next")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("active Git workspace contract", json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(manifest.read_bytes(), before)
        self.assertFalse((directory / f"{key}.json").exists())
        result = self.native_event("stop")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "block")

    def test_completed_workspace_prompt_preserves_receipts_without_new_lifecycle(self):
        child = self.native_workspace()
        (child / "answer.md").write_text("reviewed answer\n")
        result = self.workspace_command("review-start", "--repo", "child")
        self.assertEqual(result.returncode, 0, result.stderr)
        token = json.loads(result.stdout)["token"]
        result = self.workspace_command("review-report", "--repo", "child", payload={
            "token": token, "reviewer": "independent-fixture-agent", "role": "reviewer",
            "focus": ["correctness"], "paths": ["answer.md"], "summary": "0 findings",
            "evidence": "Inspected the fixture answer.", "findings": []})
        self.assertEqual(result.returncode, 0, result.stderr)
        for args, payload in [(("review",), {"child": {"workspace answer": "Read and reviewed answer."}}),
                              (("commit", "-m", "Add answer", "child/answer.md"), None),
                              (("finish",), None)]:
            result = self.workspace_command(*args, payload=payload)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = self.native_event("stop")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        key = w.digest(b"hook-workspace")[:24]
        directory = self.root / ".git/constellation"
        manifest = directory / f"workspace-{key}.json"
        before = manifest.read_bytes()
        result = self.native_event("prompt", prompt="A different task", turn_id="new-task")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_unregistered_response("UserPromptSubmit", json.loads(result.stdout))
        self.assertEqual(manifest.read_bytes(), before)
        self.assertFalse((directory / f"{key}.json").exists())


if __name__ == "__main__":
    unittest.main()
