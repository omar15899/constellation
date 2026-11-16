"""Publication behavior against actual local repositories and bare remotes."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from constellation import git
from constellation.state import StateError, Store, fingerprint


def run(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE).decode().strip()


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'work'
        self.remote = self.base / 'remote.git'
        self.root.mkdir()
        run(self.root, 'init', '-b', 'main')
        run(self.root, 'config', 'user.email', 'test@example.invalid')
        run(self.root, 'config', 'user.name', 'Test')
        (self.root / 'owned.txt').write_text('base\n')
        (self.root / 'foreign.txt').write_text('foreign base\n')
        run(self.root, 'add', 'owned.txt', 'foreign.txt')
        run(self.root, 'commit', '-m', 'Initial fixture')
        run(self.root, 'init', '--bare', str(self.remote))
        run(self.root, 'remote', 'add', 'origin', str(self.remote))
        run(self.root, 'push', '-u', 'origin', 'main')
        self.store = Store(self.base / 'state')
        self.store.begin('change', self.root, 'Change owned text', {'owned.txt': 'author'}, coordinator='coordinator')
        (self.root / 'owned.txt').write_text('review me\n')

    def approve(self):
        self.store.check('change', 'default', [sys.executable, '-c', 'pass'])
        self.store.review('change', 'reviewer', 'Read the exact owned text and checked the expected change',
                          expected_fingerprint=fingerprint(self.store.get('change')))

    def test_foreign_staging_and_index_flags_survive_exact_commit_and_push(self):
        (self.root / 'foreign.txt').write_text('foreign staged\n')
        run(self.root, 'add', 'foreign.txt')
        run(self.root, 'update-index', '--assume-unchanged', 'foreign.txt')
        before = run(self.root, 'ls-files', '--stage', '-v', 'foreign.txt')
        self.approve()
        sha = git.commit(self.store, 'change', 'Update owned text')
        self.assertEqual(before, run(self.root, 'ls-files', '--stage', '-v', 'foreign.txt'))
        self.assertEqual('foreign base', run(self.root, 'show', 'HEAD:foreign.txt'))
        self.assertEqual('owned.txt', run(self.root, 'diff-tree', '--no-commit-id', '--name-only', '-r', sha))
        self.assertEqual(sha, git.push(self.store, 'change'))
        self.assertEqual(sha, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])

    def test_edit_after_review_and_staged_scope_are_rejected(self):
        self.approve()
        (self.root / 'owned.txt').write_text('changed after review\n')
        with self.assertRaises(StateError):
            git.commit(self.store, 'change', 'Cannot publish stale review')
        run(self.root, 'add', 'owned.txt')
        with self.assertRaisesRegex(git.GitError, 'staged'):
            git.candidate(self.root, ['owned.txt'], self.store.get('change')['target'])

    def test_private_path_in_earlier_outgoing_commit_blocks_even_when_deleted(self):
        old = run(self.root, 'rev-parse', 'HEAD')
        (self.root / 'Private').mkdir()
        (self.root / 'Private' / 'fixture.txt').write_text('synthetic private fixture\n')
        run(self.root, 'add', 'Private/fixture.txt')
        run(self.root, 'commit', '-m', 'Synthetic outgoing private fixture')
        run(self.root, 'rm', 'Private/fixture.txt')
        run(self.root, 'commit', '-m', 'Remove synthetic fixture')
        with self.assertRaisesRegex(git.GitError, 'private'):
            git.check_outgoing(self.root, run(self.root, 'rev-parse', 'HEAD'), old)
        self.assertEqual(old, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])

    def test_push_accepted_then_interrupted_is_recovered_without_another_commit(self):
        self.approve()
        sha = git.commit(self.store, 'change', 'Update owned text')
        original = git._run

        def interrupted(root, *args, **kwargs):
            result = original(root, *args, **kwargs)
            if args[0] == 'push':
                raise git.GitError('Synthetic lost response after remote accepted')
            return result

        with patch.object(git, '_run', side_effect=interrupted):
            with self.assertRaises(git.GitError):
                git.push(self.store, 'change')
        self.assertEqual('push_pending', self.store.get('change')['publication']['status'])
        frozen = self.store.get('change')['publication']
        result = git.recover(self.store, 'change')
        self.assertEqual({key: value for key, value in frozen.items() if key != 'remote_before'} | {'status': 'verified'}, result)
        self.assertEqual(sha, run(self.root, 'rev-parse', 'HEAD'))
        self.assertEqual(sha, git.push(self.store, 'change'))

    def test_wrong_remote_branch_and_unreviewed_outgoing_commits_are_rejected(self):
        self.approve()
        sha = git.commit(self.store, 'change', 'Update owned text')
        old = run(self.root, 'rev-parse', 'HEAD^')
        with self.assertRaisesRegex(git.GitError, 'destination'):
            git.pre_push(self.root, 'origin', str(self.remote),
                         f'refs/heads/main {sha} refs/heads/other {old}', self.store)
        (self.root / 'other.txt').write_text('unreviewed\n')
        run(self.root, 'add', 'other.txt')
        run(self.root, 'commit', '-m', 'Unreviewed fixture')
        with self.assertRaisesRegex(git.GitError, 'unreviewed'):
            git.pre_push(self.root, 'origin', str(self.remote),
                         f"refs/heads/main {run(self.root, 'rev-parse', 'HEAD')} refs/heads/main {old}", self.store)

    def test_commit_interruption_preserves_and_recovers_foreign_index(self):
        (self.root / 'foreign.txt').write_text('foreign staged\n')
        run(self.root, 'add', 'foreign.txt')
        before = run(self.root, 'ls-files', '--stage', 'foreign.txt')
        self.approve()
        original = git._run

        def interrupted(root, *args, **kwargs):
            result = original(root, *args, **kwargs)
            if args[0] == 'update-ref':
                raise git.GitError('Synthetic interruption after updating ref')
            return result

        with patch.object(git, '_run', side_effect=interrupted):
            with self.assertRaises(git.GitError):
                git.commit(self.store, 'change', 'Update owned text')
        result = git.recover(self.store, 'change')
        self.assertEqual('committed', result['status'])
        self.assertEqual(before, run(self.root, 'ls-files', '--stage', 'foreign.txt'))
        self.assertEqual('foreign.txt', run(self.root, 'diff', '--cached', '--name-only'))

    def test_replace_refs_cannot_hide_private_objects_actually_pushed(self):
        old = run(self.root, 'rev-parse', 'HEAD')
        (self.root / 'Private').mkdir()
        (self.root / 'Private' / 'fixture').write_text('synthetic\n')
        run(self.root, 'add', 'Private/fixture')
        run(self.root, 'commit', '-m', 'Synthetic private commit')
        bad = run(self.root, 'rev-parse', 'HEAD')
        safe = run(self.root, 'commit-tree', run(self.root, 'rev-parse', old + '^{tree}'), '-p', old, '-m', 'Replacement')
        run(self.root, 'replace', bad, safe)
        self.assertNotIn('Private/fixture', run(self.root, 'ls-tree', '-r', '--name-only', bad))
        with self.assertRaisesRegex(git.GitError, 'private'):
            git.check_outgoing(self.root, bad, old)

    def test_existing_project_guard_is_executed_against_candidate_index(self):
        guard = self.base / 'pre-commit'
        guard.write_text('#!/bin/sh\ngit diff --cached --name-only > guard-observed\nexit 1\n')
        guard.chmod(0o700)
        with self.store.locked('change') as task:
            task['policy']['pre_commit_hooks'] = [str(guard)]
        self.approve()
        old = run(self.root, 'rev-parse', 'HEAD')
        with self.assertRaisesRegex(git.GitError, 'guard rejected'):
            git.commit(self.store, 'change', 'Blocked by project guard')
        self.assertEqual('owned.txt\n', (self.root / 'guard-observed').read_text())
        self.assertEqual(old, run(self.root, 'rev-parse', 'HEAD'))

    def test_interruption_before_ref_update_recovers_the_same_prepared_commit(self):
        self.approve()
        original = git._run
        old = run(self.root, 'rev-parse', 'HEAD')

        def interrupted(root, *args, **kwargs):
            if args[0] == 'update-ref':
                raise git.GitError('Synthetic interruption before ref update')
            return original(root, *args, **kwargs)

        with patch.object(git, '_run', side_effect=interrupted):
            with self.assertRaises(git.GitError):
                git.commit(self.store, 'change', 'Update owned text')
        self.assertEqual(old, run(self.root, 'rev-parse', 'HEAD'))
        intent = json.loads(git._journal_path(self.root, 'change').read_text())
        recovered = git.recover(self.store, 'change')
        self.assertEqual(intent['commit'], recovered['commit'])
        self.assertEqual(intent['commit'], run(self.root, 'rev-parse', 'HEAD'))

    def test_actual_git_pre_push_hook_accepts_reviewed_sha_and_blocks_unreviewed_tip(self):
        source = Path(git.__file__).resolve().parents[1]
        hook = self.root / '.git/hooks/pre-push'
        hook.write_text(f'#!{sys.executable}\nimport sys\nsys.path.insert(0, {str(source)!r})\n'
                        'from constellation.git import pre_push\nfrom constellation.state import Store\n'
                        f'pre_push({str(self.root)!r}, sys.argv[1], sys.argv[2], sys.stdin.read(), '
                        f'Store({str(self.store.root)!r}))\n')
        hook.chmod(0o700)
        self.approve()
        sha = git.commit(self.store, 'change', 'Update owned text')
        run(self.root, 'tag', '-a', 'unplanned-tag', '-m', 'Synthetic annotated tag')
        run(self.root, 'config', 'push.followTags', 'true')
        self.assertEqual(sha, git.push(self.store, 'change'))
        self.assertEqual('', run(self.root, 'ls-remote', '--tags', 'origin'))
        (self.root / 'other.txt').write_text('unreviewed\n')
        run(self.root, 'add', 'other.txt')
        run(self.root, 'commit', '-m', 'Unreviewed fixture')
        rejected = subprocess.run(['git', '-C', str(self.root), 'push', 'origin', 'main'],
                                  capture_output=True, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertEqual(sha, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])

    def test_private_owner_patterns_reject_case_aliases(self):
        self.assertTrue(git.private_path('09_data_sources/Codex_Conversations/item',
                                         {'private_patterns': ['09_Data_Sources/*_Conversations/**']}))
        self.assertTrue(git.private_path('system/SYNC/state.json',
                                         {'private_prefixes': ['System/Sync']}))

    def test_private_runtime_files_in_outgoing_history_are_blocked(self):
        old = run(self.root, 'rev-parse', 'HEAD')
        paths = ['02_Tasks_and_Execution/Ledger/.sync_state/codex_conversations.json',
                 'docs/codex_conversations_sync_daemon.log',
                 '.claude/cache/turn_states/example.json', '.env.production',
                 'credentials.json', '.netrc', 'archived_sessions/fixture',
                 'id_ed25519', 'rollout-synthetic.jsonl']
        for name in paths:
            with self.subTest(path=name):
                # Make a separate outgoing child for each variant, so one
                # correctly detected filename cannot hide a missed variant.
                with git._temporary_index(self.root) as index:
                    git._run(self.root, 'read-tree', old, index=index)
                    item = self.root / name
                    item.parent.mkdir(parents=True, exist_ok=True)
                    item.write_text('synthetic privacy fixture\n')
                    git._run(self.root, 'add', '--', name, index=index)
                    tree = git._text(self.root, 'write-tree', index=index)
                    sha = git._text(self.root, 'commit-tree', tree, '-p', old, '-m', 'Synthetic privacy fixture')
                with self.assertRaisesRegex(git.GitError, 'private'):
                    git.check_outgoing(self.root, sha, old)
                item.unlink()
        self.assertFalse(git.private_path('scripts/codex_conversations_sync_daemon.py'))

    def test_credential_bearing_http_remote_is_rejected_before_task_records_it(self):
        run(self.root, 'remote', 'set-url', 'origin', 'https://synthetic-user:synthetic-password@example.invalid/repo.git')
        with self.assertRaisesRegex(git.GitError, 'credential helper'):
            git.target(self.root)
        run(self.root, 'remote', 'set-url', 'origin', 'git@example.invalid:owner/repo.git')
        self.assertEqual('git@example.invalid:owner/repo.git', git.target(self.root)['url'])

    def test_follow_tags_configuration_cannot_publish_an_unplanned_ref_without_hooks(self):
        self.approve()
        sha = git.commit(self.store, 'change', 'Update owned text')
        run(self.root, 'tag', '-a', 'unplanned-tag', '-m', 'Synthetic annotated tag')
        run(self.root, 'config', 'push.followTags', 'true')
        self.assertEqual(sha, git.push(self.store, 'change'))
        self.assertEqual('', run(self.root, 'ls-remote', '--tags', 'origin'))

    def test_postcommit_local_work_stays_open_and_continues_with_fresh_review(self):
        from constellation.hooks import stop
        (self.root / 'foreign.txt').write_text('foreign staging remains\n')
        run(self.root, 'add', 'foreign.txt')
        foreign = run(self.root, 'ls-files', '--stage', '-v', 'foreign.txt')
        self.approve()
        first_evidence = self.store.get('change')['checks']
        first = git.commit(self.store, 'change', 'First reviewed change')
        (self.root / 'owned.txt').write_text('work added after the first commit\n')
        with self.assertRaisesRegex(git.GitError, 'local changes remain'):
            git.push(self.store, 'change')
        self.assertEqual(first, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])
        pending = self.store.get('change')
        self.assertEqual('open', pending['status'])
        self.assertEqual('verified_local_changes', pending['publication']['status'])
        self.assertEqual('block', stop({'cwd': str(self.root), 'session_id': 'coordinator',
                                       'agent_id': 'author'}, self.store)['decision'])
        with self.assertRaisesRegex(git.GitError, 'local changes remain'):
            git.recover(self.store, 'change')
        self.assertEqual('work added after the first commit\n', (self.root / 'owned.txt').read_text())
        self.approve()
        second = git.commit(self.store, 'change', 'Review the remaining local change')
        self.assertNotEqual(first, second)
        self.assertEqual(second, git.push(self.store, 'change'))
        self.assertEqual('closed', self.store.get('change')['status'])
        self.assertEqual(first, self.store.get('change')['publications'][0]['commit'])
        self.assertEqual(first_evidence, self.store.get('change')['publications'][0]['evidence_snapshot']['checks'])
        self.assertEqual(foreign, run(self.root, 'ls-files', '--stage', '-v', 'foreign.txt'))
        self.assertEqual(second, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])

    def test_postcommit_checks_are_frozen_and_changed_evidence_cannot_publish(self):
        self.approve()
        old_remote = run(self.root, 'rev-parse', 'HEAD')
        git.commit(self.store, 'change', 'Update owned text')
        checks = self.store.get('change')['checks']
        with self.assertRaises(StateError):
            self.store.check('change', 'default', [sys.executable, '-c', 'raise SystemExit(9)'])
        self.assertEqual(checks, self.store.get('change')['checks'])
        with self.store.locked('change') as task:
            task['checks']['default']['returncode'] = 9
        with self.assertRaisesRegex(git.GitError, 'Evidence changed'):
            git.push(self.store, 'change')
        self.assertEqual(old_remote, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])

    def test_recover_does_not_close_remote_delivery_when_evidence_changed(self):
        self.approve()
        git.commit(self.store, 'change', 'Update owned text')
        original = git._run

        def interrupted(root, *args, **kwargs):
            result = original(root, *args, **kwargs)
            if args[0] == 'push':
                raise git.GitError('Synthetic lost response')
            return result

        with patch.object(git, '_run', side_effect=interrupted):
            with self.assertRaises(git.GitError):
                git.push(self.store, 'change')
        with self.store.locked('change') as task:
            task['checks']['default']['returncode'] = 9
        with self.assertRaisesRegex(git.GitError, 'Evidence changed'):
            git.recover(self.store, 'change')
        self.assertEqual('open', self.store.get('change')['status'])


if __name__ == '__main__':
    unittest.main()
