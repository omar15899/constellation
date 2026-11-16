#!/usr/bin/env python3
"""
Auto-refreshing analytics dashboard for the OmarOS task ledger.

Outputs under ``17_Dashboards/Tasks/Auto/`` (separate from the hand-curated
``Tasks.md`` / ``Analytics.md`` in ``17_Dashboards/Tasks/`` proper). This
script is invoked by ``aggregate.py`` after every regeneration of
``_index.json`` / ``_metrics.json`` — i.e. every time the reminders-sync
daemon detects a change in Reminders.app, the dashboard refreshes within
seconds.

Files written
-------------
    17_Dashboards/Tasks/Auto/_README.md       layout + freshness contract
    17_Dashboards/Tasks/Auto/Overview.md      headline KPIs + sparklines
    17_Dashboards/Tasks/Auto/Throughput.md    daily 90d / weekly 26w / monthly 12m
    17_Dashboards/Tasks/Auto/Heatmap.md       calendar heatmaps (year + month)
    17_Dashboards/Tasks/Auto/Projects.md      portfolio table
    17_Dashboards/Tasks/Auto/Tags.md          top tags
    17_Dashboards/Tasks/Auto/Recent.md        last 30 closures + overdue + open P0
    17_Dashboards/Tasks/Auto/Aging.md         age distribution of open tasks
    17_Dashboards/Tasks/Auto/_assets/throughput_90d.png
    17_Dashboards/Tasks/Auto/_assets/heatmap_year.png
    17_Dashboards/Tasks/Auto/_assets/cycle_distribution.png

All writes are idempotent — files only change when their content actually
changes, so Obsidian does not see spurious mtime updates and the git
status stays quiet between real semantic shifts.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = Path("/Users/omarkhalil/OmarOS")
LEDGER = VAULT / "02_Tasks_and_Execution/Ledger"
DASH = VAULT / "17_Dashboards/Tasks/Auto"
ASSETS = DASH / "_assets"

sys.path.insert(0, str(HERE))
import metrics as M  # noqa: E402
import render as R  # noqa: E402


# ── filesystem helpers ────────────────────────────────────────────────────────

def _write_if_changed(path: Path, content: str | bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing == content:
            return False
        path.write_text(content, encoding="utf-8")
        return True
    existing_b = path.read_bytes() if path.exists() else None
    if existing_b == content:
        return False
    path.write_bytes(content)
    return True


def _frontmatter(title: str, slug: str) -> str:
    today = dt.date.today().isoformat()
    return (
        "---\n"
        f"title: '{title}'\n"
        "note_type: dashboard\n"
        "domain: 17_Dashboards\n"
        "subdomain: Tasks\n"
        f"slug: {slug}\n"
        "tags: [dashboard, tasks, task_ledger, auto_generated]\n"
        "status: active\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "ai_generated: true\n"
        "ai_reviewed: false\n"
        "auto_refresh: aggregate.py\n"
        "---\n\n"
    )


# ── data loading ──────────────────────────────────────────────────────────────

def _load_tasks() -> list[dict]:
    p = LEDGER / "_index.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


# ── matplotlib charts ─────────────────────────────────────────────────────────

def _chart_throughput_90d(throughput: dict[str, int]) -> bytes | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    today = dt.date.today()
    days = [today - dt.timedelta(days=i) for i in range(89, -1, -1)]
    values = [throughput.get(d.isoformat(), 0) for d in days]
    if not any(values):
        return None
    fig, ax = plt.subplots(figsize=(11, 3.2))
    ax.bar(range(len(values)), values, color="#4c8bf5", width=0.8)
    avg = sum(values) / len(values)
    ax.axhline(avg, color="#a55", linestyle="--", linewidth=0.8,
               label=f"avg {avg:.1f}/day")
    tick_idx = list(range(0, len(days), 10))
    ax.set_xticks(tick_idx)
    ax.set_xticklabels([days[i].strftime("%m-%d") for i in tick_idx],
                       rotation=0, fontsize=8)
    ax.set_ylabel("closed tasks")
    ax.set_title(f"Throughput — last 90 days (until {today.isoformat()})",
                 fontsize=11)
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return buf.getvalue()


def _chart_year_heatmap(throughput: dict[str, int], year: int) -> bytes | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
        import numpy as np
    except ImportError:
        return None
    start = dt.date(year, 1, 1)
    end = dt.date(year, 12, 31)
    n_days = (end - start).days + 1

    # GitHub-style: rows = days of week (Mon..Sun), cols = ISO weeks
    first_monday = start - dt.timedelta(days=start.weekday())
    grid: dict[tuple[int, int], int] = {}
    for i in range(n_days):
        d = start + dt.timedelta(days=i)
        col = (d - first_monday).days // 7
        row = d.weekday()
        grid[(row, col)] = throughput.get(d.isoformat(), 0)
    cols = max(c for _, c in grid.keys()) + 1
    arr = np.full((7, cols), np.nan)
    for (r, c), v in grid.items():
        arr[r, c] = v

    cmap = LinearSegmentedColormap.from_list(
        "gh", ["#ebedf0", "#c6e48b", "#7bc96f", "#239a3b", "#196127"]
    )
    fig, ax = plt.subplots(figsize=(13, 2.6))
    im = ax.imshow(arr, aspect="auto", cmap=cmap,
                   vmin=0, vmax=max(1, int(np.nanmax(arr) or 1)))
    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                       fontsize=8)
    # X ticks at first column of each month
    month_cols = []
    month_labels = []
    for m in range(1, 13):
        d = dt.date(year, m, 1)
        col = (d - first_monday).days // 7
        month_cols.append(col)
        month_labels.append(d.strftime("%b"))
    ax.set_xticks(month_cols)
    ax.set_xticklabels(month_labels, fontsize=8)
    ax.set_title(f"Calendar heatmap — {year} (closed tasks per day)", fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02).ax.tick_params(labelsize=7)
    fig.tight_layout()
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return buf.getvalue()


def _chart_cycle_distribution(cycle_values: list[float]) -> bytes | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    if not cycle_values:
        return None
    # Clip extreme outliers for the histogram (preserves p95 visibility).
    sv = sorted(cycle_values)
    p99 = sv[int(0.99 * (len(sv) - 1))]
    clipped = [min(v, p99) for v in cycle_values]
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.hist(clipped, bins=40, color="#7c3aed", alpha=0.85)
    p50 = sv[len(sv) // 2]
    p95 = sv[int(0.95 * (len(sv) - 1))]
    for q, lab, col in [(p50, "p50", "#22c55e"), (p95, "p95", "#f97316")]:
        ax.axvline(q, color=col, linestyle="--", linewidth=1.0,
                   label=f"{lab} = {q:.1f}d")
    ax.set_xlabel("cycle time (days, clipped to p99)")
    ax.set_ylabel("# closed tasks")
    ax.set_title(f"Cycle-time distribution — n={len(cycle_values)}", fontsize=11)
    ax.legend(loc="upper right", frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return buf.getvalue()


# ── markdown sections ─────────────────────────────────────────────────────────

def _window_total(throughput: dict[str, int],
                  days: int,
                  end: dt.date | None = None) -> int:
    """Total closures in the last ``days`` days ending at ``end`` (inclusive)."""
    end = end or dt.date.today()
    return sum(throughput.get((end - dt.timedelta(days=i)).isoformat(), 0)
               for i in range(days))


def _streak_data(throughput: dict[str, int],
                 today: dt.date | None = None,
                 lookback_days: int = 730) -> dict:
    """Compute current streak, longest streak, total active days.

    A "day" counts toward a streak when ≥ 1 task was closed on it. The
    current streak is the consecutive run of active days ending today
    (or, if today is still empty, ending yesterday — so the current
    streak does not flip to 0 the first millisecond of a new day).
    """
    today = today or dt.date.today()
    # Build active-day boolean series, oldest → newest.
    active: list[tuple[dt.date, bool]] = []
    for i in range(lookback_days - 1, -1, -1):
        d = today - dt.timedelta(days=i)
        active.append((d, throughput.get(d.isoformat(), 0) > 0))
    flags = [a[1] for a in active]

    # Longest run of consecutive True.
    longest = 0
    longest_end: dt.date | None = None
    cur = 0
    for (d, v) in active:
        if v:
            cur += 1
            if cur > longest:
                longest = cur
                longest_end = d
        else:
            cur = 0

    # Current streak = trailing run that includes today; if today is False
    # but yesterday was True, treat the streak as still alive (the day is
    # not yet over). It only breaks if yesterday was also empty.
    n = len(flags)
    if n == 0:
        return {
            "current": 0, "longest": 0, "longest_end": None,
            "active_days": 0, "lookback": lookback_days,
        }
    cur_streak = 0
    if flags[-1]:
        i = n - 1
        while i >= 0 and flags[i]:
            cur_streak += 1
            i -= 1
    else:
        # Today empty — still count yesterday's streak as "alive"
        i = n - 2
        while i >= 0 and flags[i]:
            cur_streak += 1
            i -= 1
    return {
        "current": cur_streak,
        "longest": longest,
        "longest_end": longest_end.isoformat() if longest_end else None,
        "active_days": sum(flags),
        "lookback": lookback_days,
    }


def _velocity_table(throughput: dict[str, int],
                    today: dt.date | None = None) -> str:
    """Render a velocity panel: total + avg + Δ vs prior equal-length window."""
    today = today or dt.date.today()
    rows = ["| ventana | cerradas | promedio/día | Δ vs período previo |",
            "|---------|---------:|-------------:|--------------------:|"]
    for label, days in [("Hoy", 1), ("7 días", 7), ("30 días", 30),
                        ("90 días", 90)]:
        cur = _window_total(throughput, days, end=today)
        if days == 1:
            rows.append(f"| {label} | {cur} | — | — |")
            continue
        prev_end = today - dt.timedelta(days=days)
        prev = _window_total(throughput, days, end=prev_end)
        avg = cur / days
        if prev > 0:
            delta = (cur - prev) / prev * 100
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "■")
            delta_str = f"{arrow} {delta:+.0f}% (prev {prev})"
        elif cur > 0:
            delta_str = f"▲ +∞% (prev 0)"
        else:
            delta_str = "—"
        rows.append(f"| {label} | {cur} | {avg:.2f} | {delta_str} |")

    # Year-to-date — a single end-of-day projection
    ytd_start = dt.date(today.year, 1, 1)
    ytd_days = (today - ytd_start).days + 1
    ytd = sum(v for k, v in throughput.items()
              if k >= ytd_start.isoformat() and k <= today.isoformat())
    ytd_avg = ytd / ytd_days if ytd_days else 0
    days_in_year = 366 if (today.year % 4 == 0 and (today.year % 100 != 0 or today.year % 400 == 0)) else 365
    projection = int(ytd_avg * days_in_year)
    rows.append(f"| YTD ({ytd_days}d) | {ytd} | {ytd_avg:.2f} | "
                f"proyección a fin de año: **{projection}** |")
    return "\n".join(rows)


def _active_projects_30d(tasks: list[dict],
                         today: dt.date | None = None,
                         top_n: int = 8) -> str:
    """Top-N reminder lists by completions in the last 30 days, with
    a 30-day sparkline per list."""
    today = today or dt.date.today()
    cutoff = today - dt.timedelta(days=29)
    # tag → list[date] of closures in window
    per_list: dict[str, list[dt.date]] = {}
    for t in tasks:
        if t.get("status") != "done":
            continue
        d = M._parse_date(t.get("closed_at"))
        if not d or d < cutoff or d > today:
            continue
        for tag in t.get("tags") or []:
            if tag.startswith("reminder_"):
                per_list.setdefault(tag, []).append(d)
                break  # only the first list-tag, never bucket twice
    if not per_list:
        return "_Ninguna lista con cierres en los últimos 30 días._"
    rows = ["| lista | cerradas (30d) | sparkline 30d |",
            "|-------|---------------:|---------------|"]
    ranked = sorted(per_list.items(), key=lambda kv: -len(kv[1]))[:top_n]
    for tag, dates in ranked:
        # Daily counts for the 30-day window
        per_day = [0] * 30
        for d in dates:
            idx = (d - cutoff).days
            if 0 <= idx < 30:
                per_day[idx] += 1
        spark = R.unicode_sparkline([float(v) for v in per_day])
        # Pretty name: strip 'reminder_' prefix
        name = tag.removeprefix("reminder_")
        rows.append(f"| `{name}` | {len(dates)} | `{spark}` |")
    return "\n".join(rows)


def _section_overview(m: dict, throughput_30: dict[str, int],
                      tasks: list[dict]) -> str:
    today = dt.date.today()
    p0_open = m.get("by_priority", {}).get("P0", 0)
    overdue = len(m.get("overdue_ids") or [])
    closed_today = throughput_30.get(today.isoformat(), 0)
    streak = _streak_data(throughput_30)

    last30 = [throughput_30.get((today - dt.timedelta(days=i)).isoformat(), 0)
              for i in range(29, -1, -1)]
    last7 = last30[-7:]

    return "\n".join([
        "# Tasks — Overview",
        "",
        f"_Last refresh: {dt.date.today().isoformat()} from "
        f"`{LEDGER.relative_to(VAULT)}/_index.json`._",
        "",
        f"## Hoy — {today.isoformat()}",
        "",
        f"- ✅ **Cerradas hoy**: {closed_today}",
        f"- 🔥 **Streak actual**: {streak['current']} días "
        f"(récord: {streak['longest']} días)",
        f"- 🚨 **P0 abiertas**: {p0_open}",
        f"- ⏰ **Overdue**: {overdue}",
        f"- 📅 **Days active (730d)**: {streak['active_days']} / {streak['lookback']} "
        f"({streak['active_days']/streak['lookback']*100:.0f}%)",
        "",
        "## Velocidad",
        "",
        _velocity_table(throughput_30, today),
        "",
        "## Headline",
        "",
        R.kpi_block(m),
        "",
        "## Recent throughput",
        "",
        f"- **Últimos 7 días**:  `{R.unicode_sparkline([float(v) for v in last7])}`  "
        f"(avg {sum(last7)/7:.1f}/día, total {sum(last7)})",
        f"- **Últimos 30 días**: `{R.unicode_sparkline([float(v) for v in last30])}`  "
        f"(avg {sum(last30)/30:.1f}/día, total {sum(last30)})",
        "",
        "## Top listas activas (últimos 30 días)",
        "",
        _active_projects_30d(tasks, today),
        "",
        "## Más vistas",
        "",
        "- [[Throughput|Throughput trends]] — daily 90d, weekly 26w, monthly 12m",
        "- [[Streak|Streak history]] — racha actual y récord",
        "- [[Heatmap|Calendar heatmap]] — year + current month",
        "- [[Projects|Project portfolio]]",
        "- [[Tags|Top tags]]",
        "- [[Recent|Recent closures, overdue, P0 open]]",
        "- [[Aging|Open-task aging]]",
        "",
    ])


def _section_daily(throughput: dict[str, int],
                   tasks: list[dict],
                   m: dict,
                   today: dt.date | None = None) -> str:
    """Today-focused dashboard: cerradas hoy, ayer, esta semana, P0/overdue.

    The heaviest panel for daily check-ins. Renders even when nothing was
    closed today (so the user always lands on the current state).
    """
    today = today or dt.date.today()
    yesterday = today - dt.timedelta(days=1)
    week_start = today - dt.timedelta(days=today.weekday())  # Monday

    by_id = {t.get("id"): t for t in tasks}

    # Tasks closed on a given date
    def closed_on(d: dt.date) -> list[dict]:
        out = []
        for t in tasks:
            if t.get("status") != "done":
                continue
            cd = M._parse_date(t.get("closed_at"))
            if cd == d:
                out.append(t)
        return sorted(out, key=lambda t: (t.get("closed_at") or "",
                                          t.get("id") or ""))

    today_closed = closed_on(today)
    yesterday_closed = closed_on(yesterday)

    # P0 open
    p0_open = sorted(
        [t for t in tasks
         if t.get("status") in ("open", "blocked", "waiting")
         and t.get("priority") == "P0"],
        key=lambda t: (t.get("when") or "9999", t.get("id") or "")
    )

    # Overdue (open with `when` < today)
    overdue: list[tuple[int, dict]] = []
    for t in tasks:
        if t.get("status") not in ("open", "blocked", "waiting"):
            continue
        d = M._parse_date(t.get("when"))
        if d and d < today:
            overdue.append(((today - d).days, t))
    overdue.sort(reverse=True, key=lambda x: (x[0], x[1].get("id") or ""))

    # Tasks due today (when == today)
    due_today = [
        t for t in tasks
        if t.get("status") in ("open", "blocked", "waiting")
        and M._parse_date(t.get("when")) == today
    ]
    due_today.sort(key=lambda t: (t.get("priority") or "Z", t.get("id") or ""))

    # Week breakdown (Mon..Sun)
    week_days = []
    for i in range(7):
        d = week_start + dt.timedelta(days=i)
        n = throughput.get(d.isoformat(), 0)
        week_days.append((d, n))
    week_total = sum(n for _, n in week_days)
    wmax = max((n for _, n in week_days), default=0) or 1
    today_idx = today.weekday()

    parts: list[str] = [
        "# Tasks — Daily",
        "",
        f"_Last refresh: {today.isoformat()}_",
        "",
        f"## Hoy — {today.isoformat()} ({today.strftime('%A')})",
        "",
        f"- ✅ **Cerradas hoy**: {len(today_closed)}",
        f"- 🚨 **P0 abiertas**: {len(p0_open)}",
        f"- 📌 **Vencen hoy**: {len(due_today)}",
        f"- ⏰ **Overdue (open)**: {len(overdue)}",
        "",
    ]

    if today_closed:
        parts.append("### Cerradas hoy")
        parts.append("")
        parts.append("| id | priority | title |")
        parts.append("|----|----------|-------|")
        for t in today_closed:
            title = (t.get("title") or "").replace("\n", " ")[:80]
            title = title.replace("|", "\\|")
            parts.append(f"| `{t.get('id', '?')}` | "
                         f"{t.get('priority') or '—'} | {title} |")
        parts.append("")

    if due_today:
        parts.append("### Vencen hoy (open)")
        parts.append("")
        parts.append("| id | priority | title |")
        parts.append("|----|----------|-------|")
        for t in due_today[:30]:
            title = (t.get("title") or "").replace("\n", " ")[:80]
            title = title.replace("|", "\\|")
            parts.append(f"| `{t.get('id', '?')}` | "
                         f"{t.get('priority') or '—'} | {title} |")
        parts.append("")

    if p0_open:
        parts.append(f"### P0 abiertas ({len(p0_open)})")
        parts.append("")
        parts.append("| when | id | title |")
        parts.append("|------|----|-------|")
        for t in p0_open[:25]:
            title = (t.get("title") or "").replace("\n", " ")[:80]
            title = title.replace("|", "\\|")
            parts.append(f"| {t.get('when') or '—'} | "
                         f"`{t.get('id', '?')}` | {title} |")
        parts.append("")

    parts.append(f"## Ayer — {yesterday.isoformat()} ({yesterday.strftime('%A')})")
    parts.append("")
    parts.append(f"Cerradas ayer: **{len(yesterday_closed)}**")
    if yesterday_closed:
        parts.append("")
        for t in yesterday_closed[:15]:
            title = (t.get("title") or "").replace("\n", " ")[:90]
            parts.append(f"- ✅ `{t.get('id', '?')}` — {title}")
        if len(yesterday_closed) > 15:
            parts.append(f"- _… {len(yesterday_closed) - 15} más_")
    parts.append("")

    parts.append(f"## Esta semana — {week_start.isoformat()} →")
    parts.append("")
    parts.append(f"Cerradas esta semana: **{week_total}**")
    parts.append("")
    parts.append("| día | fecha | cerradas | barra |")
    parts.append("|-----|-------|---------:|-------|")
    day_labels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    for i, (d, n) in enumerate(week_days):
        marker = " 👈" if i == today_idx else ""
        parts.append(
            f"| {day_labels[i]}{marker} | `{d.isoformat()}` | {n} | "
            f"`{R.unicode_bar(float(n), float(wmax), 18)}` |"
        )
    parts.append("")

    if overdue:
        parts.append(f"## Overdue ({len(overdue)})")
        parts.append("")
        parts.append("| días | id | priority | title |")
        parts.append("|-----:|----|----------|-------|")
        for age, t in overdue[:25]:
            title = (t.get("title") or "").replace("\n", " ")[:70]
            title = title.replace("|", "\\|")
            parts.append(f"| {age} | `{t.get('id', '?')}` | "
                         f"{t.get('priority') or '—'} | {title} |")
        parts.append("")

    return "\n".join(parts)


def _section_hierarchy(tasks: list[dict]) -> str:
    """Resolve parent-child reminder hierarchy on the fly.

    Calls fetch_reminders in-process to get a fresh ``{reminder_id:
    parent_id}`` map, then joins with the task ledger via the sync_state
    file to surface "parent → children" trees. Read-only; never writes
    back to the ledger.

    Falls back gracefully if the fetcher is unavailable (no Reminders
    permission, EventKit error) — produces a placeholder section.
    """
    parts = [
        "# Tasks — Sub-tareas (jerarquía Reminders)",
        "",
        f"_Last refresh: {dt.date.today().isoformat()}_",
        "",
    ]

    # Live fetch of reminder hierarchy
    try:
        sys.path.insert(0, str(Path("/Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts")))
        from fetch_reminders import fetch as _fetch_rem  # type: ignore
        remote = _fetch_rem()
    except Exception as exc:  # noqa: BLE001
        parts.append(
            f"_Hierarchy fetch failed: `{exc!s}`. The Reminders fetcher "
            f"needs Reminders permission for the Python binary._"
        )
        return "\n".join(parts) + "\n"

    # state: reminder UUID → task_id (so we can link to the right ledger row)
    state_path = LEDGER / ".sync_state/reminders.json"
    state: dict[str, str] = {}
    if state_path.exists():
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        for rid, rec in (raw.get("reminders") or {}).items():
            tid = rec.get("task_id") if isinstance(rec, dict) else None
            if tid:
                state[rid] = tid

    by_id = {t.get("id"): t for t in tasks}
    rem_by_id = {r["id"]: r for r in remote}
    children_of: dict[str, list[dict]] = {}
    for r in remote:
        pid = r.get("parent_id")
        if pid:
            children_of.setdefault(pid, []).append(r)

    if not children_of:
        parts.append("_No hay sub-tareas en este corpus de Reminders._")
        return "\n".join(parts) + "\n"

    n_parents = len(children_of)
    n_children = sum(len(v) for v in children_of.values())
    parts += [
        f"## Resumen",
        "",
        f"- **Padres con sub-tareas**: {n_parents}",
        f"- **Sub-tareas totales**: {n_children}",
        f"- **Promedio**: {n_children/n_parents:.1f} hijas/padre",
        "",
        "## Árboles",
        "",
    ]

    # Sort parents by number of children (most → least)
    parents_sorted = sorted(children_of.items(),
                            key=lambda kv: -len(kv[1]))
    for pid, kids in parents_sorted:
        parent_rem = rem_by_id.get(pid)
        if parent_rem:
            p_title = parent_rem.get("name") or "(sin título)"
            p_list = parent_rem.get("list") or "?"
        else:
            p_title = "(padre eliminado)"
            p_list = "?"
        p_task = by_id.get(state.get(pid, ""))
        p_link = (f"[[02_Tasks_and_Execution/Ledger/Daily/"
                  f"{(p_task.get('id', '')[:10] if p_task else '')}|"
                  f"{p_task.get('id', '?')}]]"
                  if p_task else "—")
        n_done = sum(1 for k in kids if k.get("completed"))
        parts.append(f"### {p_title}  · `{p_list}`  ·  {n_done}/{len(kids)} ✓")
        parts.append("")
        parts.append(f"- parent task: {p_link}")
        parts.append("")
        # Sort kids: open first (alphabetical), then done (chronological by completion)
        open_kids = sorted([k for k in kids if not k.get("completed")],
                           key=lambda k: (k.get("name") or ""))
        done_kids = sorted([k for k in kids if k.get("completed")],
                           key=lambda k: (k.get("completion_date") or ""))
        for k in open_kids + done_kids:
            mark = "✅" if k.get("completed") else "○"
            kt = (k.get("name") or "").replace("\n", " ")[:90]
            kt = kt.replace("|", "\\|")
            ktid = state.get(k["id"], "")
            tid_str = f" · `{ktid}`" if ktid else ""
            parts.append(f"  - {mark} {kt}{tid_str}")
        parts.append("")
    return "\n".join(parts)


def _section_streak(throughput: dict[str, int],
                    tasks: list[dict],
                    today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    streak = _streak_data(throughput, today)
    # Histogram of streak lengths over the lookback window
    flags = [throughput.get((today - dt.timedelta(days=i)).isoformat(), 0) > 0
             for i in range(streak["lookback"] - 1, -1, -1)]
    runs: list[int] = []
    cur = 0
    for v in flags:
        if v:
            cur += 1
        else:
            if cur > 0:
                runs.append(cur)
            cur = 0
    if cur > 0:
        runs.append(cur)
    runs.sort(reverse=True)
    longest_end = streak.get("longest_end") or "—"

    parts = [
        "# Tasks — Streak",
        "",
        f"_Last refresh: {dt.date.today().isoformat()}_",
        "",
        f"## Estado actual",
        "",
        f"- 🔥 **Streak actual**: **{streak['current']} días**",
        f"- 🏆 **Récord histórico**: **{streak['longest']} días** "
        f"(terminó {longest_end})",
        f"- 📅 **Días activos** en últimos {streak['lookback']} días: "
        f"**{streak['active_days']}** "
        f"({streak['active_days']/streak['lookback']*100:.1f}%)",
        f"- 📊 **Rachas distintas**: {len(runs)}",
        "",
        "## Top 10 rachas más largas",
        "",
        "| # | duración (días) |",
        "|---|----------------:|",
    ]
    for i, run in enumerate(runs[:10], 1):
        parts.append(f"| {i} | {run} |")

    # ── Días bomba (top productive days) ──────────────────────────────────
    # Look across the lookback window, find the top 10 days by closures.
    n_days = streak["lookback"]
    day_counts: list[tuple[dt.date, int]] = []
    for i in range(n_days):
        d = today - dt.timedelta(days=i)
        c = throughput.get(d.isoformat(), 0)
        if c > 0:
            day_counts.append((d, c))
    day_counts.sort(key=lambda kv: (-kv[1], kv[0]))
    parts += [
        "",
        f"## 🚀 Días bomba (top 10 días por volumen, últimos {n_days}d)",
        "",
        "| fecha | día | cerradas |",
        "|-------|-----|---------:|",
    ]
    for d, n in day_counts[:10]:
        parts.append(f"| `{d.isoformat()}` | {d.strftime('%A')} | {n} |")

    # ── Rachas de inactividad (longest gaps) ─────────────────────────────
    # Run-length-encode the False (inactive) bins.
    gaps: list[tuple[int, dt.date, dt.date]] = []  # (length, start, end)
    cur_start: dt.date | None = None
    cur_len = 0
    for i in range(n_days):
        d = today - dt.timedelta(days=n_days - 1 - i)
        active = throughput.get(d.isoformat(), 0) > 0
        if not active:
            if cur_start is None:
                cur_start = d
                cur_len = 1
            else:
                cur_len += 1
        else:
            if cur_start is not None:
                gaps.append((cur_len, cur_start, cur_start + dt.timedelta(days=cur_len - 1)))
                cur_start = None
                cur_len = 0
    if cur_start is not None:
        gaps.append((cur_len, cur_start, cur_start + dt.timedelta(days=cur_len - 1)))
    gaps.sort(key=lambda x: (-x[0], x[1]))
    parts += [
        "",
        f"## 💤 Rachas de inactividad (top 10, últimos {n_days}d)",
        "",
        "| longitud (días) | desde | hasta |",
        "|----------------:|-------|-------|",
    ]
    for length, start, end in gaps[:10]:
        parts.append(f"| {length} | `{start.isoformat()}` | `{end.isoformat()}` |")

    parts += [
        "",
        "## Densidad de actividad — últimos 365 días",
        "",
        "Cada celda = 1 día. Bloque = ≥ 1 tarea cerrada.",
        "",
        "```",
    ]
    # 52-week × 7-day grid, oldest top-left, today bottom-right
    from datetime import timedelta as _td
    n = 365
    start = today - _td(days=n - 1)
    # Align to Monday
    while start.weekday() != 0:
        start = start - _td(days=1)
    rows: list[str] = ["Mon Tue Wed Thu Fri Sat Sun"]
    cur_row = ""
    for i, d in enumerate([start + _td(days=k) for k in range(n + 7)]):
        if d > today:
            cell = " "
        else:
            cell = "█" if throughput.get(d.isoformat(), 0) > 0 else "·"
        cur_row += cell + "  "
        if (i + 1) % 7 == 0:
            rows.append(cur_row.rstrip())
            cur_row = ""
    if cur_row.strip():
        rows.append(cur_row.rstrip())
    parts.extend(rows)
    parts.append("```")
    parts.append("")
    return "\n".join(parts)


def _weekly_throughput(tasks: list[dict], n_weeks: int = 26) -> dict[str, int]:
    today = dt.date.today()
    out: dict[str, int] = {}
    for w in range(n_weeks - 1, -1, -1):
        end = today - dt.timedelta(days=today.weekday() + 7 * w)
        start = end - dt.timedelta(days=6)
        iso = f"{start.isocalendar().year}-W{start.isocalendar().week:02d}"
        out[iso] = 0
    for t in tasks:
        if t.get("status") != "done":
            continue
        d = M._parse_date(t.get("closed_at") or t.get("when"))
        if not d:
            continue
        iso = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
        if iso in out:
            out[iso] += 1
    return out


def _monthly_throughput(tasks: list[dict], n_months: int = 12) -> dict[str, int]:
    today = dt.date.today()
    out: dict[str, int] = {}
    y, mo = today.year, today.month
    for _ in range(n_months):
        out[f"{y:04d}-{mo:02d}"] = 0
        mo -= 1
        if mo == 0:
            mo = 12
            y -= 1
    for t in tasks:
        if t.get("status") != "done":
            continue
        d = M._parse_date(t.get("closed_at") or t.get("when"))
        if not d:
            continue
        key = d.strftime("%Y-%m")
        if key in out:
            out[key] += 1
    # reverse so oldest first
    return dict(reversed(list(out.items())))


def _section_throughput(m: dict, tasks: list[dict],
                        throughput_90: dict[str, int]) -> str:
    weekly = _weekly_throughput(tasks)
    monthly = _monthly_throughput(tasks)
    today = dt.date.today()
    last90 = [throughput_90.get((today - dt.timedelta(days=i)).isoformat(), 0)
              for i in range(89, -1, -1)]
    week_vals = list(weekly.values())
    month_vals = list(monthly.values())

    parts = [
        "# Tasks — Throughput",
        "",
        f"_Last refresh: {dt.date.today().isoformat()}_",
        "",
        "## Daily — last 90 days",
        "",
        f"`{R.unicode_sparkline([float(v) for v in last90])}`",
        "",
        f"![throughput_90d](_assets/throughput_90d.png)",
        "",
        f"- **Total closed**: {sum(last90)}",
        f"- **Average / day**: {sum(last90)/90:.2f}",
        f"- **Best day**: {max(last90)} (on "
        f"{(today - dt.timedelta(days=89-last90.index(max(last90)))).isoformat() if max(last90) else '—'})",
        "",
        "## Weekly — last 26 weeks",
        "",
        f"`{R.unicode_sparkline([float(v) for v in week_vals])}`",
        "",
        "| ISO week | closed | bar |",
        "|----------|-------:|-----|",
    ]
    wmax = max(week_vals) if week_vals else 1
    for iso, v in weekly.items():
        parts.append(f"| `{iso}` | {v} | `{R.unicode_bar(float(v), float(wmax), 18)}` |")

    parts += [
        "",
        "## Monthly — last 12 months",
        "",
        f"`{R.unicode_sparkline([float(v) for v in month_vals])}`",
        "",
        "| month | closed | bar |",
        "|-------|-------:|-----|",
    ]
    mmax = max(month_vals) if month_vals else 1
    for ym, v in monthly.items():
        parts.append(f"| `{ym}` | {v} | `{R.unicode_bar(float(v), float(mmax), 18)}` |")

    parts.append("")
    return "\n".join(parts)


def _section_heatmap(m: dict, tasks: list[dict]) -> str:
    today = dt.date.today()
    year = today.year
    year_grid = M.year_heatmap(tasks, year)

    # Three-month view: previous · current · next.
    prev_y, prev_m = (today.year, today.month - 1)
    if prev_m == 0:
        prev_y, prev_m = prev_y - 1, 12
    next_y, next_m = (today.year, today.month + 1)
    if next_m == 13:
        next_y, next_m = next_y + 1, 1
    months = [
        (prev_y, prev_m, "Mes anterior"),
        (today.year, today.month, "Mes actual"),
        (next_y, next_m, "Mes siguiente"),
    ]

    out = [
        "# Tasks — Calendar Heatmap",
        "",
        f"_Last refresh: {today.isoformat()}_",
        "",
        f"## {year} — año completo",
        "",
        f"![heatmap_year](_assets/heatmap_year.png)",
        "",
        "Unicode fallback (renders anywhere):",
        "",
        R.year_heatmap_md(year_grid, year),
        "",
        "## Vista 3 meses (anterior · actual · siguiente)",
        "",
    ]
    for (yy, mm, label) in months:
        # Per-month total of closures
        month_total = 0
        for t in tasks:
            if t.get("status") != "done":
                continue
            d = M._parse_date(t.get("closed_at"))
            if d and d.year == yy and d.month == mm:
                month_total += 1
        grid = M.month_heatmap(tasks, yy, mm)
        out.append(
            f"### {label} — {dt.date(yy, mm, 1).strftime('%B %Y')}  "
            f"·  cerradas: **{month_total}**"
        )
        out.append("")
        out.append(R.month_heatmap_md(grid, yy, mm))
        out.append("")
    return "\n".join(out)


def _section_projects(m: dict) -> str:
    return "\n".join([
        "# Tasks — Project Portfolio",
        "",
        f"_Last refresh: {dt.date.today().isoformat()}_",
        "",
        R.project_portfolio_table(m),
        "",
    ])


def _section_tags(m: dict) -> str:
    return "\n".join([
        "# Tasks — Top Tags",
        "",
        f"_Last refresh: {dt.date.today().isoformat()}_",
        "",
        R.top_tags_table(m, n=30),
        "",
    ])


def _section_aging(m: dict) -> str:
    return "\n".join([
        "# Tasks — Aging of Open Tasks",
        "",
        f"_Last refresh: {dt.date.today().isoformat()}_",
        "",
        R.aging_table(m),
        "",
        "## Cycle-time distribution",
        "",
        f"![cycle_distribution](_assets/cycle_distribution.png)",
        "",
    ])


def _section_recent(tasks: list[dict], m: dict) -> str:
    today = dt.date.today()
    closed = []
    for t in tasks:
        if t.get("status") != "done":
            continue
        d = M._parse_date(t.get("closed_at"))
        if d:
            closed.append((d, t))
    # Stable order: tie-break by task id so the list does not flicker
    # between runs when many tasks closed on the same date.
    closed.sort(reverse=True, key=lambda x: (x[0], x[1].get("id", "")))
    overdue_ids = set(m.get("overdue_ids") or [])
    p0_open = [t for t in tasks
               if t.get("status") in ("open", "blocked", "waiting")
               and t.get("priority") == "P0"]

    parts = [
        "# Tasks — Recent & Critical",
        "",
        f"_Last refresh: {dt.date.today().isoformat()}_",
        "",
        "## Last 30 closures",
        "",
        "| date | id | priority | title |",
        "|------|----|----------|-------|",
    ]
    for d, t in closed[:30]:
        parts.append(
            f"| `{d.isoformat()}` | `{t.get('id', '?')}` | "
            f"{t.get('priority') or '—'} | "
            f"{(t.get('title') or '').replace('|', '\\|')[:80]} |"
        )

    parts += [
        "",
        f"## P0 open ({len(p0_open)})",
        "",
    ]
    if not p0_open:
        parts.append("_No P0 tasks open._")
    else:
        parts.append("| id | when | title |")
        parts.append("|----|------|-------|")
        for t in p0_open[:50]:
            parts.append(
                f"| `{t.get('id', '?')}` | "
                f"{t.get('when') or '—'} | "
                f"{(t.get('title') or '').replace('|', '\\|')[:80]} |"
            )

    parts += [
        "",
        f"## Overdue ({len(overdue_ids)})",
        "",
    ]
    if not overdue_ids:
        parts.append("_Nothing overdue._")
    else:
        by_id = {t.get("id"): t for t in tasks}
        rows = []
        for tid in overdue_ids:
            t = by_id.get(tid)
            if not t:
                continue
            d = M._parse_date(t.get("when"))
            age = (today - d).days if d else None
            rows.append((age or 0, t))
        # Stable tie-break by task id.
        rows.sort(reverse=True, key=lambda x: (x[0], x[1].get("id", "")))
        parts.append("| days overdue | id | priority | title |")
        parts.append("|-------------:|----|----------|-------|")
        for age, t in rows[:50]:
            parts.append(
                f"| {age} | `{t.get('id', '?')}` | "
                f"{t.get('priority') or '—'} | "
                f"{(t.get('title') or '').replace('|', '\\|')[:80]} |"
            )

    parts.append("")
    return "\n".join(parts)


def _section_readme() -> str:
    return "\n".join([
        "# Tasks — Auto-generated dashboards",
        "",
        "Every file in this folder is regenerated by",
        "`task-marshal/scripts/dashboard.py` after each `aggregate.py` run.",
        "Since `aggregate.py` is invoked by `reminders-sync` on every cycle that",
        "produces a CREATE / UPDATE_STATUS / UPDATE_CONTENT, these views update",
        "live as you tick reminders on your phone.",
        "",
        "## Files",
        "",
        "- [[Overview]] — entry point, KPIs and sparklines",
        "- [[Throughput]] — daily / weekly / monthly trends, matplotlib chart",
        "- [[Heatmap]] — calendar heatmap, current month grid",
        "- [[Projects]] — portfolio breakdown",
        "- [[Tags]] — top 30 tags",
        "- [[Recent]] — last 30 closures, P0 open, overdue",
        "- [[Aging]] — open-task age distribution + cycle-time histogram",
        "",
        "## Do not hand-edit",
        "",
        "Manual edits in this folder are clobbered on the next refresh.",
        "Hand-curated dashboards live one level up at",
        "`17_Dashboards/Tasks/Tasks.md` and `17_Dashboards/Tasks/Analytics.md`.",
        "",
    ])


# ── orchestrator ──────────────────────────────────────────────────────────────

def refresh(*, dry_run: bool = False) -> dict:
    """Refresh every dashboard surface from the current ledger state."""
    tasks = _load_tasks()
    if not tasks:
        return {"changed": [], "reason": "no tasks"}

    today = dt.date.today()
    full = M.compute(tasks, today=today)
    throughput = full.get("throughput_by_day") or {}
    cycle_values = list(full.get("cycle_time_days", {}).get("values") or [])

    pages: dict[str, str] = {
        "_README.md": _frontmatter("Tasks dashboard — auto", "tasks_auto_readme") + _section_readme(),
        "Overview.md": _frontmatter("Tasks Overview", "tasks_overview") + _section_overview(full, throughput, tasks),
        "Daily.md": _frontmatter("Tasks Daily", "tasks_daily") + _section_daily(throughput, tasks, full, today),
        "Throughput.md": _frontmatter("Tasks Throughput", "tasks_throughput") + _section_throughput(full, tasks, throughput),
        "Streak.md": _frontmatter("Tasks Streak", "tasks_streak") + _section_streak(throughput, tasks, today),
        "Hierarchy.md": _frontmatter("Tasks Hierarchy", "tasks_hierarchy") + _section_hierarchy(tasks),
        "Heatmap.md": _frontmatter("Tasks Heatmap", "tasks_heatmap") + _section_heatmap(full, tasks),
        "Projects.md": _frontmatter("Tasks Projects", "tasks_projects") + _section_projects(full),
        "Tags.md": _frontmatter("Tasks Tags", "tasks_tags") + _section_tags(full),
        "Recent.md": _frontmatter("Tasks Recent & Critical", "tasks_recent") + _section_recent(tasks, full),
        "Aging.md": _frontmatter("Tasks Aging", "tasks_aging") + _section_aging(full),
    }
    changed: list[str] = []
    if not dry_run:
        for name, content in pages.items():
            p = DASH / name
            if _write_if_changed(p, content):
                changed.append(str(p.relative_to(VAULT)))

    # Charts
    charts: dict[str, bytes | None] = {
        "throughput_90d.png": _chart_throughput_90d(throughput),
        "heatmap_year.png": _chart_year_heatmap(throughput, today.year),
        "cycle_distribution.png": _chart_cycle_distribution(cycle_values),
    }
    if not dry_run:
        for name, blob in charts.items():
            if blob is None:
                continue
            p = ASSETS / name
            if _write_if_changed(p, blob):
                changed.append(str(p.relative_to(VAULT)))

    return {"changed": changed, "tasks_scanned": len(tasks)}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    res = refresh(dry_run=args.dry_run)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
