---
name: shared-substrate-doctrine
description: Enforce QuantOS Tier 0 doctrine inside the Shared repo — ADR-0020 single-source, the four-clock model, KnownAt[T] discipline, BLAKE3 audit DAG composability, capability typing, tritemporal data store, observability cardinality discipline. Use whenever a request touches packages/quant_core, packages/quant_data, or packages/quant_observability; whenever a downstream lab proposes mirroring or forking a substrate primitive; whenever an ADR for the substrate is being authored, reviewed, or superseded; or whenever cross-lab integration (e.g. MonteCarloEventSource into BacktestLab) is being designed. Do not use for lab-internal artefacts that import from Shared but live in another repo — that is the lab's own doctrine skill.
license: Proprietary. OmarOS internal.
contract_invariants:
  - "ADR-0020 single-source. The substrate is canonical; downstream labs mirror read-only. Forking a schema in a lab is a release blocker."
  - "Four-clock model. Every datum carries (T_event, T_available, T_logical) and a wall-clock origin used only for telemetry. Decision paths take time from CausalClock, never from time.time() or datetime.now()."
  - "KnownAt[T] discipline. A function consuming KnownAt[T] cannot produce KnownAt[T'] with T' < T. Information does not travel backwards."
  - "BLAKE3 audit DAG. Run identity is the root hash. Replays match iff root hashes match. No alternative notion of run identity is admitted."
  - "Tier 0 isolation. quant_core imports nothing from QuantOS. quant_data and quant_observability import only from quant_core. No upward import."
  - "Capability typing (ADR-0013). No effect without a token. No token without a registry entry. Capability env across the integration arrow loses tokens whose namespace is owned by the originating lab unless re-issued."
  - "Stdlib-first. New dependencies in packages/*/pyproject.toml require an ADR proposed first."
  - "Replay equivalence. Schema, RNG, or canonicalisation changes must come with a replay-equivalence argument on the regression corpus."
  - "Read first, write second. Every substrate change reads Vision/00_Substrate.md, the relevant ADRs, and the affected sub-package before any line of code is written."
  - "ADR-first workflow. New substrate components follow /new-substrate-component: intake → architect → ADR (proposed) → tests → implementation → validate → ADR (accepted)."
---

# Shared Substrate Doctrine

This skill is the style-and-invariant enforcer for Tier 0 of QuantOS. The
Shared repo hosts `quant_core`, `quant_data`, `quant_observability`. It is
the *one machine* that BacktestLab and MonteCarloLab evaluate over (Vision
§1). Whatever lives here is borne by every consumer; the cost of a poor
primitive is multiplied across the system.

The skill loads and enforces the contract above; the substantive doctrine
lives in:

- `~/OmarOS/05_Projects/QuantOS/Labs/Shared/Vision/00_Substrate.md`.
- `Vision/01_Master_Roadmap_C.md`, `Vision/02_Master_Roadmap_A_Lean.md`.
- `docs/adr/ADR-0010 .. ADR-0031` (in particular ADR-0020 single-source and
  ADR-0031 binding the substrate's role).

## When to invoke

Use this skill whenever a request:

- Adds, modifies, or removes a public symbol in `packages/quant_core/`,
  `packages/quant_data/`, `packages/quant_observability/`.
- Touches a Cap'n Proto schema or any payload that is BLAKE3-hashed.
- Affects clock semantics (`CausalClock`, `KnownAt[T]`, vendor-revision
  policy).
- Adds, types, or scopes a capability token.
- Changes the effect lattice or audit-DAG manifest.
- Requires a downstream lab to update its read-only mirror.
- Authors or reviews an ADR for the substrate.
- Designs a cross-lab integration arrow (e.g. `MonteCarloEventSource`).

Do **not** invoke for:

- Strategy code in BacktestLab — that is `quant-architect` / `strategy-builder`
  in BacktestLab's own scaffold.
- Pricer or estimator code in MonteCarloLab — `mc-architect` and friends
  there.
- Pure ADR authoring outside QuantOS — use `decision-logger`.
- Documentation chapters in the QuantOS corpus — use `scholar-quant-docs`.

## Deliverables

When the skill fires, the deliverable is one of:

1. **A routing decision** (no code) — for requests classified as `GOVERN` or
   `REASONING` by `shared-router`. The deliverable is the structured intake
   report and the architect dispatch plan.
2. **An ADR** under `docs/adr/ADR-XXXX-<slug>.md`. Status `proposed` until
   the implementation lands.
3. **A code change** in `packages/quant_*/src/` paired with property tests
   under `packages/quant_*/tests/`.
4. **A mirror update note** when the change touches a schema consumed by a
   downstream lab.

## Voice constraints

- Doctrinal voice. No marketing language. No "robust"; instead "robust
  because invariant I-X enforces …". No "general"; instead "these specific
  assumptions were removed: …".
- English-first in code, comments, ADRs. Spanish is admitted in private
  conversation but not in the substrate.
- Terse. The substrate is a kernel; its prose should read like one.
- No emojis in code, ADRs, or commit messages. None. Ever.

## Workflow checklist

Before any commit that touches the substrate:

- [ ] `shared-intake` classification report exists or is unnecessary
      (pure refactor, no public-API change).
- [ ] `substrate-architect` has approved the placement and the ADR-0020
      implication.
- [ ] ADR exists at status `proposed` if a public surface is added.
- [ ] Tests precede or accompany the implementation.
- [ ] `/validate-substrate` is green.
- [ ] `/audit-imports` is green.
- [ ] Mirror update plan exists for every consuming lab if a public schema
      is touched.
- [ ] Commit message is human-voice, present tense, no AI attribution.

## Anti-patterns (rejected at review)

- A public symbol added to `packages/quant_*/src/` without a paired test.
- A new `pandas`, `polars`, `scipy`, `sklearn`, `pytorch`, `tensorflow`
  import in `packages/quant_*` without an ADR.
- A wall-clock call (`time.time()`, `datetime.now()`) inside a decision
  path.
- A schema change without a `schema_version` bump.
- A capability check via globals or env (ambient authority).
- A test in `packages/quant_X/tests/` that imports from
  `packages/quant_Y/`.
- A commit that bundles two unrelated logical units.
- Any AI-attribution footer in a commit message.

## Authoritative references

- Vision: `Vision/00_Substrate.md`, `Vision/01_Master_Roadmap_C.md`,
  `Vision/02_Master_Roadmap_A_Lean.md`.
- ADRs: ADR-0010, ADR-0011, ADR-0013, ADR-0014, ADR-0015, ADR-0020,
  ADR-0021, ADR-0022, ADR-0023, ADR-0031.
- Code: `packages/quant_core/`, `packages/quant_data/`,
  `packages/quant_observability/`.
- Sibling labs: `~/GitHub/BacktestLab/`,
  `~/GitHub/MonteCarloLab/`.
