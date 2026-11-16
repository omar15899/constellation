---
name: decision-logger
description: Write Architecture Decision Records (ADRs) for OmarOS in 20_System_Governance/Decisions/. Use this skill when the user says "log this decision", "add an ADR", "decide X", "record that we're going to Y", "decidí X", "registra esta decisión", or invokes /decision. Also trigger when the user articulates a non-trivial architectural, policy, tooling, or methodological choice whose rationale must persist. Every ADR is append-only, carries explicit reversibility, cross-links to the project/policy/system it affects. Do NOT trigger for personal/life decisions (those go to 01_Daily_Life/Decisions/ via scholar), task CRUD (task-marshal), project status (project-reporter), or daily journal entries (journal-writer).
license: Proprietary. OmarOS internal.
outputSchema:
  $ref: 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
  composes:
  - 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
contract_invariants:
- ADRs are append-only; an accepted decision is superseded by a new ADR, never rewritten.
- Every ADR states its reversibility and cross-links the project, policy, or system it affects.
---

# Decision Logger

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Owns the ADR pattern across OmarOS. Every load-bearing architectural, policy, methodological, or tooling decision becomes a dated, cross-linked markdown file under `20_System_Governance/Decisions/`. ADRs are historical records — their content is never edited except for lifecycle frontmatter (`status`, `superseded_by`). Supersession preserves history: the old ADR is marked `superseded`, never deleted or rewritten.

## Quick reference

| User intent | Action |
|-------------|--------|
| "log a decision" (reversible) | new ADR, `reversibility: reversible` |
| "log an irreversible decision" | confirm with user first; then `reversibility: irreversible` |
| "supersede ADR X with Y" | write Y with `supersedes: [X path]`; update X's frontmatter `status: superseded`, `superseded_by: Y path` |
| "reverse decision X" | update X's frontmatter `status: reversed`; write new ADR with rationale |

## When this skill runs

- `/decision` invoked.
- User articulates a non-trivial choice with rationale and alternatives.
- Another skill needs to formalise a choice (orchestrator selecting routing policy, etc.).

Do **not** run for:

- Personal/life decisions → `scholar` (destination `01_Daily_Life/Decisions/`).
- Task state changes → `task-marshal`.
- Project status updates → `project-reporter`.
- Transient execution choices without durability → leave in session log.

## Inputs

| Input | Required | Source |
|-------|:--------:|--------|
| context | ✅ | user: what prompted the decision |
| options considered | ✅ | user: at least 2 alternatives |
| chosen option | ✅ | user |
| rationale | ✅ | user: why chosen over alternatives |
| reversibility | ✅ | reversible / hard_to_reverse / irreversible |
| affects | ✅ | list of projects/policies/systems |
| supersedes | optional | list of prior ADR paths |

## Outputs

| Artefact | Path |
|----------|------|
| new ADR | `20_System_Governance/Decisions/YYYY-MM-DD_<slug>.md` |
| updated prior ADRs (supersession) | their existing paths, frontmatter only |
| cross-link updates | in `05_Projects/<X>/Decisions.md` or affected policy notes |

Return:

```
file: <path>
reversibility: <level>
supersedes: [...]
cross_links_written: [...]
```

## Procedure

### Step 1 — Gather the five mandatory fields

Context, options considered (≥2), chosen option, rationale, reversibility, affects. If any missing, ask one focused question before writing.

### Step 2 — Confirm irreversibility

If `reversibility: irreversible`, confirm with the user explicitly. Per `CLAUDE.md` §12, irreversible is high-risk.

### Step 3 — Scaffold the ADR

Pipe a JSON payload to `scripts/new_adr.py`:

```bash
echo '{"title": "...", "slug": "...", "reversibility": "reversible", "affects": ["..."]}' \
  | python3 scripts/new_adr.py
```

The script writes `20_System_Governance/Decisions/YYYY-MM-DD_<slug>.md` with valid frontmatter and the canonical section skeleton (Context, Options considered, Decision, Rationale, Reversibility, Consequences, References). Prints the absolute path. Refuses to overwrite existing files.

Then fill the section content substantively — the script only writes the skeleton.

Slug: ASCII snake_case, ≤60 chars.

### Step 4 — Handle supersession

For each prior ADR in `supersedes`:
- Update frontmatter only: `status: superseded`, `superseded_by: <new path>`, `updated: <today>`.
- **CRITICAL:** preserve the body byte-exact.

### Step 5 — Cross-link to targets

For each entry in `affects:`:
- Project → bullet in `05_Projects/<X>/Decisions.md` (create if missing).
- Policy → reference in the policy note.
- System → reference in system doc.

### Step 6 — Emit report payload

## Constraints

- **CRITICAL:** append-only. ADR bodies never change after creation except for `## Resolution` / supersession footnote.
- **CRITICAL:** every ADR carries explicit `reversibility`. No default.
- **CRITICAL:** alternatives captured. A decision with no alternatives is an assertion, not a decision — reject or ask.
- Every decision cross-links to its target. Floating ADRs are defects.
- Irreversible decisions require explicit user confirmation in the same turn.

## Reference

Frontmatter schema (required fields):

```yaml
---
title: "<title>"
note_type: decision_log
status: active | superseded | reversed
reversibility: reversible | hard_to_reverse | irreversible
decided_at: YYYY-MM-DD
decided_by: Omar
affects: [<…>]
supersedes: []
superseded_by: null
tags: [decision, <area>]
created: YYYY-MM-DD
updated: YYYY-MM-DD
author: Omar
---
```

## Scripts

- [`scripts/new_adr.py`](scripts/new_adr.py) — scaffolds a canonical ADR from a JSON payload on stdin. Validates reversibility enum, refuses overwrites, prints target path.

## Dependencies

- Template: `18_Templates/Decision_Logs/_template.md`.
- Validate the current project metadata schema and record the check in the assignment.
- Sibling skills: `scholar` (personal decisions), `project-reporter`, `task-marshal`.
- Policy: `CLAUDE.md` §12 (risk classification).

## Cross-references

- Related policies under `20_System_Governance/Policies/` — ADRs often implement or amend them.
