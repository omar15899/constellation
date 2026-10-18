"""Concurrency policy tests: byte preservation, fail-closed scope and real Git owners."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    import tomllib
except ImportError:
    tomllib = None

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE))
from ecosystem.runtime import agent_policy as ap
from ecosystem.runtime.workspace import Workspace
from ecosystem.runtime.workflow import Blocked, git


class RenderingTests(unittest.TestCase):
    def test_preserves_model_permissions_comments_and_roles(self):
        source = ('# User configuration\nmodel = "chosen-model"\nmodel_reasoning_effort = "high"\n'
                  'approval_policy = "never"\n\n[features]\nhooks = true # trusted separately\n'
                  '\n[agents]\n# Keep this comment\nmax_depth = 2\n'
                  '\n[agents.reviewer]\ndescription = "review role"\n')
        rendered = ap.render_config(source, 6)
        block = f'{ap.BEGIN}\n{ap.KEY} = 6\n{ap.END}\n'
        self.assertEqual(rendered.replace(block, ''), source)
        self.assertEqual(ap.render_config(rendered, 6), rendered)
        changed = ap.render_config(rendered, 9)
        self.assertEqual(changed, rendered.replace(f'{ap.KEY} = 6', f'{ap.KEY} = 9'))
        if tomllib is not None:
            parsed = tomllib.loads(changed)
            self.assertEqual(parsed['agents'][ap.KEY], 9)
            self.assertEqual(parsed['model'], 'chosen-model')
            self.assertEqual(parsed['agents']['reviewer']['description'], 'review role')

    def test_new_table_and_subsequent_user_settings_keep_their_scope(self):
        source = '# Native profile\n'
        first = ap.render_config(source, 6)
        self.assertTrue(first.startswith(source))
        with_user_setting = first + 'max_depth = 2\n'
        updated = ap.render_config(with_user_setting, 8)
        self.assertTrue(updated.endswith('max_depth = 2\n'))
        if tomllib is not None:
            self.assertEqual(tomllib.loads(updated)['agents']['max_depth'], 2)
        self.assertEqual(ap.render_config(updated, 8), updated)

    def test_preserves_crlf_and_handles_no_final_newline(self):
        source = '# hello\r\nmodel = "chosen"\r\n[agents]\r\nmax_depth = 2\r\n'
        rendered = ap.render_config(source, 4)
        self.assertNotIn('\n', rendered.replace('\r\n', ''))
        self.assertEqual(ap.render_config(rendered, 4), rendered)
        self.assertEqual(ap.render_config('[agents]', 6).count('[agents]'), 1)

    def test_strings_and_arrays_cannot_impersonate_keys_tables_or_markers(self):
        source = ('prompt = """\n[agents]\nmax_threads = 100\n'
                  + ap.BEGIN + '\n' + ap.KEY + ' = 999\n' + ap.END
                  + '\n"""\ncommands = [\n "[agents]", "# marker"\n]\n')
        rendered = ap.render_config(source, 6)
        self.assertTrue(rendered.startswith(source))
        self.assertEqual(ap.render_config(rendered, 6), rendered)
        if tomllib is not None:
            self.assertEqual(tomllib.loads(rendered)['agents'][ap.KEY], 6)

    def test_unmanaged_concurrency_and_legacy_alias_are_rejected(self):
        for source in ('[agents]\nmax_threads = 6\n',
                       f'[agents]\n{ap.KEY} = 6\n',
                       'agents.max_threads = 6\n',
                       '["agents"]\n"max_threads" = 6\n',
                       '[agents.max_threads]\nlimit = 6\n',
                       '[agents]\nmax_threads.limit = 6\n',
                       'agents = {max_depth = 2}\n',
                       'agents.max_depth = 2\n'):
            with self.subTest(source=source), self.assertRaises(Blocked):
                ap.render_config(source, 6)

    def test_malformed_or_moved_managed_blocks_are_not_removed(self):
        sources = [ap.BEGIN + '\n', ap.END + '\n',
                   f'[agents]\n{ap.BEGIN}\n{ap.KEY} = 6\nmax_depth = 2\n{ap.END}\n',
                   f'[other]\n{ap.BEGIN}\n{ap.KEY} = 6\n{ap.END}\n',
                   f'[agents]\n{ap.BEGIN}\n{ap.KEY} = 6\n{ap.END}\n{ap.END}\n']
        for source in sources:
            with self.subTest(source=source), self.assertRaises(Blocked):
                ap.render_config(source, 6)

    def test_ambiguous_or_invalid_toml_fails_closed(self):
        for source in ('[agents]\n[agents]\n', 'message = "unterminated\n',
                       'value = [1, 2\n', '"ag\\u0065nts".max_threads = 2\n',
                       '[[agents]]\nmax_depth = 2\n'):
            with self.subTest(source=source), self.assertRaises(Blocked):
                ap.render_config(source, 6)

    def test_basic_rendering_does_not_require_tomllib(self):
        import builtins
        real_import = builtins.__import__

        def without_tomllib(name, *args, **kwargs):
            if name == 'tomllib':
                raise ImportError('Python 3.9 fixture')
            return real_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=without_tomllib):
            source = '# inheritance\n[agents]\nmax_depth = 2\n'
            rendered = ap.render_config(source, 6)
            self.assertEqual(ap.render_config(rendered, 6), rendered)
            with self.assertRaises(Blocked):
                ap.render_config('message = """unterminated', 6)


class PolicyFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.codex_home = self.base / "codex-home"
        self.codex_home.mkdir()
        (self.codex_home / "config.toml").write_text(f"[agents]\n{ap.KEY} = 2\n")
        self.environment = patch.dict(os.environ, {"CODEX_HOME": str(self.codex_home)})
        self.environment.start()
        self.root = self.base / 'hub'
        (self.root / '.codex').mkdir(parents=True)
        self.registry = {'schema_version': 1, 'repositories': [
            {'path': '.', 'management': 'native'},
            {'path': 'Child', 'management': 'native'},
            {'path': 'Missing', 'management': 'native'},
            {'path': 'External', 'management': 'external'}]}
        (self.root / '.codex/repositories.json').write_text(json.dumps(self.registry))
        self.data = {'schema_version': 1, 'defaults': {ap.KEY: 6}, 'repositories': {'.': {ap.KEY: 8}}}
        self.policy_path = self.root / '.codex/agent-policy.json'
        self.save_policy()
        (self.root / '.gitignore').write_text('Child/\nMissing/\nExternal/\n')
        for name in ('.', 'Child', 'External'):
            root = self.root / name
            (root / '.codex').mkdir(parents=True, exist_ok=True)
            (root / '.codex/profile.json').write_text('{"mode":"native"}\n')
            (root / ap.CONFIG).write_text('# User inheritance\n')
            remote = self.base / ('hub.git' if name == '.' else name + '.git')
            subprocess.run(['git', 'init', '--bare', '-q', str(remote)], check=True)
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(root)], check=True)
            for key, value in (('user.name', 'Test'), ('user.email', 'test@example.invalid'),
                               ('commit.gpgsign', 'false'), ('core.hooksPath', str(root / '.git/hooks'))):
                git(root, 'config', key, value)
            git(root, 'add', '--all')
            git(root, 'commit', '-m', 'Seed policy fixture')
            git(root, 'remote', 'add', 'origin', str(remote))
            git(root, 'push', '-u', 'origin', 'main')
        self.workspace = Workspace(self.root, 'policy-test')

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def save_policy(self):
        self.policy_path.write_text(json.dumps(self.data))

    def manager(self):
        return ap.AgentPolicy(self.root, 'policy-test')

    def plan(self, names):
        paths = [ap.CONFIG if name == '.' else name + '/' + ap.CONFIG for name in names]
        return self.workspace.plan({'requirements': ['Native profiles have the declared concurrency'], 'paths': paths})

    def test_show_is_read_only_and_lists_missing_clones(self):
        result = self.manager().inspect()
        self.assertEqual(result['skipped_missing'], ['Missing'])
        self.assertEqual([item['repository'] for item in result['repositories']], ['.', 'Child'])
        self.assertEqual([item[ap.KEY] for item in result['repositories']], [8, 6])
        self.assertFalse(result['matches'])
        self.assertFalse(result['primary_agent_included'])
        self.assertFalse((self.root / '.git/constellation').exists())

    def test_missing_local_configuration_inherits_global_without_writing(self):
        config = self.root / "Child" / ap.CONFIG
        config.unlink()
        global_config = self.codex_home / "config.toml"
        global_config.write_text(f"[agents]\n{ap.KEY} = 6\n")
        before = global_config.read_bytes()
        result = self.manager().inspect(["Child"])
        self.assertTrue(result["matches"])
        self.assertTrue(result["repositories"][0]["inherited"])
        self.assertFalse(config.exists())
        self.assertEqual(global_config.read_bytes(), before)
        self.assertFalse((self.root / ".git/constellation").exists())
        global_config.write_text(f"[agents]\n{ap.KEY} = 3\n")
        self.assertFalse(self.manager().inspect(["Child"])["matches"])

    def test_apply_requires_plan_and_explicit_scope(self):
        manager = self.manager()
        before = (self.root / ap.CONFIG).read_bytes()
        with self.assertRaisesRegex(Blocked, 'explicit --repo'):
            manager.apply([])
        with self.assertRaisesRegex(Blocked, 'No workspace contract'):
            manager.apply(['.'])
        self.plan(['Child'])
        with self.assertRaisesRegex(Blocked, 'outside the workspace plan'):
            manager.apply(['.'])
        self.assertEqual((self.root / ap.CONFIG).read_bytes(), before)

    def test_apply_preserves_bytes_mode_is_idempotent_and_updates_override(self):
        config = self.root / ap.CONFIG
        original = config.read_bytes()
        config.chmod(0o640)
        self.plan(['.', 'Child'])
        result = self.manager().apply(['.', 'Child'])
        self.assertEqual(result['applied'], ['.', 'Child'])
        self.assertTrue(config.read_bytes().startswith(original))
        self.assertEqual(config.stat().st_mode & 0o777, 0o640)
        self.assertTrue(self.manager().inspect()['matches'])
        self.assertEqual(self.manager().apply(['.', 'Child'])['applied'], [])
        self.data['repositories']['Child'] = {ap.KEY: 3}
        self.save_policy()
        self.assertFalse(self.manager().inspect(['Child'])['matches'])
        self.assertEqual(self.manager().apply(['Child'])['applied'], ['Child'])
        self.assertIn(f'{ap.KEY} = 3', (self.root / 'Child' / ap.CONFIG).read_text())

    def test_all_configs_are_preflighted_before_first_write(self):
        self.plan(['.', 'Child'])
        child = self.root / 'Child' / ap.CONFIG
        child.write_text('[agents]\nmax_threads = 3\n')
        before = (self.root / ap.CONFIG).read_bytes()
        with self.assertRaisesRegex(Blocked, 'Unmanaged'):
            self.manager().apply(['.', 'Child'])
        self.assertEqual((self.root / ap.CONFIG).read_bytes(), before)
        self.assertIn('max_threads', child.read_text())

    def test_config_path_itself_must_be_declared(self):
        self.workspace.plan({'requirements': ['Some other file'], 'paths': ['answer.md']})
        with self.assertRaisesRegex(Blocked, 'Undeclared patch path'):
            self.manager().apply(['.'])

    def test_unknown_external_absent_and_aliased_repositories_are_rejected(self):
        for name in ('Unknown', 'External', 'Missing', './Child', '../hub', 'Child/../Child'):
            with self.subTest(name=name), self.assertRaises(Blocked):
                self.manager().inspect([name])
        for name in ('Unknown', 'External', './Child'):
            self.data['repositories'][name] = {ap.KEY: 4}
            self.save_policy()
            with self.subTest(override=name), self.assertRaises(Blocked):
                self.manager()
            del self.data['repositories'][name]

    def test_invalid_policy_schema_and_values(self):
        originals = json.loads(json.dumps(self.data))
        cases = [None, {}, {**originals, 'schema_version': True},
                 {**originals, 'model': 'forbidden'}, {**originals, 'repositories': []}]
        for value in (0, -1, True, 6.0, '6', 2 ** 31):
            cases.append({**originals, 'defaults': {ap.KEY: value}})
        cases.append({**originals, 'defaults': {ap.KEY: 6, 'model': 'forbidden'}})
        for value in cases:
            self.policy_path.write_text(json.dumps(value))
            with self.subTest(policy=value), self.assertRaises(Blocked):
                self.manager()
        self.policy_path.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(Blocked, 'Duplicate'):
            self.manager()

    def test_symlink_policy_config_profile_and_repository_rejected(self):
        for path in (self.policy_path, self.root / ap.CONFIG, self.root / '.codex/profile.json'):
            saved = path.read_bytes()
            target = self.base / 'linked-data'
            target.write_bytes(saved)
            path.unlink()
            path.symlink_to(target)
            with self.subTest(path=path), self.assertRaises(Blocked):
                self.manager().inspect(['.'])
            path.unlink()
            path.write_bytes(saved)
        alias = self.root / 'Missing'
        alias.symlink_to(self.root / 'Child', target_is_directory=True)
        with self.assertRaisesRegex(Blocked, 'Symlink'):
            self.manager()

    def test_registry_does_not_substitute_for_a_git_boundary(self):
        (self.root / 'Missing/.codex').mkdir(parents=True)
        (self.root / 'Missing/.codex/profile.json').write_text('{"mode":"native"}')
        with self.assertRaisesRegex(Blocked, 'Git boundary'):
            self.manager().inspect(['Missing'])

    def test_cli_check_reports_drift_and_apply_has_no_implicit_selection(self):
        base = ['agent_policy.py', '--root', str(self.root), '--session', 'policy-test']
        with patch.object(sys, 'argv', base + ['check', '--repo', '.']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ap.main(), 1)
        with patch.object(sys, 'argv', base + ['apply']), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ap.main(), 2)
        self.plan(['.'])
        self.manager().apply(['.'])
        with patch.object(sys, 'argv', base + ['check', '--repo', '.']), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ap.main(), 0)


if __name__ == '__main__':
    unittest.main()
