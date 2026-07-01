#!/usr/bin/env python3
"""Promotion-enforcement tests: vectorised-only evidence cannot become CONFIRMED.

Stdlib-only, no pytest. Exercises the two constellation gates end-to-end
against throwaway copies of the registry:

  1. record_lever_verdict.py REFUSES a CONFIRMED deployable/production
     without BacktestLab provenance — in EVERY mode (implementation included).
  2. record_lever_verdict.py accepts the same verdict when the artifact
     carries a backtestlab.audit_root, and when a reconciliation artifact
     self-identifies as BacktestLab PASS — while a bare {"status": "PASS"}
     is rejected.
  3. validate_levers.py hard-fails a NEW CONFIRMED deployable row with
     vectorised-only engine values (including a post-cutoff
     vectorized-legacy claim), and passes engine: backtestlab + audit_root.

Run:  python3 .claude/tests/test_promotion_enforcement.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HUB = Path(__file__).resolve().parents[1]
RECORDER = HUB / "scripts" / "record_lever_verdict.py"
sys.path.insert(0, str(HUB / "scripts"))
import validate_levers  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  {status}  {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def _fresh_registry(tmp: Path) -> tuple[Path, Path]:
    levers = tmp / "levers.yaml"
    ledger = tmp / "research_ledger.md"
    levers.write_text(
        "schema_version: 1\ngenerated_by: test\nlevers:\n"
        "  - id: seed-lever\n"
        "    hypothesis: \"seed\"\n"
        "    verdict: OPEN\n"
        "    date: 2026-07-02\n"
        "    rerun: true\n"
        "    evidence: \"memory:seed\"\n"
        "strategies: []\n"
    )
    ledger.write_text("# ledger\n\n| id | verdict |\n|---|---|\n")
    return levers, ledger


def _record(tmp: Path, artifact: Path | None, mode: str) -> subprocess.CompletedProcess[str]:
    levers, ledger = _fresh_registry(tmp)
    cmd = [
        sys.executable,
        str(RECORDER),
        "--lever",
        "test-lever",
        "--verdict",
        "CONFIRMED",
        "--run-class",
        "deployable",
        "--mode",
        mode,
        "--levers-path",
        str(levers),
        "--ledger-path",
        str(ledger),
        "--summary",
        "test",
    ]
    if artifact is not None:
        cmd += ["--artifact", str(artifact)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> int:
    print("Promotion enforcement tests")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        md_artifact = tmp / "evaluation.md"
        md_artifact.write_text("# report claiming Sharpe 9.9\n")
        vector_metrics = tmp / "vector_only" / "metrics.json"
        vector_metrics.parent.mkdir()
        vector_metrics.write_text(json.dumps({"financial": {"sharpe": 1.45}}))
        audited_metrics = tmp / "audited" / "metrics.json"
        audited_metrics.parent.mkdir()
        audited_metrics.write_text(
            json.dumps({"backtestlab": {"audit_root": "c" * 64, "sharpe": 0.7}})
        )
        recon_pass = tmp / "reconciliation.json"
        recon_pass.write_text(
            json.dumps({"engine": "BacktestLab", "status": "PASS", "audit_root": "d" * 64})
        )
        bare_pass = tmp / "bare_pass.json"
        bare_pass.write_text(json.dumps({"status": "PASS"}))

        # 1 — refusal in every mode without provenance
        for mode in ("casual", "implementation", "research_strict"):
            r = _record(tmp, md_artifact, mode)
            check(
                f"markdown-evidence CONFIRMED deployable refused in {mode}",
                r.returncode == 2 and "REFUSED" in r.stdout,
                r.stdout[-200:],
            )
        r = _record(tmp, vector_metrics, "implementation")
        check(
            "vectorised-only metrics.json refused (no backtestlab block)",
            r.returncode == 2 and "REFUSED" in r.stdout,
            r.stdout[-200:],
        )
        r = _record(tmp, None, "implementation")
        check(
            "missing artifact refused",
            r.returncode == 2 and "REFUSED" in r.stdout,
            r.stdout[-200:],
        )

        # 2 — audited evidence accepted; recon PASS accepted; bare PASS rejected
        r = _record(tmp, audited_metrics, "implementation")
        check(
            "backtestlab audit_root accepted (dry-run reaches diff)",
            r.returncode == 0 and "dry-run" in r.stdout,
            r.stdout[-200:],
        )
        r = _record(tmp, recon_pass, "implementation")
        check(
            "BacktestLab reconciliation PASS accepted",
            r.returncode == 0 and "dry-run" in r.stdout,
            r.stdout[-200:],
        )
        r = _record(tmp, bare_pass, "implementation")
        check(
            'bare {"status": "PASS"} rejected (no engine identity)',
            r.returncode == 2 and "REFUSED" in r.stdout,
            r.stdout[-200:],
        )

        # 3 — validator rules on new rows
        def _registry_with(engine_lines: str, date: str) -> Path:
            p = tmp / f"reg_{abs(hash(engine_lines + date))}.yaml"
            p.write_text(
                "schema_version: 1\nlevers:\n"
                "  - id: new-lever\n"
                "    hypothesis: \"x\"\n"
                "    verdict: CONFIRMED\n"
                "    run_class: deployable\n"
                f"{engine_lines}"
                f"    date: {date}\n"
                "    rerun: false\n"
                "    evidence: \"memory:x\"\n"
                "strategies: []\n"
            )
            return p

        res = validate_levers.validate(_registry_with("", "2026-07-02"))
        check("validator: missing engine on new CONFIRMED deployable fails", not res["ok"])
        res = validate_levers.validate(
            _registry_with("    engine: vectorized\n", "2026-07-02")
        )
        check("validator: engine vectorized on CONFIRMED deployable fails", not res["ok"])
        res = validate_levers.validate(
            _registry_with("    engine: vectorized-legacy\n", "2026-07-02")
        )
        check("validator: post-cutoff vectorized-legacy claim fails", not res["ok"])
        res = validate_levers.validate(
            _registry_with("    engine: vectorized-legacy\n", "2026-07-01")
        )
        check("validator: pre-cutoff vectorized-legacy grandfathered", res["ok"], str(res["errors"]))
        res = validate_levers.validate(
            _registry_with(
                "    engine: backtestlab\n    audit_root: " + "a" * 64 + "\n", "2026-07-02"
            )
        )
        check("validator: backtestlab + audit_root passes", res["ok"], str(res["errors"]))
        res = validate_levers.validate(
            _registry_with("    engine: backtestlab\n", "2026-07-02")
        )
        check("validator: backtestlab without audit_root/reconciliation fails", not res["ok"])

    # The live registry must be green under the new rules.
    live = validate_levers.validate()
    check("live registry passes under enforcement", live["ok"], str(live["errors"]))

    print("=" * 50)
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        return 1
    print("all promotion-enforcement tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
