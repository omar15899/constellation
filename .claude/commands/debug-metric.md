---
name: debug-metric
description: Diagnose a suspicious, NaN, null, empty, or implausible metric by tracing it from the producing code through the input data to the output artifact — before trusting or reporting it.
---

# /debug-metric <metric / problem>

A metric is suspect (NaN, null, empty, zero, implausibly high Sharpe, etc.).
Trace it end to end before trusting or reporting it. Do **not** paper over it
with a fallback.

**Trace, in order:**

1. **Producing code** — locate the exact function/line that computes it.
2. **Inputs** — what data feeds it; is the dataframe empty, mis-indexed, or all
   NaN before the metric is computed?
3. **Shape & coverage** — sample size, date range, number of names; is the
   denominator zero?
4. **Alignment** — are features and labels aligned in time; any off-by-one?
5. **Silent fallback** — does the code swallow an exception and return a
   default / previous value?
6. **Artifact** — does the on-disk `metrics.json` / `.csv` match the reported
   number, or is the report stale?
7. **Plausibility** — is the value too good (lookahead, survivorship) or too
   bad (broken merge, wrong frequency)?

**Output:**

| symptom | suspected cause | check run | finding | fix / status |
|---|---|---|---|---|

If the root cause is a real data limitation, **state it** — do not substitute a
placeholder value. A NaN that means "no data" is information, not a bug to hide.
