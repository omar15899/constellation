"""Project shared resources into Claude's native discovery paths.

Only operations are prepared here. The existing install transaction owns writes
and recovery. Client settings, sessions, provider plugins and synced skills keep
their native ownership; generated agent documents are disposable adapters.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shlex
import sys
from typing import Any, Mapping, Sequence

from .install import AddOperation, verify_project_entry_owner
from .platform_support import is_reparse


BEGIN = '<!-- BEGIN Constellation native imports -->'
END = '<!-- END Constellation native imports -->'


def agent_document(agent: Mapping[str, Any]) -> str:
    """Render Claude Markdown from the canonical role without model overrides.

    Args:
        agent: Parsed canonical agent with name, description and instructions.

    Returns:
        A native frontmatter document using the unchanged role body.

    Raises:
        ValueError: A role name cannot safely identify one Markdown file.
    """
    name = agent['name']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
        raise ValueError(f'Unsupported native agent name: {name}')
    return ('---\nname: ' + json.dumps(name, ensure_ascii=False)
            + '\ndescription: ' + json.dumps(agent['description'], ensure_ascii=False)
            + '\n---\n\n' + agent['developer_instructions'].strip() + '\n')


def _owned_hook(handler: Mapping[str, Any], source: Path) -> bool:
    """Recognize only direct invocations of this source's two shared hooks."""
    if handler.get('type') != 'command' or not isinstance(handler.get('command'), str):
        return False
    arguments = handler.get('args')
    if arguments is None:
        try:
            argv = shlex.split(handler['command'])
        except ValueError:
            return False
    elif isinstance(arguments, list) and all(isinstance(value, str) for value in arguments):
        argv = [handler['command'], *arguments]
    else:
        return False
    if len(argv) == 6 and argv[2] == '--state-dir' and Path(argv[3]).is_absolute():
        argv = [*argv[:2], *argv[4:]]
    # Shell pipelines, wrappers and similar filenames are not ours to remove.
    return (len(argv) == 4 and Path(argv[0]).name.casefold().startswith('python')
            and Path(argv[1]) == source / 'constellation.py'
            and argv[2] == 'hook' and argv[3] in {'pre-tool', 'stop'})


def settings_document(text: str, source: Path, *, global_hooks: bool,
                      state_dir: Path | None = None) -> str:
    """Merge shared hooks while preserving unrelated native settings.

    Args:
        text: Existing JSON settings, or empty for a new user file.
        source: Canonical Constellation checkout.
        global_hooks: Install handlers in user scope when true; otherwise remove
            only exact inherited duplicates from project scope.
        state_dir: Explicit private state selected for generated hooks.

    Returns:
        Original text for a semantic no-op, otherwise complete JSON settings.

    Raises:
        ValueError: The native settings or hook structures are malformed.
    """
    decoded = text.removeprefix('\ufeff')
    original = json.loads(decoded) if decoded else {}
    if not isinstance(original, dict):
        raise ValueError('Claude settings must contain a JSON object')
    updated = deepcopy(original)
    groups = updated.get('hooks', {})
    if not isinstance(groups, dict):
        raise ValueError('Claude hooks must contain an event map')
    for event, configured in list(groups.items()):
        if not isinstance(configured, list):
            raise ValueError(f'Claude hook event must contain groups: {event}')
        retained = []
        for group in configured:
            if not isinstance(group, dict) or not isinstance(group.get('hooks'), list):
                raise ValueError(f'Claude hook group is malformed: {event}')
            handlers = group['hooks']
            if not all(isinstance(handler, dict) for handler in handlers):
                raise ValueError(f'Claude hook handler is malformed: {event}')
            remaining = [handler for handler in handlers if not _owned_hook(handler, source)]
            if remaining or remaining == handlers:
                retained.append({**group, 'hooks': remaining})
        if retained:
            groups[event] = retained
        else:
            groups.pop(event, None)
    if global_hooks:
        command = [str(source / 'constellation.py')]
        if state_dir is not None:
            command.extend(['--state-dir', str(state_dir)])
        for event, action in [('PreToolUse', 'pre-tool'), ('Stop', 'stop')]:
            handler: dict[str, Any] = {
                'type': 'command', 'command': sys.executable,
                'args': [*command, 'hook', action],
                'timeout': 10,
            }
            if event == 'PreToolUse':
                handler['onFailure'] = 'block'
            groups.setdefault(event, []).append({'hooks': [handler]})
    if groups:
        updated['hooks'] = groups
    elif 'hooks' in updated and original.get('hooks'):
        updated.pop('hooks')
    if updated == original:
        return text
    newline = '\r\n' if '\r\n' in text else '\n'
    bom = '\ufeff' if text.startswith('\ufeff') else ''
    return bom + json.dumps(updated, ensure_ascii=False, indent=2).replace('\n', newline) + newline


def _imports(text: str, paths: Sequence[Path]) -> str:
    """Replace only our delimited imports, retaining all domain-owned prose."""
    if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
        raise ValueError('Ambiguous Constellation native import markers')
    bom = '\ufeff' if text.startswith('\ufeff') else ''
    text = text.removeprefix('\ufeff')
    newline = '\r\n' if '\r\n' in text else '\n'
    if BEGIN in text:
        start = text.index(BEGIN)
        finish = text.index(END, start) + len(END)
        following = text[finish:].removeprefix(newline)
        if start == 0:
            following = following.removeprefix(newline)
        content = text[:start] + following
    else:
        content = text
    # Claude imports accept absolute paths and require escaping every space.
    rendered = ['@' + path.as_posix().replace(' ', '\\ ') for path in paths]
    existing = set(content.splitlines())
    required = [line for line in rendered if line not in existing]
    if not required:
        return bom + content
    block = newline.join([BEGIN, *required, END, ''])
    return bom + block + (newline + content if content else '')


def _central_link(path: Path, roots: Sequence[Path]) -> bool:
    """Identify a link whose destination belongs to shared resources."""
    if not path.is_symlink():
        return False
    target = (path.parent / os.readlink(path)).resolve()
    return any(target.is_relative_to(root.resolve()) for root in roots)


def plan_entries(source: Path, home: Path, state_dir: Path,
                 projects: Sequence[Mapping[str, Any]], agents: Sequence[Mapping[str, Any]],
                 entries: Sequence[Mapping[str, Any]], add: AddOperation, *,
                 include_codex_docs: bool = True) -> dict[str, Any]:
    """Prepare Claude references without claiming unrelated client files.

    Args:
        source: Canonical checkout containing the agent and skill definitions.
        home: Native clients' home owner.
        state_dir: Private runtime root for generated adapters.
        projects: Registered owners; external and missing roots stay untouched.
        agents: Eight already validated canonical agent definitions.
        entries: Skill inventory with ownership and source paths.
        add: Installer collector recording expected input fingerprints.
        include_codex_docs: Maintain the Codex shared reference when it is part
            of the selected installation.

    Returns:
        Discovery paths, preserved conflicts and domain documents for review.
        Conflicts remain unmodified; callers must not claim full parity.
    """
    conflicts: list[dict[str, str]] = []
    documents: list[str] = []
    links: list[str] = []
    native_projects = [project for project in projects
                       if project.get('management') == 'native' and Path(project['root']).exists()]
    native_roots = {Path(project['root']).resolve(): Path(project['root']) for project in native_projects}
    copies = os.name == 'nt'
    native_agents = home / '.claude/agents'
    generated = native_agents if copies else state_dir / 'native/claude/agents'
    owned_agents = [source / 'resources/native-claude-agents', generated]

    def preserve(path: Path, reason: str) -> None:
        conflict = {'path': str(path), 'reason': reason}
        if conflict not in conflicts:
            conflicts.append(conflict)

    def safe_parent(path: Path, *, project_root: Path | None = None) -> bool:
        for parent in reversed(path.parents):
            if is_reparse(parent):
                preserve(path, 'Native entry traverses a user-managed directory link')
                return False
            if parent.exists() and not parent.is_dir():
                preserve(path, f'Native parent is not a directory: {parent}')
                return False
        if project_root is not None:
            try:
                verify_project_entry_owner(path, project_root)
            except (OSError, ValueError) as error:
                preserve(path, str(error))
                return False
        return True

    def native_resource(path: Path, target: Path, owned: Sequence[Path], *,
                        project_root: Path | None = None) -> bool:
        if not safe_parent(path, project_root=project_root):
            return False
        if copies:
            if target.is_dir():
                accepted = add(path, 'managed-tree', str(target), project_root=project_root)
            else:
                accepted = add(path, 'managed-write', target.read_bytes().decode('utf-8'), project_root=project_root)
            if not accepted:
                return False
            links.append(str(path))
            return True
        if path.exists() or path.is_symlink():
            if not _central_link(path, owned):
                preserve(path, 'Existing native entry is not a shared-source link')
                return False
        if not add(path, 'symlink', str(target), project_root=project_root):
            return False
        links.append(str(path))
        return True

    for agent in agents:
        filename = agent['name'] + '.md'
        target = generated / filename
        if copies:
            inherited = safe_parent(target) and add(target, 'managed-write', agent_document(agent))
            if inherited:
                links.append(str(target))
        else:
            add(target, 'write', agent_document(agent))
            inherited = native_resource(native_agents / filename, target, owned_agents)
        # User agents are inherited; keep only one native entry per shared role.
        for project in native_projects:
            root = Path(project['root'])
            local = root / '.claude/agents' / filename
            if not safe_parent(local, project_root=root):
                continue
            if not copies and _central_link(local, owned_agents):
                if inherited:
                    add(local, 'remove', None, project_root=root)
                else:
                    preserve(local, 'Shared project role retained because its global entry conflicts')
            elif local.exists() or is_reparse(local):
                preserve(local, 'Project agent shadows the inherited shared role')

    settings = home / '.claude/settings.json'
    inherited_hooks = False
    if not safe_parent(settings):
        pass
    elif is_reparse(settings):
        preserve(settings, 'Native settings is a user-managed symbolic link')
    else:
        content = settings.read_bytes() if settings.exists() else None
        rendered = settings_document(content.decode('utf-8') if content is not None else '',
                                     source, global_hooks=True, state_dir=state_dir)
        enabled = json.loads(rendered.removeprefix('\ufeff')).get('disableAllHooks') is not True
        inherited_hooks = add(settings, 'write', rendered, expected_content=content) and enabled
        if not enabled:
            preserve(settings, 'Native disableAllHooks prevents shared hook execution')
    instruction_paths = [source / 'instructions/AGENTS.md']
    if (source / 'profiles/claude.md').is_file():
        instruction_paths.append(source / 'profiles/claude.md')
        native_resource(home / '.claude/README.md', source / 'profiles/claude.md',
                        [source / 'profiles'])
    instructions = home / '.claude/CLAUDE.md'
    if not safe_parent(instructions):
        pass
    elif is_reparse(instructions):
        preserve(instructions, 'Native instructions is a user-managed symbolic link')
    else:
        content = instructions.read_bytes() if instructions.exists() else None
        current = content.decode('utf-8') if content is not None else ''
        add(instructions, 'write', _imports(current, instruction_paths), expected_content=content)
    for project in native_projects:
        root = Path(project['root'])
        for name in ('settings.json', 'settings.local.json'):
            path = root / '.claude' / name
            if not safe_parent(path, project_root=root):
                continue
            if is_reparse(path):
                preserve(path, 'Project settings is a user-managed symbolic link')
            elif path.is_file() and inherited_hooks:
                content = path.read_bytes()
                replacement = settings_document(content.decode('utf-8'), source, global_hooks=False)
                add(path, 'write', replacement, expected_content=content, project_root=root)
        profile = project.get('profile')
        # Source instructions are authored/reviewed source, not install outputs.
        if profile and root != source:
            path = root / 'CLAUDE.md'
            if not safe_parent(path, project_root=root):
                continue
            if is_reparse(path):
                preserve(path, 'Project instructions is a user-managed symbolic link')
            else:
                content = path.read_bytes() if path.exists() else None
                current = content.decode('utf-8') if content is not None else ''
                replacement = _imports(current, [source / profile])
                accepted = add(path, 'write', replacement, expected_content=content, project_root=root)
                if accepted and replacement != current and current.strip():
                    documents.append(str(path))

    core = {row['name']: source / row['destination'] for row in entries if row['group'] == 'core'}
    inherited_core = {name: native_resource(home / '.claude/skills' / name, target, [source / 'skills'])
                      for name, target in core.items()}
    desired: dict[Path, tuple[Path, Path]] = {}
    # A core shadow need not be in the preserved inventory: historical wrapper
    # directories also mask the inherited shared method and must be reported.
    for project in native_projects:
        root = Path(project['root'])
        for name in core:
            local = root / '.claude/skills' / name
            if not safe_parent(local, project_root=root):
                continue
            if not copies and _central_link(local, [source / 'skills']):
                if inherited_core[name]:
                    add(local, 'remove', None, project_root=root)
                else:
                    preserve(local, 'Shared project skill retained because its global entry conflicts')
            elif local.exists() or is_reparse(local):
                preserve(local, 'Project skill shadows the inherited core skill')
    for row in entries:
        name, group = row['name'], row['group']
        if group == 'core':
            continue
        if group == 'workspace':
            roots = [Path(project['root']) for project in native_projects
                     if project.get('id') != 'omaros' and Path(project['root']) != source]
        elif row.get('project_root') and Path(row['project_root']).resolve() in native_roots:
            roots = [native_roots[Path(row['project_root']).resolve()]]
        else:
            roots = []
            if row.get('project_root'):
                preserve(Path(row['project_root']) / '.claude/skills' / name,
                         'Inventory skill owner is missing, external or unregistered')
        for root in roots:
            local = root / '.claude/skills' / name
            if name in core:
                continue
            # Inventory order prefers project-owned versions to later workspace
            # fallbacks, consistently with the existing Codex discovery policy.
            desired.setdefault(local, (source / row['destination'], root))
    for path, (target, root) in desired.items():
        native_resource(path, target, [source / 'skills'], project_root=root)

    documentation_tool = source / 'resources/automations/official_docs.py'
    if not copies and documentation_tool.is_file():
        clients = ('.claude', '.codex') if include_codex_docs else ('.claude',)
        for client in clients:
            path = home / client / 'tools/official_docs.py'
            if not safe_parent(path):
                continue
            if (not path.exists() and not path.is_symlink()) or _central_link(
                    path, [source / 'resources/automations']):
                add(path, 'symlink', str(documentation_tool))
            elif path.is_file() and not path.is_symlink() and path.read_bytes() == documentation_tool.read_bytes():
                add(path, 'symlink', str(documentation_tool))
            else:
                preserve(path, 'Local documentation tool differs from the shared implementation')
    return {'claude_links': links, 'claude_conflicts': conflicts,
            'claude_domain_documents': documents, 'claude_agent_directory': str(generated)}
