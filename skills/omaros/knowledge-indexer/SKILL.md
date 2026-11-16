---
name: knowledge-indexer
description: Build and maintain the Maps of Content (MOCs) and knowledge-graph indices across 06_Knowledge_Base/ and the top-level domains. Use this skill when the user says "rebuild the MOC", "update the knowledge index", "regenerate Research_MOC", "which notes are orphans", "build the knowledge map", "index the knowledge base", "what's in 06_Knowledge_Base", "actualiza el índice de conocimiento", "construye el mapa de contenidos", or invokes /dashboard or /governance-audit (both of which trigger a re-index pass). Maintains one MOC per major domain (Research, Projects, Work, Systems, AI, Learning, Finance, Health, People, Media) — each listing notes grouped by subdomain and tagged by status. Detects orphan notes with no incoming links and no MOC membership. Writes only to 06_Knowledge_Base/MOCs/. Never modifies the body of any indexed note. Do NOT trigger for writing research content (research-scribe), for refreshing Index.md (index-maintainer), or for full governance audits (governance-auditor).
license: Proprietary. OmarOS internal.
outputSchema:
  $ref: 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
  composes:
    - 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
contract_invariants:
  - "Writes only to 06_Knowledge_Base/MOCs/; never modifies the body of any indexed note."
  - "Every MOC groups notes by subdomain and flags orphan notes with no incoming links."
---

# Knowledge Indexer

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

A vault where notes can't find each other is just a folder. The knowledge indexer makes the semantic graph navigable by maintaining Maps of Content — one per major domain — that list every note grouped by subdomain, tagged by status, and cross-linked to related MOCs.

The indexer's secondary job is orphan detection: any note with no incoming links and no MOC membership is invisible to the system. Surfacing orphans is advisory — the indexer never moves or deletes them; it makes them visible so a human can decide what to do.

## Quick reference

| User intent | Action |
|-------------|--------|
| "rebuild Research MOC" | re-index all notes under `04_Research/`, write `Research_MOC.md` |
| "update all MOCs" | re-index all 10 major domains |
| "find orphan notes" | walk vault, flag notes with no incoming links and no MOC membership |
| `/dashboard` | trigger a full re-index pass |
| `/governance-audit` | same as `/dashboard` |

## When this skill runs

- User requests a MOC rebuild or knowledge index refresh.
- `/dashboard` or `/governance-audit` triggers a re-index.
- A new note has been written and the calling pipeline wants to register it in the appropriate MOC.

Do **not** run for:

- Writing research or knowledge-base notes → `research-scribe`.
- Refreshing `Index.md` (the vault's root conceptual map) → `index-maintainer`.
- Full governance audits → `governance-auditor`.

## MOC catalogue

| MOC file | Covers |
|----------|--------|
| `Research_MOC.md` | `04_Research/` — all subdomains |
| `Projects_MOC.md` | `05_Projects/` |
| `Work_MOC.md` | `03_Work/` |
| `Systems_MOC.md` | `08_Systems_and_Infrastructure/` |
| `AI_MOC.md` | `07_AI_and_Agents/` |
| `Learning_MOC.md` | `15_Reading_and_Learning/` |
| `Finance_MOC.md` | `12_Finance/` |
| `Health_MOC.md` | `13_Health/` |
| `People_MOC.md` | `16_Relationships_and_People/` |
| `Media_MOC.md` | `14_Media_and_Memory/` |

All MOC files live in `06_Knowledge_Base/MOCs/`.

## Procedure

### Step 1 — Scan the domain

Walk the target domain directory. For each `.md` file, read its frontmatter to extract: `title`, `note_type`, `status`, `subdomain`, `tags`, `updated`.

### Step 2 — Group by subdomain

Organise notes into a tree: domain → subdomain → note_type bucket. Within each bucket, sort by `updated` descending.

### Step 3 — Render the MOC

Each MOC has this structure:

```markdown
---
title: <Domain> MOC
note_type: moc
domain: 06_Knowledge_Base
updated: <ISO datetime>
---

# <Domain> Map of Content

## <Subdomain A>

- [[note_slug]] — `<note_type>` · `<status>` · <one-line description>

## <Subdomain B>
...

## Orphans

Notes in this domain with no incoming links:
- [[orphan_note]]
```

Where possible, use Dataview queries to make the listing live rather than hand-maintained:

```dataview
TABLE note_type, status, updated
FROM "04_Research"
WHERE subdomain = "Mathematics"
SORT updated DESC
```

Fall back to hand-maintained lists only when Dataview cannot express the query.

### Step 4 — Orphan detection

Cross-reference all notes in the domain against the link graph. A note is an orphan if:
1. No other note has a `[[wikilink]]` pointing to it, AND
2. It does not appear in any MOC.

List orphans in the MOC under `## Orphans`. Never delete or move them — just surface them.

### Step 5 — Write the MOC

Write the updated MOC file to `06_Knowledge_Base/MOCs/<Domain>_MOC.md`. Bump `updated:` in the frontmatter.

## Constraints

- **Never modify indexed notes** — only write to MOC files under `06_Knowledge_Base/MOCs/`.
- **Never delete domains from a MOC** — if a domain folder is temporarily missing, surface it as a warning rather than silently removing its section.
- **Orphan detection is advisory** — never move, archive, or delete orphans.
- Prefer Dataview queries over hand-maintained lists; always comment the query with its filter and sort logic.

## Dependencies

- Schema: `19_Metadata_and_Schema/Frontmatter_Standards/` (for note_type / status enum values used in Dataview).
- Sibling skills: `index-maintainer` (updates root `Index.md`; call it after a full MOC rebuild), `dashboard-builder` (reads MOCs for dashboard content).
