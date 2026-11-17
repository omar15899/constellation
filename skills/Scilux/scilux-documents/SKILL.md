---
name: scilux-documents
description: Create or revise Scilux governed notes, essays and TikZ figures using project schemas, templates, provenance and explicit artifact validation.
---
# Scilux documents

Read the [Scilux profile](../../../profiles/scilux.md), `config/document-schema-registry.yaml`, `config/style-canon.yaml` and the chosen template in `/Users/omarkhalil/GitHub/Scilux`. Use common writing, mathematics and teaching methods as appropriate. Formalization and structural analysis are responsibilities within the task, not separate dispatch systems.

## Establish the artifact

Select the requested document type: `mathematical-note`, `technical-essay`, `reflection`, `architecture-doc`, `implementation-note` or `bibliographic-synthesis`. Reuse `docs/templates/TYPE.md` and its schema. A conceptual consultation need not create a document; writing requires an authorized destination and exact scope.

Follow the selected schema's frontmatter and allowed status/confidence transitions. Set provenance, dates and `repo_path` honestly where required; do not invent sources, authors or approvals. Use the appropriate `docs/notes/`, `docs/essays/`, `docs/reflections/` or schema-selected location and its figure directory.

Define ambient structures, domains, hypotheses, quantifiers and notation before using them. Distinguish objects from representations. Mark unresolved proof gaps explicitly, for example `[GAP: reason]`; a sketch, conjecture and proof retain different evidential status.

## Figures and sources

For TikZ, first state the mathematical relationship the figure communicates. Every element must contribute to it. Preserve semantic colours, notation, readable labels and the relationship between the figure and surrounding argument. Compile the selected TeX artifacts and inspect their renders when that artifact validation is authorized; report missing validation rather than claiming delivery readiness.

If a conclusion depends on OmarOS retrieval, require actual MCP availability and cite the recovered source. Preserve the configured data source. An inference or an inaccessible historical path must never be presented as recovered vault content.

## Exact validation targets

Before artifact validation, maintain a fresh task manifest at `workspace/intellectual/tasks/TASK/hook_targets.txt`: one exact Scilux-root-relative artifact path per line, with optional `#` comments. Include all current Markdown/TeX deliverables and compare validator coverage with that list.

The current target reader expires a manifest after 300 seconds and may fall back to a shared manifest or mtime discovery. Refresh the exact task manifest before validation when necessary; a zero-target success or fallback scan is not proof that this task's artifacts were covered.

Use the maintained commands in the project profile through `constellation.py check`, with `SCILUX_ROOT` set. Intellectual startup, source retrieval, Markdown schema and TeX compilation are distinct checks; MCP health is required when retrieval supports the result. The compilation record is `logs/intellectual/compile_manifest.json`; inspect its paths and per-artifact results, not only its overall verdict.

## Review and publication

Preserve independent scientific/editorial review and report remaining gaps. Use curated summaries and source references, keeping raw prompts and conversations out of artifacts and the ledger. Create, change or run tests only when Omar explicitly requests them; an unauthorized test-dependent gate remains unmet. Publication uses the common Constellation contract and never follows automatically from writing or compiling a document.
