#!/usr/bin/env python3
"""record_lever_verdict.py — the deterministic writer behind /gate-check.

Until now /gate-check's step 6 ("append or update the lever in levers.yaml + mirror the row
in research_ledger.md") was prompt-discipline: Claude hand-edited the YAML. This makes that
step a transaction: validate -> update levers.yaml (comment-preserving line edits) -> mirror
research_ledger.md -> bump last_updated, atomically, never silently overwriting a verdict
(a verdict change is always logged in the note). The user still DECIDES the verdict via
/gate-check; this only RECORDS it. Stdlib-only; reuses hooks/_levers.py + validate_levers.py.

Dry-run by default (prints the diff); --apply writes. Refuses to write if validate_levers
fails, or (research_strict) if CONFIRMED lacks the four-bar metrics, or if the evidence
artifact is missing (unless --external).

Usage:
    python3 .claude/scripts/record_lever_verdict.py --lever ucits-trend-sleeve \\
        --verdict CONFIRMED --run-class deployable --artifact reports/ucits_trend.json \\
        --summary "UCITS-mapped trend sleeve survives costs." --mode research_strict \\
        --sharpe 1.31 --dsr 0.97 --pbo 0.08 --ci-low 0.4 --p-bh 0.03 --m 24 --apply
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
from pathlib import Path

_HUB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_HUB / "hooks"))
sys.path.insert(0, str(_HUB / "scripts"))
import _levers  # noqa: E402
import validate_levers as _vl  # noqa: E402

_LEVERS = _HUB / "registry" / "levers.yaml"
_LEDGER = _HUB / "research_ledger.md"
_REPO_ROOT = Path.home() / "GitHub"
_FOUR_BARS = ("sharpe", "dsr", "pbo", "ci_low", "p_bh")
# run classes whose CONFIRMED additionally requires BacktestLab engine
# provenance (contracts/promotion_gate.md, "Engine provenance", 2026-07-01)
_PROVENANCE_RUN_CLASSES = {"deployable", "production"}


def _resolve_artifact(artifact: str, repo: str | None) -> Path | None:
    """Resolve the evidence artifact the same way the existence gate does."""
    cand = Path(artifact)
    if cand.is_absolute():
        return cand if cand.exists() else None
    roots = [Path.cwd(), _REPO_ROOT]
    if repo:
        roots.insert(0, _REPO_ROOT / repo)
    for r in roots:
        if (r / artifact).exists():
            return r / artifact
    return None


def _has_backtestlab_provenance(artifact_path: Path | None) -> bool:
    """True iff the artifact carries audited-engine evidence.

    Accepted forms: a JSON whose `backtestlab` block has a non-null
    `audit_root`; a JSON that IS an audited metrics dict (top-level
    `audit_root`); a reconciliation artifact with `status`/`reconciliation.status`
    == PASS; or a sibling metrics.json in the artifact's directory satisfying
    the first two forms.
    """
    import json

    def _check(p: Path) -> bool:
        if not p.exists() or p.suffix.lower() != ".json":
            return False
        try:
            data = json.loads(p.read_text())
        except Exception:
            return False
        if not isinstance(data, dict):
            return False
        bt = data.get("backtestlab")
        if isinstance(bt, dict) and bt.get("audit_root"):
            return True
        if data.get("audit_root"):
            return True
        status = data.get("status") or (data.get("reconciliation") or {}).get("status")
        if status == "PASS":
            # A reconciliation artifact must self-identify as BacktestLab
            # evidence — a bare {"status": "PASS"} is not provenance.
            return data.get("engine") == "BacktestLab" or bool(
                (data.get("reconciliation") or {}).get("audit_root")
            )
        return False

    if artifact_path is None:
        return False
    if _check(artifact_path):
        return True
    sibling = artifact_path.parent / "metrics.json"
    return sibling != artifact_path and _check(sibling)


def _yaml_str(value: str) -> str:
    """Double-quote a scalar, escaping per YAML double-quoted style."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _today() -> str:
    return _dt.date.today().isoformat()


def _find_block(lines: list[str], lever_id: str) -> tuple[int, int] | None:
    """Return (start, end) line indices of the `- id: <lever_id>` block, end exclusive."""
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("- id:") and _levers._strip_scalar(line.split(":", 1)[1]) == lever_id:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        s = lines[j]
        if not s.strip():
            continue
        indent = len(s) - len(s.lstrip(" "))
        if indent == 0 or s.lstrip().startswith("- ") or (indent <= 2 and s.lstrip().startswith("#")):
            end = j
            break
    return (start, end)


def _set_field(block: list[str], field: str, value: str) -> list[str]:
    """Update or insert `    field: value` within a lever block (indent 4)."""
    line = f"    {field}: {value}"
    for i, b in enumerate(block):
        if b.lstrip().startswith(f"{field}:") and (len(b) - len(b.lstrip(" "))) == 4:
            block[i] = line
            return block
    # insert after the last indent-4 field line of the block
    last = 0
    for i, b in enumerate(block):
        if (len(b) - len(b.lstrip(" "))) == 4 and ":" in b:
            last = i
    block.insert(last + 1, line)
    return block


def _new_block(fields: dict[str, str]) -> list[str]:
    order = ["id", "hypothesis", "strategy", "repo", "verdict", "run_class", "metric",
             "gate", "evidence", "memory", "date", "rerun", "rerun_guard", "note"]
    out = [f"  - id: {fields['id']}"]
    for k in order[1:]:
        if k in fields:
            out.append(f"    {k}: {fields[k]}")
    return out


def _levers_insert_point(lines: list[str]) -> int:
    """End of the `levers:` list (before a trailing top-level/summary comment, else EOF)."""
    in_block = False
    end = len(lines)
    for i, line in enumerate(lines):
        if not in_block:
            if line.strip() == "levers:":
                in_block = True
            continue
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            end = i
            break
    # trim trailing blanks before the boundary
    while end > 0 and lines[end - 1].strip() == "":
        end -= 1
    return end


def record(args: argparse.Namespace) -> dict:
    text = _LEVERS.read_text()
    lines = text.splitlines()
    existing = {lv.get("id"): lv for lv in _levers.load_levers()}.get(args.lever)
    today = _today()
    metrics = {b: getattr(args, b) for b in _FOUR_BARS if getattr(args, b) is not None}
    metric_str = args.metric or (
        ", ".join(f"{k}={v}" for k, v in metrics.items()) if metrics else "")

    # never silently overwrite: a verdict change is recorded in the note
    note = args.summary or ""
    if existing and existing.get("verdict") and existing["verdict"] != args.verdict:
        note = f"verdict {existing['verdict']}->{args.verdict} ({today}): {note}".strip()

    fields = {
        "verdict": args.verdict,
        "date": today,
        "rerun": str(args.rerun).lower(),
    }
    if args.run_class:
        fields["run_class"] = args.run_class
    if metric_str:
        fields["metric"] = _yaml_str(metric_str)
    if args.artifact:
        fields["evidence"] = _yaml_str(args.artifact)
    if args.memory:
        fields["memory"] = args.memory
    if args.rerun_guard:
        fields["rerun_guard"] = _yaml_str(args.rerun_guard)
    if note:
        fields["note"] = _yaml_str(note)

    block_range = _find_block(lines, args.lever)
    if block_range is not None:
        start, end = block_range
        block = lines[start:end]
        for k, v in fields.items():
            block = _set_field(block, k, v)
        lines = lines[:start] + block + lines[end:]
        action = "update"
    else:
        new = dict(fields)
        new["id"] = args.lever
        if args.hypothesis:
            new["hypothesis"] = _yaml_str(args.hypothesis)
        if args.strategy:
            new["strategy"] = args.strategy
        if args.repo:
            new["repo"] = args.repo
        ins = _levers_insert_point(lines)
        block = _new_block(new)
        lines = lines[:ins] + [""] + block + lines[ins:]
        action = "add"

    # bump last_updated
    for i, line in enumerate(lines):
        if line.startswith("last_updated:"):
            lines[i] = f"last_updated: {today}"
            break

    new_text = "\n".join(lines) + "\n"

    # mirror research_ledger.md
    ledger = _LEDGER.read_text()
    rc = f" *{args.run_class}.*" if args.run_class else ""
    row = f"- `{args.lever}` — {args.summary or args.verdict}.{rc}"
    ledger_lines = ledger.splitlines()
    led_action = "append"
    for i, line in enumerate(ledger_lines):
        if line.startswith(f"- `{args.lever}`"):
            ledger_lines[i] = row
            led_action = "update"
            break
    if led_action == "append":
        ledger_lines.append(row)
    new_ledger = "\n".join(ledger_lines) + "\n"

    return {"action": action, "led_action": led_action, "new_text": new_text,
            "new_ledger": new_ledger, "old_text": text, "old_ledger": ledger, "note": note}


def _diff(old: str, new: str, label: str) -> str:
    import difflib
    d = difflib.unified_diff(old.splitlines(), new.splitlines(), f"a/{label}", f"b/{label}", lineterm="")
    return "\n".join(d)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lever", required=True)
    ap.add_argument("--verdict", required=True, choices=sorted(_vl.VERDICTS))
    ap.add_argument("--run-class", dest="run_class", default=None, choices=sorted(_vl.RUN_CLASSES))
    ap.add_argument("--artifact", default=None, help="Evidence artifact path (repo-relative or absolute).")
    ap.add_argument("--external", action="store_true", help="Evidence is external/not-on-disk; skip existence check.")
    ap.add_argument("--summary", default="")
    ap.add_argument("--memory", default=None)
    ap.add_argument("--metric", default=None, help="Free-text metric line (else built from the four bars).")
    ap.add_argument("--rerun", default="false", choices=["true", "false"])
    ap.add_argument("--rerun-guard", dest="rerun_guard", default=None)
    ap.add_argument("--hypothesis", default=None)
    ap.add_argument("--strategy", default=None)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--mode", default="implementation", choices=["casual", "implementation", "research_strict"])
    for bar in _FOUR_BARS:
        ap.add_argument(f"--{bar.replace('_', '-')}", dest=bar, default=None)
    ap.add_argument("--levers-path", default=None, help="Override registry path (tests).")
    ap.add_argument("--ledger-path", default=None, help="Override ledger path (tests).")
    ap.add_argument("--apply", action="store_true", help="Write the change (default: dry-run diff).")
    args = ap.parse_args()

    global _LEVERS, _LEDGER
    if args.levers_path:
        _LEVERS = Path(args.levers_path)
        _levers.levers_path = lambda: _LEVERS
    if args.ledger_path:
        _LEDGER = Path(args.ledger_path)

    # gate: pre-write validation + strict-mode metric requirement + evidence existence
    pre = _vl.validate(_LEVERS)
    if not pre["ok"]:
        print("REFUSED: levers.yaml fails validation before write:")
        for e in pre["errors"]:
            print(f"  ERROR: {e}")
        return 2
    if args.mode == "research_strict" and args.verdict == "CONFIRMED":
        missing = [b for b in _FOUR_BARS if getattr(args, b) is None]
        if missing:
            print(f"REFUSED: research_strict CONFIRMED requires the four-bar metrics; missing: {missing}")
            return 2
    if args.verdict == "CONFIRMED" and (args.run_class or "") in _PROVENANCE_RUN_CLASSES:
        resolved = _resolve_artifact(args.artifact, args.repo) if args.artifact else None
        if not _has_backtestlab_provenance(resolved):
            # Refused in EVERY mode since 2026-07-02 (single-backtester
            # enforcement): a serious result without BacktestLab provenance
            # or a reconciliation PASS must be impossible to record, not
            # merely warned about. Vectorised-only evidence caps at HOLD.
            print(
                "REFUSED: CONFIRMED at run_class deployable/production requires "
                "BacktestLab engine provenance (contracts/promotion_gate.md): point "
                "--artifact at a metrics.json whose 'backtestlab' block has a "
                "non-null audit_root, or at a BacktestLab reconciliation PASS "
                "artifact. Vectorised-only evidence caps at HOLD."
            )
            return 2
    if args.artifact and not args.external:
        cand = Path(args.artifact)
        roots = [Path.cwd(), _REPO_ROOT]
        if args.repo:
            roots.insert(0, _REPO_ROOT / args.repo)
        if not (cand.is_absolute() and cand.exists()) and not any((r / args.artifact).exists() for r in roots):
            print(f"REFUSED: evidence artifact not found: {args.artifact} (use --external if intentional)")
            return 2

    result = record(args)

    print(f"== record_lever_verdict ({result['action']} lever, {result['led_action']} ledger) ==")
    print(_diff(result["old_text"], result["new_text"], "registry/levers.yaml"))
    print(_diff(result["old_ledger"], result["new_ledger"], "research_ledger.md"))

    if not args.apply:
        print("\n[dry-run] no files written. Re-run with --apply to commit the transaction.")
        return 0

    # validate the NEW levers content before replacing the real file
    tmp = _LEVERS.with_suffix(".yaml.tmp")
    tmp.write_text(result["new_text"])
    post = _vl.validate(tmp)
    if not post["ok"]:
        tmp.unlink(missing_ok=True)
        print("ABORTED: the proposed levers.yaml fails validation:")
        for e in post["errors"]:
            print(f"  ERROR: {e}")
        return 2
    os.replace(tmp, _LEVERS)
    _LEDGER.write_text(result["new_ledger"])
    print(f"\nAPPLIED. {args.lever} -> {args.verdict}. last_updated bumped.")
    if result["note"]:
        print(f"note: {result['note']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
