---
name: cross-repo-refactor
description: Propagate a typed change (rename, signature update, schema migration) across multiple repositories with tier-ordered execution and per-repo validation. Trigger when the user says "rename X across all labs", "update signature Y everywhere", "refactor across the stack", "propaga este cambio", or invokes /repo-refactor.
---

# cross-repo-refactor

The skill that turns "rename `KnownAt` to `WithTime`" into an ordered,
validated, per-repo execution plan.

## When to fire

- A primitive in `Shared/` changes name or signature.
- A typed artefact (BacktestRun, PricingRun, FeatureSet) gains/loses a
  field.
- A schema in `<lab>/schemas/` is renamed or restructured.
- Any rename that the user describes as "across the stack".

## Operating procedure

1. **Identify the source of the change.** Usually the lowest-tier repo
   touched. Confirm with the user.
2. **Build the consumer set.** Use `cross-repo-grep` to find every
   reference (symbol or schema string) in higher-tier repos. The
   import graph in `agents/import-graph-auditor.md` gives the canonical
   consumer ordering.
3. **Order by tier.** Tier 0 first, then 1, 1.5, 2, 2.5, 3, then UI.
4. **Per-repo plan.** For each consumer:
   - List touched files.
   - Estimate the diff (signature update? type rename? both?).
   - Note any consumer-specific edge case (mypy strict, test fixtures,
     serialisation contracts).
5. **Present the plan.** Wait for confirmation.
6. **Execute repo by repo** via `multi-repo-orchestrator`:
   - Each repo's `.claude/` orchestrator handles its own edit.
   - After each tier completes, run `tier-discipline` to confirm the
     graph is still clean.
   - One commit per repo.
   - Stop on first failure. Never paper over.
7. **Final validation:**
   - `multi-repo-status` — every repo clean and on its branch.
   - `import-graph-auditor` — final union graph audit.
   - Generate a per-repo PR list.

## Output contract

```yaml
refactor:
  description: "rename KnownAt → WithTime"
  origin: Shared
  consumer_order:
    - tier_0: [Shared]
    - tier_1: [BacktestLab, MonteCarloLab, Sweeplab]
    - tier_1_5: [PricingLab]
    - tier_2: [NewsLab, ResearchLab, IntelligenceLab]
    - tier_2_5: [PortfolioLab]
    - tier_3: [RiskLab, ExecutionLab]
  per_repo_commits:
    Shared: a1b2c3d
    BacktestLab: ...
  validation:
    tier_audit: pass
    multi_repo_status: clean
  prs: [<url>, <url>, ...]
  vault_followup: "Open ADR under 05_Projects/QuantOS/Decisions/"
```

## Invariants

- **Never auto-bypasses pre-commit gates.** A failing gate halts the
  whole refactor for that repo.
- **No `--force` pushes.**
- One commit per repo per logical change. Never bundles.
- Always proposes the vault-side ADR follow-up; never writes it
  itself.
