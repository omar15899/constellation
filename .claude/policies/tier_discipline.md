# Tier Discipline

QuantOS encodes a strict dependency partial-order. This policy makes it
explicit and enforceable.

## The ladder

```
Tier 4 — Orchestration
        Claude Code workflows (across all labs).
        Imports allowed: any (workflows are external to the import graph).
        Imports forbidden: none.

Tier 3 — Risk & Execution            (touches money)
        Members: RiskLab, ExecutionLab.
        May import from: Tier 0, 1, 1.5, 2, 2.5.
        May NOT import from: each other's tier-3 internals (use HTTP/queue).

Tier 2.5 — Allocation
        Members: PortfolioLab.
        May import from: Tier 0, 1, 1.5, 2.

Tier 2 — Information channels
        Members: NewsLab, ResearchLab, IntelligenceLab.
        May import from: Tier 0, 1, 1.5.
        May NOT import from: each other (use FeatureSet contract).

Tier 1.5 — Pricing
        Members: PricingLab.
        May import from: Tier 0, 1.

Tier 1 — Causal evaluators
        Members: BacktestLab, MonteCarloLab, Sweeplab.
        May import from: Tier 0.
        May NOT import from: each other (use Shared types).

Tier 0 — Substrate
        Members: Shared.
        May import from: nothing in QuantOS (only stdlib + approved deps).

UI tier (outside Python import graph)
        Members: tradinginterface.
        Talks over HTTP/WS only.
```

## The two invariants

**Invariant 1 — No back-imports.** A Tier *k* component may not import
from a Tier *j* component with *j ≥ k*.

**Invariant 2 — No same-tier coupling between siblings.** A Tier 2
component (NewsLab) may not import another Tier 2 component
(ResearchLab) directly. They communicate by typed artefacts
(`FeatureSet`, `Study`, etc.) materialised through `Shared/`.

## How it is enforced

1. **Per-lab `.importlinter` contract.** Each lab declares its layers
   and forbidden imports. Pre-commit gate refuses commits that violate
   the contract.
2. **Cross-lab `import-graph-auditor`.** Walks the union graph across
   all labs. Detects violations that a single lab's contract cannot see
   (because the foreign package is a workspace dependency, not a
   first-class import).
3. **`tier-discipline` skill.** User-invocable summary of the auditor.
   Returns `PASS` / `BLOCKER`.
4. **`multi-repo-orchestrator`.** Halts cross-repo work the moment a
   tier inversion is introduced.

## Exceptions

There are exactly two:

- **Tests.** Cross-tier imports in `tests/cross_repo/` are permitted
  because they exist precisely to verify the contracts hold.
- **Conformance suites.** A Tier 0 conformance suite may import
  higher-tier shims (mock implementations) to verify Shared's
  contracts. These shims live inside `Shared/conformance/` only.

No other exceptions are permitted. If you find yourself wanting one,
the design is wrong — refactor via `cross-repo-refactor` and open an
ADR.

## Why tier discipline matters

The constellation's audit story rests on this discipline:

- Every artefact's BLAKE3 root depends on its inputs.
- Inputs are typed and content-addressed.
- A tier inversion creates a cycle in the dependency graph, which
  breaks the content-addressing invariant: a hash of A can no longer
  be computed before A's inputs, because A's inputs (transitively)
  depend on A.
- Without content-addressing, the audit DAG collapses, and with it the
  causal-identity guarantee that distinguishes QuantOS from a pile of
  scripts.

So tier discipline is not aesthetic. It is the load-bearing wall.
