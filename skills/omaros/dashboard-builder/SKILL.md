---
name: dashboard-builder
description: Build and refresh the Obsidian dashboards in 17_Dashboards/ — maintaining the Home dashboard as the vault entry point and per-area dashboards for Daily, Weekly, Research, Projects, AI, Finance, Health, System, Review, and Work. Use this skill when the user invokes /dashboard, says "refresh the dashboard", "rebuild the Home dashboard", "update the research dashboard", "the dashboard is stale", "add a Dataview query to the dashboard", "actualiza el dashboard", "reconstruye el panel", or when a significant batch of new notes has been added and the dashboards need updating. Writes Dataview queries stored in 19_Metadata_and_Schema/Dataview_Queries/ and embeds them into dashboard notes. Dashboards are read-only views — they never create, move, or modify vault notes. Do NOT trigger for building MOCs (knowledge-indexer), for refreshing Index.md (index-maintainer), or for writing vault content notes (writer skills). The /dashboard command is the canonical entrypoint.
license: Proprietary. OmarOS internal.
---

# Dashboard Builder

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Dashboards are the operational surface of the vault — live views that answer "what's active right now?" without requiring manual curation. They work because of Dataview: queries embedded in markdown files that Obsidian evaluates against the vault's frontmatter at render time.

The builder's job is to keep those queries correct, the dashboard structure coherent, and the `Home.md` entry point up to date. It never moves or writes content notes — it only writes the viewing layer.

## Dashboard catalogue

| Dashboard | File | What it shows |
|-----------|------|---------------|
| Home | `17_Dashboards/Home/Home.md` | Links to all sub-dashboards; today's date; open task count |
| Daily | `17_Dashboards/Daily/Daily.md` | Today's journal, captures, tasks due today |
| Weekly | `17_Dashboards/Weekly/Weekly.md` | Week's commits, open tasks, reflection prompts |
| Research | `17_Dashboards/Research/Research.md` | Active research notes, `latex_pending: true` backlog |
| Projects | `17_Dashboards/Projects/Projects.md` | Active projects, blockers, recent logs |
| AI | `17_Dashboards/AI/AI.md` | Recent agent runs, hook health, prompt library stats |
| Finance | `17_Dashboards/Finance/Finance.md` | Active budget items, recent expense notes |
| Health | `17_Dashboards/Health/Health.md` | Recent health notes, training logs |
| System | `17_Dashboards/System/System.md` | Sync status, device inventory, NAS state |
| Review | `17_Dashboards/Review/Review.md` | Notes `ai_reviewed: false`, orphan notes |
| Work | `17_Dashboards/Work/Work.md` | Active work items, recent meetings, decisions |

## Query storage

Dataview queries are stored in `19_Metadata_and_Schema/Dataview_Queries/<dashboard>.md` and embedded into dashboard files with `![[query_file]]` transclusion. This separates the query logic (editable) from the dashboard layout (stable).

## Procedure

### Step 1 — Assess what needs updating

On a full `/dashboard` refresh: update all dashboards. On a targeted request: update only the specified dashboard(s).

### Step 2 — Update Dataview queries

For each dashboard being refreshed:
1. Read the existing query file from `19_Metadata_and_Schema/Dataview_Queries/`.
2. Check that the query's filter fields match the current schema enums (status, note_type, domain).
3. Update the query if the schema has changed; preserve the sort and render logic.
4. Always comment the query with its filter and sort logic:

```dataviewjs
// Research dashboard: active notes with latex_pending, sorted by updated
dv.table(["Note", "Type", "Status", "Updated"],
  dv.pages('"04_Research"')
    .where(p => p.status === "active" && p.latex_pending)
    .sort(p => p.updated, 'desc')
    .map(p => [p.file.link, p.note_type, p.status, p.updated])
)
```

### Step 3 — Update the dashboard note

Each dashboard note has this structure:

```markdown
---
title: <Name> Dashboard
note_type: dashboard
domain: 17_Dashboards
updated: <ISO datetime>
---

# <Name> Dashboard

> Last refreshed: <ISO datetime>

## Active items
![[<dashboard>_active_query]]

## Known gaps
<manually maintained — list of things expected but not yet present>
```

The `## Known gaps` section is manually maintained. Never overwrite it — only append if new gaps are identified.

### Step 4 — Update Home.md

`Home.md` must always reflect the current list of sub-dashboards. Check that every sub-dashboard file is linked from `Home.md`. Add any new dashboards; do not remove entries for existing ones.

### Step 5 — Fallback for complex queries

When Dataview cannot express a query (e.g., cross-domain aggregations, git-derived stats), fall back to a hand-maintained list with an explicit `Last updated:` stamp on that section.

## Constraints

- **Dashboards are read-only views.** They never create, move, or edit vault content notes.
- **Never overwrite `## Known gaps`** — that section is manually curated.
- **Query files are the source of truth** — edit queries in `19_Metadata_and_Schema/Dataview_Queries/`, not inline in dashboard notes.
- Comment every Dataview query with its exact filter and sort logic so future maintenance is self-documenting.

## Dependencies

- Query store: `19_Metadata_and_Schema/Dataview_Queries/`.
- Schema: `19_Metadata_and_Schema/Frontmatter_Standards/` (to keep queries in sync with enum changes).
- Sibling skills: `knowledge-indexer` (produces MOC data that dashboards query), `index-maintainer` (root index; call it after rebuilding all dashboards).
