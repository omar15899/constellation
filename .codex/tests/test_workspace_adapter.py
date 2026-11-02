"""Exercise the historical entry without any local engine or real user state."""
from pathlib import Path
import json
import hashlib
import fcntl
import os
import shutil
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest


ADAPTER = Path(__file__).resolve().parents[1] / "ecosystem" / "cli.py"


class WorkspaceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.workspace = self.base / "workspace"
        self.adapter = self.workspace / ".codex" / "ecosystem" / "cli.py"
        self.adapter.parent.mkdir(parents=True)
        shutil.copy2(ADAPTER, self.adapter)
        self.home = self.base / "codex-home"
        self.launcher = self.home / "constellation" / "run"
        self.launcher.parent.mkdir(parents=True)
        self.capture = self.base / "capture.json"
        self.probe = self.base / "probe.py"
        self.probe.write_text(
            "import json, os, pathlib, sys\n"
            "pathlib.Path(os.environ['ADAPTER_CAPTURE']).write_text(\n"
            "    json.dumps({'args': sys.argv[1:], 'cwd': os.getcwd()}))\n"
            "raise SystemExit(int(os.environ.get('ADAPTER_EXIT', '0')))\n"
        )
        self.launcher.write_text(
            "#!/bin/sh\nexec " + shlex.quote(sys.executable) + " "
            + shlex.quote(str(self.probe)) + ' "$@"\n')
        self.launcher.chmod(0o700)
        hook = self.launcher.parent / "hook.py"
        hook.write_text("# Synthetic receipt-owned transport; the fixture probe handles dispatch.\n")
        hook.chmod(0o644)
        def record(path):
            return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "mode": stat.S_IMODE(path.stat().st_mode)}
        self.receipt = self.launcher.parent / "receipt.json"
        self.receipt.write_text(json.dumps({
            "schema": 4, "python": sys.executable,
            "launcher": record(self.launcher), "hook": record(hook),
            "cache": {"ecosystem/hook_entry.py": record(hook)}}))
        (self.launcher.parent / ".install.lock").touch()
        self.cwd = self.base / "unrelated-directory"
        self.cwd.mkdir()
        self.environment = dict(os.environ, CODEX_HOME=str(self.home),
                                ADAPTER_CAPTURE=str(self.capture))

    def invoke(self, *arguments, **environment):
        return subprocess.run([sys.executable, str(self.adapter), *arguments],
                              cwd=self.cwd, env={**self.environment, **environment},
                              capture_output=True, text=True)

    def recorded(self):
        return json.loads(self.capture.read_text())

    def test_workspace_uses_adapter_root_from_an_unrelated_directory(self):
        result = self.invoke("workspace", "route", "Shared/README.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), {
            "args": ["cli", "workspace", "--root", str(self.workspace),
                     "route", "Shared/README.md"], "cwd": str(self.cwd)})

    def test_system_python_entry_can_handoff_to_the_installed_interpreter(self):
        # A caller can use Apple's Python 3.9 even when the verified launcher
        # records a newer interpreter. Exercise actual external entry points,
        # rather than only the interpreter running this suite.
        interpreters = {shutil.which("python3"), "/usr/bin/python3"}
        available = sorted(path for path in interpreters if path and Path(path).is_file())
        if not available:
            self.skipTest("No external Python entry point is available")
        for interpreter in available:
            with self.subTest(interpreter=interpreter):
                result = subprocess.run(
                    [interpreter, str(self.adapter), "workspace", "route", "README.md"],
                    cwd=self.cwd, env=self.environment, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.recorded(), {
                    "args": ["cli", "workspace", "--root", str(self.workspace),
                             "route", "README.md"], "cwd": str(self.cwd)})

    def test_explicit_workspace_root_retains_later_precedence(self):
        other = self.base / "another-workspace"
        result = self.invoke("workspace", "--root", str(other), "route", "README.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded()["args"], [
            "cli", "workspace", "--root", str(self.workspace),
            "--root", str(other), "route", "README.md"])

    def test_agent_policy_receives_the_workspace_root(self):
        result = self.invoke("agent-policy", "show")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded()["args"], [
            "cli", "agent-policy", "--root", str(self.workspace), "show"])

    def test_git_preserves_explicit_root_arguments_and_caller_directory(self):
        arguments = ["git", "--root", "relative-project", "--session", "fixture", "status"]
        result = self.invoke(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), {"args": ["cli", *arguments], "cwd": str(self.cwd)})

    def test_launcher_exit_status_is_preserved(self):
        result = self.invoke("--help", ADAPTER_EXIT="17")
        self.assertEqual(result.returncode, 17, result.stderr)

    def test_missing_or_nonexecutable_launcher_fails_without_fallback(self):
        self.launcher.unlink()
        result = self.invoke("workspace", "route", "README.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("launcher is unavailable", result.stderr)
        self.assertFalse(self.capture.exists())
        self.launcher.write_text("not executable\n")
        self.launcher.chmod(0o600)
        result = self.invoke("--help")
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not match its receipt", result.stderr)
        self.assertFalse(self.capture.exists())

    def test_launcher_bytes_and_missing_receipt_cannot_select_unverified_code(self):
        self.launcher.write_text("#!/bin/sh\nprintf unexpected > "
                                 + shlex.quote(str(self.capture)) + "\n")
        result = self.invoke("--help")
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not match its receipt", result.stderr)
        self.assertFalse(self.capture.exists())
        self.receipt.unlink()
        result = self.invoke("--help")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.capture.exists())

    def test_installation_update_lock_rejects_execution(self):
        with (self.launcher.parent / ".install.lock").open("rb") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.invoke("--help")
        self.assertEqual(result.returncode, 2)
        self.assertIn("updating", result.stderr)
        self.assertFalse(self.capture.exists())

    def test_symlink_or_relative_home_cannot_select_a_launcher(self):
        alias = self.base / "home-alias"
        alias.symlink_to(self.home, target_is_directory=True)
        for home in (str(alias), "relative-home"):
            with self.subTest(home=home):
                result = self.invoke("--help", CODEX_HOME=home)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.capture.exists())

    def test_development_mode_does_not_run_the_installed_engine(self):
        result = self.invoke("--source", "workspace", "route", "README.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("~/.codex/.codex/ecosystem/cli.py", result.stderr)
        self.assertFalse(self.capture.exists())

    def test_no_adjacent_engine_is_imported(self):
        # The historical source is absent. Even a malicious former sibling must
        # never be imported while selecting the installed launcher.
        (self.adapter.parent / "core.py").write_text("raise RuntimeError('local core ran')\n")
        (self.adapter.parent / "__init__.py").write_text("raise RuntimeError('local package ran')\n")
        result = self.invoke("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded()["args"], ["cli", "--help"])


if __name__ == "__main__":
    unittest.main()
