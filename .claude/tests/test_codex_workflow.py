#!/usr/bin/env python3
"""Regression tests for the Codex adapter, projection and private evidence."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from unittest.mock import patch

HUB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HUB / "scripts"))
import codex_sync as sync
import doctor


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load("adapter", HUB / "templates/codex_hook_shim.py")
ledger = load("ledger", HUB / "hooks/bash_ledger.py")


class AdapterTests(unittest.TestCase):
    def test_command_normalized_before_argument_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = [sys.executable, str(HUB / "templates/codex_hook_shim.py"),
                       "--project-dir", tmp, "--command-glob", "git commit*", "--",
                       sys.executable, "-c", "import sys; sys.exit(2)"]
            result = subprocess.run(command, input=json.dumps({"tool_name": "exec_command",
                "tool_input": {"cmd": "git commit -m test"}}), text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)

    def test_all_patch_input_forms_and_rename(self):
        raw = "*** Begin Patch\n*** Add File: first.py\n+x = 1\n*** Update File: second.py\n*** Move to: moved.py\n@@\n-old\n+new\n*** End Patch"
        for ti in [raw, {"command": raw}, {"input": raw}, {"patch": raw}]:
            data = json.loads(adapter.normalise(json.dumps({"tool_name": "apply_patch", "tool_input": ti})))
            files = adapter.per_file_payloads(data, Path("/tmp"))
            self.assertEqual([p["tool_input"]["file_path"] for p in files],
                             ["/tmp/first.py", "/tmp/moved.py", "/tmp/second.py"])
            self.assertEqual(files[1]["tool_input"]["content"], "new\n")

    def test_shell_argv_and_false_result_preserved(self):
        data = json.loads(adapter.normalise(json.dumps({"tool_name": "shell", "tool_input": {
            "command": ["python3", "a b.py"]}, "tool_response": False})))
        self.assertEqual(shlex.split(data["tool_input"]["command"]), ["python3", "a b.py"])
        self.assertIs(data["tool_result"], False)

    def test_stop_reentry_does_not_run_inner_or_repeat_failure(self):
        result = subprocess.run([sys.executable, str(HUB / "templates/codex_hook_shim.py"),
            "--project-dir", "/nonexistent", "--", "does-not-exist"],
            input=json.dumps({"event": "Stop", "stop_hook_active": True, "cwd": "/nonexistent"}),
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_timeout_terminates_descendants(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "child-survived"
            inner = shlex.join([sys.executable, "-c",
                f"import time; from pathlib import Path; time.sleep(.3); Path({str(marker)!r}).touch()"])
            result = subprocess.run([sys.executable, str(HUB / "templates/codex_hook_shim.py"),
                "--project-dir", tmp, "--timeout", "0.05", "--", "sh", "-c", inner],
                input="{}", text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            time.sleep(.4)
            self.assertFalse(marker.exists())

    def test_multifile_structured_output_cannot_silently_allow(self):
        raw = "*** Begin Patch\n*** Add File: a\n+a\n*** Add File: b\n+b\n*** End Patch"
        result = subprocess.run([sys.executable, str(HUB / "templates/codex_hook_shim.py"),
            "--project-dir", "/tmp", "--", sys.executable, "-c", 'print(\'{"decision":"block"}\')'],
            input=json.dumps({"tool_name": "apply_patch", "tool_input": {"command": raw}}),
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")


class ProjectionTests(unittest.TestCase):
    def test_second_apply_has_no_writes_or_mtime_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / "CLAUDE.md").write_text("# Fixture\n")
            (root / ".claude/settings.json").write_text(json.dumps({"hooks": {"Stop": [{
                "hooks": [{"type": "command", "command": "true", "timeout": 15}]}]}}))
            first = sync.Projection().run(sync.Surface("fixture", root))
            self.assertTrue(first.written)
            mtimes = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
            self.assertEqual(sync.Projection().run(sync.Surface("fixture", root)).written, [])
            self.assertEqual(mtimes, {p: p.stat().st_mtime_ns for p in mtimes})
            checker = sync.Projection(check=True)
            checker.run(sync.Surface("fixture", root))
            self.assertEqual(checker.drift, [])
            config = tomllib.loads((root / ".codex/config.toml").read_text())
            self.assertTrue(config["features"]["hooks"])
            self.assertNotIn("model", config)

    def test_hook_command_quoting_and_environment(self):
        with tempfile.TemporaryDirectory(prefix="codex space '") as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            inner = root / ".claude/inner.py"
            inner.write_text('import os; print(os.environ["CLAUDE_PROJECT_DIR"])')
            settings = {"hooks": {"SessionStart": [{"hooks": [{"type": "command",
                "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/inner.py"'}]}]}}
            projection = sync.Projection()
            surface = sync.Surface("fixture", root)
            hooks = projection.project_hooks(surface, settings)
            projection.apply(surface)
            hook = hooks["SessionStart"][0]["hooks"][0]
            result = subprocess.run(["sh", "-c", hook["command"]], input="{}", text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), tmp)

    def test_invalid_settings_write_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude/settings.json").write_text("broken json")
            with self.assertRaises(ValueError):
                sync.Projection().run(sync.Surface("fixture", root))
            self.assertFalse((root / ".codex").exists())

    def test_doctor_reports_missing_config_without_claiming_activation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(doctor, "GITHUB_ROOT", Path(tmp)):
            with patch.object(doctor.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)):
                section = doctor.section_codex()
            self.assertEqual(section.status, "FAIL")
            activation = next(c for c in section.checks if c.label == "native hook activation")
            self.assertEqual(activation.status, "INFO")


class LedgerTests(unittest.TestCase):
    def test_only_executed_checks_are_classified(self):
        for command in ["cat test_codex_sync.py", "echo pytest", "python3 -c 'print(1)'", "false; pytest",
                        "pytest --collect-only", "pytest --version", "ruff check src", "bash -n script.sh"]:
            self.assertFalse(ledger.is_test_command(command), command)
        for command in ["python3 .claude/tests/test_codex_sync.py", "python3 -m unittest", "pytest tests"]:
            self.assertTrue(ledger.is_test_command(command), command)

    def test_private_idempotent_records_and_missing_identity(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ledger, "LEDGER_DIR", Path(tmp)):
            event = {"session_id": "../unsafe", "tool_use_id": "call-1", "tool_input": {
                "command": "python3 test_example.py --note private-argument", "description": "private-description"},
                "tool_response": {"exit_code": 0, "stdout": "private-output"}}
            def invoke():
                with patch.object(sys, "stdin", io.StringIO(json.dumps(event))):
                    self.assertEqual(ledger.main(), 0)
            invoke()
            target = next(Path(tmp).glob("*.jsonl"))
            before = target.stat().st_mtime_ns
            invoke()
            self.assertEqual(before, target.stat().st_mtime_ns)
            text = target.read_text()
            for private in ["private-argument", "private-description", "private-output", "call-1"]:
                self.assertNotIn(private, text)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertTrue(json.loads(text)["is_test"])
            del event["tool_use_id"]
            invoke()
            invoke()
            self.assertEqual(len(target.read_text().splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
