"""The independently approved external course code is the code that executes."""
from __future__ import annotations

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


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/course_engine.py"
spec = importlib.util.spec_from_file_location("testable_course_engine", SCRIPT)
assert spec is not None and spec.loader is not None
engine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = engine
spec.loader.exec_module(engine)


class CourseEngineTrustTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.home = self.root / "device"
        self.home.mkdir(mode=0o700)
        self.environment = patch.dict(os.environ, {"CODEX_HOME": str(self.home)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.repo = self.root / "course"
        self.source = self.repo / "_sistema"
        self.code = self.source / "scripts/entry.py"
        self.code.parent.mkdir(parents=True)
        self.code.write_text("print('approved release')\n")
        self.code.chmod(0o755)
        (self.source / "MANUAL.md").write_text("A synthetic template.\n")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.git("add", "--", "_sistema")
        tree = self.git("write-tree").strip()
        self.tree = self.git("rev-parse", f"{tree}:_sistema").strip()
        self.policy = self.home / engine.POLICY
        self.approve(self.tree)

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], text=True, capture_output=True,
                              check=True).stdout

    def approve(self, tree):
        # An explicit, isolated operator action, separate from verification.
        result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "inventory",
                                 "--repository", str(self.repo), "--tree", tree],
                                text=True, capture_output=True, check=True)
        self.policy.write_text(result.stdout)
        self.policy.chmod(0o600)

    def test_helper_runs_verified_bytes_while_the_worktree_changes(self):
        cache = self.code.parent / "__pycache__"
        cache.mkdir()
        (cache / "entry.cpython-312.pyc").write_bytes(b"untrusted bytecode")
        (self.source / "empty-assets").mkdir()
        with engine.trusted_engine(self.source) as snapshot:
            copy = snapshot.path / "scripts/entry.py"
            self.assertNotEqual(copy.stat().st_ino, self.code.stat().st_ino)
            self.assertEqual(snapshot.source, self.source)
            self.assertFalse((snapshot.path / "scripts/__pycache__").exists())
            self.assertFalse((snapshot.path / "empty-assets").exists())
            self.code.write_text("raise RuntimeError('unreviewed change')\n")
            result = subprocess.run([sys.executable, "-I", "-B", str(copy)], text=True,
                                    capture_output=True, check=True)
            self.assertEqual(result.stdout, "approved release\n")
        self.assertFalse(snapshot.path.exists())
        with self.assertRaises(engine.EngineTrustError):
            engine.verify_engine_source(self.source)

    def test_source_path_and_git_head_do_not_grant_engine_approval(self):
        first = engine.verify_engine_source(self.source)
        self.code.write_text("print('next reviewed release')\n")
        self.git("add", "--", "_sistema")
        next_tree = self.git("rev-parse", self.git("write-tree").strip() + ":_sistema").strip()
        self.assertNotEqual(self.tree, next_tree)
        with self.assertRaises(engine.EngineTrustError):
            with engine.trusted_engine(self.source):
                self.fail("Unapproved executable made available")
        self.approve(next_tree)
        self.assertNotEqual(first, engine.verify_engine_source(self.source))
        self.policy.unlink()
        with self.assertRaises(engine.EngineTrustError):
            engine.verify_engine_source(self.source)

    def test_modification_links_modes_and_undeclared_siblings_are_rejected(self):
        original = self.code.read_bytes()
        mode = self.code.stat().st_mode & 0o777
        for attack in ("bytes", "file-link", "hardlink", "mode", "extra-code", "directory-link",
                       "cache-link", "cache-code", "special"):
            with self.subTest(attack=attack):
                self.code.write_bytes(original)
                self.code.chmod(mode)
                extra = self.source / "unexpected.py"
                alias = self.root / "alias"
                cache = self.code.parent / "__pycache__"
                if attack == "bytes":
                    self.code.write_bytes(b"x" * len(original))
                elif attack == "file-link":
                    self.code.rename(alias)
                    self.code.symlink_to(alias)
                elif attack == "hardlink":
                    os.link(self.code, alias)
                elif attack == "mode":
                    self.code.chmod(0o644)
                elif attack == "extra-code":
                    extra.write_text("raise RuntimeError('never execute')\n")
                elif attack == "directory-link":
                    extra.symlink_to(self.root, target_is_directory=True)
                elif attack == "cache-link":
                    cache.symlink_to(self.root, target_is_directory=True)
                elif attack == "cache-code":
                    cache.mkdir()
                    (cache / "payload.py").write_text("raise RuntimeError('never execute')\n")
                else:
                    self.code.unlink()
                    os.mkfifo(self.code)
                with self.assertRaises((engine.EngineTrustError, OSError)):
                    engine.verify_engine_source(self.source)
                if self.code.is_symlink():
                    self.code.unlink()
                    alias.rename(self.code)
                elif attack == "special":
                    self.code.unlink()
                alias.unlink(missing_ok=True)
                extra.unlink(missing_ok=True)
                if cache.is_symlink():
                    cache.unlink()
                elif cache.is_dir():
                    (cache / "payload.py").unlink()
                    cache.rmdir()

    def test_device_policy_never_silently_falls_back_or_follows_a_link(self):
        pristine = self.policy.read_bytes()
        self.policy.chmod(0o644)
        with self.assertRaisesRegex(engine.EngineTrustError, "0600"):
            engine.verify_engine_source(self.source)
        self.policy.chmod(0o600)
        self.policy.write_text('{"schema":1,"schema":1}')
        with self.assertRaisesRegex(engine.EngineTrustError, "Duplicate"):
            engine.verify_engine_source(self.source)
        other = self.root / "foreign-policy"
        self.policy.unlink()
        other.write_bytes(pristine)
        self.policy.symlink_to(other)
        with self.assertRaises(OSError):
            engine.verify_engine_source(self.source)

    def test_unprotected_temporary_parent_cannot_host_executable_code(self):
        unsafe = self.root / "unprotected"
        unsafe.mkdir()
        unsafe.chmod(0o777)
        with patch.object(tempfile, "gettempdir", return_value=str(unsafe)):
            with self.assertRaisesRegex(engine.EngineTrustError, "ownership and permissions"):
                with engine.trusted_engine(self.source):
                    self.fail("An unprotected parent could replace the execution snapshot")

    def test_inventory_does_not_trust_candidate_code_or_mutate_policy(self):
        before = self.policy.read_bytes()
        computed = engine.candidate_inventory(self.repo, self.tree)
        self.assertEqual(computed["files"]["scripts/entry.py"]["sha256"],
                         hashlib.sha256(self.code.read_bytes()).hexdigest())
        self.assertEqual(computed, json.loads(before))
        (self.source / "symlink").symlink_to(self.code)
        self.git("add", "--", "_sistema")
        unsafe_tree = self.git("rev-parse", self.git("write-tree").strip() + ":_sistema").strip()
        with self.assertRaisesRegex(engine.EngineTrustError, "regular"):
            engine.candidate_inventory(self.repo, unsafe_tree)
        self.assertEqual(before, self.policy.read_bytes())


if __name__ == "__main__":
    unittest.main()
