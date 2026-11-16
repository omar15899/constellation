#!/usr/bin/env python3
"""Query the structured event log stream.

Reads one or more `docs/event_logs/YYYY-MM-DD.jsonl` files, filters by
kind / domain / theme / author / severity / substring, optionally
aggregates by a grouping key, and renders as table / json / timeline.

Args (all optional unless stated otherwise):

    --date <DATE>            exactly one day (YYYY-MM-DD, today, yesterday)
    --since <DATE|REL>       inclusive start (e.g. 7.days.ago, this_week)
    --until <DATE>           inclusive end (default: today)
    --kind K[,K...]          one or more kinds (commit, error, …)
    --domain D[,D...]        filter commits by top-level domain key
    --theme T[,T...]         filter commits by theme
    --author SUBSTR          substring match on author name or email
    --severity S[,S...]      filter errors/incidents by severity
    --contains SUBSTR        substring match on subject/message
    --group-by KEY           aggregate by key (kind, domain, theme, hour, author, severity)
    --sum FIELD              when grouping, sum this field (files_changed, insertions, deletions)
    --render MODE            table | json | timeline | summary       (default: table)
    --utc                    print timestamps in UTC (default: local)
    --limit N                cap output rows (default: 200)

Exit codes:
    0  ok (including empty result)
    1  bad arguments
    2  log dir not found / unreadable
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta, timezone
from pathlib import Path


OMAROS_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
EVENT_LOG_DIR = OMAROS_ROOT / "docs" / "event_logs"

VALID_RENDERS = {"table", "json", "timeline", "summary"}
VALID_GROUPS = {"kind", "domain", "theme", "hour", "author", "severity"}


def parse_rel_date(token: str) -> date:
    today = date.today()
    t = token.strip().lower()
    if t in ("today", "now"):
        return today
    if t == "yesterday":
        return today - timedelta(days=1)
    if t == "this_week":
        return today - timedelta(days=today.weekday())
    if t == "this_month":
        return today.replace(day=1)
    m = re.fullmatch(r"(\d+)\.days?\.ago", t)
    if m:
        return today - timedelta(days=int(m.group(1)))
    try:
        return date.fromisoformat(t)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"bad date '{token}': {exc}") from None


def dates_in_range(since: date, until: date) -> list[date]:
    if since > until:
        return []
    out: list[date] = []
    cur = since
    while cur <= until:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def load_events(dates: list[date]) -> list[dict]:
    events: list[dict] = []
    for d in dates:
        path = EVENT_LOG_DIR / f"{d.isoformat()}.jsonl"
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        sys.stderr.write(
                            f"warn: {path.name}:{lineno}: invalid JSON: {exc}\n"
                        )
        except OSError as exc:
            sys.stderr.write(f"warn: cannot read {path}: {exc}\n")
    return events


def matches(event: dict, args: argparse.Namespace) -> bool:
    if args.kinds and event.get("kind") not in args.kinds:
        return False
    if args.themes:
        if event.get("theme") not in args.themes:
            return False
    if args.domains:
        ev_domains = event.get("domains") or {}
        if not any(d in ev_domains for d in args.domains):
            return False
    if args.author:
        a = event.get("author") or {}
        hay = f"{a.get('name', '')} {a.get('email', '')}".lower()
        if args.author.lower() not in hay:
            return False
    if args.severities:
        if event.get("severity") not in args.severities:
            return False
    if args.contains:
        hay = f"{event.get('subject', '')} {event.get('error_message', '')}"
        if args.contains.lower() not in hay.lower():
            return False
    return True


def group_key(event: dict, key: str) -> str:
    if key == "kind":
        return event.get("kind", "unknown")
    if key == "theme":
        return event.get("theme", "unknown")
    if key == "severity":
        return event.get("severity", "unknown")
    if key == "author":
        a = event.get("author") or {}
        return a.get("name") or a.get("email") or "unknown"
    if key == "domain":
        ev_domains = event.get("domains") or {}
        if not ev_domains:
            return "root"
        return max(ev_domains.items(), key=lambda kv: kv[1])[0]
    if key == "hour":
        ts = event.get("ts", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.astimezone().strftime("%H:00")
        except ValueError:
            return "unknown"
    return "unknown"


def render_table(events: list[dict], limit: int) -> str:
    if not events:
        return "(no events)"
    kinds = {e.get("kind") for e in events}
    if kinds == {"commit"}:
        header = "| time | sha | theme | files | domain | subject |"
        sep = "|------|-----|-------|------:|--------|---------|"
    else:
        header = "| time | kind | source | summary |"
        sep = "|------|------|--------|---------|"
    rows = [header, sep]
    for e in events[:limit]:
        ts = e.get("ts", "")
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%H:%M")
        except ValueError:
            t = ts[:16] if ts else "?"
        if e.get("kind") == "commit":
            domains = e.get("domains") or {}
            top_dom = max(domains.items(), key=lambda kv: kv[1])[0] if domains else "?"
            rows.append(
                f"| {t} | `{e.get('short_sha','?')}` | {e.get('theme','?')} "
                f"| {e.get('files_changed','?')} | {top_dom} "
                f"| {e.get('subject','')[:80]} |"
            )
        else:
            summary = e.get("subject") or e.get("error_message") or e.get("skill") or ""
            rows.append(
                f"| {t} | {e.get('kind','?')} | {e.get('source','?')} | {str(summary)[:80]} |"
            )
    if len(events) > limit:
        rows.append(f"| … | | | _+{len(events)-limit} more_ |")
    return "\n".join(rows)


def render_timeline(events: list[dict], limit: int) -> str:
    if not events:
        return "(no events)"
    events = sorted(events, key=lambda e: e.get("ts", ""))
    lines: list[str] = []
    for e in events[:limit]:
        ts = e.get("ts", "")
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%H:%M:%S")
        except ValueError:
            t = "?"
        summary = e.get("subject") or e.get("error_message") or e.get("skill") or e.get("outcome") or ""
        lines.append(f"- {t} [{e.get('kind','?')}] {e.get('source','?')} — {summary}")
    if len(events) > limit:
        lines.append(f"- … (+{len(events)-limit} more)")
    return "\n".join(lines)


def render_summary(events: list[dict], group_by: str | None, sum_field: str | None) -> str:
    if group_by is None:
        group_by = "kind"
    buckets: defaultdict[str, list[dict]] = defaultdict(list)
    for e in events:
        buckets[group_key(e, group_by)].append(e)

    rows = [f"| {group_by} | count | " + (f"sum_{sum_field} |" if sum_field else "")]
    sep_cells = ["-" * max(len(group_by), 4), "----:"]
    if sum_field:
        sep_cells.append("----:")
    rows.append("| " + " | ".join(sep_cells) + " |")
    ordered = sorted(buckets.items(), key=lambda kv: len(kv[1]), reverse=True)
    for k, evs in ordered:
        line = f"| {k} | {len(evs)} |"
        if sum_field:
            total = sum(int(ev.get(sum_field, 0) or 0) for ev in evs)
            line += f" {total} |"
        rows.append(line)
    return "\n".join(rows)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", type=parse_rel_date)
    p.add_argument("--since", type=parse_rel_date)
    p.add_argument("--until", type=parse_rel_date, default=date.today())
    p.add_argument("--kind", help="comma-separated kinds")
    p.add_argument("--domain", help="comma-separated domain keys")
    p.add_argument("--theme", help="comma-separated themes")
    p.add_argument("--author", help="substring")
    p.add_argument("--severity", help="comma-separated severities")
    p.add_argument("--contains", help="substring on subject/message")
    p.add_argument("--group-by", choices=sorted(VALID_GROUPS))
    p.add_argument("--sum", dest="sum_field", choices=["files_changed", "insertions", "deletions"])
    p.add_argument("--render", choices=sorted(VALID_RENDERS), default="table")
    p.add_argument("--utc", action="store_true")
    p.add_argument("--limit", type=int, default=200)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.date and args.since:
        parser.error("--date and --since are mutually exclusive")

    if args.date:
        dates = [args.date]
    elif args.since:
        dates = dates_in_range(args.since, args.until)
    else:
        dates = [date.today()]

    if not EVENT_LOG_DIR.exists():
        sys.stderr.write(f"error: log dir not found: {EVENT_LOG_DIR}\n")
        sys.exit(2)

    args.kinds = set(args.kind.split(",")) if args.kind else set()
    args.themes = set(args.theme.split(",")) if args.theme else set()
    args.domains = set(args.domain.split(",")) if args.domain else set()
    args.severities = set(args.severity.split(",")) if args.severity else set()

    events = load_events(dates)
    filtered = [e for e in events if matches(e, args)]

    if args.group_by:
        print(render_summary(filtered, args.group_by, args.sum_field))
        return

    if args.render == "json":
        print(json.dumps(filtered, indent=2, ensure_ascii=False))
    elif args.render == "timeline":
        print(render_timeline(filtered, args.limit))
    elif args.render == "summary":
        print(render_summary(filtered, None, args.sum_field))
    else:
        print(render_table(filtered, args.limit))


if __name__ == "__main__":
    main()
