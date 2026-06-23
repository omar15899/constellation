#!/usr/bin/env python3
"""evidence_audit.py — flag metric / completion claims that lack a nearby
artifact reference.

Usage:
    evidence_audit.py [PATH ...]     audit given files/dirs
    evidence_audit.py                audit default report dirs under CWD
    evidence_audit.py --strict ...   exit 1 if any unsupported claim is found
    evidence_audit.py --json   ...   machine-readable findings on stdout

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
# Hard artifact references that count as evidence.
ARTIFACT = re.compile(
    r"(?i)(metrics?\.json|report\.json|manifest\.json|results?\.json|\.csv|\.parquet"
    r"|\.png|pytest|exit\s*code\s*0|passed|✓|\bPASS\b|commit\s+[0-9a-f]{7,40}"
    r"|\b[0-9a-f]{7,40}\b|artifact|figure\s*\d)"
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


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    as_json = "--json" in argv
    paths = [a for a in argv if not a.startswith("--")]

    all_findings: list[dict] = []
    for f in iter_target_files(paths):
        all_findings += audit_file(f)

    if as_json:
        print(json.dumps(all_findings, indent=2))
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
