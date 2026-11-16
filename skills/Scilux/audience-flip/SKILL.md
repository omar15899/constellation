---
name: audience-flip
description: Re-target the lesson for a different audience profile. Triggers re-runs of pedagogy, narrative (partial), scripting (targeted) and validation.
tools: Read, Write, Edit, Bash, Glob, Grep, Agent
disable-model-invocation: true
---

# /audience-flip

## Step 0 — Semantic gateway (I15: mandatory)

Dispatch `semantic-kernel` with:
```
[SKILL: /audience-flip] <full user request, verbatim>
```

Wait for the kernel's routing decision (will be DIRECT). Extract `SEMANTIC_KERNEL_METADATA` block.

## Contract

Usage: `/audience-flip <lesson_id> --to <audience_id>`

1. Validate `config/audience-profiles/<audience_id>.yaml` exists.
2. Update `inputs/briefs/<lesson_id>.yaml#audience`.
3. Dispatch `script-orchestrator` with the kernel's `SEMANTIC_KERNEL_METADATA` block and an audience-flip directive (phases 2, 4, 5 partial, 8 only).
4. Leave the old version in git history; do not overwrite committed artefacts before the new pass is PASS.

Typical use: turn an undergraduate lesson into a high-school variant.
