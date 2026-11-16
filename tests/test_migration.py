"""Migration preserves concurrent edits and recovers interrupted filesystem moves."""
import json
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch

import migration


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.target = self.base / 'project/legacy.md'
        self.target.parent.mkdir()
        self.target.write_bytes(b'original')
        self.backup = self.base / 'backup'
        self.saved = self.backup / 'files' / self.target.relative_to('/')
        self.saved.parent.mkdir(parents=True)
        shutil.copy2(self.target, self.saved)
        self.row = {'path': str(self.target), 'sha256': migration.digest(self.target),
                    'symlink': False, 'mode': stat.S_IMODE(self.target.stat().st_mode)}
        self.plan = {'schema_version': 1, 'files': [self.row], 'consumer_edits': [], 'git': []}
        self.evidence = {name: True for name in migration.REQUIRED_CHECKS}
        self.evidence['consumers_repointed'] = True
        self.save_plan()
        self.addCleanup(patch.stopall)
        patch.object(migration, 'candidate_roots', return_value=[(self.target, 'test legacy entry')]).start()

    def save_plan(self):
        (self.backup / 'manifest.json').write_text(json.dumps(self.plan))

    def consumer(self):
        self.plan['files'] = []
        self.plan['consumer_edits'] = [{**self.row, 'content': 'installed'}]
        self.save_plan()

    def assert_protected(self):
        self.assertEqual(self.saved.read_bytes(), b'original')

    def test_consumer_capture_rejects_and_preserves_raced_edit(self):
        self.consumer()
        rename = migration._rename_exclusive
        def racing_rename(source, destination):
            if source == self.target:
                self.target.write_bytes(b'concurrent foreign edit')
            return rename(source, destination)
        with patch.object(migration, '_rename_exclusive', racing_rename):
            with self.assertRaisesRegex(ValueError, 'Concurrent edit preserved'):
                migration.apply_consumers(self.plan, self.backup)
        self.assertEqual(self.target.read_bytes(), b'concurrent foreign edit')
        self.assert_protected()
        with self.assertRaisesRegex(ValueError, 'subsequent edits'):
            migration.restore(self.backup)

    def test_consumer_install_does_not_replace_recreated_destination(self):
        self.consumer()
        rename = migration._rename_exclusive
        def racing_rename(source, destination):
            if destination == self.target:
                self.target.write_bytes(b'concurrent new destination')
            return rename(source, destination)
        with patch.object(migration, '_rename_exclusive', racing_rename):
            with self.assertRaises(FileExistsError):
                migration.apply_consumers(self.plan, self.backup)
        self.assertEqual(self.target.read_bytes(), b'concurrent new destination')
        captured = self.backup / 'quarantine/consumers' / self.target.relative_to('/')
        self.assertEqual(captured.read_bytes(), b'original')
        self.assert_protected()

    def test_retirement_preserves_edit_after_durable_intent(self):
        record = migration.record_intent
        def racing_record(backup, name, paths):
            record(backup, name, paths)
            if name == 'removed.json':
                self.target.write_bytes(b'concurrent foreign edit')
        with patch.object(migration, 'record_intent', racing_record):
            with self.assertRaisesRegex(ValueError, 'Concurrent edit preserved'):
                migration.retire(self.plan, self.backup, self.evidence)
        self.assertEqual(self.target.read_bytes(), b'concurrent foreign edit')
        self.assert_protected()
        self.assertEqual(json.loads((self.backup / 'removed.json').read_text()), [str(self.target)])

    def test_restore_does_not_replace_concurrently_created_destination(self):
        self.target.unlink()
        migration.record_intent(self.backup, 'removed.json', [str(self.target)])
        rename = migration._rename_exclusive
        def racing_rename(source, destination):
            if destination == self.target:
                self.target.write_bytes(b'concurrent foreign edit')
            return rename(source, destination)
        with patch.object(migration, '_rename_exclusive', racing_rename):
            with self.assertRaises(FileExistsError):
                migration.restore(self.backup)
        self.assertEqual(self.target.read_bytes(), b'concurrent foreign edit')
        self.assert_protected()

    def test_restore_capture_preserves_concurrent_edit_to_installed_consumer(self):
        self.consumer()
        migration.apply_consumers(self.plan, self.backup)
        rename = migration._rename_exclusive
        def racing_rename(source, destination):
            if source == self.target:
                self.target.write_bytes(b'concurrent foreign edit')
            return rename(source, destination)
        with patch.object(migration, '_rename_exclusive', racing_rename):
            with self.assertRaisesRegex(ValueError, 'Concurrent edit preserved'):
                migration.restore(self.backup)
        self.assertEqual(self.target.read_bytes(), b'concurrent foreign edit')
        self.assert_protected()

    def test_interrupted_consumer_capture_recovers_original(self):
        self.consumer()
        self.interrupt_after_capture(lambda: migration.apply_consumers(self.plan, self.backup))
        self.assertEqual(migration.restore(self.backup), [str(self.target)])
        self.assertEqual(self.target.read_bytes(), b'original')

    def test_interrupted_retirement_capture_recovers_original(self):
        self.interrupt_after_capture(lambda: migration.retire(self.plan, self.backup, self.evidence))
        self.assertEqual(migration.restore(self.backup), [str(self.target)])
        self.assertEqual(self.target.read_bytes(), b'original')

    def test_interrupted_restore_capture_retries_without_overwriting(self):
        self.consumer()
        migration.apply_consumers(self.plan, self.backup)
        self.interrupt_after_capture(lambda: migration.restore(self.backup))
        self.assertEqual(migration.restore(self.backup), [str(self.target)])
        self.assertEqual(self.target.read_bytes(), b'original')
        self.assertEqual(migration.restore(self.backup), [])

    def interrupt_after_capture(self, action):
        rename = migration._rename_exclusive
        def interrupted_rename(source, destination):
            rename(source, destination)
            if source == self.target:
                raise KeyboardInterrupt('after capture')
        with patch.object(migration, '_rename_exclusive', interrupted_rename):
            with self.assertRaises(KeyboardInterrupt):
                action()
        self.assertFalse(self.target.exists())
        self.assert_protected()

    def test_open_writer_keeps_reachable_inode_after_retirement(self):
        with self.target.open('r+b') as writer:
            migration.retire(self.plan, self.backup, self.evidence)
            writer.write(b'late writer data')
            writer.flush()
        captured = self.backup / 'quarantine/retired' / self.target.relative_to('/')
        self.assertEqual(captured.read_bytes(), b'late writer data')
        self.assert_protected()

    def test_legacy_receipt_restores_from_existing_backup(self):
        self.target.unlink()
        migration.record_intent(self.backup, 'removed.json', [str(self.target)])
        self.assertEqual(migration.restore(self.backup), [str(self.target)])
        self.assertEqual(self.target.read_bytes(), b'original')


if __name__ == '__main__':
    unittest.main()
