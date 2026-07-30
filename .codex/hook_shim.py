#!/usr/bin/env python3
"""Bridge a Claude Code hook into Codex's hook runner.

Codex matches hooks on tool *name* only, and knows nothing about
`$CLAUDE_PROJECT_DIR`. This shim restores both:

  * `--command-glob` re-applies Claude's argument-level matcher (the
    `Bash(git commit*)` form) against `tool_input.command`, exiting 0 without
    running the hook when it does not match;
  * `CLAUDE_PROJECT_DIR` / `CODEX_PROJECT_DIR` are exported so hook scripts
    resolve repo paths identically under both agents;
  * the payload's field names are normalised, because the constellation's
    hooks read `event` and `tool_result` while Codex sends `hook_event_name`
    and `tool_response`. Those hooks default missing fields to empty and
    exit 0, so an unnormalised payload turns every gate into a silent no-op
    rather than a visible failure.

stdout, stderr and the exit code pass through untouched, so Codex's exit-2
blocking semantics keep working.
"""

import fnmatch
import json
import os
import subprocess
import sys

GENERATED_BY = "codex_sync.py"

# Codex name -> the name the .claude/hooks/ scripts expect. Added only when
# absent, so a payload that already speaks Claude's dialect is left alone.
ALIASES = {
    "event": ("hook_event_name",),
    "tool_result": ("tool_response", "tool_output", "result"),
    "tool_response": ("tool_result",),
    "hook_event_name": ("event",),
}


def normalise(payload: str) -> str:
    try:
        data = json.loads(payload)
    except ValueError:
        return payload
    if not isinstance(data, dict):
        return payload
    for target, sources in ALIASES.items():
        if data.get(target):
            continue
        for source in sources:
            if data.get(source):
                data[target] = data[source]
                break
    return json.dumps(data)


def main() -> int:
    argv = sys.argv[1:]
    project_dir = ""
    glob = ""
    while argv and argv[0].startswith("--"):
        flag = argv.pop(0)
        if flag == "--":
            break
        if not argv:
            print(f"hook_shim: {flag} needs a value", file=sys.stderr)
            return 1
        value = argv.pop(0)
        if flag == "--project-dir":
            project_dir = value
        elif flag == "--command-glob":
            glob = value
        else:
            print(f"hook_shim: unknown flag {flag}", file=sys.stderr)
            return 1
    if not argv:
        print("hook_shim: no inner command", file=sys.stderr)
        return 1

    payload = sys.stdin.read()

    if glob:
        try:
            command = (json.loads(payload).get("tool_input") or {}).get("command", "")
        except (ValueError, AttributeError):
            command = ""
        if not fnmatch.fnmatch(command.strip(), glob):
            return 0

    env = dict(os.environ)
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = project_dir
        env["CODEX_PROJECT_DIR"] = project_dir

    done = subprocess.run(argv, input=normalise(payload), text=True, env=env, capture_output=True)
    sys.stdout.write(done.stdout)
    sys.stderr.write(done.stderr)
    return done.returncode


if __name__ == "__main__":
    sys.exit(main())
