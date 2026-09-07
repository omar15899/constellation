---
name: quant-loop
description: Execute or audit quantitative research with data provenance, causal timing, historical universes, realistic costs and honest baseline comparisons before promotion.
---

# /quant-loop <research task or result>

Use this when a quantitative conclusion depends on data construction, a
backtest or inference. It adds research validity checks to
[verify-loop](verify-loop.md). Read the target repository's contract, the
[lever registry](../registry/levers.yaml) and the
[promotion contract](../contracts/promotion_gate.md) before running an experiment.
Reuse existing evidence for closed levers; do not rerun a DO-NOT-RE-RUN lever or
reopen it by renaming the experiment.

## Define the experiment before interpreting the result

Establish the hypothesis, incumbent baseline, intended universe, horizon,
evaluation period and success criterion. Identify every trial that belongs to
the search, including failed or discarded variants. A change in the universe,
selection criterion or methodology changes the experiment; do not silently
substitute one that makes the result look better.

Trace the result through producing code/configuration, input dataset and
version or manifest, and persisted output artifact. Record enough context in
the research output to reproduce the result, including units, sample size,
frequency and annualisation convention. Printed metrics alone do not establish
durable research evidence. Check stale outputs and silent fallbacks with
[debug-metric](debug-metric.md) when a value cannot be explained.

## Test the validity assumptions that carry the claim

- **Causal timing:** distinguish observation time, availability time, decision
  time and execution time. Check feature/label indices, return attribution and
  chronological train/test separation, including overlapping labels and any
  preprocessing fitted on future observations.
- **Historical population:** examine point-in-time universe construction,
  delistings, missing coverage and selection filters. Never filter a historical
  broad universe by current tradability without explicitly labeling the result
  survivorship-biased.
- **Economic implementation:** check positions, exposure, cash and constraints;
  include applicable fees, slippage, spread, borrow and turnover. Evaluate
  sensitivity to assumptions that could erase the result.
- **Comparison and inference:** compare the same dates, universe and cost basis
  against the incumbent. Separate alpha from market/factor exposure, and
  risk reduction from incremental return. Check sample size, dependence,
  uncertainty and multiplicity before treating a winner as evidence.

Choose diagnostics that can falsify the actual claim. Explain a material
assumption that cannot be checked and limit the conclusion accordingly; an
unchecked assumption is not a passed test. Do not run every diagnostic for a
task whose scope does not support or require it.

## Label and preserve the result

Associate each headline with its run class and actual construction:

- `deployable`: current tradable universe and its stated constraints;
- `broad-floor`: historical-universe comparison designed to avoid survivorship
  selection; the label alone proves neither unbiasedness nor a mathematical
  lower bound;
- `diagnostic`: exploratory evidence, with limits carried into the conclusion;
- `production`: the committed result, with operational and engine provenance.

Keep current-universe and historical-universe results separate. Preserve the
artifact and update the report or experiment record required by the task.
When a verdict is requested, use [gate-check](gate-check.md) to assess the full
family and record it through the validated writer. Deployable or production
CONFIRMED results additionally need audited BacktestLab evidence for the same
experiment. A statistical pass alone does not establish deployability or
improvement over the incumbent.
