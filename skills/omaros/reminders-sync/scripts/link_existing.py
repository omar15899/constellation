#!/usr/bin/env python3
"""
Propose links between pre-existing ledger tasks (those that did NOT come from
a Reminders sync) and current Apple reminders.

Use case: before reminders-sync existed, the ledger already held a few
hand-logged tasks. Some of those may correspond, semantically, to a reminder
that was later imported. This script identifies plausible pairs by fuzzy
title match — and writes a markdown report listing every candidate, ranked.

Conservative by design: never modifies state or the ledger. The output is a
review document. The user (or a follow-up command) decides whether to merge
each pair.

Usage:
    uv run link_existing.py --remote /path/to/reminders.json [--threshold 0.85]

Threshold defaults to 0.85 (titles must be at least 85 % similar by SequenceMatcher).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = Path("/Users/omarkhalil/OmarOS")
sys.path.insert(0, str(HERE))
from dedup import _norm  # noqa: E402

INDEX_PATH = VAULT / "02_Tasks_and_Execution/Ledger/_index.json"
STATE_PATH = VAULT / "02_Tasks_and_Execution/Ledger/.sync_state/reminders.json"
REPORT_DIR = VAULT / "11_Documents_and_Reports/Reminders_Sync"

REMINDERS_TAG = "reminders_app"


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remote", type=Path, required=True,
                    help="Reminders fetch JSON.")
    ap.add_argument("--threshold", type=float, default=0.85,
                    help="Minimum title similarity (default 0.85).")
    ap.add_argument("--top-k", type=int, default=3,
                    help="Show up to K candidates per pre-existing task.")
    ap.add_argument("--write-report", action="store_true")
    args = ap.parse_args()

    if not INDEX_PATH.exists():
        print(f"[link_existing] _index.json not found at {INDEX_PATH}",
              file=sys.stderr)
        return 2

    tasks = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    remote = json.loads(args.remote.read_text(encoding="utf-8"))

    # Already-linked task ids (origin reminders).
    linked = set()
    if STATE_PATH.exists():
        st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        linked = {rec.get("task_id") for rec in st.get("reminders", {}).values()}

    # Pre-existing tasks: NO reminders_app tag and not in state.
    candidates = [
        t for t in tasks
        if REMINDERS_TAG not in (t.get("tags") or [])
        and t.get("id") not in linked
    ]

    print(f"[link_existing] pre-existing tasks: {len(candidates)}",
          file=sys.stderr)
    print(f"[link_existing] remote reminders: {len(remote)}", file=sys.stderr)

    proposals: list[dict] = []
    for t in candidates:
        title = t.get("title") or ""
        if not title:
            continue
        scored: list[tuple[float, dict]] = []
        for r in remote:
            rt = r.get("name") or ""
            if not rt:
                continue
            score = _ratio(title, rt)
            if score >= args.threshold:
                scored.append((score, r))
        if not scored:
            continue
        scored.sort(key=lambda kv: -kv[0])
        proposals.append({
            "task": t,
            "candidates": [
                {"score": round(s, 3),
                 "reminder_id": r["id"],
                 "reminder_name": r.get("name", ""),
                 "reminder_list": r.get("list", "")}
                for s, r in scored[: args.top_k]
            ],
        })

    # Sort proposals by best-score descending so reviewers see the strongest first
    proposals.sort(key=lambda p: -p["candidates"][0]["score"])

    print(f"[link_existing] {len(proposals)} pre-existing tasks have at least "
          f"one candidate (≥ {args.threshold})", file=sys.stderr)

    if args.write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = REPORT_DIR / f"Link_Candidates_{ts}.md"
        lines = [
            "---",
            f"title: Pre-existing tasks ↔ reminders link candidates {ts}",
            "note_type: report",
            "domain: 11_Documents_and_Reports",
            "subdomain: Reminders_Sync",
            "tags: [reminders_sync, link_review]",
            "status: active",
            f"created: {datetime.now().date().isoformat()}",
            f"updated: {datetime.now().date().isoformat()}",
            "ai_generated: true",
            "ai_reviewed: false",
            "---",
            "",
            "# Pre-existing tasks ↔ reminders link candidates",
            "",
            f"**Threshold:** {args.threshold}  **Pre-existing:** "
            f"{len(candidates)}  **With candidates:** {len(proposals)}",
            "",
            "Each section is a pre-existing ledger task and the top-K "
            "reminders whose name is at least *threshold* similar. The pair "
            "is **not** auto-linked — review and merge by hand if you agree.",
            "",
        ]
        for prop in proposals:
            t = prop["task"]
            lines.append(f"## `{t['id']}` — {t.get('title','')[:120]}")
            lines.append("")
            for c in prop["candidates"]:
                lines.append(
                    f"- **{c['score']:.2f}** · `{c['reminder_id']}` "
                    f"_(list: {c['reminder_list']})_ — {c['reminder_name'][:120]}"
                )
            lines.append("")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[link_existing] report → {path}", file=sys.stderr)

    print(json.dumps({
        "pre_existing": len(candidates),
        "proposals": len(proposals),
        "threshold": args.threshold,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
