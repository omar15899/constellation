# Promotion-Gate Contract

*Constellation plane. The standing statistical bar a research result must clear
before it may be called CONFIRMED, and the vocabulary every verdict uses. This is
the methodology Omar has already paid to discover — encoded so it is not
re-derived or quietly relaxed each session. Planning decision: the bar is the
user's; Claude may not lower it to make a result pass.*

## Why a gate exists

The Sharpe t-stat is i.i.d.-normal (Lo 2002) and **overstates** significance on
overlapping H=21/63 rebalances. With ~170 configs swept, a high Sharpe is a draw
from a large search, not evidence. Every headline number is guilty until it
survives multiple-testing-aware inference.

## The bar (CONFIRMED requires ALL of)

A candidate cell is **CONFIRMED** iff **all four** hold:

1. **BH–FDR** adjusted p < α — Benjamini–Hochberg across the family.
2. **Block-bootstrap Sharpe CI** lower bound > 0 — the edge survives resampling.
3. **Annualised Sharpe ≥ min** — economic, not just statistical, size.
4. **DSR > 0.95** — Deflated Sharpe Ratio (Bailey & López de Prado): corrects for
   sample length, skew, fat tails **and** trial count.

Supporting diagnostics that qualify or kill a verdict:

- **PBO via CSCV** (Bailey–Borwein–LdP–Zhu) — Probability of Backtest
  Overfitting. High PBO (≳0.5, and certainly 0.9+) means the in-sample winner is
  expected to underperform OOS — REFUTE regardless of headline Sharpe.
- **White's Reality Check** — is the best cell better than the family's best by
  chance?
- **Robust objective J** = Sharpe − penalties(turnover, maxDD, factor-exposure,
  instability). Selection is on J, not raw Sharpe.

## Engine provenance (required since 2026-07-01)

The statistical bars are necessary but not sufficient. A **CONFIRMED** at
`run_class: deployable` or `production` additionally requires **engine
evidence** from the canonical audited backtester (BacktestLab):

- the cell's `metrics.json` carries a `backtestlab` block with a non-null
  `audit_root` (the audited causal kernel replayed this config), **or**
- a BacktestLab **reconciliation PASS** artifact exists for the same
  experiment (predefined tolerances; ResearchLab
  `docs/architecture/2026-07-01_single_backtester_unification_plan.md`).

Vectorised-engine-only evidence caps the verdict at **HOLD** — ResearchLab
enforces this inside the gate (`LTR_GATE_AUDIT=warn|enforce`; outputs stamped
`engine_class: diagnostic` are categorically unaudited), and
`record_lever_verdict.py` refuses to record such a CONFIRMED in strict mode.
The vectorised engine remains legitimate for diagnostics, exploration and
candidate generation only. Legacy CONFIRMED rows keep their verdicts but carry
the "vectorised-engine evidence only" label in their notes until reconciled.

## The multiple-testing denominator m (non-negotiable)

**The family you tried IS the denominator.** Pass *every* cell swept through the
gate, not just the survivor. A cell CONFIRMED at m=5 is only **CAPPED** at m=35.
Silently shrinking m to make a cell pass is relaxing a planning decision — it is
forbidden. State m explicitly with every verdict.

## Verdict vocabulary (canonical)

| verdict          | meaning                                                                 |
| ---------------- | ----------------------------------------------------------------------- |
| `OPEN`           | hypothesis stated, not yet tested to a verdict                          |
| `CONFIRMED`      | passes all four bars at the honest m — a real edge                      |
| `CAPPED`         | real but bounded: just under a bar (e.g. DSR ~0.89–0.94), or de-risks but no Sharpe gain |
| `NO_IMPROVEMENT` | adds nothing beyond the incumbent baseline                              |
| `REFUTED`        | fails the gate / negative / overfit (high PBO) — **do not re-run**      |
| `HOLD`           | inconclusive or blocked on data; parked, not closed                     |

## Run-class discipline (tag every headline)

- **deployable** — tradable now (current-universe).
- **broad-floor** — survivorship-honest unbiased lower bound.
- **diagnostic** — exploratory, not a claim.
- **production** — the committed result.

**Hard rule:** never filter a historical broad universe by *current* tradability
unless the number is explicitly labelled survivorship-biased. The deployable
headline and the broad floor are different runs and must never be conflated.

## Implementation (authoritative code)

Lives in `ResearchLab`, not here — this contract is the spec, the code is the
instrument:

- `research_algorithms/learning_to_rank_cross_sectional/src/ltr_cross_sectional/evaluation/promotion.py`
  — `promote()`, `pbo_cscv()`, `reality_check()`, `block_bootstrap_sharpe_ci()`,
  `benjamini_hochberg()`, `bonferroni()`, `expected_max_sharpe()`. numpy/pandas
  only; normal CDF via erfc, inverse-CDF via Acklam (no scipy).
- `scripts/promotion_report.py --glob '<outputs glob>' [--ppy 252]` — loads each
  cell's `pnl.csv`, treats the glob as the family m, writes `reports/promotion_*.json`.

> Memory citations are point-in-time; verify these paths exist in ResearchLab
> before asserting. See [[ltr-promotion-gate]].

## Known reference verdicts (sanity anchors)

- Curated post-2008 family (m=35): best ~1.0–1.15 Sharpe but **0/35 CONFIRMED**,
  all CAPPED (DSR ~0.89–0.94), family PBO 0.63.
- Broad 1800-name real cells: negative Sharpe, DSR≈0, **0/7 CONFIRMED**, PBO 0.75.
- Linear-H63 ladder: the **first CONFIRMED** cells (see [[ltr-broad-linear-edge]]).

If a fresh run contradicts these anchors without a code change to explain it,
suspect a regression in the gate before believing the new headline.

## Recording a verdict

Use [`/gate-check`](../commands/gate-check.md): it runs (or ingests) the gate
output, prints the four-bar table, and appends/updates the structured row in
[`registry/levers.yaml`](../registry/levers.yaml) + the human mirror
[`research_ledger.md`](../research_ledger.md). A verdict without a backing
artifact (`promotion_*.json`, `pnl.csv`) is unsupported — `/evidence` will flag it.
