---
name: storyboard-render
description: Re-render the storyboard (Phases 6-7) for an existing script. Optional --frames <range> narrows the surface.
tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# /storyboard-render

## Step 0 — Semantic gateway (I15: mandatory)

Dispatch `semantic-kernel` with:
```
[SKILL: /storyboard-render] <full user request, verbatim>
```

Wait for the kernel's routing decision (will be DIRECT). Extract `SEMANTIC_KERNEL_METADATA` block.

## Contract

Usage: `/storyboard-render <lesson_id> [--frames 0042-0060]`

1. Verify `lessons/<lesson_id>/script/scenes/*.md` exists.
2. Dispatch `script-orchestrator` with the kernel's `SEMANTIC_KERNEL_METADATA` block and a storyboard-only directive (Phases 6–7 on the specified range, or the full lesson).
3. Run `tikz-compiler` against the affected frames; only commit frames whose compile succeeded.
4. Update `lessons/<lesson_id>/storyboard/manifest.yaml`.

Emits: updated frame files, PNG previews, manifest diff in `logs/<lesson_id>/storyboard_update.md`.
