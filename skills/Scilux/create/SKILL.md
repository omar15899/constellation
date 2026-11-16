---
name: create
description: Natural-language front door. Accepts free-form input (text, files, URLs) and routes to input-classifier for brief generation, then kicks off the 10-phase pipeline.
tools: Read, Write, Edit, Bash, Glob, Grep, Agent, WebFetch
---

# /create — Natural-language front door

**Usage:**
```
/create <free-form description and/or file references>
```

## Step 0 — Semantic gateway (I15: mandatory)

Before any action, forward the entire raw user input to `semantic-kernel`.

Dispatch `semantic-kernel` with:
```
[SKILL: /create] <full user input, verbatim, including all file references>
```

Wait for the kernel to return its routing decision.

- If `CLARIFICATION_REQUIRED`: present the kernel's question to the user and stop.
- If `DIRECT` or `TECHNICAL_SPEC`: proceed. The kernel's metadata block MUST be prepended to every subsequent Agent dispatch (including to `input-classifier`).

## Step 1 — Classify and evaluate

Dispatch `input-classifier` with the kernel's `SEMANTIC_KERNEL_METADATA` block prepended,
followed by the full original input. The classifier will:

1. Read every referenced file
2. Search `reference/omaros/` for related prior work on the topic
3. Evaluate completeness against the brief checklist
4. Either:
   - Ask for missing information (topic, audience, or all sources missing), or
   - Generate `inputs/briefs/${lesson_id}.yaml` and proceed

## Accepted input types

Omar can pass any combination of the following:

| Type | Example |
|------|---------|
| Free-form text | "Quiero un vídeo de 10 minutos sobre la transformada de Fourier para segundos de carrera." |
| Paper path | `inputs/papers/apostol1974.pdf` or `arxiv:2301.12345` |
| Book/notes path | `inputs/books/my_fourier_notes.md` |
| Image/sketch path | `inputs/images/whiteboard_fourier.jpg` |
| Existing script | `inputs/narration/fourier_draft.md` |
| YouTube reference | `inputs/youtube/3blue1brown_fourier.yaml` |
| URL | A link to a blog post, paper, or video |

## Step 2 — If more information is needed

The classifier emits a structured question list. Present it to the user and wait. Do not proceed until the user responds and the classifier confirms completeness.

## Step 3 — Dispatch the orchestrator for P0 + playbook emission

Once the brief is confirmed, dispatch `script-orchestrator` with the kernel's `SEMANTIC_KERNEL_METADATA` block prepended and the lesson_id + brief path in the body. The orchestrator will:

1. Verify I15 provenance.
2. Execute P0 in its own context (scaffold, manifest, pipeline_report).
3. Emit a **playbook** (`playbook/v1`) at `workspace/<lesson_id>/playbook.yaml` covering every dispatch required in P1–P9, per `docs/governance/playbook.schema.json`.
4. Return a typed response with `playbook_id` and `playbook_path`.

The orchestrator does not call `Agent(…)` itself — Claude Code's depth-1 dispatcher limit prevents it. The playbook is the authority under which the root agent (you) dispatches every subsequent subagent.

## Step 4 — Execute the playbook from root (I16)

Read `workspace/<lesson_id>/playbook.yaml`. For each phase in order:

1. **Entry contract**: verify every path in `phase.entry_contract` exists.
2. **Dispatches**: for each dispatch in `phase.dispatches`, in order (parallel within a parallelism group):
   - Copy the `prompt_template` verbatim into an `Agent` call with the declared `subagent_type`.
   - The `prompt_template` already contains the `SEMANTIC_KERNEL_METADATA` block (I15) and the `PLAYBOOK_METADATA` block (I16).
   - `playbook_guard.py` fires at `PreToolUse: Agent` and verifies the dispatch matches the playbook. A mismatch is a hard block.
   - Consume the typed `agent-response/v1` envelope. On `RETRYABLE_FAILURE`, retry once; on `FAILURE`, stop and re-dispatch `script-orchestrator` with `[REVISION]` for a re-plan.
3. **Exit contract**: verify every path in `phase.exit_contract` exists and matches the declared artefacts.
4. **Blocking gate** (if any): the corresponding hook fires on the last dispatch's SubagentStop event; respect its verdict.
5. **Commit**: invoke `git-steward` with `phase.commit.files` + `phase.commit.message`. `git-steward` stages only the declared files (I9) and commits with the human message.
6. **Pipeline report**: append a row to `logs/<lesson_id>/pipeline_report.md`.

Phase 8 is special: you dispatch `review-orchestrator` (a gated orchestrator, I15 applies, I16 exempt). It emits a **review sub-playbook** at `workspace/<lesson_id>/review_playbook.yaml`. You execute that sub-playbook, aggregate the validator envelopes, and re-dispatch `review-orchestrator` with `[REPORT_ASSEMBLY]` to get the final verdict. Only on `verdict: PASS` do you run P9.

## Output format — .md primary, .tex optional

The master script output is **Markdown** (`lessons/${lesson_id}/script/full_script.md`):

- Line-diffable in git — every revision is traceable
- TikZ code lives in fenced blocks (```tikz ... ```) inside frame sheets
- Readable in Obsidian, GitHub, any markdown renderer
- Evolved iteratively: each version is a commit, building a complete revision history

## Commit discipline

One commit per logical unit. The `git-steward` agent handles all staging and committing.

## Quality bar

Every lesson produced by `/create` must pass all five blocking gates. There is no `/create --skip-validation`. Shortcuts produce bad lessons.

## What you never do

- Start the pipeline before `input-classifier` confirms completeness.
- Dispatch `input-classifier` or `script-orchestrator` without the kernel's metadata block (I15).
- Dispatch any non-infrastructure subagent without a valid `playbook_id` + `playbook_step` + `lesson_id` in the prompt (I16).
- Execute a step not declared in the active playbook. If you believe a step is needed but missing, re-dispatch the orchestrator for a revised playbook; never improvise.
- Generate a lesson_id with uppercase letters, spaces, or underscores.
- Run P9 before `review_report.md` verdict is `PASS`.
- Omit the `git-steward` commit after each phase.
