---
name: debug-metric
description: Trace an unexplained, missing or implausible metric from the reported value through its artifact, calculation and inputs; identify the first divergence and verify the correction.
---

# /debug-metric <metric, artifact or symptom>

Use this for NaN/null/empty values, unexplained discrepancies or implausible
metrics. Establish the reported value, expected meaning, units, sample and run
identity before changing the calculation. A legitimate zero or undefined value
is not automatically a defect.

Trace both directions: from the reported number to its persisted artifact and
producing function, then from the inputs through transformations to the output.
Find the first point where observed behavior diverges from the intended metric.

Inspect the likely causes:

- stale files, wrong run/configuration, caches or reports using another column;
- empty data, missing coverage, duplicates, zero denominators or non-finite values;
- joins, date indices, off-by-one returns, resampling and availability timing;
- units, percentage scaling, frequency and annualisation;
- swallowed exceptions, defaults, forward filling or previous-run fallbacks;
- leakage, survivorship selection, exposure or cost assumptions behind a result
  that is numerically correct but economically misleading.

Use the smallest diagnostic that separates plausible causes: inspect a boundary
row, trace one instrument, or recompute a small case independently. Do not rerun
a full sweep to diagnose an aggregation bug, and respect closed research levers
in the [registry](../registry/levers.yaml).

If repair is authorized, correct the cause, verify a representative case and
regenerate affected outputs as the task permits. Confirm that the report now
reads the corrected artifact. If the cause is missing data or an undefined
statistic, preserve that information and state the limitation; do not replace
it with a plausible placeholder or widen a fallback to hide the failure.

Report the cause or remaining hypotheses, the check that distinguishes them,
the correction and its effect on the conclusion. Use a trace table only when
multiple stages need comparison. For broader research validity continue with
[quant-loop](quant-loop.md); verify the final claim with
[verify-loop](verify-loop.md).
