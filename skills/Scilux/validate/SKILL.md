---
name: validate
description: Run Phase 8 validation against the current artefacts of a lesson, without touching Phases 1-7.
tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# /validate

## Step 0 — Semantic gateway (I15: mandatory)

Dispatch `semantic-kernel` with:
```
[SKILL: /validate] <lesson_id>
```

Wait for the kernel's routing decision (will be DIRECT). Extract `SEMANTIC_KERNEL_METADATA` block.

## Contract

Usage: `/validate <lesson_id>`

1. Dispatch `review-orchestrator` with the kernel's `SEMANTIC_KERNEL_METADATA` block prepended to the prompt.
2. Wait for `logs/<lesson_id>/review_report.md`.
3. Print the final verdict and, if not PASS, the top 5 findings.

Use this after manual edits to a scene or frame, before `/export`.
