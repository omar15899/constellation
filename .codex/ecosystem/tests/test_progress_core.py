"""Progress persists in the portable task without changing its evidence gates."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from helpers import WORKER, Scenario
from ecosystem.core import Engine
from ecosystem.storage import Error


def checkpoint(identifier: str = "milestone-1") -> dict:
    return {"id": identifier, "summary": "The fixture implementation is ready for review.",
            "visibility": "personal", "snapshot": {
                "objectives": ["Verify the fixture result."], "current": "Awaiting independent review.",
                "completed": ["Prepared the artifact."], "decisions": ["Keep one operational store."],
                "findings": [], "verification": ["Fixture check remains a separate gate."],
                "unresolved": ["Review remains pending."], "next_steps": ["Review the result."],
                "references": [{"kind": "documentation", "label": "Fixture result", "value": "result.md"}]}}


def receipt(envelope):
    return {"status": "RECEIVED_LOCAL", "at": "2099-01-01T00:00:00Z",
            **{key: envelope[key] for key in ("task_uid", "content_hash", "target_root_hash", "note_path")}}


class ProgressCoreTests(unittest.TestCase):
    def setUp(self):
        self.scenario = Scenario()
        self.addCleanup(self.scenario.cleanup)
        self.scenario.plan()

    def record(self, **changes):
        progress = self.scenario.call("progress-show")["task_progress"]
        fields = {"checkpoint": checkpoint(), **changes}
        if progress:
            fields["task_uid"] = progress["task_uid"]
        return self.scenario.call("progress-update", **fields)

    def policy(self):
        progress = self.scenario.call("progress-show")["task_progress"]
        path = self.scenario.base / "policy.json"
        path.write_text(json.dumps({"schema_version": 1, "target": {"root": str(self.scenario.base / "journal")}, "sources": [{
            "root": str(self.scenario.root), "alias": progress["source_alias"], "visibility": "personal"}]}))
        return path

    def export(self, policy=None):
        progress = self.scenario.call("progress-show")["task_progress"]
        return self.scenario.call("progress-export", task_uid=progress["task_uid"],
                                  policy_path=str(policy or self.policy()))["envelope"]

    def test_lazy_record_survives_new_engine_and_replan_without_approving(self):
        self.assertIsNone(self.scenario.call("progress-show")["task_progress"])
        recorded = self.record()["task_progress"]
        self.scenario.engine = Engine(self.scenario.root, self.scenario.state_dir)
        self.assertEqual(self.scenario.call("progress-show")["task_progress"], recorded)
        self.scenario.plan()
        self.assertEqual(self.scenario.call("progress-show")["task_progress"], recorded)
        self.assertFalse(self.scenario.call("status")["closure_current"])
        with self.assertRaises(Error):
            self.scenario.close()

    def test_revision_coordinator_and_request_replay_are_preserved(self):
        request = self.scenario.payload(checkpoint=checkpoint(), request_id="progress-event")
        first = self.scenario.engine.execute("progress-update", request)
        second = self.scenario.engine.execute("progress-update", request)
        self.assertTrue(second["replayed"])
        self.assertEqual(first["revision"], second["revision"])
        self.scenario.revision = first["revision"]
        with self.assertRaisesRegex(Error, "different input"):
            self.scenario.engine.execute("progress-update", {**request, "checkpoint": checkpoint("other")})
        uid = first["task_progress"]["task_uid"]
        with self.assertRaisesRegex(Error, "coordinator"):
            self.scenario.call("progress-update", actor=WORKER, task_uid=uid, checkpoint=checkpoint("other"))
        with self.assertRaisesRegex(Error, "Revision conflict"):
            self.scenario.engine.execute("progress-update", {**request, "request_id": "new-event", "task_uid": uid})

    def test_completed_task_annotation_preserves_closure_and_review(self):
        self.scenario.approve()
        self.scenario.close()
        before = self.scenario.call("status")
        self.record()
        after = self.scenario.call("status")
        for key in ("closure", "checks", "gate", "status", "stop_attempts"):
            self.assertEqual(before[key], after[key])
        self.assertTrue(after["closure_current"])

    def test_failed_export_keeps_checkpoint_and_missing_artifacts_do_not_hide_it(self):
        recorded = self.record()["task_progress"]
        policy = self.policy()
        policy.write_text(json.dumps({"schema_version": 1, "sources": []}))
        with self.assertRaises(Error):
            self.export(policy)
        self.assertEqual(self.scenario.call("progress-show")["task_progress"], recorded)
        with self.assertRaises(Error):
            self.export(self.scenario.base / "missing-policy.json")
        self.scenario.root.joinpath("result.md").unlink()
        self.assertEqual(self.scenario.call("progress-show")["task_progress"], recorded)
        self.assertEqual(self.export()["task_uid"], recorded["task_uid"])

    def test_export_runs_after_transaction_and_ack_cannot_confirm_stale_content(self):
        self.record()
        from ecosystem.runtime import progress
        original = progress.export_envelope

        def outside_transaction(*args, **kwargs):
            with self.scenario.engine.store.connection(write=True) as db:
                self.assertIsNotNone(db)
            return original(*args, **kwargs)

        with patch.object(progress, "export_envelope", outside_transaction):
            envelope = self.export()
        self.record(checkpoint=checkpoint("milestone-2"))
        with self.assertRaises(Error):
            self.scenario.call("progress-ack", task_uid=envelope["task_uid"], receipt=receipt(envelope),
                               policy_path=str(self.policy()))
        current = self.export()
        acknowledged = self.scenario.call("progress-ack", task_uid=current["task_uid"], receipt=receipt(current),
                                          policy_path=str(self.policy()))
        self.assertEqual(acknowledged["task_progress"]["receipt"]["status"], "RECEIVED_LOCAL")
        self.assertFalse(self.scenario.call("status")["closure_current"])

    def test_new_task_in_same_session_rejects_previous_uid(self):
        old = self.record()["task_progress"]
        new = Scenario(session=self.scenario.session, task="different-task", root=self.scenario.root,
                       state_dir=self.scenario.state_dir)
        self.addCleanup(new.cleanup)
        new.plan()
        with self.assertRaises(Error):
            new.call("progress-update", task_uid=old["task_uid"], checkpoint=checkpoint())
        current = new.call("progress-update", checkpoint=checkpoint())["task_progress"]
        self.assertNotEqual(current["task_uid"], old["task_uid"])

    def test_ack_response_replay_survives_missing_policy_without_new_export(self):
        self.record()
        policy = self.policy()
        envelope = self.export(policy)
        request = self.scenario.payload(task_uid=envelope["task_uid"], receipt=receipt(envelope),
                                        policy_path=str(policy), request_id="local-receipt")
        first = self.scenario.engine.execute("progress-ack", request)
        policy.unlink()
        second = self.scenario.engine.execute("progress-ack", request)
        self.assertTrue(second["replayed"])
        self.assertEqual(second["revision"], first["revision"])
        with self.assertRaises(Error):
            self.scenario.engine.execute("progress-ack", {**request, "request_id": "new-receipt"})


if __name__ == "__main__":
    unittest.main()
