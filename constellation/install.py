"""Install native entry points with a private, reversible receipt.

Only native entries live in Codex, Claude, Copilot and project discovery directories. This module
never approves hook trust or changes model, authentication, or privacy settings.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from typing import Any, Mapping, Protocol, Sequence
import uuid

from .platform_support import (
    default_state_dir,
    git_executable,
    is_reparse,
    read_ledger_record,
    replace_ledger_record,
    secure_mkdir,
    validate_windows_lookup,
    verify_windows_private_entry,
    windows_copy_dacl,
    windows_dacl_fingerprint,
)
from .projects import load_projects, relocate_entries

BEGIN = '# BEGIN Constellation native entries'
END = '# END Constellation native entries'
CLIENTS = ('all', 'codex', 'claude', 'copilot', 'visual-studio')
UNREAD = object()


class AddOperation(Protocol):
    """Record a native install operation and optionally bind its observed input."""

    def __call__(self, path: Path, kind: str, value: str | None = None, *,
                 expected_content: object = UNREAD, project_root: Path | None = None) -> bool: ...


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def fingerprint(path: Path) -> str | None:
    """Hash bytes, modes, and links without following symbolic links."""
    if not path.exists() and not path.is_symlink():
        return None
    digest = hashlib.sha256()
    if os.name == 'nt' and is_reparse(path):
        raise ValueError(f'Cannot fingerprint a Windows reparse point: {path}')
    paths = [path]
    if path.is_dir() and not path.is_symlink():
        paths.extend(sorted(_tree_paths(path)))
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


def _tree_paths(root: Path) -> list[Path]:
    """Enumerate a tree without traversing a symbolic link or junction."""
    paths: list[Path] = []
    pending = [root]
    while pending:
        for child in pending.pop().iterdir():
            if os.name == 'nt' and is_reparse(child):
                raise ValueError(f'Cannot traverse a Windows reparse point: {child}')
            paths.append(child)
            if not child.is_symlink() and child.is_dir():
                pending.append(child)
    return paths


def _portable_path(path: Path) -> None:
    """Reject substituted directories, leaf links, and ambiguous destinations."""
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError(f'Installation path must be absolute and without traversal: {path}')
    if os.name == 'nt':
        validate_windows_lookup(path)
    for entry in reversed((path, *path.parents)):
        if entry.is_symlink() or is_reparse(entry):
            raise ValueError(f'Installation path traverses a link or reparse point: {entry}')
        if entry != path and entry.exists() and not entry.is_dir():
            raise ValueError(f'Installation parent is not a directory: {entry}')
    if path.is_file() and path.lstat().st_nlink > 1:
        raise ValueError(f'Installation path is a multiply linked file: {path}')


def _managed_entries(source: Path, state_dir: Path) -> dict[Path, Mapping[str, Any] | None]:
    """Return the latest recorded material and ACL ownership of each entry."""
    directory = state_dir / 'installations'
    _portable_path(directory)
    managed: dict[Path, Mapping[str, Any] | None] = {}
    receipts = []
    for path in directory.glob('*/receipt.json'):
        _portable_path(path)
        receipt = json.loads(read_ledger_record(path))
        if Path(receipt['source']) == source and receipt['status'] != 'reverted':
            receipts.append(receipt)
    for receipt in sorted(receipts, key=lambda row: row.get('created_ns', 0), reverse=True):
        for operation in receipt['operations']:
            if operation.get('managed') and operation['status'] != 'reverted':
                owner = None
                if receipt['status'] == 'installed' and operation['status'] == 'applied':
                    owner = operation
                managed.setdefault(Path(operation['path']), owner)
    return managed


def _windows_acl_snapshot(path: Path, *, tree: bool, private: bool = False) -> str:
    """Bind discretionary ACLs and owners without following aliases.

    A recovery object keeps its native ACL after a same-volume rename. Check
    every retained entry when private access is required, since protection at
    an ancestor alone does not prevent Windows traverse bypass.
    """
    paths = [path, *sorted(_tree_paths(path))] if tree else [path]
    fingerprints = {}
    for entry in paths:
        if private:
            verify_windows_private_entry(entry)
        fingerprints[entry.relative_to(path).as_posix()] = windows_dacl_fingerprint(entry)
    if not tree:
        return fingerprints['.']
    return hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode('utf-8')).hexdigest()


def _projected_files(source: Path, skill: Path) -> dict[Path, bytes]:
    """Read a skill tree and preserve Markdown links to shared source resources."""
    if not skill.is_relative_to(source / 'skills'):
        raise ValueError(f'Skill projection leaves the canonical skills directory: {skill}')
    _portable_path(skill)
    if (source / '.git').exists():
        from .git import _run

        output = _run(source, 'ls-files', '-z', '--', skill.relative_to(source).as_posix())
        paths = [source / os.fsdecode(name) for name in output.split(b'\0') if name]
    else:
        paths = [path for path in _tree_paths(skill) if not path.is_dir() or path.is_symlink()]
    files: dict[Path, bytes] = {}
    for path in sorted(paths):
        _portable_path(path)
        if not path.is_file():
            raise ValueError(f'Canonical skill resource is not a regular file: {path}')
        data = path.read_bytes()
        if path.suffix.lower() == '.md':
            def canonical_link(match: re.Match[str]) -> str:
                target = (path.parent / match.group()).resolve()
                if target.is_relative_to(source) and not target.is_relative_to(skill):
                    return target.as_uri()
                return match.group()

            text = re.sub(r'(?<=\]\()\.\.(?:/[^\s)#?]+)+', canonical_link, data.decode('utf-8'))
            data = text.encode('utf-8')
        files[path.relative_to(skill)] = data
    if Path('SKILL.md') not in files:
        raise ValueError(f'Missing canonical skill entry point: {skill}')
    return files


def _projection_digest(files: Mapping[Path, bytes]) -> str:
    """Bind each relative filename to the exact bytes installed for the skill."""
    entries = {name.as_posix(): hashlib.sha256(data).hexdigest() for name, data in files.items()}
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode('utf-8')).hexdigest()


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
        result += f'config_file = {json.dumps(str(agent["path"]), ensure_ascii=False)}\n'
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
                             add: AddOperation, project_directories: Mapping[Path, Path]) -> dict[str, Any]:
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
        project_directories: Expected Git owner for project discovery directories.

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
            project_root = project_directories.get(directory)
            if project_root is not None:
                verify_project_entry_owner(directory, project_root)
            ancestry = _skill_parent_identity(directory)
        except (OSError, ValueError) as error:
            conflicts.append({'path': str(directory),
                              'reason': f'Cannot retire skills in this directory: {error}'})
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
            add(path, 'remove', None, project_root=project_root)
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


def _powershell_command(argv: Sequence[str]) -> str:
    """Quote local paths literally and propagate the native hook exit code."""
    quoted = ["'" + value.replace("'", "''") + "'" for value in argv]
    return '& ' + ' '.join(quoted) + '; exit $LASTEXITCODE'


def _owned_codex_hook(handler: Mapping[str, Any], source: Path, home: Path) -> bool:
    """Identify previous output by exact script and action, irrespective of state root."""
    command = handler.get('command')
    if handler.get('type') != 'command' or not isinstance(command, str):
        return False
    if os.name == 'nt':
        argv = [argument.replace("''", "'") for argument in re.findall(r"'((?:[^']|'')*)'", command)]
        if not argv or _powershell_command(argv) != command:
            return False
    else:
        try:
            argv = shlex.split(command)
        except ValueError:
            return False
    if len(argv) < 2 or not Path(argv[0]).name.casefold().startswith(('python', 'py.')):
        return False
    target = Path(argv[1])
    if target == source / 'constellation.py':
        tail = argv[2:]
        if len(tail) >= 2 and tail[0] == '--state-dir':
            tail = tail[2:]
        return tail in (['hook', 'pre-tool'], ['hook', 'stop'])
    return target == home / '.codex/hooks/omaros_permission_guard.py'


def _codex_entries(source: Path, home: Path, state_dir: Path,
                   agents: list[dict[str, Any]], entries: list[dict[str, Any]],
                   projects: list[dict[str, Any]], add: AddOperation) -> dict[str, Any]:
    """Plan Codex settings and the shared skill discovery locations."""
    codex = home / '.codex'
    config = codex / 'config.toml'
    instructions = source / 'instructions/AGENTS.md'
    hooks_path = codex / 'hooks.json'
    if os.name == 'nt':
        for path in (config, hooks_path):
            _portable_path(path)
    config_bytes = config.read_bytes() if config.exists() else None
    config_text = config_bytes.decode('utf-8') if config_bytes is not None else ''
    add(config, 'write', _native_config(config_text, source, home, entries, agents),
        expected_content=config_bytes)
    if instructions.is_file():
        if os.name == 'nt':
            add(codex / 'AGENTS.md', 'managed-write', instructions.read_bytes().decode('utf-8'))
        else:
            add(codex / 'AGENTS.md', 'symlink', str(instructions))
    if os.name != 'nt':
        for path in (codex / 'agents').glob('*.toml'):
            data = tomllib.loads(path.read_text(encoding='utf-8'))
            if data.get('name') in {row['name'] for row in agents}:
                add(path, 'remove', None)

    hooks_bytes = hooks_path.read_bytes() if hooks_path.exists() else None
    hooks = json.loads(hooks_bytes) if hooks_bytes is not None else {'hooks': {}}
    hook_groups = hooks.setdefault('hooks', {})
    for event, groups in list(hook_groups.items()):
        retained = []
        for group in groups:
            handlers = [handler for handler in group.get('hooks', [])
                        if not _owned_codex_hook(handler, source, home)]
            if handlers:
                retained.append({**group, 'hooks': handlers})
        hook_groups[event] = retained
    argv = [sys.executable, str(source / 'constellation.py')]
    if state_dir != default_state_dir().resolve():
        argv.extend(['--state-dir', str(state_dir)])
    argv.append('hook')
    for event, action in [('PreToolUse', 'pre-tool'), ('Stop', 'stop')]:
        command = _powershell_command([*argv, action]) if os.name == 'nt' else shlex.join([*argv, action])
        handler = {'type': 'command', 'command': command, 'timeout': 10}
        if os.name == 'nt':
            handler['commandWindows'] = command
        hook_groups.setdefault(event, []).append({'hooks': [handler]})
    hooks['hooks'] = {event: groups for event, groups in hook_groups.items() if groups}
    add(hooks_path, 'write', _json(hooks), expected_content=hooks_bytes)
    core_names = {row['name'] for row in entries if row['group'] == 'core'}
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
            kind = 'managed-tree' if os.name == 'nt' else 'symlink'
            if add(destination, kind, str(target), project_root=root if group != 'core' else None):
                links.append(str(destination))
    return {'skill_links': links, 'preserved_variants': skipped_variants}


def _verify_git_root(root: Path) -> None:
    """Require an exact Git owner before planning or applying project payloads."""
    from .git import GitError, _run

    if os.name == 'nt':
        validate_windows_lookup(root)
    try:
        top = _run(root, 'rev-parse', '--show-toplevel')
    except GitError as error:
        raise ValueError(f'Project installation requires the exact Git owner: {root}') from error
    if Path(os.fsdecode(top.rstrip(b'\r\n'))).resolve() != root:
        raise ValueError(f'Project installation requires the exact Git owner: {root}')


def verify_project_entry_owner(path: Path, project_root: Path) -> None:
    """Reject project entries that cross into another Git owner or linked parent.

    Args:
        path: Scope entry below the known exact Git worktree root.
        project_root: Expected owner verified at the beginning of the operation.

    Raises:
        ValueError: The path escapes the scope or may belong to a nested checkout.
        OSError: Filesystem metadata cannot be inspected safely.
    """
    if not path.is_relative_to(project_root) or path == project_root:
        raise ValueError(f'Project entry must be below its declared Git owner: {path}')
    relative = path.relative_to(project_root)
    if any(part.casefold() in {'..', '.git'} for part in relative.parts):
        raise ValueError(f'Project entry traverses a parent or Git internals: {path}')
    current = project_root
    for part in relative.parts:
        current /= part
        if is_reparse(current):
            if current != path:
                raise ValueError(f'Project entry crosses a linked directory: {current}')
            # A symbolic-link leaf can be an explicitly managed legacy alias.
            break
        metadata = current / '.git'
        if current.is_dir() and (metadata.exists() or is_reparse(metadata)):
            raise ValueError(f'Project entry belongs to a nested Git worktree: {current}')


def _git_config(root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    """Read or change configuration without inheriting Git redirections."""
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    return subprocess.run([git_executable(project=root), '-C', str(root), 'config', *arguments],
                          capture_output=True, env=env, timeout=60, check=False)


def _effective_hooks(root: Path) -> dict[str, Any]:
    """Inspect Git's active configuration and executable hook files."""
    from .git import _run

    result = _git_config(root, '--null', '--path', '--get', 'core.hooksPath')
    if result.returncode not in (0, 1):
        raise ValueError(f'Cannot inspect effective Git hook configuration: {root}')
    configured = os.fsdecode(result.stdout.removesuffix(b'\0')) if result.returncode == 0 else None
    output = _run(root, 'rev-parse', '--path-format=absolute', '--git-path', 'hooks')
    directory = Path(os.fsdecode(output.rstrip(b'\r\n'))).resolve()
    if configured is not None:
        directory = (root / configured).resolve()
    active = sorted(
        entry.name for entry in directory.iterdir()
        if not entry.name.endswith('.sample') and not entry.name.startswith('.')
        and entry.is_file() and os.access(entry, os.X_OK)
    ) if directory.is_dir() else []
    return {'configured': configured, 'directory': str(directory), 'active': active}


def _git_entries(source: Path, projects: Sequence[Mapping[str, Any]],
                 operations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Plan Git installation while retaining unknown or unsupported hook paths."""
    skipped: list[str] = []
    conflicts: list[dict[str, str]] = []
    desired = source / 'git-hooks'
    for project in projects:
        root = Path(project['root'])
        if os.name == 'nt':
            skipped.append(str(root))
            continue
        before = _git_hooks(root)
        if len(before) > 1:
            raise ValueError(f'Ambiguous multiple core.hooksPath values: {root}')
        effective = _effective_hooks(root)
        active_directory = Path(effective['directory'])
        if active_directory == desired:
            continue
        chain = project.get('preserve_git_hook_chain') or []
        chain = [chain] if isinstance(chain, str) else chain
        approved = {(root / directory).resolve() for directory in chain}
        earlier = project.get('git_hooks_before')
        known = active_directory in approved or (earlier and active_directory == (root / earlier).resolve())
        if effective['configured'] is not None and not known:
            conflicts.append({'path': str(root), 'reason': 'Preserved an unregistered core.hooksPath'})
            continue
        active = set(effective['active'])
        if active and (active_directory not in approved or active - {'pre-commit', 'pre-push'}):
            conflicts.append({'path': str(root), 'reason': 'Preserved active Git hooks outside the supported chain'})
            continue
        operations[str(root / '.git/config:core.hooksPath')] = {
            'path': str(root), 'kind': 'git-hooks', 'value': str(desired),
            'before': _values_fingerprint(before), 'before_values': before,
            'effective_hooks_before': effective,
        }
    return {'git_hook_projects_skipped': skipped, 'git_hook_conflicts': conflicts}


def build_plan(source: Path, home: Path | None = None, state_dir: Path | None = None,
               *, client: str = 'all', copilot_home: Path | None = None,
               visual_studio_agent_dir: Path | None = None,
               project_root: Path | None = None) -> dict[str, Any]:
    """Describe native installation without changing files.

    Args:
        source: Canonical Constellation checkout.
        home: Native clients' home owner. Project mappings remain machine-local.
        state_dir: Private backup destination, outside source and project data.
        client: One native surface, or all command-line integrations.
        copilot_home: Explicit Copilot CLI directory when customized.
        visual_studio_agent_dir: Explicit Visual Studio personal agent directory.
        project_root: Exact Git repository for a Visual Studio workspace install.

    Returns:
        Planned operations with expected fingerprints and preserved conflicts.
    """
    if client not in CLIENTS:
        raise ValueError(f'Select an installation client from {", ".join(CLIENTS)}')
    visual_studio_options = int(visual_studio_agent_dir is not None) + int(project_root is not None)
    if client == 'visual-studio' and visual_studio_options != 1:
        raise ValueError('Visual Studio requires exactly one of --visual-studio-agent-dir or --project-root')
    if client != 'visual-studio' and visual_studio_options:
        raise ValueError('Visual Studio scope options require --client visual-studio')

    from .copilot import directory_trees_overlap, plan_entries as copilot_entries

    source = source.resolve()
    home = (home or Path.home()).expanduser().absolute()
    state_dir = (state_dir or default_state_dir(home)).expanduser().absolute()
    if os.name == 'nt' or client == 'visual-studio':
        _portable_path(home)
        _portable_path(state_dir)
    home, state_dir = home.resolve(), state_dir.resolve()
    if directory_trees_overlap(state_dir, source):
        raise ValueError('Installation receipts and source must use separate directory trees')
    install_project_payloads = client in {'all', 'codex', 'claude'}
    projects = load_projects(source, home, state_dir=state_dir) if install_project_payloads or project_root else []
    native_projects = [
        row for row in projects
        if install_project_payloads and row.get('management') == 'native' and Path(row['root']).exists()
    ]
    for row in native_projects:
        _verify_git_root(Path(row['root']))
    if any(directory_trees_overlap(state_dir, Path(row['root'])) for row in projects):
        raise ValueError('Installation receipts and registered projects must use separate directory trees')
    if project_root and directory_trees_overlap(state_dir, project_root.resolve()):
        raise ValueError('Installation receipts and the Visual Studio project must use separate directory trees')
    if project_root is not None:
        candidate_root = project_root.expanduser().absolute()
        _portable_path(candidate_root)
        _verify_git_root(candidate_root.resolve())
    if visual_studio_agent_dir is not None:
        agent_root = visual_studio_agent_dir.expanduser().resolve()
        if directory_trees_overlap(state_dir, agent_root) or directory_trees_overlap(source, agent_root):
            raise ValueError('Visual Studio agents must be separate from source and private state')
    if os.name == 'nt':
        visual_studio_scope = project_root or visual_studio_agent_dir
        if (visual_studio_scope is not None
                and visual_studio_scope.expanduser().absolute().drive.casefold() != state_dir.drive.casefold()):
            raise ValueError('Visual Studio scope and receipts must share a volume; select a private --state-dir on that volume')
    inventory = json.loads((source / 'resource-inventory.json').read_bytes())
    entries = relocate_entries(source, inventory['entries'], projects)
    agents = []
    for path in sorted((source / 'agents').glob('*.toml')):
        data = tomllib.loads(path.read_bytes().decode('utf-8'))
        for key in ('name', 'description', 'developer_instructions'):
            if not isinstance(data.get(key), str) or not data[key]:
                raise ValueError(f'Agent lacks {key}: {path}')
        agents.append({**data, 'path': path})
    if len(agents) != 8 or len({a['name'] for a in agents}) != 8:
        raise ValueError('Expected exactly eight distinct preserved agents')

    operations: dict[str, dict[str, Any]] = {}
    desired_links: dict[str, str] = {}
    conflicts: list[dict[str, str]] = []
    managed_entries: dict[Path, Mapping[str, Any] | None] | None = None

    def add(path: Path, kind: str, value: str | None = None, *,
            expected_content: object = UNREAD, project_root: Path | None = None) -> bool:
        """Accept an operation, or preserve a colliding portable native entry."""
        nonlocal managed_entries
        managed = kind in {'managed-write', 'managed-tree'}
        if kind == 'managed-write':
            kind = 'write'
        tree = kind == 'managed-tree'
        portable = managed or os.name == 'nt' or client == 'visual-studio'
        if project_root is not None:
            try:
                verify_project_entry_owner(path, project_root)
            except (OSError, ValueError) as error:
                conflicts.append({'path': str(path), 'reason': str(error)})
                return False
        if kind == 'symlink' and value is not None:
            desired_links[str(path)] = value
        if portable:
            try:
                _portable_path(path)
                if os.name == 'nt' and path.drive.casefold() != state_dir.drive.casefold():
                    raise ValueError(f'Destination and receipts must be on the same volume: {path}')
                if kind == 'write' and path.exists() and not path.is_file():
                    raise ValueError(f'Expected a regular file at the native destination: {path}')
            except ValueError as error:
                conflicts.append({'path': str(path), 'reason': str(error)})
                return False
        if managed:
            if managed_entries is None:
                managed_entries = _managed_entries(source, state_dir)
            if ((path in managed_entries and managed_entries[path] is None)
                    or (path.exists() and path not in managed_entries)):
                conflicts.append({'path': str(path), 'reason': 'Existing entry lacks a completed Constellation receipt'})
                return False
        try:
            current = fingerprint(path)
        except ValueError as error:
            if not managed:
                raise
            conflicts.append({'path': str(path), 'reason': str(error)})
            return False
        current_acl = None
        if os.name == 'nt' and current is not None:
            try:
                current_acl = _windows_acl_snapshot(path, tree=tree, private=True)
            except (OSError, ValueError) as error:
                conflicts.append({'path': str(path), 'reason': f'Cannot safely retain existing entry: {error}'})
                return False
        if managed and current is not None:
            owner = managed_entries.get(path) if managed_entries is not None else None
            if (owner is None or current != owner['after'] or current_acl != owner.get('after_acl')
                    or (os.name == 'nt' and tree and owner.get('acl_scope') != 'tree')):
                conflicts.append({'path': str(path), 'reason': 'Managed content or access changed since installation'})
                return False
        if expected_content is not UNREAD:
            actual_content = path.read_bytes() if path.exists() else None
            if actual_content != expected_content or fingerprint(path) != current:
                raise ValueError(f'Native write input changed while planning: {path}')
        if kind == 'symlink' and path.is_symlink() and os.readlink(path) == value:
            operations.pop(str(path), None)
            return True
        if kind == 'write' and path.is_file() and not path.is_symlink() and path.read_bytes() == value.encode('utf-8'):
            return True
        if kind == 'remove' and current is None:
            return True

        operation = {'path': str(path), 'kind': kind, 'value': value, 'before': current}
        if project_root is not None:
            operation['project_root'] = str(project_root)
        if portable:
            operation['portable'] = True
        if managed:
            operation['managed'] = True
        if os.name == 'nt':
            operation['acl_scope'] = 'tree' if tree else 'entry'
            operation['before_acl'] = current_acl
        if tree:
            files = _projected_files(source, Path(value))
            if current is not None and path.is_dir():
                native_paths = [entry for entry in _tree_paths(path) if entry.is_file()]
                if files.keys() == {entry.relative_to(path) for entry in native_paths} and all(
                    entry.read_bytes() == files[entry.relative_to(path)] for entry in native_paths
                ):
                    return True
            operation['projection'] = _projection_digest(files)
        elif kind == 'write':
            # Prior permissions and DACLs are retained across native replacement.
            private = path.name in {'config.toml', 'settings.json', 'settings.local.json'} or path.is_relative_to(state_dir)
            operation['mode'] = (stat.S_IMODE(path.stat().st_mode)
                                 if path.is_file() and not path.is_symlink()
                                 else 0o600 if private else 0o644)
        operations[str(path)] = operation
        return True

    result: dict[str, Any] = {
        'schema': 1, 'source': str(source), 'home': str(home), 'state_dir': str(state_dir), 'client': client,
        'agent_names': [row['name'] for row in agents], 'skill_links': [], 'preserved_variants': [],
        'hook_trust': 'pending_native_review', 'git_hook_projects_skipped': [], 'git_hook_conflicts': [],
        'retired_skill_links': [], 'skill_link_conflicts': [], 'install_conflicts': conflicts,
        'claude_conflicts': [], 'claude_domain_documents': [], 'copilot_conflicts': [],
    }
    discovery_directories: list[Path] = []
    if client in {'all', 'copilot'}:
        result.update(copilot_entries(source, home, state_dir, agents, entries, add,
                                      copilot_home=copilot_home))
        result['skill_links'] = result['copilot_shared_skills']
        discovery_directories.append(home / '.agents/skills')
    if client in {'all', 'codex'}:
        result.update(_codex_entries(source, home, state_dir, agents, entries, projects, add))
        discovery_directories.extend(root / '.agents/skills' for root in
                                     [home, *(Path(row['root']) for row in projects if row['management'] == 'native')])
    if client in {'all', 'claude'}:
        from .claude import plan_entries as claude_entries

        result.update(claude_entries(source, home, state_dir, projects, agents, entries, add,
                                     include_codex_docs=client == 'all'))
        discovery_directories.extend(root / '.claude/skills' for root in
                                     [home, *(Path(row['root']) for row in projects if row['management'] == 'native')])
    if client == 'all':
        result.update(_git_entries(source, native_projects, operations))
    if client == 'visual-studio':
        from .visual_studio import plan_entries as visual_studio_entries

        result.update(visual_studio_entries(source, home, agents, entries, add,
                                            agents_directory=visual_studio_agent_dir, project_root=project_root))
        result['hook_trust'] = 'no_visual_studio_hooks'
    if discovery_directories and os.name != 'nt':
        protected = {row['path'] for row in result['claude_conflicts'] + result['copilot_conflicts']}
        project_directories = {
            Path(row['root']) / folder: Path(row['root'])
            for row in native_projects for folder in ('.agents/skills', '.claude/skills')
        }
        result.update(_retire_stale_skill_links(
            source, discovery_directories, desired_links, protected, operations, add, project_directories))
    result['operations'] = list(operations.values())
    result['native_project_roots'] = list(dict.fromkeys([
        *(row['root'] for row in native_projects),
        *([str(project_root.expanduser().resolve())] if project_root is not None else []),
    ]))
    return result


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
    stream = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         prefix='.receipt-', dir=path.parent, delete=False)
    temporary = Path(stream.name)
    try:
        with stream:
            stream.write(_json(receipt))
            stream.flush()
            os.fsync(stream.fileno())
        replace_ledger_record(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _git_hooks(root: Path) -> list[str]:
    result = _git_config(root, '--null', '--local', '--get-all', 'core.hooksPath')
    if result.returncode not in (0, 1):
        raise ValueError(f'Cannot inspect Git hook configuration: {root}')
    return [os.fsdecode(value) for value in result.stdout.split(b'\0')[:-1]]


def _values_fingerprint(values: list[str]) -> str:
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def _current(operation: dict[str, Any]) -> str | None:
    _verify_skill_parent(operation)
    path = Path(operation['path'])
    if operation['kind'] == 'git-hooks':
        return _values_fingerprint(_git_hooks(path))
    if 'project_root' in operation:
        verify_project_entry_owner(path, Path(operation['project_root']))
    if operation.get('portable') or os.name == 'nt':
        _portable_path(path)
    return fingerprint(path)


def _matches_before(operation: Mapping[str, Any], path: Path, current: str | None) -> bool:
    """Check the material input and its Windows access policy when recorded."""
    return current == operation['before'] and _matches_acl(operation, path, 'before')


def _matches_after(operation: Mapping[str, Any], path: Path, current: str | None) -> bool:
    """Check a recovery or promoted entry against the installer output."""
    return current == operation['after'] and _matches_acl(operation, path, 'after')


def _matches_acl(operation: Mapping[str, Any], path: Path, phase: str) -> bool:
    """Match the appropriate Windows snapshot, including a partially applied merge."""
    if os.name != 'nt' or operation[phase] is None:
        return True
    tree = operation['kind'] == 'managed-tree'
    if tree and operation.get('acl_scope') != 'tree':
        return False
    expected = {operation.get(f'{phase}_acl')}
    if phase == 'after' and operation.get('retained_acl') is not None:
        # A merge retains the existing access policy after the staged file
        # reaches its native location. A stopped install can leave either ACL.
        expected.add(operation['retained_acl'])
    try:
        return _windows_acl_snapshot(path, tree=tree, private=True) in expected
    except (OSError, ValueError):
        return False


def _set_git_hooks(root: Path, values: list[str], expected: str, recovery_root: Path, *,
                   effective_before: Mapping[str, Any] | None = None) -> None:
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
        effective_before: Active hook configuration to preserve during installation.

    Raises:
        ValueError: The expected key or configuration bytes changed.
        FileExistsError: Another native Git writer holds the config lock.
    """
    if len(values) > 1:
        raise ValueError('A hook transaction accepts at most one value')
    from .git import _run

    _verify_git_root(root)
    output = _run(root, 'rev-parse', '--path-format=absolute', '--git-path', 'config')
    config = Path(os.fsdecode(output.rstrip(b'\r\n')))
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
        if effective_before is not None and _effective_hooks(root) != effective_before:
            raise ValueError(f'Active Git hooks changed before locked update: {root}')
        candidate.write_bytes(original)
        if values:
            result = _git_config(root, '--file', str(candidate), '--replace-all', 'core.hooksPath', values[0])
            if result.returncode:
                raise ValueError(f'Cannot prepare Git hook configuration: {root}')
        else:
            result = _git_config(root, '--file', str(candidate), '--unset-all', 'core.hooksPath')
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
    source = Path(plan['source'])
    state_dir = Path(plan['state_dir'])
    for root in plan.get('native_project_roots', ()):
        _verify_git_root(Path(root))
    for operation in plan['operations']:
        path = Path(operation['path'])
        if os.name == 'nt':
            if operation['kind'] in {'git-hooks', 'symlink'}:
                raise ValueError(f'Unsupported Windows installation operation for {path}')
            if path.drive.casefold() != state_dir.drive.casefold():
                raise ValueError(f'Destination and receipts must be on the same volume: {path}')
        if not _matches_before(operation, path, _current(operation)):
            raise ValueError(f'Installation input changed: {operation["path"]}')
        if 'effective_hooks_before' in operation and _effective_hooks(path) != operation['effective_hooks_before']:
            raise ValueError(f'Active Git hooks changed after planning: {path}')
    installations = state_dir / 'installations'
    directory = installations / f'{time.strftime("%Y%m%dT%H%M%S")}-{uuid.uuid4().hex[:8]}'
    if os.name == 'nt':
        for private in (state_dir, installations, directory):
            secure_mkdir(private)
    else:
        directory.mkdir(parents=True, mode=0o700)
        os.chmod(directory, 0o700)
    receipt_path = directory / 'receipt.json'
    receipt = {'schema': 1, 'source': plan['source'], 'created_ns': time.time_ns(), 'status': 'applying',
               'operations': [], 'hook_trust': plan.get('hook_trust', 'pending_native_review')}
    _save_receipt(receipt_path, receipt)
    try:
        for index, operation in enumerate(plan['operations']):
            path = Path(operation['path'])
            if not _matches_before(operation, path, _current(operation)):
                raise ValueError(f'Installation input changed: {path}')
            backup = directory / 'before' / str(index)
            staged = directory / 'staged' / str(index)
            staged.parent.mkdir(parents=True, exist_ok=True)
            if operation['kind'] == 'symlink':
                staged.symlink_to(operation['value'])
            elif operation['kind'] == 'write':
                staged.write_bytes(operation['value'].encode('utf-8'))
                os.chmod(staged, operation.get('mode', 0o600 if path.name == 'config.toml' else 0o644))
            elif operation['kind'] == 'managed-tree':
                files = _projected_files(source, Path(operation['value']))
                if _projection_digest(files) != operation['projection']:
                    raise ValueError(f'Canonical skill changed after planning: {operation["value"]}')
                for relative, data in files.items():
                    output = staged / relative
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(data)
            after = _values_fingerprint([operation['value']]) if operation['kind'] == 'git-hooks' else fingerprint(staged)
            entry = {**operation, 'backup': str(backup) if operation['before'] is not None else None, 'after': after, 'status': 'pending'}
            if os.name == 'nt' and after is not None:
                entry['after_acl'] = _windows_acl_snapshot(
                    staged, tree=operation['kind'] == 'managed-tree', private=True)
                if not operation.get('managed') and operation.get('before_acl') is not None:
                    entry['retained_acl'] = operation['before_acl']
            receipt['operations'].append(entry)
            _save_receipt(receipt_path, receipt)
            if operation['kind'] == 'git-hooks':
                _set_git_hooks(path, [operation['value']], operation['before'],
                               directory / 'git-config' / str(index),
                               effective_before=operation.get('effective_hooks_before'))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                if operation['before'] is not None:
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    _move_install_entry(operation, path, backup)
                    if not _matches_before(operation, backup, fingerprint(backup)):
                        if not path.exists() and not path.is_symlink():
                            _move_install_entry(operation, backup, path, restoring=True)
                        raise ValueError(f'Concurrent installation edit preserved: {path}')
                if operation['kind'] != 'remove':
                    _move_install_entry(operation, staged, path, restoring=True)
                    if os.name == 'nt' and operation['before'] is not None and not operation.get('managed'):
                        windows_copy_dacl(backup, path)
            if not _matches_after(entry, path, _current(operation)):
                raise ValueError(f'Installation verification failed: {path}')
            if 'effective_hooks_before' in operation:
                active_directory = Path(_effective_hooks(path)['directory'])
                if active_directory != Path(operation['value']).resolve():
                    raise ValueError(f'Another Git configuration overrides the installed hooks: {path}')
            if os.name == 'nt' and after is not None and not operation.get('managed'):
                entry['after_acl'] = _windows_acl_snapshot(path, tree=False, private=True)
                entry.pop('retained_acl', None)
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
    if 'project_root' in operation:
        verify_project_entry_owner(Path(operation['path']), Path(operation['project_root']))
    if operation.get('portable') or os.name == 'nt':
        _portable_path(source)
        _portable_path(destination)
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

    Darwin RENAME_EXCL, Linux RENAME_NOREPLACE, and Windows same-volume rename
    all reject an occupied destination. Unix descriptors anchor link retirement
    and restoration to the verified discovery parent.
    """
    if os.name == 'nt':
        if source_dir_fd is not None or destination_dir_fd is not None:
            raise ValueError('Directory-descriptor moves are unavailable on Windows')
        os.rename(source, destination)
        return
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
        raise RuntimeError('Atomic exclusive restore requires macOS, Linux, or Windows rename support')
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
    path = Path(operation['path'])
    current = _current(operation)
    if _matches_before(operation, path, current):
        return
    pending_gap = operation['status'] in ('pending', 'reverting') and current is None and operation.get('backup') and (Path(operation['backup']).exists() or Path(operation['backup']).is_symlink())
    if not pending_gap and not _matches_after(operation, path, current):
        raise ValueError(f'Refusing to overwrite changes after installation: {operation["path"]}')
    if operation['kind'] != 'git-hooks' and operation['before'] is not None:
        backup = Path(operation['backup'])
        if not _matches_before(operation, backup, fingerprint(backup)):
            raise ValueError(f'Backup changed: {operation["path"]}')


def rollback(receipt_path: Path) -> dict[str, Any]:
    """Restore inputs with a durable phase and quarantine for interrupted reversions.

    Every path is checked again immediately before mutation. The installed entry
    is renamed into the receipt rather than deleted; unexpected concurrent bytes
    remain recoverable even if a writer races the final fingerprint check.
    """
    receipt_path = receipt_path.expanduser().absolute()
    if os.name == 'nt':
        _portable_path(receipt_path)
        if receipt_path.name != 'receipt.json' or not receipt_path.is_file():
            raise ValueError('Select an existing installation receipt.json')
        secure_mkdir(receipt_path.parent)
    receipt = json.loads(read_ledger_record(receipt_path))
    if receipt['status'] == 'reverted':
        return receipt
    for owner in {operation['project_root'] for operation in receipt['operations']
                  if operation.get('status') != 'reverted' and 'project_root' in operation}:
        _verify_git_root(Path(owner))
    for operation in receipt['operations']:
        if operation['status'] != 'reverted':
            _validate_restore(operation)
    for index in reversed(range(len(receipt['operations']))):
        operation = receipt['operations'][index]
        if operation['status'] == 'reverted':
            continue
        _validate_restore(operation)
        path = Path(operation['path'])
        if not _matches_before(operation, path, _current(operation)):
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
                if operation['before'] is not None:
                    if os.name == 'nt':
                        # Restore the original object rather than copying bytes
                        # into a file whose inherited access would differ.
                        restored = Path(operation['backup'])
                    elif not restored.exists() and not restored.is_symlink():
                        _copy(Path(operation['backup']), restored)
                operation['status'] = 'reverting'
                _save_receipt(receipt_path, receipt)
                _validate_restore(operation)
                if path.exists() or path.is_symlink():
                    retired.parent.mkdir(parents=True, exist_ok=True)
                    if retired.exists() or retired.is_symlink():
                        raise ValueError(f'Unexpected occupied rollback quarantine: {retired}')
                    _move_install_entry(operation, path, retired)
                    if not _matches_after(operation, retired, fingerprint(retired)):
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
    parser.add_argument('--home', type=Path)
    parser.add_argument('--state-dir', type=Path, default=os.environ.get('CONSTELLATION_STATE_DIR'))
    parser.add_argument('--client', choices=CLIENTS, default='all',
                        help='Choose a native client, or all three CLI integrations (default)')
    parser.add_argument('--copilot-home', type=Path,
                        default=Path(os.environ['COPILOT_HOME']) if os.environ.get('COPILOT_HOME') else None,
                        help='Copilot configuration directory (defaults to COPILOT_HOME or HOME/.copilot)')
    visual_studio = parser.add_mutually_exclusive_group()
    visual_studio.add_argument('--visual-studio-agent-dir', type=Path,
                               help='Personal agents directory configured in Visual Studio')
    visual_studio.add_argument('--project-root', type=Path,
                               help='Exact Git repository for a Visual Studio workspace installation')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--apply', action='store_true')
    action.add_argument('--rollback', type=Path)
    options = parser.parse_args(argv)
    if options.rollback:
        if options.visual_studio_agent_dir or options.project_root:
            parser.error('Rollback selects its scope from the receipt')
        result = rollback(options.rollback)
        print(_json({'status': result['status'], 'receipt': str(options.rollback)}), end='')
    else:
        plan = build_plan(options.source, options.home, options.state_dir,
                          client=options.client, copilot_home=options.copilot_home,
                          visual_studio_agent_dir=options.visual_studio_agent_dir,
                          project_root=options.project_root)
        if options.apply:
            receipt = apply_plan(plan)
            report = {key: value for key, value in plan.items() if key.endswith(
                ('_conflicts', '_status', '_projects_skipped', '_domain_documents', '_skill_links')
            )}
            status = 'installed_with_conflicts' if any(
                value for key, value in report.items() if key.endswith('_conflicts')
            ) else 'installed'
            print(_json({'status': status, 'receipt': str(receipt), 'hook_trust': plan['hook_trust'],
                         **report}), end='')
        else:
            print(_json({**plan, 'operations': [{k: v for k, v in op.items() if k != 'value'} for op in plan['operations']]}), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
