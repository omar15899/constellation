#!/usr/bin/env python3
"""evidence_audit.py — flag metric / completion claims that lack a nearby
artifact reference.

Usage:
    evidence_audit.py [PATH ...]     audit given files/dirs
    evidence_audit.py                audit default report dirs under CWD
    evidence_audit.py --strict ...   exit 1 if any unsupported claim is found
    evidence_audit.py --json   ...   machine-readable findings on stdout
    evidence_audit.py --ledger [P]   cross-check claims against the Bash run
                                     ledger (P, or newest in ~/GitHub/.claude/run/)

The `--ledger` cross-check turns prose claims into command-backed evidence: a
report that claims tests pass / all green while the session's Bash ledger
(written by bash_ledger.py) contains NO test-runner invocation is flagged as an
unsupported completion claim. This is the determinism bridge between "what the
model wrote" and "what actually ran".

Design goal (per the workflow spec): KEEP FALSE POSITIVES LOW. A line is
flagged only when it makes a *quantified* metric claim or a *strong* completion
claim AND no artifact reference appears within a small window of lines around
it. Prose that merely mentions "complete" without a number or a hard claim is
not flagged.

This is a constellation-plane library tool: dependency-free, stderr-tagged,
idempotent.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

TAG = "[constellation:evidence_audit]"
WINDOW = 6  # lines of context each side that count as "nearby"

DEFAULT_GLOBS = [
    "reports", "outputs", "docs",
    "research_algorithms/**/reports", "research_algorithms/**/outputs",
]
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".log", ".json"}

# Quantified metric: a metric keyword sitting next to a number.
_METRIC_WORDS = (
    r"sharpe|sortino|calmar|cagr|max[\s_]?dd|max[\s_]?drawdown|drawdown"
    r"|\bic\b|information[\s_]?coefficient|ndcg|turnover|decile|quintile"
    r"|hit[\s_-]?rate|win[\s_-]?rate|alpha|beta|pbo|dsr|benchmark"
)
METRIC = re.compile(
    rf"(?i)(?:({_METRIC_WORDS})\D{{0,24}}?[-+]?\d|\b[-+]?\d[\d.,]*\s*%?\s*\D{{0,12}}?({_METRIC_WORDS}))"
)
# Strong completion claims.
COMPLETION = re.compile(
    r"(?i)\b(end[\s-]?to[\s-]?end|fully\s+wired|wired\s+up|production[\s-]?ready"
    r"|completed|complete\b|fixed\b|shipped|works\s+end|all\s+passing|verified\b)"
)
# Hard artifact references that count as evidence. Deliberately NOT the bare
# words "pass"/"passed"/"PASS" (report prose like "all tests pass" would then
# self-satisfy a nearby unsupported metric claim) and NOT a bare 7+-hex token
# (matches almost anything); a commit hash must be qualified ("commit <hash>").
ARTIFACT = re.compile(
    r"(?i)(metrics?\.json|report\.json|manifest\.json|results?\.json|\.csv|\.parquet"
    r"|\.png|\bpytest\b|exit\s*code\s*0|✓|commit\s+[0-9a-f]{7,40}"
    r"|artifact|figure\s*\d)"
)


def iter_target_files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    if paths:
        for p in paths:
            pp = Path(p)
            if pp.is_dir():
                out += [f for f in pp.rglob("*") if f.suffix.lower() in TEXT_SUFFIXES]
            elif pp.is_file():
                out.append(pp)
    else:
        root = Path.cwd()
        for g in DEFAULT_GLOBS:
            for f in root.glob(g):
                if f.is_dir():
                    out += [x for x in f.rglob("*") if x.suffix.lower() in TEXT_SUFFIXES]
                elif f.suffix.lower() in TEXT_SUFFIXES:
                    out.append(f)
    # de-dup, stable
    seen, uniq = set(), []
    for f in out:
        if f not in seen:
            seen.add(f); uniq.append(f)
    return uniq


def audit_file(path: Path) -> list[dict]:
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except Exception:
        return []
    findings = []
    for i, line in enumerate(lines):
        claim = None
        if METRIC.search(line):
            claim = "metric"
        elif COMPLETION.search(line):
            claim = "completion"
        if not claim:
            continue
        lo, hi = max(0, i - WINDOW), min(len(lines), i + WINDOW + 1)
        nearby = "\n".join(lines[lo:hi])
        if ARTIFACT.search(nearby):
            continue
        findings.append({
            "file": str(path), "line": i + 1, "kind": claim,
            "text": line.strip()[:160],
        })
    return findings


# A *completion* claim about tests — requires the plural "tests", an "all"/count
# qualifier, or "test suite", so prose like "test passing the new flag" (singular
# gerund, not a pass-claim) does not trip it.
TEST_CLAIM = re.compile(
    r"(?i)(\btests\s+(?:pass|passed|passing|green)\b"
    r"|\ball\s+tests?\s+(?:pass|passed|passing|green)\b"
    r"|\b\d+\s+tests?\s+passed\b"
    r"|\btest\s+suite\s+(?:passes|passing|green)\b"
    r"|\ball\s+passing\b|\ball\s+green\b)"
)


def newest_ledger() -> Path | None:
    d = Path.home() / "GitHub" / ".claude" / "run"
    if not d.is_dir():
        return None
    cands = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return cands[0] if cands else None


def ledger_records(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return out


def ledger_check(target_files: list[Path], explicit: str | None) -> tuple[list[dict], dict]:
    """Cross-check 'tests pass' claims in the target files against the run ledger.
    Flags a claim when the ledger has NO test run, a test run that FAILED, or test
    runs none of which is a confirmed pass. Returns (findings, summary)."""
    led = Path(explicit) if explicit else newest_ledger()
    summary = {"ledger": str(led) if led else None, "commands": 0,
               "tests_run": 0, "failures": 0, "unverified": 0}
    if not led or not led.exists():
        return [], summary
    recs = ledger_records(led)
    test_recs = [r for r in recs if r.get("is_test")]
    summary["commands"] = len(recs)
    summary["tests_run"] = len(test_recs)
    # `ok` is three-valued (True/False/None). Count only explicit failures and
    # explicit unknowns; never treat a missing/None ok as a pass.
    summary["failures"] = sum(1 for r in recs if r.get("ok") is False)
    summary["unverified"] = sum(1 for r in recs if r.get("ok") is None)

    test_passed = any(r.get("ok") is True for r in test_recs)
    test_failed = any(r.get("ok") is False for r in test_recs)
    reason = None
    if not test_recs:
        reason = "the run ledger has NO test invocation"
    elif test_failed:
        reason = "the run ledger shows a test invocation that FAILED"
    elif not test_passed:
        reason = "the run ledger has test invocations but NONE recorded a pass"
    if reason is None:
        return [], summary

    findings: list[dict] = []
    for f in target_files:
        try:
            for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if TEST_CLAIM.search(line):
                    findings.append({
                        "file": str(f), "line": i, "kind": "claim-vs-ledger",
                        "text": f"claims tests pass but {reason}: " + line.strip()[:120],
                    })
        except Exception:
            continue
    return findings, summary


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    as_json = "--json" in argv
    use_ledger = "--ledger" in argv
    explicit_ledger = None
    if use_ledger:
        i = argv.index("--ledger")
        # Only swallow the next token as the ledger if it LOOKS like one — a
        # report path (e.g. `--ledger report.md`) must stay a positional, else
        # the documented `--strict --ledger <report>` form would audit nothing.
        if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            cand = argv[i + 1]
            if cand.endswith(".jsonl") or "/run/" in cand or os.sep + "run" + os.sep in cand:
                explicit_ledger = cand
    paths = [a for a in argv if not a.startswith("--") and a != explicit_ledger]

    target_files = iter_target_files(paths)
    all_findings: list[dict] = []
    for f in target_files:
        all_findings += audit_file(f)

    ledger_summary: dict = {}
    if use_ledger:
        led_findings, ledger_summary = ledger_check(target_files, explicit_ledger)
        all_findings += led_findings
        if not as_json:
            if ledger_summary.get("ledger"):
                sys.stderr.write(
                    f"{TAG} run ledger: {ledger_summary['commands']} commands, "
                    f"{ledger_summary['tests_run']} test runs, "
                    f"{ledger_summary['failures']} failed, "
                    f"{ledger_summary['unverified']} unverified "
                    f"({ledger_summary['ledger']})\n")
            else:
                sys.stderr.write(f"{TAG} run ledger: none found in ~/GitHub/.claude/run/\n")

    if as_json:
        print(json.dumps({"findings": all_findings, "ledger": ledger_summary}
                         if use_ledger else all_findings, indent=2))
    else:
        if not all_findings:
            sys.stderr.write(f"{TAG} clean — no unsupported metric/completion claims.\n")
        else:
            sys.stderr.write(f"{TAG} {len(all_findings)} claim(s) with no nearby artifact reference:\n")
            for fd in all_findings:
                sys.stderr.write(f"{TAG}   {fd['file']}:{fd['line']} [{fd['kind']}] {fd['text']}\n")
            sys.stderr.write(f"{TAG} attach a metrics/report file, command output, or commit hash near each claim.\n")

    if strict and all_findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
