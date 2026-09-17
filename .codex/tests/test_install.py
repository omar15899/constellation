"""Install in temporary repositories, preserving other users' Git hooks."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'install.py'
spec = importlib.util.spec_from_file_location('native_install', MODULE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', 'config', '--local', 'core.hooksPath', str(self.root / '.git/hooks')], cwd=self.root, check=True)
        shutil.copytree(MODULE.parent / 'git-hooks', self.root / '.codex/git-hooks')

    def tearDown(self):
        self.temp.cleanup()

    def test_installs_and_is_idempotent(self):
        first = installer.install(self.root)
        state = self.root / '.git/constellation/installation.json'
        original = state.read_bytes()
        stamp = state.stat().st_mtime_ns
        self.assertEqual(installer.install(self.root), first)
        self.assertEqual(state.read_bytes(), original)
        self.assertEqual(state.stat().st_mtime_ns, stamp)
        self.assertEqual(installer.git(self.root, 'config', '--local', '--get', 'core.hooksPath'), '.codex/git-hooks')
        self.assertEqual(first['codex_hook_trust'], 'requires_native_user_review')

    def test_preserves_existing_git_hook(self):
        hook = self.root / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 0\n')
        original = installer.git(self.root, 'config', '--get', 'core.hooksPath')
        with self.assertRaisesRegex(ValueError, 'Existing Git hooks'):
            installer.install(self.root)
        self.assertEqual(hook.read_text(), '#!/bin/sh\nexit 0\n')
        self.assertEqual(installer.git(self.root, 'config', '--get', 'core.hooksPath'), original)
        self.assertFalse((self.root / '.git/constellation').exists())

    def test_preserves_custom_hook_directory(self):
        custom = self.root / 'custom hooks'
        custom.mkdir()
        (custom / 'pre-push').write_text('custom hook')
        subprocess.run(['git', 'config', '--local', 'core.hooksPath', str(custom)], cwd=self.root, check=True)
        with self.assertRaisesRegex(ValueError, 'Existing Git hooks'):
            installer.install(self.root)
        self.assertEqual((custom / 'pre-push').read_text(), 'custom hook')

    def test_rejects_symlinked_guard(self):
        hook = self.root / '.codex/git-hooks/pre-commit'
        hook.unlink()
        hook.symlink_to(self.root / 'outside')
        with self.assertRaisesRegex(ValueError, 'regular local files'):
            installer.install(self.root)

    def test_rejects_subdirectory(self):
        child = self.root / 'child'
        child.mkdir()
        with self.assertRaisesRegex(ValueError, 'repository root'):
            installer.install(child)


if __name__ == '__main__':
    unittest.main()
