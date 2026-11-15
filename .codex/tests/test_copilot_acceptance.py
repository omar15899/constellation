"""Exercise honest acceptance reports and concrete local safety boundaries."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "profiles/copilot"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load_module("copilot_acceptance_test_installer", SOURCE / "install.py")
acceptance = load_module("copilot_acceptance_tested", SOURCE / "acceptance.py")


class CopilotAcceptanceTests(unittest.TestCase):
    """Use temporary installed profiles and explicitly synthetic protocol evidence."""

    @classmethod
    def setUpClass(cls):
        cls.context = installer.payload(SOURCE)
        cls.files, cls.commit, cls.builder = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    @contextmanager
    def prepared_payload(self, _profile):
        yield self.files, self.commit, self.builder

    @contextmanager
    def installed_home(self):
        with tempfile.TemporaryDirectory(prefix="copilot-acceptance-test-") as directory:
            root = Path(directory).resolve()
            home = root / "Synthetic user \u03a9 with spaces"
            with patch.object(installer, "payload", self.prepared_payload):
                installer.install_profile(SOURCE, home, apply=True)
            yield home

    def probe(self, home: Path, *arguments: str):
        script = home / ".copilot/constellation/profile/acceptance.py"
        result = subprocess.run([sys.executable, "-I", "-B", str(script), "--home", str(home), *arguments],
                                capture_output=True, text=True, timeout=120)
        return result, json.loads(result.stdout)

    def test_portable_report_preserves_installation_and_keeps_live_acceptance_pending(self):
        with self.installed_home() as home:
            before = {path.relative_to(home).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in home.rglob("*") if path.is_file()}
            result, report = self.probe(home, "--portable-check")
            self.assertEqual(result.returncode, 0, report)
            self.assertEqual(report["mechanical_profile_acceptance"], "passed")
            self.assertEqual(report["native_windows_acceptance"], "pending")
            self.assertEqual(report["native_copilot_dispatch"], "pending_manual_check")
            self.assertEqual(report["native_parallel_review"], "pending_manual_check")
            self.assertEqual(report["synthetic_gate_reviews"], "fixture_only")
            self.assertEqual(report["model_conversations_started"], 0)
            after = {path.relative_to(home).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in home.rglob("*") if path.is_file()}
            self.assertEqual(after, before)

    def test_hashes_and_hook_structure_reject_tampering_without_echoing_private_content(self):
        with self.installed_home() as home:
            root = home / ".copilot"
            runtime = root / "constellation/profile/runtime.py"
            original = runtime.read_bytes()
            runtime.write_bytes(b"private sentinel that must never appear in reports")
            result, report = self.probe(home, "--portable-check")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["reason"], "managed_resource_hash_mismatch")
            self.assertNotIn("private sentinel", result.stdout + result.stderr)
            runtime.write_bytes(original)
            hooks = root / "hooks/constellation.json"
            value = json.loads(hooks.read_bytes())
            value["hooks"]["preToolUse"][0]["args"][-1] = "agentStop"
            hooks.write_text(json.dumps(value), encoding="utf-8")
            receipt = root / "constellation/profile-receipt.json"
            value = json.loads(receipt.read_bytes())
            value["files"]["hooks/constellation.json"] = hashlib.sha256(hooks.read_bytes()).hexdigest()
            receipt.write_text(json.dumps(value), encoding="utf-8")
            result, report = self.probe(home, "--portable-check")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["stage"], "hooks")

    def test_reports_never_overwrite_or_enter_the_installation_through_parent_aliases(self):
        with self.installed_home() as home:
            report_file = home.parent / "acceptance.json"
            result, report = self.probe(home, "--portable-check", "--report", str(report_file))
            self.assertEqual(result.returncode, 0, report)
            original = report_file.read_bytes()
            result, _ = self.probe(home, "--portable-check", "--report", str(report_file))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report_file.read_bytes(), original)
            outside = home / "other"
            outside.mkdir()
            attempted = outside / ".." / ".copilot/constellation/bundle/report.json"
            result, report = self.probe(home, "--portable-check", "--report", str(attempted))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["stage"], "report")
            self.assertFalse(attempted.exists())

    @unittest.skipIf(os.name == "nt", "POSIX writable-directory regression")
    def test_writable_hook_parent_fails_even_when_all_managed_bytes_match(self):
        with self.installed_home() as home:
            (home / ".copilot/hooks").chmod(0o777)
            result, report = self.probe(home, "--portable-check")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["mechanical_profile_acceptance"], "pending")

    def test_native_search_ignores_empty_relative_and_caller_directory_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            project, installed = root / "project", root / "installed tools"
            project.mkdir()
            installed.mkdir()
            (project / "copilot.exe").write_bytes(b"Do not execute project code.")
            expected = installed / "copilot.exe"
            expected.write_bytes(b"Synthetic metadata search target; never executed.")
            environment = {"PATH": os.pathsep.join(("", ".", str(project), str(installed)))}
            with patch.object(acceptance, "NATIVE_WINDOWS", True), patch.object(acceptance.Path, "cwd", return_value=project):
                self.assertEqual(acceptance.native_executable("copilot", environment), str(expected))
                with self.assertRaises(acceptance.PendingAcceptance):
                    acceptance.native_executable("git", environment)
                aliases = root / "aliases"
                aliases.mkdir()
                try:
                    (aliases / "copilot.exe").symlink_to(project / "copilot.exe")
                except OSError:
                    pass  # Windows symlink privileges are not assumed here.
                else:
                    environment = {"PATH": os.pathsep.join((str(aliases), str(installed)))}
                    self.assertEqual(acceptance.native_executable("copilot", environment), str(expected))
        if os.name != "nt":
            report = acceptance.run_acceptance(Path("/unread/home"))
            self.assertEqual(report["status"], "pending")
            self.assertEqual(report["stage"], "platform")
            self.assertEqual(report["native_windows_acceptance"], "pending")

    def test_native_discovery_requires_the_enabled_installed_resource_and_known_json_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / ".copilot"
            skill = root / "skills/human-coding/SKILL.md"
            data = {"version:git": b"git version 2.52.0", "version:powershell": b"7.5.0",
                    "version:copilot": b"0.0.500",
                    "discovery:instruction": json.dumps([{"sourcePath": str(root / "copilot-instructions.md"),
                                                         "defaultDisabled": False}]).encode(),
                    "discovery:skill": json.dumps([{"name": "human-coding", "enabled": True,
                                                   "path": str(skill)}]).encode()}

            def native_output(_argv, **kwargs):
                return data[kwargs["stage"]]

            with patch.object(acceptance, "native_executable", return_value="metadata-only-fixture"), \
                    patch.object(acceptance, "run_command", side_effect=native_output):
                report = acceptance.native_metadata(root, root.parent, {})
                self.assertEqual(report["native_dependencies"], "passed")
                self.assertEqual(report["personal_instruction_effective_enablement"], "pending_manual_check")
                for path, enabled, valid in ((skill.parent, True, True), (root / "another/SKILL.md", True, False),
                                             (skill, False, False)):
                    data["discovery:skill"] = json.dumps([{"name": "human-coding", "enabled": enabled,
                                                           "path": str(path)}]).encode()
                    if valid:
                        self.assertIn("verified", acceptance.native_metadata(root, root.parent, {})["native_resource_discovery"])
                    else:
                        with self.assertRaises(acceptance.PendingAcceptance):
                            acceptance.native_metadata(root, root.parent, {})
                data["discovery:skill"] = b'{"new_schema":[]}'
                with self.assertRaises(acceptance.PendingAcceptance):
                    acceptance.native_metadata(root, root.parent, {})


if __name__ == "__main__":
    unittest.main()
