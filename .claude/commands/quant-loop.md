---
name: quant-loop
description: Run a quantitative-research task through a validity-first loop — data provenance, alignment, time ordering, survivorship, lookahead, universe, costs, alpha-vs-beta, baseline — with the deployable / broad-floor / diagnostic / production distinction enforced.
---

# /quant-loop <research task>

Run the task as a quantitative-research loop. This encodes Omar's standing
methodology so it does not have to be re-derived each session.

**Mandatory checks:**

1. Producing code path — which script/function generates the result.
2. Input data source — exact dataset and its cache/manifest.
3. Output artifact path — where the result is written.
4. Metric provenance — every number traces to a file, not a print.
5. Feature / label alignment.
6. Time ordering — no future information in past rows.
7. Survivorship bias.
8. Lookahead leakage.
9. Universe construction.
10. Costs / slippage / turnover.
11. Alpha vs beta interpretation — is the edge real, or market exposure?
12. Baseline comparison.
13. Refutation pass (`/refute`).
14. Report / log update.

**Mandatory distinction — always label which run a number belongs to:**

- **deployable / current-universe headline** (what is tradable now);
- **survivorship-honest broad floor** (the unbiased lower bound);
- **diagnostic run** (exploratory, not a claim);
- **production run** (the committed result).

**Hard rule:** never filter a historical broad universe by *current*
tradability unless the result is explicitly labelled survivorship-biased.

Close with `/evidence` on the report and `/ship-loop` before committing. A
metric without an artifact (`metrics.json`, `report.json`, `.csv`,
`.parquet`) is unsupported — run `evidence_audit.py` to check.
