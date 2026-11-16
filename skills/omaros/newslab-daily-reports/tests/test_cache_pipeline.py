"""Tests for the cache-sourced report builder (NewsLab venv: imports quant_news)."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cache_pipeline as cp  # noqa: E402

_FIXTURES = Path("/Users/omarkhalil/GitHub/NewsLab/packages/quant_news/tests/fixtures")
_ART = _FIXTURES / "gdelt_artlist_sample.json"
_TONE = _FIXTURES / "gdelt_timelinetone_sample.json"


def _stage(cache_day: Path, topic: str, queries, *, with_tone: bool = True) -> None:
    d = cache_day / topic
    d.mkdir(parents=True, exist_ok=True)
    for q in queries:
        shutil.copy(_ART, d / f"{cp.query_slug(q)}.artlist.json")
        if with_tone:
            shutil.copy(_TONE, d / f"{cp.query_slug(q)}.tone.json")


def _ns(cache_dir: Path, report_out: Path, history: Path) -> argparse.Namespace:
    return argparse.Namespace(
        as_of="2026-06-01",
        newslab_root="/Users/omarkhalil/GitHub/NewsLab",
        cache_dir=str(cache_dir),
        topics="energy,macro,markets",
        timespan="1d",
        max=75,
        report_out=str(report_out),
        history=str(history),
        zthreshold=2.0,
    )


def test_builds_report_from_cache(tmp_path):
    from quant_news.config import load_topics

    topics = {tc.name: tc for tc in load_topics()}
    cache_day = tmp_path / "2026-06-01"
    _stage(cache_day, "energy", topics["energy"].queries)        # full coverage
    _stage(cache_day, "macro", topics["macro"].queries[:2])      # partial coverage
    # markets: nothing staged → must render as zero-coverage, not crash

    rc = cp._run(_ns(cache_day, tmp_path / "out", tmp_path / "history.json"))
    assert rc == 0
    report = (tmp_path / "out" / "2026-06-01.md").read_text()
    assert "| Energy |" in report
    assert "Total articles:" in report
    # energy fully cached → non-zero; markets uncached → zero-coverage line present
    assert "_No coverage ingested for this window._" in report


def test_query_slug_stable():
    assert cp.query_slug("natural gas") == "natural_gas"
    assert cp.query_slug("TTF gas") == "ttf_gas"
    assert cp.query_slug("Russia gas sanctions") == "russia_gas_sanctions"
