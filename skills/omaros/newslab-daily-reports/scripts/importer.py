#!/usr/bin/env python3
"""Drip importer daemon for GDELT — decouples the network burst from the report.

GDELT DOC 2.1 enforces a rolling-volume throttle: a full daily run (7 topics ×
~8 queries × 2 modes ≈ 100+ calls) trips it within seconds, and *concurrency*
makes it worse. The robust answer is the opposite of async-burst: a single,
slow, sequential drip. This daemon fetches ONE (topic, query) per tick, spaced
by a base interval, with exponential backoff when the throttle bites, and writes
each raw response into a per-UTC-day cache. ``cache_pipeline.py`` then builds the
report from that cache with zero network I/O.

Cache layout (consumed verbatim by cache_pipeline.py via ReplayTransport):
    outputs/cache/<YYYY-MM-DD>/<topic>/<query_slug>.artlist.json
    outputs/cache/<YYYY-MM-DD>/<topic>/<query_slug>.tone.json

State is the cache itself: a query is "done" for the day once its artlist file
exists, so a restart resumes exactly where it stopped and a new UTC day starts a
fresh corpus. A 200-with-no-articles response is a legitimate result and is
cached; only transport errors (429 / timeout) trigger backoff-and-retry.

Runs under the NewsLab venv (imports quant_news). Long-lived; launchd KeepAlive.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from quant_news.adapters.transport import LiveHttpTransport
from quant_news.config import load_source_config, load_topics

NEWSLAB = Path(os.environ.get("NLDR_NEWSLAB", "/Users/omarkhalil/GitHub/NewsLab"))
CACHE_ROOT = NEWSLAB / "outputs" / "cache"
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# Self-healing re-run: when the morning 07:00 report was partial, regenerate it
# once the drip has accumulated meaningfully more coverage.
OMAROS_ROOT = Path("/Users/omarkhalil/OmarOS")
OMAROS_PY = Path("/Users/omarkhalil/.venvs/omaros/bin/python")
SYNC_PY = OMAROS_ROOT / ".claude" / "skills" / "newslab-daily-reports" / "scripts" / "sync.py"
REPORT_STATE = OMAROS_ROOT / "02_Tasks_and_Execution" / "Ledger" / ".sync_state" / "newslab_daily_reports.json"
RERUN_MIN_TOPICS = int(os.environ.get("NLDR_RERUN_MIN_TOPICS", "3"))

TOPICS_FILTER = {t.strip() for t in os.environ.get("NLDR_TOPICS", "").split(",") if t.strip()}
TIMESPAN = os.environ.get("NLDR_TIMESPAN", "1d")
MAX_RECORDS = os.environ.get("NLDR_MAX", "250")     # GDELT DOC artlist hard cap; honours platform.yaml osint.max_articles_per_topic
BASE_INTERVAL = float(os.environ.get("NLDR_BASE_INTERVAL", "300"))     # seconds between successful drips
MAX_BACKOFF = float(os.environ.get("NLDR_MAX_BACKOFF", "1800"))        # cap on throttle backoff
IDLE_INTERVAL = float(os.environ.get("NLDR_IDLE_INTERVAL", "1800"))    # sleep once the day's corpus is complete


def log(msg: str) -> None:
    print(f"[newslab-importer {datetime.now(UTC).isoformat()}] {msg}", flush=True)


def query_slug(query: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_") or "q"


def _pending(cache_day: Path, plan: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out = []
    for topic, query in plan:
        if not (cache_day / topic / f"{query_slug(query)}.artlist.json").exists():
            out.append((topic, query))
    return out


def _build_plan() -> list[tuple[str, str]]:
    plan: list[tuple[str, str]] = []
    for tc in load_topics():
        if TOPICS_FILTER and tc.name not in TOPICS_FILTER:
            continue
        for q in tc.queries:
            plan.append((tc.name, q))
    return plan


def _topics_present(cache_day: Path) -> set[str]:
    if not cache_day.exists():
        return set()
    return {d.name for d in cache_day.iterdir() if d.is_dir() and any(d.glob("*.artlist.json"))}


def maybe_trigger_rerun(day: str, cache_day: Path) -> None:
    """Keep today's published report in step with the drip corpus.

    The morning 07:00 report is generated from whatever the throttle-slowed drip
    has cached by then — often only the first two or three topics. As later topics
    land, this regenerates the report so it *converges* to the full topic set,
    firing once at each new coverage level (5 → 6 → 7 …) rather than freezing at
    the first upgrade. The high-water mark lives in the cache dir, seeded from the
    morning publish's covered-topic count, and is compared present-count against
    present-count (a topic counts as "present" once it has any cached query, even
    if that query returned zero articles) so a genuinely empty topic can never
    stall the corpus at full coverage and loop forever. The per-day marker is set
    before spawning, so a regeneration in flight cannot be double-triggered."""
    present = _topics_present(cache_day)
    if len(present) < RERUN_MIN_TOPICS:                  # never publish a near-empty report
        return
    try:
        st = json.loads(REPORT_STATE.read_text(encoding="utf-8"))
    except Exception:
        return
    if st.get("last_run_date") != day:                  # morning report not run yet today
        return
    hwm_file = cache_day / ".rerun_hwm"
    try:
        hwm = int(hwm_file.read_text(encoding="utf-8"))
    except Exception:
        hwm = int(st.get("topics_covered", 0))           # seed from the morning publish
    if len(present) <= hwm:                              # report already as complete as the cache allows
        return
    log(f"{len(present)} topics now cached (> last published {hwm}); "
        f"triggering report regeneration")
    hwm_file.write_text(str(len(present)), encoding="utf-8")   # set before spawning → no double-trigger
    env = {
        **os.environ,
        "NLDR_FORCE": "1", "NLDR_LLM": "1", "NLDR_PUSH": "1", "NLDR_SOURCE": "cache",
        "NLDR_TOPICS": os.environ.get(
            "NLDR_TOPICS", "energy,geopolitics,macro,markets,supply_chains,social_unrest,technology"
        ),
    }
    try:
        subprocess.run([str(OMAROS_PY), str(SYNC_PY)], env=env, timeout=2400, check=False)
        log("forced regeneration finished")
    except Exception as exc:
        log(f"forced regeneration failed: {exc!r}")


def main() -> int:
    src_cfg = load_source_config()
    transport = LiveHttpTransport(
        GDELT_URL,
        user_agent=src_cfg.user_agent,
        timeout_seconds=src_cfg.timeout_seconds,
        max_attempts=src_cfg.max_attempts,
        min_interval_seconds=max(src_cfg.min_interval_seconds, 5.0),
    )
    plan = _build_plan()
    log(f"importer up: {len(plan)} (topic, query) pairs; base interval {BASE_INTERVAL}s")

    consecutive_failures = 0
    tick = 0
    while True:
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        cache_day = CACHE_ROOT / day
        maybe_trigger_rerun(day, cache_day)
        pending = _pending(cache_day, plan)
        if not pending:
            log(f"{day}: corpus complete ({len(plan)} queries cached); idling {IDLE_INTERVAL}s")
            time.sleep(IDLE_INTERVAL)
            continue

        # Rotate through pending so a single persistently-throttled query cannot
        # starve every later topic (the throttle is global, but a malformed query
        # would otherwise block the queue forever).
        topic, query = pending[tick % len(pending)]
        tick += 1
        slug = query_slug(query)
        dest_dir = cache_day / topic
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            artlist = transport.get(
                {
                    "query": query, "mode": "artlist", "format": "json",
                    "timespan": TIMESPAN, "maxrecords": MAX_RECORDS, "sort": src_cfg.sort,
                }
            )
            tone = transport.get(
                {"query": query, "mode": "timelinetone", "format": "json", "timespan": TIMESPAN}
            )
            (dest_dir / f"{slug}.artlist.json").write_text(artlist, encoding="utf-8")
            (dest_dir / f"{slug}.tone.json").write_text(tone, encoding="utf-8")
            consecutive_failures = 0
            remaining = len(pending) - 1
            log(f"cached {topic}/{query!r} ({remaining} left today); sleeping {BASE_INTERVAL}s")
            time.sleep(BASE_INTERVAL)
        except Exception as exc:
            consecutive_failures += 1
            backoff = min(BASE_INTERVAL * (2 ** consecutive_failures), MAX_BACKOFF)
            log(f"throttled/error on {topic}/{query!r}: {exc!r}; backoff {backoff:.0f}s "
                f"(consecutive failures: {consecutive_failures})")
            time.sleep(backoff)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
