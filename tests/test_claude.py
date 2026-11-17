"""Native Claude projection preserves client data and shares canonical roles."""

import json
from pathlib import Path
import stat
import subprocess
import tempfile
import tomllib
import unittest

from constellation import claude, install


class ClaudeSettingsTests(unittest.TestCase):
    def test_merge_preserves_preferences_and_unrelated_handlers_with_one_shared_pair(self):
        source = Path('/a source/Constellation')
        unrelated = {'type': 'command', 'command': 'echo constellation remains unrelated'}
        current = {
            'model': 'personal-model', 'effortLevel': 'max', 'autoMemoryEnabled': False,
            'permissions': {'defaultMode': 'default'}, 'enabledPlugins': {'other@provider': True},
            'hooks': {'PreToolUse': [{'matcher': 'Write', 'hooks': [unrelated, {
                'type': 'command', 'command': "python3 '/a source/Constellation/constellation.py' hook pre-tool"}]}]},
        }
        rendered = claude.settings_document(json.dumps(current), source, global_hooks=True)
        result = json.loads(rendered)
        for key in set(current) - {'hooks'}:
            self.assertEqual(result[key], current[key])
        self.assertEqual(result['hooks']['PreToolUse'][0], {'matcher': 'Write', 'hooks': [unrelated]})
        shared = result['hooks']['PreToolUse'][1]['hooks'][0]
        self.assertEqual(shared['args'], [str(source / 'constellation.py'), 'hook', 'pre-tool'])
        self.assertEqual(shared['onFailure'], 'block')
        self.assertNotIn('onFailure', result['hooks']['Stop'][0]['hooks'][0])
        self.assertEqual(claude.settings_document(rendered, source, global_hooks=True), rendered)
        project = json.loads(claude.settings_document(rendered, source, global_hooks=False))
        self.assertEqual(project['hooks'], {'PreToolUse': [{'matcher': 'Write', 'hooks': [unrelated]}]})

    def test_nonowned_commands_and_empty_hook_groups_are_not_rewritten(self):
        source = Path('/source')
        for command in ('python3 /other/constellation.py hook pre-tool',
                        'python3 /source/constellation.py hook pre-tool; echo custom'):
            document = json.dumps({'hooks': {'PreToolUse': [
                {'hooks': [{'type': 'command', 'command': command}]}, {'hooks': []}]}})
            self.assertEqual(claude.settings_document(document, source, global_hooks=False), document)
        self.assertEqual(claude.settings_document('{"hooks": {}}', source, global_hooks=False), '{"hooks": {}}')


class ClaudeInstallationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.source, self.home = self.base / 'source', self.base / 'home'
        self.state = self.home / '.local/state/constellation'
        (self.source / 'agents').mkdir(parents=True)
        (self.source / 'profiles').mkdir()
        (self.source / 'instructions').mkdir()
        (self.source / 'instructions/AGENTS.md').write_text('Shared contract.\n')
        (self.source / 'profiles/claude.md').write_text('Native Claude guide.\n')
        (self.home / '.claude').mkdir(parents=True)
        self.original_settings = json.dumps({'model': 'chosen', 'autoMemoryEnabled': False})
        (self.home / '.claude/settings.json').write_text(self.original_settings)
        (self.home / '.claude/settings.json').chmod(0o600)
        for number in range(8):
            (self.source / f'agents/role{number}.toml').write_text(
                f'name = "role{number}"\ndescription = "Role {number}"\n'
                'developer_instructions = "Keep the exact canonical contract."\n')
        self.project = self.base / 'project'
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True)
        self.projects = [{'id': 'project', 'root': str(self.project), 'management': 'native',
                          'profile': 'profiles/project.md'}]
        (self.source / 'profiles/project.md').write_text('Project-specific contract.\n')
        (self.source / 'profiles/projects.json').write_text(json.dumps({'projects': self.projects}))
        self.entries = []
        self.skill('core', 'coding')
        self.skill('project', 'domain', self.project)

    def skill(self, group, name, root=None):
        directory = self.source / 'skills' / group / name
        directory.mkdir(parents=True)
        (directory / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: A method\n---\n')
        self.entries.append({'group': group, 'name': name, 'destination': str(directory.relative_to(self.source)),
                             'project_root': str(root) if root else None, 'source': '/retired/' + name})

    def plan(self):
        (self.source / 'resource-inventory.json').write_text(json.dumps({'entries': self.entries}))
        return install.build_plan(self.source, self.home, self.state)

    def test_fresh_discovery_uses_canonical_roles_and_roundtrip_restores_settings(self):
        before = install.fingerprint(self.home)
        plan = self.plan()
        self.assertEqual(install.fingerprint(self.home), before)
        receipt = install.apply_plan(plan)
        self.assertEqual(plan['claude_conflicts'], [])
        for number in range(8):
            role = self.home / f'.claude/agents/role{number}.md'
            canonical = tomllib.loads((self.source / f'agents/role{number}.toml').read_text())
            self.assertTrue(role.is_symlink())
            self.assertEqual(role.read_text(), claude.agent_document(canonical))
            self.assertNotIn('model:', role.read_text())
        self.assertTrue((self.project / '.claude/skills/domain').is_symlink())
        self.assertFalse((self.project / '.claude/agents').exists())
        self.assertIn('@' + str(self.source / 'profiles/project.md'), (self.project / 'CLAUDE.md').read_text())
        self.assertEqual((self.home / '.claude/README.md').resolve(), self.source / 'profiles/claude.md')
        self.assertEqual(stat.S_IMODE((self.home / '.claude/settings.json').stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.state / 'native/claude/agents/role0.md').stat().st_mode), 0o600)
        self.assertEqual(self.plan()['operations'], [])
        install.rollback(receipt)
        self.assertEqual((self.home / '.claude/settings.json').read_text(), self.original_settings)
        self.assertFalse((self.project / '.claude/skills/domain').exists())

    def test_unknown_native_entries_remain_active_and_are_reported(self):
        agents = self.home / '.claude/agents'
        agents.mkdir()
        (agents / 'my-role.md').write_text('Unrelated role.')
        (agents / 'role0.md').write_text('Custom same-name role.')
        domain = self.project / '.claude/skills/domain'
        domain.mkdir(parents=True)
        (domain / 'SKILL.md').write_text('Unreviewed local domain skill.')
        plan = self.plan()
        self.assertEqual({row['path'] for row in plan['claude_conflicts']}, {str(agents / 'role0.md'), str(domain)})
        install.apply_plan(plan)
        self.assertEqual((agents / 'my-role.md').read_text(), 'Unrelated role.')
        self.assertEqual((agents / 'role0.md').read_text(), 'Custom same-name role.')
        self.assertEqual((domain / 'SKILL.md').read_text(), 'Unreviewed local domain skill.')

    def test_owned_project_duplicates_retire_but_domain_text_and_hooks_survive(self):
        agents = self.project / '.claude/agents'
        agents.mkdir(parents=True)
        (agents / 'role0.md').symlink_to(self.source / 'resources/native-claude-agents/role0.md')
        self.skill('project', 'coding', self.project)
        alias = self.project / '.claude/skills/coding'
        alias.parent.mkdir(parents=True)
        alias.symlink_to(self.source / 'skills/project/coding')
        instructions = 'Domain restrictions are binding.\n'
        (self.project / 'CLAUDE.md').write_text(instructions)
        owned = {'type': 'command', 'command': f'python3 {self.source}/constellation.py hook stop'}
        other = {'type': 'command', 'command': 'domain-check'}
        settings = self.project / '.claude/settings.json'
        settings.write_text(json.dumps({'hooks': {'Stop': [{'hooks': [owned, other]}]}}))
        receipt = install.apply_plan(self.plan())
        self.assertFalse((agents / 'role0.md').is_symlink())
        self.assertFalse(alias.is_symlink())
        self.assertTrue((self.project / 'CLAUDE.md').read_text().endswith(instructions))
        self.assertEqual(json.loads(settings.read_text())['hooks']['Stop'], [{'hooks': [other]}])
        install.rollback(receipt)
        self.assertTrue(alias.is_symlink())
        self.assertTrue((agents / 'role0.md').is_symlink())
        self.assertEqual((self.project / 'CLAUDE.md').read_text(), instructions)

    def test_documentation_tools_link_only_when_existing_bytes_match(self):
        source_tool = self.source / 'resources/automations/official_docs.py'
        source_tool.parent.mkdir(parents=True)
        source_tool.write_text('shared tool\n')
        for client, content in (('.claude', 'shared tool\n'), ('.codex', 'foreign implementation\n')):
            path = self.home / client / 'tools/official_docs.py'
            path.parent.mkdir(parents=True)
            path.write_text(content)
        plan = self.plan()
        self.assertEqual([row['path'] for row in plan['claude_conflicts']],
                         [str(self.home / '.codex/tools/official_docs.py')])
        install.apply_plan(plan)
        self.assertEqual((self.home / '.claude/tools/official_docs.py').resolve(), source_tool)
        self.assertEqual((self.home / '.codex/tools/official_docs.py').read_text(), 'foreign implementation\n')

    def test_uninventoried_core_shadow_and_linked_native_directory_stay_untouched(self):
        shadow = self.project / '.claude/skills/coding'
        shadow.mkdir(parents=True)
        (shadow / 'SKILL.md').write_text('Local wrapper not in the inventory.\n')
        external = self.base / 'external-agents'
        external.mkdir()
        (self.home / '.claude/agents').symlink_to(external, target_is_directory=True)
        plan = self.plan()
        conflicts = {row['path']: row['reason'] for row in plan['claude_conflicts']}
        self.assertIn(str(shadow), conflicts)
        self.assertIn('directory link', conflicts[str(self.home / '.claude/agents/role0.md')])
        install.apply_plan(plan)
        self.assertEqual(list(external.iterdir()), [])
        self.assertEqual((shadow / 'SKILL.md').read_text(), 'Local wrapper not in the inventory.\n')

    def project_fallbacks(self):
        legacy_role = self.source / 'resources/native-claude-agents/role0.md'
        legacy_role.parent.mkdir(parents=True)
        legacy_role.write_text('Existing shared role.\n')
        role = self.project / '.claude/agents/role0.md'
        role.parent.mkdir(parents=True)
        role.symlink_to(legacy_role)
        skill = self.project / '.claude/skills/coding'
        skill.parent.mkdir(parents=True)
        skill.symlink_to(self.source / 'skills/core/coding')
        return role, skill

    def assert_fallbacks_survive(self, role, skill):
        plan = self.plan()
        self.assertFalse(any(op['path'] in {str(role), str(skill)} for op in plan['operations']))
        conflicts = {row['path']: row['reason'] for row in plan['claude_conflicts']}
        self.assertIn('global entry conflicts', conflicts[str(role)])
        self.assertIn('global entry conflicts', conflicts[str(skill)])
        install.apply_plan(plan)
        self.assertEqual(role.read_text(), 'Existing shared role.\n')
        self.assertEqual(skill.resolve(), self.source / 'skills/core/coding')

    def test_project_fallbacks_survive_same_name_global_overrides(self):
        role, skill = self.project_fallbacks()
        global_role = self.home / '.claude/agents/role0.md'
        global_role.parent.mkdir()
        global_role.write_text('User role override.\n')
        global_skill = self.home / '.claude/skills/coding'
        global_skill.mkdir(parents=True)
        (global_skill / 'SKILL.md').write_text('User skill override.\n')
        self.assert_fallbacks_survive(role, skill)
        self.assertEqual(global_role.read_text(), 'User role override.\n')
        self.assertEqual((global_skill / 'SKILL.md').read_text(), 'User skill override.\n')

    def test_project_fallbacks_survive_linked_global_discovery_directories(self):
        role, skill = self.project_fallbacks()
        for name in ('agents', 'skills'):
            external = self.base / ('external-' + name)
            external.mkdir()
            (self.home / '.claude' / name).symlink_to(external, target_is_directory=True)
        self.assert_fallbacks_survive(role, skill)
        self.assertEqual(list((self.base / 'external-agents').iterdir()), [])
        self.assertEqual(list((self.base / 'external-skills').iterdir()), [])

    def test_inventory_does_not_install_into_external_or_unregistered_owner(self):
        for registered in (True, False):
            with self.subTest(registered=registered):
                self.projects[0]['management'] = 'external'
                (self.source / 'profiles/projects.json').write_text(json.dumps(
                    {'projects': self.projects if registered else []}))
                plan = self.plan()
                self.assertFalse(any(Path(op['path']).is_relative_to(self.project)
                                     for op in plan['operations']))
                self.assertIn('external or unregistered', next(
                    row['reason'] for row in plan['claude_conflicts']
                    if row['path'] == str(self.project / '.claude/skills/domain')))

    def test_all_project_fallbacks_survive_when_global_native_entries_are_linked(self):
        role, skill = self.project_fallbacks()
        for name in ('agents', 'skills'):
            external = self.base / ('external-' + name)
            external.mkdir()
            (self.home / '.claude' / name).symlink_to(external, target_is_directory=True)
        settings = self.home / '.claude/settings.json'
        personal = self.base / 'personal-settings.json'
        settings.rename(personal)
        settings.symlink_to(personal)
        project_settings = self.project / '.claude/settings.json'
        fallback = {'hooks': {
            'PreToolUse': [{'hooks': [{'type': 'command', 'command':
                f'python3 {self.source}/constellation.py hook pre-tool'}]}],
            'Stop': [{'hooks': [{'type': 'command', 'command':
                f'python3 {self.source}/constellation.py hook stop'}]}],
        }}
        project_settings.write_text(json.dumps(fallback))
        original = project_settings.read_bytes()
        plan = self.plan()
        self.assertFalse(any(op['path'] in {str(role), str(skill), str(project_settings)}
                             for op in plan['operations']))
        self.assertTrue(any(row['path'] == str(settings) for row in plan['claude_conflicts']))
        install.apply_plan(plan)
        self.assertEqual(project_settings.read_bytes(), original)
        self.assertEqual(personal.read_text(), self.original_settings)
        self.assertEqual(role.read_text(), 'Existing shared role.\n')
        self.assertEqual(skill.resolve(), self.source / 'skills/core/coding')

    def test_project_hook_fallback_survives_linked_global_settings_directory(self):
        external = self.base / 'external-claude'
        (self.home / '.claude').rename(external)
        (self.home / '.claude').symlink_to(external, target_is_directory=True)
        project_settings = self.project / '.claude/settings.local.json'
        project_settings.parent.mkdir()
        project_settings.write_text(json.dumps({'hooks': {'PreToolUse': [{'hooks': [
            {'type': 'command', 'command': f'python3 {self.source}/constellation.py hook pre-tool'}]}]}}))
        original = project_settings.read_bytes()
        plan = self.plan()
        self.assertFalse(any(op['path'] == str(project_settings) for op in plan['operations']))
        install.apply_plan(plan)
        self.assertEqual(project_settings.read_bytes(), original)
        self.assertEqual((external / 'settings.json').read_text(), self.original_settings)

    def test_disabled_global_hooks_preserve_preference_and_project_fallback(self):
        settings = self.home / '.claude/settings.json'
        settings.write_text('{"disableAllHooks": true}')
        project_settings = self.project / '.claude/settings.json'
        project_settings.parent.mkdir()
        project_settings.write_text(json.dumps({'hooks': {'Stop': [{'hooks': [
            {'type': 'command', 'command': f'python3 {self.source}/constellation.py hook stop'}]}]}}))
        original = project_settings.read_bytes()
        plan = self.plan()
        self.assertFalse(any(op['path'] == str(project_settings) for op in plan['operations']))
        self.assertTrue(any('disableAllHooks' in row['reason'] for row in plan['claude_conflicts']))
        install.apply_plan(plan)
        self.assertTrue(json.loads(settings.read_text())['disableAllHooks'])
        self.assertEqual(project_settings.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
