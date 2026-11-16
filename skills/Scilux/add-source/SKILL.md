---
name: add-source
description: Ingest a new input (paper, book, YouTube, narration, image, link) for an existing lesson and refresh sources.json. Argument is the source path or URL.
tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebFetch
---

# /add-source

## Step 0 — Semantic gateway (I15: mandatory)

Dispatch `semantic-kernel` with:
```
[SKILL: /add-source] <full user request, verbatim>
```

Wait for the kernel's routing decision (will be DIRECT). Extract `SEMANTIC_KERNEL_METADATA` block.

## Contract

Usage: `/add-source <lesson_id> <path_or_url> [--kind paper|book|youtube|narration|image|link]`

1. If `--kind` is omitted, infer from the extension or URL host.
2. Copy the file to the right folder under `inputs/` (or create a YAML sidecar for URLs).
3. Append the entry to `inputs/briefs/<lesson_id>.yaml#sources`.
4. Dispatch the matching ingestor (with the kernel's metadata block), then `ingestion-validator`.
5. Refresh `workspace/<lesson_id>/sources.json`.
6. If downstream phases already ran, mark them stale in `logs/<lesson_id>/staleness.md` and print the recommended `/script-update` command.

Never runs the full pipeline. Leaves that to the user.
