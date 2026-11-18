#!/usr/bin/env python3
"""Common entry point for Constellation; private state never lives in source."""
from __future__ import annotations

import argparse
from io import TextIOWrapper
import json
import os
from pathlib import Path
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent
# The notes monitor invokes its entry with Python isolated mode. Resolve only
# this trusted source package, independently of cwd and PYTHONPATH.
sys.path.insert(0, str(SOURCE))


def _skill_interpreter(group: str) -> str:
    """Select a local explicit Python, installed group runtime, or this Python."""
    override = os.environ.get('CONSTELLATION_SKILL_PYTHON')
    if override:
        path = Path(override)
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError('CONSTELLATION_SKILL_PYTHON must name an existing absolute executable: ' + override)
        return str(path)

    config = SOURCE / 'profiles/runtimes.json'
    if config.is_file():
        configured = json.loads(config.read_text(encoding='utf-8')).get(group)
        if configured:
            path = Path(configured)
            if path.is_absolute() and path.is_file() and os.access(path, os.X_OK):
                return str(path)
    return sys.executable


def main() -> int:
    """Dispatch explicit commands without a second agent runtime."""
    python_options = ('-X', 'utf8') if os.name == 'nt' else ()
    if os.name == 'nt':
        # Windows' redirected streams default to the ANSI code page. Native
        # hook envelopes and Git paths cross the process boundary as UTF-8.
        for stream in (sys.stdin, sys.stdout, sys.stderr):
            if isinstance(stream, TextIOWrapper) and not stream.isatty():
                stream.reconfigure(encoding='utf-8-sig' if stream is sys.stdin else 'utf-8',
                                   errors=stream.errors)
    if sys.argv[1:2] == ['install']:
        from constellation.install import main as install_main
        return install_main(sys.argv[2:])
    if sys.argv[1:2] == ['docs']:
        return subprocess.run([sys.executable, *python_options, '-B',
            str(SOURCE / 'resources/automations/official_docs.py'), *sys.argv[2:]]).returncode
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir')
    commands = parser.add_subparsers(dest='command', required=True)
    guard = commands.add_parser('guard-status')
    guard.add_argument('--root', required=True, type=Path)
    begin = commands.add_parser('begin', help='Read the change contract as JSON from stdin')
    begin.add_argument('task')
    for name in ('status', 'checkpoint', 'review', 'commit', 'push', 'recover', 'finish', 'cancel', 'assign'):
        p = commands.add_parser(name)
        p.add_argument('task')
        if name == 'commit':
            p.add_argument('message')
    check = commands.add_parser('check')
    check.add_argument('task'); check.add_argument('check_id')
    check.add_argument('argv', nargs=argparse.REMAINDER)
    hook = commands.add_parser('hook')
    hook.add_argument('--client', choices=('shared', 'copilot'), default='shared')
    hook.add_argument('event', choices=('pre-tool', 'stop', 'sessionStart',
                                      'subagentStart', 'preToolUse', 'agentStop', 'subagentStop'))
    git_hook = commands.add_parser('git-hook')
    git_hook.add_argument('event', choices=('pre-commit', 'pre-push'))
    git_hook.add_argument('arguments', nargs='*')
    run = commands.add_parser('skill-run')
    run.add_argument('group'); run.add_argument('skill'); run.add_argument('script')
    run.add_argument('arguments', nargs=argparse.REMAINDER)
    install = commands.add_parser('install')
    install.add_argument('arguments', nargs=argparse.REMAINDER)
    docs = commands.add_parser('docs', help='Verify, search or refresh local official documentation')
    docs.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.state_dir:
        from constellation.platform_support import IS_WINDOWS, validate_windows_lookup

        state_dir = Path(args.state_dir).expanduser()
        state_dir = validate_windows_lookup(state_dir) if IS_WINDOWS else state_dir.resolve()
        os.environ['CONSTELLATION_STATE_DIR'] = str(state_dir)
    if args.command == 'guard-status':
        from constellation.platform_support import IS_WINDOWS, git_executable, is_reparse, validate_windows_lookup
        from constellation.projects import load_projects

        root = validate_windows_lookup(args.root) if IS_WINDOWS else args.root.resolve()
        projects = load_projects(SOURCE)
        registered = any(Path(p['root']) == root and p['management'] == 'native' for p in projects)
        launcher = git_executable(project=root)
        git_environment = {key: value for key, value in os.environ.items()
                           if not (key.upper() if IS_WINDOWS else key).startswith('GIT_')}
        config = subprocess.run([launcher, '-C', str(root), 'config', '--null', '--get-all', 'core.hooksPath'],
                                capture_output=True, encoding='utf-8', errors='surrogateescape',
                                env=git_environment, timeout=30, check=False)
        paths = config.stdout.removesuffix('\0').split('\0')
        hook_path = paths[0] if config.returncode == 0 and len(paths) == 1 else ''
        configured_hooks = Path(hook_path)
        hooks = configured_hooks if configured_hooks.is_absolute() else root / configured_hooks
        if not IS_WINDOWS:
            hooks = hooks.resolve()
        anchored_relative = configured_hooks.anchor and not configured_hooks.is_absolute()
        verified = False
        if registered and hook_path and not anchored_relative and hooks == SOURCE / 'git-hooks':
            if IS_WINDOWS:
                validate_windows_lookup(hooks)
            owner = subprocess.run([launcher, '-C', str(root), 'rev-parse', '--show-toplevel'],
                                   capture_output=True, encoding='utf-8', errors='surrogateescape',
                                   env=git_environment, timeout=30, check=False)
            owner_root = Path(owner.stdout.rstrip('\r\n'))
            if not IS_WINDOWS:
                owner_root = owner_root.resolve()
            verified = owner.returncode == 0 and owner_root == root and all(
                (hooks / name).is_file() and not is_reparse(hooks / name)
                and os.access(hooks / name, os.R_OK if os.name == 'nt' else os.X_OK)
                for name in ('pre-commit', 'pre-push'))
        print(json.dumps({'verified': verified, 'root': str(root), 'hooks': str(hooks)}))
        return 0 if verified else 2
    if args.command == 'hook':
        if args.client == 'copilot':
            from constellation.copilot_hooks import main as copilot_hook_main
            return copilot_hook_main(args.event)
        from constellation.hooks import main as hook_main
        return hook_main(args.event)
    if args.command == 'install':
        from constellation.install import main as install_main
        return install_main(args.arguments)
    if args.command == 'docs':
        return subprocess.run([sys.executable, *python_options, '-B',
            str(SOURCE / 'resources/automations/official_docs.py'), *args.arguments]).returncode
    if args.command == 'skill-run':
        base = (SOURCE / 'skills' / args.group / args.skill).resolve()
        script = (base / args.script).resolve()
        if not base.is_relative_to(SOURCE / 'skills') or not script.is_relative_to(base):
            parser.error('Skill script leaves its source directory')
        if not script.is_file() or script.suffix != '.py':
            parser.error('Select an existing Python skill resource')
        return subprocess.run([_skill_interpreter(args.group), *python_options,
                               str(script), *args.arguments]).returncode
    from constellation.state import Store
    from constellation import git
    store = Store(args.state_dir)
    if args.command == 'begin':
        result = store.begin(args.task, **json.load(sys.stdin))
    elif args.command == 'checkpoint':
        result = store.checkpoint(args.task, **json.load(sys.stdin))
    elif args.command == 'review':
        result = store.review(args.task, **json.load(sys.stdin))
    elif args.command == 'status':
        result = store.status(args.task)
    elif args.command == 'finish':
        result = store.finish(args.task)
    elif args.command == 'cancel':
        result = store.cancel(args.task, **json.load(sys.stdin))
    elif args.command == 'assign':
        result = store.assign(args.task, **json.load(sys.stdin))
    elif args.command == 'check':
        argv = args.argv[1:] if args.argv[:1] == ['--'] else args.argv
        result = store.check(args.task, args.check_id, argv)
    elif args.command == 'commit':
        result = git.commit(store, args.task, args.message)
    elif args.command == 'push':
        result = git.push(store, args.task)
    elif args.command == 'recover':
        result = git.recover(store, args.task)
    elif args.command == 'git-hook':
        root = Path.cwd()
        if args.event == 'pre-commit':
            result = git.pre_commit(root, store)
        else:
            if len(args.arguments) != 2:
                parser.error('pre-push requires remote name and URL')
            result = git.pre_push(root, *args.arguments, sys.stdin.read(), store)
    else:
        parser.error('Unsupported command')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if args.command == 'check' and result.get('status') != 'passed' else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print('Constellation: ' + str(error), file=sys.stderr)
        sys.exit(2)
