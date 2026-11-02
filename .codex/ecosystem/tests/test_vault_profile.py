"""Exercise a relocated install against temporary vaults and local bare remotes."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ecosystem.vault import review_gate, workflow


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, timeout=10)


class NativeVault(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.root = self.base / "relocated vault"
        self.root.mkdir()
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.name", "Local test")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "core.hooksPath", ".git/hooks")
        git(self.root, "config", "commit.gpgsign", "false")
        (self.root / "README.md").write_text("Initial owner\n")
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-m", "Seed test")
        remote = self.base / "remote.git"
        git(self.base, "init", "--bare", str(remote))
        git(self.root, "remote", "add", "origin", str(remote))
        git(self.root, "push", "-u", "origin", "main")
        self.flow = workflow.Workflow(self.root, "native-test")

    def event(self, name: str, turn: str, **fields: object) -> dict:
        return workflow.handle_hook_event({"session_id": "native-test", "turn_id": turn,
            "hook_event_name": name, "cwd": str(self.root), **fields}, project_root=self.root)

    def command(self, arguments: list[str], payload: dict | None = None) -> tuple[int, dict, str]:
        output, errors = io.StringIO(), io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(payload))), redirect_stdout(output), redirect_stderr(errors):
            result = workflow.entrypoint(["--session", "native-test", *arguments], project_root=self.root)
        return result, json.loads(output.getvalue() or "{}"), errors.getvalue()

    def test_prompt_resume_replay_and_local_closure(self) -> None:
        class PrivatePayload(dict):
            def get(self, key, default=None):
                if key in {"prompt", "transcript_path", "last_assistant_message"}:
                    raise AssertionError("Private payload field was accessed")
                return super().get(key, default)

        payload = PrivatePayload(hook_event_name="UserPromptSubmit", session_id="native-test",
                                 turn_id="first", cwd=str(self.root))
        workflow.handle_hook_event(payload, project_root=self.root)
        self.assertTrue(self.flow.path.is_relative_to(self.root / ".git/omaros"))
        self.assertEqual(self.command(["plan"], {"requirements": ["Read"], "paths": []})[0], 0)
        self.assertEqual(self.command(["review"], {"Read": "Inspected selected owner."})[0], 0)
        self.assertTrue(self.command(["finish"])[1]["local_only"])
        self.assertEqual(self.event("Stop", "first"), {})
        self.event("UserPromptSubmit", "second")
        new = self.flow.path.read_bytes()
        self.event("UserPromptSubmit", "first")
        self.assertEqual(self.flow.path.read_bytes(), new)

    def test_foreign_owner_or_payload_cannot_redirect_commands(self) -> None:
        nested = self.root / "other"
        nested.mkdir()
        git(nested, "init")
        self.assertEqual(self.event("UserPromptSubmit", "nested", cwd=str(nested)), {})
        self.assertFalse((nested / ".git/omaros").exists())
        self.assertFalse(self.flow.path.exists())
        code, _, message = self.command(["--root", str(nested), "begin"])
        self.assertEqual(code, 2)
        self.assertIn("different Git owner", message)
        self.assertFalse((nested / ".git/omaros").exists())
        self.event("UserPromptSubmit", "one")
        code, state, _ = self.command(["plan"], {"requirements": ["Read"], "paths": [],
                                                 "cwd": str(nested), "session_id": "untrusted"})
        self.assertEqual(code, 0)
        self.assertEqual(state["author"], self.flow.session)
        self.assertFalse((nested / ".git/omaros").exists())

    def test_stop_duplicate_does_not_spend_an_attempt_and_rechecks_the_current_state(self) -> None:
        self.event("UserPromptSubmit", "stop")
        first = self.event("Stop", "stop")
        self.assertEqual(first["decision"], "block")
        self.assertFalse(self.event("Stop", "stop")["continue"])
        self.assertEqual(self.flow.load()["stop_attempts"], 1)
        self.command(["plan"], {"requirements": ["Read"], "paths": []})
        self.command(["review"], {"Read": "Inspected owner."})
        self.command(["finish"])
        self.assertEqual(self.event("Stop", "stop"), {})
        git(self.root, "commit", "--allow-empty", "-m", "Concurrent change")
        self.assertTrue(self.event("Stop", "stop"))

    def test_legacy_cli_stop_without_turn_does_not_convert_different_calls_into_replays(self) -> None:
        self.event("UserPromptSubmit", "first")
        payload = {"session_id": self.flow.session, "cwd": str(self.root)}
        for attempt in (1, 2):
            code, result, error = self.command(["hook", "stop"], payload)
            self.assertEqual(code, 0, error)
            self.assertEqual(result["decision"], "block")
            self.assertEqual(self.flow.load()["stop_attempts"], attempt)
        with self.assertRaises(workflow.Blocked):
            workflow.handle_hook_event({**payload, "hook_event_name": "Stop"}, project_root=self.root)

    def test_archived_review_floor_migrates_without_resetting_open_findings(self) -> None:
        self.event("UserPromptSubmit", "one")
        path = self.root / "public.md"
        path.write_text("public\n")
        self.command(["plan"], {"requirements": ["Review"], "paths": ["public.md"]})
        code, round_one, _ = self.command(["review-start"])
        self.assertEqual(code, 0)
        finding = {"id": "pending", "path": "public.md", "line": 1, "severity": "high",
                   "origin": "introduced", "scenario": "Legacy fixture", "consequence": "Unfinished",
                   "evidence": "Independent author noted a missing claim."}
        self.assertEqual(self.command(["review-report"], {"token": round_one["token"],
            "reviewer": "independent-test", "role": "reviewer", "focus": ["correctness"],
            "paths": ["public.md"], "summary": "One finding", "evidence": "Reviewed text",
            "findings": [finding]})[0], 0)
        state = self.flow.load()
        old = state["review_gate"]
        old["schema_version"] = 1
        old["policy_floor"].update(schema_version=1, max_rounds=3)
        original_rounds, original_findings = deepcopy(old["rounds"]), deepcopy(old["findings"])
        self.flow.save(state)
        path.write_text("Revised public text\n")
        self.assertEqual(self.command(["review-start"])[0], 0)
        current = self.flow.load()["review_gate"]
        self.assertEqual(current["rounds"][:-1], original_rounds)
        self.assertEqual(current["findings"], original_findings)
        self.assertEqual(current["schema_version"], 2)
        self.assertNotIn("max_rounds", current["policy_floor"])
        self.assertEqual(self.command(["review"], {"Review": "Fixture"})[0], 2)

    def _prepare_journal(self):
        source = self.base / "personal-source"
        source.mkdir()
        policy = {"schema_version": 1, "sources": [{"root": str(source),
            "alias": "personal-source", "visibility": "personal"}], "target": {"root": str(self.root)}}
        progress = workflow.progress_engine()
        state = progress.create_progress("Check journal recovery", source_alias="personal-source")
        checkpoint = {"id": "first", "summary": "First observation", "visibility": "personal",
            "snapshot": {"objectives": ["Preserve the journal"], "current": "Recording a result",
                "completed": ["One observation"], "decisions": [], "findings": [], "verification": [],
                "unresolved": [], "next_steps": [], "references": []}}
        state = progress.checkpoint(state, checkpoint)
        envelope = progress.export_envelope(state, source_root=source, policy=policy)
        self.event("UserPromptSubmit", "journal")
        names = [envelope["note_path"], workflow.journal_engine().DASHBOARD_PATH]
        code, _, message = self.command(["plan"], {"requirements": ["Journal"], "paths": names})
        self.assertEqual(code, 0, message)

        def receive(item=envelope):
            return workflow.journal_engine().receive(self.flow, item, source_root=source, policy=policy,
                progress=progress, validate_path=workflow.safe_path, validate_blob=workflow.validate_blob)

        def advance():
            updated = progress.checkpoint(state, {**checkpoint, "id": "second", "summary": "Revised observation",
                "snapshot": {**checkpoint["snapshot"], "current": "Updated journal state"}})
            return progress.export_envelope(updated, source_root=source, policy=policy)

        return [self.root / name for name in names], receive, advance

    def _swap_journal_parent(self, position: int) -> None:
        from ecosystem.vault import progress_journal as journal
        paths, receive, _ = self._prepare_journal()
        victim = paths[position]
        peer = self.base / "sibling-owner"
        peer.mkdir()
        sentinel = peer / victim.name
        sentinel.write_text("external bytes", encoding="utf-8")
        backup = self.base / "detached-directory"
        native = journal._rename_at
        replaced = False

        def swap_after_verification(src_fd, src, dst_fd, dst, *, exchange):
            nonlocal replaced
            if not replaced and dst == victim.name:
                replaced = True
                victim.parent.rename(backup)
                victim.parent.symlink_to(peer, target_is_directory=True)
            native(src_fd, src, dst_fd, dst, exchange=exchange)

        with patch.object(journal, "_rename_at", side_effect=swap_after_verification):
            with self.assertRaises(journal.JournalError):
                receive()
        self.assertTrue(replaced)
        self.assertEqual(sentinel.read_text(), "external bytes")
        self.assertFalse((backup / victim.name).exists())
        storage = self.flow.home / "progress-journal.json"
        self.assertIsNotNone(json.loads(storage.read_text())["pending"])
        if position == 1:
            self.assertTrue(paths[0].is_file())
        else:
            self.assertFalse(paths[1].exists())
        victim.parent.unlink()
        backup.rename(victim.parent)
        self.assertEqual(receive()["status"], "RECEIVED_LOCAL")
        self.assertIsNone(json.loads(storage.read_text())["pending"])
        self.assertTrue(all(path.is_file() for path in paths))

    def test_dashboard_parent_swap_preserves_sibling_and_partial_replay(self):
        self._swap_journal_parent(1)

    def test_note_parent_swap_preserves_sibling_and_partial_replay(self):
        self._swap_journal_parent(0)

    def test_same_bytes_concurrent_replacement_preserves_its_distinct_inode(self):
        from ecosystem.vault import progress_journal as journal
        paths, receive, advance = self._prepare_journal()
        receive()
        updated = advance()
        victim = paths[1]
        previous = self.base / "previous-dashboard"
        replacement = self.base / "same-bytes"
        replacement.write_bytes(victim.read_bytes())
        foreign_inode = replacement.stat().st_ino
        native = journal._rename_at
        raced = False

        def replace_after_check(src_fd, src, dst_fd, dst, *, exchange):
            nonlocal raced
            if not raced and dst == victim.name:
                raced = True
                victim.rename(previous)
                replacement.rename(victim)
            native(src_fd, src, dst_fd, dst, exchange=exchange)

        with patch.object(journal, "_rename_at", side_effect=replace_after_check):
            with self.assertRaises(journal.JournalError):
                receive(updated)
        self.assertTrue(raced)
        self.assertEqual(victim.stat().st_ino, foreign_inode)
        self.assertEqual(victim.read_bytes(), previous.read_bytes())
        with self.assertRaises(journal.JournalError):
            receive(updated)
        victim.rename(replacement)
        previous.rename(victim)
        self.assertEqual(receive(updated)["status"], "RECEIVED_LOCAL")

    def test_guard_status_uses_installed_home_without_creating_task_state(self) -> None:
        from ecosystem.vault import install
        home = self.base / "selected-device"
        expected = {"verified": True, "root": str(self.root), "hooks": str(home / "guard")}
        before = sorted(self.flow.home.iterdir())
        with patch.dict("os.environ", {"CODEX_HOME": str(home)}), \
                patch.object(install, "verify_guard", return_value=expected, create=True) as verify, \
                patch.object(workflow, "Workflow", side_effect=AssertionError("No lifecycle for guard-status")):
            code, result, error = self.command(["guard-status"])
        self.assertEqual(code, 0, error)
        self.assertEqual(result, expected)
        verify.assert_called_once_with(self.root, home)
        self.assertEqual(sorted(self.flow.home.iterdir()), before)
        self.assertFalse(self.flow.path.exists())

    def test_guard_status_preserves_failed_validation_and_owner_boundary(self) -> None:
        from ecosystem.vault import install
        with patch.object(install, "verify_guard", side_effect=ValueError("Invalid enrolled guard"), create=True), \
                patch.object(workflow, "Workflow", side_effect=AssertionError("No lifecycle for guard-status")):
            code, result, error = self.command(["guard-status"])
        self.assertEqual(code, 2)
        self.assertEqual(result, {})
        self.assertIn("Invalid enrolled guard", error)
        self.assertFalse(self.flow.path.exists())

        nested = self.root / "nested-owner"
        nested.mkdir()
        git(nested, "init")
        with patch.object(install, "verify_guard", side_effect=AssertionError("Must reject owner first"), create=True):
            code, result, error = self.command(["--root", str(nested), "guard-status"])
        self.assertEqual(code, 2)
        self.assertIn("different Git owner", error)
        self.assertFalse((nested / ".git/omaros").exists())

    def test_missing_policy_and_private_historical_paths_fail_closed(self) -> None:
        with review_gate.selected_project(self.root):
            with patch.object(review_gate, "DEFAULT_POLICY", self.base / "absent.json"):
                with self.assertRaises(review_gate.ReviewError):
                    review_gate.policy_for(self.root)
            private = "09_Data_Sources/Email_Exports/By_Message/synthetic.md"
            state = {"paths": [], "review_authors": {"previous": [private]}}
            with self.assertRaises(review_gate.ReviewError):
                review_gate.prepare(self.root, state)


class PatchTargetBoundaries(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.root = self.base / "vault"
        self.child = self.base / "delegate"
        for owner in (self.root, self.child):
            owner.mkdir()
            git(owner, "init", "-b", "main")
            git(owner, "config", "user.name", "Local test")
            git(owner, "config", "user.email", "test@example.invalid")
            git(owner, "config", "core.hooksPath", ".git/hooks")
            git(owner, "config", "commit.gpgsign", "false")
            (owner / "allowed.md").write_text("owned")
            git(owner, "add", "allowed.md")
            git(owner, "commit", "-m", "Seed")
            remote = self.base / (owner.name + ".git")
            git(self.base, "init", "--bare", str(remote))
            git(owner, "remote", "add", "origin", str(remote))
            git(owner, "push", "-u", "origin", "main")
        self.delegate = workflow.Workflow(self.child, "delegate")
        self.delegate.begin("delegate-turn")
        self.delegate.plan({"requirements": ["Edit delegate"], "paths": ["allowed.md"]})
        self.flow = workflow.Workflow(self.root, "vault")
        self.flow.begin("vault-turn")
        self.flow.plan({"requirements": ["Edit selected owners"], "paths": ["allowed.md"],
                        "delegates": [{"root": str(self.child), "namespace": "omaros", "session": "delegate"}]})
        self.foreign = self.base / "outside"
        (self.foreign / "nested").mkdir(parents=True)
        (self.foreign / "allowed.md").write_text("outside")
        (self.root / "alias").symlink_to(self.foreign / "nested", target_is_directory=True)
        undeclared = self.child / "undeclared"
        (undeclared / "nested").mkdir(parents=True)
        (undeclared / "allowed.md").write_text("outside")
        (self.child / "alias").symlink_to(undeclared / "nested", target_is_directory=True)

    def guard(self, target: str | Path, action: str = "Update File") -> None:
        document = f"*** Begin Patch\n*** {action}: {target}\n*** End Patch"
        self.flow.guard_patch({"tool_input": document}, self.root)

    def test_lexical_cancellation_cannot_authorize_a_different_filesystem_target(self) -> None:
        self.guard("allowed.md")
        self.guard(self.child / "allowed.md")
        for raw in ("alias/../allowed.md", self.root / "alias/../allowed.md",
                    self.child / "alias/../allowed.md", "../delegate/alias/../allowed.md"):
            with self.subTest(raw=raw):
                self.assertEqual((self.root / raw).read_text(), "outside")
                with self.assertRaises(workflow.Blocked):
                    self.guard(raw)
        directory = self.root / "ordinary"
        directory.mkdir()
        with self.assertRaises(workflow.Blocked):
            self.guard("ordinary/../allowed.md")
        self.assertEqual((self.foreign / "allowed.md").read_text(), "outside")

    def test_scoped_deletion_of_a_final_delegate_link_does_not_follow_it(self) -> None:
        link = self.child / "legacy"
        link.symlink_to(self.foreign / "allowed.md")
        state = self.delegate.load()
        state.update(paths=["legacy"], deletions=["legacy"])
        self.delegate.save(state)
        self.guard(link, "Delete File")
        with self.assertRaises(workflow.Blocked):
            self.guard(link, "Update File")
        self.assertEqual((self.foreign / "allowed.md").read_text(), "outside")


if __name__ == "__main__":
    unittest.main()
