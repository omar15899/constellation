---
name: pde-results-review
description: Interpret existing Sweeplab run evidence, compare numerical methods and prepare requested scientific reports with traceable parameters, applicable invariants and explicit limits.
---
# Sweeplab run analysis

Use the [Sweeplab profile](../../../profiles/sweeplab.md) and the current run-store/report contracts in `/Users/omarkhalil/GitHub/Sweeplab`. Analyze the run named by the user or established by the task. A recent timestamp alone does not identify the intended run.

## Establish the evidence

Read the authoritative run metadata, resolved configuration, available metrics and relevant artifacts. Distinguish requested, inferred and default parameters, with their provenance. Preserve the run ID, code revision, dirty-code limitations, environment and success/partial/failure status. Missing measurements stay missing; a configuration hash is not evidence that an experiment completed.

Inspect figures when the interpretation depends on them. Check axes, units, normalization, resolution and whether each image belongs to the selected run. Keep raw outputs intact; use captured results without silently rerunning the solver, changing parameters or modifying solver code.

Compute or inspect only the derived quantities relevant to the question: errors against justified references, refinement ratios and observed orders, residual/iteration histories, constraint violations and measured cost. Apply option-pricing invariants only under the model's hypotheses. Distinguish a diagnostic discrepancy from a demonstrated implementation defect.

## Choose the deliverable

Answer in conversation when interpretation is all that was requested. For an authorized report, read [the reporting reference](references/report-structure.md). Scale the report to its scientific claim; do not impose a fixed line count, compulsory empty sections or an automatic permanent record for every execution.

Use the existing run's `reports/` directory through `labs._shared.reports.write_run_report` when a `RunPaths` is available. Cross-run reports use `labs._shared.reports.write_report` and the owner's lab/report layout. Follow the current run store instead of fabricating a timestamped run directory. Keep figures with the report and refer to original data rather than copying raw logs into a publication.

If the scoped change includes a report indexed by the project, refresh `outputs/_general/reports_index.md` with `labs._shared.build_reports_index`; do not maintain a second index by hand. Declare the report, assets and index as exact task paths before changing them. Existing reports and run records retain their ownership.

## Review and handoff

State what the evidence establishes, the regime it covers, contradictory observations, missing instrumentation and the next justified decision. Link relevant known issues without inventing findings. Use curated problem and execution summaries; do not embed conversation transcripts, verbatim prompts or private logs in a report by default.

Publication and independent review use Constellation. This method performs no automatic staging, commit, push or post-commit documentation loop. Create, change or run tests only when Omar explicitly requests them; leave any test-dependent acceptance gate unmet until that evidence is authorized and available.
