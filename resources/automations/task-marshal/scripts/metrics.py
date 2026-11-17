"""Quantitative metrics over the task ledger.

Pure functions over the flat list of task dicts (the shape written to
Ledger/_index.json). Computes the things a professional operator — in
particular someone managing many side projects in parallel — actually needs:

    - throughput:      closed tasks per day / per week / per month
    - WIP:             open + blocked + waiting, overall and per project
    - cycle time:      created_at → closed_at, p50 / p95
    - lead time:       when → closed_at (can be negative = closed early)
    - aging:           today − created_at for open tasks
    - priority load:   Σ weight(priority) per project / per tag, unclosed
    - completion rate: done / (done + open + cancelled)
    - project portfolio: per-project header stats
    - context switch: unique projects touched per day
    - heatmap grid:    calendar-day counts, ready for rendering

All outputs are deterministic and JSON-serialisable.
"""
from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from statistics import median
from typing import Any, Iterable

# Priority weights — higher = more load
PRIORITY_WEIGHT: dict[str | None, float] = {
    "P0": 4.0,
    "P1": 3.0,
    "P2": 2.0,
    "P3": 1.0,
    None: 0.5,
}

OPEN_STATES = {"open", "blocked", "waiting"}
CLOSED_STATES = {"done", "cancelled"}


# --- date helpers ---------------------------------------------------------

def _parse_date(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def _parse_datetime(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        if len(s) >= 16:
            return dt.datetime.fromisoformat(s[:16])
        return dt.datetime.combine(dt.date.fromisoformat(s[:10]), dt.time())
    except ValueError:
        return None


def _task_date(t: dict) -> dt.date | None:
    return _parse_date(t.get("when")) or _parse_date(t.get("created_at"))


# --- percentile -----------------------------------------------------------

def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    k = (len(xs) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(xs) - 1)
    frac = k - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


# --- top-level metrics ----------------------------------------------------

def compute(tasks: Iterable[dict], today: dt.date | None = None) -> dict[str, Any]:
    tasks = list(tasks)
    today = today or dt.date.today()

    total = len(tasks)
    by_status = Counter(t.get("status") or "open" for t in tasks)
    by_priority = Counter(t.get("priority") for t in tasks)

    done = by_status.get("done", 0)
    cancelled = by_status.get("cancelled", 0)
    open_like = sum(by_status.get(s, 0) for s in OPEN_STATES)

    # Completion rate excludes cancelled, since those don't count against you.
    denom = done + open_like
    completion_rate = (done / denom) if denom else 0.0

    # --- cycle & lead time on closed tasks -------------------------------
    cycle_times: list[float] = []
    lead_times: list[float] = []
    for t in tasks:
        if t.get("status") != "done":
            continue
        closed = _parse_datetime(t.get("closed_at"))
        created = _parse_datetime(t.get("created_at"))
        if closed and created:
            cycle_times.append((closed - created).total_seconds() / 86400.0)
        when = _parse_date(t.get("when"))
        if closed and when:
            lead_times.append((closed.date() - when).days)

    # --- aging on open-like tasks ----------------------------------------
    aging_days: list[float] = []
    aging_by_priority: dict[str | None, list[float]] = defaultdict(list)
    for t in tasks:
        if t.get("status") not in OPEN_STATES:
            continue
        created = _parse_datetime(t.get("created_at"))
        if not created:
            continue
        age = (dt.datetime.combine(today, dt.time()) - created).total_seconds() / 86400.0
        aging_days.append(age)
        aging_by_priority[t.get("priority")].append(age)

    # --- throughput (closed per day) ------------------------------------
    throughput_by_day: Counter = Counter()
    for t in tasks:
        if t.get("status") != "done":
            continue
        closed = _parse_date(t.get("closed_at"))
        if closed:
            throughput_by_day[closed.isoformat()] += 1

    # --- overdue --------------------------------------------------------
    overdue = []
    for t in tasks:
        if t.get("status") not in OPEN_STATES:
            continue
        when = _parse_date(t.get("when"))
        if when and when < today:
            overdue.append(t.get("id"))

    # --- WIP by project / priority-weighted load ------------------------
    wip_by_project: Counter = Counter()
    weighted_by_project: dict[str, float] = defaultdict(float)
    done_by_project: Counter = Counter()
    total_by_project: Counter = Counter()
    last_touched: dict[str, str] = {}
    minutes_by_project: dict[str, int] = defaultdict(int)

    for t in tasks:
        proj = t.get("project") or "_standalone"
        total_by_project[proj] += 1
        if t.get("status") == "done":
            done_by_project[proj] += 1
        if t.get("status") in OPEN_STATES:
            wip_by_project[proj] += 1
            weighted_by_project[proj] += PRIORITY_WEIGHT[t.get("priority")]
        dur = t.get("duration_min") or 0
        if isinstance(dur, (int, float)):
            minutes_by_project[proj] += int(dur)
        # last touched = latest of (closed_at, created_at, when)
        candidates = [t.get("closed_at"), t.get("created_at"), t.get("when")]
        best = max((c for c in candidates if c), default="")
        if best > last_touched.get(proj, ""):
            last_touched[proj] = best

    # --- per-project portfolio block ------------------------------------
    projects: list[dict] = []
    for proj in sorted(total_by_project):
        total_p = total_by_project[proj]
        done_p = done_by_project.get(proj, 0)
        projects.append({
            "project": proj,
            "total": total_p,
            "open": wip_by_project.get(proj, 0),
            "done": done_p,
            "completion": (done_p / total_p) if total_p else 0.0,
            "weighted_load": round(weighted_by_project.get(proj, 0.0), 2),
            "total_minutes": minutes_by_project.get(proj, 0),
            "last_touched": last_touched.get(proj, ""),
        })

    # --- context-switching index (unique projects per day, on `when`) ---
    projects_per_day: dict[str, set[str]] = defaultdict(set)
    for t in tasks:
        d = _task_date(t)
        if not d:
            continue
        projects_per_day[d.isoformat()].add(t.get("project") or "_standalone")
    context_switch_series = {
        day: len(projs) for day, projs in sorted(projects_per_day.items())
    }

    # --- tag counts -----------------------------------------------------
    tag_counts: Counter = Counter()
    for t in tasks:
        for tag in t.get("tags") or []:
            tag_counts[tag] += 1

    # --- Eisenhower quadrant points (P0/P1 × overdue/on-time) ----------
    quadrant_points: list[dict] = []
    for t in tasks:
        if t.get("status") not in OPEN_STATES:
            continue
        pri = t.get("priority")
        when = _parse_date(t.get("when"))
        overdue_flag = bool(when and when < today)
        if pri in ("P0", "P1"):
            quadrant_points.append({
                "id": t.get("id"),
                "title": t.get("title"),
                "priority": pri,
                "overdue": overdue_flag,
            })

    return {
        "as_of": today.isoformat(),
        "total": total,
        "by_status": dict(by_status),
        "by_priority": {str(k): v for k, v in by_priority.items()},
        "completion_rate": round(completion_rate, 4),
        "cycle_time_days": {
            "count": len(cycle_times),
            "p50": round(median(cycle_times), 2) if cycle_times else None,
            "p95": round(_percentile(cycle_times, 0.95), 2) if cycle_times else None,
            "mean": round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else None,
            "values": cycle_times,
        },
        "lead_time_days": {
            "count": len(lead_times),
            "p50": round(median(lead_times), 2) if lead_times else None,
            "p95": round(_percentile(lead_times, 0.95), 2) if lead_times else None,
        },
        "aging_days": {
            "count": len(aging_days),
            "p50": round(median(aging_days), 2) if aging_days else None,
            "p95": round(_percentile(aging_days, 0.95), 2) if aging_days else None,
            "by_priority": {
                str(k): round(median(v), 2) for k, v in aging_by_priority.items()
            },
        },
        "throughput_by_day": dict(sorted(throughput_by_day.items())),
        "overdue_ids": overdue,
        "projects": projects,
        "tag_counts": dict(tag_counts.most_common()),
        "context_switch_by_day": context_switch_series,
        "quadrant_points": quadrant_points,
    }


# --- calendar heatmap grids ----------------------------------------------

def month_heatmap(tasks: Iterable[dict], year: int, month: int) -> list[list[int | None]]:
    """Return a 6×7 grid (rows=weeks, cols=Mon..Sun) of task counts.

    Cells outside the month are None.
    """
    counts: Counter = Counter()
    for t in tasks:
        d = _task_date(t)
        if d and d.year == year and d.month == month:
            counts[d.day] += 1

    first = dt.date(year, month, 1)
    # days in month
    if month == 12:
        last = dt.date(year + 1, 1, 1) - dt.timedelta(days=1)
    else:
        last = dt.date(year, month + 1, 1) - dt.timedelta(days=1)

    # Monday=0 ... Sunday=6
    start_wd = first.weekday()
    grid: list[list[int | None]] = []
    row = [None] * start_wd
    day = 1
    while day <= last.day:
        row.append(counts.get(day, 0))
        if len(row) == 7:
            grid.append(row)
            row = []
        day += 1
    if row:
        row.extend([None] * (7 - len(row)))
        grid.append(row)
    # pad to 6 rows for visual stability
    while len(grid) < 6:
        grid.append([None] * 7)
    return grid


def year_heatmap(tasks: Iterable[dict], year: int) -> dict[str, list[int]]:
    """Return {month_name: [day_counts × 31]} with trailing zero-pad."""
    out: dict[str, list[int]] = {}
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    counts: dict[int, Counter] = {m: Counter() for m in range(1, 13)}
    for t in tasks:
        d = _task_date(t)
        if d and d.year == year:
            counts[d.month][d.day] += 1
    for m, name in enumerate(months, start=1):
        out[name] = [counts[m].get(day, 0) for day in range(1, 32)]
    return out
