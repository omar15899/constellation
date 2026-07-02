# Research Ledger

Human-readable mirror of [`registry/levers.yaml`](registry/levers.yaml) — the
persistent record of **which research hypotheses ("levers") have been tested and
what the verdict was**, so no session ever re-runs a dead lever.

This is distinct from [`loop_ledger.md`](loop_ledger.md): the loop ledger records
*how a session executed* (Plan→Execute→Verify per task); this ledger records
*what we learned about the research question* (one row per falsifiable
hypothesis, surviving across sessions).

The bar a lever must clear to be CONFIRMED is
[`contracts/promotion_gate.md`](contracts/promotion_gate.md). Record verdicts with
`/gate-check`, which writes the structured row into `levers.yaml`. This file is
the readable view.

## Verdict vocabulary

| verdict          | meaning                                                                 |
| ---------------- | ----------------------------------------------------------------------- |
| `OPEN`           | hypothesis stated, not yet tested to a verdict                          |
| `CONFIRMED`      | passes the promotion gate — a real, deployable-or-floor edge            |
| `CAPPED`         | real but bounded (e.g. de-risks but does not raise Sharpe)              |
| `NO_IMPROVEMENT` | adds nothing beyond the incumbent baseline                              |
| `REFUTED`        | fails the gate / negative / overfit (high PBO) — **do not re-run**      |
| `HOLD`           | inconclusive or blocked on data; parked, not closed                     |

## Run-class discipline (always tag the headline)

- **deployable** — what is tradable now (current-universe headline).
- **broad-floor** — survivorship-honest unbiased lower bound.
- **diagnostic** — exploratory, not a claim.
- **production** — the committed result.

Never filter a historical broad universe by *current* tradability unless the
number is explicitly labelled survivorship-biased.

## Current state (mirror of `levers.yaml`, 2026-06-23)

**The alpha search is CLOSED. The open work is VALIDITY, not alpha.**

### CONFIRMED
- `broad-linear-ridge-h63` — ENGINE LABEL 2026-07-01: vectorised-engine evidence only pending a BacktestLab reconciliation PASS (single-backtester decision). Verdict unchanged: broad edge IS recoverable with a LINEAR ridge at H63 (gate 4/7 CONFIRMED, survives mod+harsh borrow 4/4); the GBM overfits it.. *broad-floor.*
- `multisleeve-hrp-book` — KERNEL RE-VALIDATION 2026-07-02: BacktestLab-reconciled — audited causal kernel reproduced the frozen book (reconciliation PASS, dSharpe=0.0007 at tol 0.05, daily corr 0.9999972, audit_root c21f2964..., reports/hrp_kernel_reconciliation_2026-07-02.json); prior vectorised-evidence-only label superseded. Verdict unchanged: HRP book over the two uncorrelated edges (corr -0.07) -> net Sharpe 1.45 OOS; alignment re-audit 2026-06-28 SURVIVES (native 1.446 == same-day 1.449); borrow-robust 2026-07-01 (1.293 harsh, boot-CI low +0.63). Caveats stand: does NOT statistically beat deployed v1.0 (bootstrap CI straddles 0); curatedgbm overlaps v1.0 +0.42 — CONFIRMED is real-vs-zero, not beats-the-live-book.. *production.*
- `t212-score-weighting` — KERNEL RECONCILIATION 2026-07-02: long-only v1 (top-20 score-weighted cap15, H63 quarterly) BacktestLab-reconciled — PASS (coverage 1.0, corr 0.9993, dSharpe 0.0014: 1.3591 kernel vs 1.3605 vectorised, audit_root 2a405b5b…); production-mode deployability battery PASS + target book (root 47fbeb42…); gate re-run ON KERNEL PnL CONFIRMED (DSR 0.99997, BH-FDR 0.0008 at m=24, boot-CI [0.70, 2.06]). Kernel-confirmed ladder monotone in score (top10 1.43 > top20 1.36 > … > EW 1.00 > bottom20 0.70): the long-only top-leg edge is real, no short leg ever involved. Stress all PASS (tx x5 → 1.15, +1bar → 1.36); droptop5 1.05. Caveats: curated-universe-conditional (broad floor 0.27 p=0.45), beta ~1.1, semis concentration. Full audit: ResearchLab reports/t212_longonly_kernel_audit.md. Prior vectorised-only label superseded. *deployable.*

### CAPPED / NO_IMPROVEMENT
- `multi-asset-diversifiers` (Track 2) — CAPPED: decorrelation real (0.23–0.51) but risk-reduction only.
- `long-only-equity-sleeves` (Track 1) — NO_IMPROVEMENT: shared market beta (corr ≥0.57).
- `ml-sleeve-zoo` (Track 3) — NO_IMPROVEMENT: ML adds nothing beyond the v1.0 GBM.

### REFUTED — dead levers, DO NOT re-run
- `gdelt-news-tone` — tone/volume: no cross-sectional IC.
- `edgar-fundamentals` — IC+ but Sharpe−, gate-refuted under linear AND LightGBM → data ceiling.
- `gdelt-cameo-events` — one overfit broad-H21 cell (PBO 0.93). Third and last external data lever; the broad ceiling holds against all three.
- `t212-universe-zoo` (Track 4) — HOLD/NEGATIVE; high-Sharpe cells are cash artifacts. DO NOT re-run the zoo.

### OPEN — the real next steps (validity)
- `headline-audit` — Validity closed favourable: audited causal kernel corroborates the deployable economics. Fresh engine=both on the FIXED kernel (BacktestLab a46c3fb): total return +113.55% vectorised == +113.50% audited, maxDD -11.3% vs -11.7%; the 9-11x Sharpe divergence was BacktestLab per-event annualisation (fixed; per-tick 0.708 vs 0.884, same order, residual delta catalogued in the unification plan).. *deployable.*
- `short-leg-cost` — Validity closed favourable: L/S edges survive realistic borrow. Broad 4/4 CONFIRMED under mod+harsh (2026-06-19); curated GBM 1.088->1.055(mod)->1.022(harsh), drag 25-50bps/yr; HRP book recombined 1.401->1.347->1.293 with boot-CI low +0.63 (2026-07-01).. *deployable.*

---

## Template — copy when recording a new lever

```
### <id> — <verdict>
- **Hypothesis:** <one falsifiable sentence: "adding X improves metric Y of strategy Z">
- **Strategy / repo:** <strategy-id> / <repo>
- **Run class:** deployable | broad-floor | diagnostic | production
- **Result:** <headline metric, units, tagged by run class>
- **Gate:** <which gate, pass fraction, PBO/DSR/reality-check if applicable>
- **Evidence:** <artifact/report path, or memory:slug>
- **Verdict + why:** <CONFIRMED/REFUTED/...> because <reason>
- **Re-run?** <false = closed | true = open; what new data/method would reopen it>
```

Then mirror the same fields as a structured row in `registry/levers.yaml`
(prefer `/gate-check`, which does both).
