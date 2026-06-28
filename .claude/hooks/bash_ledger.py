#!/usr/bin/env python3
"""bash_ledger.py — PostToolUse Bash command ledger (constellation plane).

Fires after every Bash tool call. Appends one JSONL record per command to a
per-session ledger so that "what actually ran, and how it exited" is machine
evidence — not reconstructed from the model's prose. This closes the loop that
`evidence_audit.py` and `/ship-loop` depend on: a claim like "tests pass" can be
cross-checked against a real test invocation in the ledger.

Ledger location: ~/GitHub/.claude/run/<session_id>.jsonl  (git-ignored — these
are ephemeral session evidence; the DURABLE research ledger is the commit-trailer
history written by constellation_commit.py).

Record schema (one JSON object per line):
    {
      "ts":         ISO-8601 local timestamp,
      "cwd":        working directory of the call,
      "command":    the command string,
      "description": the tool's human description (if any),
      "exit":       integer exit code if the harness exposed one, else null,
      "interrupted": bool,
      "ok":         best-effort success flag (see below),
      "stdout_tail": last ~400 chars of stdout,
      "stderr_tail": last ~400 chars of stderr,
      "signals":    detected evidence tokens (test-runner, pass/fail, etc.)
    }

`exit` is null when the harness does not surface a numeric code. `ok` is then a
three-valued signal verdict: False if interrupted, if a known test runner emitted
a fail token, or if a fail token appears with no pass token; True only on a clear
pass token; None ("unknown") when no signal is decisive — so a silent exit-1 is
never recorded as success.

Safety contract: append-only, never blocks (always exit 0), dependency-free
stdlib, bounded record size. On ANY internal error exits 0 silently — a logging
hook must never brick a turn.

Env switches:
    BASH_LEDGER_DISABLE=1   turn the ledger off entirely
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

TAG = "[constellation:bash_ledger]"
LEDGER_DIR = Path.home() / "GitHub" / ".claude" / "run"
TAIL = 400

TEST_RUNNER = re.compile(
    r"(?i)\b(pytest|python\s+-m\s+pytest|unittest|tox|nox|cargo\s+test"
    r"|go\s+test|npm\s+(?:run\s+)?test|vitest|jest|py_compile|mypy|ruff|bash\s+-n)\b"
)
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

    stdout = tail(tr.get("stdout", "") or "")
    stderr = tail(tr.get("stderr", "") or "")
    interrupted = bool(tr.get("interrupted") or data.get("interrupted"))
    exit_code = first_int(tr, "exitCode", "exit_code", "returnCode", "return_code", "code", "status")
    if exit_code is None:
        exit_code = first_int(data, "exitCode", "exit_code", "returnCode")

    blob = f"{stdout}\n{stderr}"
    is_test = bool(TEST_RUNNER.search(command))
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
        "ts": ts,
        "cwd": data.get("cwd") or os.getcwd(),
        "command": command[:1000],
        "description": (ti.get("description") or "")[:300],
        "exit": exit_code,
        "interrupted": interrupted,
        "ok": ok,
        "is_test": is_test,
        "stdout_tail": stdout,
        "stderr_tail": stderr,
        "signals": signals,
    }

    try:
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        session = str(data.get("session_id") or "nosession").replace("/", "_")
        path = LEDGER_DIR / f"{session}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
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
