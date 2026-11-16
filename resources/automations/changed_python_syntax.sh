#!/usr/bin/env bash
# changed_python_syntax.sh — compile changed Python after Write/Edit/MultiEdit.
#
# Checks explicit paths (including untracked files), changed Python working
# files and changed Python index blobs. compile() never executes code or writes
# bytecode. Source lines are never printed, even when syntax is invalid.
#
#   exit 0  → ok / nothing to do
#   exit 2  → a changed .py file does not compile
set -uo pipefail

exec python3 /dev/fd/3 3<<'PY'
import sys, os, json, subprocess
from pathlib import Path

TAG = "[constellation:py_syntax]"
MAX_BYTES = 5_000_000

def emit(message):
    sys.stderr.write(f"{TAG} {message}\n")

def protected(path):
    parts = tuple(part.lower() for part in path.parts)
    name = parts[-1] if parts else ""
    private_tree = ("_conversations" in parts
                    or any(pair in {(".codex", "sessions"), (".codex", "archived_sessions"),
                                    (".claude", "run")} for pair in zip(parts, parts[1:])))
    return (name.startswith(".env") or name.endswith((".pem", ".key"))
            or name == "credentials.json" or (name.startswith("rollout") and name.endswith(".jsonl"))
            or private_tree)

def git(*args, check=True):
    result = subprocess.run(["git", *args], capture_output=True, timeout=5,
                            env=dict(os.environ, LC_ALL="C"))
    if check and result.returncode:
        raise RuntimeError("git inspection failed")
    return result

def check_source(label, content):
    if len(content) > MAX_BYTES:
        raise RuntimeError("source exceeds syntax-check limit")
    try:
        compile(content, label, "exec", dont_inherit=True)
        return True
    except SyntaxError as exc:
        emit(f"SYNTAX ERROR in {label!r}:{exc.lineno or 0}:{exc.offset or 0}; source omitted.")
        return False
    except (ValueError, UnicodeError):
        emit(f"INVALID PYTHON SOURCE in {label!r}; source omitted.")
        return False

def main():
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    data = json.loads(raw) if raw.strip() else {}
    if not isinstance(data, dict):
        raise ValueError("invalid event")
    if data.get("cwd"):
        os.chdir(data["cwd"])
    fp = (data.get("tool_input") or {}).get("file_path")
    files = {Path(fp).absolute()} if fp else set()
    staged = set()
    repo = git("rev-parse", "--show-toplevel", check=False)
    if repo.returncode and b"not a git repository" not in repo.stderr:
        raise RuntimeError("cannot determine git context")
    if not repo.returncode:
        os.chdir(os.fsdecode(repo.stdout.rstrip(b"\n")))
        for cached in (False, True):
            args = ["diff", "--name-only", "-z", "--diff-filter=ACMRT"]
            if cached:
                args.append("--cached")
            paths = {p for p in git(*args).stdout.split(b"\0") if p}
            files.update(Path(os.fsdecode(p)).absolute() for p in paths)
            if cached:
                staged = paths

    good = True
    for path in sorted(files):
        if path.suffix != ".py":
            continue
        if protected(path) or protected(path.resolve()):
            emit(f"Skipped protected private/secrets path {str(path)!r}; secret_scan owns the refusal.")
            continue
        if path.is_file():
            with path.open("rb") as source:
                good = check_source(str(path), source.read(MAX_BYTES + 1)) and good

    if staged:
        for entry in git("ls-files", "--stage", "-z").stdout.split(b"\0"):
            if not entry:
                continue
            metadata, raw_path = entry.split(b"\t", 1)
            path = Path(os.fsdecode(raw_path))
            if raw_path not in staged or path.suffix != ".py" or protected(path):
                continue
            mode, oid, stage = metadata.split()
            if stage != b"0":
                raise RuntimeError("unmerged index")
            if mode not in (b"100644", b"100755"):
                continue
            object_id = oid.decode("ascii")
            if int(git("cat-file", "-s", object_id).stdout) > MAX_BYTES:
                raise RuntimeError("staged source exceeds syntax-check limit")
            good = check_source(f"index:{path}", git("cat-file", "blob", object_id).stdout) and good
    return 0 if good else 2

try:
    sys.exit(main())
except Exception as exc:
    emit(f"CHECK FAILED ({type(exc).__name__}); inspect hook inputs, file size and Git state locally.")
    sys.exit(2)
PY
