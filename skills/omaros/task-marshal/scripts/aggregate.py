#!/usr/bin/env python3
"""Regenerate Ledger/{Weekly,Monthly,Yearly}/*.md, _index.json, _metrics.json.

Walks Ledger/Daily/*.md, parses every YAML task block, recomputes metrics,
renders rich rollups.

Idempotent: running twice with no source change produces byte-identical output.

Usage:
    python3 aggregate.py                 # regenerate everything
    python3 aggregate.py --only 2026-W17 # restrict to one week (and its month/year)
    python3 aggregate.py --dry-run       # print what would change, write nothing
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from parse import read_all  # noqa: E402
import metrics as M  # noqa: E402
import render as R  # noqa: E402

VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
LEDGER = VAULT_ROOT / "02_Tasks_and_Execution" / "Ledger"
DAILY = LEDGER / "Daily"
WEEKLY = LEDGER / "Weekly"
MONTHLY = LEDGER / "Monthly"
YEARLY = LEDGER / "Yearly"


def _date_of(task: dict) -> dt.date | None:
    w = task.get("when")
    if w:
        try:
            return dt.date.fromisoformat(w)
        except ValueError:
            pass
    src = task.get("_source", "")
    stem = Path(src).stem if src else ""
    try:
        return dt.date.fromisoformat(stem)
    except ValueError:
        return None


def _iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _week_bounds(iso: str) -> tuple[dt.date, dt.date]:
    year, w = int(iso[:4]), int(iso[6:])
    monday = dt.date.fromisocalendar(year, w, 1)
    sunday = monday + dt.timedelta(days=6)
    return monday, sunday


# --- Weekly ---------------------------------------------------------------

def _render_weekly(iso: str, tasks: list[dict]) -> str:
    monday, sunday = _week_bounds(iso)
    today = dt.date.today()
    m = M.compute(tasks, today=today)

    # Per-day table (human scannable)
    days = [(monday + dt.timedelta(days=i)) for i in range(7)]
    per_day_rows = [
        "| day | date | total | done | top-pri |",
        "|-----|------|-------|------|---------|",
    ]
    throughput_series: dict[str, int] = {}
    for d in days:
        day_tasks = [t for t in tasks if _date_of(t) == d]
        done = sum(1 for t in day_tasks if t.get("status") == "done")
        throughput_series[d.isoformat()] = done
        top = min((t.get("priority") for t in day_tasks if t.get("priority")), default=None)
        per_day_rows.append(
            f"| {d.strftime('%a')} | {d.isoformat()} | {len(day_tasks)} | {done} | {top or '—'} |"
        )

    body = [
        "---",
        f"title: \"Weekly task rollup — {iso}\"",
        "note_type: task_ledger_weekly",
        f"week: {iso}",
        f"year: {monday.year}",
        f"month: {monday.strftime('%Y-%m')}",
        f"range: {monday.isoformat()}..{sunday.isoformat()}",
        "status: generated",
        "tags: [task, task_ledger, weekly, generated]",
        "author: Omar",
        "ai_generated: true",
        "ai_reviewed: false",
        f"created: {today.isoformat()}",
        f"updated: {today.isoformat()}",
        "---",
        "",
        f"# Weekly task rollup — {iso}",
        "",
        f"_Range_: **{monday.isoformat()} → {sunday.isoformat()}** · generated {today.isoformat()}",
        "",
        "## KPI",
        "",
        R.kpi_block(m),
        "",
        "## Throughput",
        "",
        R.mermaid_throughput_bar(throughput_series, title=f"Closed per day — {iso}"),
        "",
        "## Status distribution",
        "",
        R.mermaid_status_pie(m),
        "",
        "## Priority × Urgency quadrant",
        "",
        R.mermaid_quadrant(m["quadrant_points"]),
        "",
        "## Aging (open tasks, median days by priority)",
        "",
        R.aging_table(m),
        "",
        "## Project portfolio",
        "",
        R.project_portfolio_table(m),
        "",
        "## Per-day breakdown",
        "",
        "\n".join(per_day_rows),
        "",
        "## Full task table",
        "",
        _full_table(_sort_tasks(tasks)),
        "",
        "## Gantt (dated tasks this week)",
        "",
        R.mermaid_gantt(tasks, title=f"Week {iso}"),
        "",
        "## By tag",
        "",
        R.top_tags_table(m, n=15),
        "",
    ]
    return "\n".join(body)


# --- Monthly --------------------------------------------------------------

def _render_monthly(ym: str, tasks: list[dict]) -> str:
    today = dt.date.today()
    year, month = int(ym[:4]), int(ym[5:7])
    m = M.compute(tasks, today=today)

    # Per-week breakdown
    weeks: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        d = _date_of(t)
        if d:
            weeks[_iso_week(d)].append(t)

    week_rows = ["| week | range | total | done | completion |",
                 "|------|-------|-------|------|------------|"]
    for wk in sorted(weeks.keys()):
        lst = weeks[wk]
        done = sum(1 for t in lst if t.get("status") == "done")
        pct = (done / len(lst)) if lst else 0.0
        mo, su = _week_bounds(wk)
        week_rows.append(
            f"| [[{wk}\\|{wk}]] | {mo.isoformat()}..{su.isoformat()} | {len(lst)} "
            f"| {done} | {R.unicode_pct_bar(pct, width=10)} |"
        )

    heat_grid = M.month_heatmap(tasks, year, month)

    body = [
        "---",
        f"title: \"Monthly task rollup — {ym}\"",
        "note_type: task_ledger_monthly",
        f"month: {ym}",
        f"year: {year}",
        "status: generated",
        "tags: [task, task_ledger, monthly, generated]",
        "author: Omar",
        "ai_generated: true",
        "ai_reviewed: false",
        f"created: {today.isoformat()}",
        f"updated: {today.isoformat()}",
        "---",
        "",
        f"# Monthly task rollup — {ym}",
        "",
        "## KPI",
        "",
        R.kpi_block(m),
        "",
        "## Status distribution",
        "",
        R.mermaid_status_pie(m),
        "",
        "## Priority distribution",
        "",
        R.mermaid_priority_pie(m),
        "",
        "## Priority × Urgency quadrant",
        "",
        R.mermaid_quadrant(m["quadrant_points"]),
        "",
        "## Daily heatmap",
        "",
        R.month_heatmap_md(heat_grid, year, month),
        "",
        "## Context-switching (unique projects per day)",
        "",
        R.context_switch_sparkline(m),
        "",
        "## Project portfolio",
        "",
        R.project_portfolio_table(m),
        "",
        "## Cycle-time histogram",
        "",
        R.cycle_time_histogram(m),
        "",
        "## Gantt — all dated tasks this month",
        "",
        R.mermaid_gantt(tasks, title=f"{ym}"),
        "",
        "## Per-week breakdown",
        "",
        "\n".join(week_rows),
        "",
        "## By tag",
        "",
        R.top_tags_table(m, n=30),
        "",
        "## Full task table",
        "",
        _full_table(_sort_tasks(tasks)),
        "",
    ]
    return "\n".join(body)


# --- Yearly ---------------------------------------------------------------

def _render_yearly(year: int, tasks: list[dict]) -> str:
    today = dt.date.today()
    m = M.compute(tasks, today=today)

    months: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        d = _date_of(t)
        if d:
            months[d.strftime("%Y-%m")].append(t)

    month_rows = ["| month | total | done | completion |",
                  "|-------|-------|------|------------|"]
    for mo in sorted(months.keys()):
        lst = months[mo]
        done = sum(1 for t in lst if t.get("status") == "done")
        pct = (done / len(lst)) if lst else 0.0
        month_rows.append(
            f"| [[{mo}\\|{mo}]] | {len(lst)} | {done} | {R.unicode_pct_bar(pct, width=10)} |"
        )

    year_grid = M.year_heatmap(tasks, year)

    body = [
        "---",
        f"title: \"Yearly task rollup — {year}\"",
        "note_type: task_ledger_yearly",
        f"year: {year}",
        "status: generated",
        "tags: [task, task_ledger, yearly, generated]",
        "author: Omar",
        "ai_generated: true",
        "ai_reviewed: false",
        f"created: {today.isoformat()}",
        f"updated: {today.isoformat()}",
        "---",
        "",
        f"# Yearly task rollup — {year}",
        "",
        "## KPI",
        "",
        R.kpi_block(m),
        "",
        "## Monthly throughput",
        "",
        R.mermaid_monthly_throughput(m["throughput_by_day"], year),
        "",
        "## Year heatmap",
        "",
        R.year_heatmap_md(year_grid, year),
        "",
        "## Status distribution",
        "",
        R.mermaid_status_pie(m),
        "",
        "## Project portfolio (annualised)",
        "",
        R.project_portfolio_table(m),
        "",
        "## Cycle-time histogram",
        "",
        R.cycle_time_histogram(m),
        "",
        "## Per-month breakdown",
        "",
        "\n".join(month_rows),
        "",
        "## Top tags",
        "",
        R.top_tags_table(m, n=40),
        "",
    ]
    return "\n".join(body)


# --- helpers -------------------------------------------------------------

PRI_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, None: 4}


def _sort_tasks(tasks: list[dict]) -> list[dict]:
    return sorted(tasks, key=lambda t: (
        t.get("when") or "9999-99-99",
        PRI_RANK.get(t.get("priority")),
        t.get("created_at") or "",
        t.get("id") or "",
    ))


def _full_table(tasks: list[dict]) -> str:
    if not tasks:
        return "_no tasks_\n"
    header = ("| date | time | status | pri | title | project | tags | min | id |\n"
              "|------|------|--------|-----|-------|---------|------|-----|----|")
    glyph = {"open": "○", "done": "✓", "cancelled": "✗", "rolled_over": "→",
             "blocked": "■", "waiting": "…"}
    rows = []
    for t in tasks:
        tags = ", ".join(t.get("tags") or []) or "—"
        status = t.get("status") or "open"
        rows.append(
            f"| {t.get('when') or '—'} "
            f"| {t.get('time_of_day') or '—'} "
            f"| {glyph.get(status, '?')} {status} "
            f"| {t.get('priority') or '—'} "
            f"| {t.get('title') or '—'} "
            f"| {t.get('project') or '—'} "
            f"| {tags} "
            f"| {t.get('duration_min') or '—'} "
            f"| `{t.get('id', '')}` |"
        )
    return header + "\n" + "\n".join(rows) + "\n"


def _write_if_changed(path: Path, content: str, dry: bool) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return True


# --- main ----------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="restrict to one ISO week (e.g. 2026-W17)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    all_tasks = read_all(DAILY)

    # Flat index
    flat = [{k: v for k, v in t.items() if k != "_source"} for t in all_tasks]
    flat.sort(key=lambda x: (x.get("when") or "9999-99-99", x.get("id") or ""))

    changes: list[str] = []

    # _index.json
    idx_path = LEDGER / "_index.json"
    idx_content = json.dumps(flat, indent=2, ensure_ascii=False) + "\n"
    if _write_if_changed(idx_path, idx_content, args.dry_run):
        changes.append(str(idx_path.relative_to(VAULT_ROOT)))

    # _by_tag.json
    by_tag: dict[str, list[str]] = defaultdict(list)
    for t in flat:
        for tag in t.get("tags") or []:
            by_tag[tag].append(t.get("id"))
    by_tag_content = json.dumps({k: by_tag[k] for k in sorted(by_tag)},
                                indent=2, ensure_ascii=False) + "\n"
    by_tag_path = LEDGER / "_by_tag.json"
    if _write_if_changed(by_tag_path, by_tag_content, args.dry_run):
        changes.append(str(by_tag_path.relative_to(VAULT_ROOT)))

    # _by_project.json
    by_proj: dict[str, list[str]] = defaultdict(list)
    for t in flat:
        by_proj[t.get("project") or "_standalone"].append(t.get("id"))
    by_proj_content = json.dumps({k: by_proj[k] for k in sorted(by_proj)},
                                 indent=2, ensure_ascii=False) + "\n"
    by_proj_path = LEDGER / "_by_project.json"
    if _write_if_changed(by_proj_path, by_proj_content, args.dry_run):
        changes.append(str(by_proj_path.relative_to(VAULT_ROOT)))

    # _metrics.json — full global metrics
    global_metrics = M.compute(flat)
    # drop raw cycle_time values (can get big; keep summary only)
    global_metrics["cycle_time_days"].pop("values", None)
    metrics_path = LEDGER / "_metrics.json"
    metrics_content = json.dumps(global_metrics, indent=2, ensure_ascii=False) + "\n"
    if _write_if_changed(metrics_path, metrics_content, args.dry_run):
        changes.append(str(metrics_path.relative_to(VAULT_ROOT)))

    # Buckets
    by_week: dict[str, list[dict]] = defaultdict(list)
    by_month: dict[str, list[dict]] = defaultdict(list)
    by_year: dict[int, list[dict]] = defaultdict(list)
    for t in all_tasks:
        d = _date_of(t)
        if d is None:
            continue
        by_week[_iso_week(d)].append(t)
        by_month[d.strftime("%Y-%m")].append(t)
        by_year[d.year].append(t)

    for iso, ts in sorted(by_week.items()):
        if args.only and args.only != iso:
            continue
        p = WEEKLY / f"{iso}.md"
        if _write_if_changed(p, _render_weekly(iso, ts), args.dry_run):
            changes.append(str(p.relative_to(VAULT_ROOT)))

    for ym, ts in sorted(by_month.items()):
        if args.only:
            _mo, _su = _week_bounds(args.only)
            if _mo.strftime("%Y-%m") != ym:
                continue
        p = MONTHLY / f"{ym}.md"
        if _write_if_changed(p, _render_monthly(ym, ts), args.dry_run):
            changes.append(str(p.relative_to(VAULT_ROOT)))

    for y, ts in sorted(by_year.items()):
        if args.only:
            _mo, _su = _week_bounds(args.only)
            if _mo.year != y:
                continue
        p = YEARLY / f"{y}.md"
        if _write_if_changed(p, _render_yearly(y, ts), args.dry_run):
            changes.append(str(p.relative_to(VAULT_ROOT)))

    # Refresh the auto-generated dashboards under 17_Dashboards/Tasks/Auto/.
    # Failure here must not abort aggregation — log and continue.
    dash_changes: list[str] = []
    try:
        import dashboard as DASH  # local import: same scripts/ dir
        dash_res = DASH.refresh(dry_run=args.dry_run)
        dash_changes = list(dash_res.get("changed") or [])
    except Exception as exc:  # noqa: BLE001
        print(f"[aggregate] dashboard refresh failed: {exc}", file=sys.stderr)

    print(json.dumps({
        "tasks_scanned": len(all_tasks),
        "files_changed": changes,
        "dashboard_changed": dash_changes,
        "dry_run": args.dry_run,
    }, indent=2))


if __name__ == "__main__":
    main()
