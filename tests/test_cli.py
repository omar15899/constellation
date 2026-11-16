"""Exercise the shipped command and native Git hooks against temporary owners."""

import json
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1]


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "owner"
        self.root.mkdir()
        self.remote = self.base / "remote.git"
        self.state = self.base / "state"
        self.env = dict(os.environ, CONSTELLATION_STATE_DIR=str(self.state),
                        PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"])
        self.git("init", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        (self.root / "note.txt").write_text("base\n")
        (self.root / "foreign.txt").write_text("foreign base\n")
        self.git("add", ".")
        self.git("commit", "-m", "Initial fixture")
        self.git("init", "--bare", str(self.remote))
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "main")
        self.git("config", "core.hooksPath", str(SOURCE / "git-hooks"))

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args], env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def command(self, *args, payload=None, code=0):
        result = subprocess.run([sys.executable, str(SOURCE / "constellation.py"),
                                 "--state-dir", str(self.state), *args], cwd=self.root,
                                env=self.env, input=json.dumps(payload) if payload is not None else None,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, code, result.stderr + result.stdout)
        return json.loads(result.stdout) if code == 0 else result

    def begin(self, mode="publish"):
        return self.command("begin", "change", payload={
            "root": str(self.root), "requirement": "Edit note only", "mode": mode,
            "assignments": {"note.txt": "author-native-id"},
            "coordinator": "coordinator-native-id", "session_id": "fresh-session"})

    def check_and_review(self):
        record = self.command("check", "change", "default", "--", sys.executable,
                              "-c", "from pathlib import Path; assert Path('note.txt').read_text() == 'changed\\n'")
        self.assertEqual(record["status"], "passed")
        status = self.command("status", "change")
        self.assertFalse(status["gate"]["ready"])
        self.command("review", "change", payload={
            "reviewer": "reviewer-native-id", "evidence": "Read note diff and current behavior check",
            "expected_fingerprint": status["gate"]["fingerprint"]})
        self.assertTrue(self.command("status", "change")["gate"]["ready"])

    def test_command_lifecycle_runs_native_push_hook_and_preserves_foreign_staging(self):
        self.begin()
        (self.root / "note.txt").write_text("changed\n")
        (self.root / "foreign.txt").write_text("foreign staged\n")
        self.git("add", "foreign.txt")
        foreign = self.git("ls-files", "--stage", "foreign.txt")
        self.command("checkpoint", "change", payload={"summary": "Note ready for review"})
        self.check_and_review()
        sha = self.command("commit", "change", "Update the note")
        self.assertEqual(sha, self.git("rev-parse", "HEAD"))
        self.assertEqual(self.git("ls-files", "--stage", "foreign.txt"), foreign)
        self.assertEqual(self.git("show", "HEAD:foreign.txt"), "foreign base")
        self.assertEqual(self.command("push", "change"), sha)
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/main").split()[0], sha)
        self.assertEqual(self.command("status", "change")["publication"]["status"], "verified")
        rejected = subprocess.run(["git", "-C", str(self.root), "commit", "-m", "Unreviewed"],
                                  env=self.env, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("constellation commit", rejected.stderr)
        self.command("git-hook", "pre-push", "origin", code=2)

    def test_local_finish_and_skill_resource_optional_arguments(self):
        self.begin(mode="local")
        (self.root / "note.txt").write_text("changed\n")
        self.check_and_review()
        done = self.command("finish", "change")
        self.assertEqual(done["closed"]["kind"], "local")
        self.assertEqual(done["publication"], {})
        result = subprocess.run([sys.executable, str(SOURCE / "constellation.py"),
                                 "skill-run", "core", "fast-finder", "scripts/query.py", "--help"],
                                cwd=self.root, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        rejected = subprocess.run([sys.executable, str(SOURCE / "constellation.py"),
                                   "skill-run", "core", "fast-finder", "../../../constellation.py"],
                                  cwd=self.root, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(rejected.returncode, 2)

    def test_guard_status_requires_executable_native_hooks(self):
        source = (self.base / "source").resolve()
        (source / "profiles").mkdir(parents=True)
        hooks = source / "git-hooks"
        hooks.mkdir()
        (source / "profiles/projects.json").write_text(json.dumps({"projects": [
            {"root": str(self.root), "management": "native"}]}))
        for name in ("pre-commit", "pre-push"):
            (hooks / name).write_text("#!/bin/sh\nexit 0\n")
            (hooks / name).chmod(0o644)
        self.git("config", "core.hooksPath", str(hooks))
        spec = importlib.util.spec_from_file_location("command_entry_fixture", SOURCE / "constellation.py")
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
        for executable, code in ((False, 2), (True, 0)):
            for name in ("pre-commit", "pre-push"):
                (hooks / name).chmod(0o755 if executable else 0o644)
            output = io.StringIO()
            with patch.object(entry, "SOURCE", source), patch.object(sys, "argv", [
                    "constellation", "guard-status", "--root", str(self.root)]), contextlib.redirect_stdout(output):
                self.assertEqual(entry.main(), code)
            self.assertEqual(json.loads(output.getvalue())["verified"], executable)

    def test_failed_check_returns_nonzero_and_keeps_failed_evidence(self):
        self.begin()
        result = self.command("check", "change", "default", "--", sys.executable,
                              "-c", "raise SystemExit(7)", code=2)
        self.assertEqual(json.loads(result.stdout)["status"], "failed")
        status = self.command("status", "change")
        self.assertFalse(status["gate"]["ready"])
        self.assertEqual(status["checks"]["default"]["returncode"], 7)


if __name__ == "__main__":
    unittest.main()
