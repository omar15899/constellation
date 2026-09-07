#!/usr/bin/env python3
"""Temporary-repository tests for exact commit selection and index preservation."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research_committer as committer


class CommitterSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="committer fixture '")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        for name in ("scripts/ours.py", "scripts/other.py", "docs/user.md"):
            self.write(name, "value = 1\n")
        self.git("add", "--", "scripts/ours.py", "scripts/other.py", "docs/user.md")
        self.git("commit", "--quiet", "-m", "Fixture baseline")
        self.pol = {"id": "fixture", "conservative": False, "dry_run_only": False,
                    "checks": ["secret_scan"], "include": [], "exclude": [],
                    "allow_reports": False, "allow_artifacts": False, "auto_push": False}

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = committer.git(self.repo, *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def write(self, relative: str, content: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def args(self, **updates) -> SimpleNamespace:
        values = dict(apply=True, push=False, repo=["fixture"], path=["scripts/ours.py"],
                      scope=[], include_prestaged=False, run_class="diagnostic",
                      message_subject="Update selected fixture", context="Test fixture.",
                      lever="", task="", session="", allow_branch_mismatch=False)
        values.update(updates)
        return SimpleNamespace(**values)

    def process(self, **updates) -> dict:
        return committer.process_repo(self.repo, self.pol, self.args(**updates))

    def index(self) -> str:
        return self.git("ls-files", "--stage", "-z").stdout

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").stdout

    def committed_paths(self) -> list[str]:
        return [path for path in self.git("diff-tree", "--root", "--no-commit-id",
                "--name-only", "--no-renames", "-r", "-z", "HEAD").stdout.split("\0") if path]

    def test_exact_path_does_not_commit_other_changes_in_the_same_scope(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        self.write("scripts/other.py", "value = 3\n")
        result = self.process()
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.committed_paths(), ["scripts/ours.py"])
        self.assertEqual(self.git("show", "HEAD:scripts/other.py").stdout, "value = 1\n")
        self.assertEqual((self.repo / "scripts/other.py").read_text(), "value = 3\n")
        self.assertEqual(self.git("diff", "--cached", "--name-only").stdout, "")

    def test_directory_to_skill_symlink_commits_only_selected_paths(self) -> None:
        self.write(".codex/skills/check/SKILL.md", "Old generated command\n")
        self.git("add", "--", ".codex/skills/check/SKILL.md")
        self.git("commit", "--quiet", "-m", "Fixture command")
        self.write(".claude/skills/check/SKILL.md", "Canonical skill\n")
        self.git("add", "--", ".claude/skills/check/SKILL.md")
        self.git("commit", "--quiet", "-m", "Fixture canonical skill")
        old = self.repo / ".codex/skills/check/SKILL.md"
        old.unlink()
        old.parent.rmdir()
        old.parent.symlink_to("../../.claude/skills/check")
        paths = [".codex/skills/check", ".codex/skills/check/SKILL.md"]
        result = self.process(path=paths)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(set(self.committed_paths()), set(paths))
        self.assertEqual(self.git("status", "--porcelain").stdout, "")

    def test_control_plane_policy_covers_projection_without_private_runtime(self) -> None:
        policy = committer.load_policy()["repos"]["constellation"]
        for relative in ("AGENTS.md", ".codex/skills/check", ".codex/agents/audit.toml",
                         ".codex/hook_shim.py", ".codex/MANIFEST.json",
                         ".claude/templates/importlinter.template"):
            with self.subTest(relative=relative):
                self.assertTrue(committer.included(relative, policy))
                self.assertNotEqual(committer.classify_scope(relative), "unknown")
        for relative in (".codex/sessions/session.jsonl", ".codex/local/private.md",
                         ".codex/log/daemon.log", "_conversations/archive.md"):
            self.assertFalse(committer.included(relative, policy), relative)

    def test_workflow_todo_check_distinguishes_fixtures_from_actionable_notes(self) -> None:
        relative = ".claude/tests/test_example.py"
        cases = (
            ('payload = "TODO: intentionally unfinished test input"\n', True),
            ('# TODO: finish implementation\nvalue = 1\n', False),
            ('def example():\n    """FIXME: finish implementation."""\n    return 1\n', False),
        )
        for content, expected in cases:
            with self.subTest(expected=expected, content=content):
                self.write(relative, content)
                self.git("add", "--", relative)
                ok, detail = committer.check_no_workflow_todos(self.repo, [relative], None, self.pol)
                self.assertEqual(ok, expected, detail)

    def test_dry_run_preserves_real_index_and_head(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        self.write("docs/user.md", "User staged work\n")
        self.git("add", "--", "docs/user.md")
        before = self.index(), self.head(), (self.repo / ".git/index").read_bytes()
        result = self.process(apply=False, include_prestaged=True)
        self.assertEqual(result["status"], "dry-run", result)
        self.assertEqual((self.index(), self.head(), (self.repo / ".git/index").read_bytes()), before)

    def test_default_refuses_any_prestaged_work(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        self.write("docs/user.md", "User staged work\n")
        self.git("add", "--", "docs/user.md")
        before = self.index(), self.head()
        result = self.process()
        self.assertEqual(result["status"], "ABORTED")
        self.assertEqual((self.index(), self.head()), before)

    def test_filtered_apply_preserves_unrelated_staged_hunks_and_paths(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        self.write("scripts/other.py", "value = 3\n")
        self.git("add", "--", "scripts/other.py")
        self.write("scripts/other.py", "value = 4\n")
        self.write("docs/user.md", "User staged work\n")
        self.git("add", "--", "docs/user.md")
        untouched = committer.index_entries(self.repo, ["scripts/other.py", "docs/user.md"])
        result = self.process(include_prestaged=True, scope=["scripts"])
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.committed_paths(), ["scripts/ours.py"])
        self.assertEqual(committer.index_entries(self.repo, ["scripts/other.py", "docs/user.md"]),
                         untouched)
        self.assertEqual((self.repo / "scripts/other.py").read_text(), "value = 4\n")
        self.assertEqual(self.git("diff", "--cached", "--name-only", "--no-renames").stdout,
                         "docs/user.md\nscripts/other.py\n")

    def test_include_prestaged_refuses_selected_partial_file(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        self.git("add", "--", "scripts/ours.py")
        self.write("scripts/ours.py", "value = 3\n")
        before = self.index(), self.head()
        result = self.process(include_prestaged=True)
        self.assertIn("partially staged", result["commits"][0]["status"])
        self.assertEqual((self.index(), self.head()), before)
        self.assertEqual((self.repo / "scripts/ours.py").read_text(), "value = 3\n")

    def test_include_prestaged_accepts_selected_complete_file(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        self.git("add", "--", "scripts/ours.py")
        result = self.process(include_prestaged=True)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.committed_paths(), ["scripts/ours.py"])
        self.assertEqual(self.git("diff", "--cached", "--name-only").stdout, "")

    def test_path_selection_intersects_scope_and_policy(self) -> None:
        for name in ("scripts/ours.py", "scripts/other.py", "docs/user.md"):
            self.write(name, "value = 9\n")
        self.pol["include"] = ["scripts/"]
        self.pol["exclude"] = ["scripts/other.py"]
        result = self.process(path=["scripts/ours.py", "scripts/other.py", "docs/user.md"],
                              scope=["scripts"])
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.committed_paths(), ["scripts/ours.py"])

    def test_literal_glob_characters_do_not_select_other_files(self) -> None:
        self.write("scripts/a * [one].py", "value = 2\n")
        self.write("scripts/abc.py", "value = 3\n")
        result = self.process(path=["scripts/a * [one].py"])
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.committed_paths(), ["scripts/a * [one].py"])
        self.assertIn("scripts/abc.py", self.git("ls-files", "--others", "--exclude-standard").stdout)

    def test_selected_deletion_preserves_unrelated_staged_content(self) -> None:
        (self.repo / "scripts/ours.py").unlink()
        self.write("docs/user.md", "User staged work\n")
        self.git("add", "--", "docs/user.md")
        before = committer.index_entries(self.repo, ["docs/user.md"])
        result = self.process(include_prestaged=True)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.committed_paths(), ["scripts/ours.py"])
        self.assertEqual(committer.index_entries(self.repo, ["docs/user.md"]), before)
        self.assertNotIn("scripts/ours.py", self.git("ls-files").stdout)

    def test_one_side_of_a_staged_rename_does_not_commit_or_unstage_the_other(self) -> None:
        self.git("mv", "scripts/ours.py", "scripts/new.py")
        result = self.process(path=["scripts/new.py"], include_prestaged=True)
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(self.committed_paths(), ["scripts/new.py"])
        self.assertEqual(self.git("show", "HEAD:scripts/ours.py").stdout, "value = 1\n")
        self.assertEqual(self.git("diff", "--cached", "--name-only", "--no-renames").stdout,
                         "scripts/ours.py\n")

    def test_unborn_branch_seeds_empty_index_and_commits_only_selection(self) -> None:
        unborn = self.repo / "unborn"
        unborn.mkdir()
        result = committer.git(unborn, "init", "--quiet")
        self.assertEqual(result.returncode, 0)
        for key, value in (("user.name", "Fixture"), ("user.email", "fixture@example.invalid"),
                           ("commit.gpgsign", "false")):
            self.assertEqual(committer.git(unborn, "config", key, value).returncode, 0)
        (unborn / "README.md").write_text("Selected\n")
        (unborn / "other.md").write_text("Unselected\n")
        result = committer.process_repo(unborn, self.pol, self.args(path=["README.md"]))
        self.assertEqual(result["status"], "committed", result)
        self.assertEqual(committer.git(unborn, "ls-tree", "--name-only", "HEAD").stdout, "README.md\n")

    def test_temp_index_creation_failure_never_falls_back_to_real_index(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        before = self.index(), self.head()
        real_git = committer.git
        seen = []
        def observe(repo, *args, **kwargs):
            seen.append((args, kwargs.get("index_file")))
            return real_git(repo, *args, **kwargs)
        with patch.object(committer.tempfile, "mkstemp", side_effect=OSError("synthetic temp failure")), \
                patch.object(committer, "git", observe):
            result = self.process()
        self.assertIn("BLOCKED", result["commits"][0]["status"])
        self.assertFalse(any(args[0] in {"add", "commit", "reset"} for args, _ in seen))
        self.assertEqual((self.index(), self.head()), before)

    def test_read_tree_or_git_add_failure_aborts_without_committing_or_resetting(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        real_git = committer.git
        for failed_command in ("read-tree", "add"):
            with self.subTest(command=failed_command):
                before = self.index(), self.head()
                seen = []
                def fail(repo, *args, **kwargs):
                    seen.append((args, kwargs.get("index_file")))
                    if args[0] == failed_command:
                        return subprocess.CompletedProcess(args, 128, "", "synthetic failure")
                    return real_git(repo, *args, **kwargs)
                with patch.object(committer, "git", fail):
                    result = self.process()
                self.assertIn("BLOCKED", result["commits"][0]["status"])
                self.assertFalse(any(args[0] in {"commit", "reset"} for args, _ in seen))
                self.assertTrue(all(index for args, index in seen if args[0] in {"read-tree", "add"}))
                self.assertEqual((self.index(), self.head()), before)

    def test_scoped_index_sync_failure_is_reported_without_global_reset(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        self.write("docs/user.md", "User staged work\n")
        self.git("add", "--", "docs/user.md")
        before = self.index()
        real_git = committer.git
        reset_calls = []
        def fail_reset(repo, *args, **kwargs):
            if args[0] == "reset":
                reset_calls.append(args)
                return subprocess.CompletedProcess(args, 128, "", "synthetic index lock")
            return real_git(repo, *args, **kwargs)
        with patch.object(committer, "git", fail_reset):
            result = self.process(include_prestaged=True)
        self.assertIn("INDEX SYNC FAILED", result["commits"][0]["status"])
        self.assertEqual(reset_calls, [("reset", "-q", "HEAD", "--", "scripts/ours.py")])
        self.assertEqual(self.index(), before)
        self.assertEqual(self.committed_paths(), ["scripts/ours.py"])

    def test_directory_and_traversal_selectors_are_rejected(self) -> None:
        before = self.index(), self.head()
        self.assertEqual(self.process(path=["scripts"])["status"], "ABORTED")
        for value in ("", ".", "..", "../other.py", "/absolute.py", "a/../b.py",
                      "./scripts/ours.py", "scripts//ours.py", "scripts/", ".git/index"):
            with self.subTest(path=value), self.assertRaises(argparse.ArgumentTypeError):
                committer.exact_path(value)
        self.assertEqual((self.index(), self.head()), before)

    def test_cli_path_requires_exactly_one_explicit_repo(self) -> None:
        script = Path(committer.__file__)
        for selection in ([], ["--repo", "first", "--repo", "second"]):
            result = subprocess.run([sys.executable, str(script), "--path", "file.py", *selection],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires exactly one", result.stderr)

    def test_include_prestaged_requires_explicit_paths(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        self.git("add", "--", "scripts/ours.py")
        before = self.index(), self.head()
        result = self.process(path=[], include_prestaged=True)
        self.assertEqual(result["status"], "ABORTED")
        self.assertEqual((self.index(), self.head()), before)

    def test_ambient_index_is_ignored_and_never_mutated(self) -> None:
        self.write("scripts/ours.py", "value = 2\n")
        self.write("scripts/other.py", "value = 3\n")
        foreign = committer.temp_index_for(self.repo)
        self.addCleanup(lambda: Path(foreign).unlink(missing_ok=True))
        result = committer.git(self.repo, "add", "--", "scripts/other.py", index_file=foreign)
        self.assertEqual(result.returncode, 0)
        foreign_before = Path(foreign).read_bytes()
        original = self.index(), self.head()
        with patch.dict(os.environ, {"GIT_INDEX_FILE": foreign}):
            result = self.process(apply=False)
        self.assertEqual(result["status"], "dry-run", result)
        self.assertEqual(Path(foreign).read_bytes(), foreign_before)
        self.assertEqual((self.index(), self.head()), original)


if __name__ == "__main__":
    unittest.main()
