---
name: risk-invariant-doctrine
description: Enforce the gate-to-execution invariant — every BacktestRun must carry a passing RiskLab certificate before it can become an OrderProposal-eligible artefact. Typed limits, dimension-additive blocking, no silent breach swallowing.
license: proprietary (Omar Khalil — QuantOS)
contract_invariants:
  - id: I1-Gate
    statement: |
      ∀ run : BacktestRun. run.is_order_proposal_eligible
        ⇒ ∃ cert : RiskReport. cert.run_id = run.id
                              ∧ cert.recommendation ≠ block
                              ∧ cert.age ≤ MAX_RISK_REPORT_AGE
                              ∧ cert.limits_version  = run.limits_version
                              ∧ cert.dataset_version = run.dataset_version
    policy_linkage: RISK_POLICY R5, R6
  - id: I2-TypedLimits
    statement: |
      Every limit dimension is a typed field on RiskLimits with a red threshold
      AND an amber threshold. RiskLimits is append-only; every amendment is a
      new version with a `valid_from` timestamp and a stated rationale.
    policy_linkage: RISK_POLICY R1, R10
  - id: I3-DimensionAdditive
    statement: |
      A breached limit blocks ExecutionIntents that would worsen *that*
      dimension. Intents that improve a breached dimension pass. Global stops
      live in the kill-switch (R4), never in the limit machinery.
    policy_linkage: RISK_POLICY R3, R4
  - id: I4-BlockIsFinal
    statement: |
      A `block` PreTradeRiskReport is non-advisory. There is no override path
      inside RiskLab. Code that catches a Breach exception and continues, or
      that maps `block` → `pass`, violates this invariant.
    policy_linkage: RISK_POLICY R6
  - id: I5-PricingProvenance
    statement: |
      Every Exposure / RiskReport records the PricingRun id (or analytic
      equivalent) of the Greeks it consumed. RiskLab never recomputes Greeks
      silently; aggregation is linear in positions.
    policy_linkage: DOCTRINE §2.2, §7
  - id: I6-DatasetVersionPin
    statement: |
      The certificate's dataset_version equals the BacktestRun's
      dataset_version. A mismatch is a hard preflight failure.
    policy_linkage: DOCTRINE §8 exit-criteria
  - id: I7-FactorModelVersioned
    statement: |
      The factor model used in any RiskReport is identified by version and
      stored as a ModelArtifact. Out-of-sample validation must precede
      promotion to live use.
    policy_linkage: DOCTRINE §6
  - id: I8-RegimeNeverOverridesLimits
    statement: |
      The regime tag is informative. It MAY modulate amber thresholds when
      authorised by risk-architect. It MAY NOT override a red limit.
    policy_linkage: RISK_POLICY R3, DOCTRINE §3
  - id: I9-StressOnEverySnapshot
    statement: |
      The standard stress battery (Doctrine §4) runs on every PortfolioSnapshot
      and the results are stored on the snapshot. ΔNAV ≤ −25% under any
      standard scenario emits an amber alert.
    policy_linkage: RISK_POLICY R7
  - id: I10-NoSilentBreach
    statement: |
      A breach is an event. It must be logged, surfaced, and either resolve
      to a block, an amber, or a structural amendment. Swallowed breaches
      (try/except pass; recommendation flipped without a new RiskLimits
      version) are a doctrinal violation.
    policy_linkage: RISK_POLICY R1, R6
---

# Risk Invariant Doctrine — Skill

This skill is the conscience of RiskLab. It is not a writer; it is an enforcer. Whenever an agent or command produces, modifies, or consumes a `RiskReport`, `RiskLimits`, `PreTradeRiskReport`, `Exposure`, or stress / VaR artefact, this skill verifies the ten invariants above before the artefact is allowed to leave RiskLab.

## When to invoke

- After `/run-risk-check` produces a candidate `RiskReport`, before it is persisted as a certificate.
- After `/new-limit` proposes a `RiskLimits` amendment, before the new version is committed.
- After `/breach-replay`, when interpreting the diff.
- Whenever a downstream lab claims OrderProposal eligibility for a BacktestRun.
- Whenever a code path is found that catches a breach without re-raising or surfacing it.

## What it checks (mechanically)

For every artefact under review, run the ten invariants in order and produce:

```
## Risk Invariant Verdict

### Artefact
- kind: [RiskReport | PreTradeRiskReport | RiskLimits | Exposure | StressResult]
- id: ...
- subject: BacktestRun / PortfolioSnapshot / ExecutionIntent id

### Invariant Results
- [PASS|FAIL|N/A] I1-Gate              — <one-line evidence>
- [PASS|FAIL|N/A] I2-TypedLimits        — ...
- [PASS|FAIL|N/A] I3-DimensionAdditive  — ...
- [PASS|FAIL|N/A] I4-BlockIsFinal       — ...
- [PASS|FAIL|N/A] I5-PricingProvenance  — ...
- [PASS|FAIL|N/A] I6-DatasetVersionPin  — ...
- [PASS|FAIL|N/A] I7-FactorModelVersioned — ...
- [PASS|FAIL|N/A] I8-RegimeNeverOverridesLimits — ...
- [PASS|FAIL|N/A] I9-StressOnEverySnapshot — ...
- [PASS|FAIL|N/A] I10-NoSilentBreach    — ...

### Verdict
- overall: [APPROVED | REVISIONS_REQUIRED | BLOCKED]
- failing invariants: [list]
- required actions: [bulleted]
```

A single FAIL on an enforcement invariant (I1, I3, I4, I6, I10) is BLOCKING. The artefact does not leave RiskLab. The orchestrator routes the failure back to `risk-architect`.

## Authoritative sources

- `~/OmarOS/05_Projects/QuantOS/Vision/Policies/RISK_POLICY.md`
- `~/OmarOS/05_Projects/QuantOS/Labs/RiskLab/Vision/00_Doctrine.md`

## What this skill is NOT

- Not a writer of `RiskReport`s (that is `/run-risk-check`).
- Not a limit author (that is `limit-engineer`).
- Not a policy editor (R-clauses live in the vault and are the user's prerogative).
