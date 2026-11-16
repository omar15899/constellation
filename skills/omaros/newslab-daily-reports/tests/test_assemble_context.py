"""Tests for the deterministic context-bundle builder.

Run under the NewsLab venv (imports quant_news via assemble_context):
    /Users/omarkhalil/GitHub/NewsLab/.venv/bin/python -m pytest <this dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import assemble_context as ac  # noqa: E402

_CAVEATS = """## Methodological caveats

This pipeline observes the world only through its media reflection. Model the
data-generating process as `Y_t = h(Z_t) + epsilon_t`. Every figure is a
property of `Y_t`, not of `Z_t`.
"""


def _report(total: int, energy: int) -> str:
    return f"""# Global News Intelligence — 2026-06-01

## Executive summary

- Total articles: {total}
- Distinct topics: 1
- Total alerts: 0

## Global risk overview

| Topic | Articles | Sources | Avg tone | Alerts |
| --- | ---: | ---: | ---: | ---: |
| Energy | {energy} | 3 | n/a | 0 |
| Geopolitics | 0 | 0 | n/a | 0 |
| Macro | 0 | 0 | n/a | 0 |
| Markets | 0 | 0 | n/a | 0 |
| Supply chains | 0 | 0 | n/a | 0 |
| Social unrest | 0 | 0 | n/a | 0 |
| Technology | 0 | 0 | n/a | 0 |

## Energy

- Articles: {energy}

{_CAVEATS}"""


def test_empty_data_aborts():
    with pytest.raises(SystemExit):
        ac.build_bundle(as_of="2026-06-01", report_md=_report(0, 0), history={})


def test_bundle_contains_report_caveats_and_regime():
    bundle = ac.build_bundle(as_of="2026-06-01", report_md=_report(12, 12), history={"energy": [2, 3, 2, 3, 12]})
    assert "## Deterministic report (verbatim — source of truth)" in bundle
    assert "Y_t = h(Z_t) + epsilon_t" in bundle           # caveats preserved
    assert "## Machine-readable signals" in bundle
    assert "## MANDATORY caveats block" in bundle
    assert '"source": "gdelt-doc-2.1"' in bundle


def test_regime_reacts_to_volume_spike():
    # prior energy ~2-3, today 12 → large z-score → a non-normal regime label
    # must appear (stress or crisis), proving the detector is actually wired in.
    bundle = ac.build_bundle(as_of="2026-06-01", report_md=_report(12, 12), history={"energy": [2, 3, 2, 3, 12]})
    assert ("stress" in bundle) or ("crisis" in bundle)


def test_byte_deterministic():
    args = dict(as_of="2026-06-01", report_md=_report(12, 12), history={"energy": [2, 3, 2, 3, 12]})
    assert ac.build_bundle(**args) == ac.build_bundle(**args)
