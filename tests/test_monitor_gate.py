"""Real native partial commits with synthetic monitor receipts and contents."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from constellation.git import GitError
from constellation.monitor_gate import PATHS, allow_snapshot


class MonitorGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'vault'
        self.root.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.hooksPath', str(self.root / '.git/hooks'))
        for name in (*PATHS, 'foreign.txt'):
            item = self.root / name
            item.parent.mkdir(parents=True, exist_ok=True)
            item.write_text('baseline\n')
        self.git('add', '--all')
        self.git('commit', '-m', 'Synthetic baseline')
        self.storage = self.root / '.git/notes-reminders-monitor'
        self.storage.mkdir(mode=0o700)
        self.receipt = self.storage / 'commit_attempt.json'
        self.registry = self.base / 'projects.json'
        identity = {}
        for name, path in (('owner', self.root), ('git_dir', self.root / '.git')):
            info = path.stat()
            identity[name] = [info.st_dev, info.st_ino]
        self.registry.write_text(json.dumps({'projects': [{'id': 'omaros', 'management': 'native',
            'root': str(self.root), 'filesystem_identity': identity}]}))
        source = Path(__file__).resolve().parents[1]
        hook = self.root / '.git/hooks/pre-commit'
        hook.write_text(f'#!{sys.executable}\nimport sys\nfrom pathlib import Path\n'
            f'sys.path.insert(0, {str(source)!r})\n'
            'from constellation.monitor_gate import allow_snapshot\n'
            f'if not allow_snapshot(Path.cwd(), registry=Path({str(self.registry)!r})): raise SystemExit(2)\n')
        hook.chmod(0o700)

    def command(self, *args, marker=None):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith('GIT_') and key != 'OMAROS_MONITOR_SNAPSHOT'}
        if marker is not None:
            env['OMAROS_MONITOR_SNAPSHOT'] = marker
        return subprocess.run(['git', '--no-replace-objects', '-C', str(self.root), *args],
                              capture_output=True, env=env, check=False, timeout=15)

    def git(self, *args):
        result = self.command(*args)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        return result.stdout

    def prepare(self):
        for name in PATHS:
            (self.root / name).write_text('synthetic generated snapshot\n')
        expected = {name: hashlib.sha256((self.root / name).read_bytes()).hexdigest() for name in PATHS}
        marker = hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        rows = [row for row in self.git('ls-files', '--stage', '-v', '-z').split(b'\0') if row]
        own = [row for row in rows if row.split(b'\t', 1)[1].decode() in PATHS]
        foreign = [row for row in rows if row.split(b'\t', 1)[1].decode() not in PATHS]
        receipt = {'schema_version': 1, 'snapshot_id': marker, 'expected': expected,
                   'parent': self.git('rev-parse', 'HEAD').decode().strip(),
                   'branch': self.git('symbolic-ref', 'HEAD').decode().strip(),
                   'own_index_sha256': hashlib.sha256(b''.join(row + b'\0' for row in own)).hexdigest(),
                   'index_fingerprint': hashlib.sha256(b'\0'.join(foreign)).hexdigest(),
                   'future_field': {'preserved': True}}
        self.receipt.write_text(json.dumps(receipt))
        self.receipt.chmod(0o600)
        return marker, receipt

    def commit(self, marker, extra=()):
        return self.command('commit', '--only', '-m', f'Snapshot\n\nOmarOS-Snapshot: {marker}',
                            '--', *PATHS, *extra, marker=marker)

    def test_absent_or_invalid_marker_has_no_receipt_effects(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(allow_snapshot(self.root, registry=self.registry))
        with patch.dict(os.environ, {'OMAROS_MONITOR_SNAPSHOT': 'bad'}):
            with self.assertRaisesRegex(GitError, 'marker'):
                allow_snapshot(self.root, registry=self.registry)
        self.assertFalse(self.receipt.exists())

    def test_real_partial_commit_preserves_foreign_staging_and_records_exact_proof(self):
        (self.root / 'foreign.txt').write_text('foreign staged\n')
        self.git('add', 'foreign.txt')
        self.git('update-index', '--assume-unchanged', 'foreign.txt')
        before = self.git('ls-files', '--stage', '-v', 'foreign.txt')
        marker, original = self.prepare()
        result = self.commit(marker)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        self.assertEqual(before, self.git('ls-files', '--stage', '-v', 'foreign.txt'))
        self.assertEqual(b'baseline\n', self.git('show', 'HEAD:foreign.txt'))
        self.assertEqual(set(PATHS), set(self.git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').decode().splitlines()))
        self.assertEqual({**original, 'guarded_snapshot': marker}, json.loads(self.receipt.read_text()))
        self.assertEqual(0o600, self.receipt.stat().st_mode & 0o777)

    def test_late_owned_staging_is_rejected_and_preserved(self):
        marker, original = self.prepare()
        (self.root / PATHS[0]).write_text('foreign version already staged\n')
        self.git('add', PATHS[0])
        staged = self.git('ls-files', '--stage', '-v', '-z')
        (self.root / PATHS[0]).write_text('synthetic generated snapshot\n')
        result = self.commit(marker)
        self.assertNotEqual(0, result.returncode)
        self.assertIn(b'concurrent staged work', result.stderr)
        self.assertEqual(staged, self.git('ls-files', '--stage', '-v', '-z'))
        self.assertEqual(original, json.loads(self.receipt.read_text()))

    def test_changed_expected_bytes_and_extra_paths_reject_without_proof(self):
        marker, original = self.prepare()
        (self.root / PATHS[0]).write_text('changed after receipt\n')
        self.assertNotEqual(0, self.commit(marker).returncode)
        (self.root / PATHS[0]).write_text('synthetic generated snapshot\n')
        (self.root / 'foreign.txt').write_text('unrelated changed\n')
        self.assertNotEqual(0, self.commit(marker, ('foreign.txt',)).returncode)
        self.assertEqual(original, json.loads(self.receipt.read_text()))

    def test_marker_cannot_enable_an_unenrolled_repository(self):
        marker, original = self.prepare()
        self.registry.write_text('{"projects": []}')
        result = self.commit(marker)
        self.assertNotEqual(0, result.returncode)
        self.assertIn(b'enrolled OmarOS', result.stderr)
        self.assertEqual(original, json.loads(self.receipt.read_text()))

    def test_unsafe_receipt_and_foreign_index_changes_fail_closed(self):
        marker, original = self.prepare()
        self.receipt.chmod(0o644)
        self.assertNotEqual(0, self.commit(marker).returncode)
        self.receipt.chmod(0o600)
        (self.root / 'foreign.txt').write_text('new unrelated staging\n')
        self.git('add', 'foreign.txt')
        result = self.commit(marker)
        self.assertNotEqual(0, result.returncode)
        self.assertIn(b'Foreign staged entries changed', result.stderr)
        self.assertEqual(original, json.loads(self.receipt.read_text()))

    def test_current_monitor_commit_snapshot_runs_on_synthetic_fixture(self):
        monitor = Path.home() / 'OmarOS/08_Systems_and_Infrastructure/Monitoring/notes_reminders_monitor.py'
        interpreter = Path.home() / '.venvs/omaros/bin/python'
        if not monitor.is_file() or not interpreter.is_file():
            self.skipTest('Optional installed-monitor compatibility fixture is unavailable')
        (self.root / 'foreign.txt').write_text('foreign staged compatibility fixture\n')
        self.git('add', 'foreign.txt')
        foreign = self.git('ls-files', '--stage', '-v', 'foreign.txt')
        for name in PATHS:
            (self.root / name).write_text('synthetic actual-monitor snapshot\n')
        # Exercise the real producer's receipt/hash/recovery contract. Only its
        # enrollment preflight is replaced: the test hook independently checks
        # this synthetic registry, while production uses the canonical registry.
        program = '''import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("monitor_fixture",sys.argv[1])
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.verify_native_git_guard=lambda root:None
root=Path(sys.argv[2])
expected=module.snapshot_hashes(root)
snapshot=module.snapshot_identifier(expected)
sha=module.commit_snapshot(root,expected,stamp="2026-11-15T00:00:00Z",snapshot_id=snapshot)
print(json.dumps({"sha":sha,"snapshot":snapshot}))
'''
        env = {key: value for key, value in os.environ.items()
               if not key.startswith('GIT_') and key != 'OMAROS_MONITOR_SNAPSHOT'}
        result = subprocess.run([str(interpreter), '-c', program, str(monitor), str(self.root)],
                                capture_output=True, env=env, check=False, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        proof = json.loads(result.stdout)
        self.assertEqual(proof['sha'], self.git('rev-parse', 'HEAD').decode().strip())
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(proof['snapshot'], receipt['guarded_snapshot'])
        self.assertEqual(proof['sha'], receipt['verified_commit'])
        self.assertEqual(foreign, self.git('ls-files', '--stage', '-v', 'foreign.txt'))


if __name__ == '__main__':
    unittest.main()
