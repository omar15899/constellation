"""Progress uses existing Git ownership, task recovery and workspace routing."""
from __future__ import annotations

import fcntl
import io
import json
import unittest
from unittest.mock import patch

import test_workflow as git_fixture
import test_workspace as workspace_fixture

w, ws = git_fixture.w, workspace_fixture.ws


def checkpoint(identifier="milestone-1"):
    return {"id": identifier, "summary": "Prepared the fixture result.", "visibility": "personal",
            "snapshot": {"objectives": ["Verify fixture behavior."], "current": "Review pending.",
                         "completed": ["Implemented result."], "decisions": [], "findings": [],
                         "verification": [], "unresolved": ["Independent review."],
                         "next_steps": ["Review the result."], "references": []}}


def update_payload(shown, identifier="milestone-1"):
    payload = {"checkpoint": checkpoint(identifier), "expected_revision": shown["revision"]}
    if shown["task_progress"]:
        payload["task_uid"] = shown["task_progress"]["task_uid"]
    else:
        payload["expected_task_start"] = shown["expected_task_start"]
    return payload


class ProgressWorkflowTests(unittest.TestCase):
    setUp = git_fixture.GitFixture.setUp
    tearDown = git_fixture.GitFixture.tearDown
    commit = git_fixture.GitFixture.commit

    def plan(self):
        self.flow.begin("progress-fixture")
        self.flow.plan({"requirements": ["Read fixture outcome"], "paths": []})

    def record(self, identifier="milestone-1"):
        shown = self.flow.progress_operation("show")
        return self.flow.progress_operation("update", update_payload(shown, identifier))

    def policy(self):
        progress = self.flow.progress_operation("show")["task_progress"]
        path = self.base / "policy.json"
        path.write_text(json.dumps({"schema_version": 1, "target": {"root": str((self.base / "journal").resolve())}, "sources": [{
            "root": str(self.root.resolve()), "alias": progress["source_alias"], "visibility": "personal"}]}))
        return path

    def test_new_instance_and_replan_preserve_checkpoint_and_gates(self):
        self.plan()
        before = self.flow.load()
        recorded = self.record()["task_progress"]
        self.flow = w.Workflow(self.root, self.flow.session)
        self.assertEqual(self.flow.progress_operation("show")["task_progress"], recorded)
        after = self.flow.load()
        for key, value in before.items():
            self.assertEqual(after[key], value)
        self.flow.plan({"requirements": ["Read fixture outcome"], "paths": []})
        self.assertEqual(self.flow.load()["task_progress"], recorded)
        with self.assertRaises(w.Blocked):
            self.flow.finish()

    def test_begin_rotates_task_and_rejects_late_initial_write(self):
        self.plan()
        previous = self.flow.progress_operation("show")
        old = self.record()["task_progress"]
        self.plan()
        self.assertIsNone(self.flow.progress_operation("show")["task_progress"])
        with self.assertRaises(w.Blocked):
            self.flow.progress_operation("update", update_payload(previous))
        with self.assertRaises(w.Blocked):
            self.flow.progress_operation("update", {"task_uid": old["task_uid"],
                "expected_revision": 0, "checkpoint": checkpoint()})
        new = self.record()["task_progress"]
        self.assertNotEqual(old["task_uid"], new["task_uid"])
        archives = list((self.flow.home / "history").glob("*.json"))
        self.assertTrue(any(json.loads(path.read_text()).get("task_progress") == old for path in archives))

    def test_duplicate_checkpoint_is_idempotent_and_stale_revision_rejects(self):
        self.plan()
        initial_request = update_payload(self.flow.progress_operation("show"))
        self.flow.progress_operation("update", initial_request)
        payload = update_payload(self.flow.progress_operation("show"), "second")
        first = self.flow.progress_operation("update", payload)
        before = self.flow.path.read_bytes()
        self.assertEqual(self.flow.progress_operation("update", payload), first)
        self.assertEqual(self.flow.progress_operation("update", initial_request), first)
        self.assertEqual(self.flow.path.read_bytes(), before)
        with self.assertRaises(w.Blocked):
            self.flow.progress_operation("update", {**initial_request, "checkpoint": checkpoint("late-new-initial")})
        with self.assertRaises(w.Blocked):
            self.flow.progress_operation("update", {**payload, "checkpoint": checkpoint("third")})

    def test_no_progress_payload_can_forge_review_or_finished(self):
        self.plan()
        payload = update_payload(self.flow.progress_operation("show"))
        with self.assertRaises(w.Blocked):
            self.flow.progress_operation("update", {**payload, "finished": True})
        with self.assertRaises(w.Blocked):
            self.flow.progress_operation("update", {**payload, "checkpoint": {**checkpoint(), "review": "passed"}})
        self.assertNotIn("task_progress", self.flow.load())

    def test_first_alias_is_explicit_and_immutable_and_cli_rejects_nonobject(self):
        self.plan()
        payload = {**update_payload(self.flow.progress_operation("show")), "source_alias": "personal-research"}
        saved = self.flow.progress_operation("update", payload)
        self.assertEqual(saved["task_progress"]["source_alias"], "personal-research")
        self.assertEqual(self.flow.progress_operation("update", payload), saved)
        with self.assertRaises(w.Blocked):
            self.flow.progress_operation("update", {**update_payload(self.flow.progress_operation("show"), "next"),
                                                    "source_alias": "changed"})
        for operation in ("progress-update", "progress-ack"):
            with self.subTest(operation=operation), patch("sys.stdin", new=io.StringIO("[]")), \
                    patch("sys.stderr", new=io.StringIO()):
                self.assertEqual(w.entrypoint(["--root", str(self.root), "--session", self.flow.session, operation]), 2)

    def test_completed_task_annotation_leaves_completion_evidence_untouched(self):
        self.plan()
        self.flow.review({"Read fixture outcome": "Read the unchanged fixture file."})
        self.flow.finish()
        before = self.flow.load()
        self.record()
        after = self.flow.load()
        for key in ("finished", "publication", "review", "checks", "commits", "stop_attempts"):
            self.assertEqual(before[key], after[key])
        uid = after["task_progress"]["task_uid"]
        self.assertTrue(self.flow.progress_operation("export", {"task_uid": uid})["workflow_finished"])
        (self.root / "forgotten.md").write_text("Not reviewed by the completed task.")
        self.assertFalse(self.flow.progress_operation("export", {"task_uid": uid})["workflow_finished"])

    def test_cli_export_releases_lock_and_failed_export_preserves_local_state(self):
        self.plan()
        progress = self.record()["task_progress"]
        policy = self.policy()
        from ecosystem.runtime import progress as journal
        original = journal.export_envelope

        def unlocked(*args, **kwargs):
            with (self.flow.home / "workflow.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return original(*args, **kwargs)

        arguments = ["--root", str(self.root), "--session", self.flow.session, "progress-export",
                     "--task-uid", progress["task_uid"], "--policy", str(policy)]
        with patch.object(journal, "export_envelope", unlocked), patch("sys.stdout", new=io.StringIO()) as output:
            self.assertEqual(w.main(arguments), 0)
        self.assertEqual(json.loads(output.getvalue())["envelope"]["task_uid"], progress["task_uid"])
        before = self.flow.path.read_bytes()
        policy.write_text(json.dumps({"schema_version": 1, "sources": []}))
        with self.assertRaises(w.Blocked), patch("sys.stdout", new=io.StringIO()):
            w.main(arguments)
        self.assertEqual(self.flow.path.read_bytes(), before)

    def test_receipt_binds_target_note_and_current_version_without_finishing(self):
        self.plan()
        progress = self.record()["task_progress"]
        policy = self.flow.progress_policy(self.policy())
        prepared = self.flow.progress_operation("export", {"task_uid": progress["task_uid"]})
        envelope = w.journal.export_envelope(prepared["task_progress"], source_root=self.root.resolve(),
                                             policy=policy, workflow_finished=prepared["workflow_finished"])
        receipt = {"status": "RECEIVED_LOCAL", "at": "2099-01-01T00:00:00Z",
                   **{key: envelope[key] for key in ("task_uid", "content_hash", "target_root_hash", "note_path")}}
        payload = {"task_uid": progress["task_uid"], "expected_revision": 1, "receipt": receipt}
        for wrong in ({"target_root_hash": "0" * 64}, {"note_path": "different.md"}, {"status": "PUBLISHED"}):
            with self.subTest(wrong=wrong), self.assertRaises(w.Blocked):
                self.flow.progress_operation("ack", {**payload, "receipt": {**receipt, **wrong}}, policy=policy)
        before = self.flow.load()
        acknowledged = self.flow.progress_operation("ack", payload, policy=policy)
        self.assertEqual(acknowledged["task_progress"]["receipt"]["status"], "RECEIVED_LOCAL")
        self.assertEqual(self.flow.load()["finished"], before["finished"])
        saved = self.flow.path.read_bytes()
        self.assertEqual(self.flow.progress_operation("ack", payload, policy=policy), acknowledged)
        self.assertEqual(self.flow.path.read_bytes(), saved)
        self.assertEqual(w.journal.export_envelope(acknowledged["task_progress"], source_root=self.root.resolve(),
                                                  policy=policy), envelope)
        with self.assertRaises(w.Blocked):
            self.flow.progress_operation("ack", payload, policy={**policy, "sources": []})
        self.record("newer")
        with self.assertRaises(w.Blocked):
            self.flow.progress_operation("ack", {**payload, "expected_revision": 2}, policy=policy)

    def test_changed_frozen_upstream_cannot_accept_new_progress(self):
        self.plan()
        self.record()
        payload = update_payload(self.flow.progress_operation("show"), "other")
        original = self.flow.path.read_bytes()
        w.git(self.root, "remote", "set-url", "origin", str(self.base / "different.git"))
        with self.assertRaisesRegex(w.Blocked, "destination changed"):
            self.flow.progress_operation("update", payload)
        self.assertEqual(self.flow.path.read_bytes(), original)
        self.assertEqual(len(self.flow.progress_operation("show")["task_progress"]["milestones"]), 1)


class ProgressWorkspaceTests(unittest.TestCase):
    setUp = workspace_fixture.WorkspaceFixture.setUp
    tearDown = workspace_fixture.WorkspaceFixture.tearDown
    make_repo = workspace_fixture.WorkspaceFixture.make_repo
    plan = workspace_fixture.WorkspaceFixture.plan

    def test_workspace_forwards_selected_owner_without_replacing_publication_progress(self):
        self.plan(["Shared/result.md", "Sibling/result.md"])
        before = self.workspace.load()
        shown = self.workspace.progress_operation("Shared", "show")
        recorded = self.workspace.progress_operation("Shared", "update", update_payload(shown))
        after = self.workspace.status()
        self.assertEqual(after["progress"], before["progress"])
        self.assertEqual(after["repositories"]["Shared"]["task_progress"], recorded["task_progress"])
        self.assertNotIn("task_progress", after["repositories"]["Sibling"])
        self.plan(["Shared/result.md", "Sibling/result.md"])
        self.assertEqual(self.workspace.progress_operation("Shared", "show")["task_progress"], recorded["task_progress"])
        with self.assertRaises(ws.Blocked):
            self.workspace.progress_operation("External", "show")


if __name__ == "__main__":
    unittest.main()
