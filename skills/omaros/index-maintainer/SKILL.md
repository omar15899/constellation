---
name: index-maintainer
description: 'Keep Index.md — the vault''s root conceptual map — consistent with the live state of the vault. Use this skill when the user invokes /index, says "refresh Index.md", "update the vault index", "regenerate the conceptual map", "Index.md is stale", "actualiza el índice raíz", or after any commit that adds a new subfolder or domain to the vault topology. Re-renders only the auto-generated block delimited by <!-- auto:conceptual-map --> tags, leaving all manually curated sections (conceptual descriptions, philosophy, goals) completely untouched. Surfaces missing or unexpected domain folders as warnings rather than silently adjusting. Do NOT trigger for building MOCs (knowledge-indexer), for refreshing dashboards (dashboard-builder), or for full governance audits (governance-auditor). If in doubt between index-maintainer and knowledge-indexer: index-maintainer owns the root Index.md; knowledge-indexer owns the per-domain MOCs.'
license: Proprietary. OmarOS internal.
---

# Index Maintainer

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

`Index.md` is the first page a reader (human or agent) sees when entering the vault. It contains two layers: a manually curated conceptual description of each domain (written once, evolved deliberately) and an auto-generated topology block that reflects the current state of subfolders and note counts.

This skill owns only the auto-generated layer. The reason for the hard separation: topology changes constantly as the vault grows, but the conceptual descriptions represent considered thought about the vault's intellectual structure. Overwriting them automatically would destroy that investment.

## Quick reference

| Trigger | Action |
|---------|--------|
| `/index` | full refresh regardless of whether topology changed |
| new subfolder committed | refresh auto block for affected domain(s) |
| `/governance-audit` | full refresh as part of audit |
| "Index.md is stale" | full refresh |

## Anatomy of `Index.md`

```markdown
---
title: Index
note_type: index
updated: <ISO datetime>
---

# OmarOS — Vault Index

<manually curated introduction — never touch>

## Domain Overview

<!-- auto:conceptual-map -->
[auto-generated content — this skill owns this block]
<!-- /auto:conceptual-map -->

## Navigation
<manually curated — never touch>

---
Last refresh: <ISO datetime>
```

The delimiters `<!-- auto:conceptual-map -->` and `<!-- /auto:conceptual-map -->` are load-bearing. Never remove or move them.

## Procedure

### Step 1 — Read `Index.md`

Read the current `Index.md`. Locate the auto-managed block. Record the exact content of all lines outside the block — they must be preserved byte-for-byte.

### Step 2 — Walk the vault

For each of the 24 numbered domains:
1. List first-level child directories (subdomains).
2. Count `.md` files by `note_type` (read frontmatter of each file).
3. Identify new subfolders not yet reflected in the current index.

### Step 3 — Re-render the auto block

Generate the updated auto block with this structure per domain:

```markdown
### `00_Inbox`
Subdomains: `mobile/`, `web/`, `voice/`  
Notes: 12 captures · 0 classified

### `04_Research`
Subdomains: `Mathematics/`, `Papers/`, `Research_Notebook/`, `Theorems/`, `Definitions/`, `Proofs/`  
Notes: 48 notes · 12 with `latex_pending: true`
```

Include a note when a domain folder is empty (expected during early vault population).

### Step 4 — Replace the auto block

Splice the new auto block between the delimiters. Every line outside the block is preserved exactly. Never rewrite conceptual descriptions.

### Step 5 — Update metadata

- `updated:` frontmatter field ← current ISO datetime.
- `Last refresh:` footer line ← current ISO datetime.

### Step 6 — Write and log

Write `Index.md`. Append a log entry to `docs/hook_logs/YYYY-MM-DD_hooks.log` describing what changed (new subfolders added, domain counts updated).

## Constraints

- **Never rewrite manually curated sections** — only the auto-managed block between the delimiters.
- **Never delete domains from the index** — if a domain folder is missing, surface a warning to the orchestrator rather than removing the domain entry.
- **Never add domains beyond the canonical 24** — a new domain requires a governance change and explicit approval.
- Commits made by this skill are prefixed `index:` and should be batched to at most one per session to avoid churn.

## Dependencies

- `Index.md`: `Index.md` at vault root.
- Log: `docs/hook_logs/YYYY-MM-DD_hooks.log`.
- Sibling skills: `knowledge-indexer` (builds per-domain MOCs; run it first if a full re-index is needed before refreshing `Index.md`).
