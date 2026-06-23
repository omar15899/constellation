#!/usr/bin/env bash
# changed_python_syntax.sh — compile changed Python after Write/Edit/MultiEdit.
#
# Reads the edited file_path from the PostToolUse stdin JSON and, when inside a
# git work tree, also compiles changed/staged .py files. No-op when there is no
# Python to check. Cheap enough for PostToolUse.
#
#   exit 0  → ok / nothing to do
#   exit 2  → a changed .py file does not compile
set -uo pipefail

payload=""
if [ ! -t 0 ]; then payload="$(cat 2>/dev/null || true)"; fi

python3 - "$payload" <<'PY'
import sys, os, json, subprocess, py_compile

TAG = "[constellation:py_syntax]"
payload = sys.argv[1] if len(sys.argv) > 1 else ""
files = set()

if payload.strip():
    try:
        d = json.loads(payload)
        fp = (d.get("tool_input") or {}).get("file_path")
        if fp:
            files.add(fp)
    except Exception:
        pass

if subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                  capture_output=True).returncode == 0:
    for args in (["git", "diff", "--name-only", "--diff-filter=ACM"],
                 ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]):
        out = subprocess.run(args, capture_output=True, text=True)
        for l in out.stdout.splitlines():
            if l.strip():
                files.add(l.strip())

pyf = [f for f in files if f.endswith(".py") and os.path.isfile(f)]
if not pyf:
    sys.exit(0)

bad = False
for f in pyf:
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        sys.stderr.write(f"{TAG} SYNTAX ERROR in {f}:\n{e}\n")
        bad = True
sys.exit(2 if bad else 0)
PY
