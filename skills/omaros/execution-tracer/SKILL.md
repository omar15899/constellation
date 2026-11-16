---
name: execution-tracer
description: 'Write the mandatory final execution-trace artefact for every non-trivial task in OmarOS under 11_Documents_and_Reports/Execution_Traces/YYYY-MM-DD/<task_id>.md. Use this skill when a task with risk ≥ low is being closed and requires a durable execution record, when the user invokes /result, or when governance-auditor finds a closed task without an artefact and forces retroactive creation. Records: objective, compiled plan, actions executed, files changed, tests run, documentation updated, git actions (commits + push state), logs, invariants checked (pass / waive / reason), pending risks, recovery actions. Every section must be populated — blanks become "n/a (reason: …)"; every waived invariant carries a named reason and authoriser. Do NOT trigger for task creation or state updates (task-marshal), for ADRs explaining why a task was decided (decision-logger), for project-level rollups (project-reporter), or for incident notes (failure-reporter). Renamed from `result-agent` on 2026-04-17 to drop the obsolete `-agent` suffix; `result-agent/` is a deprecation pointer.'
license: Proprietary. OmarOS internal.
outputSchema:
  $ref: 19_Metadata_and_Schema/Agent_Output_Schemas/pipeline_response.json
  composes:
  - 19_Metadata_and_Schema/Agent_Output_Schemas/pipeline_response.json
contract_invariants:
- Writes the mandatory final execution-trace artefact under 11_Documents_and_Reports/Execution_Traces/YYYY-MM-DD/<task_id>.md.
- 'Every section is populated; blanks become ''n/a (reason: …)'' and every waived invariant carries a named reason and authoriser.'
- No task with risk ≥ low closes without a trace artefact.
---

# Execution Tracer

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Owns `11_Documents_and_Reports/Execution_Traces/`. The durable record of **how** a task was done, **why** it was done that way, and **whether every required stage actually ran**. Git history shows what changed; the execution trace shows the full operational envelope around the change. Derived from Article XII of `GENESIS_PROMPT`. Required for closure of any non-trivial task.

## Quick reference

| Trigger | Action |
|---------|--------|
| `/result <task_id>` | compose and write trace |
| `TaskCompleted` event with `risk ≥ low` | same |
| `governance-auditor` finds closed task without trace | retroactive composition |

## When this skill runs

- A task with `risk ≥ low` transitions to `completed`.
- User invokes `/result`.
- Governance audit forces retroactive creation.

Do **not** run for:

- Task CRUD (create, transition) → `task-marshal`.
- Decision about how to do a task → `decision-logger`.
- Project-level rollup → `project-reporter`.
- Incident from failure within the task → `failure-reporter`.

## Inputs

| Input | Required | Source |
|-------|:--------:|--------|
| `task_id` | ✅ | caller or `/result` arg |
| task note | ✅ | `02_Tasks_and_Execution/**/<task_id>*.md` |
| compiled plan | optional | `planner-agent` output if any |
| action log | optional | session log for the task |
| git state | ✅ | `git log --format=... <branch>` over task range |
| invariant outputs | optional | `.claude/tests/invariants/` results |
| test results | optional | CI or local |
| doc-sync report | optional | `doc-tracer` latest |

If any input unavailable → proceed; affected section becomes `n/a (reason: input not available)`.

## Outputs

| Artefact | Path |
|----------|------|
| execution trace | `11_Documents_and_Reports/Execution_Traces/YYYY-MM-DD/<task_id>.md` |

Return:

```
artefact: <path>
task_id: <slug>
status: completed | blocked | aborted
invariants_passed: <int>
invariants_waived: <int>
pending_risks: <int>
```

## Procedure

### Step 1 — Resolve inputs

Locate the task file. Collect available inputs per §Inputs.

### Step 2 — Scaffold the trace

Pipe a JSON payload to `scripts/new_trace.py`:

```bash
echo '{"task_id": "...", "title": "...", "status": "completed", "risk": "low", "since": "HEAD~20"}' \
  | python3 scripts/new_trace.py
```

The script writes `11_Documents_and_Reports/Execution_Traces/<today>/<task_id>.md` with valid frontmatter, section skeleton, and a pre-populated `## 7. Git actions` table from `git log --format=%h|%s <since>..<until>`. All other sections start with `n/a (reason: input not available)` placeholders.

### Step 3 — Fill the sections

Replace the `n/a` placeholders with actual content, in the canonical order: Objective → Plan → Actions executed → Files changed → Tests run → Documentation updated → Git actions (extend if needed) → Logs → Invariants → Pending risks → Recovery actions.

### Step 4 — Populate invariant table

For each invariant relevant to this task kind:
- **pass** — ran + passed; evidence is a log path or script output.
- **waived** — did not run; reason + authoriser (typically user).
- **n/a** — does not apply; brief reason.

Invariants sourced from `20_System_Governance/Policies/Never_Skip_Invariants.md` when present. If not, fall back to minimal set: (i) commit present for each file claimed changed, (ii) tests run or waived, (iii) docs updated or n/a.

### Step 5 — Record push state in git actions

The script pre-fills commit hashes and subjects. For each row, fill the `Pushed` column by checking the push hook log at `docs/hook_logs/push_on_commit*.log` or `git log origin/main..HEAD` to infer which commits are ahead of the remote.

### Step 6 — Enumerate pending risks

Even a successfully closed task may leave risks (quick patch needing revisit, disabled test, TODO, feature flag). List them. If any is high-severity, escalate to `decision-logger` or `task-marshal` for follow-up.

### Step 7 — Emit report payload

## Constraints

- **CRITICAL:** artefact exists before task is marked `completed`. Enforced by `task-marshal`.
- **CRITICAL:** every section populated. Blanks become `n/a (reason: …)`. No silent gaps.
- **CRITICAL:** waived invariants carry a named reason AND authoriser.
- **CRITICAL:** never fabricate evidence. Real commit hashes, real test output, real paths. If not performed, `n/a`.
- Idempotent per `task_id`. Re-running overwrites the same day's file.

## Reference

Frontmatter schema:

```yaml
---
task_id: <slug>
title: "<title>"
status: completed | blocked | aborted
worktree: <path or null>
created: YYYY-MM-DDTHH:MM:SSZ
completed: YYYY-MM-DDTHH:MM:SSZ
risk: low | medium | high
note_type: execution_trace
project: <slug or null>
related_task: <path>
invariants_passed: [<names>]
invariants_waived: [<names>]
tags: [execution_trace, <project>]
---
```

## Scripts

- [`scripts/new_trace.py`](scripts/new_trace.py) — scaffolds the trace with frontmatter, section skeleton, and a pre-populated git-actions table computed from `git log`.

## Dependencies

- Article XII: `07_AI_and_Agents/Prompts/Master_Prompts/GENESIS_PROMPT.md`.
- Invariants policy: `20_System_Governance/Policies/Never_Skip_Invariants.md`.
- Template (create on first use): `18_Templates/Execution_Traces/_template.md`.
- Sibling skills: `task-marshal`, `decision-logger`, `project-reporter`, `failure-reporter`, `governance-auditor`.
- Escalations: `planner-agent` (missing plan), `failure-recovery-agent` (repeated failure to produce).

## Cross-references

- Rename history: `20_System_Governance/Decisions/2026-04-17_rename_result_agent_to_execution_tracer.md` (forthcoming).
