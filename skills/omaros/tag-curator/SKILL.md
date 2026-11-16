---
name: tag-curator
description: Finalise the frontmatter of any vault note after it has been written — fill missing fields, validate enum values, normalise tags, verify wikilinks, and inject the traceability block. Use this skill whenever the user says "fix the tags on this note", "finalise frontmatter", "add metadata to this note", "clean up the YAML header", "update tags", "stamp the trace block", "arregla los tags", "el frontmatter está incompleto", or when any writer skill completes and needs its output certified. Never touches note bodies — only the YAML frontmatter. Do NOT trigger for writing note content (writer skills), for full vault-wide governance audits (governance-auditor), or for schema enum changes (those require an explicit schema-change scope first).
license: Proprietary. OmarOS internal.
outputSchema:
  $ref: 19_Metadata_and_Schema/Agent_Output_Schemas/pipeline_response.json
  composes:
  - 19_Metadata_and_Schema/Agent_Output_Schemas/pipeline_response.json
contract_invariants:
- Finalises frontmatter and writes the trace block before task closure.
- Never invents enum values; refers to 19_Metadata_and_Schema/ for every field.
---

# Tag Curator

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Use this method when a note requires metadata validation. Its job: make the frontmatter complete, schema-compliant, and carrying a record of its own provenance.

The key insight is that a note's frontmatter is not just decoration — it is the control plane that lets Dataview queries, the MOC system, and future agents understand the note's role, status, and history. A note with a broken or empty frontmatter is an orphan; a note with a correct frontmatter is a first-class citizen of the knowledge graph.

## Quick reference

| Situation | Action |
|-----------|--------|
| Missing `domain` / `subdomain` | fill from placement record |
| Missing `note_type` | infer from specialist writer + domain |
| Missing `status` | default to `draft` |
| Missing `created` | use file mtime |
| Pipeline-written note | set `ai_generated: true`, `ai_reviewed: false` |
| Invalid enum value | flag as blocking error; do not invent values |
| Unregistered topical tag | warn and leave empty rather than guess |
| Unresolved `[[wikilink]]` | add to `trace.forward_links`; do NOT remove the link |
| All checks pass | inject `trace:` block, bump `updated:` |

## When this skill runs

- A requested note edit needs frontmatter validation under the current vault schema.
- User asks to fix, validate, or complete the frontmatter of an existing note.
- `/governance-audit` triggers a bulk frontmatter repair sweep.

Do **not** run for:

- Writing or editing note bodies → specialist writer skills.
- Vault-wide structural audits → `governance-auditor`.
- Adding new values to a schema enum → requires editing `19_Metadata_and_Schema/` files first, then re-running this skill.

## Inputs

| Input | Required | Notes |
|-------|:--------:|-------|
| note path | ✅ | the note to finalise |
| placement record | optional | from the current placement decision (domain, subdomain, note_type) |
| style envelope | optional | from style-writer (register, voice) |
| writer identity | optional | which specialist wrote the note |

## Procedure

### Step 1 — Read the frontmatter

Read the note. Parse its YAML frontmatter. Identify missing mandatory fields and check every present field against its enum.

### Step 2 — Fill missing fields

Use the placement record and style envelope as the source of truth:
- `domain`, `subdomain` ← from placement, or infer from note path.
- `note_type` ← from placement record; must be a registered enum value.
- `status: draft` if not set.
- `created:` ← file mtime if missing; never overwrite an existing value.
- `ai_generated: true`, `ai_reviewed: false` for any note written through the pipeline.

### Step 3 — Validate enums

Every enum field (`status`, `note_type`, `priority`, `confidence`) must match a value in `19_Metadata_and_Schema/Status_Enums/` and `19_Metadata_and_Schema/Frontmatter_Standards/`. A value not in the enum is a **blocking error** — set `status: blocked` and log to the investigation log rather than silently coercing it.

### Step 4 — Normalise tags

Two categories:
- **Structural tag** (one per note): `moc`, `evergreen`, `log`, `capture`, `reflection`, `decision`, `task`, `report`, `dashboard`, `template`, `schema`, `governance`.
- **Topical tags**: normalise to `snake_case`; accept only tags registered in `19_Metadata_and_Schema/Tag_Conventions.md`.

Never invent tags. If a legitimate topical concept has no registered tag, surface a warning and leave the field incomplete rather than adding an unregistered value.

### Step 5 — Verify wikilinks

Walk every `[[wikilink]]` in the body. For each link:
- Resolves to an existing file → mark resolved.
- No matching file → add to `trace.forward_links`; do NOT remove the link (the target may be created later).

### Step 6 — Record actual provenance

Use the current vault schema for provenance fields. Record the actual source,
assigned author and unresolved forward links where the schema requires them.
Never invent a pipeline ID, classification, agent or review status. Reuse the
current assignment's evidence and reference; do not create a second execution
registry inside a note. Preserve existing historical provenance.

### Step 7 — Bump `updated:`

Set `updated:` to the current ISO datetime. Preserve `created:` unchanged.

### Step 8 — Write

Write the updated frontmatter block back to the file. The note body is untouched.

## Constraints

- **Never mutate the note body** — only the YAML frontmatter block.
- **Never downgrade `status`** — only the writer or an explicit state-transition command can reduce status (e.g., active → draft). This preserves the integrity of lifecycle tracking.
- Blocking errors result in `status: blocked` + investigation log entry. The pre-commit gate will reject the note until a human resolves it.

## Dependencies

- Schema: `19_Metadata_and_Schema/Frontmatter_Standards/`, `19_Metadata_and_Schema/Status_Enums/`, `19_Metadata_and_Schema/Tag_Conventions.md`.
- The central project profile defines the metadata checks required before publication.
- Sibling skills: all writer skills are upstream; `governance-auditor` uses this skill in bulk repair mode.
