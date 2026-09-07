---
name: tier-check
description: Audit QuantOS dependencies, same-tier coupling and perimeter boundaries against repository contracts. Use for check tier discipline, audit imports or verify the cross-repository dependency graph.
---

# Check tier and dependency boundaries

Use [import-graph-auditor](../../agents/import-graph-auditor.md), supplying the
requested roots or changed boundary. Read [tier discipline](../../policies/tier_discipline.md)
and relevant repository contracts. Do not audit unrelated repos by default.

For a cross-repository edge `importer → dependency` with numeric QuantOS tiers,
require `dependency.tier < importer.tier`. This includes fractional tiers and
Tier 4. Same-repository imports, UI transport and documented test/conformance
exceptions require their own applicable rules.

Report `PASS`, `BLOCKER` or `INCOMPLETE` with scope and evidence. A syntax scan,
valid `.importlinter` file or absent textual matches alone cannot prove the
runtime dependency graph is valid. Name unresolved imports and missing checks.
Propose concrete repairs; never weaken the contract or edit neighboring code
under a read-only audit request.
