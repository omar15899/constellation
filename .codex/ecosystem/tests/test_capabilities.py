"""Metadata-only diagnostics: synthetic failure coverage and real native discovery."""
from __future__ import annotations

from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
SOURCE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_DIR))

import native


class CapabilityMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = native.NativeClient(Path("/synthetic/home"), cwd=Path("/synthetic/project"))
        self.location = str(self.client.cwd)
        self.skills = {"data": [{"cwd": self.location, "errors": [], "skills": [
            {"name": "global", "description": "Global skill", "path": "/synthetic/home/skills/g/SKILL.md",
             "scope": "user", "enabled": True, "pluginId": None},
            {"name": "project", "description": "Project skill", "path": "/synthetic/project/.agents/skills/p/SKILL.md",
             "scope": "repo", "enabled": False, "pluginId": None},
            {"name": "plugin:skill", "description": "Plugin skill", "path": "/synthetic/cache/SKILL.md",
             "scope": "user", "enabled": True, "pluginId": "plugin@market",
             "dependencies": {"tools": [{"url": "https://PRIVATE_DEPENDENCY"}]}}
        ]}]}
        self.hooks = {"data": [{"cwd": self.location, "errors": [], "warnings": [], "hooks": [
            {"key": "key", "eventName": "stop", "source": "plugin", "sourcePath": "/synthetic/hooks.json",
             "pluginId": "plugin@market", "enabled": True, "trustStatus": "untrusted",
             "command": "PRIVATE_HOOK_COMMAND"}
        ]}]}
        self.config = {"config": {"agents": {"max_concurrent_threads_per_session": 64},
                                  "mcp_servers": {"secret": {"token": "PRIVATE_CONFIG"}}},
                       "origins": {"secret": "PRIVATE_ORIGIN"}}
        self.plugins = [{"pluginId": "plugin@market", "enabled": True, "version": "1.0.0",
                         "unknown": "PRIVATE_PLUGIN"}]
        self.servers = [{"name": "configured-server", "enabled": False, "auth_status": "unsupported",
                         "transport": {"env": {"TOKEN": "PRIVATE_TOKEN"},
                                       "url": "https://user:PRIVATE_PASSWORD@example.org"}}]
        self.rpc = Mock()
        self.rpc.call.side_effect = self.respond

    def respond(self, method: str, parameters: dict) -> dict:
        expected = {"skills/list": {"cwds": [self.location], "forceReload": True},
                    "hooks/list": {"cwds": [self.location]},
                    "config/read": {"cwd": self.location, "includeLayers": False}}
        self.assertIn(method, expected, "Only read-only metadata requests are allowed")
        self.assertEqual(parameters, expected[method])
        value = {"skills/list": self.skills, "hooks/list": self.hooks, "config/read": self.config}[method]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)

    def discover(self) -> dict:
        with patch.object(native, "_Rpc", return_value=self.rpc), \
                patch.object(self.client, "plugins", return_value=self.plugins), \
                patch.object(self.client, "_run_json", return_value=self.servers) as command:
            result = self.client.capabilities()
        command.assert_called_once_with("mcp", "list")
        self.rpc.close.assert_called()
        return result

    def test_all_native_skill_sources_are_preserved_without_execution_claims(self) -> None:
        result = self.discover()
        self.assertEqual(result["surface"], "fresh_codex_cli")
        self.assertEqual(result["status"], "complete")
        self.assertEqual([row["name"] for row in result["skills"]], ["global", "project", "plugin:skill"])
        self.assertFalse(result["skills"][1]["enabled"])
        self.assertEqual(result["hooks"][0]["trustStatus"], "untrusted")
        self.assertEqual(result["agents"]["configured_max_concurrent_threads_per_session"], 64)
        self.assertIsNone(result["agents"]["effective_session_limit"])
        self.assertIn("executed", result["unverified"])
        self.assertIn("authorized", result["unverified"])
        self.assertEqual(self.rpc.call.call_count, 3)

    def test_private_config_commands_and_mcp_transport_never_leave_adapter(self) -> None:
        result = self.discover()
        self.assertNotIn("PRIVATE_", json.dumps(result))
        self.assertEqual(result["mcp_servers"], [{"name": "configured-server", "enabled": False,
                                                "configured": True, "auth_status": "unsupported"}])

    def test_warnings_and_errors_mark_partial_without_echoing_source_messages(self) -> None:
        self.skills["data"][0]["errors"] = [{"path": "/synthetic/bad/SKILL.md", "message": "PRIVATE_CONTENT"}]
        self.hooks["data"][0]["warnings"] = ["failed to parse PRIVATE_CONTENT"]
        result = self.discover()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(len(result["warnings"]), 1)
        self.assertEqual(len(result["skills"]), 3)
        self.assertEqual(result["checks"]["hooks"]["status"], "partial")
        self.assertNotIn("PRIVATE_CONTENT", json.dumps(result))

    def test_unavailable_rpc_method_preserves_other_capabilities(self) -> None:
        self.skills = native.NativeError("PRIVATE_ERROR")
        result = self.discover()
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["skills"], [])
        self.assertEqual(result["checks"]["hooks"]["status"], "ok")
        self.assertTrue(result["plugins"])
        self.assertNotIn("PRIVATE_ERROR", json.dumps(result))

    def test_missing_or_wrong_cwd_and_malformed_metadata_fail_transparently(self) -> None:
        invalid = [{}, {"data": []}, {"data": [{"cwd": "/other", "errors": [], "skills": []}]},
                   {"data": [{"cwd": self.location, "errors": [], "skills": [{}]}]},
                   {"data": [{"cwd": self.location, "errors": "bad", "skills": []}]}]
        for value in invalid:
            with self.subTest(value=value):
                self.skills = value
                result = self.discover()
                self.assertEqual(result["checks"]["skills"]["status"], "failed")
                self.assertEqual(result["skills"], [])

    def test_malformed_mcp_and_plugins_are_not_reported_as_empty_success(self) -> None:
        self.servers = {"not": "a list"}
        self.plugins = [{"pluginId": "broken"}]
        result = self.discover()
        self.assertEqual(result["checks"]["plugins"]["status"], "failed")
        self.assertEqual(result["checks"]["mcp"]["status"], "failed")
        self.assertEqual(result["checks"]["skills"]["status"], "ok")

    def test_invalid_capacity_is_not_reported_as_an_effective_limit(self) -> None:
        for value in (True, -1, "64", {}):
            with self.subTest(value=value):
                self.config["config"]["agents"]["max_concurrent_threads_per_session"] = value
                result = self.discover()
                self.assertEqual(result["checks"]["agents"]["status"], "failed")
                self.assertIsNone(result["agents"]["effective_session_limit"])
        self.config = {"config": {}}
        self.assertEqual(self.discover()["checks"]["agents"]["status"], "ok")

    def test_server_launch_failure_preserves_cli_results(self) -> None:
        with patch.object(native, "_Rpc", side_effect=native.NativeError("PRIVATE_STARTUP")), \
                patch.object(self.client, "plugins", return_value=self.plugins), \
                patch.object(self.client, "_run_json", return_value=self.servers):
            result = self.client.capabilities()
        self.assertEqual(len(result["errors"]), 3)
        self.assertTrue(result["plugins"])
        self.assertTrue(result["mcp_servers"])
        self.assertNotIn("PRIVATE_STARTUP", json.dumps(result))

    def test_cli_has_nonzero_exit_for_partial_and_prevents_mutation_flags(self) -> None:
        for status, exit_code in (("complete", 0), ("partial", 1)):
            output = io.StringIO()
            with patch.object(native.NativeClient, "capabilities", return_value={"status": status}), \
                    redirect_stdout(output):
                self.assertEqual(native.main(["--codex-home", "/synthetic", "--capabilities"]), exit_code)
            self.assertEqual(json.loads(output.getvalue()), {"status": status})
        for extra in (["--exclude-source-root", "/source"], ["--marketplace-path", "/market"],
                      ["--modules", "coding"]):
            with self.subTest(extra=extra), patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit):
                native.main(["--codex-home", "/synthetic", "--capabilities", *extra])


@unittest.skipUnless(shutil.which("codex"), "Native Codex is unavailable; metadata mocks are separate")
class RealNativeCapabilityTests(unittest.TestCase):
    def test_fresh_cli_discovers_global_and_project_skills_with_no_project_scaffolding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="constellation-capabilities-") as temporary:
            root = Path(temporary).resolve()
            home, project, empty = (root / name for name in ("home", "project", "empty"))
            for directory in (home, project, empty):
                directory.mkdir()
            (home / "config.toml").write_text("[agents]\nmax_concurrent_threads_per_session = 7\n")
            for base, name in ((home / "skills", "diagnostic-global"),
                               (project / ".agents/skills", "diagnostic-project")):
                skill = base / name / "SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text(f"---\nname: {name}\ndescription: Synthetic discovery fixture.\n---\nFixture only.\n")
            before = {str(path.relative_to(project)): path.read_bytes() for path in project.rglob("*") if path.is_file()}
            for location, expected_local in ((project, True), (empty, False)):
                with self.subTest(cwd=location.name):
                    process = subprocess.run([sys.executable, "-B", str(SOURCE_DIR / "native.py"),
                                              "--codex-home", str(home), "--cwd", str(location), "--capabilities"],
                                             capture_output=True, text=True, timeout=60)
                    self.assertEqual(process.returncode, 0, process.stderr)
                    result = json.loads(process.stdout)
                    names = {row["name"] for row in result["skills"]}
                    self.assertIn("diagnostic-global", names)
                    self.assertEqual("diagnostic-project" in names, expected_local)
                    self.assertEqual(result["agents"]["configured_max_concurrent_threads_per_session"], 7)
                    self.assertEqual(result["status"], "complete")
                    self.assertIn("executed", result["unverified"])
            self.assertEqual(list(empty.iterdir()), [])
            after = {str(path.relative_to(project)): path.read_bytes() for path in project.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertFalse((project / ".git").exists())
            self.assertFalse((home / "sessions").exists())


if __name__ == "__main__":
    unittest.main()
