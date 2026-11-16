---
name: formalize
description: Convert informal prose, intuitions, partial treatments or proof sketches into rigorously stated formal mathematics. Trigger on "formalize X", "formaliza X", "state this rigorously", "turn this sketch into a theorem".
---

# /formalize — Mathematical formalization

Convert informal prose, intuitions, partial treatments, or proof sketches into
rigorously stated formal mathematics.

## Usage

```
/formalize <description of what to formalize>
/formalize <inline prose or claim>
/formalize --input docs/notes/<slug>.md
/formalize --output docs/notes/<output-slug>.md
```

## Step 0 — Semantic gateway (I15: mandatory)

Before dispatching any agent, forward the entire raw user request to `semantic-kernel`.

Dispatch `semantic-kernel` with:
```
[SKILL: /formalize] <full user request, verbatim>
```

Wait for the kernel to return its routing decision.

- If `CLARIFICATION_REQUIRED`: present the kernel's question to the user and stop.
- If `DIRECT` or `TECHNICAL_SPEC`: proceed using the kernel's metadata block.

Every subsequent Agent dispatch MUST include the `SEMANTIC_KERNEL_METADATA` block.

## Step 1 — Dispatch intellectual-orchestrator

Forward the kernel's `TECHNICAL_REQUEST` (or `forward_request`) to `intellectual-orchestrator`
with the metadata block prepended and `task_type: formalizing` confirmed.

The orchestrator will dispatch:
1. `repository-memory-agent` — surface existing notation conventions
2. `mathematical-formalization-agent` — build the formal structure
3. Optionally `markdown-knowledge-agent` + `metadata-provenance-agent` for a governed document

## What formalization produces

- Complete formal definitions with explicit domains, codomains, and quantifiers
- Theorem statements with ALL hypotheses stated
- Proof, proof sketch (with `[GAP:]` markers), or deferred with citation
- Notation declaration block: every symbol defined

## Examples

```
/formalize "the idea that a Fourier series converges when the function is smooth enough"
/formalize "the claim that a continuous function on a compact set achieves its maximum"
/formalize "why the Lebesgue integral extends the Riemann integral" --output docs/notes/lebesgue-vs-riemann.md
/formalize --input docs/reflections/spectral-theorem-intuition.md
```

## Quality standard

Every output of `/formalize` must satisfy: no symbol appears before it is defined;
every theorem states all its hypotheses; every proof gap is labelled with `[GAP: reason]`.
