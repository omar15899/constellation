#!/usr/bin/env python3
"""validate_levers.py — schema validator for registry/levers.yaml.

Stdlib-only. Reuses the existing reader (hooks/_levers.py) — it does NOT re-implement
the parser. Catches malformed entries before they enter persistent state, and backs both
record_lever_verdict.py (pre-write validation) and doctor.py (constellation health).

Checks (HARD = nonzero exit; WARN = advisory):
  HARD  id present, kebab-case, unique
  HARD  verdict in the canonical vocabulary
  WARN  run_class in the canonical vocabulary
  WARN  date present and ISO-8601 (YYYY-MM-DD)
  WARN  evidence present (a verdict without a backing artifact pointer is unsupported)
  WARN  closed verdict (REFUTED / CONFIRMED / NO_IMPROVEMENT) with rerun true and no rerun_guard
  WARN  OPEN lever with rerun: false (an open lever should be re-runnable)
  WARN  strategy references a declared strategy id

Usage:
    python3 .claude/scripts/validate_levers.py            # validate the real registry
    python3 .claude/scripts/validate_levers.py --path X   # validate a copy (tests)
    python3 .claude/scripts/validate_levers.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks"))
import _levers  # noqa: E402

VERDICTS = {"OPEN", "CONFIRMED", "CAPPED", "NO_IMPROVEMENT", "REFUTED", "HOLD"}
RUN_CLASSES = {"diagnostic", "broad-floor", "deployable", "production", "research", "control-plane"}
CLOSED = {"REFUTED", "CONFIRMED", "NO_IMPROVEMENT"}
# engine vocabulary (single-backtester enforcement, 2026-07-02):
#   backtestlab       — audited causal-kernel evidence (audit_root / reconciliation)
#   vectorized        — diagnostic engine; legal only below deployable/production CONFIRMED
#   vectorized-legacy — pre-enforcement CONFIRMED rows, promotion-frozen pending
#                       reconciliation; only grandfathered for date <= 2026-07-01
#   n/a               — non-PnL levers (data plumbing, controls)
ENGINES = {"backtestlab", "vectorized", "vectorized-legacy", "n/a"}
_PROVENANCE_RUN_CLASSES = {"deployable", "production"}
_LEGACY_CUTOFF = "2026-07-01"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate(path: Path | None = None) -> dict:
    if path is not None:
        _levers.levers_path = lambda: path  # redirect the reader for tests
    levers = _levers.load_levers()
    strategies = {s.get("id") for s in _levers.load_strategies()}
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()

    for lev in levers:
        lid = lev.get("id", "")
        tag = lid or "<no-id>"
        if not lid:
            errors.append(f"{tag}: missing id")
        elif not _KEBAB.match(lid):
            errors.append(f"{lid}: id is not kebab-case")
        if lid in seen:
            errors.append(f"{lid}: duplicate id")
        seen.add(lid)

        verdict = lev.get("verdict", "")
        if verdict not in VERDICTS:
            errors.append(f"{tag}: invalid verdict {verdict!r} (allowed: {sorted(VERDICTS)})")

        rc = lev.get("run_class", "")
        if rc and rc not in RUN_CLASSES:
            warnings.append(f"{tag}: unknown run_class {rc!r}")

        date = lev.get("date", "")
        if not date:
            warnings.append(f"{tag}: missing date")
        elif not _ISO.match(date):
            warnings.append(f"{tag}: date {date!r} is not ISO-8601 (YYYY-MM-DD)")

        if not lev.get("evidence") and not lev.get("memory"):
            warnings.append(f"{tag}: no evidence/memory pointer (verdict is unsupported)")

        rerun = _levers.is_truthy(lev.get("rerun"))
        if verdict in CLOSED and rerun and not lev.get("rerun_guard"):
            warnings.append(f"{tag}: closed verdict re-runnable but no rerun_guard set")
        if verdict == "OPEN" and lev.get("rerun") is not None and not rerun:
            warnings.append(f"{tag}: OPEN lever has rerun: false (should be re-runnable)")

        strat = lev.get("strategy")
        if strat and strategies and strat not in strategies:
            warnings.append(f"{tag}: strategy {strat!r} is not a declared strategy id")

        # Engine provenance (single-backtester enforcement, 2026-07-02).
        # A CONFIRMED at deployable/production must carry structured engine
        # evidence: backtestlab (with a 64-hex audit_root or a reconciliation
        # pointer), or the frozen pre-enforcement grandfather class.
        engine = lev.get("engine", "")
        if engine and engine not in ENGINES:
            errors.append(f"{tag}: unknown engine {engine!r} (allowed: {sorted(ENGINES)})")
        if verdict == "CONFIRMED" and rc in _PROVENANCE_RUN_CLASSES:
            if not engine:
                errors.append(
                    f"{tag}: CONFIRMED {rc} requires an 'engine' field "
                    "(backtestlab | vectorized-legacy)"
                )
            elif engine == "backtestlab":
                root = lev.get("audit_root", "")
                if not (_HEX64.match(root or "") or lev.get("reconciliation")):
                    errors.append(
                        f"{tag}: engine backtestlab requires a 64-hex audit_root "
                        "or a reconciliation artifact pointer"
                    )
            elif engine == "vectorized-legacy":
                if not date or date > _LEGACY_CUTOFF:
                    errors.append(
                        f"{tag}: vectorized-legacy is only grandfathered for verdicts "
                        f"dated <= {_LEGACY_CUTOFF}; a new CONFIRMED {rc} needs "
                        "engine: backtestlab evidence"
                    )
            else:
                errors.append(
                    f"{tag}: engine {engine!r} cannot back a CONFIRMED {rc} "
                    "(vectorised evidence caps at HOLD; see contracts/promotion_gate.md)"
                )

    histogram: dict[str, int] = {}
    for lev in levers:
        histogram[lev.get("verdict", "OPEN")] = histogram.get(lev.get("verdict", "OPEN"), 0) + 1

    return {
        "ok": not errors,
        "levers": len(levers),
        "histogram": dict(sorted(histogram.items())),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--path", default=None, help="Validate a specific levers.yaml (default: the registry).")
    ap.add_argument("--json", action="store_true", help="Emit JSON.")
    args = ap.parse_args()
    result = validate(Path(args.path) if args.path else None)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASS" if result["ok"] else "FAIL"
        if result["ok"] and result["warnings"]:
            status = "WARN"
        print(f"LEVER REGISTRY: {status}")
        print(f"levers: {result['levers']}")
        for verdict, count in result["histogram"].items():
            print(f"  {verdict}: {count}")
        for err in result["errors"]:
            print(f"ERROR: {err}")
        for warn in result["warnings"]:
            print(f"warning: {warn}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
