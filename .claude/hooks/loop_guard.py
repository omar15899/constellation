#!/usr/bin/env python3
"""loop_guard.py — Stop-time verification gate (constellation plane).

Runs on the Claude Code `Stop` event. Blocks completion (exit 2 → the model is
told to continue) on HARD, deterministic signals:

  - staged secrets, checked by the same secret_scan.sh gate as tool events;
  - inability to complete that deterministic secret check.

A SOFT heuristic — strong completion language in the final message without any
CONCRETE evidence token (a real path / hash / exit-code / metrics file, not a
bare adjective like "verified") — is also computed, but it only BLOCKS when
`LOOP_GUARD_STRICT=1`. A Stop hook that misjudges prose would brick every turn,
so the heuristic is advisory by default and opt-in for strictness.

Env switches:
    LOOP_GUARD_DISABLE=1   turn the guard off entirely
    LOOP_GUARD_STRICT=1    let the completion-language heuristic block too

Safety contract: honors `stop_hook_active`, reports internal errors without
source data, and never reads conversation transcripts. TODO markers are advisory
only, scoped to the current final message. Cheap checks only — no tests.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

TAG = "[constellation:loop_guard]"
SECRET_SCAN = Path(__file__).with_name("secret_scan.sh")

BLOCK_MSG = """LOOP GUARD BLOCKED COMPLETION
Resolve the reported gate failure and run the minimal verification again.
The next Stop event with stop_hook_active=true is allowed to finish."""

# actionable markers only (followed by ':' or '(') — NOT the word in prose.
TODO_MARK = re.compile(r"(?<![A-Za-z])(TODO|FIXME|XXX|TKTK)[:(]")

COMPLETION = re.compile(r"(?i)\b(done\b|complete[d]?\b|fixed\b|wired\b|end[\s-]?to[\s-]?end"
                        r"|shipped|fully\s+working|all\s+set|good\s+to\s+go|production[\s-]?ready)")
# CONCRETE evidence only — bare adjectives ("verified", lone "pass") do NOT count.
EVIDENCE = re.compile(
    r"(?i)(pytest|exit\s*code\s*0|tests?\s+(?:pass|passed|passing|green)"
    r"|commit\s+[0-9a-f]{7,}|\b[0-9a-f]{7,40}\b|metrics?\.json|report\.json"
    r"|manifest\.json|results?\.json|\.(?:csv|parquet|png)\b"
    r"|evidence\s+table|\|\s*status\s*\|)")


def emit(m: str) -> None:
    sys.stderr.write(f"{TAG} {m}\n")


def git_staged_secrets(cwd: str) -> list[str]:
    result = subprocess.run(
        ["bash", str(SECRET_SCAN)],
        input=json.dumps({"cwd": cwd, "hook_event_name": "Stop"}),
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode == 0:
        return []
    # The shared scanner guarantees redacted diagnostics; never replay stdout
    # or subprocess exception text, which can carry arbitrary source data.
    if result.stderr:
        sys.stderr.write(result.stderr)
    return ["staged secret verification refused completion"]


def main() -> int:
    if os.environ.get("LOOP_GUARD_DISABLE", "").strip() in ("1", "true", "yes"):
        return 0
    try:
        payload = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(payload) if payload.strip() else {}
        if not isinstance(data, dict):
            raise ValueError("invalid event")
    except Exception as exc:
        emit(f"invalid Stop event ({type(exc).__name__}); no transcript was read")
        return 2
    if data.get("stop_hook_active"):
        return 0

    hard: list[str] = []
    try:
        hard += git_staged_secrets(data.get("cwd") or os.getcwd())
    except Exception as exc:
        hard.append(f"staged secret verification could not finish ({type(exc).__name__})")

    strict = os.environ.get("LOOP_GUARD_STRICT", "").strip() in ("1", "true", "yes")
    soft = ""
    final = data.get("last_assistant_message") or ""
    if not isinstance(final, str):
        final = ""
    if len(final) > 80 and COMPLETION.search(final) and not EVIDENCE.search(final):
        soft = "final message claims completion with no concrete evidence token (path/hash/exit-code/metrics)"
    if TODO_MARK.search(final):
        emit("advisory: the current final message contains an unresolved-work marker")

    if hard or (strict and soft):
        emit("BLOCKED:")
        for h in hard:
            emit(f"  hard: {h}")
        if strict and soft:
            emit(f"  soft: {soft}")
        sys.stderr.write(BLOCK_MSG + "\n")
        return 2

    if soft:
        emit(f"advisory (not blocking; set LOOP_GUARD_STRICT=1 to enforce): {soft}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        emit(f"guard failed ({type(exc).__name__}); no transcript or source text was emitted")
        sys.exit(2)
