"""Resolve canonical project policies against a machine's local checkout paths."""

from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping, Sequence

from .platform_support import IS_WINDOWS, default_state_dir, validate_windows_lookup


def _catalogue(source: Path) -> list[dict[str, Any]]:
    path = source / 'profiles/projects.json'
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    projects = data.get('projects') if isinstance(data, dict) else None
    if not isinstance(projects, list) or any(
            not isinstance(row, dict) or not isinstance(row.get('root'), str)
            or ('id' in row and not isinstance(row['id'], str)) for row in projects):
        raise ValueError(f'Expected project records with root paths in {path}')
    return projects


def _local_path(value: object, label: str) -> Path:
    if not isinstance(value, str):
        raise ValueError(f'{label} must be an absolute path on this machine')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError(f'{label} must be a native absolute path without parent traversal')
    return validate_windows_lookup(path) if IS_WINDOWS else path.resolve()


def _local_roots(home: Path | None, state_dir: Path | None) -> dict[str, Path]:
    override = os.environ.get('CONSTELLATION_PROJECTS_FILE')
    if override:
        path = _local_path(override, 'CONSTELLATION_PROJECTS_FILE')
    else:
        configured_state = os.environ.get('CONSTELLATION_STATE_DIR')
        root = state_dir if state_dir is not None else (
            Path(configured_state).expanduser() if configured_state else default_state_dir(home))
        path = root / 'projects.json'
        if IS_WINDOWS:
            validate_windows_lookup(path)
        if not path.exists() and not path.is_symlink():
            return {}
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if (not isinstance(data, dict) or set(data) != {'projects'}
            or not isinstance(data['projects'], dict)):
        raise ValueError(f'Expected a projects object mapping project IDs to local roots in {path}')
    return {name: _local_path(value, f'Root for {name!r} in {path}')
            for name, value in data['projects'].items()}


def _relocate_hook_path(value: str | None, old_root: str, new_root: Path) -> str | None:
    """Keep repository-owned validators when a checkout moves to another machine."""
    if not value:
        return value
    if PureWindowsPath(old_root).is_absolute():
        original_root = PureWindowsPath(old_root)
        original = PureWindowsPath(value)
    else:
        original_root = PurePosixPath(old_root)
        original = PurePosixPath(value)
    if original.is_absolute():
        if not original.is_relative_to(original_root):
            return None
        relative = original.relative_to(original_root)
        relocated = new_root.joinpath(*relative.parts)
        relocated = validate_windows_lookup(relocated) if IS_WINDOWS else relocated.resolve()
        return str(relocated) if relocated.is_relative_to(new_root) else None
    return value if not PureWindowsPath(value).anchor and '..' not in original.parts else None


def load_projects(source: Path, home: Path | None = None, *,
                  state_dir: Path | None = None) -> list[dict[str, Any]]:
    """Bind canonical project metadata to native absolute checkout paths.

    Args:
        source: Constellation checkout containing the canonical project catalog.
        home: Alternate local home for installer previews and custom installs.
        state_dir: Explicit state directory that contains the local registry.

    Returns:
        Project records with local root paths and the original privacy patterns.
        Paths unsupported on the current host are omitted unless locally mapped.
        Standalone source archives supply the library without a Git owner.

    Raises:
        ValueError: Local mappings contain an unknown ID, ambiguous root or
            invalid path.
    """
    source = validate_windows_lookup(source) if IS_WINDOWS else source.resolve()
    canonical = _catalogue(source)
    local = _local_roots(home, state_dir)
    unknown = local.keys() - {row.get('id') for row in canonical}
    if unknown:
        raise ValueError('Unknown project IDs in local registry: ' + ', '.join(sorted(unknown)))
    if local.get('constellation', source) != source:
        raise ValueError('The constellation project is bound to the current source checkout')
    projects: list[dict[str, Any]] = []
    occupied: set[Path] = set()
    for row in canonical:
        name = row.get('id')
        original = Path(row['root'])
        if name == 'constellation':
            metadata = source / '.git'
            if IS_WINDOWS:
                validate_windows_lookup(metadata)
            if not metadata.is_dir() and not metadata.is_file():
                continue
            root = source
        elif name in local:
            root = local[name]
        elif original.is_absolute():
            root = validate_windows_lookup(original) if IS_WINDOWS else original.resolve()
        else:
            continue
        if root in occupied:
            raise ValueError(f'Multiple Constellation projects use the same root: {root}')
        occupied.add(root)
        project = {**row, 'root': str(root)}
        if root != original:
            project.pop('filesystem_identity', None)
            if 'git_hooks_before' in row:
                project['git_hooks_before'] = _relocate_hook_path(row['git_hooks_before'], row['root'], root)
            chain = row.get('preserve_git_hook_chain')
            if isinstance(chain, list):
                relocated_chain = []
                for entry in chain:
                    relocated = _relocate_hook_path(entry, row['root'], root)
                    if relocated:
                        relocated_chain.append(relocated)
                project['preserve_git_hook_chain'] = relocated_chain
            elif chain:
                project['preserve_git_hook_chain'] = _relocate_hook_path(chain, row['root'], root)
        projects.append(project)
    return projects


def relocate_entries(source: Path, entries: Sequence[Mapping[str, Any]],
                     projects: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Resolve each inventory skill's historic owner through its project ID.

    Args:
        source: Checkout containing the canonical project catalog.
        entries: Skill inventory records, whose source paths are kept intact.
        projects: Project records already bound to native roots.

    Returns:
        A copy of the inventory with project destinations bound to local roots.
    """
    roots = {row['id']: row['root'] for row in projects if 'id' in row}
    canonical_ids = {row['root']: row['id'] for row in _catalogue(source) if 'id' in row}
    relocated = []
    for entry in entries:
        owner = entry.get('project_root')
        if owner in canonical_ids and canonical_ids[owner] in roots:
            owner = roots[canonical_ids[owner]]
        elif owner is not None and not Path(owner).is_absolute():
            owner = None
        relocated.append({**entry, 'project_root': owner})
    return relocated
