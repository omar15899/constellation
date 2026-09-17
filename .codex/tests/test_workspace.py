"""Integration tests against independent repositories and disposable bare remotes."""
from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
import workspace as ws


class WorkspaceFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "hub"
        (self.root / ".codex").mkdir(parents=True)
        self.registry = {"schema_version": 1, "repositories": [
            {"path": ".", "management": "native"},
            {"path": "Shared", "management": "native"},
            {"path": "Sibling", "management": "native"},
            {"path": "External", "management": "external"}]}
        (self.root / ".codex/repositories.json").write_text(json.dumps(self.registry))
        (self.root / ".gitignore").write_text("Shared/\nSibling/\nExternal/\nUnknown/\n")
        self.remotes = {}
        for name in (".", "Shared", "Sibling", "External"):
            self.make_repo(name)
        self.workspace = ws.Workspace(self.root, "test-workspace")

    def tearDown(self):
        self.temp.cleanup()

    def make_repo(self, name):
        root = self.root / name
        root.mkdir(parents=True, exist_ok=True)
        remote = self.base / ("hub.git" if name == "." else name + ".git")
        self.remotes[name] = remote
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
        for key, value in (("user.name", "Test"), ("user.email", "test@example.invalid"),
                           ("commit.gpgsign", "false"), ("core.hooksPath", str(root / ".git/hooks"))):
            ws.git(root, "config", key, value)
        (root / "README.md").write_text("seed\n")
        (root / "AGENTS.md").write_text("Repository instructions\n")
        ws.git(root, "add", "--all")
        ws.git(root, "commit", "-m", "Seed fixture")
        ws.git(root, "remote", "add", "origin", str(remote))
        ws.git(root, "push", "-u", "origin", "main")

    def plan(self, paths, **extra):
        return self.workspace.plan({"requirements": ["Artifacts satisfy the task"], "paths": paths, **extra})

    def write_and_review(self, paths):
        for name in paths:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("verified artifact\n")
        state = self.workspace.load()
        self.workspace.review({repo: {"Artifacts satisfy the task": "Read each declared artifact and verified its contents."}
                               for repo in state["roots"]})

    def test_route_uses_real_owner_and_is_read_only(self):
        routes = self.workspace.route(["new.md", "Shared/new dir/new.md", "Sibling/README.md"])
        self.assertEqual([item["repository"] for item in routes], [".", "Shared", "Sibling"])
        self.assertEqual(routes[1]["path"], "new dir/new.md")
        self.assertEqual(routes[1]["remotes"], ["origin"])
        self.assertEqual(routes[1]["upstream"], "origin/main")
        self.assertFalse((self.root / ".git/constellation").exists())
        self.assertFalse((self.root / "Shared/.git/constellation").exists())
        self.assertNotIn(str(self.base / "Shared.git"), json.dumps(routes))

    def test_instruction_chain_includes_parent_and_deepest_override(self):
        folder = self.root / "Shared/nested"
        folder.mkdir()
        (folder / "AGENTS.md").write_text("default")
        (folder / "AGENTS.override.md").write_text("override")
        result = self.workspace.route_one("Shared/nested/new.md")
        expected = [str(self.root / "AGENTS.md"), str(self.root / "Shared/AGENTS.md"),
                    str(folder / "AGENTS.override.md")]
        self.assertEqual(result["instructions"][-3:], expected)
        self.assertNotIn(str(folder / "AGENTS.md"), result["instructions"])

    def test_deleted_file_is_owned_by_child_and_committed_there(self):
        path = "Shared/README.md"
        self.plan([path], deletions=[path])
        (self.root / path).unlink()
        self.assertEqual(self.workspace.route_one(path)["repository"], "Shared")
        self.workspace.review({"Shared": {"Artifacts satisfy the task": "The tracked obsolete file is absent."}})
        self.workspace.commit([path], "Remove obsolete file")
        self.assertTrue(self.workspace.finish()["completed"])
        self.assertFalse(ws.git(self.root / "Shared", "ls-tree", "HEAD", "README.md"))
        self.assertTrue((self.root / "README.md").exists())

    def test_literal_paths_and_dependencies_publish_to_three_correct_remotes(self):
        paths = [":(glob)*.md", "Shared/with space.md", "Sibling/result.md"]
        self.plan(paths, depends_on={".": ["Sibling"], "Sibling": ["Shared"]})
        self.write_and_review(paths)
        committed = []
        original = ws.Workflow.commit

        def record(flow, selected, message):
            committed.append(flow.root.relative_to(self.root).as_posix())
            return original(flow, selected, message)

        with patch.object(ws.Workflow, "commit", new=record):
            self.workspace.commit(paths, "Add workspace artifacts")
        self.assertEqual(committed, ["Shared", "Sibling", "."])
        self.assertTrue(self.workspace.finish()["completed"])
        for name in (".", "Shared", "Sibling"):
            self.assertEqual(ws.git(self.root / name, "rev-parse", "HEAD"),
                             ws.git(self.root / name, "rev-parse", "origin/main"))
        self.assertNotIn("Shared/", ws.git(self.root, "ls-files"))
        self.assertIn(":(glob)*.md", ws.git(self.root, "ls-files"))

    def test_subset_commit_only_commits_requested_repository(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths)
        self.write_and_review(paths)
        head = ws.git(self.root, "rev-parse", "HEAD")
        result = self.workspace.commit([paths[1]], "Add child artifact")
        self.assertEqual(set(result["repositories"]), {"Shared"})
        self.assertEqual(ws.git(self.root, "rev-parse", "HEAD"), head)
        self.workspace.commit([paths[0]], "Add root artifact")
        self.assertTrue(self.workspace.finish()["completed"])

    def test_staged_work_in_later_child_blocks_entire_batch_and_is_preserved(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths)
        self.write_and_review(paths)
        child = self.root / "Shared"
        (child / "user.md").write_text("user work")
        ws.git(child, "add", "user.md")
        head = ws.git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ws.Blocked, "Index already"):
            self.workspace.commit(paths, "Add artifacts")
        self.assertEqual(ws.git(self.root, "rev-parse", "HEAD"), head)
        self.assertEqual(ws.git(child, "diff", "--cached", "--name-only"), "user.md")
        self.assertEqual((child / "user.md").read_text(), "user work")

    def test_preserve_index_publishes_and_finishes_three_repositories(self):
        staged = {}
        for name in (".", "Shared", "Sibling"):
            repo = self.root / name
            (repo / "README.md").write_text("staged draft\n")
            (repo / "user draft.md").write_text("unrelated whitespace   \n")
            (repo / "AGENTS.md").unlink()
            ws.git(repo, "add", "--all")
            (repo / "README.md").write_text("unstaged continuation\n")
            staged[name] = ws.git(repo, "diff", "--cached", "--binary")
        paths = [":(glob)*.md", "Shared/with space.md", "Sibling/answer.md"]
        self.plan(paths, depends_on={".": ["Sibling"], "Sibling": ["Shared"]})
        self.write_and_review(paths)
        result = self.workspace.commit(paths, "Add task artifacts", preserve_index=True)
        self.assertEqual(set(result["repositories"]), {".", "Shared", "Sibling"})
        self.assertTrue(self.workspace.finish()["completed"])
        for name, selected in zip((".", "Shared", "Sibling"), (":(glob)*.md", "with space.md", "answer.md")):
            repo = self.root / name
            self.assertEqual(ws.git(repo, "diff", "--cached", "--binary"), staged[name])
            self.assertEqual((repo / "README.md").read_text(), "unstaged continuation\n")
            self.assertEqual((repo / "user draft.md").read_text(), "unrelated whitespace   \n")
            self.assertFalse((repo / "AGENTS.md").exists())
            self.assertEqual(ws.git(repo, "diff", "HEAD^", "HEAD", "--name-only"), selected)

    def test_preserve_index_overlap_in_child_blocks_before_parent_commit(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths)
        self.write_and_review(paths)
        child = self.root / "Shared"
        ws.git(child, "add", "answer.md")
        before = ws.git(child, "diff", "--cached", "--binary")
        parent_head = ws.git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ws.Blocked, "overlap"):
            self.workspace.commit(paths, "Add artifacts", preserve_index=True)
        self.assertEqual(ws.git(self.root, "rev-parse", "HEAD"), parent_head)
        self.assertEqual(ws.git(child, "diff", "--cached", "--binary"), before)

    def test_preserve_index_cli_is_explicit_and_keeps_staging(self):
        child = self.root / "Shared"
        (child / "user.md").write_text("existing staging\n")
        ws.git(child, "add", "user.md")
        before = ws.git(child, "diff", "--cached", "--binary")
        self.plan(["Shared/answer.md"])
        self.write_and_review(["Shared/answer.md"])
        with self.assertRaisesRegex(ws.Blocked, "Index already"):
            self.workspace.commit(["Shared/answer.md"], "Add answer")
        argv = ["workspace.py", "--root", str(self.root), "--session", "test-workspace",
                "commit", "--preserve-index", "-m", "Add answer", "Shared/answer.md"]
        with patch.object(sys, "argv", argv), patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(ws.main(), 0)
        self.assertEqual(ws.git(child, "diff", "--cached", "--binary"), before)
        self.assertTrue(self.workspace.finish()["completed"])

    def test_preexisting_changes_require_adoption_and_are_preserved(self):
        path = self.root / "Shared/README.md"
        path.write_text("existing work\n")
        with self.assertRaisesRegex(ws.Blocked, "adopt_existing"):
            self.plan(["Shared/README.md"])
        self.assertEqual(path.read_text(), "existing work\n")
        self.plan(["Shared/README.md"], adopt_existing={"Shared/README.md": "User authorizes integrating the inspected draft."})
        self.assertEqual(self.workspace.status()["repositories"]["Shared"]["adoption"],
                         {"README.md": "User authorizes integrating the inspected draft."})

    def test_external_repo_requires_explicit_acceptance_but_route_does_not(self):
        self.assertEqual(self.workspace.route_one("External/new.md")["management"], "external")
        with self.assertRaisesRegex(ws.Blocked, "external_repositories"):
            self.plan(["External/new.md"])
        self.assertFalse((self.root / "External/.git/constellation").exists())
        self.plan(["External/new.md"], external_repositories=["External"])
        self.assertEqual(self.workspace.load()["roots"], ["External"])

    def test_unregistered_ignored_child_cannot_be_adopted_by_parent(self):
        self.make_repo("Unknown")
        self.assertEqual(self.workspace.route_one("Unknown/file.md")["management"], "unregistered")
        with self.assertRaisesRegex(ws.Blocked, "Register Git owner"):
            self.plan(["Unknown/file.md"])

    def test_missing_registered_git_boundary_does_not_fall_back_to_parent(self):
        (self.root / "Shared/.git").rename(self.base / "detached-child-git")
        with self.assertRaisesRegex(ws.Blocked, "lost its Git boundary"):
            self.workspace.route_one("Shared/README.md")

    def test_symlink_escape_and_private_paths_are_rejected(self):
        (self.root / "alias").symlink_to(self.root / "Shared", target_is_directory=True)
        for name in ("alias/README.md", "../outside.md", "/tmp/outside.md", "Shared/.git/config", "Shared/auth.json"):
            with self.subTest(name=name), self.assertRaises(ws.Blocked):
                self.plan([name])

    def test_cycle_fails_before_creating_any_contract(self):
        with self.assertRaisesRegex(ws.Blocked, "cycle"):
            self.plan(["answer.md", "Shared/answer.md"], depends_on={".": ["Shared"], "Shared": ["."]})
        self.assertFalse(self.workspace.path.exists())

    def test_dependency_must_be_published_before_dependent_subset(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths, depends_on={".": ["Shared"]})
        self.write_and_review(paths)
        with self.assertRaises(ws.Blocked):
            self.workspace.commit(["answer.md"], "Add parent")
        self.workspace.commit(["Shared/answer.md"], "Add dependency")
        self.workspace.commit(["answer.md"], "Add parent")
        self.assertTrue(self.workspace.finish()["completed"])

    def test_failed_child_publish_records_incomplete_and_preserves_parent(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths, depends_on={".": ["Shared"]})
        self.write_and_review(paths)
        hook = self.remotes["Shared"] / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        parent_head = ws.git(self.root, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ws.Blocked, "incomplete at Shared"):
            self.workspace.commit(paths, "Add artifacts")
        state = self.workspace.load()
        self.assertIsNone(state["finished"])
        self.assertEqual(state["error"]["repository"], "Shared")
        self.assertEqual(ws.git(self.root, "rev-parse", "HEAD"), parent_head)
        self.assertEqual(len(ws.Workflow(self.root / "Shared", "test-workspace").load()["commits"]), 1)
        hook.unlink()
        self.workspace.commit(paths, "Add artifacts")
        self.assertEqual(len(ws.Workflow(self.root / "Shared", "test-workspace").load()["commits"]), 1)
        self.assertTrue(self.workspace.finish()["completed"])

    def test_changed_child_destination_blocks_batch_before_parent_commit(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths)
        self.write_and_review(paths)
        parent_head = ws.git(self.root, "rev-parse", "HEAD")
        ws.git(self.root / "Shared", "config", "remote.origin.pushurl", str(self.remotes["Sibling"]))
        with self.assertRaises(ws.Blocked):
            self.workspace.commit(paths, "Add artifacts")
        self.assertEqual(ws.git(self.root, "rev-parse", "HEAD"), parent_head)

    def test_replan_after_partial_finish_retains_completed_child_history(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths, depends_on={".": ["Shared"]})
        self.write_and_review(paths)
        self.workspace.commit(paths, "Add artifacts")
        original = ws.Workflow.finish

        def finish(flow):
            if flow.root == self.root:
                raise ws.Blocked("Synthetic root failure")
            return original(flow)

        with patch.object(ws.Workflow, "finish", new=finish):
            with self.assertRaisesRegex(ws.Blocked, "Synthetic root failure"):
                self.workspace.finish()
        child = ws.Workflow(self.root / "Shared", "test-workspace")
        before = child.load()
        self.assertTrue(before["finished"])
        self.plan(paths, depends_on={".": ["Shared"]})
        after = child.load()
        self.assertEqual(after["initial_head"], before["initial_head"])
        self.assertEqual(after["commits"], before["commits"])

    def test_finish_cannot_ignore_dirty_child(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths)
        self.write_and_review(paths)
        self.workspace.commit(paths, "Add artifacts")
        (self.root / "Shared/forgotten.md").write_text("pending task file")
        with self.assertRaisesRegex(ws.Blocked, "scope review"):
            self.workspace.finish()
        self.assertIsNone(self.workspace.load()["finished"])

    def test_late_child_change_is_detected_after_other_repositories_finish(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths, depends_on={".": ["Shared"]})
        self.write_and_review(paths)
        self.workspace.commit(paths, "Add artifacts")
        original = ws.Workflow.finish

        def finish(flow):
            result = original(flow)
            if flow.root == self.root:
                (self.root / "Shared/late.md").write_text("late change")
            return result

        with patch.object(ws.Workflow, "finish", new=finish):
            with self.assertRaisesRegex(ws.Blocked, "scope review"):
                self.workspace.finish()
        self.assertIsNone(self.workspace.load()["finished"])

    def test_existing_contract_requires_explicit_extension_and_keeps_original_scope(self):
        flow = ws.Workflow(self.root / "Shared", "test-workspace")
        flow.begin("original")
        flow.plan({"requirements": ["Original goal"], "paths": ["original.md"]})
        with self.assertRaisesRegex(ws.Blocked, "extend_existing"):
            self.plan(["Shared/new.md"])
        self.assertEqual(flow.load()["requirements"], ["Original goal"])
        self.plan(["Shared/new.md"], extend_existing=True)
        self.assertEqual(flow.load()["paths"], ["original.md", "new.md"])
        self.assertEqual(flow.load()["requirements"], ["Original goal", "Artifacts satisfy the task"])

    def test_check_uses_selected_repo_and_persists_only_hashes(self):
        self.plan(["Shared/tool.py"])
        (self.root / "Shared/tool.py").write_text("print('OK')\n")
        sentinel = "PRIVATE_CHECK_COMMAND_SENTINEL"
        with patch("sys.stdout", new=io.StringIO()):
            self.workspace.check("Shared", [sys.executable, "-c", f"from pathlib import Path; assert Path('tool.py').is_file(); print('{sentinel}')"])
        self.workspace.review({"Shared": {"Artifacts satisfy the task": "Executed a passing check from the child repository."}})
        state = self.workspace.status()
        self.assertNotIn(sentinel, json.dumps(state))
        self.assertIn("command_sha256", json.dumps(state))

    def test_read_only_dependency_can_finish_without_previous_commit(self):
        self.plan(["README.md", "Shared/README.md"], depends_on={".": ["Shared"]})
        self.workspace.review({repo: {"Artifacts satisfy the task": "Read the unchanged tracked artifact."}
                               for repo in (".", "Shared")})
        self.assertTrue(self.workspace.finish()["completed"])

    def test_guard_routes_root_child_and_moves_under_each_contract(self):
        self.plan(["answer.md", "Shared/new.md", "Shared/moved.md"])
        body = ("*** Begin Patch\n*** Add File: answer.md\n+root\n"
                "*** Update File: Shared/new.md\n*** Move to: Shared/moved.md\n*** End Patch")
        self.workspace.guard_patch({"tool_input": {"command": body}}, self.root)
        self.workspace.guard_patch({"tool_input": "*** Begin Patch\n*** Add File: new.md\n+child\n*** End Patch"}, self.root / "Shared")
        for path in ("Shared/undeclared.md", "Sibling/new.md", str(self.base / "outside.md")):
            with self.subTest(path=path), self.assertRaises(ws.Blocked):
                self.workspace.guard_patch({"tool_input": f"*** Begin Patch\n*** Add File: {path}\n+x\n*** End Patch"}, self.root)

    def test_guard_rejects_recreating_declared_deletion(self):
        self.plan(["Shared/README.md"], deletions=["Shared/README.md"])
        for action in ("Add File", "Update File", "Move to"):
            with self.subTest(action=action), self.assertRaisesRegex(ws.Blocked, "only authorizes Delete File"):
                self.workspace.guard_patch({"tool_input": f"*** Begin Patch\n*** {action}: Shared/README.md\n*** End Patch"}, self.root)
        self.workspace.guard_patch({"tool_input": "*** Begin Patch\n*** Delete File: Shared/README.md\n*** End Patch"}, self.root)

    def test_stop_checks_every_child_without_publishing_and_is_bounded(self):
        paths = ["answer.md", "Shared/answer.md"]
        self.plan(paths)
        self.write_and_review(paths)
        with patch.object(ws.Workflow, "publish", side_effect=AssertionError("stop must not publish")):
            self.assertEqual(self.workspace.stop()["decision"], "block")
            self.assertEqual(self.workspace.stop()["decision"], "block")
            self.assertFalse(self.workspace.stop()["continue"])
        self.workspace.commit(paths, "Add artifacts")
        self.workspace.finish()
        self.assertEqual(self.workspace.stop(), {})
        (self.root / "Shared/forgotten.md").write_text("new task work")
        self.assertFalse(self.workspace.stop()["continue"])


if __name__ == "__main__":
    unittest.main()
