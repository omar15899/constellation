#!/usr/bin/env python3
"""Exercise projection ownership, removals and refusal paths in temporary repos."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import codex_sync as sync


class ProjectionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".claude").mkdir()
        (self.root / "CLAUDE.md").write_text("# Fixture\n")

    def source(self, rel, text):
        path = self.root / ".claude" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def agent(self, name="auditor"):
        return self.source(f"agents/{name}.md", f"---\nname: {name}\ndescription: Audit.\n---\nInspect.\n")

    def skill(self, name="check"):
        return self.source(f"skills/{name}/SKILL.md", f"---\nname: {name}\ndescription: Check.\n---\nCheck.\n")

    def command(self, name="review"):
        return self.source(f"commands/{name}.md", f"---\nname: {name}\ndescription: Review.\n---\nReview.\n")

    def run_projection(self, **kwargs):
        projection = sync.Projection(**kwargs)
        surface = projection.run(sync.Surface("fixture", self.root))
        return projection, surface

    def snapshot(self):
        return {str(path.relative_to(self.root)): (sync.fingerprint(path), path.lstat().st_mtime_ns)
                for path in self.root.rglob("*") if path.is_file() or path.is_symlink()}

    def manifest(self):
        return json.loads((self.root / ".codex/MANIFEST.json").read_text())

    def write_manifest(self, data):
        (self.root / ".codex/MANIFEST.json").write_text(json.dumps(data))

    def legacy(self):
        data = self.manifest()
        baseline = {"repo_path": str(self.root), "verified_outputs": data.pop("managed_outputs")}
        data.pop("version")
        self.write_manifest(data)
        return baseline

    def native(self):
        directory = self.root / ".codex"
        directory.mkdir(exist_ok=True)
        (directory / "profile.json").write_text('{"mode": "native"}\n')
        (self.root / "AGENTS.md").write_text("# AGENTS.md — Native fixture\nOwn contract.\n")
        return directory

    def test_native_run_and_check_preserve_every_file_without_reading_projection(self):
        self.agent()
        self.run_projection()
        directory = self.native()
        self.source("settings.json", "invalid source JSON must not be read")
        (directory / "MANIFEST.json").write_text("invalid legacy manifest must not be read")
        (directory / "config.toml").write_text("# Native config\n")
        before = self.snapshot()
        for check in (False, True):
            with self.subTest(check=check):
                projection, surface = self.run_projection(check=check)
                self.assertEqual(projection.planned, {})
                self.assertEqual(projection.drift, [])
                self.assertEqual(surface.written, [])
                self.assertTrue(surface.skipped)
                self.assertEqual(self.snapshot(), before)

    def test_direct_apply_cannot_overwrite_native_outputs(self):
        self.native()
        surface = sync.Surface("fixture", self.root)
        projection = sync.Projection()
        projection.write(surface, self.root / "AGENTS.md", "Generated overwrite\n")
        before = self.snapshot()
        projection.apply(surface)
        self.assertEqual(surface.written, [])
        self.assertTrue(surface.skipped)
        self.assertEqual(self.snapshot(), before)

    def test_corrupt_native_marker_refuses_before_mutation(self):
        marker = self.native() / "profile.json"
        for text in ("broken JSON", "[]", "{}", '{"mode": "projection"}', '{"mode": null}'):
            with self.subTest(marker=text):
                marker.write_text(text)
                before = self.snapshot()
                for check in (False, True):
                    with self.assertRaisesRegex(ValueError, "profile marker"):
                        self.run_projection(check=check)
                self.assertEqual(self.snapshot(), before)

    def test_symlink_or_directory_native_marker_refuses(self):
        marker = self.native() / "profile.json"
        marker.unlink()
        target = self.root / "external-profile.json"
        target.write_text('{"mode": "native"}')
        for destination in (target, self.root / "missing-profile.json"):
            marker.symlink_to(destination)
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, "regular local file"):
                self.run_projection()
            self.assertEqual(self.snapshot(), before)
            marker.unlink()
        marker.mkdir()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "regular local file"):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_symlink_codex_directory_refuses_before_reading_marker(self):
        directory = self.native()
        target = self.root / "elsewhere"
        directory.rename(target)
        directory.symlink_to(target, target_is_directory=True)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "symlink ancestor"):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_native_check_needs_no_manifest_hooks_config_or_adapter(self):
        self.native()
        before = self.snapshot()
        projection, surface = self.run_projection(check=True)
        self.assertEqual(projection.drift, [])
        self.assertTrue(surface.skipped)
        self.assertEqual(self.snapshot(), before)

    def test_native_entry_point_errors_refuse_without_writes(self):
        directory = self.native()
        for rel, content in (("AGENTS.md", ""), (".codex/config.toml", "[broken"),
                             (".codex/hooks.json", '{"hooks": []}')):
            with self.subTest(path=rel):
                path = self.root / rel
                previous = path.read_bytes() if path.exists() else None
                path.write_text(content)
                before = self.snapshot()
                with self.assertRaises(ValueError):
                    self.run_projection(check=True)
                self.assertEqual(self.snapshot(), before)
                if previous is None:
                    path.unlink()
                else:
                    path.write_bytes(previous)
        agents = self.root / "AGENTS.md"
        agents.unlink()
        agents.symlink_to(self.root / "CLAUDE.md")
        with self.assertRaisesRegex(ValueError, "regular local file"):
            self.run_projection()
        self.assertFalse((directory / "MANIFEST.json").exists())

    def test_source_removal_prunes_all_owned_output_kinds(self):
        agent, skill, command = self.agent(), self.skill(), self.command()
        self.source("settings.json", json.dumps({"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "true"}]}]}, "permissions": {"deny": ["Bash(rm *)"]}}))
        self.run_projection()
        old = set(self.manifest()["managed_outputs"])
        for path in [agent, skill, command]:
            path.unlink()
        self.source("settings.json", "{}")
        self.run_projection()
        removed = old - set(self.manifest()["managed_outputs"])
        self.assertEqual(removed, {".codex/agents/auditor.toml", ".codex/skills/check",
            ".codex/skills/review/SKILL.md", ".codex/hooks.json", ".codex/hook_shim.py",
            ".codex/rules/default.rules"})
        for rel in removed:
            self.assertFalse(os.path.lexists(self.root / rel), rel)

    def test_check_reports_retirement_without_writes_then_apply_is_idempotent(self):
        source = self.agent()
        self.run_projection()
        source.unlink()
        before = self.snapshot()
        projection, _ = self.run_projection(check=True)
        self.assertTrue(any("auditor.toml would remove" in item for item in projection.drift))
        self.assertEqual(self.snapshot(), before)
        self.run_projection()
        before = self.snapshot()
        _, surface = self.run_projection()
        self.assertEqual(surface.written, [])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.run_projection(check=True)[0].drift, [])

    def test_edited_retired_file_refuses_before_updating_other_outputs(self):
        source = self.agent()
        self.run_projection()
        (self.root / ".codex/agents/auditor.toml").write_text("User work\n")
        source.unlink()
        self.command()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "changed locally"):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_edited_surviving_file_refuses(self):
        self.agent()
        self.run_projection()
        (self.root / ".codex/agents/auditor.toml").write_text("User work\n")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "changed locally"):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_unknown_skills_agents_and_local_files_survive(self):
        self.agent()
        self.run_projection()
        paths = [".codex/agents/personal.toml", ".codex/skills/personal/SKILL.md", ".codex/local/notes.md"]
        for rel in paths:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Personal work\n")
        _, surface = self.run_projection()
        self.assertTrue(any("unmanaged Codex entry preserved" in message for message in surface.warnings))
        for rel in paths:
            self.assertEqual((self.root / rel).read_text(), "Personal work\n")

    def test_command_extra_file_is_preserved_on_retirement(self):
        source = self.command()
        self.run_projection()
        note = self.root / ".codex/skills/review/notes.md"
        note.write_text("Personal work")
        source.unlink()
        self.run_projection()
        self.assertEqual(note.read_text(), "Personal work")
        self.assertFalse(note.with_name("SKILL.md").exists())

    def test_unowned_directory_collision_never_removes_contents(self):
        self.skill()
        directory = self.root / ".codex/skills/check"
        directory.mkdir(parents=True)
        (directory / "notes.md").write_text("Personal work")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "collision"):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_symlink_target_collision_and_changed_owned_link_refuse(self):
        self.skill()
        self.run_projection()
        target = self.root / ".codex/skills/check"
        target.unlink()
        target.symlink_to("../../elsewhere")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "changed locally"):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_file_symlink_and_directory_ancestor_are_never_followed(self):
        self.agent()
        self.run_projection()
        output = self.root / ".codex/agents/auditor.toml"
        outside = self.root / "private-note.txt"
        outside.write_text("Personal work")
        output.unlink()
        output.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "changed locally"):
            self.run_projection()
        self.assertEqual(outside.read_text(), "Personal work")
        output.unlink()
        output.parent.rmdir()
        output.parent.symlink_to(self.root)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "symlink ancestor"):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_manifest_symlink_refuses(self):
        self.run_projection()
        manifest = self.root / ".codex/MANIFEST.json"
        data = manifest.read_text()
        external = self.root / "unmanaged.json"
        external.write_text(data)
        manifest.unlink()
        manifest.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "manifest must not be a symlink"):
            self.run_projection()
        self.assertEqual(external.read_text(), data)

    def test_content_update_does_not_modify_an_external_hard_link(self):
        source = self.agent()
        self.run_projection()
        output = self.root / ".codex/agents/auditor.toml"
        personal = self.root / "personal-copy.toml"
        personal.hardlink_to(output)
        before = personal.read_bytes()
        source.write_text(source.read_text() + "Updated instructions.\n")
        self.run_projection()
        self.assertEqual(personal.read_bytes(), before)
        self.assertNotEqual(output.read_bytes(), before)

    def test_interruption_before_manifest_can_resume_when_outputs_match_plan(self):
        source = self.agent()
        self.run_projection()
        source.write_text(source.read_text() + "Updated instructions.\n")
        original_replace = Path.replace

        def interrupted_replace(path, target):
            if Path(target).name == "MANIFEST.json":
                raise OSError("simulated interruption before manifest update")
            return original_replace(path, target)

        with patch.object(Path, "replace", interrupted_replace):
            with self.assertRaisesRegex(OSError, "simulated interruption"):
                self.run_projection()
        self.run_projection()
        self.assertEqual(self.run_projection(check=True)[0].drift, [])

    def test_command_to_shared_skill_refuses_if_directory_contains_user_work(self):
        source = self.command("review")
        self.run_projection()
        note = self.root / ".codex/skills/review/notes.md"
        note.write_text("Personal work")
        source.unlink()
        self.skill("review")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "collision"):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_duplicate_command_names_and_mismatched_skill_name_refuse(self):
        self.command("review")
        duplicate = self.source("commands/duplicate.md", "---\nname: review\ndescription: Review.\n---\nReview.\n")
        with self.assertRaisesRegex(ValueError, "duplicate command name"):
            self.run_projection()
        self.assertFalse((self.root / ".codex").exists())
        duplicate.unlink()
        self.source("skills/check/SKILL.md", "---\nname: other\ndescription: Check.\n---\nCheck.\n")
        with self.assertRaisesRegex(ValueError, "must match its directory"):
            self.run_projection()
        self.assertFalse((self.root / ".codex").exists())

    def test_ownership_cannot_include_a_link_and_its_descendant(self):
        with self.assertRaisesRegex(ValueError, "overlapping"):
            sync.validate_ownership({
                ".codex/skills/check": {"kind": "symlink", "target": "../../.claude/skills/check"},
                ".codex/skills/check/SKILL.md": {"kind": "file", "sha256": "0" * 64},
            })

    def test_invalid_manifest_and_ownership_paths_write_nothing(self):
        self.run_projection()
        for bad in ["../AGENTS.md", "/tmp/AGENTS.md", ".codex/local/note.md", ".codex/skills/../note"]:
            data = self.manifest()
            data["managed_outputs"][bad] = {"kind": "file", "sha256": "0" * 64}
            self.write_manifest(data)
            before = self.snapshot()
            with self.assertRaisesRegex(ValueError, "invalid managed output"):
                self.run_projection()
            self.assertEqual(self.snapshot(), before)
            del data["managed_outputs"][bad]
            self.write_manifest(data)
        (self.root / ".codex/MANIFEST.json").write_text("broken json")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_invalid_names_duplicate_names_and_late_invalid_hooks_write_nothing(self):
        for name in ["../escape", "/escape", "has space"]:
            self.source("agents/test.md", f"---\nname: {name}\ndescription: Bad.\n---\nBad.\n")
            with self.assertRaisesRegex(ValueError, "invalid agent or skill name"):
                self.run_projection()
            self.assertFalse((self.root / ".codex").exists())
        self.source("agents/test.md", "---\nname: auditor\ndescription: Duplicate.\n---\nDuplicate.\n")
        self.agent()
        with self.assertRaisesRegex(ValueError, "duplicate agent"):
            self.run_projection()
        self.assertFalse((self.root / ".codex").exists())
        (self.root / ".claude/agents/test.md").unlink()
        self.source("settings.json", json.dumps({"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "true", "timeout": -1}]}]}}))
        with self.assertRaisesRegex(ValueError, "timeout"):
            self.run_projection()
        self.assertFalse((self.root / ".codex").exists())

    def test_legacy_adopts_only_outputs_matching_expected(self):
        self.agent()
        self.run_projection()
        self.legacy()
        self.run_projection()
        self.assertEqual(self.manifest()["version"], 2)
        self.legacy()
        (self.root / ".codex/agents/auditor.toml").write_text("Personal work")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "cannot safely adopt"):
            self.run_projection()
        self.assertEqual(self.snapshot(), before)

    def test_verified_baseline_can_migrate_after_source_changes(self):
        agent = self.agent()
        self.command()
        self.run_projection()
        baseline = self.legacy()
        agent.unlink()
        self.source("commands/review.md", "---\nname: review\ndescription: Changed.\n---\nChanged.\n")
        before = self.snapshot()
        projection, _ = self.run_projection(check=True, legacy_ownership=baseline)
        self.assertTrue(projection.drift)
        self.assertEqual(self.snapshot(), before)
        self.run_projection(legacy_ownership=baseline)
        self.assertFalse((self.root / ".codex/agents/auditor.toml").exists())
        self.assertEqual(self.manifest()["version"], 2)

    def test_legacy_baseline_cannot_adopt_changes_or_another_repo(self):
        self.agent()
        self.run_projection()
        baseline = self.legacy()
        (self.root / ".codex/agents/auditor.toml").write_text("Personal work")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "cannot safely adopt"):
            self.run_projection(legacy_ownership=baseline)
        self.assertEqual(self.snapshot(), before)
        baseline["repo_path"] = "/another/repository"
        with self.assertRaisesRegex(ValueError, "another repository"):
            self.run_projection(legacy_ownership=baseline)

    def test_command_to_shared_skill_transition_preserves_source(self):
        command = self.command("review")
        self.run_projection()
        command.unlink()
        source = self.skill("review")
        original = source.read_bytes()
        self.run_projection()
        self.assertTrue((self.root / ".codex/skills/review").is_symlink())
        self.assertEqual(source.read_bytes(), original)

    def test_shared_skill_to_command_transition_preserves_source(self):
        source = self.skill("review")
        self.run_projection()
        source.rename(source.with_suffix(".retired"))
        self.command("review")
        self.run_projection()
        target = self.root / ".codex/skills/review"
        self.assertFalse(target.is_symlink())
        self.assertTrue((target / "SKILL.md").is_file())
        self.assertFalse(source.exists(), "writing a generated command must not follow the old shared symlink")

    def test_markdown_links_rebase_to_the_same_files(self):
        source = self.root / ".claude/commands/review.md"
        target = self.root / ".codex/skills/review/SKILL.md"
        body = ('[local](../scripts/check.py#entry) [sibling](verify.md) '
                '[web](https://example.com/doc) [anchor](#here) [absolute](/tmp/file)\n'
                '[reference]: ../docs/guide.md "Guide"\n')
        rendered = sync.rebase_links(body, source, target)
        self.assertIn("../../../.claude/scripts/check.py#entry", rendered)
        self.assertIn("../../../.claude/commands/verify.md", rendered)
        self.assertIn('[reference]: ../../../.claude/docs/guide.md "Guide"', rendered)
        self.assertIn("[web](https://example.com/doc) [anchor](#here) [absolute](/tmp/file)", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
