"""Behavior checks for the curated, local-only AI home profile installer."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "profiles/install.py"
SPEC = importlib.util.spec_from_file_location("home_profiles", SCRIPT)
assert SPEC and SPEC.loader
profiles = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = profiles
SPEC.loader.exec_module(profiles)


class HomeProfilesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / "checkout"
        self.home = self.root / "other-home"
        for name in set(profiles.MAPPING.values()):
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Profile {{SOURCE_ROOT}}\n" if name.endswith(".md") else "# helper\n")

    def install(self, **kwargs):
        return profiles.install(self.source, self.home, **kwargs)

    def test_read_only_preview_creates_nothing(self):
        result = self.install()
        self.assertEqual(result["status"], "planned")
        self.assertFalse(self.home.exists())
        self.assertEqual(set(result["actions"].values()), {"create"})

    def test_installs_seven_destinations_in_another_home(self):
        result = self.install(apply=True)
        self.assertEqual(result["status"], "installed")
        self.assertIsNone(result["backup"])
        self.assertIn(str(self.source), (self.home / ".claude/CLAUDE.md").read_text())
        self.assertEqual((self.home / ".claude/tools/official_docs.py").read_bytes(),
                         (self.home / ".codex/tools/official_docs.py").read_bytes())
        receipt = self.home / profiles.RECEIPT
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        data = json.loads(receipt.read_text())
        self.assertEqual(set(data["files"]), set(profiles.MAPPING))
        for name, record in data["files"].items():
            self.assertEqual(record["installed_sha256"], profiles.read_file(self.home / name).sha256)

    def test_idempotent_install_keeps_file_identity_and_receipt(self):
        self.install(apply=True)
        before = {name: profiles.read_file(self.home / name) for name in (*profiles.MAPPING, profiles.RECEIPT)}
        result = self.install(apply=True)
        self.assertEqual(result["status"], "unchanged")
        self.assertIsNone(result["backup"])
        self.assertEqual(before, {name: profiles.read_file(self.home / name) for name in before})

    def test_settings_and_private_sentinels_are_never_adopted(self):
        names = (".codex/config.toml", ".codex/auth.json", ".claude/settings.json",
                 ".claude/.credentials.json", ".claude/projects/private.jsonl")
        for name in names:
            path = self.home / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic private sentinel")
        before = {name: profiles.read_file(self.home / name) for name in names}
        self.install(apply=True, backup_existing=True)
        self.assertEqual(before, {name: profiles.read_file(self.home / name) for name in names})

    def test_unowned_conflict_fails_before_any_profile_write(self):
        path = self.home / ".claude/docs/README.md"
        path.parent.mkdir(parents=True)
        path.write_text("Personal guide\n")
        with self.assertRaisesRegex(profiles.ProfileError, "backup-existing"):
            self.install(apply=True)
        self.assertEqual(path.read_text(), "Personal guide\n")
        self.assertFalse((self.home / ".codex/AGENTS.md").exists())
        self.assertFalse((self.home / profiles.RECEIPT).exists())

    def test_explicit_adoption_preserves_original_bytes_and_mode(self):
        path = self.home / ".claude/CLAUDE.md"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"Original personal instructions\n")
        path.chmod(0o600)
        result = self.install(apply=True, backup_existing=True)
        backup = Path(result["backup"]) / ".claude/CLAUDE.md"
        self.assertEqual(backup.read_bytes(), b"Original personal instructions\n")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_local_edit_requires_explicit_adoption(self):
        self.install(apply=True)
        path = self.home / ".claude/CLAUDE.md"
        path.write_text("Local edit\n")
        with self.assertRaisesRegex(profiles.ProfileError, "backup-existing"):
            self.install(apply=True)
        result = self.install(apply=True, backup_existing=True)
        self.assertEqual((Path(result["backup"]) / ".claude/CLAUDE.md").read_text(), "Local edit\n")

    def test_owned_update_preserves_previous_release(self):
        self.install(apply=True)
        path = self.home / ".claude/CLAUDE.md"
        old = path.read_bytes()
        (self.source / profiles.MAPPING[".claude/CLAUDE.md"]).write_text("# Updated\n")
        result = self.install(apply=True)
        self.assertEqual(path.read_bytes(), b"# Updated\n")
        self.assertEqual((Path(result["backup"]) / ".claude/CLAUDE.md").read_bytes(), old)

    def test_source_and_destination_are_same_file_is_unchanged(self):
        self.home = self.root
        self.source = self.home / ".codex"
        for name in set(profiles.MAPPING.values()):
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Profile\n" if name.endswith(".md") else "# helper\n")
        path = self.source / "AGENTS.md"
        before = profiles.read_file(path)
        result = self.install(apply=True)
        self.assertEqual(result["actions"][".codex/AGENTS.md"], "unchanged")
        self.assertEqual(profiles.read_file(path), before)

    def test_symlink_ancestor_leaf_and_source_are_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.home.mkdir()
        (self.home / ".claude").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(profiles.ProfileError):
            self.install(apply=True, backup_existing=True)
        self.assertEqual(list(outside.iterdir()), [])
        (self.home / ".claude").unlink()
        (self.home / ".claude").mkdir()
        (self.home / ".claude/CLAUDE.md").symlink_to(self.source / "AGENTS.md")
        with self.assertRaises((OSError, profiles.ProfileError)):
            self.install(apply=True, backup_existing=True)
        (self.home / ".claude/CLAUDE.md").unlink()
        source = self.source / "AGENTS.md"
        source.unlink()
        source.symlink_to(self.source / ".codex/profiles/claude/CLAUDE.md")
        with self.assertRaises((OSError, profiles.ProfileError)):
            self.install(apply=True)

    def test_receipt_symlink_or_permission_change_is_rejected(self):
        self.install(apply=True)
        receipt = self.home / profiles.RECEIPT
        original = self.root / "receipt-copy.json"
        receipt.rename(original)
        receipt.symlink_to(original)
        with self.assertRaises((OSError, profiles.ProfileError)):
            self.install(apply=True, backup_existing=True)
        receipt.unlink()
        original.rename(receipt)
        receipt.chmod(0o644)
        with self.assertRaisesRegex(profiles.ProfileError, "receipt permissions"):
            self.install(apply=True, backup_existing=True)

    def test_hardlinks_and_invalid_receipt_cannot_authorize_overwrite(self):
        target = self.home / ".claude/CLAUDE.md"
        target.parent.mkdir(parents=True)
        os.link(self.source / "AGENTS.md", target)
        with self.assertRaises(profiles.ProfileError):
            self.install(apply=True, backup_existing=True)
        target.unlink()
        self.install(apply=True)
        receipt = self.home / profiles.RECEIPT
        data = json.loads(receipt.read_text())
        data["files"][".codex/config.toml"] = data["files"][".codex/AGENTS.md"]
        receipt.write_text(json.dumps(data))
        with self.assertRaisesRegex(profiles.ProfileError, "receipt is invalid"):
            self.install(apply=True, backup_existing=True)

    def test_write_failure_restores_originals_and_removes_new_files(self):
        original = self.home / ".claude/CLAUDE.md"
        original.parent.mkdir(parents=True)
        original.write_bytes(b"Keep me\n")
        real_replace = profiles.replace_file

        def fail(path, data, mode, **kwargs):
            if path == self.home / ".claude/README.md":
                raise OSError("simulated disk failure")
            return real_replace(path, data, mode, **kwargs)

        with patch.object(profiles, "replace_file", side_effect=fail):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                self.install(apply=True, backup_existing=True)
        self.assertEqual(original.read_bytes(), b"Keep me\n")
        self.assertFalse((self.home / ".codex/AGENTS.md").exists())
        self.assertFalse((self.home / profiles.RECEIPT).exists())
        backups = list((self.home / ".codex/backups/profiles").iterdir())
        self.assertEqual((backups[0] / ".claude/CLAUDE.md").read_bytes(), b"Keep me\n")

    def test_rollback_preserves_concurrent_edits(self):
        real_replace = profiles.replace_file
        changed = self.home / ".codex/AGENTS.md"

        def fail(path, data, mode, **kwargs):
            if path == self.home / ".claude/README.md":
                changed.write_text("Concurrent edit\n")
                raise OSError("simulated disk failure")
            return real_replace(path, data, mode, **kwargs)

        with patch.object(profiles, "replace_file", side_effect=fail):
            with self.assertRaisesRegex(profiles.ProfileError, "concurrent or unrecoverable"):
                self.install(apply=True)
        self.assertEqual(changed.read_text(), "Concurrent edit\n")
        self.assertFalse((self.home / profiles.RECEIPT).exists())

    def _existing_instructions(self) -> Path:
        target = self.home / ".claude/CLAUDE.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"Original instructions\n")
        return target

    def _assert_recovery_contains(self, data: bytes) -> None:
        root = self.home / ".codex/backups/profiles"
        self.assertTrue(root.is_dir())
        self.assertTrue(any(path.read_bytes() == data for path in root.rglob("*") if path.is_file()))
        self.assertEqual(list(self.home.rglob(".profile-next-*")), [])
        self.assertEqual(list(self.home.rglob(".profile-recovery-*")), [])

    def test_edit_on_replace_entry_is_captured_and_preserved(self):
        target = self._existing_instructions()
        unique = b"Concurrent edit on replacement entry\n"
        real_replace = profiles.replace_file
        triggered = False

        def edit(path, data, mode, **kwargs):
            nonlocal triggered
            if path == target and not triggered:
                triggered = True
                target.write_bytes(unique)
            return real_replace(path, data, mode, **kwargs)

        with patch.object(profiles, "replace_file", side_effect=edit):
            with self.assertRaisesRegex(profiles.ProfileError, "changed during staging"):
                self.install(apply=True, backup_existing=True)
        self.assertEqual(target.read_bytes(), unique)
        self._assert_recovery_contains(unique)

    def test_edit_during_staging_is_captured_and_preserved(self):
        target = self._existing_instructions()
        unique = b"Concurrent edit during mkstemp\n"
        real_mkstemp = profiles.tempfile.mkstemp
        triggered = False

        def edit(*args, **kwargs):
            nonlocal triggered
            if kwargs.get("dir") == target.parent and not triggered:
                triggered = True
                target.write_bytes(unique)
            return real_mkstemp(*args, **kwargs)

        with patch.object(profiles.tempfile, "mkstemp", side_effect=edit):
            with self.assertRaisesRegex(profiles.ProfileError, "changed during staging"):
                self.install(apply=True, backup_existing=True)
        self.assertEqual(target.read_bytes(), unique)
        self._assert_recovery_contains(unique)

    def test_edit_immediately_before_capture_is_not_lost(self):
        target = self._existing_instructions()
        unique = b"Concurrent edit at rename entry\n"
        real_rename = profiles.os.rename
        triggered = False

        def edit(source, destination, *args, **kwargs):
            nonlocal triggered
            if source == target and not triggered:
                triggered = True
                target.write_bytes(unique)
            return real_rename(source, destination, *args, **kwargs)

        with patch.object(profiles.os, "rename", side_effect=edit):
            with self.assertRaisesRegex(profiles.ProfileError, "changed during staging"):
                self.install(apply=True, backup_existing=True)
        self.assertEqual(target.read_bytes(), unique)
        self._assert_recovery_contains(unique)

    def test_new_destination_before_promotion_is_never_clobbered(self):
        target = self._existing_instructions()
        original = target.read_bytes()
        unique = b"Another writer recreated the destination\n"
        real_link = profiles.os.link
        triggered = False

        def edit(source, destination, *args, **kwargs):
            nonlocal triggered
            if destination == target and not triggered:
                triggered = True
                target.write_bytes(unique)
            return real_link(source, destination, *args, **kwargs)

        with patch.object(profiles.os, "link", side_effect=edit):
            with self.assertRaisesRegex(profiles.ProfileError, "Promotion failed"):
                self.install(apply=True, backup_existing=True)
        self.assertEqual(target.read_bytes(), unique)
        self._assert_recovery_contains(original)

    def test_unexpected_destination_on_initial_create_is_preserved(self):
        target = self.home / ".claude/CLAUDE.md"
        unique = b"Another writer created this new profile\n"
        real_link = profiles.os.link
        triggered = False

        def edit(source, destination, *args, **kwargs):
            nonlocal triggered
            if destination == target and not triggered:
                triggered = True
                target.write_bytes(unique)
            return real_link(source, destination, *args, **kwargs)

        with patch.object(profiles.os, "link", side_effect=edit):
            with self.assertRaises(FileExistsError):
                self.install(apply=True)
        self.assertEqual(target.read_bytes(), unique)
        self.assertFalse((self.home / profiles.RECEIPT).exists())

    def test_success_retains_inode_for_a_writer_with_an_open_descriptor(self):
        target = self._existing_instructions()
        unique = b"Late write through the captured original descriptor\n"
        real_link = profiles.os.link
        triggered = False
        with target.open("r+b") as writer:
            original_inode = os.fstat(writer.fileno()).st_ino

            def edit(source, destination, *args, **kwargs):
                nonlocal triggered
                if destination == target and not triggered:
                    triggered = True
                    writer.seek(0)
                    writer.write(unique)
                    writer.truncate()
                    writer.flush()
                return real_link(source, destination, *args, **kwargs)

            with patch.object(profiles.os, "link", side_effect=edit):
                result = self.install(apply=True, backup_existing=True)
        self.assertEqual(result["status"], "installed")
        self.assertNotEqual(target.read_bytes(), unique)
        self._assert_recovery_contains(unique)
        captures = list((Path(result["backup"]) / "captured").rglob("original"))
        self.assertTrue(any(path.stat().st_ino == original_inode for path in captures))

    def test_rollback_capture_preserves_an_edit_at_the_delete_boundary(self):
        real_replace = profiles.replace_file
        real_rename = profiles.os.rename
        target = self.home / ".codex/AGENTS.md"
        unique = b"Concurrent edit at rollback capture\n"
        failing = False

        def fail(path, data, mode, **kwargs):
            nonlocal failing
            if path == self.home / ".claude/README.md":
                failing = True
                raise OSError("simulated later failure")
            return real_replace(path, data, mode, **kwargs)

        def edit(source, destination, *args, **kwargs):
            if failing and source == target:
                target.write_bytes(unique)
            return real_rename(source, destination, *args, **kwargs)

        with patch.object(profiles, "replace_file", side_effect=fail), patch.object(profiles.os, "rename", side_effect=edit):
            with self.assertRaisesRegex(profiles.ProfileError, "concurrent or unrecoverable"):
                self.install(apply=True)
        self.assertEqual(target.read_bytes(), unique)
        self._assert_recovery_contains(unique)


if __name__ == "__main__":
    unittest.main(verbosity=2)
