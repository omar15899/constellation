---
name: portfolio-allocation-doctrine
description: Enforces PortfolioLab allocation doctrine — typed constraints, PSD covariance, no leakage from BacktestRun future window, intelligence-weighting provenance. Triggers on any allocation, optimisation, rebalance, BL view, or HRP run.
license: proprietary
contract_invariants:
  - I-1: universe_hash(w*) = universe_hash(Σ) = universe_hash(μ) = universe_hash(IntelligenceBundle)
  - I-2: Σ ⪰ 0 verified by Cholesky; Σ̂_post (BL) records projection method when used
  - I-3: ConstraintSet certified non-empty before solver dispatch (typed feasibility, not exception-handler)
  - I-4: every input I satisfies available_at(I) ≼ decision_time
  - I-5: every contributing CF estimator id and BacktestRun ancestry present in Allocation.metadata
  - I-6: same (Σ, μ, ConstraintSet, π, w_prev, IntelligenceBundle) → bit-identical w* (deterministic)
  - I-7: no input window strictly later than decision_time (no leakage from BacktestRun future window)
  - I-8: AuditDAG chains back to every input; replay reproduces w*
---

# PortfolioLab Allocation Doctrine

This skill governs every PortfolioLab allocation. It is the operational
expression of ADR-0026 (`portfolio-intelligence-layer`) — PortfolioLab is
the ground-truth substrate for runtime portfolio reasoning, so its
allocations must be auditable end-to-end.

## When this skill fires

Any of:
- writing or modifying `allocators/*.py`
- running `/new-allocator`, `/optimize`, `/simulate-rebalance`,
  `/black-litterman`, `/hrp`, `/audit-allocation`
- consuming a `BacktestRun` or an IntelligenceLab CF estimate from a
  PortfolioLab pipeline
- editing `packages/quant_portfolio/` interfaces

## Hard rules

### 1. Typed constraints

Constraints are typed leaves, never strings, never lambdas:

```
LongOnly | LeverageCap(L) | TurnoverCap(τ, w_prev) |
SectorCap(group, cap) | FactorBox(B, lo, hi) |
PositionBox(lo, hi) | Cardinality(k) | And(c₁, c₂)
```

Every `ConstraintSet` must be certified non-empty before solver dispatch.
Infeasibility is a typed error — not a silently-returned zero vector.

### 2. PSD covariance

Σ ⪰ 0 verified by Cholesky before optimisation. If projection was needed
(nearest-PSD, eigenvalue clipping, Higham), the method is recorded in the
Allocation metadata. Σ̂_post from Black-Litterman is checked the same way.

### 3. No leakage from BacktestRun future window

When a `BacktestRun` artefact feeds an allocation (directly or via an
IntelligenceLab CF estimate trained on it), the run window must close
strictly before `decision_time`. Reads must be wrapped in `KnownAt[t]`. The
preflight hook flags raw `BacktestRun` references that bypass the causal
guard.

### 4. Intelligence-weighting provenance

When the Allocation consumed an IntelligenceLab CF estimator, every
contributing estimator's id, the BacktestRun ancestry, the dataset hash,
and the weighting parameters are written into `Allocation.metadata`. An
Allocation that consumed CF estimates without recording their provenance is
a bug.

### 5. Determinism

Same inputs → bit-identical w*. No global RNG. Any randomness routes
through a counter-based RNG keyed by the allocation context (mirrors
ADR-0016 in the MC layer).

### 6. Audit completeness

`Allocation.audit_dag` chains back to Σ, μ, ConstraintSet, π, w_prev, and
the IntelligenceBundle. Pre-trade verifiers must replay the allocation
purely from the audit DAG.

## Engine-vs-application boundary (ADR-0003)

`packages/quant_portfolio` is stdlib-first. `cvxpy`, `scipy.optimize`,
`osqp`, `ecos`, `numpy`, `pandas` belong in `allocators/` not in
`packages/`. The engine consumes typed `Allocator` protocols; the solver
choice is a property of the script.

## Failure modes

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `Allocation` rejected at audit | I-1 universe-hash mismatch | Recompute Σ / μ on the same dataset version |
| Solver returns NaN | Σ not PSD | Add a regulariser, record the projection |
| Allocation differs run-to-run | mutable dict in state OR global RNG | switch to PMap, route RNG through the counter-based source |
| `ReconciliationFailure` (ADR-0026) | live portfolio drift exceeds tolerance | block ExecutionIntent until PortfolioLab snapshot is reconciled |

## References

- ADR-0026 — `portfolio-intelligence-layer`
- ADR-0003 — engine stdlib-first policy
- ADR-0016 — counter-based RNG (allocator-side echo)
- `packages/quant_portfolio/` — Allocator, Allocation, ConstraintSet,
  CovarianceEstimate, RebalanceTrigger
- `.claude/hooks/portfolio_preflight.py` — preflight enforcement
