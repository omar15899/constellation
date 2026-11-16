---
name: pde-example-review
description: Generate a complete, permanent review package for any SweepLab example execution — capturing intent, routing decision, full parameter trace, execution trace, artifacts, numerical results, and improvement opportunities. Use this skill after any EXAMPLE-class execution completes (successful or failed). The orchestrator invokes this automatically; it can also be triggered directly with /example-review or whenever a user asks for a run to be documented or reviewed. Never skip this after an execution.
---

# PDE Example Review

Generate a first-class permanent record for a concrete SweepLab execution. This is called with an execution context block and produces a committed review package. The record must be complete, honest, and traceable.

Read `docs/known_issues.md` before writing — cross-reference any KI numbers triggered during the run.

## Invocation context

You receive some or all of these fields:

```
NL_REQUEST:       Exact natural-language request from the user
INTENT_CLASS:     EXAMPLE (always)
ROUTE:            Which workflow / case / pipeline was invoked
CASE_SCRIPT:      Path to the Python case script
PARAMETERS:       Dict of parameters used
STDOUT:           Captured stdout
STDERR:           Captured stderr / warnings
OUTPUT_DIR:       Path to output files
ARTIFACTS:        List of generated files
GIT_HASH:         Git hash at execution time
STATUS:           success | failure | partial
EXECUTION_NOTES:  Notes from the orchestrator
```

Work with what is present. Be explicit about what is missing.

## Step 1: Derive slug and timestamp

From `CASE_SCRIPT` or `ROUTE`, derive a stable lowercase hyphenated slug:
- `cases/bs_greeks_american.py` → `american-options-greeks`
- `cases/bs_greeks_european.py` → `european-options-greeks`
- heat equation case → `heat-equation-convergence`

Timestamp: current datetime `YYYY-MM-DD_HH-MM-SS`.

## Step 2: Locate or create run directory

The run directory should already exist at `outputs/<experiment>/YYYY-MM-DD_HH-MM-SS[_tag]/` (created by RunContext). If not, create it:
```bash
mkdir -p outputs/<experiment>/<timestamp>/assets
mkdir -p outputs/<experiment>/<timestamp>/raw
mkdir -p outputs/<experiment>/<timestamp>/analysis
```

## Step 3: Copy artifacts

- PNG/PDF figures for the committed report → `assets/`
- Intermediate plots/CSVs → `analysis/` (gitignored)
- stdout → `analysis/stdout.txt`, stderr → `analysis/stderr.txt` (gitignored)
- Files under `/tmp/` that will be lost: copy them now to `analysis/`

## Step 4: Read supporting context

```bash
cat <CASE_SCRIPT>
git log --oneline -5
find <OUTPUT_DIR> -type f 2>/dev/null | head -30
```

## Step 5: Read known issues

```bash
cat docs/known_issues.md
```

Flag any KI-XXX numbers relevant to this execution.

## Step 6: Write the review document

Write to `outputs/<experiment>/<run>/final_document_YYYY-MM-DD_example.md`. This is the committed report. All sections are mandatory — never reduce the structure.

```markdown
# Example Execution Review: <Human-readable title>

**Slug:** `<slug>`
**Execution ID:** `<slug>/<timestamp>`
**Date:** <YYYY-MM-DD HH:MM>
**Status:** ✅ Success | ⚠️ Partial | ❌ Failure
**Git hash:** `<hash>`

---

## 1. Natural-Language Request

> <verbatim NL_REQUEST>

### Interpreted Intent
<What the request means in project terms. What the user expected.>

### Assumptions Made
<Any non-trivial inference. If the request was ambiguous, state the resolution.>

---

## 2. Routing Decision

| Field | Value |
|-------|-------|
| Intent class | EXAMPLE |
| Entry point | <orchestrator phase or direct> |
| Case script | `<CASE_SCRIPT>` |
| Workflow selected | <pipeline or shortcut> |
| Reason for selection | <why this over alternatives> |
| Math-first applies | <yes/no> |

---

## 3. Execution Plan

<What the orchestrator planned. Which phases, agents, order.>

### Dependency Chain
<Sequence: which agent/command/script produced which artifact.>

---

## 4. Parameter Trace

### 4.1 Explicit Parameters (set by user)
| Parameter | Value | Set where |
|-----------|-------|-----------|

### 4.2 Inferred Parameters
| Parameter | Value | Inference rule |
|-----------|-------|----------------|

### 4.3 Default Parameters
| Parameter | Value | Source file:line |
|-----------|-------|-----------------|

### 4.4 Environment Settings
| Variable | Value | Effect |
|----------|-------|--------|
| FIREDRAKE_TSFC_KERNEL_CACHE_DIR | `$TMPDIR/tsfc_cache` | Redirects TSFC JIT cache |
| XDG_CACHE_HOME | `$TMPDIR/xdg_cache` | Redirects loopy cache |
| PYOP2_CACHE_DIR | `$TMPDIR/pyop2_cache` | Redirects pyop2 cache |

---

## 5. Step-by-Step Execution Trace

| Step | Action | Outcome | Notes |
|------|--------|---------|-------|

---

## 6. Artifacts Produced

| File | Type | Location | Description |
|------|------|----------|-------------|

---

## 7. Visual Evidence

<For each figure: embed as markdown image, 2–3 sentences of interpretation.>

![<alt>](assets/<filename>)
<What this shows and what it confirms.>

---

## 8. Key Numerical Results

| Quantity | Value | Reference | Rel. Error | Status |
|----------|-------|-----------|------------|--------|

---

## 9. Logs and Observability

### Warnings
<Non-fatal warnings. Are they benign?>

### Errors
<Errors encountered. Were they handled?>

### Known Limitations Triggered
<Cross-reference docs/known_issues.md KI-XXX numbers.>

### What Was NOT Captured
<Missing instrumentation — be explicit.>

---

## 10. Output Assessment

### What Worked
### What Failed or Was Partial
### What Is Brittle

---

## 11. Reproducibility

```bash
source /Users/omarkhalil/Documents/Universidad/ImperialCollege/Project/programming/venv-firedrake/bin/activate
cd /Users/omarkhalil/GitHub/Sweeplab
export PYOP2_CACHE_DIR="$TMPDIR/pyop2_cache"
export FIREDRAKE_TSFC_KERNEL_CACHE_DIR="$TMPDIR/tsfc_cache"
export XDG_CACHE_HOME="$TMPDIR/xdg_cache"
python <CASE_SCRIPT>
```

**Git hash:** `<hash>` (branch: `<branch>`)

---

## 12. Improvement Opportunities

### Orchestrator
### Case Script
### Observability
### Documentation

---

## 13. Related Files

| File | Relationship |
|------|-------------|
| `<case_script>` | Primary case script |
| `docs/known_issues.md` | KI cross-references |
| `outputs/<experiment>/` | Run history |
```

## Step 7: Write metrics to analysis/

Write `analysis/metrics.json` in the run directory (gitignored) with structured metadata:
```json
{
  "schema_version": "1.0",
  "experiment": "<experiment>",
  "timestamp": "<ISO datetime>",
  "status": "<success|failure|partial>",
  "git_hash": "<hash>",
  "git_branch": "<branch>",
  "natural_language_request": "<verbatim>",
  "intent_class": "EXAMPLE",
  "case_script": "<relative path>",
  "parameters": { "explicit": {}, "inferred": {}, "defaults": {} },
  "artifacts": [],
  "key_results": {}
}
```

RunContext already writes `meta.json` with core metadata. This adds review-specific detail.

## Step 8: Commit the report and assets

Only `final_document_*.md` and `assets/` are committed. Everything else is gitignored.

```bash
git add outputs/<experiment>/<run>/final_document_YYYY-MM-DD_example.md
git add outputs/<experiment>/<run>/assets/
git commit -m "review[example]: <experiment> — <one-line result summary>"
```

## Honesty requirements

- If timing was not captured, say so in section 9.
- Label inferred parameters as `(inferred)`.
- If output was in `/tmp/` and may be lost, say so and note whether artifacts were copied.
- If a result is borderline, do not call it a clean pass.
- Cross-reference KI numbers for any known limitations triggered.

## Scope

Do not re-run the solver, modify case scripts, or invent results not present in STDOUT or output files.
