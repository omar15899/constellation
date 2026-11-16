---
name: project-isomorph
description: Transform any private, proprietary, or sensitive project (codebase, folder, scripts, pipelines, data flows, research code) into a mathematically precise, structurally isomorphic, but semantically anonymized dossier — so the user can share it, reason about it with an external model, or hand it to a downstream AI to rebuild an equivalent system, without leaking identifiers, business logic, formulas, endpoints, column names, schemas, or credentials. Use this skill whenever the user says "abstract this project", "anonymize my codebase", "make an agnostic version of this repo", "extract a blueprint", "privacy-safe spec of this project", "isomorphic representation", "shareable structural summary", "turn this proprietary code into something I can post online", "describe this system without revealing the names", "convert to agnostic spec", "structurally faithful but redacted", "sanitize for external sharing", "what would this look like with the names stripped out", or presents any project/directory and asks to document it in a way that strips identifiers while preserving architecture. Output is a strict 8-section markdown dossier (overview → architecture graph → module structure → component specs → data schemas → execution flow → integration points → reconstructability notes) with every real name replaced by semantically meaningful but generic placeholders, every algorithm abstracted to its class (regression / Monte Carlo / PDE solver / event loop / cache layer / etc.), every formula replaced by its type-level role, but every interface signature, shape, constraint, dependency edge, and invariant preserved exactly — so the spec is plug-and-play generative-compatible and a downstream AI can rebuild a behaviourally equivalent system from the dossier alone. Do NOT trigger for (a) ordinary code review — use code-review tooling; (b) README or onboarding doc generation that keeps real names — use doc-coauthoring; (c) git-diff state reports — use repo-reporter; (d) AI-setup audits of `.claude/` — use ai-setup-inspector; (e) cases where the user explicitly wants to preserve real names for their own internal documentation.
license: Proprietary. OmarOS internal.
---

# Project Isomorph — Lossy-Secure Structural Representation

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Omar often needs to share a project with something (or someone) that must not see its real names, formulas, endpoints, or business logic — a public LLM, a forum, a collaborator under NDA mismatch, a write-up that will be published. The intuition most people reach for is "summarise it", but a summary is **not reconstructable** — it loses the skeleton that makes the system a system. A diagram is not enough either: it loses type information.

This skill produces a third thing: a **lossy-secure isomorphism**. Structure is kept down to the level of type signatures, shapes, and dependency edges. Identifiers are rewritten to generic-but-semantic placeholders. Formulas are reduced to their algorithmic class. A downstream AI, given only the dossier, should be able to stand up a behaviourally equivalent system without ever seeing the original.

Two simultaneous goals:

- **Maximize reconstructability.** Every interface, every shape, every invariant, every data-flow edge is preserved exactly. Two systems that produce the same dossier are structurally indistinguishable.
- **Maximize redaction.** Every identifier, every formula, every credential, every unique endpoint is gone. Given only the dossier, nothing in the original can be uniquely recovered.

Think of it as a **de Bruijn index for whole projects**: the graph and types are kept, the labels are renamed to canonical, content-free tokens.

## When this skill runs

Trigger whenever the user presents a project, directory, or code artefact and asks for anonymization, abstraction, blueprint extraction, or a shareable representation. Typical phrasings:

- "abstract this project", "anonymize my codebase"
- "make an agnostic version of this for ChatGPT"
- "I want to ask online about the design but I can't leak the real names"
- "privacy-safe spec", "isomorphic representation", "structural blueprint"
- "sanitize this for external sharing"
- presentation of a folder + request to "describe it without the specifics"

Do **not** trigger for:

- Ordinary code review or refactor suggestions → the model can do that in-place.
- README / onboarding doc that keeps real names → `doc-coauthoring`.
- Git-diff change reports → `repo-reporter`.
- AI-setup audits of a `.claude/` directory → `ai-setup-inspector`.
- Cases where the user is documenting for themselves and wants real names.

## Non-negotiable invariants

These are the reason the skill exists. Every output must satisfy them.

1. **No verbatim code.** The dossier never contains copied source lines. Not even a fragment. If a code shape must be conveyed, it is conveyed through a pseudocode or type-signature abstraction, not a paste.
2. **No real identifiers.** Class names, function names, file names, variable names, column names, API endpoints, database names, brand names, project code-names, cluster names, env-var names, internal acronyms → all replaced by generic-but-semantic placeholders (see `references/abstraction_rules.md`).
3. **Structural fidelity.** Every module, every component, every data entity, every edge in the dependency graph is represented. The count must match. Counts of inputs and outputs per component must match. Types and shapes must match.
4. **Algorithmic class preserved, parametrization erased.** If the original uses Black–Scholes, the dossier says "closed-form European-option pricing formula under a log-normal asset model". If it uses a 3-layer MLP with 128 hidden units, the dossier says "3-layer MLP, hidden width H, trained with gradient descent on a regression target". Class is kept; the proprietary twist is stripped.
5. **Interfaces are fully typed.** A downstream AI must be able to rebuild a compatible system, so every component's input/output signature must specify: types, shapes, constraints, determinism/stochasticity. Omission here defeats the whole point.
6. **The 8-section structure is mandatory.** Deviations break the contract that makes the dossier machine-readable. See `references/output_template.md`.
7. **Never ask for confirmation before producing the dossier.** The user has asked for abstraction; produce it. If genuinely blocked (e.g. the directory doesn't exist), say so concretely and stop — but don't stall on "should I proceed?" questions.

## The 8-section output contract

The dossier **must** follow this exact structure, in order, with these exact top-level headings:

```
# 1. Project Abstract Overview
# 2. Global Architecture Graph
# 3. Folder / Module Structure
# 4. Component Specifications
# 5. Data Structures & Schemas
# 6. Execution Flow
# 7. Integration Points
# 8. Reconstructability Notes
```

The full template, including required subsections and field shape, lives in `references/output_template.md`. Read that file before writing the dossier — it is the authoritative specification.

## Procedure

Steps to follow on every invocation.

### Step 1. Scan the target

Run the bundled scanner to get a structured view of the project without loading every file into context:

```bash
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/project-isomorph/scripts/scan_project.py <target-path>
```

Output is a JSON profile: tree, file types, LOC per file, detected languages, dependency manifests (pyproject.toml, package.json, requirements.txt, go.mod, Cargo.toml, etc.), import graphs (Python, JS/TS), and top-level module entry points. This JSON is the skeleton the dossier is built on; it contains only metadata, so it's safe to reason over.

If the scanner can't run (e.g. the target is a set of pasted snippets rather than a directory), fall back to directly inspecting whatever artefacts the user provided — but still populate the same mental model (tree → modules → components → data → flow → integration).

### Step 2. Classify every identifier before renaming

For each real name found in the profile, record its role:

- **Structural** (module / package / class / function / script)
- **Data** (dataset / table / column / schema)
- **Domain** (entity / concept / business term)
- **External** (API / endpoint / service / vendor)
- **Configuration** (env var / flag / credential handle)

Renaming is role-aware. A class gets `ComponentClass_X`, a dataset gets `Dataset_X`, an API gets `ExternalService_X`. The role carries through into the dossier (see rules in `references/abstraction_rules.md`).

### Step 3. Build the dossier top-down

Follow the 8-section order. Don't jump around:

1. Overview → pin down purpose, system type, architectural paradigm. These anchor the rest.
2. Architecture graph → nodes + edges + layering. This is the skeleton.
3. Module structure → for each folder, emit role + deps + interfaces + invariants.
4. Component specs → for each component in each module, full IO signature + abstracted internal logic + side effects.
5. Data schemas → every dataset, table, or message schema, columns replaced by role-labelled placeholders.
6. Execution flow → walk the pipeline end-to-end.
7. Integration points → external systems, abstracted.
8. Reconstructability notes → the explicit "what you'd need to rebuild this" section — the most important section for a downstream AI.

### Step 4. Self-verify before returning

Run the validator against the draft dossier:

```bash
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/project-isomorph/scripts/validate_output.py <dossier.md>
```

It checks: all 8 sections present in order, no obvious raw identifiers leaked (heuristic — flags camelCase/snake_case tokens that look like real names), every component has a full IO signature, every module lists deps and invariants, code fences are empty of real source. Treat its complaints as a prompt to rewrite, not as a rubber stamp.

### Step 5. Return the dossier

Emit the full markdown. Default return is inline; if the user requested a file, write to the path they specified or to `11_Documents_and_Reports/Project_Isomorphs/<generic-slug>.md` inside the vault. Never write under the target project's tree.

## Abstraction rules (the renaming map)

A summary of the renaming conventions — the full decision tree lives in `references/abstraction_rules.md`.

| Real kind | Generic placeholder shape | Examples |
|-----------|---------------------------|----------|
| Module / package | `Module_<Role>` | `Module_Ingestion`, `Module_Pricing`, `Module_Reporting` |
| Class | `<Role>Component` | `PricingEngineComponent`, `CalibrationServiceComponent` |
| Function / method | `<verb>_<object_role>` | `transform_raw_inputs`, `calibrate_model_parameters` |
| Dataset / table | `Dataset_<Role>` | `Dataset_RawInputs`, `Dataset_CalibratedParameters` |
| Column | `col_<role>` | `col_timestamp`, `col_identifier`, `col_numeric_measure` |
| External API | `ExternalService_<Role>` | `ExternalService_MarketDataVendor`, `ExternalService_PaymentProcessor` |
| Endpoint | `/api/<generic-resource>` | `/api/resources`, `/api/resources/{resource_id}/events` |
| Database | `Database_<Role>` | `Database_OperationalStore`, `Database_AnalyticsWarehouse` |
| Env var / secret | `ENV_<ROLE>` | `ENV_API_KEY_MARKETDATA`, `ENV_DB_CONNECTION_STRING` |
| Algorithm | class-only | "closed-form option pricing under a log-normal model", "stochastic gradient descent on MSE", "LU-decomposition-based linear solve" |

Role tokens (`<Role>`) should be semantically meaningful. A class that computes VaR becomes `RiskMetricComponent`, not `ClassX`. The dossier must still read as a coherent system — just one whose specifics are gone.

## Hard constraints

- **No code, ever.** If a transformation needs explanation, use English + type signatures. A pseudocode block is acceptable when it clarifies data flow; a literal code paste is not.
- **Numerical values are abstracted.** `timeout=30` becomes `timeout=T_seconds`. `batch_size=128` becomes `batch_size=B`. `learning_rate=0.001` becomes `learning_rate=η`. Preserving the numeric class (int/float/bounded) matters; preserving the specific tuning does not and often leaks.
- **Error strings, log messages, comments — all redacted.** They are the most common leak vectors. A log message like `"failed to fetch prices for ticker {symbol}"` exposes the business domain; replace with `"failed to fetch <input-record> for <record-identifier>"`.
- **File paths are redacted.** `/opt/pricing_engine/src/bs_pricer.py` → `<root>/<pricing_module>/<option_pricing_script>`.
- **Preserve cardinality precisely.** If the real project has 14 modules, the dossier has 14 modules. Not 12, not "approximately 14", not "several".
- **Interfaces are not optional.** Every component spec must include input signature (types, shape, constraints) and output signature (types, shape, determinism). Missing these destroys reconstructability.
- **The dossier is a single file.** Do not split it across files. Internal references with `#section-N` links are fine.

## Edge cases

- **User pastes a code snippet instead of a directory.** Treat the snippet as a 1-component project. Build a minimal dossier. Section 3 (module structure) will have one entry; that's fine.
- **Project is primarily non-code (LaTeX, data, docs).** Same rules apply. Modules become document/data clusters. Components become chapters, scripts, pipelines. Schemas still apply to the underlying data.
- **Project mixes languages.** The module structure reflects that. Components carry a `Runtime` field (see template) naming the execution platform abstractly (`Runtime_InterpretedDynamic`, `Runtime_CompiledStatic`, `Runtime_Managed`) rather than the specific language when the language itself is business-identifying.
- **Ambiguous whether a name is business-sensitive.** Err toward redaction. A downstream AI doesn't need the real name to reconstruct; Omar doesn't want to leak it. Redact.
- **Component uses a well-known public library.** The library's existence can be named generically (`dependency on an HTTP client`, `dependency on a DataFrame library`) — do not name the specific library when it correlates with the internal architecture in a recognisable way. When in doubt, abstract.

## Bundled resources

- `references/output_template.md` — the authoritative 8-section template with required subsections, field types, and example shapes for each entry kind. **Read before writing.**
- `references/abstraction_rules.md` — full decision tree for renaming: role classification, placeholder derivation, collision resolution, table of canonical tokens.
- `references/examples.md` — two worked input→output examples (a small Python pricing pipeline, a mixed research project) to anchor the style.
- `scripts/scan_project.py` — walks a target directory and emits a JSON topology (file tree, LOC, languages detected, dependency manifests parsed, Python import graph, top-level entry points). Safe to run on any directory; never writes into the target.
- `scripts/validate_output.py` — validates a produced dossier: checks all 8 sections present in order, IO signatures present, no leaked camelCase/snake_case tokens that look like real identifiers, no code fences with source content.

## Cross-references

- Sibling skills: `ai-setup-inspector` (audits `.claude/` maturity, complementary — an audit describes the setup; this skill abstracts the whole project). `repo-reporter` (git-diff state reports, orthogonal).
