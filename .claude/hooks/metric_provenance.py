#!/usr/bin/env python3
"""metric_provenance.py — PostToolUse provenance gate for research artifacts.

Fires after Write/Edit/MultiEdit. Deterministic, filesystem-level checks that
complement (do NOT duplicate) evidence_audit.py — that tool audits report *prose*
for metric-claims-without-a-nearby-artifact-reference; this tool audits the
*filesystem*:

  HARD (blocks by default, exit 2): a report/output file references a CONCRETE
    result artifact path (e.g. reports/promotion_curated.json, outputs/.../pnl.csv,
    a .parquet/.npy/.pkl/.feather file) that DOES NOT EXIST on disk. A metric
    backed by a dangling artifact path is the unambiguous "numero sin artefacto"
    failure mode the workflow exists to stop.

  SOFT (advisory unless METRIC_PROVENANCE_STRICT=1): a research python file uses
    an RNG (numpy/random) without setting a seed — a reproducibility risk.

Scope is deliberately narrow to keep false positives near zero:
  - report/output files: acted on only when the written path lives under a
    reports|outputs|results|docs dir OR is named like a report/metrics/result,
    and NEVER under .claude/ (these workflow docs reference metrics.json etc. as
    examples on purpose).
  - referenced paths are flagged only when concrete (no glob/URL) and carrying a
    result-artifact suffix or a results-ish name.

Env switches:
    METRIC_PROVENANCE_DISABLE=1   turn the gate off entirely
    METRIC_PROVENANCE_STRICT=1    let the soft seed check block too

Safety contract: on ANY internal error, exit 0 — never brick a write on a bug
in the gate.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

TAG = "[constellation:metric_provenance]"

# A written file is treated as a research report/output when its path matches.
REPORT_DIR = re.compile(r"(?i)(^|/)(reports?|outputs?|results?|docs)(/|$)")
REPORT_NAME = re.compile(r"(?i)(report|metrics?|results?|promotion|summary|pnl)")
REPORT_SUFFIX = {".md", ".txt", ".json", ".rst", ".log"}

# Concrete result-artifact references whose existence we enforce.
#   - any path ending in a hard data suffix, OR
#   - a results-ish-named .json/.csv/.parquet
HARD_SUFFIX = re.compile(r"(?i)\.(csv|parquet|npy|feather|pkl)$")
RESULTISH = re.compile(r"(?i)(report|metrics?|results?|promotion|pnl|manifest)[\w./-]*\.(json|csv|parquet)$")
# Token that looks like a relative/explicit artifact path (not a URL, not a glob).
PATH_TOKEN = re.compile(r"(?<![\w./-])([\w][\w./-]*\.(?:json|csv|parquet|npy|feather|pkl))(?![\w/])")

# RNG usage without a seed (soft).
RNG_USE = re.compile(r"(?i)\b(np\.random\.|numpy\.random\.|\brandom\.(?:random|randint|shuffle|sample|choice)"
                     r"|RandomState\(|default_rng\(|\.sample\(|\.shuffle\()")
SEED_SET = re.compile(r"(?i)(np\.random\.seed|numpy\.random\.seed|random\.seed|seed\s*=|random_state\s*=|"
                      r"default_rng\(\s*\d|RandomState\(\s*\d|set_seed|torch\.manual_seed)")


def emit(m: str) -> None:
    sys.stderr.write(f"{TAG} {m}\n")


def hook_file_path() -> str:
    try:
        payload = sys.stdin.read() if not sys.stdin.isatty() else ""
        data = json.loads(payload) if payload.strip() else {}
    except Exception:
        return ""
    ti = data.get("tool_input", {}) or {}
    return ti.get("file_path") or ti.get("path") or ""


def repo_root(start: Path) -> Path:
    p = start if start.is_dir() else start.parent
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    return p


def is_report(path: Path) -> bool:
    s = str(path)
    if "/.claude/" in s or s.endswith("/.claude"):
        return False
    if path.suffix.lower() not in REPORT_SUFFIX:
        return False
    return bool(REPORT_DIR.search(s) or REPORT_NAME.search(path.name))


def referenced_artifacts(text: str) -> list[str]:
    out = []
    for m in PATH_TOKEN.finditer(text):
        tok = m.group(1)
        if "*" in tok or "?" in tok or "{" in tok or "://" in tok:
            continue
        if HARD_SUFFIX.search(tok) or RESULTISH.search(tok):
            out.append(tok)
    # de-dup, stable
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            seen.add(t); uniq.append(t)
    return uniq


def missing_artifacts(report: Path) -> list[str]:
    try:
        text = report.read_text(errors="ignore")
    except Exception:
        return []
    root = repo_root(report)
    bases = [report.parent, Path.cwd(), root]
    missing = []
    for tok in referenced_artifacts(text):
        cand = Path(tok)
        if cand.is_absolute():
            if not cand.exists():
                missing.append(tok)
            continue
        if not any((b / tok).exists() for b in bases):
            missing.append(tok)
    return missing


def seedless_rng(path: Path) -> bool:
    if path.suffix.lower() != ".py":
        return False
    if "/.claude/" in str(path):
        return False
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return False
    return bool(RNG_USE.search(text)) and not SEED_SET.search(text)


def main() -> int:
    if os.environ.get("METRIC_PROVENANCE_DISABLE", "").strip() in ("1", "true", "yes"):
        return 0
    fp = hook_file_path()
    if not fp:
        return 0
    path = Path(fp)
    if not path.exists():
        return 0

    strict = os.environ.get("METRIC_PROVENANCE_STRICT", "").strip() in ("1", "true", "yes")

    hard: list[str] = []
    if is_report(path):
        for tok in missing_artifacts(path):
            hard.append(f"{path.name} references artifact '{tok}' that does not exist on disk")

    soft: list[str] = []
    if seedless_rng(path):
        soft.append(f"{path.name} uses an RNG with no seed — result is not reproducible")

    if hard:
        emit("BLOCKED — metric provenance:")
        for h in hard:
            emit(f"  hard: {h}")
        emit("A metric backed by a missing artifact is unsupported. Generate the artifact, "
             "fix the path, or remove the claim. (METRIC_PROVENANCE_DISABLE=1 to bypass.)")
        if strict and soft:
            for s in soft:
                emit(f"  soft: {s}")
        return 2

    if soft:
        if strict:
            emit("BLOCKED — reproducibility (strict):")
            for s in soft:
                emit(f"  {s}")
            return 2
        for s in soft:
            emit(f"advisory (set METRIC_PROVENANCE_STRICT=1 to enforce): {s}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
