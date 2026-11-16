"""Tests for the post-write safety linter (stdlib-only; any interpreter)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import safety_lint  # noqa: E402

_DETERMINISTIC = """# Report

## Methodological caveats

This pipeline observes the world only through its media reflection.
Model it as `Y_t = h(Z_t) + epsilon_t`; every figure is a property of `Y_t`.

## Provenance

| Topic | Feature digest |
"""

_CAVEATS_BLOCK = (
    "This pipeline observes the world only through its media reflection.\n"
    "Model it as `Y_t = h(Z_t) + epsilon_t`; every figure is a property of `Y_t`."
)


def _study(extra: str = "", *, with_caveats: bool = True) -> str:
    body = "# Study\n\nMedia coverage of energy rose this week.\n"
    if with_caveats:
        body += f"\n## Methodological caveats\n\n{_CAVEATS_BLOCK}\n"
    return body + ("\n" + extra if extra else "")


def test_clean_report_passes():
    assert safety_lint.lint(_study(), _DETERMINISTIC) == []


def test_missing_caveats_fails():
    v = safety_lint.lint(_study(with_caveats=False), _DETERMINISTIC)
    assert any("caveats" in x for x in v)


def test_forbidden_price_target_fails():
    v = safety_lint.lint(_study("Our price target is 120."), _DETERMINISTIC)
    assert any("price target" in x for x in v)


def test_forbidden_recommendation_fails():
    v = safety_lint.lint(_study("We recommend buying energy names."), _DETERMINISTIC)
    assert v  # trade recommendation flagged


def test_forbidden_directional_forecast_fails():
    v = safety_lint.lint(_study("Gas prices will surge next week."), _DETERMINISTIC)
    assert any("directional" in x for x in v)


def test_ordinary_reportage_not_flagged():
    # "the company will sell assets" / "inflation rose" are honest reportage.
    text = _study("The utility plans to sell its grid unit; inflation rose to 3%.")
    assert safety_lint.lint(text, _DETERMINISTIC) == []
