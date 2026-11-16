---
name: diagram
description: Produce a semantically meaningful, mathematically precise TikZ diagram that makes a visual argument rather than illustrating one. Trigger on "draw X", "diagram X", "haz un diagrama de X", or --type commutative|geometric|stochastic|algebraic|dependency|flow.
---

# /diagram — Produce a TikZ diagram

Produce a semantically meaningful, mathematically precise TikZ diagram.
The diagram must make a visual argument — not illustrate one.

## Usage

```
/diagram <semantic intent>
/diagram <intent> --type commutative|geometric|stochastic|algebraic|dependency|flow
/diagram <intent> --output docs/<path>/figures/<name>.tex
```

## Step 0 — Semantic gateway (I15: mandatory)

Before dispatching any agent, forward the entire raw user request to `semantic-kernel`.

Dispatch `semantic-kernel` with:
```
[SKILL: /diagram] <full user request, verbatim>
```

Wait for the kernel to return its routing decision.

- If `CLARIFICATION_REQUIRED`: present the kernel's question to the user and stop.
- If `DIRECT` or `TECHNICAL_SPEC`: proceed using the kernel's metadata block.

Every subsequent Agent dispatch MUST include the `SEMANTIC_KERNEL_METADATA` block.

## Step 1 — Dispatch intellectual-orchestrator

Forward the kernel's request to `intellectual-orchestrator` with `task_type: diagrammatic` and the full metadata block.

The orchestrator dispatches `tikz-visual-agent` with the semantic intent — what the diagram must communicate, not how to draw it. The agent designs, writes, and sandbox-compiles the TikZ.

## What to give the skill

Describe what the diagram must COMMUNICATE, not how to draw it.

Good:
```
/diagram "the universal property of the tensor product: every bilinear map factors uniquely through it"
/diagram "a filtration growing over time: sigma-algebras nested, information accumulating"
/diagram "the commutative square expressing naturality of the Yoneda embedding"
```

Not useful:
```
/diagram "a circle with an arrow"
/diagram "something about limits"
```

## Diagram types

| Type | Use for |
|------|---------|
| `commutative` | Commutative diagrams, functors, natural transformations |
| `geometric` | Manifolds, bundles, geodesics, fibre diagrams |
| `stochastic` | Filtration growth, Markov chains, probability timelines |
| `algebraic` | Hasse diagrams, lattices, subgroup chains, filtration towers |
| `dependency` | Pipeline stages, logical dependencies, module interfaces |
| `flow` | Processes, algorithms, decision trees |

## Output location

Default: `docs/figures/<intent-slug>.tex`

Custom: specify `--output docs/<path>/figures/<name>.tex`

## Quality standard

Every diagram shipped by `/diagram` compiles without errors under LuaLaTeX.
Every element has a semantic role. No decorative elements.
The visual argument can be stated in one sentence.
