---
name: export
description: Produce the final delivery bundle for a lesson. Refuses unless review_report.md verdict is PASS.
tools: Read, Write, Edit, Bash, Glob, Agent
disable-model-invocation: true
---

# /export

## Step 0 — Semantic gateway (I15: mandatory)

Dispatch `semantic-kernel` with:
```
[SKILL: /export] <lesson_id>
```

Wait for the kernel's routing decision (will be DIRECT). Extract `SEMANTIC_KERNEL_METADATA` block.

## Contract

Usage: `/export <lesson_id>`

1. Read `logs/<lesson_id>/review_report.md`. Refuse if verdict ≠ PASS.
2. Dispatch `script-assembler`, `storyboard-assembler`, `delivery-packager`, `companion-generator` in sequence (with the kernel's metadata block in each prompt).
3. Commit the delivery bundle and the companion with a human commit message.
4. Print the bundle path and the companion path.
