# Promotion-Gate Contract

*Constellation plane. The standing statistical bar a research result must clear
before it may be called CONFIRMED, and the vocabulary every verdict uses. This is
the methodology Omar has already paid to discover — encoded so it is not
re-derived or quietly relaxed each session. Planning decision: the bar is the
user's; no model or executor may lower it to make a result pass.*

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

Vectorised-engine-only evidence caps the verdict at **HOLD**. Enforcement is
layered and fail-closed (hardened 2026-07-02):

- **ResearchLab gate** — `LTR_GATE_AUDIT` defaults to `enforce`; outputs
  stamped `engine_class: diagnostic` are categorically unaudited.
- **Registry writer** — `record_lever_verdict.py` refuses such a CONFIRMED in
  **every** mode (not just strict). A reconciliation artifact must
  self-identify as BacktestLab (`engine: "BacktestLab"` or an audit root);
  a bare `{"status": "PASS"}` is not provenance.
- **Registry schema** — levers carry a structured `engine:` field
  (`backtestlab | vectorized | vectorized-legacy | n/a`).
  `validate_levers.py` hard-fails any CONFIRMED deployable/production row
  without `engine: backtestlab` (+ 64-hex `audit_root` or `reconciliation`
  pointer). `vectorized-legacy` grandfathers only rows dated ≤ 2026-07-01:
  historical facts stay recorded, promotion-frozen pending reconciliation —
  a NEW row cannot claim it.
- **Tests** — `.claude/tests/test_promotion_enforcement.py` proves each
  refusal path (run it before trusting an edit to any of the above).

The vectorised engine remains legitimate for diagnostics, exploration and
candidate generation only.

## The multiple-testing denominator m (non-negotiable)

**The family you tried IS the denominator.** Pass *every* cell swept through the
gate, not just the survivor. A cell CONFIRMED at m=5 is only **CAPPED** at m=35.
Silently shrinking m to make a cell pass is relaxing a planning decision — it is
forbidden. State m explicitly with every verdict.

The CLI's `--glob` selects the cells loaded into the report; it does **not**
define the trial denominator. `--n-trials-total` supplies that denominator;
without it, `_search_trial_count()` estimates it from local outputs and the
search registry. Verify that estimate against the actual search history. An
explicit value is not independently authenticated by the CLI.

An honest count alone is insufficient: retain the complete family's returns,
per-bar Sharpe dispersion and selection history. DSR, PBO and Reality Check
cannot recover omitted trials from a larger `m`. A report over a curated subset
must disclose its missing family evidence and cannot support a family-wide
CONFIRMED claim merely because its denominator was increased.

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
- `research_algorithms/learning_to_rank_cross_sectional/scripts/promotion_report.py`
  — run from that subproject with `--glob '<outputs glob>' [--ppy 252]
  [--n-trials-total M]`. Repeated globs select cells; the loader prefers
  `pnl_backtestlab.csv` and otherwise reads `pnl.csv`. The default output is
  `reports/promotion_report.json`; `--out` chooses another report path.
- `research_algorithms/learning_to_rank_cross_sectional/src/ltr_cross_sectional/promotion/report.py`
  — `build_promotion_report()` combines the four bars, PBO, Reality Check,
  robust objective and engine/run-class restrictions. Consume this complete
  report, not only the preliminary per-cell table.

The CLI's automatic count is the maximum of the number of output directories
containing `pnl.csv`, the combined nonempty-line counts of
`reports/research_search_registry.jsonl` and its `.bak`, and one. It then takes
at least the number of loaded candidates. This is a local estimate, not a
deduplicated catalogue of every experiment. The CLI derives return matrices and
Sharpe dispersion from the selected cells, so use the full relevant family and
document missing or unusable trials rather than assuming autodetection supplies
their statistical evidence. Direct `promote()` calls without `n_trials_total`
still fall back to the candidate count with a warning; that fallback does not
waive this contract.

The current CLI sorts candidates by annualised Sharpe and builds the complete
report only for that winner. It does not supply `costs`, `turnover` or
`factor_exposure`: cost sensitivity is unavailable (NaN), and the latter two
penalties contribute zero. This is a wiring limitation, not evidence of selection
on the fully specified robust objective. Supply and verify those inputs through
the existing report API when claiming that validation; do not treat missing
cost sensitivity or a default penalty as a measured zero.

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
