---
name: work-scribe
description: Write work-context artefacts in OmarOS 03_Work/ — meeting notes, narrow work decisions, weekly work summaries. Use this skill when the user says "meeting note", "write up the meeting", "record the meeting with X", "reunión con…", "notas de la reunión", "work log", "semana laboral", "summary of this week at work", or describes a work event with attendees, agenda, or action items. Forwards action items to task-marshal with the meeting as parent. Keeps work-sensitive content scoped to 03_Work/; never leaks to 01_Daily_Life/ or public-facing dashboards. Do NOT trigger for cross-meeting architectural decisions (decision-logger), long-form work reflections (scholar), or work-project status (project-reporter).
license: Proprietary. OmarOS internal.
outputSchema:
  $ref: 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
  composes:
  - 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
contract_invariants:
- Writes only inside 03_Work/ and never leaks work-sensitive content outside that domain.
- Forwards action items to task-marshal with the meeting note as parent.
---

# Work Scribe

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Owns `03_Work/`. The work domain is separated from personal life because its artefacts have different privacy properties, retention, and audiences. This skill writes meeting notes, narrow meeting-scoped decisions, and weekly work rollups. Long-form reflection routes to `scholar`; architectural work decisions route to `decision-logger`; task CRUD to `task-marshal`.

## Quick reference

| User intent | Artefact |
|-------------|----------|
| "meeting with X on Y" | `03_Work/Meetings/YYYY-MM-DD_<slug>.md` |
| "decided in the meeting to Z" | `03_Work/Decisions/YYYY-MM-DD_<slug>.md` (narrow); escalate to `decision-logger` if architectural |
| "week summary" | `03_Work/Weekly/YYYY-Www.md` |
| "action item from meeting" | forward to `task-marshal` with `parent_meeting:` set |

## When this skill runs

- User describes a scheduled conversation with named attendees.
- User articulates a work-scoped decision.
- User asks for weekly work summary.

Do **not** run for:

- Personal meetings (friends, family) → `journal-writer`.
- Cross-meeting architectural decision → `decision-logger`.
- Long-form reflection on a work topic → `scholar`.
- Work-project status rollup → `project-reporter`.

## Inputs

| Input | Required | Kind |
|-------|:--------:|------|
| date | ✅ | ISO |
| attendees | ✅ (meetings) | list of names + roles |
| agenda | ✅ (meetings) | list |
| discussion | ✅ (meetings) | prose per topic |
| decisions | optional | inline references |
| action items | optional | each forwarded to task-marshal |
| employer / project scope | optional | slugs |

## Outputs

| Artefact | Path |
|----------|------|
| meeting | `03_Work/Meetings/YYYY-MM-DD_<slug>.md` |
| work decision | `03_Work/Decisions/YYYY-MM-DD_<slug>.md` |
| weekly summary | `03_Work/Weekly/YYYY-Www.md` |
| forwarded tasks | `02_Tasks_and_Execution/Backlog/<slug>.md` via `task-marshal` |

Return:

```
artefact: <path>
kind: meeting | work_decision | weekly_summary
attendees: [...]
decisions_extracted: [...]
action_items_forwarded: <int>
```

## Procedure

### Step 1 — Classify

`meeting` / `work_decision` / `weekly_summary`.

### Step 2a — Meeting note

1. Capture attendees (name + role); ask once if unknown.
2. Record agenda items; they structure the body.
3. Discussion section is prose per topic, not verbatim.
4. For each decision extracted: narrow → `03_Work/Decisions/`; architectural → escalate to `decision-logger`.
5. For each action item: invoke `task-marshal` with `parent_meeting: <path>`. Replace inline item with wikilink to created task.

### Step 2b — Work decision

Mirror of `decision-logger` but scoped to work, with simpler body (context, options, decision, reversibility). For wide-scope: escalate to `decision-logger`.

### Step 2c — Weekly summary

1. Glob `Meetings/YYYY-MM-??.md` for the ISO week.
2. Cite each meeting: one-line summary + wikilink. Do not duplicate content.
3. Aggregate: decision count, action items opened/closed (from task-marshal).
4. End with 3-5 "what moved" bullets.

### Step 3 — Emit report payload

## Constraints

- **CRITICAL:** work-sensitive content never leaves `03_Work/`. No attendee names in public dashboards.
- **CRITICAL:** every meeting has named attendees. A meeting without attendees is a personal note.
- **CRITICAL:** every action item forwarded to `task-marshal`. No floating action items.
- Weekly summaries compress, not duplicate.
- Salary, performance reviews, hiring deliberations never appear in weekly summaries or any dashboard.

## Reference

Meeting frontmatter:

```yaml
---
title: "<meeting topic>"
note_type: meeting
date: YYYY-MM-DD
attendees: [<name>, …]
employer: <slug or null>
project: <slug or null>
agenda: [<…>]
decisions: [<wikilinks>]
action_items_count: <int>
status: completed | cancelled
tags: [meeting, work, <area>]
---
```

## Dependencies

- Sibling skills: `task-marshal`, `decision-logger`, `project-reporter`, `scholar`.
- Template: `18_Templates/Meetings/_template.md`.
- Dashboards: `17_Dashboards/Work/Weekly.md`.

## Cross-references

- Privacy rules: `CLAUDE.md` §12 (high-risk: attendee leakage).
