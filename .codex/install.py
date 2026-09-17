#!/usr/bin/env python3
"""Install this repository's Git guards without changing global Codex settings."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def install(root: Path) -> dict[str, str]:
    root = root.resolve()
    if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
        raise ValueError('Install from the repository root, not a parent or child repository.')
    target = root / '.codex/git-hooks'
    for part in (root / '.codex', target):
        if part.is_symlink() or not part.is_dir():
            raise ValueError('Git guard directory must be a regular local directory.')
    guards = [target / event for event in ('pre-commit', 'post-commit', 'pre-push')]
    if any(path.is_symlink() or not path.is_file() for path in guards):
        raise ValueError('All three Git guards must be regular local files.')
    configured = subprocess.run(['git', 'config', '--get', 'core.hooksPath'], cwd=root,
                                capture_output=True, text=True)
    if configured.returncode not in (0, 1):
        raise ValueError('Cannot determine existing Git hook configuration.')
    previous = configured.stdout.strip()
    hooks = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'hooks'))
    if hooks.resolve() != target.resolve():
        occupied = [p for p in hooks.glob('*') if not p.name.endswith('.sample')]
        if occupied:
            raise ValueError('Existing Git hooks would be replaced; integrate them explicitly first.')
    private = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'constellation'))
    private.mkdir(mode=0o700, parents=True, exist_ok=True)
    state = private / 'installation.json'
    if not state.exists():
        with state.open('x') as stream:
            json.dump({'previous_git_hooks_path': previous}, stream)
        state.chmod(0o600)
    for path in guards:
        path.chmod(path.stat().st_mode | 0o111)
    subprocess.run(['git', 'config', '--local', 'core.hooksPath', '.codex/git-hooks'], cwd=root, check=True)
    return {'git_hooks': str(target), 'codex_hook_trust': 'requires_native_user_review'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.root)))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'Constellation: {exc}\n')
