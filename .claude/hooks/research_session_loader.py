#!/usr/bin/env python3
"""research_session_loader.py — SessionStart brief from the lever registry.

Runs on the Claude Code `SessionStart` event. Reads registry/levers.yaml and
injects a compact research brief into the new session's context so each session
starts from the ACCUMULATED methodology instead of re-deriving it — in
particular, so it never re-runs a lever already closed as REFUTED/HOLD.

Emits the documented SessionStart shape:
    {"hookSpecificOutput": {"hookEventName": "SessionStart",
                            "additionalContext": "<markdown brief>"}}

Safety contract: on ANY error, or if there are no levers, exits 0 silently —
never block or pollute a session start on a bug here.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from _levers import by_verdict, is_truthy, load_levers, load_strategies
except Exception:
    sys.exit(0)

CLOSED = ("REFUTED", "HOLD", "NO_IMPROVEMENT", "CAPPED")


def build_brief() -> str:
    levers = load_levers()
    if not levers:
        return ""
    bv = by_verdict(levers)
    strategies = {s["id"]: s for s in load_strategies()}

    lines: list[str] = []
    lines.append("## Research brief (from .claude/registry/levers.yaml)")
    lines.append("")
    lines.append("Standing state of the research program. **Do not re-run a "
                 "lever marked DO-NOT-RE-RUN** — its verdict is already paid for. "
                 "Bar: contracts/promotion_gate.md. Record new verdicts with /gate-check.")
    lines.append("")

    open_l = bv.get("OPEN", [])
    if open_l:
        lines.append("### OPEN — the real next steps")
        for l in open_l:
            lines.append(f"- `{l['id']}` ({l.get('strategy','?')}): {l.get('hypothesis','')}")
        lines.append("")

    confirmed = bv.get("CONFIRMED", [])
    if confirmed:
        lines.append("### CONFIRMED edges (the incumbent baselines to beat)")
        for l in confirmed:
            lines.append(f"- `{l['id']}` [{l.get('run_class','?')}]: {l.get('metric','')}")
        lines.append("")

    dead = []
    for v in CLOSED:
        for l in bv.get(v, []):
            if not is_truthy(l.get("rerun", "false")):
                dead.append((v, l))
    if dead:
        lines.append("### DO NOT RE-RUN (closed verdicts)")
        for v, l in dead:
            lines.append(f"- `{l['id']}` — **{v}**: {l.get('metric','')}")
        lines.append("")

    counts = ", ".join(f"{v}:{len(bv[v])}" for v in sorted(bv))
    lines.append(f"_levers: {len(levers)} ({counts}); strategies: {len(strategies)}._")
    return "\n".join(lines)


def main() -> int:
    if os.environ.get("RESEARCH_LOADER_DISABLE", "").strip() in ("1", "true", "yes"):
        return 0
    try:
        brief = build_brief()
    except Exception:
        return 0
    if not brief.strip():
        return 0
    out = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": brief,
        }
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
