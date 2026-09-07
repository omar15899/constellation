# Tier discipline

The [repository registry](../registry/repos.yaml) declares current members and
tiers. This hub has no QuantOS tier. Agent orchestration is a workflow; it must
not be confused with Tier 4 application code.

For an edge `importer repository → dependency repository` between distinct
QuantOS repositories with numeric tiers, require:

`dependency.tier < importer.tier`

Fractional tiers use numeric order. Tier 2 → Tier 1 is allowed by this rule;
Tier 1 → Tier 2 and same-tier sibling imports are forbidden. Internal imports
within one repo follow its local contracts. Stricter perimeter and local
forbidden-import constraints still apply.

| Tier | Role | Permitted numeric dependency tiers |
| --- | --- | --- |
| 0 | Shared substrate | None in QuantOS |
| 1 | Data and causal evaluators | 0 |
| 1.5 | Pricing | 0, 1 |
| 2 | Information channels | 0, 1, 1.5 |
| 2.5 | Allocation | 0, 1, 1.5, 2 |
| 3 | Risk and execution | 0, 1, 1.5, 2, 2.5 |
| 4 | Strategy orchestration code | 0, 1, 1.5, 2, 2.5, 3 |
| UI | Separate transport boundary | HTTP/WS, not Python cross-imports |

## Enforcement and coverage

Local `.importlinter` contracts constrain imports when the repository runs them;
their mere existence does not establish enforcement. The
[import-graph-auditor](../agents/import-graph-auditor.md), invoked through
`tier-check`, audits relevant cross-repository edges and reports `PASS`,
`BLOCKER` or `INCOMPLETE` with explicit scope. A static scan cannot prove all
dynamic imports are absent. The orchestrator stops dependent promotion when a
verified violation is found and repairs it within task authority.

## Exceptions

- Cross-tier imports in `tests/cross_repo/` may verify cross-repository contracts.
- Tier 0 conformance tests may import higher-tier mock shims located inside
  `Shared/conformance/` to verify Shared contracts.

Ordinary tests are not automatically exempt. Neither exception permits production
coupling. Other proposed exceptions require an architectural decision; do not
relabel the repository or weaken its contract to make the audit pass.

Strictly decreasing numeric tiers preclude cycles among those production edges.
A tier inversion violates the architectural order even if it does not itself
create a cycle. Dependency acyclicity and content-addressing claims still need
the actual graph and artifact contracts; tier labels alone do not prove them.
