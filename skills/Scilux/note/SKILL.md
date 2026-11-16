---
name: note
description: Create a formally structured, metadata-complete knowledge artefact — mathematical note, technical essay, reflection, architecture doc, implementation note, or bibliographic synthesis — from the schema registry. Trigger on "make a note on X", "crea una nota sobre X", "document X formally".
---

# /note — Create a governed knowledge artefact

Create a formally structured, metadata-complete knowledge document — a mathematical note,
technical essay, reflection, or other document type from the schema registry.

## Usage

```
/note <topic>
/note <topic> --type mathematical-note|technical-essay|reflection|architecture-doc|implementation-note|bibliographic-synthesis
/note <topic> --status draft|stable
/note <topic> --confidence conjecture|plausible|established|textbook
/note <topic> --audience self|specialist|graduate|undergraduate
/note <topic> --output docs/notes/<slug>.md
```

## Step 0 — Semantic gateway (I15: mandatory)

Before dispatching any agent, forward the entire raw user request to `semantic-kernel`.

Dispatch `semantic-kernel` with:
```
[SKILL: /note] <full user request, verbatim, including all flags>
```

Wait for the kernel to return its routing decision.

- If `CLARIFICATION_REQUIRED`: present the kernel's question to the user and stop.
- If `DIRECT` or `TECHNICAL_SPEC`: proceed using the kernel's metadata block.

Every subsequent Agent dispatch MUST include the `SEMANTIC_KERNEL_METADATA` block.

## Step 1 — Dispatch intellectual-orchestrator

1. Read `config/document-schema-registry.yaml` for the schema of the requested type.
2. Read `docs/templates/<type>.md` for the template.
3. Forward the kernel's request to `intellectual-orchestrator` with `task_type: infrastructural`,
   the document type, schema path, template path, and the full metadata block prepended.

The orchestrator runs:
`repository-memory-agent` → `abstract-concepts-agent` → `technical-expositor-agent` →
`markdown-knowledge-agent` → `metadata-provenance-agent`

## Defaults

- `--type`: `mathematical-note` if the topic is mathematical; `technical-essay` otherwise
- `--status`: `draft`
- `--confidence`: inferred from content (set to `conjecture` if no sources; `established` if proved)
- `--audience`: `self`
- `--output`: `docs/notes/<slug>.md`

## Document types

| Type | Use for |
|------|---------|
| `mathematical-note` | Formal treatment with definitions, theorems, proofs |
| `technical-essay` | Extended exposition, continuous prose, no single theorem focus |
| `reflection` | Raw intellectual encounter, questions, sensed connections |
| `architecture-doc` | System or pipeline design |
| `implementation-note` | Record of a specific technical decision |
| `bibliographic-synthesis` | Structured synthesis of a body of literature |

## Examples

```
/note "Sobolev spaces and their relation to distributional derivatives"
/note "the concept of a monad in category theory and functional programming" --type technical-essay
/note "why the Banach fixed point theorem feels like it should generalise to more abstract settings" --type reflection
/note "design of the intellectual pipeline in Scilux" --type architecture-doc --output docs/architecture/intellectual-pipeline.md
```

## Governance

Every document created by `/note` will have:
- Complete frontmatter (all required fields filled)
- Correct `type`, `confidence`, `status`, and `audience` fields
- `repo_path` set to the actual file path
- `ai_involvement` set honestly
- `created` and `updated` set to today's date
- Tags and domains inferred from the content
