#!/usr/bin/env python3
"""loop_guard.py — Stop-time verification gate (constellation plane).

Runs on the Claude Code `Stop` event. Blocks completion (exit 2 → the model is
told to continue) on HARD, deterministic signals:

  - a secret or `.env` staged in git;
  - actionable TODO/FIXME markers left inside the workflow dirs
    (`.claude/commands`, `.claude/hooks`, `.claude/contracts`, the ledger) —
    scoped there on purpose so a stray marker in general docs cannot brick
    every session.

A SOFT heuristic — strong completion language in the final message without any
CONCRETE evidence token (a real path / hash / exit-code / metrics file, not a
bare adjective like "verified") — is also computed, but it only BLOCKS when
`LOOP_GUARD_STRICT=1`. A Stop hook that misjudges prose would brick every turn,
so the heuristic is advisory by default and opt-in for strictness.

Env switches:
    LOOP_GUARD_DISABLE=1   turn the guard off entirely
    LOOP_GUARD_STRICT=1    let the completion-language heuristic block too

Safety contract: honors `stop_hook_active`; on ANY internal error exits 0
(never brick a session on a bug in the guard). Cheap checks only — no tests.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

TAG = "[constellation:loop_guard]"
GITHUB_ROOT = Path.home() / "GitHub"
WORKFLOW_DIRS = ["commands", "hooks", "contracts"]

BLOCK_MSG = """LOOP GUARD BLOCKED COMPLETION
Claude must continue:
1. identify missing evidence,
2. run the minimal check,
3. update the evidence table,
4. rerun final audit."""

# actionable markers only (followed by ':' or '(') — NOT the word in prose.
TODO_MARK = re.compile(r"(?<![A-Za-z])(TODO|FIXME|XXX|TKTK)[:(]")

KEY_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
PREFIX = re.compile(r"(AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}"
                    r"|sk-[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
                    r"|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_\-]{30,})")
COMPLETION = re.compile(r"(?i)\b(done\b|complete[d]?\b|fixed\b|wired\b|end[\s-]?to[\s-]?end"
                        r"|shipped|fully\s+working|all\s+set|good\s+to\s+go|production[\s-]?ready)")
# CONCRETE evidence only — bare adjectives ("verified", lone "pass") do NOT count.
EVIDENCE = re.compile(
    r"(?i)(pytest|exit\s*code\s*0|tests?\s+(?:pass|passed|passing|green)"
    r"|commit\s+[0-9a-f]{7,}|\b[0-9a-f]{7,40}\b|metrics?\.json|report\.json"
    r"|manifest\.json|results?\.json|\.(?:csv|parquet|png)\b|✓"
    r"|evidence\s+table|\|\s*status\s*\|)")


def emit(m: str) -> None:
    sys.stderr.write(f"{TAG} {m}\n")


def git_staged_secrets() -> list[str]:
    hits: list[str] = []
    if subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                      capture_output=True).returncode != 0:
        return hits
    out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                         capture_output=True, text=True)
    for n in (l.strip() for l in out.stdout.splitlines() if l.strip()):
        b = os.path.basename(n)
        if b == ".env" or b.startswith(".env."):
            hits.append(f"{n} (.env staged)")
    diff = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True).stdout
    for ln in diff.splitlines():
        if ln.startswith("+") and (KEY_BLOCK.search(ln) or PREFIX.search(ln)):
            hits.append("staged diff contains key/token material")
            break
    return hits


def claude_todo_markers() -> list[str]:
    hits: list[str] = []
    base = GITHUB_ROOT / ".claude"
    paths: list[Path] = []
    for d in WORKFLOW_DIRS:
        p = base / d
        if p.exists():
            paths += [f for f in p.rglob("*") if f.suffix in (".md", ".py", ".sh")]
    ledger = base / "loop_ledger.md"
    if ledger.exists():
        paths.append(ledger)
    for f in paths:
        if "__pycache__" in f.parts or not f.is_file():
            continue
        try:
            for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if TODO_MARK.search(line):
                    hits.append(f"{f}:{i} {line.strip()[:80]}")
        except Exception:
            continue
    return hits


def last_assistant_text(transcript_path: str) -> str:
    try:
        latest = ""
        with open(transcript_path, errors="ignore") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except Exception:
                    continue
                if rec.get("type") != "assistant":
                    continue
                content = rec.get("message", {}).get("content")
                if isinstance(content, str):
                    latest = content
                elif isinstance(content, list):
                    latest = " ".join(
                        c.get("text", "") for c in content
                        if isinstance(c, dict) and c.get("type") == "text")
        return latest
    except Exception:
        return ""


def main() -> int:
    if os.environ.get("LOOP_GUARD_DISABLE", "").strip() in ("1", "true", "yes"):
        return 0
    try:
        payload = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(payload) if payload.strip() else {}
    except Exception:
        return 0
    if data.get("stop_hook_active"):
        return 0

    hard: list[str] = []
    try:
        hard += git_staged_secrets()
    except Exception:
        pass
    try:
        hard += claude_todo_markers()
    except Exception:
        pass

    strict = os.environ.get("LOOP_GUARD_STRICT", "").strip() in ("1", "true", "yes")
    soft = ""
    if data.get("transcript_path"):
        final = last_assistant_text(data["transcript_path"])
        if final and len(final) > 80 and COMPLETION.search(final) and not EVIDENCE.search(final):
            soft = "final message claims completion with no concrete evidence token (path/hash/exit-code/metrics)"

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
    except Exception:
        sys.exit(0)
