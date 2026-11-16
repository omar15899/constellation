#!/usr/bin/env python3
"""Post-write safety linter for the LLM-elevated NewsLab daily report.

The headless Claude step is told (in its prompt and system framing) to stay
observation-only and to preserve NewsLab's mandatory caveats verbatim. Prompt
instructions are necessary but not sufficient — this linter is the deterministic
gate that actually enforces the NewsLab safety contract on the produced text:

1. The deterministic report's "Methodological caveats" block (the
   ``Y_t = h(Z_t) + epsilon_t`` observation model and its consequences) must be
   reproduced verbatim. Dropping or paraphrasing it fails the run.
2. The report must not emit trade signals: no buy/sell ratings, price targets,
   directional price forecasts, expected returns, or over/under-weight calls.
   The study is monitoring/research about a *media* process, never an order.

A non-empty violation list means the LLM output is discarded and the
deterministic report is kept; the pipeline exits non-zero. Failing safe.

stdlib-only by design so it runs under any interpreter (the orchestrator imports
it directly; it also works as a CLI).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Signal-emitting / predictive language forbidden in an observation report.
# Deliberately targeted at advice and price-direction claims, not ordinary
# reportage, so honest prose ("inflation rose", "the company will sell assets")
# does not trip the gate.
_FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bprice target\b", "price target"),
    (r"\b(strong\s+)?(buy|sell)\s+(rating|recommendation|signal)\b", "buy/sell rating"),
    (r"\bwe\s+recommend\s+(buying|selling|going\s+(long|short)|a\s+(long|short))\b", "trade recommendation"),
    (r"\b(go|going)\s+(long|short)\b", "long/short call"),
    (r"\b(expected|projected|forecast(ed)?)\s+returns?\b", "expected return"),
    (r"\bguaranteed\b", "guarantee language"),
    (r"\b(will|should)\s+(rise|fall|surge|plunge|rally|crash|soar|tumble|spike)\b", "directional price forecast"),
    (r"\btrade\s+signal\b", "trade signal"),
    (r"\b(over|under)weight\b", "over/under-weight call"),
    (r"\bprice\s+(will|should)\s+(reach|hit|test)\b", "price-level forecast"),
)

_CAVEAT_HEADING = "## Methodological caveats"


def extract_caveats(deterministic_md: str) -> str:
    """Return the deterministic report's Methodological caveats section, trimmed.

    The section runs from the ``## Methodological caveats`` heading to the next
    ``## `` heading (or end of file). This exact block is the contract the
    elevated report must reproduce verbatim.
    """
    start = deterministic_md.find(_CAVEAT_HEADING)
    if start == -1:
        return ""
    body_start = start + len(_CAVEAT_HEADING)
    nxt = deterministic_md.find("\n## ", body_start)
    section = deterministic_md[body_start:] if nxt == -1 else deterministic_md[body_start:nxt]
    return section.strip()


def _normalise(text: str) -> str:
    """Collapse whitespace so a faithful copy still matches across re-wrapping."""
    return re.sub(r"\s+", " ", text).strip()


def lint(generated_md: str, deterministic_md: str) -> list[str]:
    """Return a list of safety violations; empty means the report may publish."""
    violations: list[str] = []

    caveats = extract_caveats(deterministic_md)
    if not caveats:
        violations.append("deterministic report carries no Methodological caveats block to enforce")
    elif _normalise(caveats) not in _normalise(generated_md):
        violations.append("mandatory Methodological caveats block is missing or altered (not reproduced verbatim)")

    for pattern, label in _FORBIDDEN_PATTERNS:
        match = re.search(pattern, generated_md, flags=re.IGNORECASE)
        if match:
            violations.append(f"forbidden signal-language [{label}]: {match.group(0)!r}")

    return violations


def _main() -> int:
    parser = argparse.ArgumentParser(description="Lint an LLM-elevated NewsLab report for the safety contract.")
    parser.add_argument("--generated", type=Path, required=True, help="The LLM-elevated report.")
    parser.add_argument("--deterministic", type=Path, required=True, help="The source deterministic report.")
    args = parser.parse_args()

    violations = lint(
        args.generated.read_text(encoding="utf-8"),
        args.deterministic.read_text(encoding="utf-8"),
    )
    if violations:
        print("SAFETY LINT FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("safety lint passed")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
