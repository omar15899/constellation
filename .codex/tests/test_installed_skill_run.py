"""Exercise allowlisted public helper selection under an actual installed release."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_workflow import CODEX, install_test_bundle
from ecosystem.build import AVAILABLE_MODULES, build_bundle


@unittest.skipIf(os.name == "nt", "Codex device installation is a POSIX target")
class InstalledHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.base = Path(temporary.name).resolve()
        cls.vault, cls.foreign = (cls.base / name for name in ("vault", "foreign"))
        for root in (cls.vault, cls.foreign):
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            marker = root / "05_Projects/OmarOS/Architecture/OmarOS_Architecture.md"
            marker.parent.mkdir(parents=True)
            marker.write_text("Fixture architecture")
            (root / ".gitignore").write_text("/06_Knowledge_Base/Mathematics/Finance/ENGIE/Private/\n")
        cls.note = "06_Knowledge_Base/Mathematics/Examples/CanonicalToken.md"
        note = cls.vault / cls.note
        note.parent.mkdir(parents=True)
        note.write_text("---\ntitle: CanonicalToken\ntags: [example]\n---\nUnique specimen.\n")
        cls.home = cls.base / "device"
        cls.bundle = cls.base / "bundle"
        build_bundle(cls.bundle, modules=AVAILABLE_MODULES, source_root=CODEX)
        install_test_bundle(cls.bundle, cls.home)
        shadow = cls.base / "bin"
        shadow.mkdir()
        for name in ("python3", "git", "rg"):
            binary = shadow / name
            binary.write_text("#!/bin/sh\nexit 96\n")
            binary.chmod(0o755)
        cls.environment = {**os.environ, "CODEX_HOME": str(cls.home), "PATH": str(shadow),
                           "GIT_DIR": str(cls.foreign / ".git"), "PYTHONPATH": str(cls.foreign)}
        cls.device = str(cls.home / "constellation/run")
        subprocess.run([cls.device, "register-vault", "--project-root", str(cls.vault)],
                       cwd=cls.foreign, env=cls.environment, capture_output=True, text=True, check=True)

    def dispatch(self, *args: str, cwd: Path | None = None):
        return subprocess.run([self.device, "cli", "skill-run", *args], cwd=cwd or self.vault,
                              env=self.environment, capture_output=True, text=True, timeout=60)

    def test_registered_vault_uses_device_python_and_tools(self):
        result = self.dispatch("fast-finder", "search", "--root", str(self.vault),
                               "CanonicalToken", cwd=self.foreign)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(self.note, result.stdout)
        self.assertIsInstance(json.loads(result.stdout), dict)
        nested = self.vault / "06_Knowledge_Base"
        result = self.dispatch("fast-finder", "query", "--help", cwd=nested)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage", result.stdout)
        authorized_help = self.dispatch("engie-learning", "learning", "--help", cwd=nested)
        self.assertEqual(authorized_help.returncode, 0, authorized_help.stderr)
        self.assertIn("prepare", authorized_help.stdout)
        status = self.dispatch("engie-learning", "learning", "status", cwd=nested)
        self.assertEqual(status.returncode, 0, status.stderr or status.stdout)
        observed = json.loads(status.stdout)
        self.assertEqual(observed["status"], "ready")
        self.assertTrue(Path(observed["state"]).is_relative_to(self.vault / ".git"))

    def test_unregistered_owner_override_or_executable_is_rejected(self):
        for args in (["--root", str(self.foreign)], ["--root=" + str(self.foreign)],
                     ["--root", str(self.vault), "--root", str(self.foreign)],
                     ["--ro=" + str(self.foreign)]):
            result = self.dispatch("fast-finder", "search", *args, "CanonicalToken")
            self.assertNotEqual(result.returncode, 0, args)
            self.assertNotIn(self.note, result.stdout)
        # An option after '--' is positional; it may not override the pinned root.
        result = self.dispatch("fast-finder", "search", "--", "--root=" + str(self.foreign))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["query"], "--root=" + str(self.foreign))
        self.assertNotEqual(self.dispatch("engie-learning", "learning", "status",
                                          cwd=self.foreign).returncode, 0)
        marker = self.base / "never-executed"
        injected = self.foreign / "injected.py"
        injected.write_text(f"open({str(marker)!r}, 'w').close()")
        for args in (("fast-finder", str(injected)), ("../fast-finder", "search"),
                     ("engie-learning", "scripts/learning.py")):
            self.assertNotEqual(self.dispatch(*args).returncode, 0)
        self.assertFalse(marker.exists())

    def test_course_context_supports_a_separate_project(self):
        result = self.dispatch("brainteasers-quant-notes", "context", "--help", cwd=self.foreign)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--project", result.stdout)
        raw = subprocess.run([sys.executable, "-I", str(self.bundle / "ecosystem/cli.py"), "skill-run",
                              "brainteasers-quant-notes", "context", "--help"], env=self.environment,
                             capture_output=True, text=True, cwd=self.foreign)
        self.assertEqual(raw.returncode, 2)
        self.assertIn("verified device launcher", raw.stderr)
