#!/usr/bin/env python3
"""Deterministic context-bundle builder for the NewsLab daily report.

Consumes the artefacts that ``scripts/run_daily_pipeline.py`` already wrote for a
given ``as_of`` date — the governed markdown report and the per-topic
article-count history — and produces a single hand-off file that is the *sole*
input to the downstream headless-Claude step. The LLM never touches GDELT or the
network; it only elevates this deterministic bundle into a scholar-style study.

What this step adds on top of the rendered report:

* **Empty-data guard (B1).** If the report shows zero total articles (e.g. every
  live GDELT query was throttled), it exits non-zero so the orchestrator aborts
  before any LLM call or commit — no report is ever written from an empty
  FeatureSet.
* **Regime wiring (M6).** ``run_daily_pipeline.py`` computes z-score alerts but
  never invokes the regime detector. Here each topic's article-count z-score
  drives ``RuleBasedRegimeDetector.infer_regime`` (tone/shock/volatility inputs
  stay 0.0 — honestly unavailable from GDELT's artlist mode), yielding a
  per-topic and an aggregate regime state.
* **A verbatim caveats block** the LLM is required to reproduce unchanged.

The output is byte-deterministic in its inputs (the only time reference is the
passed ``--as-of``), so the bundle is reproducible and testable.

Runs under the NewsLab venv (imports ``quant_news``).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

from quant_news.alerts import zscore_alerts
from quant_news.regimes.rule_based_regime_detector import RuleBasedRegimeDetector

CANONICAL_TOPICS = (
    "energy",
    "geopolitics",
    "macro",
    "markets",
    "supply_chains",
    "social_unrest",
    "technology",
)


def _label_to_key(label: str) -> str:
    return label.strip().lower().replace(" ", "_")


def _parse_total_articles(report_md: str) -> int:
    m = re.search(r"^- Total articles:\s*(\d+)\s*$", report_md, flags=re.MULTILINE)
    return int(m.group(1)) if m else 0


def _parse_overview_counts(report_md: str) -> dict[str, int]:
    """Parse the Global risk overview table into ``{topic_key: article_count}``."""
    counts: dict[str, int] = {}
    in_table = False
    for line in report_md.splitlines():
        if line.startswith("## Global risk overview"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or cells[0] in {"Topic", "---"} or cells[0].startswith("-"):
                continue
            key = _label_to_key(cells[0])
            try:
                counts[key] = int(cells[1])
            except ValueError:
                continue
    return counts


def _zscore(prior: list[float], current: float) -> float:
    """Sample z-score of ``current`` against ``prior``; 0.0 when undefined.

    Mirrors the convention in ``quant_news.alerts``: a series with fewer than two
    observations or zero variance admits no scale and reads as 0.0.
    """
    if len(prior) < 2:
        return 0.0
    std = statistics.stdev(prior)
    if std == 0.0:
        return 0.0
    return round((current - statistics.mean(prior)) / std, 4)


def _detector_features(article_count_zscore: float) -> dict[str, float]:
    """Map the one robustly-available signal into the detector's namespace.

    Only the article-volume z-score is honestly observable from GDELT's artlist
    mode. Negative-tone, shock-score, and volatility inputs require per-article
    tone, a shock kernel, and market data respectively — none wired in the MVP —
    so they read as 0.0, and the regime is volume-anomaly driven by design.
    """
    return {
        "topic_article_count_zscore": article_count_zscore,
        "negative_tone_zscore": 0.0,
        "geopolitical_event_count": 0.0,
        "volatility_zscore": 0.0,
    }


def build_bundle(*, as_of: str, report_md: str, history: dict[str, list[float]]) -> str:
    total = _parse_total_articles(report_md)
    if total <= 0:
        raise SystemExit(
            f"[abort] deterministic report for {as_of} has zero total articles — "
            "refusing to assemble context (no LLM, no commit)."
        )

    current_counts = _parse_overview_counts(report_md)
    # The pipeline appends today's count before this step runs; exclude it so the
    # z-scores and alerts reproduce exactly what the report computed.
    prior_history = {k: [float(x) for x in v[:-1]] for k, v in history.items()}
    current = {k: float(v) for k, v in current_counts.items() if v > 0}

    alerts = zscore_alerts("article_count", prior_history, current, threshold=2.0)
    detector = RuleBasedRegimeDetector()

    per_topic: list[dict] = []
    max_z = 0.0
    for topic in CANONICAL_TOPICS:
        count = current_counts.get(topic, 0)
        z = _zscore(prior_history.get(topic, []), float(count)) if count > 0 else 0.0
        max_z = max(max_z, z)
        state = detector.infer_regime(_detector_features(z), asof_time=f"{topic}@{as_of}")
        per_topic.append(
            {
                "topic": topic,
                "article_count": count,
                "article_count_zscore": z,
                "regime": state.label.value,
                "regime_confidence": round(state.confidence, 4),
                "regime_rationale": state.rationale,
            }
        )

    aggregate_state = detector.infer_regime(_detector_features(max_z), asof_time=f"aggregate@{as_of}")
    machine_block = {
        "as_of": as_of,
        "source": "gdelt-doc-2.1",
        "total_articles": total,
        "aggregate_regime": {
            "label": aggregate_state.label.value,
            "confidence": round(aggregate_state.confidence, 4),
            "rationale": aggregate_state.rationale,
        },
        "topics": per_topic,
        "alerts": [
            {
                "topic": a.topic,
                "metric": a.metric,
                "value": a.value,
                "mean": a.mean,
                "std": a.std,
                "zscore": a.zscore,
                "direction": a.direction,
            }
            for a in alerts
        ],
    }

    caveats = _extract_caveats(report_md)

    lines: list[str] = []
    lines.append(f"# NewsLab daily context bundle — {as_of}")
    lines.append("")
    lines.append(
        "This bundle is the deterministic, causally-admissible substrate for the "
        "daily study. It is the SOLE input to the report writer. Do not introduce "
        "any fact, number, entity, or claim not present below. The data describes a "
        "**media-coverage** process (GDELT DOC 2.1), not ground truth."
    )
    lines.append("")
    lines.append("## Machine-readable signals")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(machine_block, indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")
    lines.append("## Regime summary")
    lines.append("")
    lines.append("| Topic | Articles | Count z-score | Regime | Confidence |")
    lines.append("| --- | ---: | ---: | --- | ---: |")
    for row in per_topic:
        lines.append(
            f"| {row['topic']} | {row['article_count']} | {row['article_count_zscore']:.4f} "
            f"| {row['regime']} | {row['regime_confidence']:.4f} |"
        )
    lines.append(
        f"| **aggregate** | {total} | {max_z:.4f} | {aggregate_state.label.value} "
        f"| {round(aggregate_state.confidence, 4):.4f} |"
    )
    lines.append("")
    lines.append("## Deterministic report (verbatim — source of truth)")
    lines.append("")
    lines.append(report_md.strip())
    lines.append("")
    lines.append("## MANDATORY caveats block — reproduce VERBATIM in the study")
    lines.append("")
    lines.append("The elevated report MUST contain the following block unchanged, under a")
    lines.append('"## Methodological caveats" heading. Do not paraphrase, summarise, or drop it.')
    lines.append("")
    lines.append(caveats)
    lines.append("")
    return "\n".join(lines)


def _extract_caveats(report_md: str) -> str:
    heading = "## Methodological caveats"
    start = report_md.find(heading)
    if start == -1:
        return ""
    body_start = start + len(heading)
    nxt = report_md.find("\n## ", body_start)
    section = report_md[body_start:] if nxt == -1 else report_md[body_start:nxt]
    return section.strip()


def _run(args: argparse.Namespace) -> int:
    root = Path(args.newslab_root)
    report_path = args.report or (root / "outputs" / "reports" / f"{args.as_of}.md")
    history_path = args.history or (root / "outputs" / "features" / "history.json")
    out_path = args.out or (root / "outputs" / "context" / f"{args.as_of}.md")

    if not report_path.exists():
        print(f"[abort] deterministic report not found: {report_path}", file=sys.stderr)
        return 2

    report_md = report_path.read_text(encoding="utf-8")
    history: dict[str, list[float]] = {}
    if history_path.exists():
        raw = json.loads(history_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            history = {str(k): [float(x) for x in v] for k, v in raw.items()}

    bundle = build_bundle(as_of=args.as_of, report_md=report_md, history=history)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(bundle, encoding="utf-8")
    print(f"context bundle written to {out_path}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--as-of", required=True, dest="as_of", help="YYYY-MM-DD report date.")
    parser.add_argument(
        "--newslab-root",
        default="/Users/omarkhalil/GitHub/NewsLab",
        dest="newslab_root",
        help="NewsLab repo root.",
    )
    parser.add_argument("--report", type=Path, default=None, help="Override deterministic report path.")
    parser.add_argument("--history", type=Path, default=None, help="Override history.json path.")
    parser.add_argument("--out", type=Path, default=None, help="Override context bundle output path.")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(_run(_parse_args()))
