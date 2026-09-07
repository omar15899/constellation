#!/usr/bin/env python3
"""Regression checks for hook boundaries, using disposable Git repositories."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
ADAPTER = HOOKS.parent / "templates" / "codex_hook_shim.py"
# Synthetic fixtures are assembled so the test source contains no live-looking
# credential and never relies on personal credentials or repository contents.
SYNTHETIC = "ghp_" + "Example1234567890" * 2


class HookSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="constellation hooks ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo with spaces"
        self.repo.mkdir()
        self.git("init", "--quiet")

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=self.repo, capture_output=True, text=True, check=True,
        )

    def write(self, path: str, content: str) -> Path:
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return target

    def run_hook(
        self, name: str, data: object | None = None, *,
        extra_env: dict[str, str] | None = None, raw: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("LOOP_GUARD_DISABLE", None)
        env.pop("LOOP_GUARD_STRICT", None)
        if extra_env:
            env.update(extra_env)
        executable = "bash" if name.endswith(".sh") else sys.executable
        return subprocess.run(
            [executable, str(HOOKS / name)],
            input=raw if raw is not None else json.dumps(data or {}),
            cwd=self.repo, capture_output=True, text=True, env=env, timeout=20,
        )

    def event(self, path: str, content: str | None = None, *, post: bool = False) -> dict:
        tool_input = {"file_path": path}
        if content is not None:
            tool_input["content"] = content
        return {
            "cwd": str(self.repo), "hook_event_name": "PostToolUse" if post else "PreToolUse",
            "tool_name": "Write", "tool_input": tool_input,
        }

    def run_patch_hook(self, name: str, patch: str, *, post: bool = False) -> subprocess.CompletedProcess[str]:
        data = {
            "cwd": str(self.repo), "event": "PostToolUse" if post else "PreToolUse",
            "tool_name": "functions.apply_patch", "tool_input": {"command": patch},
        }
        return subprocess.run(
            [sys.executable, str(ADAPTER), "--project-dir", str(self.repo),
             "--", "bash", str(HOOKS / name)],
            input=json.dumps(data), cwd=self.repo, text=True, capture_output=True, timeout=20,
        )

    def assert_blocked_without_value(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn(SYNTHETIC, result.stdout + result.stderr)

    def test_pending_write_is_checked_before_file_exists(self) -> None:
        result = self.run_hook("secret_scan.sh", self.event("new file.py", SYNTHETIC))
        self.assert_blocked_without_value(result)
        self.assertFalse((self.repo / "new file.py").exists())

    def test_pending_edit_and_multiedit_are_checked(self) -> None:
        for values in ({"new_string": SYNTHETIC}, {"edits": [{"new_string": SYNTHETIC}]}):
            with self.subTest(values=list(values)):
                event = self.event("edited.py")
                event["tool_input"].update(values)
                self.assert_blocked_without_value(self.run_hook("secret_scan.sh", event))

    def test_post_checks_full_file_even_with_clean_pending_fragment(self) -> None:
        self.write("result.py", SYNTHETIC)
        event = self.event("result.py", "clean fragment", post=True)
        self.assert_blocked_without_value(self.run_hook("secret_scan.sh", event))

    def test_index_secret_survives_clean_working_copy_or_removed_file(self) -> None:
        target = self.write("staged file.py", SYNTHETIC)
        self.git("add", "--", target.name)
        target.write_text("value = 1\n")
        self.assert_blocked_without_value(self.run_hook("secret_scan.sh"))
        target.unlink()
        self.assert_blocked_without_value(self.run_hook("secret_scan.sh"))

    def test_clean_index_does_not_read_unstaged_secret(self) -> None:
        target = self.write("staged.py", "value = 1\n")
        self.git("add", "--", target.name)
        target.write_text(SYNTHETIC)
        result = self.run_hook("secret_scan.sh")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_protected_names_are_refused_before_open(self) -> None:
        for name in (".env", ".env.local", ".environment", "server.pem", "server.key", "credentials.json"):
            with self.subTest(name=name):
                # FIFO contents would hang if the gate tried to read them.
                target = self.repo / name
                os.mkfifo(target)
                result = self.run_hook("secret_scan.sh", self.event(name, post=True))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("contents were not read", result.stderr)

    def test_symlink_to_protected_target_is_refused(self) -> None:
        target = self.write(".env.local", SYNTHETIC)
        (self.repo / "safe.txt").symlink_to(target)
        result = self.run_hook("secret_scan.sh", self.event("safe.txt", post=True))
        self.assert_blocked_without_value(result)
        self.assertIn("contents were not read", result.stderr)

    def test_staged_protected_file_is_not_read_as_blob(self) -> None:
        self.write("credentials.json", "fixture only\n")
        self.git("add", "--", "credentials.json")
        trace = self.root / "git trace"
        result = self.run_hook("secret_scan.sh", extra_env={"GIT_TRACE": str(trace)})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("contents were not read", result.stderr)
        self.assertNotIn("cat-file", trace.read_text())

    def test_private_archive_paths_are_blocked_before_any_blob_read(self) -> None:
        paths = (
            "_conversations/example.json", ".codex/sessions/example.jsonl",
            ".codex/archived_sessions/example.jsonl", "rollout-example.jsonl",
            ".claude/run/example.jsonl",
        )
        for path in paths:
            self.write(path, "synthetic fixture only\n")
            self.git("add", "--", path)
            result = self.run_hook("secret_scan.sh", self.event(path, post=True))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("contents were not read", result.stderr)
        trace = self.root / "private path trace"
        result = self.run_hook("secret_scan.sh", extra_env={"GIT_TRACE": str(trace)})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn("cat-file", trace.read_text())

    def test_research_manifests_remain_allowed(self) -> None:
        self.write("research/manifest.json", '{"artifact": "metrics.json"}\n')
        self.git("add", "--", "research/manifest.json")
        result = self.run_hook("secret_scan.sh", self.event("research/manifest.json", post=True))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_symlink_parent_traversal_resolves_before_privacy_check(self) -> None:
        folder = self.repo / ".codex" / "sessions" / "folder"
        folder.mkdir(parents=True)
        self.write(".codex/sessions/entry.jsonl", "synthetic fixture only\n")
        (self.repo / "alias").symlink_to(folder, target_is_directory=True)
        path = "alias/../entry.jsonl"
        direct = self.run_hook("secret_scan.sh", self.event(path, post=True))
        self.assertEqual(direct.returncode, 2, direct.stderr)
        patch = "\n".join([
            "*** Begin Patch", f"*** Update File: {path}", "@@", "+fixture", "*** End Patch",
        ])
        adapted = self.run_patch_hook("secret_scan.sh", patch, post=True)
        self.assertEqual(adapted.returncode, 2, adapted.stderr)
        self.assertIn("contents were not read", adapted.stderr)

    def test_index_paths_with_newlines_and_tabs_are_preserved(self) -> None:
        name = "odd\nname\tfile.py"
        self.write(name, SYNTHETIC)
        self.git("add", "--", name)
        self.assert_blocked_without_value(self.run_hook("secret_scan.sh"))

    def test_native_multipatch_scans_renamed_file_after_clean_added_file(self) -> None:
        patch = "\n".join([
            "*** Begin Patch", "*** Add File: clean new.py", "+value = 1",
            "*** Update File: old file.py", "*** Move to: new file.py", "@@",
            "-old value", "+" + SYNTHETIC, "*** End Patch",
        ])
        result = self.run_patch_hook("secret_scan.sh", patch)
        self.assert_blocked_without_value(result)
        self.assertIn("new file.py", result.stderr)

    def test_native_patch_only_removed_secret_is_not_rescanned(self) -> None:
        self.write("old.py", SYNTHETIC)
        patch = "\n".join([
            "*** Begin Patch", "*** Update File: old.py", "@@", "-" + SYNTHETIC,
            "+value = 1", "*** End Patch",
        ])
        result = self.run_patch_hook("secret_scan.sh", patch)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_patch_rename_checks_protected_destination_and_source(self) -> None:
        for source, destination in (("old.py", "credentials.json"), (".env.local", "new.py")):
            with self.subTest(source=source, destination=destination):
                patch = "\n".join([
                    "*** Begin Patch", f"*** Update File: {source}", f"*** Move to: {destination}",
                    "@@", "+value = 1", "*** End Patch",
                ])
                result = self.run_patch_hook("secret_scan.sh", patch)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("contents were not read", result.stderr)

    def test_native_post_patch_scans_full_renamed_destination(self) -> None:
        self.write("new file.py", SYNTHETIC)
        patch = "\n".join([
            "*** Begin Patch", "*** Update File: old file.py", "*** Move to: new file.py",
            "@@", "+# clean insertion", "*** End Patch",
        ])
        result = self.run_patch_hook("secret_scan.sh", patch, post=True)
        self.assert_blocked_without_value(result)

    def test_native_post_multipatch_checks_second_untracked_python_file(self) -> None:
        self.write("first file.py", "value = 1\n")
        self.write("second file.py", "def incomplete(\n")
        patch = "\n".join([
            "*** Begin Patch", "*** Add File: first file.py", "+value = 1",
            "*** Add File: second file.py", "+def incomplete(", "*** End Patch",
        ])
        result = self.run_patch_hook("changed_python_syntax.sh", patch, post=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("second file.py", result.stderr)

    def test_large_content_fails_instead_of_silently_truncating(self) -> None:
        self.write("large.txt", "a" * 5_000_001)
        result = self.run_hook("secret_scan.sh", self.event("large.txt", post=True))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("could not finish", result.stderr)

    def test_invalid_events_are_visible_and_sanitized(self) -> None:
        for name in ("secret_scan.sh", "changed_python_syntax.sh", "loop_guard.py"):
            with self.subTest(name=name):
                result = self.run_hook(name, raw="invalid " + SYNTHETIC)
                self.assert_blocked_without_value(result)

    def test_failed_git_inspection_is_not_mistaken_for_nonrepository(self) -> None:
        fake_bin = self.root / "fake bin"
        fake_bin.mkdir()
        fake_git = fake_bin / "git"
        fake_git.write_text("#!/bin/sh\nexit 42\n")
        fake_git.chmod(0o755)
        for name in ("secret_scan.sh", "changed_python_syntax.sh", "loop_guard.py"):
            with self.subTest(name=name):
                result = self.run_hook(name, extra_env={"PATH": str(fake_bin) + os.pathsep + os.environ["PATH"]})
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_untracked_python_is_checked_without_bytecode_or_execution(self) -> None:
        content = "from pathlib import Path\nPath('executed').touch()\n"
        self.write("new script.py", content)
        event = self.event("new script.py", post=True)
        result = self.run_hook("changed_python_syntax.sh", event)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.repo / "executed").exists())
        self.assertEqual(list(self.repo.rglob("*.pyc")), [])
        self.assertEqual(list(self.repo.rglob("__pycache__")), [])

    def test_syntax_error_does_not_print_source(self) -> None:
        self.write("invalid file.py", "def broken(" + SYNTHETIC + "\n")
        result = self.run_hook("changed_python_syntax.sh", self.event("invalid file.py", post=True))
        self.assert_blocked_without_value(result)
        self.assertIn("SYNTAX ERROR", result.stderr)

    def test_staged_python_is_checked_even_when_working_copy_fixed(self) -> None:
        target = self.write("staged file.py", "def broken(\n")
        self.git("add", "--", target.name)
        target.write_text("value = 1\n")
        result = self.run_hook("changed_python_syntax.sh")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("index:", result.stderr)

    def test_unrelated_untracked_python_is_not_checked(self) -> None:
        self.write("someone elses.py", "def broken(\n")
        self.write("mine.py", "value = 1\n")
        result = self.run_hook("changed_python_syntax.sh", self.event("mine.py", post=True))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_syntax_check_does_not_follow_protected_symlink(self) -> None:
        target = self.repo / ".env.private"
        os.mkfifo(target)
        (self.repo / "alias.py").symlink_to(target)
        result = self.run_hook("changed_python_syntax.sh", self.event("alias.py", post=True))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Skipped protected", result.stderr)

    def test_stop_does_not_read_transcript_and_uses_message(self) -> None:
        transcript = self.root / "private transcript"
        os.mkfifo(transcript)
        data = {
            "transcript_path": str(transcript),
            "last_assistant_message": "The requested implementation is complete. " * 3,
        }
        result = self.run_hook("loop_guard.py", data)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("advisory", result.stderr)
        strict = self.run_hook("loop_guard.py", data, extra_env={"LOOP_GUARD_STRICT": "1"})
        self.assertEqual(strict.returncode, 2, strict.stderr)

    def test_stop_reuses_index_gate_and_honors_reentry(self) -> None:
        self.write("config.txt", SYNTHETIC)
        self.git("add", "--", "config.txt")
        self.assert_blocked_without_value(self.run_hook("loop_guard.py"))
        result = self.run_hook("loop_guard.py", {"stop_hook_active": True})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stop_does_not_block_on_unrelated_todos(self) -> None:
        self.write(".claude/hooks/unrelated.py", "# TODO: another task owns this\n")
        result = self.run_hook("loop_guard.py", {"last_assistant_message": "TODO: documented next step"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("advisory", result.stderr)


if __name__ == "__main__":
    unittest.main()
