---
name: causal-inference-doctrine
description: The IntelligenceLab causal-inference doctrine. Enforces explicit assumption declaration, identifiability before estimation, and sensitivity analysis on every reported effect. Use whenever an SCM is designed, an identification strategy is chosen, an assumption is declared or audited, a counterfactual is estimated, or a sensitivity analysis is reported. Invoked automatically by /new-scm, /run-counterfactual, /audit-assumptions, /identify-estimand, /sensitivity-test, and by the intelligence_preflight hook.
license: MIT
contract_invariants:
  - I-CI-1 — Assumptions are declared, not implicit. Every counterfactual carries a typed list of assumptions; an empty list is a doctrine violation.
  - I-CI-2 — Identifiability before estimation. No estimator runs without an Estimand record whose verdict is identifiable or identifiable-on-subregion.
  - I-CI-3 — Acyclicity. The SCM graph is acyclic. The intelligence_preflight hook enforces this on every run.
  - I-CI-4 — Distribution kind is typed. Every CounterfactualEstimate carries distribution_kind ∈ {observational, interventional, counterfactual}; conflating P(Y|X), P(Y|do(X)), P(Y_x|·) is a doctrine violation.
  - I-CI-5 — Sensitivity is mandatory. No effect leaves IntelligenceLab without a sensitivity envelope (E-value, Rosenbaum, partial-R², Manski, or twin-network).
  - I-CI-6 — Backend through Capability. dowhy and pyro are imported only by dowhy-adapter and pyro-adapter respectively (ADR-0019).
  - I-CI-7 — Portfolio independence. IntelligenceLab reads a stamped PortfolioSnapshot for relevance filtering; it never writes portfolio state (ADR-0027).
  - I-CI-8 — Twin-network for variance reduction. When a counterfactual delta is reported, prefer shared-noise twin-network coupling over naive resampling (ADR-0019).
---

# Causal-Inference Doctrine

IntelligenceLab is the counterfactual / causal-inference layer of QuantOS. Its outputs are typed counterfactual estimates consumed by ResearchLab and PortfolioLab. The distinction between observational, interventional, and counterfactual distributions is explicit in every output. Assumptions are declared, not implicit.

This skill is the doctrine. It is non-negotiable.

## Doctrine source

- **ADR-0019** — Counterfactual SCM via DoWhy + Pyro do-operator + custom twin-network. DoWhy provides graph utilities and the high-level estimation API; Pyro provides the do-operator and full Bayesian posteriors over counterfactuals; the twin network couples factual and counterfactual paths via shared noise coordinates for variance reduction.
- **ADR-0027** — IntelligenceLab pipeline: filter-first, position-aware, portfolio-independent. Four-filter pipeline (materiality, relevance, novelty, credibility) before any analysis. `contradictory_evidence` is mandatory. Reddit is a crowding thermometer, not a research source. IntelligenceLab does not own portfolio state.

## The three rules

### Rule 1 — Declare assumptions

Every causal claim rests on assumptions. Every IntelligenceLab counterfactual carries them as typed metadata: positivity, ignorability, SUTVA, consistency, exclusion, monotonicity, parallel trends, continuity at threshold. Empty lists are violations.

### Rule 2 — Identify before estimating

No estimator runs without an `Estimand` record whose verdict is `identifiable` or `identifiable-on-subregion`. The verdict is produced by `identification-strategist` via do-calculus / ID algorithm and persisted. The `intelligence_preflight` hook reads it.

A non-identifiable estimand does not become identifiable because the estimator returns a number. It returns a regression coefficient, not a causal effect.

### Rule 3 — Sensitivity on every effect

No reported effect lacks a sensitivity envelope. `sensitivity-analyst` is mandatory. A point estimate without a bound on unobserved confounding is not a causal claim.

Methods, by strategy:
- Backdoor + binary outcome → E-value + partial-R²
- Backdoor + matched → Rosenbaum bounds
- Backdoor + linear → partial-R² (sensemakr)
- IV → Conley plausibly-exogenous on exclusion
- DiD → pre-trend placebo, anticipation test
- Non-identifiable → Manski / Balke-Pearl bounds
- Pyro / twin-network available → twin-network counterfactual sensitivity (preferred, ADR-0019)
- DoWhy backend → refutation battery (placebo, random common cause, data subset) by default

## Distribution-kind discipline

The single most common failure mode is conflating $P(Y \mid X)$, $P(Y \mid \mathrm{do}(X))$, and $P(Y_x \mid X = x', Y = y')$. Every `CounterfactualEstimate` carries a `distribution_kind` field. The estimator is responsible for setting it correctly. An adjusted regression that recovers the interventional mean under backdoor adjustment may set `interventional`. An unadjusted regression may not.

## Capability discipline

`dowhy` is imported only inside `dowhy-adapter`. `pyro` is imported only inside `pyro-adapter`. Estimator scripts and engine code are backend-agnostic. The preflight hook enforces this.

## When this skill fires

- Designing an SCM (`/new-scm`, `scm-architect`)
- Choosing an identification strategy (`/identify-estimand`, `identification-strategist`)
- Declaring or auditing assumptions (`/audit-assumptions`, `assumption-auditor`)
- Estimating a counterfactual (`/run-counterfactual`, `counterfactual-engineer`)
- Reporting sensitivity (`/sensitivity-test`, `sensitivity-analyst`)
- The `intelligence_preflight` hook before any counterfactual run

## Failure modes the doctrine prevents

1. Reporting $P(Y \mid X)$ as if it were $P(Y \mid \mathrm{do}(X))$.
2. Estimating an unidentifiable estimand and treating the regression coefficient as causal.
3. Quoting a point estimate with no bound on unobserved confounding.
4. Building an SCM with a cycle.
5. Importing DoWhy or Pyro outside the adapter boundary, defeating Option B/C portability.
6. Generating a `ThesisCandidate` with empty `contradictory_evidence` (ADR-0027).
7. Mutating portfolio state from inside IntelligenceLab (ADR-0027).
