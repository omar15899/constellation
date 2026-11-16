---
name: pde-results-review
description: Analyse SweepLab solver output and transform it into structured knowledge — compute errors, convergence orders, iteration statistics, and write a complete summary report with manifest and next-step recommendations. Use this skill whenever a run has completed and there is output to interpret, when the user asks about convergence, accuracy, or what the results mean, or when /analyze is invoked. Trigger even if the user just pastes raw output or says "what happened here".
---

# PDE Results Review

Take raw solver output and transform it into structured, committed knowledge. This is an analysis skill — it never re-runs experiments or modifies solver code.

## Step 1: Locate and read output

```bash
# Find metrics and checkpoint files
find <output_path> -name "*.json" | head -20
find <output_path> -name "*.h5" | head -10
```

Read every JSON metrics file found. If the output was passed inline as stdout text, parse it directly from the conversation.

## Step 2: Extract key metrics

From the output, extract:
- Solution values at reference points
- SNES iteration counts per time step
- Residual history (if logged)
- Wall time per step and total
- Constraint violations — `max(g − u)` for VI problems

## Step 3: Compute derived quantities

**Error analysis:**
- Absolute error: `|u_computed − u_reference|`
- Relative error: `|u_computed − u_reference| / |u_reference|`
- L2 and L∞ norms if solution field is available

**Convergence orders** (when multiple resolutions present):
```
order_temporal = log(e₁ / e₂) / log(dt₁ / dt₂)
order_spatial  = log(e₁ / e₂) / log(h₁  / h₂)
```

**Efficiency:**
- Cost per digit: `wall_time / (−log₁₀(error))`
- Iterations per step: mean, max, std
- Parallel speedup if serial + parallel data both present

## Step 4: Write the summary report

Write to `outputs/<experiment>/<run>/analysis/summary.md` (gitignored intermediate artifact).
If a permanent report is needed, write `outputs/<experiment>/<run>/final_document_YYYY-MM-DD_<type>.md` instead.

```markdown
# Run Summary: [Problem Name]

## Problem
- PDE: [description]
- Method: [VI / penalty / projection]
- Key parameters: [dt, mesh size, sweeps, lambda, etc.]

## Results

### Solution at Reference Points
| Point | Computed | Reference | Relative Error |
|-------|----------|-----------|----------------|

### Convergence Table
| dt (or h) | Error | Order |
|-----------|-------|-------|

### Iteration Statistics
| Metric | Value |
|--------|-------|
| Mean SNES iterations/step | |
| Max SNES iterations/step  | |
| Total wall time           | |
| Time per step             | |

### Constraint Satisfaction
| Metric | Value |
|--------|-------|
| Max violation             | |
| Active set size (% DOFs)  | |

## Comparison with Reference
- CRR (N=2000): [value], relative error = [value]
- Analytical (if available): [value], relative error = [value]

## Numerical Invariant Check
1. American call = European call: [PASS/FAIL] (error = ...)
2. American put > European put: [PASS/FAIL] (premium = ...)
3. Delta signs correct: [PASS/FAIL]
4. Gamma > 0: [PASS/FAIL]
5. Put monotonicity: [PASS/FAIL]
6. CRR consistency: [PASS/FAIL] (error = ...)
7. SDC convergence order: [PASS/FAIL] (measured = ..., expected = ...)

## Diagnosis

### What Went Well
### Issues Found
### Next Steps
```

## Step 5: Write metrics to analysis/

Write metrics to `outputs/<experiment>/<run>/analysis/metrics.json` (gitignored).
RunContext already writes `meta.json` to the run directory with run metadata.

## Step 6: Diagnostic plots (if matplotlib available)

```bash
source /Users/omarkhalil/Documents/Universidad/ImperialCollege/Project/programming/venv-firedrake/bin/activate
python -c "import matplotlib; print('ok')"
```

If available, generate (100 DPI, <150 KB each, save to output directory):
- Error vs dt (log-log) for convergence studies
- Solution profile at final time
- Iteration count vs time step
- Constraint violation vs time

## Interpretation guide

| Observation | Likely cause | Action |
|-------------|-------------|--------|
| Order 0.5 below expected | Pre-asymptotic | Try finer resolution |
| Order 1.0+ below expected | Bug | Flag immediately |
| SNES iterations > 500 | dt too large for VI | Reduce dt |
| Constraint violation > 1e-6 | Lambda too small or bounds broken | Check VI setup |
| Wall time > 10 min (standard profile) | Efficiency concern | Flag |
| American call ≠ European call by > 1e-4 | Constraint bug | Critical — investigate |

## Output locations

All output lives inside `solver/outputs/<experiment>/YYYY-MM-DD_HH-MM-SS[_tag]/`:
- `raw/` — solver checkpoints (.h5, .pvd, .vtu, .xdmf) — gitignored
- `analysis/` — intermediate plots, CSVs, summary.md, metrics.json — gitignored
- `final_document_YYYY-MM-DD_<type>.md` — committed synthesis report (only if warranted)
- `assets/` — figures for the committed report

## Scope

Analysis only. Do not modify solver source, re-run experiments, or change parameters (that is `parameter-strategist`).
