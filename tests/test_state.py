"""Behavior checks for private task scope, concurrency and evidence freshness."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from constellation.state import StateError, Store, fingerprint, ready


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.git("remote", "add", "origin", str(self.base / "remote.git"))
        for name in ("a.txt", "b.txt", "foreign.txt"):
            (self.root / name).write_text("initial\n")
        self.git("add", ".")
        self.git("commit", "-m", "Initial")
        self.store = Store(self.base / "private-state")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args],
                                       stderr=subprocess.DEVNULL, text=True).strip()

    def begin(self, name="task", assignments=None):
        return self.store.begin(name, self.root, "Change the assigned files",
                                assignments or {"a.txt": "native-author"},
                                coordinator="native-coordinator", session_id="session")

    def successful_check(self, name="task"):
        return self.store.check(name, "default", [sys.executable, "-c", "pass"])

    def approve(self, name="task"):
        observed = fingerprint(self.store.get(name))
        return self.store.review(name, "native-reviewer", "Observed the exact diff",
                                 expected_fingerprint=observed)

    def test_parallel_disjoint_tasks_preserve_both_records_and_reject_overlap(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.begin, "first", {"a.txt": "author-a"}),
                       pool.submit(self.begin, "second", {"b.txt": "author-b"})]
            self.assertEqual({future.result()["id"] for future in futures}, {"first", "second"})
        self.assertEqual(len(self.store.active(self.root)), 2)
        with self.assertRaises(StateError):
            self.begin("third", {"a.txt": "other-author"})
        self.assertEqual(self.store.get("first")["session_id"], "session")

    def test_cross_task_prefix_and_case_aliases_are_reserved(self):
        self.begin("parent", {"new": "first-author"})
        for path in ("new/file.txt", "NEW"):
            with self.subTest(path=path), self.assertRaises(StateError):
                self.begin("conflict", {path: "second-author"})

    def test_reject_traversal_directory_symlink_and_nested_owner(self):
        (self.root / "alias").symlink_to(self.base, target_is_directory=True)
        nested = self.root / "nested"
        nested.mkdir()
        subprocess.run(["git", "init", str(nested)], capture_output=True, check=True)
        for path in ("../outside.txt", "a/../b.txt", "nested/file.txt", "alias/file.txt", "nested"):
            with self.subTest(path=path), self.assertRaises(StateError):
                self.begin(assignments={path: "author"})

    def test_review_requires_observed_fingerprint_and_independent_identity(self):
        self.begin()
        (self.root / "a.txt").write_text("candidate\n")
        self.successful_check()
        observed = fingerprint(self.store.get("task"))
        for author in ("native-author", "native-coordinator"):
            with self.assertRaises(StateError):
                self.store.review("task", author, "Looks good", expected_fingerprint=observed)
        (self.root / "a.txt").write_text("changed after inspection\n")
        with self.assertRaises(StateError):
            self.store.review("task", "reviewer", "Looks good", expected_fingerprint=observed)
        self.assertFalse(self.store.status("task")["gate"]["ready"])

    def test_post_review_edit_invalidates_approval_and_check(self):
        self.begin()
        (self.root / "a.txt").write_text("candidate\n")
        self.successful_check()
        self.approve()
        self.assertTrue(self.store.status("task")["gate"]["ready"])
        (self.root / "a.txt").write_text("later edit\n")
        with self.assertRaises(StateError):
            ready(self.store.get("task"))
        self.successful_check()
        self.assertFalse(self.store.status("task")["gate"]["ready"])
        self.approve()
        self.assertTrue(self.store.status("task")["gate"]["ready"])

    def test_failed_latest_check_blocks_and_output_stays_private(self):
        self.begin()
        (self.root / "a.txt").write_text("candidate\n")
        self.successful_check()
        self.approve()
        check = self.store.check("task", "default", [sys.executable, "-c",
                "print('do-not-store-this-output'); raise SystemExit(9)"])
        self.assertEqual(check["returncode"], 9)
        self.assertFalse(self.store.status("task")["gate"]["ready"])
        self.assertNotIn("do-not-store-this-output", (self.store.tasks / "task.json").read_text())

    def test_replacing_check_after_review_requires_new_review(self):
        self.begin()
        self.successful_check()
        self.approve()
        old = fingerprint(self.store.get("task"))
        self.store.check("task", "default", [sys.executable, "-c", "assert 1 + 1 == 2"])
        self.assertNotEqual(fingerprint(self.store.get("task")), old)
        self.assertFalse(self.store.status("task")["gate"]["ready"])
        self.approve()
        self.assertTrue(self.store.status("task")["gate"]["ready"])

    def test_owner_instruction_edit_invalidates_existing_review(self):
        (self.root / "AGENTS.md").write_text("Initial owner rule\n")
        self.begin()
        self.successful_check()
        self.approve()
        self.assertTrue(self.store.status("task")["gate"]["ready"])
        (self.root / "AGENTS.md").write_text("Stricter owner rule\n")
        self.assertFalse(self.store.status("task")["gate"]["ready"])

    def test_nested_instruction_change_invalidates_local_review(self):
        area = self.root / "area"
        area.mkdir()
        (area / "note.txt").write_text("Note\n")
        (area / "AGENTS.md").write_text("Initial nested rule\n")
        self.store.begin("local", self.root, "Edit note", {"area/note.txt": "author"},
                         coordinator="coordinator", mode="local")
        self.successful_check("local")
        self.approve("local")
        self.assertTrue(self.store.status("local")["gate"]["ready"])
        (area / "AGENTS.md").write_text("Updated nested rule\n")
        self.assertFalse(self.store.status("local")["gate"]["ready"])

    def test_fifo_scope_is_rejected_before_reading(self):
        os.mkfifo(self.root / "pipe")
        with self.assertRaisesRegex(StateError, "regular"):
            self.store.begin("pipe", self.root, "Invalid scope", {"pipe": "author"},
                             coordinator="coordinator", mode="local")

    def test_mutating_check_cannot_pass_and_foreign_index_is_unchanged(self):
        self.begin()
        (self.root / "foreign.txt").write_text("foreign staged\n")
        self.git("add", "foreign.txt")
        index_before = self.git("ls-files", "--stage")
        check = self.store.check("task", "default", [sys.executable, "-c",
                "from pathlib import Path; Path('a.txt').write_text('changed')"])
        self.assertEqual(check["status"], "stale")
        self.assertEqual(self.git("ls-files", "--stage"), index_before)

    def test_check_timeout_is_failure_and_checkpoint_is_recoverable(self):
        self.begin()
        record = self.store.check("task", "default", [sys.executable, "-c",
                                 "import time; time.sleep(1)"], timeout=0.01)
        self.assertEqual(record["status"], "failed")
        self.store.checkpoint("task", "Prepared files; review pending")
        restored = Store(self.store.root).get("task")
        self.assertEqual(restored["milestones"][-1]["summary"], "Prepared files; review pending")
        self.assertEqual((self.store.tasks / "task.json").stat().st_mode & 0o777, 0o600)

    def test_current_rejection_blocks_until_reviewer_corrects_it(self):
        self.begin()
        self.successful_check()
        self.approve()
        observed = fingerprint(self.store.get("task"))
        self.store.review("task", "second-reviewer", "Missing behavior", "reject",
                          expected_fingerprint=observed)
        self.assertFalse(self.store.status("task")["gate"]["ready"])
        self.store.review("task", "second-reviewer", "Verified that behavior", "approve",
                          expected_fingerprint=observed)
        self.assertTrue(self.store.status("task")["gate"]["ready"])

    def test_local_private_task_never_writes_git_objects_and_finishes_locally(self):
        self.git("remote", "remove", "origin")
        private = self.root / "Private"
        private.mkdir()
        (private / "note.txt").write_text("private note\n")
        objects = sorted(path.relative_to(self.root / ".git/objects")
                         for path in (self.root / ".git/objects").rglob("*"))
        self.store.begin("local", self.root, "Edit private note",
                         {"Private/note.txt": "native-author"},
                         coordinator="native-coordinator", mode="local")
        self.successful_check("local")
        self.approve("local")
        task = self.store.finish("local")
        self.assertEqual(task["closed"]["kind"], "local")
        self.assertIsNone(task["target"])
        self.assertEqual(task["publication"], {})
        after = sorted(path.relative_to(self.root / ".git/objects")
                       for path in (self.root / ".git/objects").rglob("*"))
        self.assertEqual(objects, after)

    def test_cancel_releases_unassessed_scope_without_claiming_success(self):
        self.begin()
        original = (self.root / "a.txt").read_bytes()
        task = self.store.cancel("task", "Assign the actual clean-session native actor")
        self.assertEqual(task["closed"]["kind"], "cancelled")
        self.assertEqual(self.store.active(), [])
        self.assertEqual((self.root / "a.txt").read_bytes(), original)
        self.begin("replacement")
        self.successful_check("replacement")
        with self.assertRaises(StateError):
            self.store.cancel("replacement", "Cannot hide recorded checks")

    def test_reassign_invalidates_evidence_and_keeps_previous_authors_ineligible(self):
        self.begin()
        self.successful_check()
        self.approve()
        before = self.store.get("task")
        task = self.store.assign("task", "a.txt", "spawn-returned-native-id",
                                 "Correct inherited environment identity")
        self.assertEqual(task["assignments"]["a.txt"], "spawn-returned-native-id")
        self.assertEqual(set(task["authors"]["a.txt"]), {"native-author", "spawn-returned-native-id"})
        self.assertEqual(task["checks"], before["checks"])
        self.assertEqual(task["reviews"], before["reviews"])
        self.assertFalse(self.store.status("task")["gate"]["ready"])
        self.successful_check()
        self.assertFalse(self.store.status("task")["gate"]["ready"])
        current = fingerprint(self.store.get("task"))
        for author in ("native-author", "spawn-returned-native-id"):
            with self.subTest(author=author), self.assertRaises(StateError):
                self.store.review("task", author, "Cannot self-review", expected_fingerprint=current)
        self.approve()
        self.assertTrue(self.store.status("task")["gate"]["ready"])

    def test_reassign_rejects_new_scope_and_publication_or_closed_tasks(self):
        self.begin()
        with self.assertRaises(StateError):
            self.store.assign("task", "b.txt", "new-author", "Not in this task")
        from constellation.git import _journal_path

        intent = _journal_path(self.root, "task")
        intent.parent.mkdir(parents=True)
        intent.write_text("{}")
        with self.assertRaises(StateError):
            self.store.assign("task", "a.txt", "new-author", "Unrecovered intent")
        intent.unlink()
        with self.store.locked("task") as task:
            task["publication"] = {"commit": "synthetic-committed-marker"}
        with self.assertRaises(StateError):
            self.store.assign("task", "a.txt", "new-author", "Already committed")
        with self.store.locked("task") as task:
            task["publication"] = {}
            task["status"] = "closed"
        with self.assertRaises(StateError):
            self.store.assign("task", "a.txt", "new-author", "Already closed")

    def test_legacy_task_reassignment_preserves_original_author(self):
        self.begin()
        with self.store.locked("task") as task:
            task.pop("authors")
            task.pop("assignment_history")
        changed = self.store.assign("task", "a.txt", "new-author", "Correct legacy actor record")
        self.assertEqual(changed["authors"]["a.txt"], ["native-author", "new-author"])
        self.assertEqual(changed["assignment_history"][0]["previous"], "native-author")

    def test_actor_session_binding_invalidates_review_and_preserves_old_aliases(self):
        self.store.begin("task", self.root, "Edit note", {"a.txt": "/root/author"},
                         coordinator="/root", actor_sessions={"/root/author": "event-one"})
        self.successful_check()
        self.approve()
        self.assertTrue(self.store.status("task")["gate"]["ready"])
        changed = self.store.assign("task", "a.txt", "/root/author", "Register renewed event session",
                                    session_id="event-two")
        self.assertEqual(changed["actor_sessions"], {"/root/author": "event-two"})
        self.assertEqual(changed["actor_session_history"]["/root/author"], ["event-one", "event-two"])
        self.assertFalse(self.store.status("task")["gate"]["ready"])
        self.successful_check()
        current = fingerprint(self.store.get("task"))
        for actor in ("/root/author", "event-one", "event-two"):
            with self.subTest(actor=actor), self.assertRaises(StateError):
                self.store.review("task", actor, "Cannot review through an alias", expected_fingerprint=current)
        self.approve()
        self.assertTrue(self.store.status("task")["gate"]["ready"])

    def test_ambiguous_or_undeclared_event_aliases_fail_without_partial_transfer(self):
        for aliases in ({"author-a": "same", "author-b": "same"},
                        {"unknown": "event"}, {"author-a": "author-b"}):
            with self.subTest(aliases=aliases), self.assertRaises(StateError):
                self.store.begin("invalid", self.root, "Parallel ownership",
                                 {"a.txt": "author-a", "b.txt": "author-b"},
                                 coordinator="coordinator", actor_sessions=aliases)
        self.store.begin("task", self.root, "Parallel ownership",
                         {"a.txt": "author-a", "b.txt": "author-b"}, coordinator="coordinator",
                         actor_sessions={"author-a": "event-a", "author-b": "event-b"})
        self.store.assign("task", "a.txt", "author-a", "New session", session_id="event-a-new")
        before = self.store.get("task")
        with self.assertRaises(StateError):
            self.store.assign("task", "b.txt", "author-c", "Cannot reuse historical identity",
                              session_id="event-a")
        self.assertEqual(self.store.get("task"), before)
        with self.assertRaises(StateError):
            self.store.assign("task", "b.txt", "event-a", "Cannot use an alias as another native actor")
        self.assertEqual(self.store.get("task"), before)

    def test_explicit_legacy_uuid_correction_preserves_history_and_blocks_self_review(self):
        legacy = "01a1e17f-6280-7613-883b-1ed05dd11b18"
        native = "/root/acceptance_a_fresh"
        self.begin(assignments={"a.txt": legacy})
        self.store.assign("task", "a.txt", native, "Use the tool-returned native identity")
        self.successful_check()
        self.approve()
        corrected = self.store.assign("task", "a.txt", native,
            "Native event evidence associates this old raw UUID with the canonical actor", session_id=legacy)
        self.assertEqual(corrected["actor_sessions"], {native: legacy})
        self.assertIn(legacy, corrected["authors"]["a.txt"])
        self.assertEqual(corrected["assignment_history"][-1]["identity_corrections"],
                         [{"legacy_actor": legacy, "native_actor": native}])
        self.assertFalse(self.store.status("task")["gate"]["ready"])
        self.successful_check()
        observed = fingerprint(self.store.get("task"))
        with self.assertRaises(StateError):
            self.store.review("task", legacy, "Cannot review through old identity", expected_fingerprint=observed)
        self.approve()
        self.assertTrue(self.store.status("task")["gate"]["ready"])
        # A subsequent independent transfer keeps the established join valid.
        self.store.assign("task", "a.txt", "/root/next", "Transfer subsequent editing")

    def test_legacy_uuid_correction_cannot_merge_active_or_explicitly_distinct_actors(self):
        legacy = "01a1e17f-6280-7613-883b-1ed05dd11b18"
        native = "/root/acceptance_a_fresh"
        self.begin(assignments={"a.txt": legacy, "b.txt": legacy})
        with self.assertRaises(StateError):
            self.store.assign("task", "a.txt", native, "Other path still uses the raw actor", session_id=legacy)
        self.store.assign("task", "a.txt", native, "Canonical ownership first")
        self.store.assign("task", "b.txt", "/root/different", "Distinct actor owns second path", session_id=legacy)
        before = self.store.get("task")
        with self.assertRaises(StateError):
            self.store.assign("task", "a.txt", native, "Cannot merge distinct explicit bindings", session_id=legacy)
        self.assertEqual(self.store.get("task"), before)

    def test_publication_intent_freezes_evidence_until_verified_local_followup(self):
        from constellation.git import _journal_path

        self.begin()
        self.successful_check()
        self.approve()

        previous = self.store.get("task")
        observed = fingerprint(previous)
        intent = _journal_path(self.root, "task")
        intent.parent.mkdir(parents=True)
        intent.write_text(json.dumps({"phase": "commit_pending", "commit": "recorded-sha"}))
        with self.assertRaisesRegex(StateError, "frozen"):
            self.successful_check()
        with self.assertRaisesRegex(StateError, "frozen"):
            self.store.review("task", "other-reviewer", "Cannot replace committed evidence",
                              expected_fingerprint=observed)
        self.assertEqual(self.store.get("task"), previous)
        with self.store.locked("task") as task:
            task["publication"] = {"status": "verified_local_changes", "commit": "recorded-sha"}
        with self.assertRaisesRegex(StateError, "frozen"):
            self.successful_check()
        intent.write_text(json.dumps({"phase": "verified", "commit": "different-sha"}))
        with self.assertRaisesRegex(StateError, "frozen"):
            self.successful_check()
        intent.write_text(json.dumps({"phase": "verified", "commit": "recorded-sha"}))
        self.successful_check()
        self.approve()

    def test_owner_session_correction_preserves_identity_and_invalidates_evidence(self):
        self.store.begin("task", self.root, "Edit note", {"a.txt": "/root/author"},
                         coordinator="/root", session_id="mistaken-child-group",
                         actor_sessions={"/root/author": "child-event"})
        self.successful_check()
        self.approve()
        before = self.store.get("task")
        changed = self.store.assign("task", "a.txt", "/root/author", "Use actual parent hook session",
            session_id="child-event", owner_session_id="parent-session")
        self.assertEqual(changed["session_id"], "parent-session")
        for field in ("assignments", "authors", "paths", "actor_sessions", "actor_session_history"):
            self.assertEqual(changed[field], before[field])
        self.assertEqual(changed["assignment_history"][-1]["previous_owner_session_id"], "mistaken-child-group")
        self.assertEqual(changed["assignment_history"][-1]["owner_session_id"], "parent-session")
        self.assertFalse(self.store.status("task")["gate"]["ready"])
        self.successful_check()
        self.approve()
        self.assertTrue(self.store.status("task")["gate"]["ready"])
        with self.assertRaises(StateError):
            self.store.assign("task", "a.txt", "/root/author", "No-op",
                              session_id="child-event", owner_session_id="parent-session")


if __name__ == "__main__":
    unittest.main()
