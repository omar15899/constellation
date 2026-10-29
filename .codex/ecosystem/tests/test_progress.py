"""Independent behavioural fixtures for curated, recoverable task progress."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CODEX_ROOT = Path(__file__).resolve().parents[2]
if str(CODEX_ROOT) not in sys.path:
    sys.path.insert(0, str(CODEX_ROOT))
from ecosystem.runtime import progress as subject


CREATED = "2026-10-18T10:00:00Z"
FIRST = "2026-10-18T11:00:00Z"
SECOND = "2026-10-19T11:00:00Z"
RECEIVED = "2026-10-19T12:00:00Z"


def payload(identifier: str = "first", visibility: str = "personal") -> dict:
    return {"id": identifier, "visibility": visibility, "summary": "Implemented the numerical experiment.",
            "snapshot": {"objectives": ["Compare two convergent methods."],
                         "current": "Independent review remains pending.",
                         "completed": ["Implemented both methods."],
                         "decisions": ["Use identical initial conditions."],
                         "findings": ["The coarse grid has greater error."],
                         "verification": ["Observed decreasing error on three grids."],
                         "unresolved": ["The convergence order is not yet established."],
                         "next_steps": ["Check the independent formulation."],
                         "references": [{"kind": "commit", "label": "Implementation", "value": "0123456789abcdef"},
                                        {"kind": "experiment", "label": "Grid study", "value": "results/grid.json"}]}}


def receipt(envelope: dict) -> dict:
    return {"status": "RECEIVED_LOCAL", "at": RECEIVED,
            **{key: envelope[key] for key in ("task_uid", "content_hash", "target_root_hash", "note_path")}}


class ProgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="constellation-progress-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "source"
        self.root.mkdir()
        self.target = self.base / "vault"
        self.policy = {"schema_version": 1, "target": {"root": str(self.target)},
                       "sources": [{"root": str(self.root), "alias": "source", "visibility": "personal"}]}
        self.initial = subject.create_progress("Local operational objective.", source_alias="source", created_at=CREATED)
        self.state = subject.checkpoint(self.initial, payload(), at=FIRST)

    def envelope(self, state: dict | None = None, **options: object) -> dict:
        return subject.export_envelope(state or self.state, source_root=self.root, policy=self.policy, **options)

    def test_identity_is_not_a_session_and_initial_state_has_no_export_authority(self) -> None:
        other = subject.create_progress("Local operational objective.", source_alias="source", created_at=CREATED)
        self.assertNotEqual(self.initial["task_uid"], other["task_uid"])
        self.assertEqual([], self.initial["milestones"])
        with self.assertRaises(subject.ProgressError):
            self.envelope(self.initial)
        for invalid in (None, "", False):
            corrupted = {**self.initial, "task_uid": invalid}
            with self.assertRaises(subject.ProgressError):
                subject.validate_progress(corrupted)

    def test_resume_in_a_fresh_python_process_preserves_the_full_snapshot(self) -> None:
        path = self.base / "state.json"
        path.write_text(json.dumps(self.state))
        program = ("import json,sys;sys.path.insert(0,sys.argv[1]);"
                   "from ecosystem.runtime.progress import validate_progress;"
                   "print(json.dumps(validate_progress(json.load(open(sys.argv[2])))))")
        completed = subprocess.run([sys.executable, "-I", "-B", "-c", program, str(CODEX_ROOT), str(path)],
                                   capture_output=True, text=True, check=True)
        self.assertEqual(self.state, json.loads(completed.stdout))
        self.assertEqual(payload()["snapshot"], self.state["milestones"][-1]["snapshot"])

    def test_retry_is_noop_even_after_a_newer_checkpoint(self) -> None:
        later = subject.checkpoint(self.state, payload("second"), at=SECOND)
        self.assertEqual(later, subject.checkpoint(later, payload(), at=RECEIVED))
        self.assertEqual("second", later["milestones"][-1]["id"])
        self.assertEqual(1, len(self.state["milestones"]))

    def test_id_conflict_requires_a_new_correction_milestone(self) -> None:
        changed = payload()
        changed["snapshot"]["findings"] = ["Independent replication contradicts the original observation."]
        with self.assertRaises(subject.ProgressError):
            subject.checkpoint(self.state, changed, at=SECOND)
        changed["id"] = "correction"
        amended = subject.checkpoint(self.state, changed, at=SECOND)
        self.assertEqual(payload()["snapshot"]["findings"], amended["milestones"][0]["snapshot"]["findings"])

    def test_chronology_and_stored_content_are_validated(self) -> None:
        with self.assertRaises(subject.ProgressError):
            subject.checkpoint(self.state, payload("second"), at=CREATED)
        for mutate in (
            lambda state: state["milestones"][0].update(summary="tampered"),
            lambda state: state.update(created_at=None),
            lambda state: state["milestones"].append(deepcopy(state["milestones"][0])),
        ):
            state = deepcopy(self.state)
            mutate(state)
            with self.assertRaises(subject.ProgressError):
                subject.validate_progress(state)

    def test_timezone_conversion_overflow_is_a_progress_error(self) -> None:
        for timestamp in ("0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00"):
            with self.subTest(timestamp=timestamp), self.assertRaises(subject.ProgressError):
                subject.create_progress("Timestamp boundary", source_alias="source", created_at=timestamp)

    def test_unknown_visibility_is_default_and_latest_restriction_denies_export(self) -> None:
        unspecified = payload("unknown")
        del unspecified["visibility"]
        for event in (unspecified, payload("restricted", "restricted")):
            state = subject.checkpoint(self.state, event, at=SECOND)
            with self.assertRaises(subject.ProgressError):
                self.envelope(state)

    def test_personal_checkpoint_cannot_export_restricted_history_or_initial_objective(self) -> None:
        private = payload("private", "restricted")
        private["summary"] = "PRIVATE_HISTORY_MARKER"
        private["snapshot"]["findings"] = ["PRIVATE_FINDING_MARKER"]
        state = subject.checkpoint(self.initial, private, at=FIRST)
        state = subject.checkpoint(state, payload("shareable"), at=SECOND)
        envelope = self.envelope(state)
        encoded = json.dumps(envelope)
        self.assertNotIn("PRIVATE_", encoded)
        self.assertNotIn(self.initial["objective"], encoded)
        self.assertEqual(["shareable"], [entry["id"] for entry in envelope["milestones"]])

    def test_policy_never_inherits_authority_from_parent_registration_or_alias(self) -> None:
        sibling = self.base / "source-extra"
        nested = self.root / "nested"
        sibling.mkdir()
        nested.mkdir()
        (nested / ".git").mkdir()
        for root in (self.base, sibling, nested):
            with self.assertRaises(subject.ProgressError):
                subject.export_envelope(self.state, source_root=root, policy=self.policy)
        for visibility in ("unknown", "restricted"):
            policy = deepcopy(self.policy)
            policy["sources"][0]["visibility"] = visibility
            with self.assertRaises(subject.ProgressError):
                subject.export_envelope(self.state, source_root=self.root, policy=policy)

    def test_missing_malformed_or_duplicate_policy_fails_closed(self) -> None:
        policies = [{}, {"schema_version": 1, "sources": []},
                    {**self.policy, "sources": []}, {**self.policy, "model": "irrelevant"}]
        duplicate = deepcopy(self.policy)
        duplicate["sources"].append(deepcopy(duplicate["sources"][0]))
        policies.append(duplicate)
        for policy in policies:
            with self.subTest(policy=policy), self.assertRaises(subject.ProgressError):
                subject.export_envelope(self.state, source_root=self.root, policy=policy)

    def test_source_and_destination_symlinks_are_not_authorisation(self) -> None:
        linked = self.base / "link"
        linked.symlink_to(self.root, target_is_directory=True)
        policy = deepcopy(self.policy)
        policy["sources"][0]["root"] = str(linked)
        with self.assertRaises(subject.ProgressError):
            subject.export_envelope(self.state, source_root=linked, policy=policy)
        policy = deepcopy(self.policy)
        policy["target"]["root"] = str(linked)
        with self.assertRaises(subject.ProgressError):
            subject.export_envelope(self.state, source_root=self.root, policy=policy)

    def test_missing_vault_does_not_prevent_local_progress_or_write_any_files(self) -> None:
        self.assertFalse(self.target.exists())
        before = deepcopy(self.state)
        envelope = self.envelope()
        subject.render_note(envelope)
        subject.render_dashboard([subject.dashboard_entry(envelope)])
        self.assertEqual(before, self.state)
        self.assertFalse(self.target.exists())
        self.assertIsNone(self.state["receipt"])

    def test_typed_references_reject_credentials_private_state_and_active_syntax(self) -> None:
        for value in ("https://user:password@example.org/doc", "https://example.org/doc?token=secret",
                      "https://example.org/doc#secret", "javascript:alert(1)", "http://example.org/doc",
                      "https://example.org/%0Asecret", "https://example.org/%250Asecret",
                      "../private.md", ".codex/sessions/rollout.jsonl", ".codex/auth.json",
                      ".codex/memories/MEMORY.md", ".codex/learning/PROFILE.md", ".env",
                      "https://example.org/api_key/secret"):
            event = payload()
            event["snapshot"]["references"] = [{"kind": "documentation", "label": "Unsafe reference", "value": value}]
            with self.subTest(value=value), self.assertRaises(subject.ProgressError):
                subject.checkpoint(self.initial, event, at=FIRST)

    def test_reference_validation_does_not_read_source_files(self) -> None:
        event = payload()
        event["snapshot"]["references"] = [{"kind": "documentation", "label": "Paper", "value": "https://example.org/paper.pdf"},
                                             {"kind": "experiment", "label": "Future artifact", "value": "missing/results.json"}]
        state = subject.checkpoint(self.initial, event, at=FIRST)
        self.assertEqual(event["snapshot"]["references"], self.envelope(state)["snapshot"]["references"])

    def test_narrative_cannot_inject_a_managed_segment_or_transclusion(self) -> None:
        for text in ("<script>alert(1)</script>", "![[private]]", "<!-- marker -->", "```python",
                     "line one\nline two", "https://example.org/?token=secret", "data:text/html,unsafe"):
            event = payload()
            event["summary"] = text
            with self.subTest(text=text), self.assertRaises(subject.ProgressError):
                subject.checkpoint(self.initial, event, at=FIRST)
        event = payload()
        event["summary"] = "[visible](javascript:payload)"
        with self.assertRaises(subject.ProgressError):
            subject.checkpoint(self.initial, event, at=FIRST)

    def test_envelope_tampering_and_unknown_fields_are_rejected(self) -> None:
        for key, value in (("note_path", "../../escape.md"), ("content_hash", "0" * 64),
                           ("source_root", str(self.root)), ("workflow_finished", "true"),
                           ("target_root_hash", "not-a-hash")):
            envelope = self.envelope()
            envelope[key] = value
            with self.subTest(key=key), self.assertRaises(subject.ProgressError):
                subject.validate_envelope(envelope)

    def test_only_trusted_workflow_flag_can_render_completion(self) -> None:
        event = payload()
        event["snapshot"]["current"] = "Everything is complete and published."
        state = subject.checkpoint(self.initial, event, at=FIRST)
        ordinary = subject.render_note(self.envelope(state))
        self.assertIn('status: "in_progress"', ordinary)
        finished = subject.render_note(self.envelope(state, workflow_finished=True))
        self.assertIn('status: "completed"', finished)
        self.assertTrue(any(disclaimer in finished for disclaimer in (
            "no demuestra por sí solo conclusiones científicas",
            "does not by itself prove scientific conclusions",
        )))
        self.assertEqual(self.state, subject.validate_progress(self.state))

    def test_exact_receipt_is_idempotent_and_never_completes_task(self) -> None:
        envelope = self.envelope()
        ack = receipt(envelope)
        result = subject.acknowledge(self.state, envelope=envelope, receipt=ack)
        self.assertEqual("RECEIVED_LOCAL", result["receipt"]["status"])
        self.assertEqual(self.state["milestones"], result["milestones"])
        self.assertEqual(result, subject.acknowledge(result, envelope=envelope, receipt={**ack, "at": "2026-10-20T12:00:00Z"}))
        self.assertNotIn("finished", result)
        self.assertNotIn("published", result)

    def test_receipt_rejects_stale_wrong_task_target_path_and_publication(self) -> None:
        envelope = self.envelope()
        for key, value in (("status", "PUBLISHED"), ("content_hash", "0" * 64),
                           ("task_uid", "00000000-0000-0000-0000-000000000000"),
                           ("target_root_hash", "0" * 64), ("note_path", "other.md")):
            wrong = {**receipt(envelope), key: value}
            with self.subTest(key=key), self.assertRaises(subject.ProgressError):
                subject.acknowledge(self.state, envelope=envelope, receipt=wrong)
        newer = subject.checkpoint(self.state, payload("newer"), at=SECOND)
        with self.assertRaises(subject.ProgressError):
            subject.acknowledge(newer, envelope=envelope, receipt=receipt(envelope))
        other_target = deepcopy(self.policy)
        other_target["target"]["root"] = str(self.base / "other-vault")
        redirected = subject.export_envelope(self.state, source_root=self.root, policy=other_target)
        with self.assertRaises(subject.ProgressError):
            subject.acknowledge(self.state, envelope=redirected, receipt=receipt(envelope))

    def test_note_path_stays_on_creation_day_and_render_preserves_manual_tail(self) -> None:
        envelope = self.envelope()
        note = subject.render_note(envelope)
        self.assertTrue(note.startswith("---\n"))
        self.assertIn('subdomain: "Execution_Traces"', note)
        self.assertIn('tags: ["constellation", "progress"]', note)
        self.assertEqual(note, subject.render_note(envelope, note))
        tail = "\n\n## My observations\nOriginal manual text.\n"
        note += tail
        updated = self.envelope(subject.checkpoint(self.state, payload("later"), at=SECOND))
        self.assertEqual(envelope["note_path"], updated["note_path"])
        self.assertIn("/2026-10-18/constellation_source_", updated["note_path"])
        output = subject.render_note(updated, note)
        self.assertTrue(output.endswith(tail))
        self.assertIn('updated: "2026-10-19"', output)

    def test_edited_managed_content_metadata_or_ambiguous_markers_are_rejected(self) -> None:
        envelope = self.envelope()
        note = subject.render_note(envelope)
        bad = ("foreign note", note.replace('author: "Omar"', 'author: "Other"'),
               note.replace("Independent review remains pending", "Everything approved"),
               note + "\n<!-- constellation-progress:foreign:sha256=" + "0" * 64 + " -->",
               note + f"\n<!-- /constellation-progress:{envelope['task_uid']} -->")
        for existing in bad:
            with self.subTest(existing=existing[:60]), self.assertRaises(subject.ProgressError):
                subject.render_note(envelope, existing)

    def test_dashboard_is_idempotent_preserves_tail_and_rejects_duplicate_task(self) -> None:
        envelope = self.envelope()
        dashboard = subject.render_dashboard([subject.dashboard_entry(envelope)])
        self.assertTrue(dashboard.startswith("---\n"))
        self.assertEqual(dashboard, subject.render_dashboard([subject.dashboard_entry(envelope)], dashboard))
        tail = "\nManual prioritisation stays here.\n"
        self.assertTrue(subject.render_dashboard([subject.dashboard_entry(envelope)], dashboard + tail).endswith(tail))
        with self.assertRaises(subject.ProgressError):
            subject.render_dashboard([subject.dashboard_entry(envelope), subject.dashboard_entry(envelope)])
        with self.assertRaises(subject.ProgressError):
            subject.render_dashboard([subject.dashboard_entry(envelope)], dashboard.replace("# Constellation", "# Manipulated heading"))

    def test_dashboard_index_is_thin_and_cannot_mix_destinations(self) -> None:
        entry = subject.dashboard_entry(self.envelope())
        self.assertNotIn("snapshot", entry)
        self.assertNotIn("milestones", entry)
        self.assertNotIn("completed", entry)
        second_state = subject.create_progress("Another objective", source_alias="source", created_at=CREATED)
        second_state = subject.checkpoint(second_state, payload(), at=FIRST)
        second = subject.dashboard_entry(self.envelope(second_state))
        second["target_root_hash"] = "0" * 64
        with self.assertRaises(subject.ProgressError):
            subject.render_dashboard([entry, second])
        with self.assertRaises(subject.ProgressError):
            subject.render_dashboard([{**entry, "snapshot": {}}])


if __name__ == "__main__":
    unittest.main()
