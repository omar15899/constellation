"""Exercise profile preservation and portable package installation."""
from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
import os
import stat
import hashlib
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / "profiles/copilot"
SPEC = importlib.util.spec_from_file_location("copilot_install_tested", SOURCE / "install.py")
assert SPEC is not None and SPEC.loader is not None
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class CopilotInstallTests(unittest.TestCase):
    """Check meaningful failures without changing the user's Copilot home."""

    @classmethod
    def setUpClass(cls):
        cls.context = installer.payload(SOURCE)
        cls.files, cls.commit, cls.builder = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    @contextmanager
    def prepared_payload(self, profile):
        yield self.files, self.commit, self.builder

    def test_check_is_read_only_and_apply_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(installer, "payload", self.prepared_payload):
            home = Path(directory).resolve()
            result = installer.install_profile(SOURCE, home)
            self.assertGreater(result["missing"], 0)
            self.assertFalse((home / ".copilot").exists())
            installer.install_profile(SOURCE, home, apply=True)
            result = installer.install_profile(SOURCE, home, apply=True)
            self.assertEqual(result["missing"], 0)
            hooks = json.loads((home / ".copilot/hooks/constellation.json").read_bytes())
            self.assertEqual(set(hooks["hooks"]), set(installer.HOOK_EVENTS))
            for event, entries in hooks["hooks"].items():
                self.assertTrue(Path(entries[0]["exec"]).is_absolute())
                self.assertEqual(entries[0]["args"][-3:], ["hook", "--event", event])
                self.assertNotIn("powershell", entries[0])
            self.builder.verify_bundle(home / ".copilot/constellation/bundle")

    def test_existing_shared_native_directories_keep_their_access_and_files(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(installer, "payload", self.prepared_payload):
            home = Path(directory).resolve()
            root = home / ".copilot"
            for name in ("agents", "hooks", "skills"):
                target = root / name
                target.mkdir(parents=True)
                # Keep one native inherited ACL alongside explicit safe public
                # directories; installation must preserve both access policies.
                if name != "skills":
                    self.builder._PLATFORM.set_access(target, 0o755)
            sentinel = root / "agents/existing-agent.agent.md"
            sentinel.write_text("Keep this independent agent.\n", encoding="utf-8")
            access = {name: self.builder._PLATFORM.access_fingerprint(root / name)
                      for name in ("agents", "hooks", "skills")}
            installer.install_profile(SOURCE, home, apply=True)
            self.assertEqual(sentinel.read_text(), "Keep this independent agent.\n")
            for name, fingerprint in access.items():
                self.assertEqual(self.builder._PLATFORM.access_fingerprint(root / name), fingerprint)
            self.assertEqual(installer.install_profile(SOURCE, home)["missing"], 0)

    @unittest.skipIf(os.name == "nt", "Writable-directory modes are a POSIX scenario")
    def test_unsafe_shared_directory_fails_before_installation_writes(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(installer, "payload", self.prepared_payload):
            home = Path(directory).resolve()
            root = home / ".copilot"
            hooks = root / "hooks"
            hooks.mkdir(parents=True)
            hooks.chmod(0o777)
            sentinel = root / "keep.txt"
            sentinel.write_text("Keep unrelated configuration.\n", encoding="utf-8")
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            with self.assertRaises(OSError):
                installer.install_profile(SOURCE, home, apply=True)
            self.assertEqual(sorted(path.relative_to(root).as_posix() for path in root.rglob("*")), before)
            self.assertEqual(sentinel.read_text(), "Keep unrelated configuration.\n")
            self.assertEqual(stat.S_IMODE(hooks.stat().st_mode), 0o777)

    def test_one_conflict_prevents_all_profile_writes(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(installer, "payload", self.prepared_payload):
            home = Path(directory).resolve()
            target = home / ".copilot/copilot-instructions.md"
            target.parent.mkdir()
            target.write_text("Keep my existing instructions.\n", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.install_profile(SOURCE, home, apply=True)
            self.assertEqual(target.read_text(), "Keep my existing instructions.\n")
            self.assertEqual(list(target.parent.iterdir()), [target])

    def test_export_is_reproducible_and_installable_after_relocation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            first, second = root / "first.zip", root / "second.zip"
            tool_path = root / "official_docs.py"
            tool_path.write_bytes(self.files["official_docs.py"])
            docs_tool = installer._load(tool_path, "copilot_install_docs_fixture")
            snapshot = root / "public-docs"
            snapshot.mkdir()
            records = {}
            for name, url in docs_tool.sources("copilot").items():
                data = b"# Official documentation fixture\n"
                (snapshot / name).write_bytes(data)
                records[name] = {"url": url, "final_url": url, "fetched_at": "2026-11-15T00:00:00+00:00",
                                 "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            (snapshot / "manifest.json").write_bytes(installer._json_bytes(
                {"schema": 1, "provider": "copilot", "files": records}))
            (snapshot / "INDEX.md").write_text("# Official documentation fixture\n", encoding="utf-8")
            with patch.object(installer, "payload", self.prepared_payload):
                installer.export_profile(SOURCE, first, snapshot)
                installer.export_profile(SOURCE, second, snapshot)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                archive.extractall(root / "another computer")
            package = root / "another computer/copilot-profile"
            home = root / "new user"
            result = installer.install_profile(package, home, apply=True)
            self.assertEqual(result["core_source_commit"], self.commit)
            runtime = home / ".copilot/constellation/profile/runtime.py"
            self.assertEqual(runtime.read_bytes(), self.files["runtime.py"])
            acceptance = home / ".copilot/constellation/profile/acceptance.py"
            self.assertEqual(acceptance.read_bytes(), self.files["acceptance.py"])
            portable = subprocess.run([sys.executable, "-I", "-B", str(acceptance),
                "--home", str(home), "--portable-check"], capture_output=True, text=True)
            self.assertEqual(portable.returncode, 0, portable.stderr)
            report = json.loads(portable.stdout)
            self.assertEqual(report["mechanical_profile_acceptance"], "passed")
            self.assertEqual(report["native_windows_acceptance"], "pending")
            self.assertEqual(report["native_copilot_dispatch"], "pending_manual_check")
            verify = subprocess.run([sys.executable, "-I", "-B",
                str(home / ".copilot/tools/official_docs.py"), "--home", str(home),
                "--provider", "copilot", "verify"], capture_output=True, text=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)
            lock = home / ".copilot/docs/.official.lock"
            lock.write_bytes(b"preserve runtime lock")
            installer.install_profile(package, home, apply=True)
            self.assertEqual(lock.read_bytes(), b"preserve runtime lock")
            (package / "runtime.py").write_text("tampered", encoding="utf-8")
            with self.assertRaises(installer.InstallError):
                installer.install_profile(package, root / "untouched", apply=True)
            self.assertFalse((root / "untouched").exists())

    def test_linked_home_and_archive_overwrite_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "real").mkdir()
            try:
                (root / "alias").symlink_to(root / "real", target_is_directory=True)
            except OSError:
                self.skipTest("Creating symlinks requires additional Windows privileges")
            with self.assertRaises(installer.InstallError):
                installer.install_profile(SOURCE, root / "alias", apply=True)
            archive = root / "existing.zip"
            archive.write_bytes(b"preserve")
            with self.assertRaises(installer.InstallError):
                installer.export_profile(SOURCE, archive)
            self.assertEqual(archive.read_bytes(), b"preserve")


if __name__ == "__main__":
    unittest.main()
