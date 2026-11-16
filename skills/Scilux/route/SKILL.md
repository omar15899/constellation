---
name: route
description: Explicit invocation of the Scilux semantic gateway — the Step 0 every other skill runs internally, exposed directly. Trigger on any free-form Scilux request whose destination skill is unclear, or on "route this", "where does this go".
---

# /route — Semantic kernel entry point

`/route` is the explicit invocation of the semantic gateway. Every other skill internally
calls the semantic-kernel as Step 0; `/route` IS that step, exposed directly.

## Usage

```
/route <any free-form request>
```

No flags. No arguments. The entire text after `/route` is the request.

## What this does

1. Dispatches `semantic-kernel` with the raw request (no `[SKILL:]` prefix — the kernel is invoked directly).
2. The kernel scores the request on 10 semantic dimensions and generates a `semantic_kernel_run_id`.
3. Returns one of three outputs:

   **DIRECT** (precision ≥ 0.75): forwards the normalized request immediately to the
   correct pipeline — lesson pipeline (`/create` flow), intellectual pipeline (`/write`
   flow), or infrastructure. The downstream orchestrator receives the full `SEMANTIC_KERNEL_METADATA` block.

   **TECHNICAL_SPEC** (precision < 0.75): rewrites the request into a system-grade
   execution contract with explicit domain, abstraction level, selected agents, latent
   subgoals, and prior-art retrieval strategy. Then executes it.

   **CLARIFICATION_REQUIRED** (insufficient information): asks exactly one precise
   question identifying the minimum missing information. Resumes on answer.

## When to use

Use `/route` when:
- You have a complex or open-ended request and want the system to maximally exploit its capabilities
- You are unsure which pipeline or skill applies
- You want the system to infer latent subgoals and treat the request as a full execution contract

All other skills (`/write`, `/think`, `/formalize`, etc.) implicitly call the semantic-kernel
as their Step 0. `/route` is the explicit form of that step.

## Routing decision tree

```
/route "X"
   ↓
semantic-kernel evaluates X
generates: semantic_kernel_run_id, execution_mode, precision_score, domain, pipeline
   ├── lesson-pipeline signal (video, students, script, frames)?
   │       → routes to input-classifier (/create flow) — with SEMANTIC_KERNEL_METADATA
   ├── intellectual-pipeline signal (note, essay, proof, formalize, analyse)?
   │       → routes to intellectual-orchestrator (/write flow) — with SEMANTIC_KERNEL_METADATA
   ├── infrastructure signal (git, config, hooks, agents)?
   │       → direct execution or git-steward
   └── ambiguous?
           → TECHNICAL_SPEC upgrade or CLARIFICATION_REQUIRED
```

## Example

```
/route "help me understand why the spectral theorem works"
→ TECHNICAL_SPEC: intellectual pipeline, mathematics register, structural level,
  prior-art retrieval from Reflexiones, output: technical-essay

/route "quiero un video de 10 minutos sobre la integral de Riemann para undergrads"
→ DIRECT: lesson pipeline, routes to /create

/route "write about hedging"
→ TECHNICAL_SPEC: intellectual pipeline, finance+mathematics register,
  "hedging as local linearisation" framing, stochastic replication, output: technical-essay
```
