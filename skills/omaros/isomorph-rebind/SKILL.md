---
name: isomorph-rebind
description: Produce a rigorous, privacy-preserving reintegration map that tells the user exactly how to bind a generic implementation (typically produced by `isomorph-synth`) back into their private real-world codebase — without ever writing the private code, without fabricating private names/paths/secrets/schemas, and without requiring the private system to be in context. The output is a strict 8-section markdown artefact (Reintegration assumptions → System correspondence map → Adaptation points → Required private bindings → File-level integration strategy → Validation and regression checklist → Reintegration risks → Minimal safe integration order) written in contract-level language so a technically strong user can perform the local binding themselves with minimal ambiguity and minimal risk. Use this skill whenever the user says "plan the reintegration", "how do I bind this generic code to my real system", "reintegration map", "binding plan for this scaffold", "how do I merge this scaffold into my private codebase", "I have the generic implementation — now how do I connect it", "map this back to my real project", "integration plan for the synth output", "guide for reincorporating this into my internal system", or follows up an `isomorph-synth` run by asking how to plug the result into their private environment. The skill is deliberately the third of a triptych with `project-isomorph` (private→abstract) and `isomorph-synth` (abstract→generic); together they form the complete roundtrip but each runs independently. Do NOT trigger for (a) actually writing or editing the private code — the skill refuses that on purpose because Claude does not and should not have private code in context; (b) generating the generic scaffold itself — that is `isomorph-synth`; (c) pure-refactor tasks on existing code the user already has open — use a code review tool; (d) documentation / PRD / onboarding docs aimed at readers outside the engineering team — use doc-coauthoring; (e) ADR recording a single architectural decision — use decision-logger.
license: Proprietary. OmarOS internal.
---

# Isomorph Rebind — Reintegration Planner

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

This skill is the third leg of a deliberate roundtrip:

```
private project  ──[project-isomorph]──►  8-section agnostic dossier
agnostic dossier ──[isomorph-synth]────►  6-section generic scaffold
generic scaffold + private knowledge ──[isomorph-rebind]──►  reintegration map
```

The reintegration map is an **8-section plan**, not code. The reason is blunt: binding the generic scaffold to a private system requires knowledge of the private system, which Claude does not (and must not) have in context — that's the whole point of the anonymisation step. So this skill treats the reintegration as a **boundary-preserving mapping problem**:

- the generic scaffold is one system, described precisely (inputs Claude has).
- the private system is another system, described only at the contract level (what the user says, nothing more).
- the skill produces the **morphism** between them: for every generic seam, what private contract it must bind to, what must remain invariant after binding, what can stay generic.

The user then performs the binding locally, inside their own environment, without leaking anything to Claude. The skill's output is rich enough that an engineer familiar with the private system can execute it mechanically, section by section.

## When this skill runs

Trigger whenever the user presents a generic scaffold (a 6-section `isomorph-synth` artefact, a materialized scaffold directory, or code clearly produced by that pipeline) and asks for a binding / reintegration / merging plan. Typical phrasings:

- "plan the reintegration", "reintegration map", "how do I bind this to my real system"
- "how do I merge this scaffold into my private codebase"
- "I have the generic implementation — now how do I connect it"
- "map this back to my real project", "integration plan for the synth output"
- "guide for reincorporating this into my internal system"
- an implicit follow-up to an `isomorph-synth` run: the scaffold is visible in context and the user now asks how to plug it in

Do **not** trigger for:

- **Writing or editing the actual private code.** The skill produces a plan, not private code. If the user asks "just write the binding for me", redirect: the skill's contract is that Claude doesn't touch their internals.
- Generating the generic scaffold itself → `isomorph-synth`.
- Refactoring existing code the user already has open in their repo → normal code-review tooling.
- Producing migration / onboarding / PRD documentation for readers outside the immediate engineer binding the code → `doc-coauthoring`.
- Recording a single architectural decision → `decision-logger`.

## Invariants (the reason this skill exists and is shaped the way it is)

1. **No private code is written.** The skill only writes the plan. The user binds locally. This is absolute — generated code would either be guesswork (dangerous) or require the private system in context (defeats the anonymisation).
2. **No invented private specifics.** No real endpoint URLs, class names, file paths, credential handles, column names, or schema details are guessed. When the private system is unknown, the recommendation is contract-level, not named.
3. **Uncertainty is first-class.** Every correspondence in Section 2 carries a confidence label (`high confidence` / `medium confidence` / `low confidence`). Low-confidence items must present at least one alternative plausible integration mode; they must not be dressed up as certainties.
4. **Contracts over names.** A binding is specified by the **methods, fields, shapes, invariants** that must hold — not by "this maps to `AcmePricer`" which Claude cannot know.
5. **Integration-mode classification is load-bearing.** Every non-trivial integration decision carries one of the six modes from `references/integration_modes.md` (direct drop-in / adapter-mediated / interface-only / architectural reference / partial manual transplantation / non-reintegrable without redesign) with a one-line justification. This is how the user calibrates how much work each piece is.
6. **Narrow seams, broad stability.** The plan prefers putting all private-specific work into a small number of adapter files, with the generic code unchanged. Invasive edits spreading across many files are flagged as a risk, not a recommendation.
7. **The 8-section structure is mandatory.** It is the contract that makes the artefact machine-parseable by `validate_rebind_map.py` and predictable for the user reading it during the bind.

## The 8-section output contract

Headings are fixed, in this order, spelled exactly:

```
# 1. Reintegration assumptions
# 2. System correspondence map
# 3. Adaptation points
# 4. Required private bindings
# 5. File-level integration strategy
# 6. Validation and regression checklist
# 7. Reintegration risks
# 8. Minimal safe integration order
```

Each section has a required shape. The authoritative specification is `references/output_protocol.md` — read it before writing the artefact.

## Procedure

### Step 1. Establish what is known

Before writing, separate three sources of knowledge:

1. **What the generic scaffold gives you** — the 6-section artefact or the materialized directory. If it's an artefact, parse it; if it's a directory, run the bundled extractor:

   ```bash
   uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/isomorph-rebind/scripts/extract_adaptation_points.py <target>
   ```

   The extractor walks the scaffold (markdown artefact or live directory), finds every `ADAPTATION POINT` / `USER-INTEGRATION REQUIRED` / `PROJECT-SPECIFIC IMPLEMENTATION GOES HERE` marker, and emits structured JSON: marker kind, file, symbol, surrounding docstring, inferred contract. This JSON is the skeleton for Section 3.

2. **What the user has told you about their private system** — only what's in the conversation. Treat this as the only private-domain information you have. If the user has been terse, say so in Section 1 and proceed with contract-level recommendations.

3. **What you must not assume** — specific class names, specific endpoints, specific library versions, specific internal conventions. Everything named in the output must be either (a) a generic name from the scaffold, or (b) a contract that the user must match.

### Step 2. Draft Section 1 (Assumptions) before anything else

List, separately:

- what is known from the generic scaffold
- what is known about the private system (direct user statements; nothing else)
- what is **unknown** about the private system — explicitly. Missing knowledge is load-bearing; burying it is how reintegrations fail silently
- what assumptions the plan makes to proceed (e.g. "assuming the private system has a dependency-injection container capable of registering the scaffold's interfaces")

### Step 3. Build the correspondence map (Section 2)

For every major generic artefact (module, component, dataset, interface, external integration), emit a row in the correspondence table: generic name → likely private counterpart category → correspondence type → confidence → notes.

**Categories** (from the user's specification):

- `exact structural analogue` — private system almost certainly has a one-to-one match
- `interface-level analogue` — match exists at the shape level; private implementation will differ
- `infrastructure placeholder` — scaffold provided a stub for something the private system owns fully (DB, broker, identity)
- `schema placeholder` — scaffold named a schema generically; private schema exists with equivalent semantics but different column names
- `domain-logic placeholder` — scaffold provided a textbook implementation; private version is proprietary
- `integration wrapper` — scaffold provided an adapter that the private system either already has or will create
- `test harness` — scaffold provided fixtures / synthetic data; private side has real data or separate test infrastructure

**Confidence labels** (see `references/confidence_discipline.md`):

- `high confidence` — the correspondence follows from the generic scaffold alone; no private-side inference needed.
- `medium confidence` — the correspondence follows from common patterns in the private system's category (e.g. "most pricing engines have a calibration step, so there is almost certainly one here").
- `low confidence` — correspondence is plausible but the user's description left it genuinely uncertain; emit at least one alternative.

### Step 4. Enumerate adaptation points (Section 3)

For every marker found in Step 1, emit a subsection:

- **identifier** (from the scaffold's Section 4, unique)
- **location** in generic code (file + symbol)
- **what must change** (the body, the adapter, the config)
- **why** (the contract the private system imposes)
- **what private object / system must be bound** — by contract, not by name
- **mandatory vs optional**
- **what must remain invariant** after the change (signature, shape, determinism, idempotency, error semantics)

Use the tags: `ADAPTATION POINT`, `PRIVATE BINDING REQUIRED`, `LOCAL NAME REBINDING`, `SCHEMA REBINDING REQUIRED`, `INFRASTRUCTURE SUBSTITUTION REQUIRED`, `SAFE TO KEEP GENERIC`.

### Step 5. Required private bindings (Section 4)

For each binding, spell out the **contract** the private object must satisfy. Concrete formulations:

- "bind this generic `MarketDataInterface` to the internal market-data service that satisfies methods `fetch_observations(universe) -> DataFrame[N, K]` with transient-failure tolerance, no cross-run caching, and vendor-auth handled by the caller."
- "replace the generic DataFrame adapter with the local normalization layer, preserving a timestamp column, an identifier column, and two numeric-measure columns of equivalent semantic role."
- "map this settings object to the private runtime settings provider that supplies environment-specific endpoints and credential handles."

For each binding include: **target contract**, **required methods/fields**, **invariants**, **failure modes if bound incorrectly**.

### Step 6. File-level integration strategy (Section 5)

For every file in the scaffold, one disposition:

- `keep as is` — copy-paste into the private repo, unchanged.
- `keep with renaming` — rename to match private conventions; contents unchanged.
- `keep with local adapter injection` — generic body stays; a thin adapter is injected via dependency-injection / partial / decorator / factory.
- `merge manually into an existing private file` — file already exists privately; user must cherry-pick portions.
- `use only as a design reference` — the scaffold's file is illustrative; the private analogue is written from scratch using the scaffold as a sketch.
- `do not integrate directly` — the scaffold file is a stub / fixture / test helper the private system already has more fully.

Each file carries: integration action, rationale, effort estimate (trivial / small / medium / large), dependency considerations, validation requirement post-integration.

### Step 7. Validation checklist (Section 6)

Deterministic checks, not vague guidance. Typical items:

- interface conformance (mypy / tsc / runtime type check on the adapter boundary)
- schema conformance (parse + validate a representative sample)
- shape / dtype consistency (assertions on representative inputs)
- dependency resolution (`uv sync` / `pnpm install` / `cargo check` without conflicts)
- config loading correctness (settings object resolves on all target environments)
- integration test success (specific test files must pass)
- side-effect correctness (observability sink receives N events per batch; DB write lands in the right table)
- logging behaviour (log lines match the scaffold's log contract — no private content accidentally leaked into logs written to shared sinks)
- caching behaviour (if any — the scaffold usually avoids caching by default)
- backward compatibility (if rebinding into an existing private module, the prior public API must still satisfy its callers)
- output equivalence at the contract level (same-input / same-output against a golden file, not a pointwise comparison on potentially-changed numerics)
- performance sanity (order-of-magnitude — a 100× regression is a regression, ±20% is not)

### Step 8. Risks (Section 7)

Use the catalog in `references/risk_register.md`. For each risk picked: description, severity (low / medium / high / critical), detectability (easy / moderate / hard / invisible-until-production), mitigation.

### Step 9. Minimal safe integration order (Section 8)

Pick an ordering that minimises blast radius and maximises observability. Default template:

1. bind configuration (smallest surface, fastest feedback if wrong)
2. bind interfaces (signature-only binding; nothing executes yet)
3. bind schemas (types + shapes)
4. integrate pure domain logic (no I/O, cheap to test)
5. integrate infrastructure adapters (real I/O, real failure modes; tested in isolation first)
6. integrate orchestration / pipeline layer
7. run the scaffold's tests against the bound implementation
8. run side-effect-safe smoke checks (read-only end-to-end in a staging env)
9. run production-like validation (dark-launch, shadow-deploy, or gated rollout per the private system's norms)

Adapt the ordering if the scaffold's shape calls for a different one, but state explicitly what you changed and why.

### Step 10. Self-validate

```bash
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/isomorph-rebind/scripts/validate_rebind_map.py <output.md>
```

Checks: all 8 sections present in order; every adaptation point in Section 3 has a matching binding in Section 4; every binding states a contract and at least one failure mode; every file in Section 5 has a disposition chosen from the six valid options; Section 8 is ordered and numbered. Warnings for low-confidence correspondences without alternatives, risks without detectability tags, and checklist items without deterministic content.

### Step 11. Return the plan

Default: emit the full markdown inline. If the user asks for a file, write to the path they specify or default to `11_Documents_and_Reports/Reintegration_Maps/<slug>.md` inside the vault.

## Hard constraints

- **Never propose or write private code.** If tempted to show "what the adapter body might look like in the private system", stop — that is either guesswork (dangerous) or inferring from private context Claude shouldn't have.
- **Never guess a private name.** File paths, class names, endpoint URLs, table names, column names — if the user didn't state them, they are unknown. Say so and recommend by contract.
- **Never recommend bulk copy-paste into sensitive systems.** Every integration touches either a controlled boundary (adapter file) or goes through a reviewed PR. Bulk dumps into production code are a risk flag, not an action item.
- **Never collapse integration effort into vague advice.** "Integrate the adapter carefully" is not a plan; "bind the adapter to a service whose interface conforms to `X`, then run the three validation checks in Section 6 items 1–3" is.
- **Integration modes are tagged for every non-trivial decision.** Implicit modes are a frequent source of confusion; making them explicit keeps the bind legible.

## Bundled resources

- `references/output_protocol.md` — the authoritative 8-section output template. Read before writing.
- `references/integration_modes.md` — the six integration-mode labels, when each applies, and how to tag them in Section 5.
- `references/risk_register.md` — catalog of typical reintegration risks with severity / detectability / mitigation patterns. Use to populate Section 7.
- `references/confidence_discipline.md` — rules for `high / medium / low` labels, including when to emit alternatives at low confidence.
- `references/examples.md` — one worked example end-to-end: a pricing-engine scaffold from the `isomorph-synth` example, translated into a full reintegration map against a sketched private environment.
- `scripts/extract_adaptation_points.py` — parses a 6-section synth artefact or a materialized scaffold directory, finds all adaptation markers, emits JSON (marker kind, file, symbol, surrounding contract). Use as the skeleton for Section 3.
- `scripts/validate_rebind_map.py` — validates a 8-section reintegration map: sections present and ordered, adaptation points ↔ bindings ↔ integration dispositions cross-linked, contracts + failure modes non-empty, confidence labels present on every correspondence, integration modes tagged.

## Cross-references

- Sibling: `project-isomorph` (forward — private → agnostic dossier).
- Sibling: `isomorph-synth` (middle — agnostic → generic scaffold). The usual input to this skill.
- Not `doc-coauthoring` (writes prose for humans outside the binding engineer).
- Not `decision-logger` (records one architectural decision, not a migration plan).
- Not `project-import` (ingests a real project into the vault, not a reintegration plan).
- **Portability note**: the 8-section contract and the tag vocabulary are stack-agnostic and tool-agnostic on purpose. The same artefact can be consumed by a human engineer, by GitHub Copilot via a repository-level instruction, or by another AI system that supports reusable prompt templates. Keep that portability when editing this skill.
