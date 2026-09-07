#!/usr/bin/env python3
"""PostToolUse execution evidence, local-only and free of command/output text.

Records command SHA-256, check classification, observed exit/unknown status,
interruption and evidence signals in gitignored .claude/run/. Files are private
and event IDs are deduplicated under a lock. No transcripts, command arguments,
descriptions, stdout or stderr are persisted. Existing historical ledgers are
not rewritten. evidence_audit.py consumes is_test/ok, which remain compatible.

Missing exit status is unknown unless actual result signals establish a verdict.
This observational hook never blocks a turn. BASH_LEDGER_DISABLE=1 opts out.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shlex
import sys
from datetime import datetime
from pathlib import Path

TAG = "[constellation:bash_ledger]"
LEDGER_DIR = Path.home() / "GitHub" / ".claude" / "run"
TAIL = 400

def is_test_command(command: str) -> bool:
    """Conservative recognition of an executed check, never a file mention."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if not argv or re.search(r"[;&|<>`\n]|\$\(", command):
        return False  # compound shell status cannot prove every check passed
    if set(argv) & {"--help", "-h", "--version", "-V", "--collect-only", "--co", "--list-tests", "--list", "-l"}:
        return False
    executable = Path(argv[0]).name
    if executable in {"pytest", "unittest", "tox", "nox", "vitest", "jest"}:
        return True
    if re.fullmatch(r"python(?:\d+(?:\.\d+)*)?", executable):
        args = argv[1:]
        while args and args[0] in {"-B", "-u", "-I", "-s", "-E"}:
            args.pop(0)
        if args[:1] == ["-m"]:
            return len(args) > 1 and args[1] in {"pytest", "unittest"}
        return bool(args and re.fullmatch(r"test_[A-Za-z0-9_]+\.py", Path(args[0]).name))
    return ((executable in {"cargo", "go"} and argv[1:2] == ["test"])
            or (executable == "npm" and argv[1:2] == ["test"])
            or (executable == "npm" and argv[1:3] == ["run", "test"]))
FAIL_TOKEN = re.compile(
    r"(?i)(\bFAILED\b|\bERROR\b|\bfailed\b|Traceback|\bE\s+assert|exit\s*code\s*[1-9]"
    r"|\b\d+\s+failed\b|fatal:|command not found|No such file|Permission denied)"
)
# Note: no bare "\bOK\b" — it matches prose like "looks OK though" next to a real
# Traceback and would mask a failure.
PASS_TOKEN = re.compile(
    r"(?i)(\b\d+\s+passed\b|\bPASSED\b|tests?\s+pass(?:ed|ing)?|exit\s*code\s*0|✓)"
)


def tail(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    return s[-TAIL:] if len(s) > TAIL else s


def first_int(d: dict, *keys) -> int | None:
    for k in keys:
        v = d.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            return int(v.strip())
    return None


def main() -> int:
    if os.environ.get("BASH_LEDGER_DISABLE", "").strip() in ("1", "true", "yes"):
        return 0
    try:
        payload = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(payload) if payload.strip() else {}
    except Exception:
        return 0
    if not data:
        return 0

    ti = data.get("tool_input", {})
    if isinstance(ti, str):
        ti = {"command": ti}          # some payloads put the command bare
    elif not isinstance(ti, dict):
        ti = {}
    tr = data.get("tool_response", {}) or {}
    if not isinstance(tr, dict):
        tr = {"stdout": str(tr)}

    command = ti.get("command") or ""
    if not command:
        return 0  # nothing to log

    stdout = tail(tr.get("stdout", "") or tr.get("output", "") or "")
    stderr = tail(tr.get("stderr", "") or "")
    interrupted = bool(tr.get("interrupted") or data.get("interrupted"))
    exit_code = first_int(tr, "exitCode", "exit_code", "returnCode", "return_code", "code", "status")
    if exit_code is None:
        exit_code = first_int(data, "exitCode", "exit_code", "returnCode")

    blob = f"{stdout}\n{stderr}"
    is_test = is_test_command(command)
    has_fail = bool(FAIL_TOKEN.search(blob))
    has_pass = bool(PASS_TOKEN.search(blob))

    # Honest verdict. With a real exit code, use it. Without one (the harness
    # usually does not surface it), fall back to signals — but a failing test or
    # a fail-token must DOMINATE a pass-token, and the absence of any decisive
    # signal is recorded as ok=None ("unknown"), never as success. A silent
    # exit-1 ('false') must not be counted as a pass.
    if exit_code is not None:
        ok: bool | None = exit_code == 0 and not interrupted
    elif interrupted:
        ok = False
    elif is_test and has_fail:
        ok = False
    elif has_fail and not has_pass:
        ok = False
    elif has_pass:
        ok = True
    else:
        ok = None

    signals = []
    if is_test:
        signals.append("test-runner")
    if has_pass:
        signals.append("pass-token")
    if has_fail:
        signals.append("fail-token")

    try:
        ts = datetime.now().isoformat(timespec="seconds")
    except Exception:
        ts = ""

    rec = {
        "schema": 2,
        "ts": ts,
        "cwd": data.get("cwd") or os.getcwd(),
        "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
        "exit": exit_code,
        "interrupted": interrupted,
        "ok": ok,
        "is_test": is_test,
        "signals": signals,
    }

    # Keep only execution evidence. Commands, arguments, descriptions and
    # outputs can contain private conversation text or credentials.
    event_id = data.get("tool_use_id")
    if event_id:
        rec["event_sha256"] = hashlib.sha256(str(event_id).encode()).hexdigest()

    try:
        LEDGER_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        session = hashlib.sha256(str(data.get("session_id") or "nosession").encode()).hexdigest()
        path = LEDGER_DIR / f"{session}.jsonl"
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            fh.seek(0)
            if event_id and any(json.loads(line).get("event_sha256") == rec["event_sha256"] for line in fh if line.strip()):
                return 0
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        return 0

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
