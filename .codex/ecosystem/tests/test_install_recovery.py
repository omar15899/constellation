"""Interrupt a real installer process and recover through its normal public entry point.

The native registry is synthetic. Both the registry and the installation use real
files. SIGKILL prevents Python exception handlers and context managers from
compensating in the interrupted process.
"""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import ExitStack
from pathlib import Path
import select
import shlex
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_package import (
    BundleCase, InstallError, NativeClient, SyntheticNativeClient, install_bundle, installer,
    verify_bundle,
)


def _interrupt(bundle: Path, home: Path, boundary: str) -> None:
    """Kill the installer on the requested side of a native or receipt publication boundary."""
    client = SyntheticNativeClient(home)

    def stop() -> None:
        os.kill(os.getpid(), signal.SIGKILL)
        raise AssertionError("SIGKILL returned")

    if boundary in {"receipt", "committed"}:
        live_receipt = home / "constellation/receipt.json"

        def stop_at_publication(operation):
            def publish(source, target):
                if target != live_receipt:
                    return operation(source, target)
                if not (home / "constellation/run").is_file():
                    raise AssertionError("Receipt publication preceded launcher promotion")
                if boundary == "receipt":
                    stop()
                operation(source, target)
                stop()
            return publish

        with ExitStack() as stack:
            for name in ("promote_file", "exchange_files"):
                original = getattr(installer.platform, name)
                stack.enter_context(patch.object(installer.platform, name, stop_at_publication(original)))
            install_bundle(bundle, home, client=client)
    elif boundary in {"add_marketplace", "add_plugin"}:
        operation = getattr(client, boundary)

        def after_native(*args, **kwargs):
            operation(*args, **kwargs)
            stop()

        with patch.object(client, boundary, after_native):
            install_bundle(bundle, home, client=client)
    else:
        raise ValueError("Unknown test boundary")
    raise AssertionError("Installer did not reach the requested interruption")


def _orphan_install(bundle: Path, home: Path, executable: Path) -> None:
    """Use real subprocess dispatch for plugin addition and a durable fixture for status queries."""
    registry = SyntheticNativeClient(home)
    client = NativeClient(home, str(executable), cwd=home, timeout=60)
    with ExitStack() as stack:
        for method in ("marketplaces", "plugins", "add_marketplace", "remove_marketplace", "remove_plugin"):
            stack.enter_context(patch.object(client, method, getattr(registry, method)))
        install_bundle(bundle, home, client=client)


def _native_add() -> None:
    """An orphan can finish its authorized filesystem mutation after its caller was killed."""
    if sys.argv[2:] != ["plugin", "add", "constellation@constellation", "--json"]:
        raise AssertionError("Unexpected native fixture invocation")
    home = Path(os.environ["CODEX_HOME"])
    with (home.parent / "orphan-ready").open("wb", buffering=0) as ready:
        ready.write(b"R")
    with (home.parent / "orphan-release").open("rb", buffering=0) as release:
        if release.read(1) != b"X":
            raise AssertionError("Invalid release marker")
    SyntheticNativeClient(home).add_plugin()
    with (home.parent / "orphan-done").open("wb", buffering=0) as done:
        done.write(b"D")
    # There is no consumer of CLI stdout: the installer process is dead.
    os._exit(0)


def _read_barrier(fd: int, expected: bytes) -> None:
    if not select.select([fd], [], [], 25)[0] or os.read(fd, 1) != expected:
        raise AssertionError(f"Native process did not reach the {expected!r} barrier")


@unittest.skipUnless(os.name == "posix", "SIGKILL recovery uses the POSIX Codex installer")
class InstallationCrashTests(BundleCase):
    def setUp(self) -> None:
        super().setUp()
        self.home = self.root / "codex"
        self.home.mkdir()
        self.client = SyntheticNativeClient(self.home)
        self.foreign = self.home / "agents/team.toml"
        self.foreign.parent.mkdir()
        self.foreign.write_text("independently maintained agent\n")
        self.config = self.home / "config.toml"
        self.config.write_text('[plugins."another@market"]\nenabled = false\n')

    def interrupt(self, bundle: Path, boundary: str) -> None:
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--interrupt",
             str(bundle), str(self.home), boundary],
            cwd=self.root, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stdout + result.stderr)

    def assert_recovered(self, bundle: Path) -> None:
        install_bundle(bundle, self.home, client=self.client)
        manifest = verify_bundle(bundle)
        receipt = json.loads((self.home / "constellation/receipt.json").read_text())
        self.assertEqual(receipt["cache"]["bundle.json"]["sha256"],
                         hashlib.sha256((bundle / "bundle.json").read_bytes()).hexdigest())
        self.assertEqual(receipt["modules"], manifest["modules"])
        self.assertEqual(self.client.plugins()[0]["version"], receipt["version"])
        self.assertEqual(receipt["launcher"]["sha256"],
                         hashlib.sha256((self.home / "constellation/run").read_bytes()).hexdigest())
        self.assertEqual(self.foreign.read_text(), "independently maintained agent\n")
        self.assertIn('[plugins."another@market"]\nenabled = false', self.config.read_text())
        self.client.mutations.clear()
        self.assertEqual(install_bundle(bundle, self.home, client=self.client)["status"], "current")
        self.assertFalse(self.client.mutations)

    def test_first_install_recovers_marketplace_registration_without_acknowledgement(self) -> None:
        self.interrupt(self.bundle, "add_marketplace")
        self.assertEqual(len(self.client.marketplaces()), 1)
        self.assertEqual(self.client.plugins(), [])
        self.assert_recovered(self.bundle)

    def test_first_install_recovers_plugin_registration_without_acknowledgement(self) -> None:
        self.interrupt(self.bundle, "add_plugin")
        self.assertEqual(self.client.plugins()[0]["version"], self.current_version)
        self.assertFalse((self.home / "constellation/receipt.json").exists())
        self.assert_recovered(self.bundle)

    def test_launcher_without_first_receipt_can_be_recovered(self) -> None:
        self.interrupt(self.bundle, "receipt")
        self.assertTrue((self.home / "constellation/run").is_file())
        self.assertFalse((self.home / "constellation/receipt.json").exists())
        self.assert_recovered(self.bundle)

    def test_committed_first_receipt_retires_the_interrupted_transition(self) -> None:
        self.interrupt(self.bundle, "committed")
        self.assertEqual(json.loads((self.home / "constellation/receipt.json").read_text())["version"],
                         self.current_version)
        self.assert_recovered(self.bundle)

    def test_upgrade_recovers_with_old_receipt_and_new_native_cache(self) -> None:
        install_bundle(self.bundle, self.home, client=self.client)
        old = (self.home / "constellation/receipt.json").read_bytes()
        update = self.changed_bundle("2.0.0", change_entry=True, change_agent=True)
        self.interrupt(update, "add_plugin")
        self.assertEqual((self.home / "constellation/receipt.json").read_bytes(), old)
        self.assertEqual(self.client.plugins()[0]["version"], "2.0.0")
        self.assert_recovered(update)
        read = subprocess.run(
            [str(self.home / "constellation/run"), "cli", "skill-read", self.module],
            cwd=self.root, capture_output=True, timeout=20,
        )
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertEqual(json.loads(read.stdout)["content"],
                         (update / "skills" / self.module / "SKILL.md").read_text(encoding="utf-8"))

    def test_interrupted_upgrade_after_existing_launcher_exchange_is_retryable(self) -> None:
        install_bundle(self.bundle, self.home, client=self.client)
        launcher = self.home / "constellation/run"
        receipt = self.home / "constellation/receipt.json"
        before_launcher, before_receipt = launcher.read_bytes(), receipt.read_bytes()
        update = self.changed_bundle("2.0.0", change_entry=True)
        self.interrupt(update, "receipt")
        self.assertNotEqual(launcher.read_bytes(), before_launcher)
        self.assertEqual(receipt.read_bytes(), before_receipt)
        self.assertEqual(self.client.plugins()[0]["version"], "2.0.0")
        self.assert_recovered(update)

    def test_committed_upgrade_settles_before_stale_proposal_is_rejected(self) -> None:
        install_bundle(self.bundle, self.home, client=self.client)
        receipt = self.home / "constellation/receipt.json"
        old_digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
        stable_directories = [(directory, {p.name for p in directory.iterdir()})
                              for directory in (self.home, receipt.parent)]
        update = self.changed_bundle("2.0.0", change_entry=True, change_agent=True)
        self.interrupt(update, "committed")
        committed = receipt.read_bytes()
        self.assertEqual(json.loads(committed)["version"], "2.0.0")
        self.client.mutations.clear()
        with self.assertRaisesRegex(InstallError, "receipt changed"):
            install_bundle(update, self.home, client=self.client,
                           expected_receipt_sha256=old_digest)
        self.assertEqual(receipt.read_bytes(), committed)
        self.assertEqual(self.client.plugins()[0]["version"], "2.0.0")
        self.assertFalse(self.client.mutations)
        for directory, names in stable_directories:
            self.assertEqual({p.name for p in directory.iterdir()}, names)
        self.assert_recovered(update)

    def test_resume_preserves_an_independently_modified_native_cache_file(self) -> None:
        self.interrupt(self.bundle, "add_plugin")
        path = self.home / "plugins/cache/constellation/constellation" / self.current_version / "ecosystem/core.py"
        path.write_text("independent work\n")
        with self.assertRaises(InstallError):
            install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(path.read_text(), "independent work\n")
        self.assertFalse(self.client.mutations)

    def test_foreign_projected_agent_is_preserved_before_native_recovery(self) -> None:
        self.interrupt(self.bundle, "receipt")
        agent = self.home / "agents/constellation-reviewer.toml"
        self.assertTrue(agent.is_file())
        agent.write_text("independent agent edits\n")
        with self.assertRaises(InstallError):
            install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(agent.read_text(), "independent agent edits\n")
        self.assertFalse(self.client.mutations)

    def test_orphaned_native_mutation_retains_lock_until_its_own_exit(self) -> None:
        executable = self.root / "fixture-codex"
        executable.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " -I -B " +
                              shlex.quote(str(Path(__file__).resolve())) + ' --native-add "$@"\n')
        executable.chmod(0o700)
        with ExitStack() as stack:
            fds = []
            for name in ("orphan-ready", "orphan-release", "orphan-done"):
                fifo = self.root / name
                os.mkfifo(fifo, 0o600)
                fd = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
                stack.callback(os.close, fd)
                fds.append(fd)
            ready, release, done = fds
            installer_process = subprocess.Popen(
                [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--orphan-install",
                 str(self.bundle), str(self.home), str(executable)],
                cwd=self.root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            active = False
            try:
                _read_barrier(ready, b"R")
                active = True
                installer_process.kill()
                self.assertEqual(installer_process.wait(timeout=15), -signal.SIGKILL)
                with self.assertRaisesRegex(InstallError, "(?i)lock|busy|active|running"):
                    install_bundle(self.bundle, self.home, client=self.client)
                self.assertFalse(self.client.mutations)
            finally:
                if installer_process.poll() is None:
                    installer_process.kill()
                    installer_process.wait(timeout=15)
                os.write(release, b"X")
                if active:
                    _read_barrier(done, b"D")

        # The native operation is durable at the done barrier; its process is
        # still allowed to be completing exit. Wait for its descriptor to close.
        subprocess.run(
            [sys.executable, "-I", "-c",
             "import fcntl,sys; f=open(sys.argv[1],'rb'); fcntl.flock(f,fcntl.LOCK_SH)",
             str(self.home / "constellation/.install.lock")],
            check=True, timeout=10, stdin=subprocess.DEVNULL,
        )
        self.assert_recovered(self.bundle)

    def test_native_callback_cannot_grant_ownership_of_a_replaced_or_new_agent(self) -> None:
        update = self.changed_bundle("2.0.0", change_agent=True)
        for predecessor, same_contents in ((False, False), (True, False), (False, True)):
            with self.subTest(previously_installed=predecessor, same_contents=same_contents):
                home = self.root / f"concurrent-home-{predecessor}-{same_contents}"
                home.mkdir()
                client = SyntheticNativeClient(home)
                if predecessor:
                    install_bundle(self.bundle, home, client=client)
                target = home / "agents/constellation-reviewer.toml"
                target.parent.mkdir(exist_ok=True)
                self.assertEqual(target.exists(), predecessor)
                foreign = self.root / "independent-role"
                content = ((update / "ecosystem/agents/reviewer.toml").read_bytes() if same_contents
                           else b"operator-owned role\n")
                foreign.write_bytes(content)
                foreign.chmod(0o644)
                identity = foreign.stat().st_ino
                native_add = client.add_plugin

                def replace_after_native_update():
                    result = native_add()
                    if foreign.exists():
                        foreign.replace(target)
                    return result

                with patch.object(client, "add_plugin", replace_after_native_update):
                    with self.assertRaises(InstallError):
                        install_bundle(update, home, client=client)
                self.assertEqual(target.stat().st_ino, identity)
                self.assertEqual(target.read_bytes(), content)
                self.assertEqual(target.stat().st_mode & 0o777, 0o644)
                self.assertEqual(install_bundle(update, home, client=client, check=True)["status"],
                                 "recovery_required")

    def test_recovery_preserves_explicit_disablement(self) -> None:
        self.interrupt(self.bundle, "add_plugin")
        self.client._enable(False)
        before = self.config.read_bytes()
        with self.assertRaises(InstallError):
            install_bundle(self.bundle, self.home, client=self.client)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse(self.client.mutations)


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--interrupt":
        _interrupt(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])
    elif len(sys.argv) == 5 and sys.argv[1] == "--orphan-install":
        _orphan_install(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    elif sys.argv[1:2] == ["--native-add"]:
        _native_add()
    else:
        unittest.main()
