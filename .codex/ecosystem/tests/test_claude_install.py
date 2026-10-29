"""Exercise real portable Claude installations without model or account access."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SOURCE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_DIR))

from build import BUNDLE_MANIFEST, INSTALL_RECEIPT, build_bundle, file_record, verify_bundle
import claude as installer
from install import InstallError


def snapshot(root: Path) -> dict:
    result = {}
    if root.exists():
        for directory, subdirs, files in os.walk(root, followlinks=False):
            for name in subdirs + files:
                path = Path(directory) / name
                relative = path.relative_to(root).as_posix()
                if path.is_symlink():
                    result[relative] = ("link", os.readlink(path))
                elif path.is_file():
                    result[relative] = ("file", path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
                else:
                    result[relative] = ("directory", stat.S_IMODE(path.stat().st_mode))
    return result


class ClaudeInstallationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.shared = tempfile.TemporaryDirectory(prefix="claude-distribution-")
        cls.bundle = Path(cls.shared.name).resolve() / "release with spaces"
        manifest = build_bundle(cls.bundle)
        cls.skill_relative = Path("skills") / manifest["modules"][0] / "SKILL.md"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.shared.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="claude-install-")
        self.base = Path(self.temporary.name).resolve()
        self.home = self.base / "laptop one" / "claude home"
        self.target = self.home / "skills/constellation"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def changed_bundle(self) -> Path:
        result = self.base / "next release"
        shutil.copytree(self.bundle, result)
        manifest = json.loads((result / BUNDLE_MANIFEST).read_text())
        for name in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
            path = result / name
            plugin = json.loads(path.read_text())
            plugin["version"] = "1.3.2"
            path.write_text(json.dumps(plugin, sort_keys=True, indent=2) + "\n")
            manifest["files"][name] = file_record(path)
        (result / BUNDLE_MANIFEST).write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        verify_bundle(result)
        return result

    def owned_130(self, *, home: Path | None = None, modules: list[str] | None = None) -> Path:
        """Reconstruct the old layout as data; never import or run its code."""
        home = self.home if home is None else home
        target = home / "skills/constellation"
        build_bundle(target, modules=modules, source_root=self.bundle)
        legacy_docs = {
            "architecture": "ARCHITECTURE", "compatibility": "COMPATIBILITY",
            "migrations": "MIGRATION", "progress": "PROGRESS", "evaluation": "EVALUATION",
        }
        manifest = json.loads((target / BUNDLE_MANIFEST).read_text())
        for current, previous in legacy_docs.items():
            source = f"ecosystem/docs/{current}.md"
            destination = f"ecosystem/{previous}.md"
            (target / source).rename(target / destination)
            manifest["files"][destination] = manifest["files"].pop(source)
        (target / "ecosystem/docs").rmdir()
        historical = target / "ecosystem/evaluation.json"
        historical.write_text('{"fixture":"historical evaluation"}\n')
        historical.chmod(0o644)
        manifest["files"]["ecosystem/evaluation.json"] = file_record(historical)
        for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
            path = target / relative
            metadata = json.loads(path.read_text())
            metadata["version"] = "1.3.0"
            path.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n")
            manifest["files"][relative] = file_record(path)
        (target / BUNDLE_MANIFEST).write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        marker = target / INSTALL_RECEIPT
        marker.write_text(json.dumps({
            "schema": 1, "owner": "constellation-claude-skills-dir",
            "plugin_id": "constellation@skills-dir", "version": "1.3.0",
            "modules": manifest["modules"], "bundle_sha256": _manifest_hash(target),
        }, sort_keys=True, indent=2) + "\n")
        marker.chmod(0o600)
        lock = home / installer.LOCK_PATH
        lock.parent.mkdir(mode=0o700, parents=True)
        lock.touch(mode=0o600)
        return target

    def test_130_upgrade_supports_full_and_partial_releases_without_executing_old_code(self) -> None:
        available = json.loads((self.bundle / BUNDLE_MANIFEST).read_text())["modules"]
        for label, modules in (("full", available), ("partial", available[:1])):
            with self.subTest(layout=label):
                home = self.base / label
                target = self.owned_130(home=home, modules=modules)
                settings = home / "settings.json"
                settings.write_text('{"model":"unchanged-choice"}\n')
                settings_before = settings.read_bytes(), settings.stat().st_mode
                # A verified predecessor is data to the new installer, not an
                # implementation that can participate in its own verification.
                manifest = json.loads((target / BUNDLE_MANIFEST).read_text())
                for relative in ("ecosystem/build.py", "ecosystem/claude.py"):
                    path = target / relative
                    path.write_text('raise AssertionError("previous code must not execute")\n')
                    manifest["files"][relative] = file_record(path)
                (target / BUNDLE_MANIFEST).write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
                marker = target / INSTALL_RECEIPT
                receipt = json.loads(marker.read_text())
                receipt["bundle_sha256"] = _manifest_hash(target)
                marker.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
                self.assertEqual(installer.verify_installation(target)["receipt"]["version"], "1.3.0")
                incoming = self.base / (label + "-incoming")
                build_bundle(incoming, modules=modules, source_root=self.bundle)
                result = installer.install_bundle(incoming, home)
                self.assertEqual(result["status"], "updated")
                self.assertEqual(result["version"], "1.3.1")
                self.assertEqual(result["modules"], modules)
                self.assertEqual((settings.read_bytes(), settings.stat().st_mode), settings_before)
                self.assertFalse((target / "ecosystem/evaluation.json").exists())
                self.assertFalse((target / "ecosystem/ARCHITECTURE.md").exists())
                self.assertTrue((target / "ecosystem/docs/architecture.md").is_file())
                self.assertEqual(installer.install_bundle(incoming, home)["status"], "unchanged")

    def test_130_corruption_is_rejected_before_any_installation_change(self) -> None:
        for case in ("modified", "unknown", "symlink", "mode", "mixed"):
            with self.subTest(case=case):
                home = self.base / case
                target = self.owned_130(home=home)
                resource = target / "ecosystem/ARCHITECTURE.md"
                if case == "modified":
                    resource.write_text("user changed this file\n")
                elif case == "unknown":
                    (target / "unowned.txt").write_text("preserve this file\n")
                elif case == "symlink":
                    resource.unlink()
                    resource.symlink_to(target / "ecosystem/README.md")
                elif case == "mode":
                    resource.chmod(0o600)
                else:
                    destination = target / "ecosystem/docs/architecture.md"
                    destination.parent.mkdir()
                    resource.rename(destination)
                    manifest = json.loads((target / BUNDLE_MANIFEST).read_text())
                    manifest["files"]["ecosystem/docs/architecture.md"] = manifest["files"].pop("ecosystem/ARCHITECTURE.md")
                    (target / BUNDLE_MANIFEST).write_text(json.dumps(manifest))
                    marker = target / INSTALL_RECEIPT
                    receipt = json.loads(marker.read_text())
                    marker.write_text(json.dumps({**receipt, "bundle_sha256": _manifest_hash(target)}))
                before = snapshot(home)
                with self.assertRaises(InstallError):
                    installer.install_bundle(self.bundle, home)
                self.assertEqual(snapshot(home), before)

    def test_failed_130_upgrade_restores_exact_predecessor(self) -> None:
        self.owned_130()
        before = snapshot(self.home)
        original = Path.rename

        def fail_stage(path: Path, destination: Path):
            if path.name == installer.STAGING_NAME:
                raise OSError("synthetic upgrade promotion failure")
            return original(path, destination)

        with patch.object(Path, "rename", fail_stage):
            with self.assertRaisesRegex(InstallError, "previous owned payload was restored"):
                installer.install_bundle(self.bundle, self.home)
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(installer.verify_installation(self.target)["receipt"]["version"], "1.3.0")

    def test_predecessor_compatibility_does_not_accept_legacy_as_incoming_release(self) -> None:
        previous = self.owned_130()
        (previous / INSTALL_RECEIPT).unlink()
        other_home = self.base / "new-home"
        with self.assertRaises(ValueError):
            installer.install_bundle(previous, other_home)
        self.assertFalse(other_home.exists())

    def test_two_homes_share_release_bytes_and_preserve_unrelated_settings(self) -> None:
        self.home.mkdir(parents=True)
        settings = self.home / "settings.json"
        settings.write_text('{"model":"user-choice","enabledPlugins":{"other@source":true}}\n')
        other = self.home / "skills/other/SKILL.md"
        other.parent.mkdir(parents=True)
        other.write_text("User-owned skill\n")
        settings_before = settings.read_bytes(), settings.stat().st_mode
        first = installer.install_bundle(self.bundle, self.home)
        second_home = self.base / "different laptop" / "config"
        second = installer.install_bundle(self.bundle, second_home)
        self.assertEqual(first["status"], "installed")
        self.assertEqual(first["bundle_sha256"], second["bundle_sha256"])
        self.assertEqual(snapshot(self.target), snapshot(second_home / "skills/constellation"))
        self.assertEqual((settings.read_bytes(), settings.stat().st_mode), settings_before)
        self.assertEqual(other.read_text(), "User-owned skill\n")
        self.assertEqual(first["live_execution"], "not_verified")
        self.assertEqual(installer.verify_installation(self.target)["receipt"]["plugin_id"], installer.PLUGIN_ID)

    def test_dry_run_is_read_only_for_absent_and_existing_homes(self) -> None:
        result = installer.install_bundle(self.bundle, self.home, check=True)
        self.assertEqual(result["status"], "checked")
        self.assertFalse(self.home.exists())
        installer.install_bundle(self.bundle, self.home)
        before = snapshot(self.home)
        installer.install_bundle(self.bundle, self.home, check=True)
        self.assertEqual(snapshot(self.home), before)

    def test_repeat_is_idempotent_and_upgrade_changes_only_owned_payload(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        before = snapshot(self.home)
        result = installer.install_bundle(self.bundle, self.home)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(snapshot(self.home), before)
        result = installer.install_bundle(self.changed_bundle(), self.home)
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["version"], "1.3.2")
        self.assertFalse((self.target.parent / installer.BACKUP_NAME).exists())

    def test_explicit_disablement_and_unowned_collision_preserve_every_byte(self) -> None:
        self.home.mkdir(parents=True)
        settings = self.home / "settings.json"
        settings.write_text(json.dumps({"enabledPlugins": {installer.PLUGIN_ID: False}}))
        before = snapshot(self.home)
        with self.assertRaisesRegex(InstallError, "explicitly disabled"):
            installer.install_bundle(self.bundle, self.home)
        self.assertEqual(snapshot(self.home), before)
        settings.unlink()
        self.target.mkdir(parents=True)
        (self.target / "notes.txt").write_text("foreign data")
        before = snapshot(self.home)
        with self.assertRaises(InstallError):
            installer.install_bundle(self.bundle, self.home)
        self.assertEqual(snapshot(self.home), before)

    def test_modified_payload_receipt_and_extra_files_are_rejected(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        candidates = ((self.target / self.skill_relative, b"modified\n"),
                      (self.target / INSTALL_RECEIPT, b"{}\n"),
                      (self.target / "unowned.txt", b"preserve\n"))
        for path, content in candidates:
            with self.subTest(path=path.name):
                original = path.read_bytes() if path.exists() else None
                path.write_bytes(content)
                before = snapshot(self.home)
                with self.assertRaises((InstallError, ValueError)):
                    installer.install_bundle(self.bundle, self.home)
                self.assertEqual(snapshot(self.home), before)
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)

    def test_symlink_ancestors_resources_and_hardlinks_are_rejected(self) -> None:
        real = self.base / "real"
        real.mkdir()
        linked = self.base / "linked"
        linked.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(InstallError, "symbolic link"):
            installer.install_bundle(self.bundle, linked / "config")
        self.assertEqual(snapshot(real), {})
        installer.install_bundle(self.bundle, self.home)
        resource = self.target / self.skill_relative
        original = resource.read_bytes()
        resource.unlink()
        outside = self.base / "unrelated.txt"
        outside.write_bytes(original)
        resource.symlink_to(outside)
        with self.assertRaises((InstallError, ValueError)):
            installer.verify_installation(self.target)
        resource.unlink()
        os.link(outside, resource)
        with self.assertRaisesRegex(InstallError, "singly linked"):
            installer.verify_installation(self.target)
        self.assertEqual(outside.read_bytes(), original)

    def test_mode_change_and_hardlinked_lock_fail_without_payload_mutation(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        marker = self.target / INSTALL_RECEIPT
        marker.chmod(0o644)
        with self.assertRaisesRegex(InstallError, "permissions"):
            installer.verify_installation(self.target)
        marker.chmod(0o600)
        lock = self.home / installer.LOCK_PATH
        os.link(lock, self.base / "lock-alias")
        before = snapshot(self.home)
        with self.assertRaisesRegex(InstallError, "singly linked"):
            installer.install_bundle(self.bundle, self.home)
        self.assertEqual(snapshot(self.home), before)

    def test_lock_permissions_and_noninteger_receipt_schema_are_rejected(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        lock = self.home / installer.LOCK_PATH
        lock.chmod(0o644)
        with self.assertRaisesRegex(InstallError, "lock changed"):
            installer.install_bundle(self.bundle, self.home)
        lock.chmod(0o600)
        marker = self.target / INSTALL_RECEIPT
        receipt = json.loads(marker.read_text())
        receipt["schema"] = True
        marker.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(InstallError, "receipt differs"):
            installer.verify_installation(self.target)

    def test_live_hook_lock_rejects_installation_without_mutating_payload(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        before = snapshot(self.home)
        with installer.verified_installation(self.target):
            with self.assertRaisesRegex(InstallError, "hook is running"):
                installer.install_bundle(self.bundle, self.home)
        self.assertEqual(snapshot(self.home), before)

    def test_failed_second_rename_restores_previous_owned_release(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        before = snapshot(self.home)
        next_bundle = self.changed_bundle()
        original = Path.rename

        def fail_stage(path: Path, destination: Path):
            if path.name == installer.STAGING_NAME:
                raise OSError("synthetic second rename failure")
            return original(path, destination)

        with patch.object(Path, "rename", fail_stage):
            with self.assertRaisesRegex(InstallError, "previous owned payload was restored"):
                installer.install_bundle(next_bundle, self.home)
        self.assertEqual(snapshot(self.home), before)
        installer.verify_installation(self.target)

    def test_failed_first_rename_preserves_current_release_and_removes_own_stage(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        before = snapshot(self.home)
        next_bundle = self.changed_bundle()
        original = Path.rename

        def fail_target(path: Path, destination: Path):
            if path == self.target:
                raise OSError("synthetic first rename failure")
            return original(path, destination)

        with patch.object(Path, "rename", fail_target):
            with self.assertRaises(InstallError):
                installer.install_bundle(next_bundle, self.home)
        self.assertEqual(snapshot(self.home), before)

    def test_destination_appearing_during_staging_is_preserved(self) -> None:
        original = installer._sync_tree

        def concurrent_file(root: Path) -> None:
            original(root)
            self.target.mkdir()
            (self.target / "foreign.txt").write_text("created during installation")

        with patch.object(installer, "_sync_tree", concurrent_file):
            with self.assertRaises(InstallError):
                installer.install_bundle(self.bundle, self.home)
        self.assertEqual((self.target / "foreign.txt").read_text(), "created during installation")
        self.assertFalse((self.target.parent / installer.STAGING_NAME).exists())

    def test_stage_collision_during_exclusive_claim_is_preserved(self) -> None:
        original = Path.mkdir
        stage = self.target.parent / installer.STAGING_NAME

        def concurrent_stage(path: Path, *arguments, **options):
            if path == stage:
                original(path, mode=0o755)
                (path / "foreign.txt").write_text("not owned by installer")
            return original(path, *arguments, **options)

        with patch.object(Path, "mkdir", concurrent_stage):
            with self.assertRaises(InstallError):
                installer.install_bundle(self.bundle, self.home)
        self.assertEqual((stage / "foreign.txt").read_text(), "not owned by installer")
        self.assertFalse(self.target.exists())

    def test_bundle_inside_install_lock_directory_is_rejected_without_changes(self) -> None:
        source = self.home / "constellation"
        source.parent.mkdir(parents=True)
        shutil.copytree(self.bundle, source)
        before = snapshot(self.home)
        with self.assertRaisesRegex(InstallError, "must not overlap"):
            installer.install_bundle(source, self.home)
        self.assertEqual(snapshot(self.home), before)

    def test_interrupted_stage_and_backup_are_preserved_for_explicit_recovery(self) -> None:
        installer.install_bundle(self.bundle, self.home)
        for name in (installer.STAGING_NAME, installer.BACKUP_NAME):
            with self.subTest(name=name):
                pending = self.target.parent / name
                pending.mkdir()
                (pending / "recover-me.txt").write_text("retained")
                before = snapshot(self.home)
                with self.assertRaisesRegex(InstallError, "pending staging or backup"):
                    installer.install_bundle(self.bundle, self.home)
                self.assertEqual(snapshot(self.home), before)
                shutil.rmtree(pending)

    def test_distribution_and_installed_cli_work_from_a_relocated_path(self) -> None:
        relocated = self.base / "copied release" / "bundle"
        relocated.parent.mkdir()
        shutil.copytree(self.bundle, relocated)
        result = subprocess.run([sys.executable, "-B", str(relocated / "ecosystem/claude.py"),
                                 "install", "--bundle", str(relocated), "--claude-home", str(self.home)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "installed")
        result = subprocess.run([sys.executable, "-B", str(self.target / "ecosystem/claude.py"),
                                 "verify", "--claude-home", str(self.home)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "verified")
        self.assertEqual(_manifest_hash(self.target), _manifest_hash(relocated))


def _manifest_hash(root: Path) -> str:
    return hashlib.sha256((root / BUNDLE_MANIFEST).read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
