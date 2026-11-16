#!/usr/bin/env python3
"""Common entry point for Constellation; private state never lives in source."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent
# The notes monitor invokes its entry with Python isolated mode. Resolve only
# this trusted source package, independently of cwd and PYTHONPATH.
sys.path.insert(0, str(SOURCE))


def main() -> int:
    """Dispatch explicit commands without a second agent runtime."""
    if sys.argv[1:2] == ['install']:
        from constellation.install import main as install_main
        return install_main(sys.argv[2:])
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
    hook.add_argument('event', choices=('pre-tool', 'stop'))
    git_hook = commands.add_parser('git-hook')
    git_hook.add_argument('event', choices=('pre-commit', 'pre-push'))
    git_hook.add_argument('arguments', nargs='*')
    run = commands.add_parser('skill-run')
    run.add_argument('group'); run.add_argument('skill'); run.add_argument('script')
    run.add_argument('arguments', nargs=argparse.REMAINDER)
    install = commands.add_parser('install')
    install.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.state_dir:
        os.environ['CONSTELLATION_STATE_DIR'] = str(Path(args.state_dir).expanduser().resolve())
    if args.command == 'guard-status':
        root = args.root.resolve()
        projects = json.loads((SOURCE / 'profiles/projects.json').read_text())['projects']
        registered = any(Path(p['root']).resolve() == root and p['management'] == 'native' for p in projects)
        hook_path = subprocess.run(['git', '-C', str(root), 'config', '--get', 'core.hooksPath'],
                                   capture_output=True, text=True, check=False).stdout.strip()
        hooks = Path(hook_path) if Path(hook_path).is_absolute() else root / hook_path
        verified = registered and hooks.resolve() == SOURCE / 'git-hooks' and all(
            (hooks / name).is_file() and not (hooks / name).is_symlink()
            and os.access(hooks / name, os.X_OK)
            for name in ('pre-commit', 'pre-push'))
        print(json.dumps({'verified': verified, 'root': str(root), 'hooks': str(hooks.resolve())}))
        return 0 if verified else 2
    if args.command == 'hook':
        from constellation.hooks import main as hook_main
        return hook_main(args.event)
    if args.command == 'install':
        from constellation.install import main as install_main
        return install_main(args.arguments)
    if args.command == 'skill-run':
        base = (SOURCE / 'skills' / args.group / args.skill).resolve()
        script = (base / args.script).resolve()
        if not base.is_relative_to(SOURCE / 'skills') or not script.is_relative_to(base):
            parser.error('Skill script leaves its source directory')
        if not script.is_file() or script.suffix != '.py':
            parser.error('Select an existing Python skill resource')
        runners = json.loads((SOURCE / 'profiles/runtimes.json').read_text())
        interpreter = runners.get(args.group, sys.executable)
        if not Path(interpreter).is_file():
            parser.error('The configured skill interpreter is unavailable: ' + interpreter)
        return subprocess.run([interpreter, str(script), *args.arguments]).returncode
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
