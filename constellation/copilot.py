"""Project shared roles into GitHub Copilot CLI's native discovery paths.

This module only prepares operations. The common installer owns writes,
receipts and rollback; Copilot owns execution, permissions and concurrency.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Mapping, Sequence
import unicodedata

from .install import AddOperation
from .platform_support import is_reparse


BEGIN = '<!-- BEGIN Constellation Copilot instructions -->'
END = '<!-- END Constellation Copilot instructions -->'
VISUAL_STUDIO_ROLE = '<!-- Constellation Visual Studio agent -->'
HOOK_EVENTS = ('sessionStart', 'subagentStart', 'preToolUse', 'agentStop', 'subagentStop')
READ_ONLY_ROLES = {
    'ecosystem_counterexample', 'ecosystem_reviewer',
    'ecosystem_security_reviewer', 'ecosystem_verifier',
}


def directory_trees_overlap(first: Path, second: Path) -> bool:
    """Check containment using existing directory identities and remaining paths.

    Args:
        first: Absolute directory path without parent-directory components.
        second: Another absolute directory path without parent components.

    Returns:
        Whether either location contains the other, including filesystem aliases
        and missing descendants. On macOS and Windows, Unicode normalization and
        case folding conservatively compare the remaining components; this may
        reject distinct names on a case-sensitive volume. Other platforms keep
        case-sensitive comparison. Actual paths remain unchanged for symlink
        checks and installation.

    Raises:
        ValueError: A path is relative, contains parent traversal, has a
            non-directory ancestor, or its existing ancestry cannot be inspected.
    """
    fold_case = sys.platform == 'darwin' or os.name == 'nt'

    def ancestor_suffixes(path: Path) -> dict[tuple[int, int], list[tuple[str, ...]]]:
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('Directory comparison requires absolute paths without parent traversal')
        locations: dict[tuple[int, int], list[tuple[str, ...]]] = {}
        for ancestor in (path, *path.parents):
            try:
                metadata = ancestor.stat()
            except FileNotFoundError:
                continue
            except OSError as error:
                raise ValueError(f'Cannot inspect directory ancestry: {ancestor}') from error
            if not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(f'Installation path has a non-directory ancestor: {ancestor}')
            suffix = path.relative_to(ancestor).parts
            if fold_case:
                suffix = tuple(unicodedata.normalize('NFC', part).casefold() for part in suffix)
            identity = (metadata.st_dev, metadata.st_ino)
            # Distinct spellings can reach the same ancestor through a firmlink,
            # mount or root alias. Keep every suffix without rewriting the path.
            locations.setdefault(identity, []).append(suffix)
        if not locations:
            raise ValueError(f'Installation path has no inspectable directory ancestor: {path}')
        return locations

    first_locations = ancestor_suffixes(first)
    second_locations = ancestor_suffixes(second)
    for identity in first_locations.keys() & second_locations.keys():
        for first_suffix in first_locations[identity]:
            for second_suffix in second_locations[identity]:
                common_length = min(len(first_suffix), len(second_suffix))
                if first_suffix[:common_length] == second_suffix[:common_length]:
                    return True
    return False


def agent_document(agent: Mapping[str, Any]) -> str:
    """Render one canonical role with Copilot's native tool restrictions.

    Args:
        agent: Canonical TOML definition containing name, description and body.

    Returns:
        A Markdown agent profile. Models and reasoning settings are inherited.

    Raises:
        ValueError: The role name cannot safely identify a native file.
    """
    name = agent['name']
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name):
        raise ValueError(f'Unsupported native agent name: {name}')
    tools = ['read', 'search', 'web_fetch']
    if name not in READ_ONLY_ROLES:
        tools.extend(['edit', 'execute', 'skill', 'agent'])
    return ('---\nname: ' + json.dumps(name)
            + '\ndescription: ' + json.dumps(agent['description'], ensure_ascii=False)
            + '\ntools: ' + json.dumps(tools)
            + '\nstrict-tools-list: true\ninclude-custom-instructions: true\n'
            + '---\n\n' + agent['developer_instructions'].strip() + '\n')


def hooks_document(source: Path, *, state_dir: Path | None = None) -> str:
    """Render local CLI hooks as executable arguments, without shell expansion.

    Args:
        source: Canonical checkout containing the shared command entry point.
        state_dir: Explicit private state selected for the installation.

    Returns:
        Version 1 hook configuration for the five integration events.
        This local configuration is not a cloud-agent deployment.
    """
    command = [str(source / 'constellation.py')]
    if state_dir is not None:
        command.extend(['--state-dir', str(state_dir)])
    hooks = {
        event: [{
            'type': 'command', 'exec': sys.executable,
            'args': [*command, 'hook', '--client', 'copilot', event],
            'timeoutSec': 10,
        }]
        for event in HOOK_EVENTS
    }
    return json.dumps({'version': 1, 'hooks': hooks}, indent=2) + '\n'


def instructions_document(text: str, source: Path) -> str:
    """Refresh our instruction block while retaining every user-owned byte.

    Args:
        text: Existing native user instructions, or empty when absent.
        source: Checkout containing the authoritative shared instructions.

    Returns:
        Instructions with a generated common body and a short native bootstrap.

    Raises:
        ValueError: Existing markers cannot identify one unambiguous owned block.
    """
    common = (source / 'instructions/AGENTS.md').read_text(encoding='utf-8').strip()
    bootstrap = (
        '\n\n## GitHub Copilot CLI\n\n'
        'Use the native task tool for independent parallel work. Assign exclusive '
        'paths, register the returned native identities before edits, and keep '
        'reviewers separate from authors. Inherit the session model and reasoning '
        'settings; respect the effective client and account concurrency limits. '
        'Hooks guard supported operations and remind the coordinator of pending '
        'work; they do not launch agents or certify correctness.\n\n'
        f'Read `{source / "profiles/copilot.md"}` for native discovery, hook '
        'limitations and the review workflow. User-level skills already shared '
        'through `~/.agents/skills` remain the canonical skills.\n'
    )
    return merge_instructions(text, common + bootstrap, BEGIN, END)


def merge_instructions(text: str, body: str, begin: str, end: str) -> str:
    """Refresh one owned Markdown block while preserving adjacent text and BOM.

    Args:
        text: Existing UTF-8 instruction text decoded with original newlines.
        body: Generated Markdown with LF line endings and a final newline.
        begin: Opening ownership marker.
        end: Closing ownership marker.

    Returns:
        Updated text using the existing file's line ending for the owned block.

    Raises:
        ValueError: The markers do not identify one unambiguous owned block.
    """
    if text.count(begin) != text.count(end) or text.count(begin) > 1:
        raise ValueError('Ambiguous Constellation Copilot instruction markers')
    newline = '\r\n' if '\r\n' in text else '\n'
    block = begin + newline + body.replace('\n', newline) + end
    if begin not in text:
        if not text.removeprefix('\ufeff') or text.endswith(newline * 2):
            separator = ''
        elif text.endswith(newline):
            separator = newline
        else:
            separator = newline * 2
        return text + separator + block + newline
    start = text.index(begin)
    finish = text.index(end)
    if finish < start:
        raise ValueError('Constellation Copilot instruction markers are reversed')
    return text[:start] + block + text[finish + len(end):]


def plan_entries(source: Path, home: Path, state_dir: Path,
                 agents: Sequence[Mapping[str, Any]], entries: Sequence[Mapping[str, Any]],
                 add: AddOperation, *, copilot_home: Path | None = None) -> dict[str, Any]:
    """Prepare native entries without replacing unrelated configuration.

    Args:
        source: Canonical checkout containing shared roles and skills.
        home: Owner of the shared personal skills directory.
        state_dir: Private runtime root used for generated adapters and receipts.
        agents: Validated canonical role definitions.
        entries: Preserved skill inventory.
        add: Common installer collector with expected input fingerprints.
        copilot_home: Explicit native home, otherwise ``home / '.copilot'``.

    Returns:
        Discovery paths, shared skill entries and conflicts that remain unchanged.
        No repository, authentication, model or permission settings are changed.

    Raises:
        ValueError: Native home contains parent traversal, overlaps source/state,
            or a core skill is missing.
    """
    native = (copilot_home or home / '.copilot').expanduser()
    # Reject traversal before lexical containment checks. Resolving this path
    # would hide user-managed symlinks that safe_path must leave untouched.
    if '..' in native.parts:
        raise ValueError('Copilot home cannot contain parent-directory components')
    native = native.absolute()
    for protected in (source, state_dir):
        if directory_trees_overlap(native, protected):
            raise ValueError('Copilot home must be separate from source and private state')
    copies = os.name == 'nt'
    generated = native if copies else state_dir / 'native/copilot'
    conflicts: list[dict[str, str]] = []
    links: list[str] = []
    skills: list[str] = []

    def preserve(path: Path, reason: str) -> None:
        conflicts.append({'path': str(path), 'reason': reason})

    def safe_path(path: Path, *, directory: bool = False) -> bool:
        for parent in reversed(path.parents):
            if is_reparse(parent):
                preserve(path, 'Native entry traverses a user-managed directory link')
                return False
            if parent.exists() and not parent.is_dir():
                preserve(path, f'Native parent is not a directory: {parent}')
                return False
        if copies and is_reparse(path):
            preserve(path, 'Native entry is a user-managed link or reparse point')
            return False
        if path.exists() and not (path.is_dir() if directory else path.is_file()) and not path.is_symlink():
            preserve(path, 'Native entry is not a regular file or managed link')
            return False
        return True

    def managed_link(path: Path, target: Path) -> bool:
        if not safe_path(path):
            return False
        if path.exists() or path.is_symlink():
            if not path.is_symlink() or (path.parent / os.readlink(path)).absolute() != target:
                preserve(path, 'Existing native entry is not this shared-source link')
                return False
        add(path, 'symlink', str(target))
        links.append(str(path))
        return True

    for agent in agents:
        filename = agent['name'] + '.agent.md'
        if copies:
            path = native / 'agents' / filename
            if not safe_path(path):
                continue
            if path.is_file() and VISUAL_STUDIO_ROLE.encode('utf-8') in path.read_bytes():
                preserve(path, 'Visual Studio owns this role; use a separate native agent directory')
                continue
            if add(path, 'managed-write', agent_document(agent)):
                links.append(str(path))
            continue
        target = generated / 'agents' / filename
        if not safe_path(target):
            continue
        if target.is_symlink():
            preserve(target, 'Generated role cannot replace a user-managed link')
            continue
        add(target, 'write', agent_document(agent))
        managed_link(native / 'agents' / filename, target)

    hook_target = native / 'hooks/constellation.json' if copies else generated / 'hooks.json'
    if safe_path(hook_target):
        if hook_target.is_symlink():
            preserve(hook_target, 'Generated hooks cannot replace a user-managed link')
        elif copies:
            if add(hook_target, 'managed-write', hooks_document(source, state_dir=state_dir)):
                links.append(str(hook_target))
        else:
            add(hook_target, 'write', hooks_document(source, state_dir=state_dir))
            managed_link(native / 'hooks/constellation.json', hook_target)

    instruction_path = native / 'copilot-instructions.md'
    if safe_path(instruction_path):
        if instruction_path.is_symlink():
            preserve(instruction_path, 'Native instructions is a user-managed symbolic link')
        else:
            content = instruction_path.read_bytes() if instruction_path.exists() else None
            current = content.decode('utf-8') if content is not None else ''
            add(instruction_path, 'write', instructions_document(current, source),
                expected_content=content)

    for row in entries:
        if row['group'] != 'core':
            continue
        target = source / row['destination']
        if not target.is_dir() or not (target / 'SKILL.md').is_file():
            raise ValueError(f'Missing canonical core skill: {target}')
        path = home / '.agents/skills' / row['name']
        # Copilot discovers the same personal directory as Codex. Only a missing
        # reference needs installation; conflicting personal skills keep ownership.
        if copies:
            if safe_path(path, directory=True) and add(path, 'managed-tree', str(target)):
                skills.append(str(path))
        elif managed_link(path, target):
            skills.append(str(path))

    return {
        'copilot_home': str(native), 'copilot_agent_directory': str(generated / 'agents'),
        'copilot_links': links, 'copilot_shared_skills': skills, 'copilot_conflicts': conflicts,
        'copilot_hook_events': list(HOOK_EVENTS),
        'copilot_native_status': 'native_execution_not_observed',
    }
