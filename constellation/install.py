"""Install native entry points with a private, reversible receipt.

Only native entries live in Codex, Claude, Copilot and project discovery directories. This module
never approves hook trust or changes model, authentication, or privacy settings.
"""
from __future__ import annotations

import argparse
import ctypes
import sys
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time
import tomllib
from typing import Any, Callable, Mapping, Sequence
import uuid

BEGIN = '# BEGIN Constellation native entries'
END = '# END Constellation native entries'


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def fingerprint(path: Path) -> str | None:
    """Hash bytes, modes, and links without following symbolic links."""
    if not path.exists() and not path.is_symlink():
        return None
    digest = hashlib.sha256()
    paths = [path] + (sorted(path.rglob('*')) if path.is_dir() and not path.is_symlink() else [])
    for item in paths:
        mode = item.lstat().st_mode
        digest.update(str(item.relative_to(path)).encode())
        digest.update(str(stat.S_IMODE(mode)).encode())
        if item.is_symlink():
            digest.update(b'L' + os.fsencode(os.readlink(item)))
        elif item.is_file():
            digest.update(b'F' + item.read_bytes())
        elif item.is_dir():
            digest.update(b'D')
        else:
            raise ValueError(f'Unsupported filesystem object: {item}')
    return digest.hexdigest()


def _toml_blocks(text: str) -> list[str]:
    starts = [m.start() for m in re.finditer(r'^\[.*\]\s*$', text, re.MULTILINE)]
    if not starts:
        return [text]
    return [text[:starts[0]]] + [text[a:b] for a, b in zip(starts, starts[1:] + [len(text)])]


def _native_config(text: str, source: Path, home: Path, entries: list[dict[str, Any]], agents: list[dict[str, Any]]) -> str:
    """Replace only owned references; preserve unrelated TOML, including memories."""
    original_text = text
    original_config = tomllib.loads(text)
    text = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n?', '', text, flags=re.DOTALL)
    old_skills = {str(Path(row['source']) / filename) for row in entries for filename in ('SKILL.md', 'skill.md')}
    old_skills.update(str(home / 'OmarOS/.agents/skills' / row['name'] / 'SKILL.md') for row in entries if row['group'] == 'omaros')
    agent_names = {row['name'] for row in agents}
    preserved = []
    for block in _toml_blocks(text):
        header = block.splitlines()[0].strip() if block.strip() else ''
        if header in ('[marketplaces.constellation]', '[plugins."constellation@constellation"]'):
            continue
        if header.startswith('[hooks.state.') and 'constellation@constellation' in header:
            continue
        if header.startswith('[agents.'):
            try:
                if set(tomllib.loads(block).get('agents', {})) & agent_names:
                    continue
            except tomllib.TOMLDecodeError:
                pass
        if header == '[[skills.config]]':
            parsed = tomllib.loads(block)['skills']['config'][0]
            candidate = parsed.get('path', '')
            # A disabled skill is an explicit client preference, even when its
            # discovery link is regenerated or the inventory changes ownership.
            if (parsed.get('enabled') is not False and
                    (candidate in old_skills or ('/constellation/' in candidate and candidate.endswith('/SKILL.md')))):
                continue
        # Historical markers enclosed both agent and personal memory settings.
        # Remove markers, never the enclosed privacy/preferences content.
        block = re.sub(r'^# (?:BEGIN|END) constellation managed agent policy\n?', '', block, flags=re.MULTILINE)
        preserved.append(block)
    result = ''.join(preserved).rstrip() + '\n\n' + BEGIN + '\n'
    for agent in agents:
        result += f'\n[agents.{json.dumps(agent["name"])}]\n'
        result += f'description = {json.dumps(agent["description"], ensure_ascii=False)}\n'
        result += f'config_file = {json.dumps(str(agent["path"]))}\n'
    # Read presence before removing managed markers, which may enclose an
    # existing disabled entry. A removed plugin must stay absent on reinstall.
    if 'constellation@constellation' in original_config.get('plugins', {}):
        result += '\n[plugins."constellation@constellation"]\nenabled = false\n'
    result += END + '\n'
    parsed = tomllib.loads(result)
    return original_text if parsed == original_config else result


def _skill_parent_identity(directory: Path) -> list[dict[str, Any]]:
    """Bind a discovery directory and its ancestry without following links."""
    identities = []
    for parent in (directory, *directory.parents):
        metadata = parent.lstat()
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f'Skill discovery parent is not a real directory: {parent}')
        identities.append({'path': str(parent), 'device': metadata.st_dev,
                           'inode': metadata.st_ino})
    return identities


def _verify_skill_parent(operation: Mapping[str, Any]) -> None:
    """Reject a substituted ancestor before inspecting or moving a retired link."""
    identities = operation.get('skill_parent_identity')
    if identities is None:
        return
    if not identities or identities[0]['path'] != str(Path(operation['path']).parent):
        raise ValueError('Retired skill link has an invalid parent identity')
    try:
        current = _skill_parent_identity(Path(identities[0]['path']))
    except OSError as error:
        raise ValueError(f'Skill discovery parent is unavailable: {operation["path"]}') from error
    if current != identities:
        raise ValueError(f'Skill discovery parent changed: {operation["path"]}')


def _retire_stale_skill_links(source: Path, directories: Sequence[Path],
                             desired: Mapping[str, str], protected: set[str],
                             operations: dict[str, dict[str, Any]],
                             add: Callable[[Path, str, str | None], None]) -> dict[str, Any]:
    """Reconcile direct canonical skill aliases with this installation's scope.

    Ownership requires an absolute lexical target of the exact form
    ``source/skills/group/name`` and the same native entry name. Neither target
    resolution nor a retired-name catalog is needed, including for broken links.
    Unknown entries and provider directories are never traversed or removed.

    Args:
        source: Canonical checkout used by the native link installer.
        directories: Only native discovery directories authorized for this client.
        desired: Successful current or planned links, collected by the installer.
        protected: Conflict paths, including Claude's retained project fallbacks.
        operations: Existing reversible operation map, augmented with parent guards.
        add: Common operation collector with expected content fingerprints.

    Returns:
        Exact retired links and conflicts that remain untouched.
    """
    retired: list[str] = []
    conflicts: list[dict[str, str]] = []
    discovery_directories = list(dict.fromkeys(directories))
    # Earlier adapters can request core deduplication without the ancestry
    # guard used here. Remove those requests before any filesystem-dependent
    # skip; only a fully revalidated direct link may re-enter the final plan.
    prior_removals = {
        name: operations.pop(name)
        for name, operation in list(operations.items())
        if operation['kind'] == 'remove' and Path(name).parent in discovery_directories
    }
    for directory in discovery_directories:
        if not directory.exists() and not directory.is_symlink():
            continue
        try:
            ancestry = _skill_parent_identity(directory)
        except (OSError, ValueError):
            conflicts.append({'path': str(directory),
                              'reason': 'Skill discovery directory has unsafe or unavailable ancestry'})
            continue
        for path in sorted(directory.iterdir()):
            if str(path) in desired or str(path) in protected or not path.is_symlink():
                continue
            if str(path) in operations:
                continue
            previous = prior_removals.get(str(path))
            metadata = path.lstat()
            if not stat.S_ISLNK(metadata.st_mode):
                raise ValueError(f'Skill entry changed while planning: {path}')
            raw_target = os.readlink(path)
            target = Path(raw_target)
            try:
                relative = target.relative_to(source / 'skills')
            except ValueError:
                if previous is not None:
                    # Claude's inherited core deduplication may have resolved
                    # an indirect provider link into the source. That does not
                    # confer ownership of the provider's original native link.
                    conflicts.append({'path': str(path),
                                      'reason': 'Preserved removal candidate without a direct canonical target'})
                continue
            if (not target.is_absolute() or str(target) != raw_target
                    or len(relative.parts) != 2 or '..' in relative.parts
                    or relative.name != path.name):
                conflicts.append({'path': str(path),
                                  'reason': 'Shared-source alias does not match a canonical skill entry'})
                continue
            if _skill_parent_identity(directory) != ancestry:
                raise ValueError(f'Skill discovery parent changed while planning: {directory}')
            add(path, 'remove', None)
            operation = operations.get(str(path))
            if operation is None:
                continue
            expected = hashlib.sha256()
            expected.update(b'.')
            expected.update(str(stat.S_IMODE(metadata.st_mode)).encode())
            expected.update(b'L' + os.fsencode(raw_target))
            if (operation['before'] != expected.hexdigest()
                    or (previous is not None and previous['before'] != expected.hexdigest())):
                raise ValueError(f'Skill entry changed while planning: {path}')
            operation['skill_parent_identity'] = ancestry
            _verify_skill_parent(operation)
            retired.append(str(path))
    for name in sorted(prior_removals.keys() - set(retired)):
        if not any(conflict['path'] == name for conflict in conflicts):
            conflicts.append({'path': name,
                              'reason': 'Prior skill removal canceled because current ownership was not verified'})
    return {'retired_skill_links': retired, 'skill_link_conflicts': conflicts}


def build_plan(source: Path, home: Path | None = None, state_dir: Path | None = None,
               *, client: str = 'all', copilot_home: Path | None = None) -> dict[str, Any]:
    """Describe native installation without changing files.

    Args:
        source: Canonical Constellation checkout.
        home: Native clients' home owner. Project roots still come from the inventory;
            tests must supply an isolated inventory as well as an alternate home.
        state_dir: Private backup destination, outside source and project data.
        client: All native integrations, or only Copilot's personal entries.
        copilot_home: Explicit Copilot configuration directory when customized.

    Returns:
        A plan containing exact expected input fingerprints and desired operations.
    """
    source = source.resolve()
    home = (home or Path.home()).resolve()
    state_dir = (state_dir or home / '.local/state/constellation').resolve()
    if client not in {'all', 'copilot'}:
        raise ValueError('Select all clients or the Copilot-only installation')
    from .copilot import directory_trees_overlap, plan_entries as copilot_entries
    if directory_trees_overlap(state_dir, source):
        raise ValueError('Installation receipts and source must use separate directory trees')
    inventory = json.loads((source / 'resource-inventory.json').read_text())
    entries = inventory['entries']
    agents = []
    for path in sorted((source / 'agents').glob('*.toml')):
        data = tomllib.loads(path.read_text())
        for key in ('name', 'description', 'developer_instructions'):
            if not isinstance(data.get(key), str) or not data[key]:
                raise ValueError(f'Agent lacks {key}: {path}')
        agents.append({**data, 'path': path})
    if len(agents) != 8 or len({a['name'] for a in agents}) != 8:
        raise ValueError('Expected exactly eight distinct preserved agents')
    operations: dict[str, dict[str, Any]] = {}
    desired_links: dict[str, str] = {}

    def add(path: Path, kind: str, value: str | None = None) -> None:
        if kind == 'symlink' and value is not None:
            desired_links[str(path)] = value
        current = fingerprint(path)
        if kind == 'symlink' and path.is_symlink() and os.readlink(path) == value:
            operations.pop(str(path), None)
            return
        if kind == 'write' and path.is_file() and not path.is_symlink() and path.read_text() == value:
            return
        if kind == 'remove' and current is None:
            return
        operation = {'path': str(path), 'kind': kind, 'value': value, 'before': current}
        if kind == 'write':
            # Replacing a native settings file must not broaden its permissions.
            private = path.name in {'config.toml', 'settings.json', 'settings.local.json'} or path.is_relative_to(state_dir)
            operation['mode'] = (stat.S_IMODE(path.stat().st_mode)
                                 if path.is_file() and not path.is_symlink()
                                 else 0o600 if private else 0o644)
        operations[str(path)] = operation

    copilot = copilot_entries(source, home, state_dir, agents, entries, add,
                              copilot_home=copilot_home)
    if client == 'copilot':
        retirement = _retire_stale_skill_links(
            source, [home / '.agents/skills'], desired_links,
            {row['path'] for row in copilot['copilot_conflicts']}, operations, add)
        return {'schema': 1, 'source': str(source), 'home': str(home),
                'state_dir': str(state_dir), 'client': client,
                'operations': list(operations.values()),
                'agent_names': [row['name'] for row in agents],
                'skill_links': copilot['copilot_shared_skills'],
                'preserved_variants': [], 'hook_trust': 'pending_native_review', **copilot, **retirement}

    codex = home / '.codex'
    config = codex / 'config.toml'
    add(config, 'write', _native_config(config.read_text() if config.exists() else '', source, home, entries, agents))
    instructions = source / 'instructions/AGENTS.md'
    if instructions.is_file():
        add(codex / 'AGENTS.md', 'symlink', str(instructions))
    for path in (codex / 'agents').glob('*.toml'):
        data = tomllib.loads(path.read_text())
        if data.get('name') in {row['name'] for row in agents}:
            add(path, 'remove')
    hooks_path = codex / 'hooks.json'
    hooks = json.loads(hooks_path.read_text()) if hooks_path.exists() else {'hooks': {}}
    hook_groups = hooks.setdefault('hooks', {})
    for event, groups in list(hook_groups.items()):
        retained = []
        for group in groups:
            handlers = [h for h in group.get('hooks', []) if not any(marker in h.get('command', '') for marker in ('constellation', 'omaros_permission_guard.py'))]
            if handlers:
                retained.append({**group, 'hooks': handlers})
        hook_groups[event] = retained
    import shlex
    command = f'{shlex.quote(os.sys.executable)} {shlex.quote(str(source / "constellation.py"))} hook'
    for event, action in [('PreToolUse', 'pre-tool'), ('Stop', 'stop')]:
        hook_groups.setdefault(event, []).append({'hooks': [{'type': 'command', 'command': f'{command} {action}', 'timeout': 10}]})
    hooks['hooks'] = {event: groups for event, groups in hook_groups.items() if groups}
    add(hooks_path, 'write', _json(hooks))
    core_names = {row['name'] for row in entries if row['group'] == 'core'}
    profiles_file = source / 'profiles/projects.json'
    projects = json.loads(profiles_file.read_text()).get('projects', []) if profiles_file.exists() else []
    native_roots = {Path(row['root']).resolve() for row in projects
                    if row.get('management') == 'native' and Path(row['root']).exists()}
    native_projects = [Path(row['root']) for row in projects if row.get('management') == 'native'
                       and row.get('id') != 'omaros' and Path(row['root']) != source
                       and Path(row['root']).exists()]
    skipped_variants = []
    links = []
    for row in entries:
        target = source / row['destination']
        if not target.is_dir() or not (target / 'SKILL.md').is_file():
            raise ValueError(f'Missing preserved skill: {target}')
        group, name = row['group'], row['name']
        if group != 'core' and name in core_names:
            skipped_variants.append(row['destination'])
            continue
        if group == 'core':
            roots = [home]
        elif group == 'workspace':
            roots = native_projects
        else:
            owner = Path(row['project_root']) if row.get('project_root') else None
            roots = [owner] if owner is not None and owner.resolve() in native_roots else []
        for root in roots:
            destination = root / '.agents/skills' / name
            # Duplicate names have one native source per scope. Inventory retains
            # every variant for explicit use without ambiguous native selectors.
            if str(destination) in links:
                skipped_variants.append(row['destination'])
                continue
            add(destination, 'symlink', str(target))
            links.append(str(destination))
    for project in projects:
        if project.get('management') != 'native':
            continue
        root = Path(project['root'])
        if not root.exists():
            continue
        desired = str(source / 'git-hooks')
        before_values = _git_hooks(root)
        if len(before_values) > 1:
            raise ValueError(f'Ambiguous multiple core.hooksPath values: {root}')
        if before_values != [desired]:
            operations[str(root / '.git/config:core.hooksPath')] = {'path': str(root), 'kind': 'git-hooks', 'value': desired, 'before': _values_fingerprint(before_values), 'before_values': before_values}
    from .claude import plan_entries
    claude = plan_entries(source, home, state_dir, projects, agents, entries, add)
    discovery_roots = [home] + [Path(row['root']) for row in projects
                               if row.get('management') == 'native']
    retirement = _retire_stale_skill_links(
        source, [root / folder for root in discovery_roots
                 for folder in ('.agents/skills', '.claude/skills')], desired_links,
        {row['path'] for row in claude['claude_conflicts'] + copilot['copilot_conflicts']},
        operations, add)
    return {'schema': 1, 'source': str(source), 'home': str(home), 'state_dir': str(state_dir), 'client': client, 'operations': list(operations.values()), 'agent_names': [row['name'] for row in agents], 'skill_links': links, 'preserved_variants': skipped_variants, 'hook_trust': 'pending_native_review', **claude, **copilot, **retirement}


def _copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        destination.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
    else:
        shutil.copy2(source, destination)


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _save_receipt(path: Path, receipt: dict[str, Any]) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(_json(receipt))
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def _git_hooks(root: Path) -> list[str]:
    result = subprocess.run(['git', '-C', str(root), 'config', '--local', '--get-all', 'core.hooksPath'], capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise ValueError(f'Cannot inspect Git hook configuration: {root}')
    return result.stdout.splitlines()


def _values_fingerprint(values: list[str]) -> str:
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def _current(operation: dict[str, Any]) -> str | None:
    _verify_skill_parent(operation)
    if operation['kind'] == 'git-hooks':
        return _values_fingerprint(_git_hooks(Path(operation['path'])))
    return fingerprint(Path(operation['path']))


def _set_git_hooks(root: Path, values: list[str], expected: str, recovery_root: Path) -> None:
    """Compare and change one local key under Git's native config lock.

    The lock is acquired before reading the key, so another ``git config``
    writer either finishes before comparison or fails to acquire the same lock.
    Git parses and rewrites a private candidate; unrelated configuration stays
    intact. Atomic exchange and a retained original inode preserve late writes
    through already-open file descriptors, even after publication succeeds.

    Args:
        root: Repository whose local configuration is being changed.
        values: Zero or one replacement values for ``core.hooksPath``.
        expected: Fingerprint of the values authorized by the receipt.
        recovery_root: Private receipt directory for retained inodes and journals.

    Raises:
        ValueError: The expected key or configuration bytes changed.
        FileExistsError: Another native Git writer holds the config lock.
    """
    if len(values) > 1:
        raise ValueError('A hook transaction accepts at most one value')
    result = subprocess.run(['git', '-C', str(root), 'rev-parse',
                             '--path-format=absolute', '--git-path', 'config'],
                            capture_output=True, text=True, check=True)
    config = Path(result.stdout.strip())
    if config.is_symlink() or not config.is_file():
        raise ValueError(f'Expected a regular local Git config: {config}')
    lock = config.with_name(config.name + '.lock')
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    lock_identity = os.fstat(descriptor).st_ino
    candidate_directory: Path | None = None
    preserve_lock = False
    try:
        recovery = recovery_root / uuid.uuid4().hex
        recovery.mkdir(parents=True, mode=0o700)
        os.chmod(recovery, 0o700)
        # An inode cannot be retained across filesystems. Reject before changing
        # configuration rather than replacing inode retention with a byte copy.
        if recovery.stat().st_dev != config.stat().st_dev:
            raise ValueError('Git configuration recovery must share its filesystem')
        retained = recovery / 'config.before'
        journal_path = recovery / 'journal.json'
        journal = {'schema': 1, 'config': str(config), 'retained': str(retained),
                   'expected_values': expected, 'replacement_values': values,
                   'status': 'prepared'}
        _save_receipt(journal_path, journal)
        candidate_directory = Path(tempfile.mkdtemp(prefix='.constellation-config-', dir=config.parent))
        candidate = candidate_directory / 'config'
        original = config.read_bytes()
        original_mode = stat.S_IMODE(config.stat().st_mode)
        if _values_fingerprint(_git_hooks(root)) != expected:
            raise ValueError(f'Git hook configuration changed before locked update: {root}')
        candidate.write_bytes(original)
        if values:
            subprocess.run(['git', 'config', '--file', str(candidate),
                            '--replace-all', 'core.hooksPath', values[0]],
                           check=True, capture_output=True)
        else:
            result = subprocess.run(['git', 'config', '--file', str(candidate),
                                     '--unset-all', 'core.hooksPath'], capture_output=True)
            if result.returncode not in (0, 5):
                raise ValueError(f'Cannot prepare Git hook configuration: {root}')
        prepared = candidate.read_bytes()
        with os.fdopen(descriptor, 'wb') as stream:
            descriptor = -1
            stream.write(prepared)
            stream.flush()
            os.fchmod(stream.fileno(), original_mode)
            os.fsync(stream.fileno())
        # Native Git writers remain excluded by config.lock. Also reject a
        # direct edit observed while preparing the candidate.
        if config.is_symlink() or config.read_bytes() != original:
            raise ValueError(f'Git configuration changed outside its native lock: {root}')
        _rename_exchange(lock, config)
        # From this point config.lock holds the displaced original inode. Never
        # unlink it: a writer may still hold a descriptor to that inode.
        preserve_lock = True
        lock_identity = lock.lstat().st_ino
        if lock.read_bytes() != original:
            # Keep both versions if an uncooperative writer raced publication.
            # Restoring by exchange also retains a still later edit in the lock.
            preserve_lock = True
            if config.read_bytes() == prepared:
                _rename_exchange(lock, config)
            journal['status'] = 'conflict_lock_retained'
            _save_receipt(journal_path, journal)
            raise ValueError(f'Concurrent direct Git config edit preserved; inspect {lock}')
        _rename_exclusive(lock, retained)
        journal['status'] = 'published_original_inode_retained'
        _save_receipt(journal_path, journal)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        if not preserve_lock and lock.exists() and lock.lstat().st_ino == lock_identity:
            lock.unlink()
        if candidate_directory is not None:
            shutil.rmtree(candidate_directory)


def apply_plan(plan: dict[str, Any]) -> Path:
    """Apply an inspected plan and durably record recovery before every mutation.

    Changed inputs abort. Files use atomic replacement, and directories move into
    the private backup before their discovery link is installed. A pending entry
    can be recovered after either rename without overwriting subsequent edits.
    """
    for operation in plan['operations']:
        if _current(operation) != operation['before']:
            raise ValueError(f'Installation input changed: {operation["path"]}')
    directory = Path(plan['state_dir']) / 'installations' / f'{time.strftime("%Y%m%dT%H%M%S")}-{uuid.uuid4().hex[:8]}'
    directory.mkdir(parents=True, mode=0o700)
    os.chmod(directory, 0o700)
    receipt_path = directory / 'receipt.json'
    receipt = {'schema': 1, 'source': plan['source'], 'status': 'applying', 'operations': [], 'hook_trust': 'pending_native_review'}
    _save_receipt(receipt_path, receipt)
    try:
        for index, operation in enumerate(plan['operations']):
            path = Path(operation['path'])
            if _current(operation) != operation['before']:
                raise ValueError(f'Installation input changed: {path}')
            backup = directory / 'before' / str(index)
            staged = directory / 'staged' / str(index)
            staged.parent.mkdir(parents=True, exist_ok=True)
            if operation['kind'] == 'symlink':
                staged.symlink_to(operation['value'])
            elif operation['kind'] == 'write':
                staged.write_text(operation['value'])
                os.chmod(staged, operation.get('mode', 0o600 if path.name == 'config.toml' else 0o644))
            after = _values_fingerprint([operation['value']]) if operation['kind'] == 'git-hooks' else fingerprint(staged)
            entry = {**operation, 'backup': str(backup) if operation['before'] is not None else None, 'after': after, 'status': 'pending'}
            receipt['operations'].append(entry)
            _save_receipt(receipt_path, receipt)
            if operation['kind'] == 'git-hooks':
                _set_git_hooks(path, [operation['value']], operation['before'],
                               directory / 'git-config' / str(index))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                if operation['before'] is not None:
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    _move_install_entry(operation, path, backup)
                    if fingerprint(backup) != operation['before']:
                        if not path.exists() and not path.is_symlink():
                            _move_install_entry(operation, backup, path, restoring=True)
                        raise ValueError(f'Concurrent installation edit preserved: {path}')
                if operation['kind'] != 'remove':
                    _rename_exclusive(staged, path)
            if _current(operation) != after:
                raise ValueError(f'Installation verification failed: {path}')
            entry['status'] = 'applied'
            _save_receipt(receipt_path, receipt)
        receipt['status'] = 'installed'
        _save_receipt(receipt_path, receipt)
    except BaseException:
        receipt['status'] = 'interrupted'
        _save_receipt(receipt_path, receipt)
        raise
    return receipt_path


def _move_install_entry(operation: Mapping[str, Any], source: Path, destination: Path,
                        *, restoring: bool = False) -> None:
    """Move a retirement entry through its verified, opened discovery directory.

    Args:
        operation: Receipt operation; skill retirements carry parent identities.
        source: Existing entry to capture or the preserved entry being restored.
        destination: Empty receipt or native destination.
        restoring: Anchor the native destination instead of the native source.

    Raises:
        ValueError: A discovery directory was replaced after planning.
        OSError: The exclusive move cannot safely complete.
    """
    identities = operation.get('skill_parent_identity')
    if identities is None:
        _rename_exclusive(source, destination)
        return
    _verify_skill_parent(operation)
    parent = Path(operation['path']).parent
    descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(descriptor)
        expected = identities[0]
        if (metadata.st_dev, metadata.st_ino) != (expected['device'], expected['inode']):
            raise ValueError(f'Skill discovery parent changed before moving: {operation["path"]}')
        _verify_skill_parent(operation)
        # Descriptor-relative rename stays attached to the verified directory
        # even if its pathname is substituted after the final ancestry check.
        if restoring:
            _rename_exclusive(source, Path(destination.name), destination_dir_fd=descriptor)
        else:
            _rename_exclusive(Path(source.name), destination, source_dir_fd=descriptor)
    finally:
        os.close(descriptor)


def _rename_exclusive(source: Path, destination: Path, *, source_dir_fd: int | None = None,
                      destination_dir_fd: int | None = None) -> None:
    """Atomically move an entry while refusing to replace any destination.

    Darwin RENAME_EXCL and Linux RENAME_NOREPLACE apply to files, symbolic links,
    and directories. Optional descriptors anchor skill retirement and restoration
    to the verified discovery parent. Unsupported platforms fail without writes.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        if source_dir_fd is None and destination_dir_fd is None:
            function = libc.renamex_np
            function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            result = function(os.fsencode(source), os.fsencode(destination), 0x00000004)
        else:
            function = libc.renameatx_np
            function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            result = function(-2 if source_dir_fd is None else source_dir_fd, os.fsencode(source),
                              -2 if destination_dir_fd is None else destination_dir_fd,
                              os.fsencode(destination), 0x00000004)
    elif sys.platform.startswith('linux') and hasattr(libc, 'renameat2'):
        function = libc.renameat2
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        result = function(-100 if source_dir_fd is None else source_dir_fd, os.fsencode(source),
                          -100 if destination_dir_fd is None else destination_dir_fd,
                          os.fsencode(destination), 1)
    else:
        raise RuntimeError('Atomic exclusive restore requires Darwin or Linux rename support')
    if result:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(destination))


def _rename_exchange(source: Path, destination: Path) -> None:
    """Atomically exchange two files, keeping displaced bytes recoverable."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        function = libc.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        result = function(os.fsencode(source), os.fsencode(destination), 2)
    elif sys.platform.startswith('linux') and hasattr(libc, 'renameat2'):
        function = libc.renameat2
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        result = function(-100, os.fsencode(source), -100, os.fsencode(destination), 2)
    else:
        raise RuntimeError('Atomic config exchange requires Darwin or Linux support')
    if result:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(destination))


def _validate_restore(operation: dict[str, Any]) -> None:
    current = _current(operation)
    if current == operation['before']:
        return
    pending_gap = operation['status'] in ('pending', 'reverting') and current is None and operation.get('backup') and (Path(operation['backup']).exists() or Path(operation['backup']).is_symlink())
    if current != operation['after'] and not pending_gap:
        raise ValueError(f'Refusing to overwrite changes after installation: {operation["path"]}')
    if operation['kind'] != 'git-hooks' and operation['before'] is not None:
        if fingerprint(Path(operation['backup'])) != operation['before']:
            raise ValueError(f'Backup changed: {operation["path"]}')


def rollback(receipt_path: Path) -> dict[str, Any]:
    """Restore inputs with a durable phase and quarantine for interrupted reversions.

    Every path is checked again immediately before mutation. The installed entry
    is renamed into the receipt rather than deleted; unexpected concurrent bytes
    remain recoverable even if a writer races the final fingerprint check.
    """
    receipt = json.loads(receipt_path.read_text())
    if receipt['status'] == 'reverted':
        return receipt
    for operation in receipt['operations']:
        if operation['status'] != 'reverted':
            _validate_restore(operation)
    for index in reversed(range(len(receipt['operations']))):
        operation = receipt['operations'][index]
        if operation['status'] == 'reverted':
            continue
        _validate_restore(operation)
        if _current(operation) != operation['before']:
            path = Path(operation['path'])
            if operation['kind'] == 'git-hooks':
                original = operation['before_values']
                if len(original) > 1:
                    raise ValueError('Cannot restore ambiguous multiple core.hooksPath values')
                operation['status'] = 'reverting'
                _save_receipt(receipt_path, receipt)
                _validate_restore(operation)
                _set_git_hooks(path, original, operation['after'],
                               receipt_path.parent / 'git-config-rollback' / str(index))
            else:
                restored = receipt_path.parent / 'restore' / str(index)
                retired = receipt_path.parent / 'retired' / str(index)
                if operation['before'] is not None and not restored.exists() and not restored.is_symlink():
                    _copy(Path(operation['backup']), restored)
                operation['status'] = 'reverting'
                _save_receipt(receipt_path, receipt)
                _validate_restore(operation)
                if path.exists() or path.is_symlink():
                    retired.parent.mkdir(parents=True, exist_ok=True)
                    if retired.exists() or retired.is_symlink():
                        raise ValueError(f'Unexpected occupied rollback quarantine: {retired}')
                    _move_install_entry(operation, path, retired)
                    if fingerprint(retired) != operation['after']:
                        if not path.exists() and not path.is_symlink():
                            _move_install_entry(operation, retired, path, restoring=True)
                        raise ValueError(f'Concurrent edit preserved during rollback: {path}')
                if operation['before'] is not None:
                    if path.exists() or path.is_symlink():
                        raise ValueError(f'Concurrent destination created during rollback: {path}')
                    _move_install_entry(operation, restored, path, restoring=True)
        operation['status'] = 'reverted'
        _save_receipt(receipt_path, receipt)
    receipt['status'] = 'reverted'
    _save_receipt(receipt_path, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    """Run installation preview, explicit apply, or guarded rollback."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--state-dir', type=Path)
    parser.add_argument('--client', choices=('all', 'copilot'), default='all',
                        help='Limit installation to Copilot personal entries, or install all clients')
    parser.add_argument('--copilot-home', type=Path,
                        default=Path(os.environ['COPILOT_HOME']) if os.environ.get('COPILOT_HOME') else None,
                        help='Copilot configuration directory (defaults to COPILOT_HOME or HOME/.copilot)')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--apply', action='store_true')
    action.add_argument('--rollback', type=Path)
    options = parser.parse_args(argv)
    if options.rollback:
        result = rollback(options.rollback)
        print(_json({'status': result['status'], 'receipt': str(options.rollback)}), end='')
    else:
        plan = build_plan(options.source, options.home, options.state_dir,
                          client=options.client, copilot_home=options.copilot_home)
        if options.apply:
            receipt = apply_plan(plan)
            print(_json({'status': 'installed', 'receipt': str(receipt), 'hook_trust': 'pending_native_review',
                         'claude_conflicts': plan.get('claude_conflicts', []),
                         'claude_domain_documents': plan.get('claude_domain_documents', []),
                         'copilot_conflicts': plan['copilot_conflicts'],
                         'copilot_native_status': plan['copilot_native_status'],
                         'retired_skill_links': plan['retired_skill_links'],
                         'skill_link_conflicts': plan['skill_link_conflicts']}), end='')
        else:
            print(_json({**plan, 'operations': [{k: v for k, v in op.items() if k != 'value'} for op in plan['operations']]}), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
