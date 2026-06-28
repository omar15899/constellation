#!/usr/bin/env python3
"""dead_lever_guard.py — PreToolUse(Bash) guard against re-running a dead lever.

The single most expensive recurring waste in this constellation is re-running a
research lever that was already closed as REFUTED/HOLD in a prior session. This
guard inspects a pending Bash command and, when it matches the explicit
`rerun_guard` keywords of a non-re-runnable lever AND looks like an expensive
research run, surfaces the prior verdict.

Posture (balanced, per the user's choice): ADVISORY by default — it warns on
stderr and exits 0, never bricking a command (the keyword match is a heuristic,
and the user may have a legitimate reason). Set DEAD_LEVER_STRICT=1 to make a
match BLOCK (exit 2) instead.

Only levers that declare a `rerun_guard` field in levers.yaml participate, so the
guard is precise and opt-in per lever — it cannot fire on an undecorated lever.

Safety contract: on ANY error, exit 0.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from _levers import is_truthy, load_levers
except Exception:
    sys.exit(0)

TAG = "[constellation:dead_lever_guard]"

# The command must look like an expensive research RUN, not an inspect/grep.
RUN_VERB = re.compile(r"(?i)(python3?\s|\buv\s+run\b|\.py\b|\.mjs\b|node\s|\bbq\b|bigquery"
                      r"|research_search|promotion_report|--glob|backtest|sweep|ingest|train)")
# Cheap read-only commands never trip the guard even if they mention a keyword.
READ_ONLY = re.compile(r"(?i)^\s*(cat|less|head|tail|grep|rg|ls|find|git\s+(log|status|diff|show)|wc|sed\s+-n)\b")


def pending_command() -> str:
    try:
        payload = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(payload) if payload.strip() else {}
    except Exception:
        return ""
    return (data.get("tool_input", {}) or {}).get("command", "") or ""


def matches(cmd: str, guard: str) -> list[str]:
    hits = []
    for kw in (k.strip() for k in guard.split(",") if k.strip()):
        try:
            if re.search(kw, cmd, re.IGNORECASE):
                hits.append(kw)
        except re.error:
            if kw.lower() in cmd.lower():
                hits.append(kw)
    return hits


def main() -> int:
    if os.environ.get("DEAD_LEVER_GUARD_DISABLE", "").strip() in ("1", "true", "yes"):
        return 0
    cmd = pending_command()
    if not cmd or READ_ONLY.search(cmd) or not RUN_VERB.search(cmd):
        return 0

    findings = []
    for lev in load_levers():
        if is_truthy(lev.get("rerun", "false")):
            continue
        guard = lev.get("rerun_guard", "")
        if not guard:
            continue
        hits = matches(cmd, guard)
        if hits:
            findings.append((lev, hits))
    if not findings:
        return 0

    strict = os.environ.get("DEAD_LEVER_STRICT", "").strip() in ("1", "true", "yes")
    sys.stderr.write(f"{TAG} this command looks like a re-run of a CLOSED lever:\n")
    for lev, hits in findings:
        sys.stderr.write(f"{TAG}   `{lev['id']}` — {lev.get('verdict','?')} "
                         f"(matched: {', '.join(hits)})\n")
        sys.stderr.write(f"{TAG}      {lev.get('metric','')}\n")
        if lev.get("memory"):
            sys.stderr.write(f"{TAG}      see memory:{lev['memory']} / research_ledger.md\n")
    if strict:
        sys.stderr.write(f"{TAG} BLOCKED (DEAD_LEVER_STRICT). If the re-run is intentional "
                         f"(new data/method), unset it or update the lever's verdict via /gate-check.\n")
        return 2
    sys.stderr.write(f"{TAG} advisory only — proceeding. Confirm the re-run is intentional; "
                     f"set DEAD_LEVER_STRICT=1 to block.\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
