---
name: tier-discipline
description: Verify that the import graph across QuantOS labs respects the canonical tier hierarchy (a Tier k component may import from Tiers 0..k-1, never from k..4). Trigger when the user says "check tier discipline", "audit imports", "verify the tier graph", "tier check", or invokes /tier-check.
---

# tier-discipline

Front door for `agents/import-graph-auditor.md`, exposed as a one-shot
skill.

## When to fire

- After any Tier 0 / Tier 1 edit that might leak upward.
- Before opening a cross-repo refactor PR.
- On demand: "is the import graph clean".

## Operating procedure

1. Dispatch `import-graph-auditor` (the agent).
2. Read the resulting `docs/import_audit.md`.
3. Summarise to the user. If there is a tier inversion, mark the
   summary `BLOCKER` and refuse to proceed with downstream cross-repo
   work.

## Output

```
Tier audit — 2026-05-15
Status: PASS
Labs scanned: 11
Edges in union graph: 187
Violations: 0
```

Or, when failing:

```
Tier audit — 2026-05-15
Status: BLOCKER
Violations:
  - tier_inversion: BacktestLab → quant_research_runner.Study
    (Tier 1 → Tier 2)
Action: resolve before any cross-repo merge.
Detail: docs/import_audit.md
```

## Invariants

- Never auto-rewrites imports.
- Always surfaces the precise file:line for each violation.
- Idempotent.
