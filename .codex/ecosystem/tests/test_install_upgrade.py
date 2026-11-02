"""Cross-layout upgrades must recognize published bytes before replacing them."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from test_package import (
    ALL_MODULES, BundleCase, CODEX_DIR, InstallError, SyntheticNativeClient, build_bundle, install_bundle, installer,
    snapshot, write_json,
)


class ReleaseUpgradeTests(BundleCase):
    def setUp(self) -> None:
        super().setUp()
        self.home = self.root / "codex"
        self.home.mkdir()
        self.client = SyntheticNativeClient(self.home)
        install_bundle(self.bundle, self.home, client=self.client)
        self.receipt = self.home / "constellation/receipt.json"
        # Published predecessors predate the device launcher and its schema 4
        # fields. Model that layout explicitly before binding the fixture pin.
        (self.home / "constellation/run").unlink()
        old = json.loads(self.receipt.read_text())
        old.pop("python")
        old.pop("python_target")
        old.pop("launcher")
        write_json(self.receipt, {**old, "schema": 3})
        self.catalog = self.home / "constellation/catalog"
        self.previous = self.catalog / installer.PLUGIN_DIRECTORY
        # A historical fixture deliberately has a file the new release does
        # not own. An explicit pin below models a frozen, published manifest.
        (self.previous / "ecosystem/previous.py").write_text(
            'raise AssertionError("must not import the previous payload")\n')
        for name in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
            path = self.previous / name
            write_json(path, {**json.loads(path.read_text()), "version": "1.3.1"})
        self.prior_digest = self.record_prior()
        self.pins = {"1.3.1": {self.prior_digest}}
        self.client.mutations.clear()

    def record_prior(self) -> str:
        """Update the fixture's manifest, registration, cache and receipt."""
        receipt = json.loads(self.receipt.read_text())
        records = installer._inventory(self.previous)
        records.pop("bundle.json")
        manifest = self.previous / "bundle.json"
        write_json(manifest, {"schema": 1, "modules": receipt["modules"], "files": records})
        self.client.add_plugin()
        cache = self.home / "plugins/cache/constellation/constellation/1.3.1"
        write_json(self.receipt, {**receipt, "version": "1.3.1",
                                  "catalog": installer._inventory(self.catalog),
                                  "cache": installer._inventory(cache)})
        return hashlib.sha256(manifest.read_bytes()).hexdigest()

    def test_known_prior_upgrades_and_repeat_avoids_native_mutations(self) -> None:
        with patch.object(installer, "_PUBLISHED_PREDECESSORS", self.pins):
            self.assertEqual(install_bundle(self.bundle, self.home, check=True, client=self.client)["status"],
                             "checked")
            self.assertFalse(self.client.mutations)
            self.assertEqual(install_bundle(self.bundle, self.home, client=self.client)["status"], "updated")
        before = snapshot(self.home)
        self.client.mutations.clear()
        self.assertEqual(install_bundle(self.bundle, self.home, client=self.client)["status"], "current")
        self.assertFalse(self.client.mutations)
        self.assertEqual(snapshot(self.home), before)
        self.assertFalse((self.previous / "ecosystem/previous.py").exists())

    def test_rehashed_extra_files_cannot_claim_prior_ownership(self) -> None:
        (self.previous / "independent.txt").write_text("preserve")
        self.record_prior()
        before = snapshot(self.home)
        self.client.mutations.clear()
        with patch.object(installer, "_PUBLISHED_PREDECESSORS", self.pins):
            with self.assertRaises(InstallError):
                install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(snapshot(self.home), before)
        self.assertFalse(self.client.mutations)

    def test_claimed_pin_cannot_hide_different_receipt_contents(self) -> None:
        receipt = json.loads(self.receipt.read_text())
        receipt["cache"]["ecosystem/previous.py"]["sha256"] = "0" * 64
        write_json(self.receipt, receipt)
        before = snapshot(self.home)
        with patch.object(installer, "_PUBLISHED_PREDECESSORS", self.pins):
            with self.assertRaises(InstallError):
                install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(snapshot(self.home), before)
        self.assertFalse(self.client.mutations)

    def test_redirected_marketplace_cannot_use_a_matching_receipt(self) -> None:
        path = self.catalog / installer.CATALOG_MANIFEST
        market = json.loads(path.read_text())
        market["plugins"][0]["source"]["path"] = "../independent"
        write_json(path, market)
        receipt = json.loads(self.receipt.read_text())
        receipt["catalog"][installer.CATALOG_MANIFEST] = installer.file_record(path)
        write_json(self.receipt, receipt)
        before = snapshot(self.home)
        with patch.object(installer, "_PUBLISHED_PREDECESSORS", self.pins):
            with self.assertRaisesRegex(InstallError, "marketplace"):
                install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(snapshot(self.home), before)
        self.assertFalse(self.client.mutations)

    def test_failed_native_upgrade_restores_the_verified_predecessor(self) -> None:
        before = snapshot(self.home)
        self.client.fail_once = "add_plugin"
        with patch.object(installer, "_PUBLISHED_PREDECESSORS", self.pins):
            with self.assertRaisesRegex(InstallError, "previous owned files and registration restored"):
                install_bundle(self.bundle, self.home, client=self.client)
            self.assertEqual(snapshot(self.home), before)
            self.assertEqual(install_bundle(self.bundle, self.home, check=True, client=self.client)["status"],
                             "checked")


class EnrolledDeviceTests(BundleCase):
    def setUp(self) -> None:
        super().setUp()
        self.home = self.root / "codex"
        self.home.mkdir()
        self.client = SyntheticNativeClient(self.home)
        self.binding = self.home / "constellation-vault.json"

    def assert_general_rejected(self) -> None:
        before = snapshot(self.home)
        self.client.mutations.clear()
        for check in (True, False):
            with self.assertRaisesRegex(InstallError, "personal profile"):
                install_bundle(self.bundle, self.home, [self.module], check=check, client=self.client)
        self.assertFalse(self.client.mutations)
        self.assertEqual(snapshot(self.home), before)

    def test_dangling_binding_blocks_general_install_before_any_mutation(self) -> None:
        self.binding.symlink_to(self.root / "missing")
        self.assert_general_rejected()

    @unittest.skipUnless((CODEX_DIR / "ecosystem/vault/workflow.py").is_file(),
                         "This general distribution excludes the OmarOS module")
    def test_registered_personal_install_survives_general_request_and_retries(self) -> None:
        personal = self.root / "personal"
        build_bundle(personal, [*ALL_MODULES, "omaros"], source_root=CODEX_DIR)
        install_bundle(personal, self.home, client=self.client)
        write_json(self.binding, {"schema": 1, "root": str(self.root),
                                  "owner": [1, 2], "git_dir": [3, 4]})
        self.binding.chmod(0o600)
        self.assert_general_rejected()
        self.assertEqual(install_bundle(personal, self.home, client=self.client)["status"], "current")
        self.assertFalse(self.client.mutations)


class ReceiptPreconditionTests(BundleCase):
    def test_slow_update_cannot_replace_a_concurrent_winner(self) -> None:
        home = self.root / "codex"
        home.mkdir()
        client = SyntheticNativeClient(home)
        receipt = home / "constellation/receipt.json"
        install_bundle(self.bundle, home, client=client, expected_receipt_sha256="absent")
        observed = hashlib.sha256(receipt.read_bytes()).hexdigest()
        newer = self.changed_bundle()
        original_lock = installer._lock
        winner = {}

        @contextmanager
        def interleave(lock_home):
            # A competing sync wins after the slow proposal's first preflight,
            # before that proposal acquires its exclusive lock.
            if not winner:
                winner["running"] = True
                install_bundle(newer, home, client=client, expected_receipt_sha256=observed)
                winner["files"] = snapshot(home)
                winner["mutations"] = list(client.mutations)
            with original_lock(lock_home):
                yield

        with patch.object(installer, "_lock", side_effect=interleave):
            with self.assertRaisesRegex(InstallError, "receipt changed"):
                install_bundle(self.bundle, home, client=client, expected_receipt_sha256=observed)
        self.assertEqual(snapshot(home), winner["files"])
        self.assertEqual(client.mutations, winner["mutations"])
        for stale in (observed, "absent"):
            with self.assertRaisesRegex(InstallError, "receipt changed"):
                install_bundle(self.bundle, home, check=True, client=client, expected_receipt_sha256=stale)
        fresh = hashlib.sha256(receipt.read_bytes()).hexdigest()
        self.assertEqual(install_bundle(newer, home, client=client, expected_receipt_sha256=fresh)["status"],
                         "current")
        self.assertEqual(client.mutations, winner["mutations"])


class DeviceLauncherTests(BundleCase):
    def setUp(self) -> None:
        super().setUp()
        self.home = self.root / "codex home '$dollar"
        self.home.mkdir()
        self.client = SyntheticNativeClient(self.home)
        self.launcher = self.home / "constellation/run"
        self.receipt = self.home / "constellation/receipt.json"
        install_bundle(self.bundle, self.home, client=self.client)

    def test_launcher_ignores_wrong_path_and_home_and_keeps_cli_exit_status(self) -> None:
        fake = self.root / "distractor"
        fake.mkdir()
        env = {**os.environ, "PATH": str(fake), "CODEX_HOME": str(fake)}
        response = subprocess.run([self.launcher, "cli", "--help"], env=env,
                                  capture_output=True, text=True, timeout=15)
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertIn("usage:", response.stdout)
        rejected = subprocess.run([self.launcher, "unknown-mode"], env=env,
                                  capture_output=True, text=True, timeout=15)
        self.assertNotEqual(rejected.returncode, 0)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(receipt["python"], sys.executable)
        self.assertEqual(receipt["python_target"], os.path.realpath(sys.executable))
        self.assertEqual(receipt["launcher"], {"mode": 0o700,
                                               "sha256": hashlib.sha256(self.launcher.read_bytes()).hexdigest()})

    def test_interpreter_change_rebinds_without_reinstalling_native_plugin(self) -> None:
        alias = self.root / "python 'alias $"
        alias.symlink_to(sys.executable)
        self.client.mutations.clear()
        with patch.object(sys, "executable", str(alias)):
            self.assertEqual(install_bundle(self.bundle, self.home, client=self.client)["status"], "updated")
            self.assertEqual(install_bundle(self.bundle, self.home, client=self.client)["status"], "current")
        self.assertFalse(self.client.mutations)
        self.assertEqual(json.loads(self.receipt.read_text())["python"], str(alias))
        alias.unlink()
        env = {**os.environ, "PATH": str(self.root / "missing"), "CODEX_HOME": str(self.root / "wrong-home")}
        denial = subprocess.run([self.launcher, "PreToolUse"], input="{}", env=env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(denial.returncode, 0, denial.stderr)
        self.assertEqual(json.loads(denial.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(install_bundle(self.bundle, self.home, client=self.client)["status"], "updated")

    def test_failed_interpreter_rebind_restores_previous_launcher_inode(self) -> None:
        alias = self.root / "other python"
        alias.symlink_to(sys.executable)
        inode = self.launcher.stat().st_ino
        before = snapshot(self.home)
        publish = installer._publish_receipt

        def fail_after_receipt(*args, forward):
            publish(*args, forward=forward)
            if forward:
                self.assertNotEqual(self.launcher.stat().st_ino, inode)
                raise OSError("Lost acknowledgement")

        with patch.object(sys, "executable", str(alias)), patch.object(installer, "_publish_receipt", fail_after_receipt):
            with self.assertRaisesRegex(InstallError, "previous owned files.*restored"):
                install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(self.launcher.stat().st_ino, inode)
        self.assertEqual(snapshot(self.home), before)

    def test_independently_replaced_launcher_survives_failed_rebind(self) -> None:
        alias = self.root / "replacement python"
        alias.symlink_to(sys.executable)
        previous_inode = self.launcher.stat().st_ino
        previous_receipt = self.receipt.read_bytes()
        foreign = self.root / "independent launcher"
        foreign.write_text("independently preserved")
        foreign_inode = foreign.stat().st_ino

        publish = installer._publish_receipt

        def substitute_then_fail(*args, forward):
            if forward:
                foreign.replace(self.launcher)
                raise OSError("Synthetic concurrent replacement")
            publish(*args, forward=forward)

        with patch.object(sys, "executable", str(alias)), patch.object(installer, "_publish_receipt", substitute_then_fail):
            with self.assertRaisesRegex(InstallError, "rollback needs attention"):
                install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(self.launcher.stat().st_ino, foreign_inode)
        self.assertEqual(self.launcher.read_text(), "independently preserved")
        self.assertEqual(self.receipt.read_bytes(), previous_receipt)
        retained = list(self.home.glob("constellation/.transition/launcher-image"))
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0].stat().st_ino, previous_inode)


@unittest.skipIf(os.name == "nt", "These native crash paths use the POSIX Codex installer")
class LauncherInterruptionTests(BundleCase):
    def setUp(self) -> None:
        super().setUp()
        self.home = self.root / "codex"
        self.home.mkdir()
        self.client = SyntheticNativeClient(self.home)
        self.python = self.root / "second python"
        self.python.symlink_to(sys.executable)
        self.run = self.home / "constellation/run"
        self.receipt = self.home / "constellation/receipt.json"

    def kill_installer(self, point: str) -> None:
        """Use a real process death either side of the actual atomic promotion."""
        script = """
import os, sys, signal
from pathlib import Path
sys.path[:0] = sys.argv[1:3]
import install as subject
from test_package import SyntheticNativeClient
home, bundle = map(Path, sys.argv[3:5])
point = sys.argv[5]
sys.executable = sys.argv[6]
swap = subject.platform.exchange_files
promote = subject.platform.promote_file
def die():
    os.kill(os.getpid(), signal.SIGKILL)
def exchange(stage, target):
    if target == home / "constellation/run" and point == "before-swap":
        die()
    swap(stage, target)
    if target == home / "constellation/run" and point == "after-swap":
        die()
def create(stage, target):
    promote(stage, target)
    if target == home / "constellation/run" and point == "after-create":
        die()
subject.platform.exchange_files = exchange
subject.platform.promote_file = create
subject.install_bundle(bundle, home, client=SyntheticNativeClient(home))
raise SystemExit("Crash injection point was not reached")
"""
        from signal import SIGKILL
        process = subprocess.run([sys.executable, "-B", "-c", script, str(CODEX_DIR / "ecosystem"),
                                  str(CODEX_DIR / "ecosystem/tests"), str(self.home), str(self.bundle),
                                  point, str(self.python)], capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, -SIGKILL, process.stderr)
        self.assertTrue((self.home / "constellation/.transition").is_dir())
        self.assertEqual(install_bundle(self.bundle, self.home, check=True,
                                        client=self.client)["status"], "recovery_required")

    def resume(self) -> None:
        with patch.object(sys, "executable", str(self.python)):
            install_bundle(self.bundle, self.home, client=self.client)
            self.assertEqual(install_bundle(self.bundle, self.home, client=self.client)["status"], "current")
        value = json.loads(self.receipt.read_text())
        self.assertEqual(value["python"], str(self.python))
        self.assertEqual(self.run.stat().st_nlink, 1)
        self.assertFalse((self.home / "constellation/.transition").exists())

    def test_first_install_killed_between_launcher_and_receipt_recovers_on_retry(self) -> None:
        independent = self.home / "AGENTS.md"
        independent.write_text("keep me")
        self.kill_installer("after-create")
        self.assertTrue(self.run.is_file())
        self.assertFalse(self.receipt.exists())
        self.assertEqual(self.run.stat().st_nlink, 1)
        self.resume()
        self.assertEqual(independent.read_text(), "keep me")

    def test_installed_launcher_stays_singly_linked_across_interrupted_exchanges(self) -> None:
        for point in ("before-swap", "after-swap"):
            with self.subTest(point=point):
                install_bundle(self.bundle, self.home, client=self.client)
                self.kill_installer(point)
                self.assertEqual(self.run.stat().st_nlink, 1)
                self.resume()

    def test_foreign_replacement_winning_the_swap_race_is_preserved(self) -> None:
        install_bundle(self.bundle, self.home, client=self.client)
        foreign = self.root / "foreign"
        foreign.write_text("foreign executable body")
        foreign.chmod(0o700)
        foreign_id = foreign.stat().st_ino
        exchange = installer.platform.exchange_files
        def race(stage, target):
            if target == self.run and foreign.exists():
                foreign.replace(target)
            exchange(stage, target)
        with patch.object(installer.platform, "exchange_files", race), patch.object(sys, "executable", str(self.python)):
            with self.assertRaisesRegex(InstallError, "rollback needs attention"):
                install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(self.run.stat().st_ino, foreign_id)
        self.assertEqual(self.run.read_text(), "foreign executable body")
        self.assertTrue((self.home / "constellation/.transition").is_dir())

    def test_independent_receipt_winning_the_swap_race_keeps_its_inode_and_bytes(self) -> None:
        install_bundle(self.bundle, self.home, client=self.client)
        foreign = self.root / "independent receipt"
        foreign.write_text("independent receipt content")
        foreign.chmod(0o600)
        foreign_inode = foreign.stat().st_ino
        exchange = installer.platform.exchange_files

        def race(stage, target):
            if target == self.receipt and foreign.exists():
                foreign.replace(target)
            exchange(stage, target)

        with patch.object(installer.platform, "exchange_files", race), patch.object(sys, "executable", str(self.python)):
            with self.assertRaisesRegex(InstallError, "rollback needs attention"):
                install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(self.receipt.stat().st_ino, foreign_inode)
        self.assertEqual(self.receipt.read_text(), "independent receipt content")
        self.assertTrue((self.home / "constellation/.transition").is_dir())
