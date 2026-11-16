---
name: script-generate
description: Run the full 10-phase Scilux pipeline for one lesson, end to end. Argument is the lesson_id.
tools: Read, Write, Edit, Bash, Glob, Grep, Agent, TaskCreate, TaskUpdate, TaskList
disable-model-invocation: true
---

# /script-generate

## Step 0 — Semantic gateway (I15: mandatory)

Dispatch `semantic-kernel` with:
```
[SKILL: /script-generate] <lesson_id>
```

Wait for the kernel's routing decision. The kernel will return DIRECT (this is a technically precise operation). Extract the `SEMANTIC_KERNEL_METADATA` block with `semantic_kernel_run_id`.

If `CLARIFICATION_REQUIRED` (unexpected): present the question and stop.

## Contract

Usage: `/script-generate <lesson_id>`

1. Verify `inputs/briefs/<lesson_id>.yaml` exists and has a non-placeholder `topic`, `audience`, `duration_budget`, and at least one source.
2. Dispatch `script-orchestrator` with the lesson_id, a full-pipeline directive (phases 0–9), and the kernel's `SEMANTIC_KERNEL_METADATA` block prepended to the prompt.
3. Surface phase-by-phase status to the user; the orchestrator emits `logs/<lesson_id>/pipeline_report.md` continuously.
4. On any phase-gate failure, stop and print the blocker list from `logs/<lesson_id>/blockers.md`.
5. On success, point the user to `logs/<lesson_id>/review_report.md` and `lessons/<lesson_id>/delivery/`.

Delegation: dispatch `script-orchestrator` (Opus).
