"""Publication behavior against actual local repositories and bare remotes."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from constellation import git
from constellation.state import StateError, Store, artifact_fingerprint, fingerprint, ready


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

    def approve(self, task_id='change'):
        self.store.check(task_id, 'default', [sys.executable, '-c', 'pass'])
        self.store.review(task_id, 'reviewer', 'Read the exact owned text and checked the expected change',
                          expected_fingerprint=fingerprint(self.store.get(task_id)))

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

    def test_publish_resumes_the_prepared_sha_after_commit_and_push_interruptions(self):
        self.approve()
        old = run(self.root, 'rev-parse', 'HEAD')
        original = git._run

        def before_ref_update(root, *args, **kwargs):
            if args[0] == 'update-ref':
                raise git.GitError('Synthetic interruption before ref update')
            return original(root, *args, **kwargs)

        with patch.object(git, '_run', side_effect=before_ref_update):
            with self.assertRaisesRegex(git.GitError, 'before ref update'):
                git.publish(self.store, 'change', 'Publish the reviewed change')
        intent = json.loads(git._journal_path(self.root, 'change').read_text())
        self.assertEqual(old, run(self.root, 'rev-parse', 'HEAD'))
        self.assertEqual({}, self.store.get('change')['publication'])

        def after_remote_acceptance(root, *args, **kwargs):
            self.assertNotEqual('commit-tree', args[0])
            result = original(root, *args, **kwargs)
            if args[0] == 'push':
                raise git.GitError('Synthetic interruption after remote acceptance')
            return result

        with patch.object(git, '_run', side_effect=after_remote_acceptance):
            with self.assertRaisesRegex(git.GitError, 'after remote acceptance'):
                git.publish(self.store, 'change')
        sha = intent['commit']
        self.assertEqual(sha, run(self.root, 'rev-parse', 'HEAD'))
        self.assertEqual(sha, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])

        def verify_only(root, *args, **kwargs):
            self.assertNotIn(args[0], ('commit-tree', 'push'))
            return original(root, *args, **kwargs)

        with patch.object(git, '_run', side_effect=verify_only):
            self.assertEqual(sha, git.publish(self.store, 'change'))
        self.assertEqual('closed', self.store.get('change')['status'])

    def test_competing_commit_waits_for_exact_verification_and_owned_follow_up(self):
        old = run(self.root, 'rev-parse', 'HEAD')
        self.approve()
        first = git.commit(self.store, 'change', 'Publish the first reviewed change')
        self.store.begin('peer', self.root, 'Update another path', {'foreign.txt': 'author'},
                         coordinator='coordinator')
        (self.root / 'foreign.txt').write_text('peer change\n')
        self.approve('peer')
        with self.assertRaisesRegex(git.GitError, 'publish change$'):
            git.publish(self.store, 'peer', 'Publish the peer change')
        self.assertEqual(first, run(self.root, 'rev-parse', 'HEAD'))
        self.assertEqual(old, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])

        (self.root / 'owned.txt').write_text('owned follow-up\n')
        with self.assertRaisesRegex(git.GitError, 'local changes remain'):
            git.push(self.store, 'change')
        self.assertEqual(first, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])
        with self.assertRaisesRegex(git.GitError, 'publish change$'):
            git.commit(self.store, 'peer', 'Publish the peer change')

        self.approve()
        follow_up = git.publish(self.store, 'change', 'Publish the reviewed follow-up')
        self.assertEqual(follow_up, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])
        self.approve('peer')
        peer = git.publish(self.store, 'peer', 'Publish the peer change')
        self.assertEqual(peer, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])
        self.assertEqual(follow_up, run(self.root, 'rev-parse', 'HEAD^'))

    def test_prepared_peer_intent_reserves_the_same_remote_ref_across_checkouts(self):
        self.approve()
        original = git._run

        def before_ref_update(root, *args, **kwargs):
            if args[0] == 'update-ref':
                raise git.GitError('Synthetic interruption before ref update')
            return original(root, *args, **kwargs)

        with patch.object(git, '_run', side_effect=before_ref_update):
            with self.assertRaisesRegex(git.GitError, 'before ref update'):
                git.commit(self.store, 'change', 'Prepare the reviewed change')
        self.assertEqual({}, self.store.get('change')['publication'])
        checkout = self.base / 'other-checkout'
        run(self.base, 'clone', '--branch', 'main', str(self.remote), str(checkout))
        run(checkout, 'switch', '-c', 'other')
        run(checkout, 'config', 'user.name', 'Test')
        run(checkout, 'config', 'user.email', 'test@example.invalid')
        run(checkout, 'remote', 'add', 'same-destination', str(self.remote))
        self.store.begin('peer', checkout, 'Update another path', {'foreign.txt': 'author'},
                         coordinator='coordinator', remote='same-destination', ref='refs/heads/main')
        (checkout / 'foreign.txt').write_text('peer change\n')
        self.approve('peer')
        with self.assertRaisesRegex(git.GitError, 'publish change$'):
            git.commit(self.store, 'peer', 'Publish the peer change')
        self.assertEqual({}, self.store.get('peer')['publication'])

        self.store.begin('independent', checkout, 'Update a different ref', {'owned.txt': 'author'},
                         coordinator='coordinator', ref='refs/heads/other')
        (checkout / 'owned.txt').write_text('independent change\n')
        self.approve('independent')
        sha = git.commit(self.store, 'independent', 'Commit to an unrelated ref')
        self.assertEqual(sha, run(checkout, 'rev-parse', 'HEAD'))

    def test_simultaneous_publish_refreshes_once_to_the_durable_commit(self):
        original = git.commit
        for task_id, verified in (('change', False), ('another', True)):
            with self.subTest(verified=verified):
                if verified:
                    self.store.begin(task_id, self.root, 'Change the owned path again',
                                     {'owned.txt': 'author'}, coordinator='coordinator')
                    (self.root / 'owned.txt').write_text('another change\n')
                old = run(self.root, 'rev-parse', 'HEAD')
                self.approve(task_id)
                created = []

                def overlapping_commit(store, task_id, message):
                    sha = original(store, task_id, message)
                    created.append(sha)
                    if verified:
                        git.push(store, task_id)
                    return original(store, task_id, message)

                with (patch.object(git, 'commit', side_effect=overlapping_commit),
                      patch.object(self.store, 'get', wraps=self.store.get) as reads):
                    sha = git.publish(self.store, task_id, 'Publish the reviewed change')
                    self.assertEqual(2, reads.call_count)
                self.assertEqual([sha], created)
                self.assertEqual(sha, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])
                self.assertEqual(old, run(self.root, 'rev-parse', 'HEAD^'))
                self.assertEqual('closed', self.store.get(task_id)['status'])

    def test_publication_retry_leaves_later_work_in_its_own_task(self):
        self.approve()
        sha = git.commit(self.store, 'change', 'Publish the first reviewed change')
        before_close = self.store.get('change')
        self.assertEqual(sha, git.push(self.store, 'change'))
        completed = self.store.get('change')

        self.store.begin('later', self.root, 'Change the same path in a new task',
                         {'owned.txt': 'later-author'}, coordinator='coordinator')
        (self.root / 'owned.txt').write_text('later work\n')
        with patch.object(git, '_run', side_effect=AssertionError('Closed tasks need no Git query')):
            self.assertEqual(sha, git.push(self.store, 'change'))
            self.assertEqual(completed['publication'], git.recover(self.store, 'change'))
            # Model a publisher that read before another caller closed the task.
            with patch.object(self.store, 'get', return_value=before_close):
                self.assertEqual(sha, git.publish(self.store, 'change'))
        self.assertEqual(completed, self.store.get('change'))
        self.assertEqual(['later'], [task['id'] for task in self.store.active(self.root)])
        self.assertEqual('later work\n', (self.root / 'owned.txt').read_text())

        before_cancel = self.store.get('later')
        self.store.cancel('later', 'Leave the synthetic work locally')
        with patch.object(git, '_run', side_effect=AssertionError('Closed tasks need no Git query')):
            for operation in (git.publish, git.push, git.recover):
                with self.assertRaisesRegex(git.GitError, 'no verified publication'):
                    operation(self.store, 'later')
        # Even valid evidence cannot override cancellation observed under lock.
        cancelled = self.store.get('later')
        cancelled['checks']['default'] = {
            'status': 'passed', 'returncode': 0, 'fingerprint': artifact_fingerprint(cancelled)}
        current = fingerprint(cancelled)
        cancelled['reviews'].append({
            'reviewer': 'reviewer', 'verdict': 'approve', 'fingerprint': current})
        self.assertEqual(current, ready(cancelled))
        with (patch.object(self.store, 'get', return_value=before_cancel),
              patch.object(self.store, '_read', return_value=cancelled)):
            with self.assertRaisesRegex(git.GitError, 'requires an open publication task'):
                git.publish(self.store, 'later', 'Update the reviewed path')
        self.assertEqual('closed', self.store.get('later')['status'])
        self.assertEqual(sha, run(self.root, 'rev-parse', 'HEAD'))

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

    def test_recover_keeps_head_and_index_if_prepared_index_is_unavailable(self):
        self.approve()
        old_head = run(self.root, 'rev-parse', 'HEAD')
        index = git._git_dir(self.root) / 'index'
        old_index = index.read_bytes()
        original = git._run

        def before_ref_update(root, *args, **kwargs):
            if args[0] == 'update-ref':
                raise git.GitError('Synthetic interruption before ref update')
            return original(root, *args, **kwargs)

        with patch.object(git, '_run', side_effect=before_ref_update):
            with self.assertRaisesRegex(git.GitError, 'before ref update'):
                git.commit(self.store, 'change', 'Prepare the reviewed change')
        journal = git._journal_path(self.root, 'change')
        intent = json.loads(journal.read_text())
        prepared = journal.with_suffix('.index')
        expected = prepared.read_bytes()
        prepared.unlink()

        for damaged in (False, True):
            with self.subTest(damaged=damaged):
                if damaged:
                    prepared.write_bytes(b'synthetic corruption')
                with self.assertRaisesRegex(git.GitError, 'Prepared recovery index is unavailable'):
                    git.recover(self.store, 'change')
                self.assertEqual(old_head, run(self.root, 'rev-parse', 'HEAD'))
                self.assertEqual(old_index, index.read_bytes())
                self.assertEqual(intent, json.loads(journal.read_text()))

        prepared.write_bytes(expected)
        self.assertEqual(intent['commit'], git.recover(self.store, 'change')['commit'])

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
        # Simulate a prior delivery whose verified receipt has not been recorded.
        run(self.root, 'push', 'origin', 'main')
        (self.root / 'owned.txt').write_text('work added after the first commit\n')
        with self.assertRaisesRegex(git.GitError, 'local changes remain'):
            git.push(self.store, 'change')
        self.assertEqual(first, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])
        pending = self.store.get('change')
        self.assertEqual('open', pending['status'])
        self.assertEqual('verified_local_changes', pending['publication']['status'])
        journal = git._journal_path(self.root, 'change')
        self.assertEqual('verified', json.loads(journal.read_text())['phase'])
        self.assertEqual('block', stop({'cwd': str(self.root), 'session_id': 'coordinator',
                                       'agent_id': 'author'}, self.store)['decision'])
        with self.assertRaisesRegex(git.GitError, 'local changes remain'):
            git.recover(self.store, 'change')
        self.assertEqual('work added after the first commit\n', (self.root / 'owned.txt').read_text())
        self.approve()
        original = git._run

        def before_follow_up_ref_update(root, *args, **kwargs):
            if args[0] == 'update-ref':
                raise git.GitError('Synthetic interruption before follow-up ref update')
            return original(root, *args, **kwargs)

        with patch.object(git, '_run', side_effect=before_follow_up_ref_update):
            with self.assertRaisesRegex(git.GitError, 'before follow-up ref update'):
                git.publish(self.store, 'change', 'Review the remaining local change')
        second = json.loads(journal.read_text())['commit']
        self.assertNotEqual(first, second)
        self.assertEqual(first, run(self.root, 'rev-parse', 'HEAD'))
        self.assertEqual(second, git.publish(self.store, 'change'))
        self.assertEqual('closed', self.store.get('change')['status'])
        self.assertEqual(first, self.store.get('change')['publications'][0]['commit'])
        self.assertEqual(first_evidence, self.store.get('change')['publications'][0]['evidence_snapshot']['checks'])
        self.assertEqual(foreign, run(self.root, 'ls-files', '--stage', '-v', 'foreign.txt'))
        self.assertEqual(second, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])

    def test_restoring_published_bytes_closes_with_original_evidence(self):
        owned = self.root / 'owned.txt'
        for task_id, restore_before_checks in (('change', True), ('another', False)):
            with self.subTest(restore_before_checks=restore_before_checks):
                if not restore_before_checks:
                    self.store.begin(task_id, self.root, 'Change the owned path again',
                                     {'owned.txt': 'author'}, coordinator='coordinator')
                    owned.write_text('another published change\n')
                self.approve(task_id)
                published = owned.read_bytes()
                sha = git.commit(self.store, task_id, 'Publish the reviewed bytes')

                owned.write_text('post-commit local work\n')
                with self.assertRaisesRegex(git.GitError, 'local changes remain'):
                    git.push(self.store, task_id)
                frozen = self.store.get(task_id)['publication']
                self.assertEqual('verified_local_changes', frozen['status'])
                if restore_before_checks:
                    owned.write_bytes(published)
                self.approve(task_id)
                if not restore_before_checks:
                    run(self.root, 'add', 'owned.txt')
                    owned.write_bytes(published)
                    with self.assertRaisesRegex(git.GitError, 'local changes remain'):
                        git.recover(self.store, task_id)
                    self.assertEqual('post-commit local work', run(self.root, 'show', ':owned.txt'))
                    self.assertEqual(published, owned.read_bytes())
                    run(self.root, 'restore', '--staged', '--', 'owned.txt')

                audit = self.store.get(task_id)
                self.assertNotEqual(frozen['evidence_snapshot']['checks'], audit['checks'])
                if restore_before_checks:
                    parent = run(self.root, 'rev-parse', 'HEAD^')
                    run(self.remote, 'update-ref', 'refs/heads/main', parent, sha)
                    with self.assertRaisesRegex(git.GitError, 'no longer at the frozen destination'):
                        git.publish(self.store, task_id)
                    self.assertEqual('open', self.store.get(task_id)['status'])
                    run(self.remote, 'update-ref', 'refs/heads/main', sha, parent)
                    self.assertEqual(sha, git.publish(self.store, task_id))
                else:
                    self.assertEqual(sha, git.recover(self.store, task_id)['commit'])

                closed = self.store.get(task_id)
                self.assertEqual('closed', closed['status'])
                self.assertEqual({**frozen, 'status': 'verified'}, closed['publication'])
                self.assertEqual(audit['checks'], closed['checks'])
                self.assertEqual(audit['reviews'], closed['reviews'])
                self.assertEqual(sha, run(self.root, 'rev-parse', 'HEAD'))
                self.assertEqual(sha, run(self.root, 'ls-remote', 'origin', 'refs/heads/main').split()[0])
                self.assertEqual(published, owned.read_bytes())
                self.assertEqual(sha, git.push(self.store, task_id))

    def test_legacy_verified_local_receipt_requires_current_evidence_to_reconcile(self):
        self.approve()
        sha = git.commit(self.store, 'change', 'Publish the reviewed bytes')
        run(self.root, 'push', 'origin', 'main')
        owned = self.root / 'owned.txt'
        published = owned.read_bytes()
        owned.write_text('post-commit local work\n')
        with self.store.locked('change') as task:
            task['publication']['status'] = 'verified_local_changes'
            task['checks']['default']['returncode'] = 9
        journal = git._journal_path(self.root, 'change')
        self.assertEqual('committed', json.loads(journal.read_text())['phase'])

        with self.assertRaisesRegex(git.GitError, 'Evidence changed'):
            git.recover(self.store, 'change')
        self.assertEqual('committed', json.loads(journal.read_text())['phase'])
        with self.store.locked('change') as task:
            task['checks']['default']['returncode'] = 0
        with self.assertRaisesRegex(git.GitError, 'local changes remain'):
            git.recover(self.store, 'change')
        self.assertEqual('verified', json.loads(journal.read_text())['phase'])
        owned.write_bytes(published)
        self.assertEqual(sha, git.publish(self.store, 'change'))
        self.assertEqual('closed', self.store.get('change')['status'])

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
        (self.root / 'owned.txt').write_text('post-commit local work\n')
        with self.assertRaisesRegex(git.GitError, 'Evidence changed'):
            git.recover(self.store, 'change')
        pending = self.store.get('change')
        self.assertEqual('open', pending['status'])
        self.assertEqual('push_pending', pending['publication']['status'])
        intent = json.loads(git._journal_path(self.root, 'change').read_text())
        self.assertEqual('push_pending', intent['phase'])


if __name__ == '__main__':
    unittest.main()
