"""Plan GitHub Copilot Chat resources for Microsoft Visual Studio on Windows."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Sequence

from .copilot import (
    READ_ONLY_ROLES,
    VISUAL_STUDIO_ROLE,
    directory_trees_overlap,
    merge_instructions,
)
from .install import AddOperation, verify_project_entry_owner
from .platform_support import git_executable, is_reparse, validate_windows_lookup


BEGIN = '<!-- BEGIN Constellation Visual Studio instructions -->'
END = '<!-- END Constellation Visual Studio instructions -->'


def agent_document(agent: Mapping[str, Any]) -> str:
    """Render a canonical agent for Visual Studio's tool names and picker.

    Args:
        agent: Validated role containing its name, description and instructions.

    Returns:
        Native Markdown inheriting the model selected in Copilot Chat. Review
        roles request only the documented read and search tools.

    Raises:
        ValueError: The role name cannot safely identify a native file.
    """
    name = agent['name']
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name):
        raise ValueError(f'Unsupported Visual Studio agent name: {name}')
    header = ['---', 'name: ' + json.dumps(name),
              'description: ' + json.dumps(agent['description'], ensure_ascii=False)]
    if name in READ_ONLY_ROLES:
        header.append('tools: ["code_search", "readfile"]')
    return '\n'.join([*header, '---', '', VISUAL_STUDIO_ROLE, '',
                      agent['developer_instructions'].strip(), ''])


def _target_directory(path: Path, source: Path) -> Path:
    """Validate an explicit native scope before reading anything from it."""
    path = path.expanduser()
    if '..' in path.parts or any(part.casefold() == '.git' for part in path.parts):
        raise ValueError(f'Visual Studio target cannot traverse parent or Git internals: {path}')
    if path.anchor and not path.is_absolute():
        raise ValueError(f'Visual Studio target cannot use a drive-relative or root-relative path: {path}')
    path = path.absolute()
    if os.name == 'nt':
        validate_windows_lookup(path)
    for parent in (*reversed(path.parents), path):
        if is_reparse(parent):
            raise ValueError(f'Visual Studio target traverses a symbolic link or reparse point: {parent}')
        if parent.exists() and not parent.is_dir():
            raise ValueError(f'Visual Studio target requires a directory: {parent}')
    if directory_trees_overlap(path, source):
        raise ValueError('Visual Studio target must be outside the Constellation source checkout')
    return path


def _verify_repository(root: Path) -> None:
    """Require the exact root of a Git worktree before creating .github files."""
    environment = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith('GIT_')}
    result = subprocess.run([git_executable(project=root), '-C', str(root), 'rev-parse', '--show-toplevel'],
                            capture_output=True, env=environment, check=False)
    if (result.returncode != 0 or not result.stdout
            or Path(os.fsdecode(result.stdout.rstrip(b'\r\n'))).resolve() != root.resolve()):
        raise ValueError(f'Visual Studio project must name the exact root of a Git worktree: {root}')


def plan_entries(source: Path, home: Path, agents: Sequence[Mapping[str, Any]],
                 entries: Sequence[Mapping[str, Any]], add: AddOperation, *,
                 agents_directory: Path | None = None,
                 project_root: Path | None = None) -> dict[str, Any]:
    """Prepare Visual Studio discovery files in one explicitly selected scope.

    Args:
        source: Canonical Constellation checkout.
        home: User profile for personal instructions and skills.
        agents: Canonical agent definitions.
        entries: Canonical skill inventory with locally resolved project owners.
        add: Installer callback recording ownership, expected bytes and conflicts.
        agents_directory: Personal agent path selected in Visual Studio settings.
        project_root: Exact Git worktree root for a repository-local installation.

    Returns:
        Planned native paths, conflicts and the status of IDE verification.

    Raises:
        ValueError: A scope is missing, overlapping, linked, or outside the
            declared Git owner, or a canonical role or skill is invalid.
    """
    if (agents_directory is None) == (project_root is None):
        raise ValueError('Select either --project-root or --visual-studio-agent-dir')
    if project_root is not None:
        project_root = _target_directory(project_root, source)
        _verify_repository(project_root)
        native = project_root / '.github'
        agents_directory = native / 'agents'
        skills_directory = native / 'skills'
        instructions_path = native / 'copilot-instructions.md'
    else:
        assert agents_directory is not None
        agents_directory = _target_directory(agents_directory, source)
        skills_directory = home / '.agents/skills'
        instructions_path = home / 'copilot-instructions.md'

    conflicts: list[dict[str, str]] = []
    installed_agents: list[str] = []
    installed_skills: list[str] = []

    def safe_entry(path: Path, *, directory: bool = False) -> bool:
        for parent in reversed(path.parents):
            if is_reparse(parent) or (parent.exists() and not parent.is_dir()):
                conflicts.append({'path': str(path), 'reason': f'Unsafe native parent: {parent}'})
                return False
        expected_kind = path.is_dir if directory else path.is_file
        if is_reparse(path) or (path.exists() and not expected_kind()):
            conflicts.append({'path': str(path), 'reason': 'Existing native path has an incompatible type'})
            return False
        if project_root is not None:
            try:
                verify_project_entry_owner(path, project_root)
            except (OSError, ValueError) as error:
                conflicts.append({'path': str(path), 'reason': str(error)})
                return False
        return True

    for agent in agents:
        rendered = agent_document(agent)
        path = agents_directory / (agent['name'] + '.agent.md')
        if not safe_entry(path):
            continue
        if path.is_file() and b'strict-tools-list: true' in path.read_bytes():
            conflicts.append({'path': str(path), 'reason': 'Existing role uses the Copilot CLI tool schema'})
            continue
        if add(path, 'managed-write', rendered, project_root=project_root):
            installed_agents.append(str(path))

    general_skills = {row['name'] for row in entries if row['group'] == 'core'}
    handled_skills: set[str] = set()
    for row in entries:
        name = row['name']
        owner = row.get('project_root')
        if row['group'] != 'core' and (
                name in general_skills or not owner or Path(owner) != project_root):
            continue
        if name in handled_skills:
            continue
        handled_skills.add(name)
        target = source / row['destination']
        if not (target / 'SKILL.md').is_file():
            raise ValueError(f'Missing canonical skill: {target}')
        path = skills_directory / name
        if safe_entry(path, directory=True) and add(path, 'managed-tree', str(target), project_root=project_root):
            installed_skills.append(str(path))

    instructions = None
    if safe_entry(instructions_path):
        content = instructions_path.read_bytes() if instructions_path.exists() else None
        text = content.decode('utf-8') if content is not None else ''
        body = (
            '## Constellation in GitHub Copilot Chat\n\n'
            'Read the repository instructions and select the appropriate Constellation role '
            'and skills. Respect the active Visual Studio tool, confirmation and trust settings.\n\n'
            'Make the smallest complete change with readable code. Start with static inspection '
            'and keep any required test work focused on the affected behavior.\n\n'
            'For registered projects, use the Constellation terminal workflow to record '
            'contracts, checks and independent review. Record execution identities returned '
            'by the native client. If the current session cannot provide a required identity, '
            'leave that step pending for a client that provides it.\n'
        )
        if project_root is None:
            common = (source / 'instructions/AGENTS.md').read_text(encoding='utf-8').strip()
            body = common + '\n\n' + body
        replacement = merge_instructions(text, body, BEGIN, END)
        if add(instructions_path, 'write', replacement, expected_content=content, project_root=project_root):
            instructions = str(instructions_path)

    return {
        'visual_studio_agent_directory': str(agents_directory),
        'visual_studio_agents': installed_agents,
        'visual_studio_skills': installed_skills,
        'visual_studio_instructions': instructions,
        'visual_studio_conflicts': conflicts,
        'visual_studio_native_status': 'native_execution_not_observed',
    }
