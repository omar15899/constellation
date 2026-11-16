#!/usr/bin/env python3
"""Produce a narrative daily summary of the event stream.

Reads `docs/event_logs/<date>.jsonl`, counts kinds, top themes, domain
breakdown, surfaces errors and incidents, flags anomalies against a
trailing-7-day mean, and prints a narrative summary to stdout.

Usage:
    python3 summarize_day.py today
    python3 summarize_day.py 2026-04-17
    python3 summarize_day.py today --terse
    python3 summarize_day.py --week 2026-W16

Exit codes:
    0  ok (even if the day had no events — prints an explicit note)
    1  bad arguments
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, stdev


OMAROS_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
EVENT_LOG_DIR = OMAROS_ROOT / "docs" / "event_logs"


def parse_token(token: str) -> date:
    t = token.strip().lower()
    if t in ("today", "now"):
        return date.today()
    if t == "yesterday":
        return date.today() - timedelta(days=1)
    return date.fromisoformat(t)


def parse_iso_week(token: str) -> list[date]:
    m = re.fullmatch(r"(\d{4})-w(\d{1,2})", token.lower())
    if not m:
        raise argparse.ArgumentTypeError(f"bad week '{token}' (expected YYYY-Www)")
    year, week = int(m.group(1)), int(m.group(2))
    monday = date.fromisocalendar(year, week, 1)
    return [monday + timedelta(days=i) for i in range(7)]


def load_day(d: date) -> list[dict]:
    path = EVENT_LOG_DIR / f"{d.isoformat()}.jsonl"
    if not path.exists():
        return []
    events: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def trailing_mean_commits(target: date, window: int = 7) -> tuple[float, float]:
    samples: list[int] = []
    for i in range(1, window + 1):
        d = target - timedelta(days=i)
        events = load_day(d)
        n = sum(1 for e in events if e.get("kind") == "commit")
        samples.append(n)
    if not samples:
        return 0.0, 0.0
    m = mean(samples)
    s = stdev(samples) if len(samples) > 1 else 0.0
    return m, s


def summarize(target: date, terse: bool = False) -> str:
    events = load_day(target)
    if not events:
        return f"On {target.isoformat()}: no events logged."

    kind_counts = Counter(e.get("kind", "unknown") for e in events)
    commits = [e for e in events if e.get("kind") == "commit"]
    theme_counts = Counter(e.get("theme", "chore") for e in commits)
    total_files = sum(int(e.get("files_changed", 0) or 0) for e in commits)
    total_insertions = sum(int(e.get("insertions", 0) or 0) for e in commits)
    total_deletions = sum(int(e.get("deletions", 0) or 0) for e in commits)
    domain_counter: Counter = Counter()
    for c in commits:
        for d in (c.get("domains") or {}).keys():
            domain_counter[d] += 1
    errors = [e for e in events if e.get("kind") in ("error", "incident")]

    lines: list[str] = []
    lines.append(f"**Day summary — {target.isoformat()}**")
    lines.append("")
    lines.append(
        f"On {target.isoformat()}: **{len(commits)} commits** touched **{total_files} files** "
        f"(+{total_insertions} / -{total_deletions}) across **{len(domain_counter)} domains**. "
        f"{len(errors)} errors/incidents, "
        f"{kind_counts.get('session_start', 0)} session start(s), "
        f"{kind_counts.get('session_end', 0)} session end(s)."
    )

    if terse:
        return "\n".join(lines)

    if commits:
        lines.append("")
        lines.append("**Themes**")
        for theme, n in theme_counts.most_common():
            lines.append(f"- {theme}: {n}")
        lines.append("")
        lines.append("**Top domains**")
        for d, n in domain_counter.most_common(10):
            lines.append(f"- {d}: {n}")

    if errors:
        lines.append("")
        lines.append("**Errors / incidents**")
        for e in errors[:20]:
            msg = e.get("error_message") or e.get("subject") or e.get("title") or ""
            sev = e.get("severity", "?")
            lines.append(f"- [{sev}] {e.get('source','?')}: {str(msg)[:120]}")

    # Anomaly flags
    flags: list[str] = []
    m, s = trailing_mean_commits(target)
    if s > 0 and len(commits) > m + 2 * s:
        flags.append(
            f"commit count {len(commits)} is >2σ above trailing-7-day mean ({m:.1f}±{s:.1f}) — possible burst"
        )
    elif s > 0 and len(commits) < max(0, m - 2 * s):
        flags.append(
            f"commit count {len(commits)} is >2σ below trailing-7-day mean ({m:.1f}±{s:.1f}) — quiet day"
        )
    bulky = [c for c in commits if int(c.get("insertions", 0) or 0) + int(c.get("deletions", 0) or 0) > 1000]
    if bulky:
        flags.append(f"{len(bulky)} bulk commit(s) (>1000 lines each) — review for mass edits")

    if flags:
        lines.append("")
        lines.append("**Flags**")
        for f in flags:
            lines.append(f"- {f}")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("date", nargs="?", help="target date (today, yesterday, YYYY-MM-DD)")
    p.add_argument("--week", help="summarise a whole ISO week (YYYY-Www)")
    p.add_argument("--terse", action="store_true", help="one-paragraph summary only")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.week:
        days = parse_iso_week(args.week)
        for d in days:
            print(summarize(d, terse=args.terse))
            print()
        return
    if not args.date:
        parser.error("date argument required (or use --week)")
    d = parse_token(args.date)
    print(summarize(d, terse=args.terse))


if __name__ == "__main__":
    main()
