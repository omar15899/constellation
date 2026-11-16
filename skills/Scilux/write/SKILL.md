---
name: write
description: Invoke the intellectual writing pipeline for any topic needing extraordinary prose, mathematical depth, or cross-domain synthesis. Trigger on "write about X", "escribe sobre X", "draft an essay on X", or --mode synthesis|integration.
---

# /write — High-authority intellectual writing

Invoke the intellectual writing pipeline for any topic requiring extraordinary prose,
mathematical depth, or cross-domain synthesis.

## Usage

```
/write <topic or prompt>
/write <topic> --mode synthesis|integration
/write <topic> --format md|tex|fragment
/write <topic> --register math|physics|computing|philosophy|interdisciplinary
/write <topic> --audience self|specialist|graduate|undergraduate
/write <topic> --output docs/notes/<slug>.md
```

## Step 0 — Semantic gateway (I15: mandatory)

Before dispatching any agent, you MUST forward the entire raw user request to `semantic-kernel`.

Dispatch `semantic-kernel` with:
```
[SKILL: /write] <full user request, verbatim, including all flags>
```

Wait for the kernel to return its routing decision.

- If `CLARIFICATION_REQUIRED`: present the kernel's question to the user and stop. Do not proceed.
- If `DIRECT` or `TECHNICAL_SPEC`: the kernel's output contains a `SEMANTIC_KERNEL_METADATA` block with `semantic_kernel_run_id`. Use this metadata for all subsequent dispatches.

Every subsequent Agent call to `intellectual-orchestrator` MUST include the kernel's `SEMANTIC_KERNEL_METADATA` block verbatim at the top of its prompt.

## Step 1 — Dispatch intellectual-orchestrator

Using the kernel's `TECHNICAL_REQUEST` (or `forward_request` if DIRECT), dispatch `intellectual-orchestrator` with the full metadata block prepended.

The orchestrator classifies the task, selects agents, and produces the final artefact.

## Defaults

- `--mode`: determined by routing policy (integration if prior material exists; synthesis otherwise)
- `--format`: `md`
- `--register`: inferred from topic
- `--audience`: `self` (maximum density, no scaffolding)
- `--output`: `docs/essays/<slug>.md`

## When to use

- Writing a technical essay or mathematical note on any topic
- Producing an exposition of a concept you want to develop deeply
- Generating a first draft of a formal document
- Creating a bilingual note (add `--lang en,es`)

## When NOT to use

- For video script generation: use `/create` or `/script-generate` instead
- For TikZ diagrams alone: use `/diagram` instead
- For mathematical formalization alone: use `/formalize` instead

## Examples

```
/write "the relationship between the Fourier transform and the spectral theorem"
/write "why Sobolev spaces are the right setting for weak solutions of PDEs" --register math --audience graduate
/write "local linearisation as a unifying theme across calculus, finance, and control theory" --register interdisciplinary
/write "the design of the Scilux intellectual pipeline" --format md --output docs/architecture/intellectual-pipeline.md
```
