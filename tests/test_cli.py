"""Exercise the shipped command and native Git hooks against temporary owners."""

import json
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import stat
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

    def begin(self, mode="publish", code=0, **options):
        return self.command("begin", "change", code=code, payload={
            "root": str(self.root), "requirement": "Edit note only", "mode": mode,
            "assignments": {"note.txt": "author-native-id"},
            "coordinator": "coordinator-native-id", "session_id": "fresh-session", **options})

    @unittest.skipUnless(os.name == "posix", "Local note creation uses the POSIX ledger lock")
    def test_save_note_creates_only_unowned_notes_with_read_only_registry(self):
        self.env["CONSTELLATION_PROJECTS_FILE"] = str(self.base / "projects.json")
        Path(self.env["CONSTELLATION_PROJECTS_FILE"]).write_text(
            json.dumps({"projects": {"omaros": str(self.root.resolve())}}), encoding="utf-8")
        area = "06_Knowledge_Base/Mathematics"
        private = f"{area}/Finance/ENGIE/Private/Topics"
        for directory in (area, private, "03_Work"):
            (self.root / directory).mkdir(parents=True)
        create = f"{area}/new.md"
        reserved = f"{area}/reserved.md"
        self.begin(mode="local", assignments={reserved: "author-native-id"})

        record = self.state / "tasks/change.json"
        protected = (self.state, self.state / "tasks", self.state / ".lock", record)
        for directory in protected[:2]:
            directory.chmod(0o500)
            self.addCleanup(directory.chmod, 0o700)
        protected[2].chmod(0o400)
        record.chmod(0o400)
        before = [(p.stat().st_mtime_ns, stat.S_IMODE(p.stat().st_mode)) for p in protected]
        before_record = record.read_bytes()
        content = "# Valoración\n".encode("utf-8")

        def save(name, body=content):
            return subprocess.run([sys.executable, str(SOURCE / "constellation.py"),
                                   "save-note", name], cwd=self.root, env=self.env,
                                  input=body, capture_output=True, timeout=30)

        result = save(create)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(json.loads(result.stdout)["status"], "saved")
        self.assertEqual((self.root / create).read_bytes(), content)

        self.assertEqual(save(create, b"# Different\n").returncode, 2)
        self.assertEqual((self.root / create).read_bytes(), content)
        result = save(reserved)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"unfinished task", result.stderr)
        self.assertFalse((self.root / reserved).exists())

        for rejected in (f"{area}/AGENTS.md", f"{area}/nested/missing.md",
                         "03_Work/note.md", f"{private}/note.md"):
            with self.subTest(rejected=rejected):
                self.assertEqual(save(rejected).returncode, 2)
                self.assertFalse((self.root / rejected).exists())
        self.assertEqual(save(f"{area}/invalid.md", b"\xff").returncode, 2)
        self.assertFalse((self.root / f"{area}/invalid.md").exists())
        self.assertEqual(before, [(p.stat().st_mtime_ns, stat.S_IMODE(p.stat().st_mode))
                                  for p in protected])
        self.assertEqual(record.read_bytes(), before_record)
        self.assertEqual(sorted(p.name for p in (self.root / area).iterdir()), ["Finance", "new.md"])

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

    def test_final_opted_review_publishes_exact_sha_through_native_hooks(self):
        if os.name == "posix":
            source_alias = self.base / "source-alias"
            source_alias.symlink_to(SOURCE, target_is_directory=True)
            self.git("config", "core.hooksPath", str(source_alias / "git-hooks"))
        message = "Update the reviewed note"
        self.begin(publication_message=message)
        initial = self.git("rev-parse", "HEAD")
        (self.root / "note.txt").write_text("changed\n")
        (self.root / "foreign.txt").write_text("foreign staged\n")
        self.git("add", "foreign.txt")
        foreign = self.git("ls-files", "--stage", "foreign.txt")

        def review(reviewer="reviewer-native-id", verdict="approve"):
            status = self.command("status", "change")
            return self.command("review", "change", payload={
                "reviewer": reviewer, "verdict": verdict, "evidence": "Read the exact patch and evidence",
                "expected_fingerprint": status["gate"]["fingerprint"]})

        self.assertNotIn("publication", review())
        self.command("check", "change", "default", "--", sys.executable, "-c",
                     "from pathlib import Path; assert Path('note.txt').read_text() == 'changed\\n'")
        self.assertNotIn("publication", review(verdict="reject"))
        self.assertNotIn("publication", review(reviewer="second-independent-reviewer"))
        self.assertEqual(initial, self.git("rev-parse", "HEAD"))
        self.assertEqual(initial, self.git("ls-remote", "origin", "refs/heads/main").split()[0])

        publication = review()["publication"]
        sha = self.git("rev-parse", "HEAD")
        self.assertEqual(publication, {"commit": sha, "status": "verified"})
        self.assertEqual(sha, self.git("ls-remote", "origin", "refs/heads/main").split()[0])
        self.assertEqual(message, self.git("log", "-1", "--format=%s"))
        self.assertEqual("note.txt", self.git("diff-tree", "--no-commit-id", "--name-only", "-r", sha))
        self.assertEqual(foreign, self.git("ls-files", "--stage", "foreign.txt"))
        self.assertEqual(sha, self.command("publish", "change"))
        self.assertEqual("closed", self.command("status", "change")["status"])

    def test_local_finish_and_skill_resource_optional_arguments(self):
        rejected = self.begin(mode="local", publication_message="Publish a private task", code=2)
        self.assertIn("requires publish mode", rejected.stderr)
        self.begin(mode="local")
        self.assertIn("A local task cannot publish",
                      self.command("publish", "change", "Publish a private task", code=2).stderr)
        (self.root / "note.txt").write_text("changed\n")
        self.check_and_review()
        done = self.command("finish", "change")
        self.assertEqual(done["closed"]["kind"], "local")
        self.assertEqual(done["publication"], {})
        result = subprocess.run([sys.executable, str(SOURCE / "constellation.py"),
                                 "skill-run", "omaros", "fast-finder", "scripts/query.py", "--help"],
                                cwd=self.root, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage:", result.stdout)
        rejected = subprocess.run([sys.executable, str(SOURCE / "constellation.py"),
                                   "skill-run", "omaros", "fast-finder", "../../../constellation.py"],
                                  cwd=self.root, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(rejected.returncode, 2)

    def engie_fixture(self):
        source = self.base / "source"
        shutil.copytree(SOURCE / "constellation", source / "constellation",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(SOURCE / "constellation.py", source / "constellation.py")
        (source / "resources").mkdir()
        shutil.copyfile(SOURCE / "resources/vault.py", source / "resources/vault.py")
        root = self.root.resolve()
        owner, gitdir = root.stat(), (root / ".git").stat()
        (source / "profiles").mkdir()
        (source / "profiles/projects.json").write_text(json.dumps({"projects": [{
            "id": "omaros", "root": str(root), "management": "native",
            "filesystem_identity": {"owner": [owner.st_dev, owner.st_ino],
                                    "git_dir": [gitdir.st_dev, gitdir.st_ino]}}]}))
        private = "06_Knowledge_Base/Mathematics/Finance/ENGIE/Private"
        (root / ".git/info/exclude").write_text(f"/{private}/\n")
        general = self.base / "default-ledger"
        environment = dict(self.env)
        for name in ("CONSTELLATION_STATE_DIR", "CONSTELLATION_PROJECTS_FILE"):
            environment.pop(name, None)
        launcher = """
import runpy
import sys
from pathlib import Path

source = Path(sys.argv[1])
sys.path.insert(0, str(source.parent))
from constellation import platform_support

fixture_ledger = Path(sys.argv[2])
platform_support.default_state_dir = lambda home=None: fixture_ledger
sys.argv = [str(source), *sys.argv[3:]]
runpy.run_path(str(source), run_name='__main__')
"""

        def run(*args, payload=None, code=0):
            result = subprocess.run([sys.executable, "-B", "-c", launcher,
                                     str(source / "constellation.py"), str(general), *args],
                                    cwd=root, env=environment, capture_output=True, text=True,
                                    input=json.dumps(payload), timeout=30)
            self.assertEqual(result.returncode, code, result.stderr + result.stdout)
            return json.loads(result.stdout) if code == 0 else result.stderr

        return run, root, private, general

    @unittest.skipUnless(os.name == "posix", "Private capture is POSIX-only")
    def test_engie_learning_local_lifecycle_and_read_only_native_hooks(self):
        run, root, private, general = self.engie_fixture()
        topic, daily = f"{private}/Topics/onboarding.md", f"{private}/Daily/2026/2026-11-21.md"
        task = "engie-learning-fixture"
        owner, author = "fixture-owner-session", "fixture-native-author"
        contract = {"root": str(root), "requirement": "Record a synthetic learning event", "mode": "local",
                    "assignments": {topic: author, daily: author}, "coordinator": owner, "session_id": owner}
        self.assertEqual(run("hook", "stop", payload={"session_id": owner, "cwd": str(root)}), {})
        run("--engie-learning", "begin", task, payload=contract)
        ledger = root / private / ".learning/task-ledger"
        record = ledger / "tasks" / (task + ".json")
        for path in (ledger.parent, ledger, ledger / "tasks", ledger / ".lock", record):
            self.assertEqual(path.stat().st_mode & 0o077, 0)
        self.assertFalse(general.exists())
        self.assertFalse((root / ".git/constellation").exists())

        event = {"session_id": owner, "agent_id": author, "cwd": str(root),
                 "tool_name": "Write", "tool_input": {"file_path": topic}}
        self.assertEqual(run("hook", "pre-tool", payload=event), {})
        denied = run("hook", "pre-tool", payload={**event, "agent_id": "someone-else"})
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")
        copilot = {"sessionId": owner, "agentId": author, "cwd": str(root),
                   "toolName": "create", "toolArgs": {"path": daily}}
        self.assertEqual(run("hook", "--client", "copilot", "preToolUse", payload=copilot), {})
        self.assertIn(task, run("hook", "--client", "copilot", "sessionStart",
                                payload=copilot)["additionalContext"])
        self.assertIn(task, run("hook", "stop", payload=event)["reason"])

        for name in (topic, daily):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Synthetic note\n")
        check = run("--engie-learning", "check", task, "default", "--", sys.executable, "-c",
                    f"from pathlib import Path; assert Path({topic!r}).read_text() == 'Synthetic note\\n'")
        self.assertEqual(check["status"], "passed")
        status = run("--engie-learning", "status", task)
        run("--engie-learning", "review", task, payload={"reviewer": "fixture-reviewer",
            "evidence": "Compared synthetic scope and current check", "expected_fingerprint": status["gate"]["fingerprint"]})
        closed = run("--engie-learning", "finish", task)
        self.assertEqual(closed["closed"]["kind"], "local")
        self.assertEqual(run("hook", "stop", payload=event), {})
        self.assertFalse(general.exists())
        self.assertFalse((root / ".git/constellation").exists())

    @unittest.skipUnless(os.name == "posix", "Private capture is POSIX-only")
    def test_engie_learning_checks_legacy_reservations_and_private_boundaries(self):
        run, root, private, general = self.engie_fixture()
        topic, other = f"{private}/Topics/onboarding.md", f"{private}/Daily/unknown.md"
        ledger = root / private / ".learning/task-ledger"
        contract = {"root": str(root), "requirement": "Reserve a synthetic note", "mode": "local",
                    "assignments": {topic: "fixture-author"}, "coordinator": "fixture-coordinator"}
        for changes in ({"root": str(root.parent)}, {"mode": "publish"},
                        {"publication_message": "Publish a private capture"},
                        {"assignments": {f"{private}/Daily/2025/2026-11-21.md": "fixture-author"}},
                        {"assignments": {f"{private}/.learning/record.json": "fixture-author"}}):
            run("--engie-learning", "begin", "invalid", payload={**contract, **changes}, code=2)
        run("--state-dir", str(self.state), "--engie-learning", "begin", "invalid", payload=contract, code=2)
        run("--engie-learning", "commit", "invalid", "Invalid publication", code=2)
        run("--engie-learning", "publish", "invalid", code=2)
        self.assertFalse(ledger.exists())
        legacy_id = "legacy-fixture"
        run("begin", legacy_id, payload=contract)
        general.chmod(0o500)
        (general / "tasks").chmod(0o500)
        (general / ".lock").chmod(0o400)
        self.addCleanup(general.chmod, 0o700)
        self.addCleanup((general / "tasks").chmod, 0o700)
        records_before = {path: (path.stat().st_mtime_ns, stat.S_IMODE(path.stat().st_mode))
                          for path in (general, general / ".lock", general / "tasks",
                                       general / "tasks" / (legacy_id + ".json"))}
        alternative = {**contract, "assignments": {other: "fixture-author"}}
        error = run("--engie-learning", "begin", legacy_id, payload=alternative, code=2)
        self.assertIn("ID already exists", error)
        error = run("--engie-learning", "begin", "overlap", payload=contract, code=2)
        self.assertIn("unfinished task owns", error)
        private_id = "private-fixture"
        run("--engie-learning", "begin", private_id, payload=alternative)
        run("hook", "stop", payload={"session_id": "fixture-coordinator", "cwd": str(root)})
        self.assertEqual(records_before, {path: (path.stat().st_mtime_ns, stat.S_IMODE(path.stat().st_mode))
                                         for path in records_before})
        (general / ".lock").chmod(0o600)
        error = run("begin", "overlap", payload=alternative, code=2)
        self.assertIn("unfinished task owns", error)
        error = run("begin", private_id, payload=contract, code=2)
        self.assertIn("ID already exists", error)
        run("--state-dir", str(ledger), "status", private_id, code=2)

        # A redirected runtime directory is neither read nor replaced.
        moved = ledger.with_name("moved-ledger")
        ledger.rename(moved)
        ledger.symlink_to(moved, target_is_directory=True)
        run("--engie-learning", "status", private_id, code=2)
        self.assertTrue(ledger.is_symlink())
        self.assertTrue((moved / "tasks" / (private_id + ".json")).is_file())

    @unittest.skipUnless(os.name == "posix", "Private capture is POSIX-only")
    def test_engie_learning_rejects_nested_task_directory_owner(self):
        run, root, private, _ = self.engie_fixture()
        ledger = root / private / ".learning/task-ledger"
        ledger.parent.mkdir(mode=0o700, parents=True)
        ledger.mkdir(mode=0o700)
        tasks = ledger / "tasks"
        tasks.mkdir(mode=0o700)
        self.git("-C", str(tasks), "init", "-q")
        contract = {"root": str(root), "requirement": "Reserve a synthetic note", "mode": "local",
                    "assignments": {f"{private}/Topics/onboarding.md": "fixture-author"},
                    "coordinator": "fixture-coordinator"}
        error = run("--engie-learning", "begin", "nested-owner", payload=contract, code=2)
        self.assertIn("registered Git owner", error)
        self.assertFalse((ledger / ".lock").exists())
        self.assertEqual(set(tasks.iterdir()), {tasks / ".git"})

    @unittest.skipUnless(os.name == "posix", "Private capture is POSIX-only")
    def test_engie_learning_rejects_case_aliases_in_index_and_head(self):
        run, root, private, _ = self.engie_fixture()
        topic = f"{private}/Topics/onboarding.md"
        contract = {"root": str(root), "requirement": "Reserve a synthetic note", "mode": "local",
                    "assignments": {topic: "fixture-author"}, "coordinator": "fixture-coordinator"}
        learning = root / private / ".learning"
        learning.mkdir(mode=0o700, parents=True)
        ledger_alias = learning / "Task-Ledger/fixture.txt"
        ledger_alias.parent.mkdir(mode=0o700)
        ledger_alias.write_text("Synthetic alias\n")
        alias = ledger_alias.relative_to(root).as_posix()
        self.git("add", "-f", "--", alias)
        ledger_alias.unlink()
        ledger_alias.parent.rmdir()
        error = run("--engie-learning", "begin", "ledger-alias", payload=contract, code=2)
        self.assertIn("must be untracked", error)
        self.git("restore", "--staged", "--", alias)

        note_alias = root / private / "Topics/Onboarding.md"
        note_alias.parent.mkdir()
        note_alias.write_text("Synthetic alias\n")
        alias = note_alias.relative_to(root).as_posix()
        self.git("add", "-f", "--", alias)
        tree = self.git("write-tree")
        commit = self.git("commit-tree", tree, "-p", "HEAD", "-m", "Add a synthetic note alias")
        self.git("update-ref", "HEAD", commit)
        self.git("update-index", "--force-remove", "--", alias)
        note_alias.unlink()
        self.assertEqual(self.git("ls-files", "--", alias), "")
        error = run("--engie-learning", "begin", "note-alias", payload=contract, code=2)
        self.assertIn("must be untracked", error)
        self.assertFalse((learning / "task-ledger").exists())

    @unittest.skipUnless(os.name == "posix", "Private capture is POSIX-only")
    def test_engie_learning_native_edits_recheck_note_protection(self):
        run, root, private, _ = self.engie_fixture()
        topic = f"{private}/Topics/onboarding.md"
        owner, author = "fixture-owner-session", "fixture-native-author"
        contract = {"root": str(root), "requirement": "Reserve a synthetic note", "mode": "local",
                    "assignments": {topic: author}, "coordinator": owner, "session_id": owner}
        run("--engie-learning", "begin", "protected-note", payload=contract)
        event = {"session_id": owner, "agent_id": author, "cwd": str(root),
                 "tool_name": "Write", "tool_input": {"file_path": topic}}
        self.assertEqual(run("hook", "pre-tool", payload=event), {})
        exclusions = root / ".git/info/exclude"
        exclusions.write_text(f"/{private}/.learning/\n")
        denied = run("hook", "pre-tool", payload=event)
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")
        copilot = {"sessionId": owner, "agentId": author, "cwd": str(root),
                   "toolName": "create", "toolArgs": {"path": topic}}
        denied = run("hook", "--client", "copilot", "preToolUse", payload=copilot)
        self.assertEqual(denied["permissionDecision"], "deny")

        exclusions.write_text(f"/{private}/\n")
        path = root / topic
        path.parent.mkdir()
        os.link(root / "note.txt", path)
        denied = run("hook", "pre-tool", payload=event)
        self.assertEqual(denied["hookSpecificOutput"]["permissionDecision"], "deny")

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
