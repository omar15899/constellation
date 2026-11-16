#!/usr/bin/env python3
"""Generate a per-tag deep-dive report.

Given one or more tag names, walks `_index.json`, collects every matching
task, and writes a markdown report with:

  - Header: tag, total matches, breakdown by status/priority/project
  - Stats table
  - Full task list (grouped by status, sorted by date asc)
  - Each task's body and references inline (so the report is self-contained —
    no need to open the Daily file to read the ChatGPT paste)
  - Index of related tags (co-occurring tags)

Output goes to `11_Documents_and_Reports/Task_Tag_Reports/<tag>.md` by
default; override with `--out`.

Usage:
    python3 tag_report.py --tag finanzas
    python3 tag_report.py --tag mates --tag matematicas --title "Matemáticas 2025"
    python3 tag_report.py --tag renta_fija --stdout
    python3 tag_report.py --list  # inventory every tag in use, counts
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
INDEX = VAULT_ROOT / "02_Tasks_and_Execution" / "Ledger" / "_index.json"
DEFAULT_OUT_DIR = VAULT_ROOT / "11_Documents_and_Reports" / "Task_Tag_Reports"

PRI_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, None: 4}
STATUS_ORDER = ["open", "blocked", "waiting", "rolled_over", "done", "cancelled"]


def _slugify(s: str) -> str:
    import re
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")
    return s or "untitled"


def _load_index() -> list[dict]:
    if not INDEX.exists():
        sys.stderr.write(f"error: {INDEX} not found — run aggregate.py first\n")
        sys.exit(4)
    return json.loads(INDEX.read_text(encoding="utf-8"))


def _filter(items: list[dict], tags: list[str]) -> list[dict]:
    tag_set = {t.lower() for t in tags}
    out = []
    for t in items:
        task_tags = {x.lower() for x in (t.get("tags") or [])}
        if tag_set.issubset(task_tags):
            out.append(t)
    return out


def _sorted(tasks: list[dict]) -> list[dict]:
    return sorted(
        tasks,
        key=lambda t: (
            STATUS_ORDER.index(t.get("status") or "open")
            if (t.get("status") or "open") in STATUS_ORDER
            else 99,
            t.get("when") or "9999-99-99",
            PRI_RANK.get(t.get("priority")),
            t.get("id") or "",
        ),
    )


def _render_report(tags: list[str], tasks: list[dict], title: str | None) -> str:
    today = dt.date.today().isoformat()
    hdr_title = title or f"Task report — tag: {', '.join(tags)}"

    by_status = Counter(t.get("status") or "open" for t in tasks)
    by_priority = Counter(t.get("priority") or "—" for t in tasks)
    by_project = Counter(t.get("project") or "_standalone" for t in tasks)
    by_month = Counter(
        (t.get("when") or "")[:7] or "undated" for t in tasks
    )

    co_tags: Counter = Counter()
    for t in tasks:
        for tg in t.get("tags") or []:
            if tg not in tags:
                co_tags[tg] += 1

    lines = [
        "---",
        f'title: "{hdr_title}"',
        "note_type: task_tag_report",
        f"domain: 11_Documents_and_Reports",
        f"tags_queried: [{', '.join(tags)}]",
        f"matches: {len(tasks)}",
        f"generated: {today}",
        "status: generated",
        "tags: [task, task_report, generated]",
        "author: Omar",
        "ai_generated: true",
        "ai_reviewed: false",
        f"created: {today}",
        f"updated: {today}",
        "---",
        "",
        f"# {hdr_title}",
        "",
        f"Query: `{' ∧ '.join(tags)}` · {len(tasks)} tasks · generated {today}",
        "",
        "## Overview",
        "",
        "| metric | value |",
        "|--------|-------|",
        f"| total matches | {len(tasks)} |",
        f"| distinct projects | {len([p for p in by_project if p != '_standalone'])} |",
        f"| distinct months | {len([m for m in by_month if m != 'undated'])} |",
        f"| undated | {by_month.get('undated', 0)} |",
        "",
        "### By status",
        "",
        "| status | count |",
        "|--------|-------|",
    ]
    for s in STATUS_ORDER:
        c = by_status.get(s, 0)
        if c:
            lines.append(f"| {s} | {c} |")
    lines += [
        "",
        "### By priority",
        "",
        "| priority | count |",
        "|----------|-------|",
    ]
    for p in ("P0", "P1", "P2", "P3", "—"):
        c = by_priority.get(p, 0)
        if c:
            lines.append(f"| {p} | {c} |")

    if any(p != "_standalone" for p in by_project):
        lines += [
            "",
            "### By project",
            "",
            "| project | count |",
            "|---------|-------|",
        ]
        for p, c in sorted(by_project.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {p} | {c} |")

    if by_month:
        lines += [
            "",
            "### By month",
            "",
            "| month | count |",
            "|-------|-------|",
        ]
        for m in sorted(by_month.keys()):
            lines.append(f"| {m or 'undated'} | {by_month[m]} |")

    if co_tags:
        lines += [
            "",
            "## Co-occurring tags",
            "",
            "Tags that appear alongside the query on the matched tasks, ranked by frequency.",
            "",
            "| tag | co-occurrences |",
            "|-----|----------------|",
        ]
        for tg, c in co_tags.most_common(30):
            lines.append(f"| `{tg}` | {c} |")

    # Tasks grouped by status
    lines += ["", "## Tasks", ""]
    grouped: dict[str, list[dict]] = defaultdict(list)
    for t in _sorted(tasks):
        grouped[t.get("status") or "open"].append(t)

    for status in STATUS_ORDER:
        lst = grouped.get(status, [])
        if not lst:
            continue
        lines += [f"### status: {status}  ({len(lst)})", ""]
        for t in lst:
            tid = t.get("id") or "—"
            title = t.get("title") or "(untitled)"
            when = t.get("when") or "—"
            pri = t.get("priority") or "—"
            proj = t.get("project") or "—"
            tt = ", ".join(t.get("tags") or []) or "—"
            lines += [
                f"#### `{tid}` — {title}",
                "",
                f"- **when**: {when}  ·  **priority**: {pri}  ·  **project**: {proj}",
                f"- **tags**: {tt}",
            ]
            if t.get("duration_min"):
                lines.append(f"- **duration**: {t['duration_min']} min")
            if t.get("closed_at"):
                lines.append(f"- **closed_at**: {t['closed_at']}")
            body = t.get("body")
            refs = t.get("references")
            if body:
                lines += ["", "**Body:**", "", "```text", str(body), "```"]
            if refs:
                lines += ["", "**References:**", "", "```text", str(refs), "```"]
            lines.append("")

    return "\n".join(lines) + "\n"


def _list_tags() -> None:
    items = _load_index()
    counts: Counter = Counter()
    for t in items:
        for tg in t.get("tags") or []:
            counts[tg] += 1
    print("| tag | count |")
    print("|-----|-------|")
    for tg, c in counts.most_common():
        print(f"| `{tg}` | {c} |")
    print()
    print(f"total distinct tags: {len(counts)}  ·  total tag-occurrences: {sum(counts.values())}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", action="append", default=[],
                    help="tag to require; repeat for AND of tags")
    ap.add_argument("--title", help="override the report title")
    ap.add_argument("--out", help="output path (default: 11_Documents_and_Reports/Task_Tag_Reports/<slug>.md)")
    ap.add_argument("--stdout", action="store_true", help="print to stdout instead of writing a file")
    ap.add_argument("--list", action="store_true",
                    help="inventory every tag in the ledger with counts")
    args = ap.parse_args()

    if args.list:
        _list_tags()
        return

    if not args.tag:
        sys.stderr.write("error: --tag is required (or use --list)\n")
        sys.exit(2)

    items = _load_index()
    matched = _filter(items, args.tag)
    content = _render_report(args.tag, matched, args.title)

    if args.stdout:
        sys.stdout.write(content)
        return

    if args.out:
        out = Path(args.out)
    else:
        DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
        slug = "_and_".join(_slugify(t) for t in args.tag)
        out = DEFAULT_OUT_DIR / f"{slug}.md"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(json.dumps({
        "action": "tag_report",
        "tags": args.tag,
        "matches": len(matched),
        "out": str(out.relative_to(VAULT_ROOT)) if out.is_absolute() else str(out),
    }, indent=2))


if __name__ == "__main__":
    main()
