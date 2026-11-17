"""Deterministic markdown renderers for task-ledger analytics.

All functions are pure: they take metric dicts / task lists and return strings
ready to drop into a Weekly/Monthly/Yearly rollup or the analytics dashboard.

Two output families:

    - Unicode visuals   — bars, sparklines, density heatmaps. Render anywhere
                          (Obsidian, GitHub, plain terminal).
    - Mermaid blocks    — pie / gantt / xychart-beta / quadrantChart. Obsidian
                          renders these natively. Zero external dependencies.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

# --- 1. Unicode primitives -----------------------------------------------

_BAR_FILL = "█"
_BAR_EMPTY = "░"
_SPARK = "▁▂▃▄▅▆▇█"
_HEAT = " ░▒▓█"          # 5 density levels, space for zero
_HEAT_LABELS = ["0", "1", "2-3", "4-6", "7+"]


def unicode_bar(value: float, max_value: float, width: int = 20) -> str:
    """Return a solid/empty bar of fixed width. Example: ``█████░░░░░░░░░``."""
    if max_value <= 0:
        return _BAR_EMPTY * width
    ratio = max(0.0, min(1.0, value / max_value))
    filled = int(round(ratio * width))
    return _BAR_FILL * filled + _BAR_EMPTY * (width - filled)


def unicode_pct_bar(fraction: float, width: int = 10) -> str:
    """``fraction`` in [0, 1]. Appends percentage after the bar."""
    fraction = max(0.0, min(1.0, fraction))
    filled = int(round(fraction * width))
    return _BAR_FILL * filled + _BAR_EMPTY * (width - filled) + f" {fraction * 100:>5.1f}%"


def unicode_sparkline(values: list[float]) -> str:
    """Return an 8-level sparkline. Empty string if no values."""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return _SPARK[len(_SPARK) // 2] * len(values)
    span = hi - lo
    return "".join(_SPARK[int((v - lo) / span * (len(_SPARK) - 1))] for v in values)


def _heat_char(count: int | None) -> str:
    if count is None:
        return " "
    if count == 0:
        return _HEAT[0]
    if count == 1:
        return _HEAT[1]
    if count <= 3:
        return _HEAT[2]
    if count <= 6:
        return _HEAT[3]
    return _HEAT[4]


# --- 2. Unicode heatmap (month / year grids) -----------------------------

def month_heatmap_md(grid: list[list[int | None]], year: int, month: int) -> str:
    """Render a 6×7 month heatmap grid as a code-fenced block.

    Grid shape comes from metrics.month_heatmap: rows=weeks, cols=Mon..Sun.
    """
    name = dt.date(year, month, 1).strftime("%B %Y")
    out = ["```", f"{name:^36}".rstrip(), "Mon Tue Wed Thu Fri Sat Sun"]
    for row in grid:
        cells = []
        for v in row:
            if v is None:
                cells.append("   ")
            else:
                # Display the count if small, else a heat glyph
                cells.append(f" {_heat_char(v)} ")
        out.append(" ".join(c.strip().center(3) for c in cells).rstrip())
    out.append("")
    out.append(f"legend: {_HEAT[0]}=0  {_HEAT[1]}=1  {_HEAT[2]}=2-3  {_HEAT[3]}=4-6  {_HEAT[4]}=7+")
    out.append("```")
    return "\n".join(out)


def year_heatmap_md(year_grid: dict[str, list[int]], year: int) -> str:
    out = ["```", f"Year heatmap — {year}", "        " + "".join(f"{d:>3}" for d in range(1, 32))]
    for month, days in year_grid.items():
        cells = "".join(f"  {_heat_char(c)}" for c in days)
        out.append(f"{month:>5}  {cells}".rstrip())
    out.append("")
    out.append(f"legend: {_HEAT[0]}=0  {_HEAT[1]}=1  {_HEAT[2]}=2-3  {_HEAT[3]}=4-6  {_HEAT[4]}=7+")
    out.append("```")
    return "\n".join(out)


# --- 3. KPI block --------------------------------------------------------

def kpi_block(m: dict) -> str:
    total = m["total"]
    open_n = sum(m["by_status"].get(s, 0) for s in ("open", "blocked", "waiting"))
    done = m["by_status"].get("done", 0)
    cycle = m["cycle_time_days"]
    aging = m["aging_days"]
    lines = [
        "| metric | value |",
        "|--------|-------|",
        f"| total tasks | **{total}** |",
        f"| open / in-flight | **{open_n}** |",
        f"| done | **{done}** |",
        f"| completion rate | **{unicode_pct_bar(m['completion_rate'])}** |",
        f"| overdue (open) | **{len(m['overdue_ids'])}** |",
    ]
    if cycle["count"]:
        lines.append(f"| cycle time p50 / p95 | **{cycle['p50']}d / {cycle['p95']}d** (n={cycle['count']}) |")
    if aging["count"]:
        lines.append(f"| aging p50 / p95 (open) | **{aging['p50']}d / {aging['p95']}d** |")
    return "\n".join(lines)


# --- 4. Mermaid renderers -------------------------------------------------

def _mermaid_safe(s: str) -> str:
    return (s or "").replace('"', "'").replace("\n", " ").strip()


def mermaid_status_pie(m: dict, title: str = "Status distribution") -> str:
    by = m["by_status"]
    if not by:
        return "_no tasks_"
    out = ["```mermaid", "pie showData", f'    title {title}']
    for k in ("open", "done", "blocked", "waiting", "cancelled", "rolled_over"):
        v = by.get(k, 0)
        if v:
            out.append(f'    "{k}" : {v}')
    out.append("```")
    return "\n".join(out)


def mermaid_priority_pie(m: dict, title: str = "Priority distribution") -> str:
    by = m["by_priority"]
    out = ["```mermaid", "pie showData", f'    title {title}']
    for k in ("P0", "P1", "P2", "P3", "None"):
        v = by.get(k, 0)
        if v:
            label = k if k != "None" else "unprioritised"
            out.append(f'    "{label}" : {v}')
    out.append("```")
    return "\n".join(out)


def mermaid_throughput_bar(series: dict[str, int], title: str = "Throughput (closed / day)") -> str:
    """xychart-beta bar of closed-per-day for a date range."""
    if not series:
        return "_no throughput data_"
    days = list(series.keys())
    vals = list(series.values())
    # label days with MM-DD for compactness
    labels = [d[5:] for d in days]
    ymax = max(vals) + 1 if vals else 1
    out = [
        "```mermaid",
        "xychart-beta",
        f'    title "{title}"',
        "    x-axis [" + ", ".join(labels) + "]",
        f'    y-axis "closed" 0 --> {ymax}',
        "    bar [" + ", ".join(str(v) for v in vals) + "]",
        "```",
    ]
    return "\n".join(out)


def mermaid_monthly_throughput(series: dict[str, int], year: int) -> str:
    """Line chart of closed-per-month for one year. Pads missing months."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    vals = []
    for m in range(1, 13):
        key = f"{year:04d}-{m:02d}"
        vals.append(sum(v for k, v in series.items() if k.startswith(key)))
    ymax = max(vals) + 1 if vals else 1
    out = [
        "```mermaid",
        "xychart-beta",
        f'    title "Monthly throughput — {year}"',
        "    x-axis [" + ", ".join(months) + "]",
        f'    y-axis "closed" 0 --> {ymax}',
        "    line [" + ", ".join(str(v) for v in vals) + "]",
        "    bar [" + ", ".join(str(v) for v in vals) + "]",
        "```",
    ]
    return "\n".join(out)


def mermaid_gantt(tasks: list[dict], title: str, only_with_date: bool = True) -> str:
    """Produce a Mermaid gantt grouped by project.

    Each task uses its `when` as start and `duration_min` (or default 1d) as
    duration. Status maps to gantt status keyword.
    """
    by_proj: dict[str, list[dict]] = {}
    for t in tasks:
        if only_with_date and not t.get("when"):
            continue
        by_proj.setdefault(t.get("project") or "_standalone", []).append(t)
    if not by_proj:
        return "_no dated tasks_"

    status_kw = {
        "done": "done",
        "cancelled": "crit",
        "blocked": "crit",
        "waiting": "active",
        "rolled_over": "active",
        "open": "active",
    }

    out = ["```mermaid", "gantt", f"    title {title}",
           "    dateFormat  YYYY-MM-DD",
           "    axisFormat  %m-%d"]
    for proj in sorted(by_proj):
        out.append(f"    section {proj}")
        for t in sorted(by_proj[proj], key=lambda x: x.get("when") or ""):
            label = _mermaid_safe(t.get("title") or t.get("id") or "(no title)")[:60]
            when = t.get("when")
            if not when:
                continue
            dur_min = t.get("duration_min") or 0
            # Gantt time resolution is day-level; round up
            dur_d = max(1, int((dur_min + 240) // 480))  # >8h = 2d, etc., rough
            kw = status_kw.get(t.get("status") or "open", "active")
            tid = t.get("id") or ""
            out.append(f"    {label} :{kw}, {tid}, {when}, {dur_d}d")
    out.append("```")
    return "\n".join(out)


def mermaid_quadrant(points: list[dict]) -> str:
    """Eisenhower-ish quadrant: x=priority (P1 low, P0 high), y=urgency (overdue high).

    Uses mermaid quadrantChart. Points at the same (priority, urgency) tuple
    get a deterministic hash-based jitter so labels don't collapse on top of
    each other.
    """
    if not points:
        return "_no P0/P1 open_"

    import hashlib

    def _jitter(key: str) -> float:
        # Signed jitter in [-0.08, +0.08], deterministic per id.
        h = hashlib.md5(key.encode("utf-8")).digest()
        return ((h[0] / 255.0) - 0.5) * 0.16

    out = [
        "```mermaid",
        "quadrantChart",
        "    title Priority × Urgency (open P0/P1)",
        "    x-axis Lower priority --> Higher priority",
        "    y-axis On time --> Overdue",
        "    quadrant-1 Urgent & important",
        "    quadrant-2 Important, on time",
        "    quadrant-3 Low priority, on time",
        "    quadrant-4 Urgent, lower priority",
    ]
    for p in points:
        base_x = 0.85 if p["priority"] == "P0" else 0.55
        base_y = 0.85 if p["overdue"] else 0.30
        seed = p.get("id") or p.get("title") or ""
        x = max(0.02, min(0.98, base_x + _jitter("x:" + seed)))
        y = max(0.02, min(0.98, base_y + _jitter("y:" + seed)))
        label = _mermaid_safe(p.get("title") or p.get("id") or "")[:40] or "(task)"
        out.append(f'    "{label}": [{x:.3f}, {y:.3f}]')
    out.append("```")
    return "\n".join(out)


# --- 5. Tables -----------------------------------------------------------

def project_portfolio_table(m: dict) -> str:
    rows = ["| project | open | done | total | completion | weighted load | minutes | last touched |",
            "|---------|------|------|-------|------------|---------------|---------|--------------|"]
    projects = sorted(m["projects"], key=lambda p: (-p["weighted_load"], -p["open"], p["project"]))
    if not projects:
        return "_no projects_"
    max_load = max((p["weighted_load"] for p in projects), default=1) or 1
    for p in projects:
        load_bar = unicode_bar(p["weighted_load"], max_load, width=12)
        comp = unicode_pct_bar(p["completion"], width=8)
        mins = p["total_minutes"]
        mins_str = f"{mins//60}h{mins%60:02d}" if mins else "—"
        rows.append(
            f"| {p['project']} | {p['open']} | {p['done']} | {p['total']} "
            f"| {comp} | `{load_bar}` {p['weighted_load']} "
            f"| {mins_str} | {p['last_touched'][:10] or '—'} |"
        )
    return "\n".join(rows)


def aging_table(m: dict) -> str:
    by_pri = m["aging_days"]["by_priority"]
    if not by_pri:
        return "_no open tasks_"
    # Clamp negatives to zero for the bar ("future task, not yet aged") while
    # preserving the raw signed median in the number column — useful signal.
    bar_vals = {k: max(0.0, v) for k, v in by_pri.items()}
    max_age = max(bar_vals.values()) or 1
    rows = ["| priority | median age (d) | |",
            "|----------|----------------|-|"]
    for k in ("P0", "P1", "P2", "P3", "None"):
        if k not in by_pri:
            continue
        v = by_pri[k]
        label = k if k != "None" else "unprioritised"
        rows.append(f"| {label} | {v} | `{unicode_bar(bar_vals[k], max_age, width=18)}` |")
    return "\n".join(rows)


def cycle_time_histogram(m: dict, bins: int = 10) -> str:
    values = m["cycle_time_days"].get("values") or []
    if not values:
        return "_no closed tasks yet_"
    lo, hi = min(values), max(values)
    if hi == lo:
        return f"_all {len(values)} closed tasks completed in {round(lo,1)}d_"
    step = (hi - lo) / bins
    buckets = [0] * bins
    for v in values:
        idx = min(bins - 1, int((v - lo) / step))
        buckets[idx] += 1
    max_b = max(buckets) or 1
    rows = ["| days | count | |",
            "|------|-------|-|"]
    for i, c in enumerate(buckets):
        left = lo + i * step
        right = lo + (i + 1) * step
        rows.append(f"| {left:.1f}–{right:.1f} | {c} | `{unicode_bar(c, max_b, width=18)}` |")
    return "\n".join(rows)


def context_switch_sparkline(m: dict) -> str:
    series = m["context_switch_by_day"]
    if not series:
        return "_n/a_"
    vals = list(series.values())
    return f"`{unicode_sparkline([float(v) for v in vals])}`  (max={max(vals)}, days={len(vals)})"


def top_tags_table(m: dict, n: int = 15) -> str:
    tag_counts = m["tag_counts"]
    if not tag_counts:
        return "_no tags_"
    total = max(tag_counts.values())
    rows = ["| tag | count | |",
            "|-----|-------|-|"]
    for i, (tag, count) in enumerate(tag_counts.items()):
        if i >= n:
            break
        rows.append(f"| #{tag} | {count} | `{unicode_bar(count, total, width=18)}` |")
    return "\n".join(rows)
