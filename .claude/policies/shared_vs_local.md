# Shared vs Local

When does a primitive belong in `~/GitHub/Shared/` (the QuantOS
substrate) vs in a lab repo? This policy answers the question for
every cross-lab abstraction.

## The four-question test

A primitive belongs in `Shared/` **iff** all four hold:

1. **Causally identifying.** Different inputs must produce different
   content-addressed roots. The primitive participates in the
   BLAKE3-hashed audit DAG.
2. **Deterministically reproducible.** Pure function of typed inputs.
   No hidden state, no clock, no I/O, no global mutables. Two
   invocations with the same inputs return the same output, in any
   environment.
3. **Needed by ≥2 labs.** A primitive used by exactly one lab does not
   belong in `Shared/` — it lives in that lab. Lifting it prematurely
   inflates the substrate and creates coupling.
4. **On the audit path.** Its output appears in artefact manifests
   (`BacktestRun`, `PricingRun`, `Allocation`, `RiskCert`,
   `OrderProposal`). If the primitive is internal scaffolding only,
   it stays local.

Fail any of the four → it belongs in the lab. If exploratory: keep
inside a `scratch/` directory until it stabilises.

## Anti-pattern: vendored duplicates

A lab that re-implements a Shared primitive **vendored** (copied) is a
release blocker. Open an ADR proposing one of:

- Add the missing capability to `Shared/`.
- Generalise the existing `Shared/` primitive.
- Document that the lab's variant is intentionally different (and why).

The `perimeter-keeper` agent detects vendored duplicates by symbol
name + signature similarity.

## When to lift from lab → Shared

Trigger: a primitive that started life in one lab is now needed by a
second. Workflow:

1. Confirm the four-question test passes for the new home.
2. Lift the primitive into `Shared/packages/<appropriate>/`.
3. Update the source lab to import from `Shared/`.
4. Update the second lab to import from `Shared/`.
5. Run `tier-discipline` (auditor) — the lifted primitive must not
   create a tier inversion.
6. Open a vault-side decision under
   `~/OmarOS/05_Projects/QuantOS/Decisions/`.

## When NOT to add to Shared

- It's a one-off (used by exactly one lab).
- It depends on a higher-tier package (impossible by tier discipline).
- It has hidden state (HTTP client with cookies, DB connection pool,
  threading primitives that mutate state). These belong in the lab
  that owns the state.
- It is a UI concern. `tradinginterface` is on its own side of the
  HTTP boundary.

## Stability tiers inside Shared

Inside `Shared/`, a primitive is in one of three states:

- **Experimental** — pre-API, breakable. Lives in `Shared/scratch/`
  and is not imported by any lab.
- **Substantive** — API stabilising, in use by one or two labs.
  Tagged `status: substantive` in the registry.
- **Mature** — frozen API, in use by ≥3 labs. Tagged `status: mature`.
  Changing the signature requires a `cross-repo-refactor`.

Promotion across these tiers is a deliberate decision recorded in a
vault-side ADR.
