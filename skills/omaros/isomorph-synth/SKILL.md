---
name: isomorph-synth
description: Synthesize generic, production-style, reintegrable code from an agnostic structural specification — the inverse of `project-isomorph`. Given a privacy-safe markdown dossier (the 8-section output of project-isomorph, or any equivalent agnostic spec describing a project, codebase, folder structure, pipeline, interface layer, or software subsystem), reconstruct a clean implementation that preserves the architecture, the data contracts, the execution flow, and the integration boundaries — but never invents proprietary business logic, fake secrets, fake endpoints, or private names. Use this skill whenever the user says "synthesize code from this spec", "generate a scaffold from this dossier", "build the generic implementation", "rebuild from this spec", "reconstruct the code from the abstract description", "implement this specification", "realize this dossier", "scaffold the project described here", "turn this isomorph into code", "give me a starting implementation from this spec", "generate the code skeleton", "materialize this architecture", "generic implementation please", or provides an agnostic structural specification (especially one following the 8-section project-isomorph template) and asks for implementation-ready code. Emit a strict 6-section markdown artefact (Assumptions → Generated folder structure → File contents → Adaptation points → Integration notes → Reintegration map) that another human or AI can drop into an empty repository and begin binding to private internals immediately. Every uncertain detail becomes a labelled `ADAPTATION POINT` / `USER-INTEGRATION REQUIRED` / `PROJECT-SPECIFIC IMPLEMENTATION GOES HERE` seam, never a hallucinated specific. Do NOT trigger for (a) refactoring or reviewing existing concrete code — use code review tools; (b) writing READMEs or onboarding docs — use doc-coauthoring; (c) decision records / ADRs — use decision-logger; (d) cases where the user already has the real code and wants it modified in place rather than rebuilt from an abstract spec.
license: Proprietary. OmarOS internal.
---

# Isomorph Synth — Generic Code from Agnostic Spec

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

This skill is the inverse of `project-isomorph`. That skill takes a private project and produces an 8-section, identifier-free dossier. This skill takes such a dossier — or any agnostic structural specification of similar rigour — and emits a generic, production-style, reintegrable implementation.

The roundtrip is intentional. Omar works on proprietary systems at work and in research; sharing code directly with an external model or forum is a leak surface. Isomorphing the project strips the leak. But if he then wants to ask an external model for a refactor, a fix, or a whole re-implementation, he needs code back. This skill closes the loop:

```
private project  ──[project-isomorph]──►  agnostic dossier
agnostic dossier ──[isomorph-synth]────►  generic scaffold
generic scaffold ──[manual rebinding]──►  private project (improved)
```

The generic scaffold is never a copy of the original. It is a fresh implementation that **shares the same architectural shape** (modules, components, data schemas, execution flow, integration points, invariants) and exposes **clean adaptation seams** where private internals must be bound later. A team-mate with access to the original can paste the scaffold into an empty folder, wire their proprietary adapters into the marked points, and have a working derivative within an afternoon.

## When this skill runs

Trigger whenever the user presents an agnostic structural specification (markdown, usually an 8-section dossier from `project-isomorph`, but any rigorous abstract description will do) and asks for:

- "synthesize code from this spec" / "generate a scaffold from this dossier"
- "rebuild from this spec" / "realize this dossier" / "materialize this architecture"
- "implement this specification" / "scaffold the project described here"
- "turn this isomorph into code" / "give me a starting implementation"
- an implicit follow-up to a `project-isomorph` run: the dossier is visible in context and the user now wants code

Do **not** trigger for:

- refactoring or reviewing existing concrete code — the user has real source in front of them.
- README / onboarding doc generation — `doc-coauthoring`.
- ADR / decision record — `decision-logger`.
- cases where the user wants the private code modified in place, not rebuilt from an abstract spec.

## Invariants (the reason this skill exists)

1. **Structural fidelity to the spec.** Every module, component, dataset, integration point, and invariant declared in the input appears in the output. Counts match. Interface shapes match. The execution flow is recognisable end-to-end.
2. **No invention of private material.** No made-up endpoint URLs, no fake API keys, no fabricated formulas, no hallucinated business rules. When the spec is silent on a detail, emit a labelled adaptation point — never a guess dressed up as fact.
3. **Generic by construction.** Placeholder content uses generic-but-semantic names (same discipline as `project-isomorph`): `PricingEngineComponent`, not `AcmePricer`; `Database_OperationalStore`, not `ops_prod_v2`.
4. **Reintegration-first design.** The generated code is optimized for later binding to private internals: clear interface seams, dependency injection, replaceable adapters, configuration-driven behaviour, isolated domain logic. One domain layer, one infrastructure layer, one configuration layer, one interface layer, unless the spec is genuinely too small to justify that much separation.
5. **Every uncertainty is explicit.** Use the labelled markers from `references/adaptation_markers.md`. Never bury an assumption in a comment; surface it in the Assumptions section or as a named adaptation point.
6. **Tests that exercise contracts, not ornamentation.** Tests verify the interface shape, the core data flow, and the placeholder contracts, so a downstream binding has something to regression-test against. No smoke tests of `1 + 1 == 2`.
7. **Output follows the 6-section contract.** The shape below is load-bearing — downstream tooling and the validator script rely on it.

## The 6-section output contract

The artefact is a single markdown document. Headings and ordering are fixed.

```
# 1. Assumptions
# 2. Generated folder structure
# 3. File contents
# 4. Adaptation points
# 5. Integration notes
# 6. Reintegration map
```

Read `references/generation_protocol.md` before writing — it is the authoritative specification for what belongs under each section, including field shapes, file-presentation convention, and adaptation-marker vocabulary.

## Procedure

Work in this order. Each step builds on the previous one; skipping ahead produces incoherent scaffolds.

### Step 1. Identify system purpose and stack

Read the input spec end-to-end before writing. Two questions first, before anything else:

- What **kind** of system is this? (data pipeline, pricing engine, async API client, UI dashboard, batch ETL, event-driven service, research toolkit, …) The spec's Section 1 (if it is a project-isomorph dossier) states this directly; if not, infer it from the described shape.
- What **stack** should the scaffold use? The spec may pin this (e.g. "Runtime_InterpretedDynamic"); if not, apply the heuristics in `references/stack_selection.md` and **state the assumption explicitly** in Section 1 of the output.

Do not begin generating until both are decided. A pricing engine scaffold written in TypeScript for a spec that clearly wants Python wastes the user's time.

### Step 2. Extract contracts and invariants

Walk the spec and list, in order:

- Every module (Section 3 of a project-isomorph dossier).
- Every component with its input/output signature (Section 4).
- Every data schema (Section 5).
- Every integration point (Section 7).
- Every invariant declared at module and component level.
- Every known-non-preservation item (Section 8) — these become explicit adaptation points.

This list becomes the bill of materials for the scaffold. Nothing extra, nothing missing.

### Step 3. Draft the folder structure

Lay out the tree top-down. Separate concerns by layer when the project is non-trivial: `domain/`, `infrastructure/`, `adapters/`, `config/`, `interfaces/` (or equivalent idiomatic names for the chosen stack). The scaffold should read as a clean, layered codebase from the first glance.

For each top-level module in the spec, create a corresponding package / directory. For each component, create a corresponding file or class. For each integration point, create a corresponding adapter. For each data schema, create a corresponding DTO / typed model.

### Step 4. Define interfaces before implementations

Write every public interface first: method signatures, typed parameters, typed returns. Only then fill in bodies. A body with a clean signature is easy to replace; a body tangled with ad-hoc types is not. This is the single biggest determinant of how reintegrable the scaffold is.

### Step 5. Fill in bodies with generic but coherent code

Provide meaningful generic implementations where the spec gives enough information:

- If the spec says "computes a closed-form valuation under a log-normal asset model", write a small plausible closed-form function (e.g. a vanilla Black–Scholes call in an options context) clearly labelled as a generic placeholder implementation, with the note that the private tuning must be re-bound.
- If the spec says "calibrates by Levenberg–Marquardt on a residuals objective", use `scipy.optimize.least_squares` with a generic residuals function.
- If the spec says "runs a Kalman filter update", implement one against a plausible generic state-space model.

The point is that the scaffold should **run end-to-end** on synthetic inputs — it's a testbed for binding private details, not a collection of `raise NotImplementedError`.

Where the spec is silent (or the private tuning is explicitly marked non-preserved), leave a clearly labelled adaptation seam. The taxonomy and labelling rules live in `references/adaptation_markers.md`.

### Step 6. Generate tests

Emit tests that verify the contracts, not the business logic:

- that every component's input/output interface matches the declared shape.
- that every adapter's public methods exist with the declared signatures.
- that every data schema round-trips through serialization.
- that the end-to-end pipeline runs on a synthetic input without crashing and produces the expected output shape.
- that every adaptation point's interface compiles (i.e. a stub that implements the interface can be plugged in).

Tests are in the scaffold's idiomatic test framework (pytest for Python, vitest/jest for TS, `go test` for Go, etc.).

### Step 7. Write the Assumptions and Reintegration Map

Assumptions go first in the output artefact; the Reintegration Map goes last. Assumptions are the explicit list of what the spec didn't pin down (stack version, concrete third-party library chosen for a role, storage backend chosen for a generic integration point, etc.). The Reintegration Map is the table of every adaptation point with three columns: what must be replaced, what private system or contract it binds to, what must remain true after binding.

### Step 8. Self-validate

Run the validator before returning:

```bash
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/isomorph-synth/scripts/validate_scaffold.py <output.md>
```

It checks: all 6 sections present in order; every file declared in Section 2 has content in Section 3; every adaptation point in Section 4 uses a recognised marker and appears in the Reintegration Map in Section 6; at least one test file is present. Treat warnings as drafting signals, not rubber stamps.

### Step 9. Return or materialize

Default: return the full markdown artefact inline. If the user asks for files on disk ("write the scaffold to `<path>`"), run:

```bash
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/isomorph-synth/scripts/materialize_scaffold.py <output.md> --out <path>
```

It parses the 6-section artefact, reconstructs the tree in Section 2, and writes every file from Section 3. The materializer refuses to overwrite existing non-empty files unless `--force` is passed — the reintegration target is typically an empty repository, and accidental overwrites there are expensive.

## Hard constraints

- **No verbatim code from any real source.** This skill only has access to the abstract spec; if you ever feel tempted to paste something "like what the real code must look like" based on guesses about the domain, stop and emit an adaptation point instead.
- **No fake secrets, endpoints, or credentials.** Ever. Not even as examples. Configuration placeholders are labelled `<configure locally>` or live in `.env.example` with generic names and empty values.
- **No mixed stacks.** If the spec implies Python, the scaffold is Python throughout, including tests and build tooling. Only split stacks when the spec explicitly describes a split (e.g. Python backend + TypeScript frontend).
- **No over-abstraction.** Interfaces exist where the spec says an integration point exists, not prophylactically. A YAGNI abstract factory for a single concrete class is a drag on reintegration.
- **No under-abstraction.** Where the spec declares an integration point, generate an explicit adapter behind an interface. "Just inline the call to external X" defeats the reintegration goal.
- **Adaptation markers are always labelled.** The taxonomy is `ADAPTATION POINT`, `USER-INTEGRATION REQUIRED`, `PROJECT-SPECIFIC IMPLEMENTATION GOES HERE`. Ad-hoc `TODO`s, `FIXME`s, or bare `NotImplementedError`s without a labelled marker are bugs.
- **Tests are real, not ornamental.** A test that always passes regardless of whether the contract is met is worse than no test.

## Adaptation markers — short cheat sheet

The full taxonomy lives in `references/adaptation_markers.md`; use that when in doubt. The three primary kinds:

| Marker | Meaning |
|--------|---------|
| `ADAPTATION POINT` | Interface is defined; an implementation will be supplied later by the user. The default when binding a private internal. |
| `USER-INTEGRATION REQUIRED` | A connection to an external system (API, broker, DB) whose concrete details must be bound by the user — typically paired with a generic adapter. |
| `PROJECT-SPECIFIC IMPLEMENTATION GOES HERE` | A function body / configuration block that will be substituted wholesale by the user's proprietary version. |

Every marker carries a short prose hint: what is expected, what the contract is, what the downstream binding should preserve.

## Stack inference — quick summary

See `references/stack_selection.md` for the full table. Quick defaults when the spec is silent:

- Data pipeline / batch ETL / numerical modelling → Python 3.11+, `uv`/`poetry`, `pytest`.
- Web UI / dashboard → TypeScript + React + Vite.
- Service layer / REST API → Python + FastAPI, or TypeScript + Fastify, mirroring the spec's async-ness.
- Numerical solver with heavy linear algebra → Python + NumPy/SciPy, noting that a faster implementation in Julia/Rust/C++ is possible and the scaffold is intentionally in the most adaptable stack.
- Event-driven / message broker consumer → Python + `aio-pika`/`confluent-kafka`, or TypeScript equivalent.
- LaTeX / research — the scaffold is the build pipeline (Python for figure generation + the LaTeX build), not the content.

State the assumption in the Assumptions section. The user can override by saying "use Go" or "do this in Rust".

## Bundled resources

- `references/generation_protocol.md` — authoritative 6-section output template. Read before writing the artefact.
- `references/adaptation_markers.md` — full taxonomy of labelled seams, how to emit them, and how they are picked up by the validator and the Reintegration Map.
- `references/stack_selection.md` — inference table: spec signals → chosen stack, with justification for each default.
- `references/examples.md` — one end-to-end worked example: an 8-section dossier input → a fully assembled 6-section scaffold output.
- `scripts/materialize_scaffold.py` — parses a 6-section artefact and writes the file tree from Section 2 / file contents from Section 3 to disk. Refuses to overwrite unless `--force`.
- `scripts/validate_scaffold.py` — validates a 6-section artefact: all sections present, declared files have contents, every adaptation marker appears in the Reintegration Map, tests are present.

## Cross-references

- Sibling: `project-isomorph` (forward direction — sensitive project → agnostic dossier). Most inputs to this skill are outputs of that one.
- Not `doc-coauthoring` (writes prose for humans, not scaffold code).
- Not `decision-logger` (records a single decision, not a re-implementation).
- Not `project-import` (imports a real project into OmarOS, does not synthesize from a spec).
- Portability note: the behavioural contract in this file is deliberately stack-agnostic and tool-agnostic, so the same specification can be adapted into a Copilot `.github/copilot-instructions.md` or a Cursor `.cursorrules` file if the user wants the same behaviour outside Claude Code.
