---
name: tier-check
description: Audit the tier discipline across QuantOS labs — runs the import-graph-auditor and prints a PASS / BLOCKER summary.
---

# /tier-check

Verify that every QuantOS lab respects the tier hierarchy: a Tier *k*
component may import from Tiers *0..k−1*, never from *k..4*.

## Pipeline

1. Invoke the `tier-discipline` skill.
2. The skill dispatches `import-graph-auditor`.
3. Output the verdict and (on BLOCKER) the precise file:line of each
   violation.

## When to use

- After a Tier 0 / Tier 1 edit.
- Before a cross-repo refactor merges.
- As part of `/governance-audit` workflows at the vault.

## Aliases

`/audit-imports`, `/import-audit`.
