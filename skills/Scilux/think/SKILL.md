---
name: think
description: Surface the deepest abstract structure of a topic: the object, its ambient structure, invariants, cross-domain connections, and what makes it load-bearing. A structural dissection, not an essay. Trigger on "what is the structure of X", "think about X abstractly", "piensa en X".
---

# /think — Abstract structural analysis

Surface the deepest abstract structure of any topic. Returns a structured analysis
of the object, its ambient structure, invariants, cross-domain connections, and
what makes it structurally load-bearing in the larger theory.

This is not an essay — it is a structural dissection. The output feeds `/write`
and `/formalize`, but it is also useful on its own as a thinking tool.

## Usage

```
/think <topic>
/think <topic> --depth axiomatic|structural|algorithmic|applied
/think <topic> --output docs/notes/<slug>.md
```

## Step 0 — Semantic gateway (I15: mandatory)

Before dispatching any agent, forward the entire raw user request to `semantic-kernel`.

Dispatch `semantic-kernel` with:
```
[SKILL: /think] <full user request, verbatim>
```

Wait for the kernel to return its routing decision.

- If `CLARIFICATION_REQUIRED`: present the kernel's question to the user and stop.
- If `DIRECT` or `TECHNICAL_SPEC`: proceed using the kernel's metadata block.

Every subsequent Agent dispatch MUST include the `SEMANTIC_KERNEL_METADATA` block.

## Step 1 — Dispatch agents

Using the kernel's output:

1. Dispatch `repository-memory-agent` to surface any prior structural analysis on this topic.
2. Dispatch `abstract-concepts-agent` with the topic, integration context, and the full metadata block.
3. Return the structured YAML analysis and a compact prose summary.

## Output structure

The output contains:
- The object at its most intrinsic, coordinate-free level
- The ambient mathematical structure
- The admissible transformations (the morphisms that preserve essential structure)
- The key invariants
- The intrinsic vs. representation-dependent properties
- The cross-domain structural connections (identified, not asserted)
- Why the definition is what it is (what pathologies it excludes)
- What the object makes possible in the larger theory
- Open structural questions

## Examples

```
/think "the Fourier transform"
/think "a martingale"
/think "a type class in functional programming"
/think "the principal bundle in gauge theory" --depth structural
/think "the concept of adjoint functors" --depth axiomatic
```

## When to use

- Before writing a note on a topic, to establish the right level of abstraction
- When you sense two things are structurally the same but cannot yet articulate why
- When you want to understand what a definition is actually doing
- As the first step in a `/write` or `/formalize` workflow

## What you get back

Not a polished essay. A structural report you can build from. The `/write` skill
takes `/think` output as its intellectual backbone.
