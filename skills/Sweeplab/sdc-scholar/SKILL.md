---
name: sdc-scholar
description: Generate a complete, thesis-quality research report for any SweepLab run. Covers mathematical framework, price surfaces, Greeks, Gamma diagnostics, free boundary, EEP, epsilon convergence, method comparison, dividend stress test, spatial/temporal convergence, and 10-point invariant verification. Written in formal academic prose with inline LaTeX, tables as primary data vehicle, every figure embedded with analytical commentary. Writes final_document_YYYY-MM-DD_<type>.md + assets/ into the run directory (outputs/<experiment>/<run>/), which are the only committed artifacts. Use whenever a run deserves a permanent record: after any deep run, after a convergence study, after a method comparison, or when the user says "escribe el informe", "generate the report", "documento completo", "informe del run", "haz el scholar", or "write the discussion". Outputs a committed markdown report, auto-pushed. Also supersedes the old results-report command.
---

# SweepLab Scholar

Generate a permanent research document for a SweepLab run. The output must match the quality and structure of the existing gold-standard corpus — specifically the `american_iv_research_2026-04-11` discussion (740 lines, 15 sections) and the `american_put_analysis` (459 lines, 9 sections + appendix). Read those documents before writing anything.

---

## Step 0 — Read the calibration corpus first

Before reading any run data, read these two reference documents in full:

```bash
# Read the calibration anchors from the outputs directory
find outputs/ -name "final_document_*.md" | sort | tail -5
# Read the most relevant existing reports for style calibration
```

These are the calibration anchors. Every structural, stylistic, and depth decision you make should be checked against them. Note specifically:
- How the Introduction leads with a bullet list of quantitative results
- How the Mathematical Framework section is written (full weak form, named theorems, proofs)
- How figures are embedded and described (minimum 4 sentences per figure)
- How tables are used as the primary data vehicle (parameters, Greeks, convergence, invariants)
- How the Conclusions section gives practical recommendations, not summaries

---

## Step 1 — Locate the run

If called with a path or run_id, use it. Otherwise find the most recent run:
```bash
find outputs/ -name "meta.json" | sort | tail -5
find outputs/ -name "greeks*.json" | sort | tail -5
```

Read `meta.json` from the run directory. Extract: problem, method, parameters, key_results, git_hash, timestamp.

---

## Step 2 — Read everything

**Run directory:**
```bash
cat <run_dir>/meta.json
ls <run_dir>/raw/
ls <run_dir>/analysis/
ls <run_dir>/assets/
```

**Data files:**
```bash
find <run_dir> -name "*.json" | sort
find <run_dir> -name "*.txt" | sort
```
Read every JSON and TXT. Extract all numbers at full precision — four significant figures minimum when reporting.

**Every figure:**
Use the Read tool on every PNG in `analysis/` and `assets/`. For each image, record internally before writing:
1. What each panel shows (axes, what is plotted, log or linear scale)
2. Key visual features: curve shapes, peaks, kinks, plateaus, transitions
3. Consistency with theory: does the visual confirm equations?
4. What the plot reveals that numbers alone do not
5. Any anomalies or unexpected features

**Known issues cross-reference:**
```bash
cat docs/known_issues.md
```

---

## Step 3 — Compute derived quantities

Compute with full precision before writing a single line of prose:

**BS theta identity** (at S₀=K, for each option type):
```
½ × σ² × S₀² × Γ + b × S₀ × Δ − r × V  =?=  |Θ|
```
Report absolute and relative discrepancy.

**Early exercise premium:** EEP = V_Am − V_Eu, as absolute value and fraction of V_Eu.

**Convergence orders** (if multiple resolutions present):
```
EOC_temporal = log(e₁/e₂) / log(dt₁/dt₂)
EOC_spatial  = log(e₁/e₂) / log(h₁/h₂)
EOC_epsilon  = log(e₁/e₂) / log(ε₁/ε₂)
```

**SDC order:** K sweeps → O(Δt^{K+1}) theoretical. Measure against actual errors.

---

## Step 4 — Write the report

Write the report as `final_document_YYYY-MM-DD_<type>.md` directly in the run directory (`outputs/<experiment>/YYYY-MM-DD_HH-MM-SS[_tag]/`). Figures for the report go in `assets/` in the same run directory.

**Target length:** 450–750 lines. The `american_iv_research` discussion (740 lines, 15 sections) is the upper bound for a complete study; the `american_put_analysis` (459 lines, 9 sections) is the lower bound for a focused run. Do not exceed 800 lines — depth comes from precision, not length.

**Header block** (mandatory, verbatim structure):
```markdown
# <Problem Name>: Full Analysis Report
## Run `<run_id>`

**Grid:** <n_elem>, dt=<dt>, M=<M> Radau-right nodes, K=<K> SDC sweeps
**Parameters:** S₀=<S0>, K=<K_strike>, σ=<sigma>, r=<r>, T=<T> yr, b=<b>
**Solver:** PETSc SNES `<snes_type>` (<description>)
**Git:** `<hash>` — <ISO timestamp>
```

**Section sequence** — adapt by including only sections for which run data exists, but never thin a section that exists:

| § | Title | Always include? |
|---|-------|----------------|
| 1 | Introduction | YES |
| 2 | Mathematical Framework | YES |
| 3 | Numerical Setup | YES |
| 4 | Price Surfaces and Time Evolution | if price surface plot exists |
| 5 | Early Exercise Premium | if EEP data exists |
| 6 | Greeks Surfaces: Δ, Γ, Θ | if Greeks plots exist |
| 7 | Gamma Diagnostics and Free Boundary | if Gamma diagnostics plot exists |
| 8 | Merton's Theorem / Call Free Boundary | if call data exists |
| 9 | Vega and Rho | if Vega/Rho plots exist |
| 10 | Greeks at S₀: Full Numerical Report | YES if Greeks data exists |
| 11 | Epsilon Convergence | if epsilon study was run |
| 12 | Method Comparison | if method comparison was run |
| 13 | Dividend Stress Test | if dividend study was run |
| 14 | Convergence Analysis | if convergence study was run |
| 15 | Numerical Invariant Verification | YES |
| 16 | Conclusions and Outlook | YES |

Canonical write location is the run directory's `reports/` subdir:
`outputs/runs/<lab>/<exp_id>/<run_id>/reports/final_document_YYYY-MM-DD_<type>.md`.
Prefer the typed helper `labs._shared.reports.write_run_report(paths, name, body)`
when a `RunPaths` is in hand; it resolves `paths.reports_dir` for you. Lab-level
(cross-run) reports go to `labs/<lab>/reports/` via
`labs._shared.reports.write_report(lab_id, exp_id, name, body)`.

See `references/report-structure.md` for the required content of each section.

**Non-negotiable quality requirements:**

1. **Introduction leads with bullet numbers.** The very first paragraph ends with a bulleted list of the central quantitative results — all numbers at four significant figures. A reader who only reads §1 knows the full scope.

2. **Tables are the primary data vehicle.** Use tables for: parameter specifications, Greeks values, convergence tables (h/dt | error | EOC), invariant checklist, method comparison. Prose interprets tables; it does not repeat them.

3. **Every figure inline with 4-sentence minimum analysis.** `![Fig N: caption](path/fig.png)` immediately followed by: (a) what axes and panels show, (b) key visual features and their geometric character, (c) what they confirm about physics/numerics, (d) any noteworthy subtlety. Do not write "as shown above" — state the observation and why it matters.

4. **Named theorems.** "By the Lions–Stampacchia theorem..." not "It can be shown that..." Cite Jaillet–Lamberton–Lapeyre (1990) for O(ε) penalty convergence. Cite Merton (1973) for no-early-exercise theorem.

5. **Physical interpretation after every mathematical claim.** One sentence: what does this mean for a trader or for the solver?

6. **Solver configuration exact.** Git hash, SNES type, rtol, atol, max_it, preconditioner — exact values from the run data, not paraphrased.

7. **No bulleted summaries in analytical sections.** Prose paragraphs that build on each other. Each paragraph opens with a claim, develops it, closes with a forward connection to the next paragraph.

---

## Step 4.5 — Register the report in the global index

After the report file lands in its `reports/` dir, refresh the global index so
the report is discoverable from one place. The index is owned by
`labs._shared.reports.update_global_index`; the scanner that backfills it from
the on-disk corpus is `labs._shared.build_reports_index`. Just run it — it
rescans every `final_document_*.md` / `thesis_*.md` under
`outputs/runs/**/reports/` and `labs/*/reports/` and rewrites
`outputs/_general/reports_index.md` deterministically (no hand-editing the
table):

```bash
python -m labs._shared.build_reports_index
```

Stage the regenerated index alongside the report in Step 5.

---

## Step 5 — Commit the report and assets

Only the `final_document_*.md`, `assets/`, and the refreshed global index are
committed (the rest of the run dir is gitignored).

```bash
git add outputs/runs/<lab>/<exp_id>/<run_id>/reports/final_document_YYYY-MM-DD_<type>.md
git add outputs/runs/<lab>/<exp_id>/<run_id>/reports/assets/
git add outputs/_general/reports_index.md
git commit -m "scholar: <type> — <one-line finding>

What:
  outputs/<experiment>/<run>/final_document_YYYY-MM-DD_<type>.md — <N>-line analysis report.
  Covers: <list key sections>.

Why:
  Permanent record of run <run_id> at git <hash>.

Evidence:
  Put: <price> (CRR <ref>, err <err>). Call: <price>. All invariants pass."
```

---

## Scope

Read and write one report. Do not re-run experiments, modify solver code, or change parameters.
