"""Exact-content publication with isolated indexes and recoverable Git intents.

The commit command uses Git plumbing after the same gate exposed to hooks. It
does not run arbitrary repository hooks: the central gate is the publication
authority. Native pre-commit/pre-push hooks protect ordinary porcelain use.
Local records and reviewer names are accountable declarations, not a security
boundary against a user who can rewrite the repository or these records.
"""

from __future__ import annotations

import contextlib
import copy
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile
from typing import Any, Iterator
from urllib.parse import urlsplit


class GitError(RuntimeError):
    """A publication invariant or Git operation failed."""


def _run(root: str | Path, *args: str, data: bytes | None = None,
         index: str | Path | None = None, timeout: int = 60) -> bytes:
    """Run Git with no inherited repository redirection and bounded execution."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env['GIT_LITERAL_PATHSPECS'] = '1'
    env['GIT_NO_REPLACE_OBJECTS'] = '1'
    env['GIT_TERMINAL_PROMPT'] = '0'
    if index is not None:
        env['GIT_INDEX_FILE'] = str(index)
    try:
        result = subprocess.run(['git', '--no-replace-objects', '-C', str(root), *args], input=data,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitError('Git operation failed or timed out; inspect local intent') from exc
    if result.returncode:
        # Do not persist or echo repository data, URLs, or credential helpers.
        raise GitError(f'Git {args[0]} failed (exit {result.returncode})')
    return result.stdout


def _text(root: str | Path, *args: str, **kwargs: Any) -> str:
    return _run(root, *args, **kwargs).decode('utf-8', 'surrogateescape').strip()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True).encode()).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else 'missing'


def _git_dir(root: str | Path) -> Path:
    return Path(_text(root, 'rev-parse', '--absolute-git-dir'))


def target(root: str | Path, remote: str = 'origin', branch: str | None = None,
           ref: str | None = None) -> dict[str, str]:
    """Freeze the current branch, one push URL and exact destination ref."""
    current = _text(root, 'symbolic-ref', '--short', 'HEAD')
    branch = branch or current
    if branch != current:
        raise GitError('Task branch must be the checked-out branch')
    urls = _text(root, 'remote', 'get-url', '--push', '--all', remote).splitlines()
    if len(urls) != 1:
        raise GitError('Publication requires exactly one push URL')
    parsed_url = urlsplit(urls[0])
    if parsed_url.scheme.lower() in ('http', 'https') and (
            parsed_url.username is not None or parsed_url.password is not None):
        raise GitError('HTTP remote credentials must use a credential helper, not URL userinfo')
    ref = ref or f'refs/heads/{branch}'
    if not ref.startswith('refs/heads/'):
        raise GitError('Publication target must be a branch')
    _run(root, 'check-ref-format', ref)
    return {'branch': branch, 'remote': remote, 'ref': ref, 'url': urls[0]}


def _target_current(root: str | Path, frozen: dict[str, str]) -> None:
    if target(root, frozen['remote'], frozen['branch'], frozen['ref']) != frozen:
        raise GitError('Branch or remote push URL changed since task creation')


def _paths(root: Path, paths: list[str],
           policy: dict[str, Any] | None = None) -> list[str]:
    """Use the contract's literal-path validator for publication snapshots."""
    from .state import StateError, validate_paths
    if not paths or len(paths) != len(set(paths)):
        raise GitError('Scope must contain distinct exact paths')
    try:
        return list(validate_paths(root, {name: 'scope' for name in paths}, policy))
    except StateError as exc:
        raise GitError(str(exc)) from exc


def _staged(root: str | Path, index: Path | None = None) -> set[str]:
    return {p.decode('utf-8', 'surrogateescape') for p in
            _run(root, 'diff', '--cached', '--name-only', '-z', '--no-renames',
                 index=index).split(b'\0') if p}


def _index_entries(root: str | Path, index: Path | None = None) -> dict[str, list[str]]:
    """Read index modes, object IDs and stages without reading their blobs."""
    result: dict[str, list[str]] = {}
    records = _run(root, 'ls-files', '--stage', '-z', index=index).split(b'\0')
    for record in records:
        if not record:
            continue
        metadata, raw_name = record.split(b'\t', 1)
        name = raw_name.decode('utf-8', 'surrogateescape')
        result.setdefault(name, []).append(metadata.decode('ascii'))
    return result


def _index_snapshot(root: str | Path, paths: list[str]) -> dict[str, list[str]]:
    """Bind selected index entries, including an explicit absence or deletion."""
    entries = _index_entries(root)
    return {name: entries.get(name, []) for name in sorted(set(paths))}


def _path_input(paths: list[str]) -> bytes:
    """Encode exact names for Git's NUL-delimited stdin path interfaces."""
    return b''.join(name.encode('utf-8', 'surrogateescape') + b'\0' for name in paths)


def _tree_entries(root: str | Path, tree: str) -> dict[str, bytes]:
    """Read tree entry modes and object IDs without opening file contents."""
    result: dict[str, bytes] = {}
    for record in _run(root, 'ls-tree', '-r', '-z', tree).split(b'\0'):
        if record:
            metadata, raw_name = record.split(b'\t', 1)
            mode, _kind, object_id = metadata.split(b' ')
            result[raw_name.decode('utf-8', 'surrogateescape')] = mode + b' ' + object_id
    return result


def _reset_index_paths(root: str | Path, tree: str, paths: list[str], index: Path) -> None:
    """Replace owned index entries from a reviewed tree, preserving other entries.

    Index-info input avoids command-line limits for large cleanup contracts and
    never refreshes or follows a removed private worktree path.
    """
    entries = _tree_entries(root, tree)
    encoded = {name: name.encode('utf-8', 'surrogateescape') for name in paths}
    # Remove all owned entries first: a new link can replace an old directory
    # only after its explicitly owned descendant entries have been removed.
    records = [b'0 ' + b'0' * len(tree) + b'\t' + encoded[name] + b'\0' for name in paths]
    records.extend(entries[name] + b'\t' + encoded[name] + b'\0'
                   for name in paths if name in entries)
    _run(root, 'update-index', '-z', '--index-info', data=b''.join(records), index=index)


def _worktree_snapshot(root: str | Path, paths: list[str],
                       policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Bind owned files or literal links without reading explicitly removed data.

    Removal entries describe an index-only effect; their local files, if any,
    are outside the publication and are deliberately neither opened nor hashed.

    Args:
        root: Exact Git owner root.
        paths: Exact owned file, removal or declared leaf-link paths.
        policy: Validated publication capabilities governing these paths.

    Returns:
        Regular-file hashes and modes, literal link targets, deletion markers,
        or index-only removal markers for the exact scope.
    """
    root = Path(root).resolve()
    names = _paths(root, paths, policy)
    removed = set((policy or {}).get('remove_paths', []))
    result: dict[str, Any] = {}
    for name in names:
        if name in removed:
            result[name] = {'remove_from_index': True}
            continue
        path = root / name
        if path.is_symlink():
            result[name] = {'symlink_target': os.readlink(path), 'mode': 0o120000}
            continue
        if not path.exists():
            result[name] = None
            continue
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise GitError('Scope requires regular files or explicit deletions')
        result[name] = {'sha256': _file_hash(path), 'mode': stat.S_IMODE(metadata.st_mode)}
    return result


DEFAULT_PRIVATE = frozenset({'private', 'conversations', 'conversation_archives',
                             'transcripts', 'secrets', '.env', 'auth.json',
                             'sessions', 'rollouts', 'daemon_logs', 'sync_state',
                             '.sync_state', 'turn_states', 'archived_sessions',
                             'credentials.json', '.netrc', 'id_rsa', 'id_ed25519',
                             '.playwright-mcp'})


def private_path(path: str, policy: dict[str, Any] | None = None) -> bool:
    """Recognize private paths without reading their contents.

    Project policy adds ``private_prefixes`` and ``private_components``. Defaults
    cannot be removed by a project. Generic words such as 'logs' or 'manifests'
    are not globally blocked because build manifests and application logs can
    legitimately be source; owners must declare their private directories.
    """
    policy = policy or {}
    parts = PurePosixPath(path).parts
    lowered = {p.casefold() for p in parts}
    if lowered & (DEFAULT_PRIVATE | {p.casefold() for p in policy.get('private_components', [])}):
        return True
    folded_path = path.casefold()
    name = parts[-1].casefold() if parts else ''
    # These identify runtime/private material even when it was force-added or
    # later deleted. Source scripts such as conversations_sync_daemon.py remain
    # ordinary code: classify the data suffix, not merely the word 'daemon'.
    if any(part.casefold().endswith('_conversations') for part in parts):
        return True
    if ((name.startswith('.env.') and name != '.env.example')
            or name.startswith('rollout-')
            or ('_daemon.' in name and name.endswith(('.json', '.jsonl', '.sqlite', '.db', '.log', '.err')))
            or ('_daemon.log' in name)
            or ('conversation' in name and name.endswith(('.json', '.jsonl', '.log')))):
        return True
    if any(folded_path == prefix or folded_path.startswith(prefix + '/')
           for prefix in ('.claude/cache', '.claude/logs', '.codex/cache', '.codex/logs')):
        return True
    return any(folded_path == prefix.casefold().rstrip('/') or folded_path.startswith(prefix.casefold().rstrip('/') + '/')
               for prefix in policy.get('private_prefixes', [])) or any(
                   fnmatch.fnmatchcase(folded_path, pattern.casefold())
                   or fnmatch.fnmatchcase('/' + folded_path, pattern.casefold())
                   for pattern in policy.get('private_patterns', []))


def _guard_paths(policy: dict[str, Any], event: str) -> list[Path]:
    paths = [Path(name) for name in policy.get(event.replace('-', '_') + '_hooks', [])]
    chain = policy.get('preserve_git_hook_chain', [])
    if isinstance(chain, str):
        chain = [chain]
    for directory in chain:
        hook = Path(directory) / event
        if hook.exists():
            paths.append(hook)
    return list(dict.fromkeys(paths))


@contextlib.contextmanager
def _temporary_index(root: str | Path, initial: Path | None = None) -> Iterator[Path]:
    fd, name = tempfile.mkstemp(prefix='constellation-index-', dir=_git_dir(root))
    os.close(fd)
    path = Path(name)
    path.unlink()
    try:
        if initial is not None and initial.exists():
            shutil.copyfile(initial, path)
        yield path
    finally:
        path.unlink(missing_ok=True)
        Path(str(path) + '.lock').unlink(missing_ok=True)


def candidate(root: str | Path, paths: list[str], target: dict[str, str],
              policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the exact reviewed worktree scope without changing real staging.

    Explicit policy lists can adopt owned staging, publish literal leaf links,
    or remove tracked entries while retaining their local data. Adopted staging
    is fingerprinted, but current worktree bytes remain the publication source.
    The default contract continues to reject overlap with existing staging.

    Args:
        root: Exact Git owner root.
        paths: Complete literal scope, including replaced descendants.
        target: Frozen remote, branch and destination ref.
        policy: Project restrictions and explicit publication capabilities.

    Returns:
        The exact parent, candidate tree, snapshots and their fingerprint.

    Raises:
        GitError: Scope, current data, staging, destination or privacy violates
            the declared contract. The real index remains untouched.
    """
    from .state import effective_policy
    root = Path(root).resolve()
    policy = effective_policy(root, policy)
    paths = _paths(root, paths, policy)
    removed = set(policy.get('remove_paths', []))
    adopted = policy.get('adopt_staged_paths', [])
    adopted_names = set(adopted)
    _target_current(root, target)
    if any((_git_dir(root) / name).exists() for name in
           ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply')):
        raise GitError('Complete the existing Git operation before publication')
    scoped_index = _index_snapshot(root, paths)
    if any(entry.rsplit(' ', 1)[-1] != '0'
           for entries in scoped_index.values() for entry in entries):
        raise GitError('Resolve unmerged scoped index entries before publication')
    if (_staged(root) & set(paths)) - adopted_names:
        raise GitError('Scope overlaps already staged work')
    if any(private_path(path, policy) for path in paths if path not in removed):
        raise GitError('Private paths cannot enter a publication candidate')
    parent = _text(root, 'rev-parse', 'HEAD')
    parent_entries = _tree_entries(root, parent)
    for name in paths:
        if name in removed:
            continue
        if (parent_entries.get(name, b'').startswith(b'160000 ')
                or any(entry.startswith('160000 ') for entry in scoped_index[name])):
            raise GitError('Gitlinks may only be removed from this Git owner')
    adopted_index = {name: scoped_index[name] for name in sorted(adopted)}
    worktree = _worktree_snapshot(root, paths, policy)
    with _temporary_index(root) as index:
        _run(root, 'read-tree', parent, index=index)
        if removed:
            _run(root, 'update-index', '--force-remove', '-z', '--stdin',
                 data=_path_input(sorted(removed)), index=index)
        added = [name for name in paths if name not in removed
                 and (worktree[name] is not None or name in parent_entries)]
        ordinary = [name for name in added if name not in adopted_names]
        if ordinary:
            _run(root, 'add', '--all', '--pathspec-from-file=-', '--pathspec-file-nul',
                 data=_path_input(ordinary), index=index)
        adopted_files = [name for name in added if name in adopted_names]
        if adopted_files:
            # Existing staging is an explicit adoption contract, including
            # files deliberately staged despite an ignore rule. Only those
            # exact names may bypass ignore matching in the isolated index.
            _run(root, 'add', '--all', '--force', '--pathspec-from-file=-', '--pathspec-file-nul',
                 data=_path_input(adopted_files), index=index)
        tree = _text(root, 'write-tree', index=index)
    changed = {name.decode('utf-8', 'surrogateescape') for name in _run(
        root, 'diff-tree', '--no-commit-id', '--name-only', '-r', '--no-renames', '-z',
        parent, tree).split(b'\0') if name}
    if changed - set(paths):
        raise GitError('Candidate changes undeclared paths; include replaced descendants in scope')
    if any(private_path(name, policy) for name in _tree_entries(root, tree)):
        raise GitError('Candidate retains private tracked paths; declare index-only removals')
    if (_text(root, 'rev-parse', 'HEAD') != parent
            or _worktree_snapshot(root, paths, policy) != worktree
            or (adopted and _index_snapshot(root, adopted) != adopted_index)):
        raise GitError('HEAD, scoped bytes or adopted staging changed while preparing candidate; retry')
    value = {'root': str(root), 'paths': paths, 'parent': parent, 'tree': tree,
             'target': target, 'policy': policy or {}, 'worktree': worktree}
    if adopted:
        value['adopted_index'] = adopted_index
    value['guard_hashes'] = {str(path): _file_hash(path) for event in ('pre-commit', 'pre-push')
                             for path in _guard_paths(policy or {}, event)}
    value['fingerprint'] = _digest(value)
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.intent-')
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


@contextlib.contextmanager
def _index_lock(root: str | Path) -> Iterator[tuple[Path, Path]]:
    index = _git_dir(root) / 'index'
    lock = Path(str(index) + '.lock')
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise GitError('Git index is busy; retry after its owner finishes') from exc
    os.close(fd)
    try:
        yield index, lock
    finally:
        lock.unlink(missing_ok=True)


def _journal_path(root: str | Path, task_id: str) -> Path:
    # Hash IDs so task labels never become filesystem paths.
    return _git_dir(root) / 'constellation' / 'publication' / (_digest(task_id) + '.json')


def _preserve_index(root: str | Path, index: Path, task_id: str) -> dict[str, str]:
    """Retain the original index and its staged objects before adopting staging.

    The private index copy preserves stage metadata. A local tree ref keeps the
    referenced blobs reachable through garbage collection; it is never a push
    destination. Neither operation opens the worktree files represented there.

    Args:
        root: Exact Git owner root, with its real index lock already held.
        index: The unchanged original index being adopted.
        task_id: Native ledger task owning this publication.

    Returns:
        Private backup path and hash, preservation tree and local ref.

    Raises:
        GitError: Existing recovery data differs or staging cannot be safely
            preserved. No branch or worktree file has been changed.
    """
    original_hash = _file_hash(index)
    journal = _journal_path(root, task_id)
    journal.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = journal.with_name(journal.stem + '.original-' + original_hash + '.index')
    if backup.exists():
        if _file_hash(backup) != original_hash:
            raise GitError('Original index recovery copy changed; inspect before publication')
    else:
        shutil.copyfile(index, backup)
        with backup.open('rb') as stream:
            os.fsync(stream.fileno())
    # Build the preservation tree from another index so write-tree cannot
    # refresh the real index or contend with its already-held lock.
    with _temporary_index(root, backup) as original:
        tree = _text(root, 'write-tree', index=original)
    reference = 'refs/constellation/index-backups/' + _digest(task_id) + '/' + original_hash
    _run(root, 'update-ref', reference, tree)
    if _file_hash(index) != original_hash:
        raise GitError('Original index changed while preserving adopted staging')
    return {'path': str(backup), 'sha256': original_hash, 'tree': tree, 'ref': reference}


def _project_guards(root: str | Path, tree: str, policy: dict[str, Any]) -> None:
    """Run preserved project validators against the exact candidate index.

    ``pre_commit_hooks`` contains absolute executable paths. The installer must
    identify non-Constellation hooks before replacing the native hooksPath.
    Guards may inspect the worktree but must not alter candidate staged bytes.
    """
    hooks = _guard_paths(policy, 'pre-commit')
    if not hooks:
        return
    with _temporary_index(root) as index:
        _run(root, 'read-tree', tree, index=index)
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env['GIT_INDEX_FILE'] = str(index)
        for name in hooks:
            executable = Path(name)
            if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
                raise GitError('Preserved project pre-commit guard is unavailable')
            try:
                result = subprocess.run([str(executable)], cwd=root, env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        timeout=120, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise GitError('Preserved project guard failed or timed out') from exc
            if result.returncode or _text(root, 'write-tree', index=index) != tree:
                raise GitError('Preserved project guard rejected or changed the candidate')


def commit(store: Any, task_id: str, message: str) -> str:
    """Commit reviewed bytes while preserving foreign staging, with crash intent.

    The store lock serializes task updates; Git's index lock protects staging;
    update-ref compares the old head. A durable intent and prepared new index
    precede the ref change. ``recover`` completes a crash between ref and index.
    """
    from .state import fingerprint, ready
    if not message.strip() or '\0' in message:
        raise GitError('A nonempty commit message is required')
    with store.locked(task_id) as task:
        previous = task.get('publication', {})
        continuation = previous.get('status') == 'verified_local_changes'
        if previous.get('commit') and not continuation:
            raise GitError('Task already has a commit; use push or recover')
        if task.get('mode', 'publish') != 'publish':
            raise GitError('A local task cannot publish')
        ready(task)
        root = task['root']
        if continuation and (_text(root, 'rev-parse', 'HEAD') != previous['commit']
                             or remote_sha(root, task['target']) != previous['commit']):
            raise GitError('Continuation requires the previously verified commit at HEAD and remote')
        if _journal_path(root, task_id).exists() and not continuation:
            raise GitError('Publication intent already exists; recover it first')
        with _index_lock(root) as (index, lock):
            current = candidate(root, task['paths'], task['target'], task.get('policy'))
            if current['tree'] == _text(root, 'rev-parse', 'HEAD^{tree}'):
                raise GitError('No scoped changes to commit')
            _project_guards(root, current['tree'], current['policy'])
            # Re-evaluate ready after acquiring index lock and building the tree.
            expected = fingerprint(task, current)
            if ready(task) != expected:
                raise GitError('Candidate changed during publication')
            index_backup = (_preserve_index(root, index, task_id)
                            if _staged(root) & set(task['paths']) else None)
            sha = _text(root, 'commit-tree', current['tree'], '-p', current['parent'],
                        data=(message.rstrip() + '\n').encode())
            journal_path = _journal_path(root, task_id)
            prepared = journal_path.with_suffix('.index')
            prepared.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            original_entries = _index_entries(root, index)
            with _temporary_index(root, index) as replacement:
                _reset_index_paths(root, current['tree'], task['paths'], replacement)
                replacement_entries = _index_entries(root, replacement)
                foreign = (set(original_entries) | set(replacement_entries)) - set(task['paths'])
                if any(original_entries.get(name) != replacement_entries.get(name) for name in foreign):
                    raise GitError('Preparing the owned index would change foreign staging')
                shutil.copyfile(replacement, prepared)
            intent = {'task': task_id, 'phase': 'commit_pending', 'candidate': current,
                      'commit': sha, 'old_index': _file_hash(index),
                      'new_index': _file_hash(prepared), 'evidence': _publication_evidence(task),
                      'evidence_snapshot': copy.deepcopy({'checks': task['checks'], 'reviews': task['reviews']})}
            if index_backup:
                intent['index_backup'] = index_backup
            if continuation:
                history = task.setdefault('publications', [])
                if not any(item['commit'] == previous['commit'] for item in history):
                    history.append(dict(previous))
                # Keep the verified receipt before replacing the latest intent.
                store.save_locked(task)
            _atomic_json(journal_path, intent)
            _run(root, 'update-ref', f"refs/heads/{task['target']['branch']}", sha, current['parent'])
            shutil.copyfile(prepared, lock)
            os.replace(lock, index)
            intent['phase'] = 'committed'
            _atomic_json(journal_path, intent)
            task['publication'] = {'commit': sha, 'parent': current['parent'],
                                   'tree': current['tree'], 'guard_hashes': current['guard_hashes'],
                                   'worktree': current['worktree'], 'evidence': intent['evidence'],
                                   'evidence_snapshot': intent['evidence_snapshot'],
                                   'status': 'committed'}
            if index_backup:
                task['publication']['index_backup'] = index_backup
            prepared.unlink(missing_ok=True)
            return sha


def _tasks(store: Any) -> list[dict[str, Any]]:
    """Read tasks through the public list method supplied by the store."""
    return store.list_tasks()


def _approved(store: Any, root: str | Path) -> dict[str, dict[str, Any]]:
    result = {}
    for task in _tasks(store):
        if task['root'] != str(Path(root).resolve()):
            continue
        for publication in task.get('publications', []):
            result[publication['commit']] = {**task, 'publication': publication, 'publication_current': False}
        publication = task.get('publication', {})
        if publication.get('commit'):
            result[publication['commit']] = {**task, 'publication_current': True}
    return result


def _publication_evidence(task: dict[str, Any]) -> str:
    return _digest({'checks': task['checks'], 'reviews': task['reviews']})


def _evidence_unchanged(task: dict[str, Any]) -> None:
    if task['publication'].get('evidence') != _publication_evidence(task):
        raise GitError('Evidence changed after commit; the frozen publication cannot be pushed')


def _close_verified(store: Any, task: dict[str, Any]) -> None:
    """Close only when remote verification leaves no owned local work behind."""
    publication = task['publication']
    try:
        pending = (_worktree_snapshot(task['root'], task['paths'], task.get('policy')) != publication['worktree']
                   or bool(_staged(task['root']) & set(task['paths'])))
    except (GitError, OSError):
        pending = True
    if pending:
        publication['status'] = 'verified_local_changes'
        task['status'] = 'open'
        store.save_locked(task)
        raise GitError('Remote SHA verified; owned local changes remain. Run fresh checks, review and commit in this task')
    _evidence_unchanged(task)
    publication['status'] = 'verified'
    task['status'] = 'closed'


def _outgoing(root: str | Path, local: str, remote: str) -> list[str]:
    graft_path = Path(_text(root, 'rev-parse', '--git-path', 'info/grafts'))
    if not graft_path.is_absolute():
        graft_path = Path(root) / graft_path
    if graft_path.exists() or _text(root, 'rev-parse', '--is-shallow-repository') == 'true':
        raise GitError('Outgoing validation requires complete history without grafts')
    args = ['rev-list', local]
    if remote.strip('0'):
        _run(root, 'cat-file', '-e', remote + '^{commit}')
        try:
            _run(root, 'merge-base', '--is-ancestor', remote, local)
        except GitError as exc:
            raise GitError('Non-fast-forward publication is forbidden') from exc
        args += ['--not', remote]
    return _text(root, *args).splitlines()


def check_outgoing(root: str | Path, local: str, remote: str,
                   policy: dict[str, Any] | None = None) -> list[str]:
    """Inspect every outgoing commit tree, including private paths deleted later."""
    commits = _outgoing(root, local, remote)
    for sha in commits:
        names = _run(root, 'ls-tree', '-r', '--name-only', '-z', sha).split(b'\0')
        if any(private_path(p.decode('utf-8', 'surrogateescape'), policy) for p in names if p):
            raise GitError('Outgoing history contains a private path')
    return commits


def pre_push(root: str | Path, remote: str, url: str, lines: str, store: Any) -> None:
    """Validate the exact ref update stream supplied by Git's pre-push hook."""
    from .state import effective_policy
    approved = _approved(store, root)
    updates = [line.split() for line in lines.splitlines() if line.strip()]
    if not updates:
        return
    preserved_hooks: set[Path] = set()
    for update in updates:
        if len(update) != 4:
            raise GitError('Malformed pre-push update')
        local_ref, sha, remote_ref, old = update
        if not sha.strip('0') or sha not in approved:
            raise GitError('Deletion or unreviewed commit publication is forbidden')
        task = approved[sha]
        if task.get('publication_current'):
            _evidence_unchanged(task)
        frozen = task['target']
        _target_current(root, frozen)
        if ((remote, url, remote_ref) != (frozen['remote'], frozen['url'], frozen['ref'])
                or local_ref not in (f"refs/heads/{frozen['branch']}", sha)):
            raise GitError('Push target differs from the reviewed destination')
        policy = effective_policy(root, task.get('policy'))
        preserved_hooks.update(_guard_paths(policy, 'pre-push'))
        outgoing = check_outgoing(root, sha, old, policy)
        if any(commit not in approved for commit in outgoing):
            raise GitError('Outgoing history includes commits without review records')
        for commit_sha in outgoing:
            record = approved[commit_sha]
            if record['target'] != frozen:
                raise GitError('Outgoing commit was approved for another destination')
            if _text(root, 'rev-parse', commit_sha + '^{tree}') != record['publication']['tree']:
                raise GitError('Publication record tree mismatch')
            current_guards = {str(path): _file_hash(path) for event in ('pre-commit', 'pre-push')
                              for path in _guard_paths(policy, event)}
            if record['publication'].get('guard_hashes', {}) != current_guards:
                raise GitError('Project guards changed after review')
    for hook in sorted(preserved_hooks):
        if not hook.is_absolute() or not hook.is_file() or not os.access(hook, os.X_OK):
            raise GitError('Preserved pre-push guard is unavailable')
        env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        try:
            result = subprocess.run([str(hook), remote, url], cwd=root, env=env,
                                    input=lines.encode(), stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=120, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitError('Preserved pre-push guard failed or timed out') from exc
        if result.returncode:
            raise GitError('Preserved pre-push guard rejected publication')


def pre_commit(root: str | Path, store: Any) -> None:
    """Validate the configured snapshot automation or require managed commit."""
    from .monitor_gate import allow_snapshot
    if allow_snapshot(Path(root)):
        return
    raise GitError('Use constellation commit so review and foreign staging are checked')


def remote_sha(root: str | Path, frozen: dict[str, str]) -> str | None:
    """Read the exact destination ref from the frozen push URL."""
    output = _text(root, 'ls-remote', '--refs', frozen['url'], frozen['ref'])
    matches = [line.split()[0] for line in output.splitlines()
               if len(line.split()) == 2 and line.split()[1] == frozen['ref']]
    if len(matches) > 1:
        raise GitError('Ambiguous remote ref')
    return matches[0] if matches else None


def push(store: Any, task_id: str) -> str:
    """Persist intent, push one frozen ref, then confirm the exact remote SHA."""
    with store.locked(task_id) as task:
        if task.get('mode', 'publish') != 'publish':
            raise GitError('A local task cannot publish')
        root, frozen = task['root'], task['target']
        _target_current(root, frozen)
        pub = task.get('publication', {})
        sha = pub.get('commit')
        if not sha or _text(root, 'rev-parse', 'HEAD') != sha:
            raise GitError('Publish requires the task commit at HEAD')
        old = remote_sha(root, frozen)
        if old == sha:
            _close_verified(store, task)
            return sha
        _evidence_unchanged(task)
        pre_push(root, frozen['remote'], frozen['url'],
                 f"refs/heads/{frozen['branch']} {sha} {frozen['ref']} {old or '0' * 40}", store)
        pub.update(status='push_pending', remote_before=old)
        store.save_locked(task)
        journal_path = _journal_path(root, task_id)
        intent = json.loads(journal_path.read_text())
        intent.update(phase='push_pending', remote_before=old)
        _atomic_json(journal_path, intent)
        _run(root, 'push', '--no-follow-tags', frozen['remote'], f"{sha}:{frozen['ref']}", timeout=120)
        if remote_sha(root, frozen) != sha:
            raise GitError('Push returned without the expected remote SHA; recover')
        intent['phase'] = 'verified'
        _atomic_json(journal_path, intent)
        _close_verified(store, task)
        return sha


def recover(store: Any, task_id: str) -> dict[str, Any]:
    """Reconcile commit/index and interrupted push without creating another commit."""
    with store.locked(task_id) as task:
        if task.get('mode', 'publish') != 'publish':
            raise GitError('A local task has no publication to recover')
        root, frozen = task['root'], task['target']
        _target_current(root, frozen)
        path = _journal_path(root, task_id)
        if not path.exists():
            raise GitError('No publication intent to recover')
        intent = json.loads(path.read_text())
        sha, candidate_value = intent['commit'], intent['candidate']
        head = _text(root, 'rev-parse', 'HEAD')
        if head != sha and not (intent['phase'] == 'commit_pending' and head == candidate_value['parent']):
            raise GitError('HEAD differs from interrupted commit; no changes made')
        if intent['phase'] == 'commit_pending':
            with _index_lock(root) as (index, lock):
                current = _file_hash(index)
                if head == candidate_value['parent']:
                    from .state import fingerprint, ready
                    if current != intent['old_index'] or ready(task) != fingerprint(task, candidate_value):
                        raise GitError('Pre-commit interruption changed; inspect before recovery')
                    _run(root, 'update-ref', f"refs/heads/{frozen['branch']}", sha, head)
                if current == intent['old_index']:
                    prepared = path.with_suffix('.index')
                    if _file_hash(prepared) != intent['new_index']:
                        raise GitError('Prepared recovery index is unavailable')
                    shutil.copyfile(prepared, lock)
                    os.replace(lock, index)
                elif current != intent['new_index']:
                    raise GitError('Index changed after interruption; preserve and inspect it')
            intent['phase'] = 'committed'
            _atomic_json(path, intent)
        task['publication'] = {'commit': sha, 'parent': candidate_value['parent'],
                               'tree': candidate_value['tree'],
                               'guard_hashes': candidate_value['guard_hashes'],
                               'worktree': candidate_value['worktree'], 'evidence': intent['evidence'],
                               'evidence_snapshot': intent['evidence_snapshot'],
                               'status': 'committed'}
        if intent.get('index_backup'):
            task['publication']['index_backup'] = intent['index_backup']
        if intent['phase'] in ('push_pending', 'verified'):
            if remote_sha(root, frozen) == sha:
                intent['phase'] = 'verified'
                _atomic_json(path, intent)
                _close_verified(store, task)
            else:
                task['publication']['status'] = 'push_pending'
        return task['publication']
