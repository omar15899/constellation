#!/usr/bin/env python3
"""Build the deterministic daily report from a drip-cached GDELT corpus.

The importer daemon (``importer.py``) slowly accumulates each (topic, query)'s raw
GDELT response into a per-day cache, staying under GDELT's rolling-volume throttle.
This builder reads that cache and produces the same governed report that
``run_daily_pipeline.py`` would have, by replaying each cached response through the
*identical* live code path (``ReplayTransport`` → ``GdeltAdapter`` → ``run_topic``).
No network I/O happens here — the burst is decoupled from the report.

A query with no cached file is simply skipped (graceful partial coverage); a topic
with no cached queries renders as zero-coverage. Reuses ``run_daily_pipeline``'s
merge/alerts/render logic verbatim so cache-built and live-built reports are
byte-identical given identical inputs.

Runs under the NewsLab venv (imports ``quant_news``).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from quant_news.adapters._capabilities import gdelt_capability
from quant_news.adapters.gdelt import GdeltAdapter, GdeltQuery
from quant_news.adapters.transport import ReplayTransport
from quant_news.alerts import zscore_alerts
from quant_news.build import TopicResult, run_topic
from quant_news.config import load_source_config, load_topics
from quant_news.features.aggregate import DailySignal
from quant_news.ontology import load_ontology
from quant_news.report import render_daily_report

_HISTORY_CAP = 90


def query_slug(query: str) -> str:
    """Filesystem-safe, importer/builder-agreed slug for a GDELT query string."""
    return re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_") or "q"


def _as_of_date() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _load_history(path: Path) -> dict[str, list[float]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): [float(x) for x in v] for k, v in data.items()} if isinstance(data, dict) else {}


def _save_history(path: Path, history: dict[str, list[float]], current: dict[str, float]) -> None:
    merged = {k: list(v) for k, v in history.items()}
    for topic, value in current.items():
        merged.setdefault(topic, []).append(value)
    merged = {k: v[-_HISTORY_CAP:] for k, v in merged.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=2, sort_keys=True), encoding="utf-8")


def _import_run_daily_pipeline():
    """Load run_daily_pipeline as a module to reuse its exact _merge_signals."""
    import importlib.util

    script = _newslab_root() / "scripts" / "run_daily_pipeline.py"
    spec = importlib.util.spec_from_file_location("run_daily_pipeline", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_NEWSLAB_ROOT = Path("/Users/omarkhalil/GitHub/NewsLab")


def _newslab_root() -> Path:
    return _NEWSLAB_ROOT


def _run(args: argparse.Namespace) -> int:
    global _NEWSLAB_ROOT
    _NEWSLAB_ROOT = Path(args.newslab_root)
    print("GDELT measures media coverage, not ground truth.", file=sys.stderr)

    as_of = args.as_of or _as_of_date()
    cache_dir = Path(args.cache_dir) if args.cache_dir else (_NEWSLAB_ROOT / "outputs" / "cache" / as_of)
    requested = {t.strip() for t in args.topics.split(",") if t.strip()}

    src_cfg = load_source_config()
    all_topics = {tc.name: tc for tc in load_topics()}
    ontology = load_ontology()
    capability = gdelt_capability()
    rdp = _import_run_daily_pipeline()

    all_signals: list[DailySignal] = []
    all_digests: dict[str, str] = {}
    cached_queries = 0

    for topic_name in sorted(requested):
        queries = all_topics[topic_name].queries if topic_name in all_topics else (topic_name,)
        topic_signals: list[DailySignal] = []
        topic_digests: list[str] = []

        for q_str in queries:
            slug = query_slug(q_str)
            artlist = cache_dir / topic_name / f"{slug}.artlist.json"
            if not artlist.exists():
                continue
            tone = cache_dir / topic_name / f"{slug}.tone.json"
            transport = ReplayTransport.from_files(
                artlist=artlist, timelinetone=tone if tone.exists() else None
            )
            adapter = GdeltAdapter(transport, src_cfg)
            gq = GdeltQuery(topic=topic_name, query=q_str, timespan=args.timespan, max_records=args.max)
            try:
                result: TopicResult = run_topic(
                    adapter, gq, ontology=ontology, capability=capability, fetch_tone=tone.exists()
                )
            except Exception as exc:  # a corrupt cache file should not kill the run
                print(f"  [warn] cache build failed for {topic_name}/{q_str!r}: {exc}", file=sys.stderr)
                continue
            cached_queries += 1
            topic_digests.append(result.feature_set.value.audit_root.short())
            topic_signals.append(result.signal)

        if topic_signals:
            merged = rdp._merge_signals(topic_signals, topic=topic_name, as_of=as_of)
            all_signals.append(merged)
            all_digests[topic_name] = topic_digests[0] if topic_digests else ""
            print(f"  {topic_name}: {merged.article_count} articles from {len(topic_signals)} cached queries")

    history_path = Path(args.history)
    history = _load_history(history_path)
    current = {s.topic: float(s.article_count) for s in all_signals}
    alerts = zscore_alerts("article_count", history, current, threshold=args.zthreshold)
    _save_history(history_path, history, current)

    report_dir = Path(args.report_out)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{as_of}.md"
    report_text = render_daily_report(
        as_of=as_of, signals=all_signals, alerts=alerts, feature_digests=all_digests
    )
    report_path.write_text(report_text, encoding="utf-8")
    total = sum(s.article_count for s in all_signals)
    print(f"\nReport written to {report_path} ({total} articles from {cached_queries} cached queries)")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--as-of", dest="as_of", default=None, help="YYYY-MM-DD (default: today UTC).")
    parser.add_argument("--newslab-root", dest="newslab_root", default="/Users/omarkhalil/GitHub/NewsLab")
    parser.add_argument("--cache-dir", dest="cache_dir", default=None, help="Per-day cache dir.")
    parser.add_argument("--topics", default="energy")
    parser.add_argument("--timespan", default="1d")
    parser.add_argument("--max", type=int, default=250, dest="max")
    parser.add_argument("--report-out", dest="report_out", default="/Users/omarkhalil/GitHub/NewsLab/outputs/reports")
    parser.add_argument("--history", default="/Users/omarkhalil/GitHub/NewsLab/outputs/features/history.json")
    parser.add_argument("--zthreshold", type=float, default=2.0)
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(_run(_parse_args()))
