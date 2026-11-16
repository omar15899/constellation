"""Behavioral tests of native entry installation and guarded recovery."""
import json
from pathlib import Path
import subprocess
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from constellation import install


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'source'
        self.home = self.base / 'home'
        (self.source / 'agents').mkdir(parents=True)
        (self.home / '.codex').mkdir(parents=True)
        (self.source / 'instructions').mkdir()
        (self.source / 'instructions/AGENTS.md').write_text('Use central instructions.\n')
        for number in range(8):
            (self.source / f'agents/role{number}.toml').write_text(f'name = "role{number}"\ndescription = "Role {number}"\ndeveloper_instructions = "Read contracts."\n')
        skill = self.source / 'skills/core/coding'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: coding\ndescription: Coding\n---\n')
        self.entries = [{'group': 'core', 'name': 'coding', 'source': str(self.home / '.codex/.codex/skills/coding'), 'destination': 'skills/core/coding', 'project_root': None}]
        (self.source / 'resource-inventory.json').write_text(json.dumps({'entries': self.entries}))
        self.config = self.home / '.codex/config.toml'
        self.original = 'model = "chosen-model"\n[features]\nmemories = false\nhooks = true\n[memories]\ngenerate_memories = false\n[marketplaces.constellation]\nsource = "/old/source"\n[hooks.state."/old/unrelated"]\ntrusted_hash = "preserve"\n'
        self.config.write_text(self.original)

    def plan(self):
        return install.build_plan(self.source, self.home)

    def test_preview_is_read_only_and_roundtrip_preserves_private_config(self):
        before = install.fingerprint(self.home)
        plan = self.plan()
        self.assertEqual(install.fingerprint(self.home), before)
        receipt = install.apply_plan(plan)
        config = tomllib.loads(self.config.read_text())
        self.assertEqual(config['model'], 'chosen-model')
        self.assertFalse(config['features']['memories'])
        self.assertFalse(config['memories']['generate_memories'])
        self.assertEqual(len(config['agents']), 8)
        self.assertEqual(config['hooks']['state']['/old/unrelated']['trusted_hash'], 'preserve')
        self.assertTrue((self.home / '.agents/skills/coding').is_symlink())
        self.assertTrue((self.home / '.codex/AGENTS.md').is_symlink())
        self.assertEqual(self.plan()['operations'], [])
        install.rollback(receipt)
        self.assertEqual(self.config.read_text(), self.original)
        self.assertFalse((self.home / '.agents/skills/coding').exists())

    def test_reinstall_retains_native_trust_and_unrelated_hooks(self):
        hooks = self.home / '.codex/hooks.json'
        hooks.write_text(json.dumps({'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo unrelated'}]}]}}))
        install.apply_plan(self.plan())
        self.config.write_text(self.config.read_text() + '\n[hooks.state."' + str(hooks) + ':stop:1:0"]\ntrusted_hash = "native-current-value"\n')
        plan = self.plan()
        self.assertFalse(any(op['path'] in (str(self.config), str(hooks)) for op in plan['operations']))
        self.assertEqual(len(json.loads(hooks.read_text())['hooks']['Stop']), 2)

    def test_install_disables_only_existing_legacy_plugin(self):
        unrelated = '\n[plugins."other@provider"]\nenabled = true\nsetting = "preserve"\n'
        for enabled in (None, True, False):
            with self.subTest(legacy_enabled=enabled):
                original = self.original + unrelated
                if enabled is not None:
                    original += '\n[plugins."constellation@constellation"]\nenabled = ' + str(enabled).lower() + '\n'
                self.config.write_text(original)
                receipt = install.apply_plan(self.plan())
                config = tomllib.loads(self.config.read_text())
                self.assertEqual(config['plugins']['other@provider'],
                                 {'enabled': True, 'setting': 'preserve'})
                if enabled is None:
                    self.assertNotIn('constellation@constellation', config['plugins'])
                else:
                    self.assertFalse(config['plugins']['constellation@constellation']['enabled'])
                self.assertEqual(self.plan()['operations'], [])
                install.rollback(receipt)
                self.assertEqual(self.config.read_text(), original)

    def test_changed_input_aborts_before_any_mutation(self):
        plan = self.plan()
        self.config.write_text(self.original + '# user edit\n')
        with self.assertRaisesRegex(ValueError, 'input changed'):
            install.apply_plan(plan)
        self.assertFalse((self.home / '.codex/hooks.json').exists())

    def test_rollback_rejects_edit_after_installation(self):
        receipt = install.apply_plan(self.plan())
        self.config.write_text(self.config.read_text() + '# user edit\n')
        with self.assertRaisesRegex(ValueError, 'overwrite changes'):
            install.rollback(receipt)
        self.assertTrue(self.config.read_text().endswith('# user edit\n'))

    def test_interruption_between_directory_move_and_link_is_recoverable(self):
        directory = self.home / '.agents/skills/coding'
        directory.mkdir(parents=True)
        (directory / 'local.txt').write_text('Preserve local resource')
        original_replace = install._rename_exclusive
        def replace(path, target):
            if Path(target) == directory:
                raise OSError('simulated interruption')
            return original_replace(path, target)
        with patch.object(install, '_rename_exclusive', replace):
            with self.assertRaisesRegex(OSError, 'simulated interruption'):
                install.apply_plan(self.plan())
        receipt = next((self.home / '.local/state/constellation/installations').glob('*/receipt.json'))
        self.assertFalse(directory.exists())
        install.rollback(receipt)
        self.assertEqual((directory / 'local.txt').read_text(), 'Preserve local resource')
        self.assertEqual(self.config.read_text(), self.original)

    def test_interrupted_rollback_restores_on_retry(self):
        receipt = install.apply_plan(self.plan())
        original_rename = install._rename_exclusive
        def rename(path, target):
            if Path(target) == self.config and 'restore' in path.parts:
                raise OSError('rollback interrupted')
            return original_rename(path, target)
        with patch.object(install, '_rename_exclusive', rename):
            with self.assertRaisesRegex(OSError, 'rollback interrupted'):
                install.rollback(receipt)
        self.assertFalse(self.config.exists())
        install.rollback(receipt)
        self.assertEqual(self.config.read_text(), self.original)

    def test_concurrent_edit_during_rollback_is_retained(self):
        receipt = install.apply_plan(self.plan())
        original_save = install._save_receipt
        injected = False
        def save(path, data):
            nonlocal injected
            if not injected and any(op['path'] == str(self.config) and op['status'] == 'reverting' for op in data['operations']):
                self.config.write_text('model = "concurrent user edit"\n')
                injected = True
            return original_save(path, data)
        with patch.object(install, '_save_receipt', save):
            with self.assertRaisesRegex(ValueError, 'overwrite changes'):
                install.rollback(receipt)
        self.assertEqual(self.config.read_text(), 'model = "concurrent user edit"\n')

    def test_restore_never_clobbers_file_created_at_final_rename(self):
        receipt = install.apply_plan(self.plan())
        original_rename = install._rename_exclusive
        def rename(path, target):
            if Path(target) == self.config and 'restore' in path.parts:
                self.config.write_text('model = "late foreign edit"\n')
            return original_rename(path, target)
        with patch.object(install, '_rename_exclusive', rename):
            with self.assertRaises(FileExistsError):
                install.rollback(receipt)
        self.assertEqual(self.config.read_text(), 'model = "late foreign edit"\n')
        self.assertTrue(any((receipt.parent / 'before').iterdir()))

    def test_apply_keeps_edit_racing_the_backup_move(self):
        plan = self.plan()
        original_rename = install._rename_exclusive
        injected = False
        def rename(path, target):
            nonlocal injected
            if path == self.config and not injected:
                self.config.write_text('model = "concurrent installation edit"\n')
                injected = True
            return original_rename(path, target)
        with patch.object(install, '_rename_exclusive', rename):
            with self.assertRaisesRegex(ValueError, 'edit preserved'):
                install.apply_plan(plan)
        self.assertEqual(self.config.read_text(), 'model = "concurrent installation edit"\n')

    def test_claude_agent_links_survive_idempotent_reinstallation(self):
        adapters = self.source / 'resources/native-claude-agents'
        adapters.mkdir(parents=True)
        (adapters / 'coder.md').write_text('---\nname: coder\n---\nInstructions.\n')
        install.apply_plan(self.plan())
        alias = self.home / '.claude/agents/coder.md'
        self.assertTrue(alias.is_symlink())
        self.assertFalse(any(op['path'] == str(alias) for op in self.plan()['operations']))

    def test_git_hook_configuration_roundtrip_preserves_unrelated_config(self):
        project = self.base / 'project'
        subprocess.run(['git', 'init', '-q', str(project)], check=True)
        subprocess.run(['git', '-C', str(project), 'config', 'core.hooksPath', '.githooks'], check=True)
        (self.source / 'profiles').mkdir()
        (self.source / 'profiles/projects.json').write_text(json.dumps({'projects': [{'id': 'project', 'root': str(project), 'management': 'native'}]}))
        receipt = install.apply_plan(self.plan())
        self.assertEqual(install._git_hooks(project), [str(self.source / 'git-hooks')])
        subprocess.run(['git', '-C', str(project), 'config', 'user.name', 'Preserve User'], check=True)
        install.rollback(receipt)
        self.assertEqual(install._git_hooks(project), ['.githooks'])
        result = subprocess.check_output(['git', '-C', str(project), 'config', 'user.name'], text=True).strip()
        self.assertEqual(result, 'Preserve User')

    def git_plan(self, name):
        project = self.base / name
        subprocess.run(['git', 'init', '-q', str(project)], check=True)
        subprocess.run(['git', '-C', str(project), 'config', 'core.hooksPath', 'original-hooks'], check=True)
        operation = {'path': str(project), 'kind': 'git-hooks', 'value': 'central-hooks',
                     'before': install._values_fingerprint(['original-hooks']),
                     'before_values': ['original-hooks']}
        plan = {'source': str(self.source), 'state_dir': str(self.home / '.local/state/constellation'),
                'operations': [operation]}
        return project, plan

    def test_git_config_change_before_lock_is_preserved_on_apply_and_rollback(self):
        for phase in ('apply', 'rollback'):
            with self.subTest(phase=phase):
                project, plan = self.git_plan(phase)
                receipt = install.apply_plan(plan) if phase == 'rollback' else None
                native_open = install.os.open
                def concurrent_open(path, flags, mode=0o777, **kwargs):
                    if Path(path) == project / '.git/config.lock':
                        subprocess.run(['git', '-C', str(project), 'config',
                                        'core.hooksPath', 'foreign-hooks'], check=True)
                    return native_open(path, flags, mode, **kwargs)
                with patch.object(install.os, 'open', concurrent_open):
                    with self.assertRaisesRegex(ValueError, 'changed before locked update'):
                        install.rollback(receipt) if receipt else install.apply_plan(plan)
                self.assertEqual(install._git_hooks(project), ['foreign-hooks'])
                self.assertFalse((project / '.git/config.lock').exists())

    def test_native_git_writer_cannot_change_configuration_during_transaction(self):
        project, plan = self.git_plan('locked-writer')
        native_run = subprocess.run
        competing_codes = []
        def competing_run(argv, **kwargs):
            if '--file' in argv and '--replace-all' in argv:
                attempt = native_run(['git', '-C', str(project), 'config',
                                      'core.hooksPath', 'foreign-hooks'], capture_output=True)
                competing_codes.append(attempt.returncode)
            return native_run(argv, **kwargs)
        with patch.object(subprocess, 'run', competing_run):
            receipt = install.apply_plan(plan)
            install.rollback(receipt)
        self.assertEqual(len(competing_codes), 2)
        self.assertTrue(all(code != 0 for code in competing_codes))
        self.assertEqual(install._git_hooks(project), ['original-hooks'])

    def test_direct_edit_at_atomic_config_exchange_keeps_foreign_bytes(self):
        for phase in ('apply', 'rollback'):
            with self.subTest(phase=phase):
                project, plan = self.git_plan('direct-' + phase)
                receipt = install.apply_plan(plan) if phase == 'rollback' else None
                native_exchange = install._rename_exchange
                injected = False
                def racing_exchange(source, destination):
                    nonlocal injected
                    if not injected:
                        config = project / '.git/config'
                        config.write_text(config.read_text().replace(
                            'central-hooks' if phase == 'rollback' else 'original-hooks', 'foreign-direct-hooks'))
                        injected = True
                    return native_exchange(source, destination)
                with patch.object(install, '_rename_exchange', racing_exchange):
                    with self.assertRaisesRegex(ValueError, 'direct Git config edit preserved'):
                        install.rollback(receipt) if receipt else install.apply_plan(plan)
                self.assertEqual(install._git_hooks(project), ['foreign-direct-hooks'])
                self.assertTrue((project / '.git/config.lock').exists())

    def test_preopened_config_descriptor_remains_recoverable_after_publication(self):
        for phase in ('apply', 'rollback'):
            with self.subTest(phase=phase):
                project, plan = self.git_plan('descriptor-' + phase)
                receipt = install.apply_plan(plan) if phase == 'rollback' else None
                config = project / '.git/config'
                native_rename = install._rename_exclusive
                with config.open('r+b') as writer:
                    original_inode = install.os.fstat(writer.fileno()).st_ino
                    def write_late(text):
                        writer.seek(0)
                        writer.write(text)
                        writer.truncate()
                        writer.flush()
                    def racing_rename(source, destination):
                        if source.name == 'config.lock' and destination.name == 'config.before':
                            write_late(b'late write after verification\n')
                        return native_rename(source, destination)
                    with patch.object(install, '_rename_exclusive', racing_rename):
                        if receipt:
                            install.rollback(receipt)
                        else:
                            receipt = install.apply_plan(plan)
                    group = 'git-config-rollback' if phase == 'rollback' else 'git-config'
                    retained = next((receipt.parent / group).glob('*/*/config.before'))
                    self.assertEqual(retained.stat().st_ino, original_inode)
                    self.assertEqual(retained.read_bytes(), b'late write after verification\n')
                    write_late(b'even later write after return\n')
                    self.assertEqual(retained.read_bytes(), b'even later write after return\n')
                    journal = json.loads(retained.with_name('journal.json').read_text())
                    self.assertEqual(journal['status'], 'published_original_inode_retained')
                self.assertFalse((project / '.git/config.lock').exists())
                self.assertEqual(install._git_hooks(project),
                                 ['original-hooks' if phase == 'rollback' else 'central-hooks'])


if __name__ == '__main__':
    unittest.main()
