# Scientific run reports

This reference supplements `pde-results-review` when a report is requested. Use the sections that support the actual claim; unavailable studies are limitations, not invitations to manufacture evidence.

## Identity and provenance

Identify the question, selected run(s), status, code revision and model regime. Record parameters with units and distinguish explicit choices, defaults and inferences. Cite the authoritative configuration and input artifacts. A clean hash, a dirty worktree, an interrupted run and a reconstructed analysis are different evidence states.

Keep a compact artifact map: source data, derived metrics, figures and the final report. Record absent timing, missing fields, partial outputs and inaccessible references. Summarize the objective in your own words; preserve private prompts and raw logs outside publication.

## Mathematical and numerical specification

State the equation or variational problem, domain, initial/boundary data, function spaces, constraints and assumptions. Separate the continuous model, regularization, discretization and numerical solution. Include weak-form or theorem detail when it supports a conclusion, and state the theorem's hypotheses.

Specify the actual mesh, temporal grid, SDC quadrature/sweeps, constraint method, nonlinear/linear solvers, tolerances and termination status from the run. Record dividend/event treatment and any frozen-policy or active-set approximation. A nominal method or requested tolerance is not achieved accuracy.

## Quantities and comparisons

- Report absolute errors and justified norms. Relative error is undefined at a zero reference and unstable near zero; provide a meaningful scale or absolute error instead.
- For two comparable refinements, an observed order is `log(e_coarse/e_fine) / log(step_coarse/step_fine)`. It requires positive errors and distinct positive step sizes, with other error sources controlled. State the reference and refinement ratio; roundoff or a vanishing reference can invalidate the estimate.
- Separate spatial, temporal, regularization, truncation and reference errors. SDC order is limited by the method, quadrature, regularity and convergence of correction/constraint solves; a sweep count alone is not a universal order claim.
- Compare methods on the same problem, units and accuracy basis. Distinguish theoretical order, fitted order and a pre-asymptotic trend. Explain fit ranges and uncertainty when reporting a slope.
- Summarize residuals, iteration counts, stopping reasons and constraint violations. The sign and norm of a violation must match the stated feasible set.
- Report efficiency only from recorded measurements. Speedup requires comparable serial/parallel work, hardware and accuracy; hashes and successful MPI launch do not establish scaling.

## Pricing-specific analysis, when applicable

Use the selected contract, exercise style, rates/carry and dividend model. Report early-exercise premium, relevant Greeks and free-boundary behavior only when corresponding data exists. Distinguish continuation/stopping regions, event times and smooth regimes from nonsmooth boundaries.

State the assumptions behind each invariant. American-call/european-call equality needs the applicable no-early-exercise hypotheses; it is not a general dividend-paying-call invariant. Bounds, monotonicity, convexity and Greek signs likewise depend on the product and regime. A tree or closed-form reference has its own truncation/discretization assumptions.

Use the PDE's declared time variable and sign convention when checking theta or other identities; do not replace signed quantities with absolute values to force agreement. FE derivatives must come from the FE representation, not differences of arbitrarily ordered DOFs. Label smoothing and frozen-active-set sensitivities as derived approximations, including their limits.

## Presentation and conclusion

Use tables for parameters, comparisons, error/refinement data and applicable invariant verdicts. Give figures readable units, axes and source-run identity. Explain what each relevant figure shows, what supports the conclusion and what remains ambiguous; fixed sentence quotas add no evidence.

Conclude with the supported result, its parameter/domain scope, unresolved failures and a justified next step. Distinguish an observed pass, a mathematical proof, a plausible explanation and a recommendation. A failed or partial run can still yield a useful report.

## Owner paths and publication

Per-run reports belong at the current `RunPaths.reports_dir`; use `labs._shared.reports.write_run_report`. Cross-run reports follow `labs._shared.reports.write_report`. Preserve original metadata and use the run store for any separately authorized run creation; never reconstruct a run identity from the current clock.

Use `labs._shared.build_reports_index` for the existing global report index when the task covers that index. `docs/known_issues.md`, `docs/numerical_validation.md` and `docs/american_option_methods.md` are owner documents: update them only when the scoped finding changes their claims. Keep each modification with its evidence and independent review in the same Constellation task.

Tests and new numerical experiments require explicit authorization. Missing required evidence remains an unmet gate; publication does not turn an untested conclusion into a verified result.
