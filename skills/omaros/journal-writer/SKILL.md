---
name: journal-writer
description: Append to or create Omar's daily journal at 01_Daily_Life/Journal/Daily/YYYY-MM-DD.md. Use this skill when the user starts today's journal, adds a narrative entry, logs mood/energy/weather, links a decision or commit to today, or runs /daily. Trigger on phrases like "today I…", "note for today", "journal entry", "add to today's note", "diario de hoy", "escribe algo de hoy". Do NOT trigger for long-form reflections with no day anchor (use scholar), project status updates (project-reporter), or raw unclassified capture (capture skill). Never overwrites existing content; every edit is append-only and bumps the `updated` field.
license: Proprietary. OmarOS internal.
outputSchema:
  $ref: 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
  composes:
  - 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
contract_invariants:
- Writes to 01_Daily_Life/Journal/ under ISO-dated filenames.
- Never alters historical entries; only the day-anchored file is mutable.
---

# Journal Writer

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Owns the daily journal surface at `01_Daily_Life/Journal/Daily/YYYY-MM-DD.md`. One file per calendar day. Creation is from template only; subsequent edits are append-only by section. The canonical section order (Narrative, Tasks today, Decisions, Commits, Reflection prompts, Links) is load-bearing — downstream Dataview queries and the weekly reviewer address sections by heading.

## Quick reference

| User intent | Section / action |
|-------------|------------------|
| "today I figured out…" | `## Narrative` — append paragraph |
| "answer to reflection prompt N" | `## Reflection prompts` — inline under item N |
| "link the decision I just logged" | `## Decisions` — bullet with wikilink |
| "mood: calm" | frontmatter `mood:` (only if empty) |
| file does not exist | create from `assets/daily_template.md` |
| second entry same day | `### HH:MM` subheading in Narrative |

## When this skill runs

- `/daily` is invoked.
- User prose references a specific calendar day.
- Another skill requests a day-anchored append (e.g., `decision-logger` linking a new ADR).

Do **not** run for:

- Long-form reflection with no day anchor → `scholar`.
- Project status → `project-reporter`.
- Raw unclassified capture → `capture`.

## Inputs

| Input | Required | Source |
|-------|:--------:|--------|
| target date | ✅ | caller; default = today |
| content kind | ✅ | narrative / decision-link / commit-link / task-mention / reflection-answer / frontmatter-field |
| content payload | ✅ | caller |

## Outputs

| Artefact | Path |
|----------|------|
| daily note | `01_Daily_Life/Journal/Daily/YYYY-MM-DD.md` |

Return payload:

```
file: <path>
action: created_from_template | appended_to_narrative | appended_to_decisions | …
sections_touched: [<names>]
frontmatter_changes: [<fields>]
```

## Procedure

### Step 1 — Resolve date

Default to today. If the user's phrasing is ambiguous (e.g. "last night", "early this morning") and the wall-clock day differs from the subjective day, ask once.

### Step 2 — Create or open

Read target file.
- **Missing:** run `python3 scripts/new_daily.py [YYYY-MM-DD]`. It copies `assets/daily_template.md`, substitutes `{{date}}` and `{{weekly}}`, writes the file, and prints the absolute path. Idempotent: safe to run if the file already exists (no-op).
- **Present:** proceed to Step 3.

### Step 3 — Route to section

Apply the Quick reference table. Diff-safe patterns per section in `references/append_patterns.md`.

### Step 4 — Bump frontmatter

- `updated` ← local ISO datetime, strictly ≥ prior value.
- `mood` / `energy` / `weather` ← set only if user supplied AND field currently empty.
- Never remove a field or a tag.

### Step 5 — Emit report payload

Per §Outputs.

## Constraints

- **CRITICAL:** never overwrite existing content; append only.
- **CRITICAL:** one file per calendar day.
- **CRITICAL:** section heading names are load-bearing; do not rename.
- Privacy: do not pull content from `13_Health/` or `16_Relationships_and_People/` unless user explicitly asks this turn.
- Frontmatter must validate against the current owner schema and central project profile.

## Reference

- [`scripts/new_daily.py`](scripts/new_daily.py) — idempotent daily-note scaffolder; CLI takes optional `YYYY-MM-DD` (default today), prints the resulting path.
- [`references/frontmatter.md`](references/frontmatter.md) — required fields, enums, enforcement.
- [`references/append_patterns.md`](references/append_patterns.md) — diff-safe patterns per section.

## Dependencies

- Template: `18_Templates/Daily_Notes/_template.md` (mirrored in `assets/`).
- Validate the current project metadata schema and record the check in the assignment.
- Sibling skills: `scholar`, `decision-logger`, `project-reporter`.
- Schema: `19_Metadata_and_Schema/Frontmatter_Standards/`.

## Cross-references

- Weekly review (future, capa 2): `weekly-reviewer`.
- Routing doctrine: `CLAUDE.md` §7.
