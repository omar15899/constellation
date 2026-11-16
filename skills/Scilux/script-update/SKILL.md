---
name: script-update
description: Re-run selected phases or scenes for an existing lesson. Usage, e.g., /script-update <lesson_id> --phases 4,5 or --scenes s02,s05.
tools: Read, Write, Edit, Bash, Glob, Grep, Agent, TaskCreate, TaskUpdate, TaskList
disable-model-invocation: true
---

# /script-update

## Step 0 — Semantic gateway (I15: mandatory)

Dispatch `semantic-kernel` with:
```
[SKILL: /script-update] <full user request, verbatim>
```

Wait for the kernel's routing decision (will be DIRECT). Extract `SEMANTIC_KERNEL_METADATA` block.

## Contract

Usage:
- `/script-update <lesson_id> --phases <csv>` — re-run listed phases.
- `/script-update <lesson_id> --scenes <csv>` — re-run Phase 5 restricted to listed scenes, then Phases 6, 7, 8 on the affected surface only.

Steps:

1. Load `workspace/<lesson_id>/manifest.json`.
2. Verify that all entry contracts for the requested phases are satisfied by existing artefacts.
3. Dispatch `script-orchestrator` with the explicit phase/scene filter and the kernel's `SEMANTIC_KERNEL_METADATA` block prepended to the prompt.
4. Run validators (Phase 8) on the affected surface before closing.

Refuses to run Phase 9 unless Phase 8 is green. Use `/export` explicitly.
