---
name: gate-check
description: Run a research result through the promotion gate (DSR/PBO/reality-check/BH-FDR/bootstrap-CI at the honest family m), assign a verdict from the canonical vocabulary, and record it as a structured row in registry/levers.yaml + research_ledger.md. The bar that turns a headline Sharpe into a CONFIRMED/REFUTED/CAPPED verdict.
---

# /gate-check <result, glob, or lever id>

Judge a quantitative research result against the standing bar in
[`contracts/promotion_gate.md`](../contracts/promotion_gate.md) and persist the
verdict so no future session re-derives or re-runs it.

**The bar is the user's planning decision. Do not lower it to make a result pass.**

## Steps

1. **Identify the family.** Determine the full set of cells swept — this IS the
   multiple-testing denominator `m`. If only the winner is shown, find the rest;
   a verdict at a shrunken `m` is invalid.

2. **Run or ingest the gate.** Prefer the authoritative instrument in ResearchLab:
   `scripts/promotion_report.py --glob '<outputs glob>' [--ppy 252]`, which writes
   `reports/promotion_*.json`. If a report already exists, ingest it — do not
   re-run blindly.

3. **Read the four bars** for the candidate: BH–FDR adjusted p, block-bootstrap
   Sharpe CI lower bound, annualised Sharpe, DSR. Plus family PBO and the
   reality-check. Print:

   | cell | Sharpe | DSR | CI_low | BH-FDR p | PBO(family) | bar met? |
   |---|---|---|---|---|---|---|

4. **Assign the verdict** from the canonical vocabulary (OPEN / CONFIRMED /
   CAPPED / NO_IMPROVEMENT / REFUTED / HOLD). CONFIRMED requires **all four**
   bars at the honest `m`. High PBO REFUTES regardless of headline Sharpe.

5. **Tag the run class** — deployable / broad-floor / diagnostic / production.
   Never conflate the deployable headline with the survivorship-honest broad floor.

6. **Record it.** Append or update the lever in
   [`registry/levers.yaml`](../registry/levers.yaml) (the structured source of
   truth) and mirror the readable row in
   [`research_ledger.md`](../research_ledger.md). Set `rerun: false` for a closed
   verdict (REFUTED / CONFIRMED / final NO_IMPROVEMENT); `rerun: true` only if a
   specific new data source or method would genuinely reopen it. Bump
   `last_updated`. Never silently overwrite an existing verdict — if it changes,
   say why in the `note`.

7. **Refute** (`/refute`) and attach evidence (`/evidence`). A verdict without a
   backing artifact (`promotion_*.json`, `pnl.csv`) is unsupported.

## Guardrails

- A high Sharpe from a large sweep is a draw from the search, not evidence.
- If a fresh run contradicts the reference anchors in the contract without a code
  change to explain it, suspect a regression in the gate before believing it.
- This command **writes to the registry** — it is the only sanctioned path for a
  lever verdict to enter persistent state.
