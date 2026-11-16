---
name: project-reporter
description: Own project notes, status reports, checkpoints, and risk registers in OmarOS 05_Projects/<Project>/. Use this skill when the user says "update the project", "status of X", "checkpoint for Y", "project log", "write a status report", "registra el estado del proyecto", or invokes /project-log, /checkpoint, /new-project. Also trigger when the user narrates milestones, risks, or blockers tied to a specific project. Maintains README.md as the project MOC, writes dated status reports under Status/, end-of-phase checkpoints under Checkpoints/, and risk register under Risks.md. Every status report cites task/commit/decision deltas since the previous report. Do NOT trigger for ADRs (decision-logger), task CRUD (task-marshal), long-form reflective essays on a project (scholar), or external-repo git-diff reports (repo-reporter).
license: Proprietary. OmarOS internal.
outputSchema:
  $ref: 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
  composes:
  - 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
contract_invariants:
- Writes only inside 05_Projects/<Project>/; status reports cite task/commit/decision deltas since the previous report.
- Maintains README.md as the project MOC and keeps Status/, Checkpoints/, Risks.md in sync.
---

# Project Reporter

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Owns `05_Projects/<project-slug>/` as the vault-internal project surface. A project is a durable named body of work with its own README (MOC), status timeline, checkpoints, decisions, tasks, and risks. This skill writes all of them except ADRs (`decision-logger`) and task CRUD (`task-marshal`). A project moves to `99_Archive/` only after a final checkpoint.

## Quick reference

| User intent | Artefact |
|-------------|----------|
| "status of X" | `Status/YYYY-MM-DD.md` |
| "checkpoint end-of-phase" | `Checkpoints/<phase>.md` |
| "log this to project" | `Logs/YYYY-MM-DD_<slug>.md` |
| "new risk for X" | `Risks.md` append |
| "new open problem" | `Open_Problems/<slug>.md` |
| "bootstrap new project X" | scaffold directory + README + Vision + Architecture |
| "archive project" | final checkpoint + `/archive` |

## When this skill runs

- `/project-log`, `/checkpoint`, `/new-project` invoked.
- User narrates a milestone, risk, blocker, or status tied to a project.
- `repo-reporter` produced a state report that needs integration inside the project tree.

Do **not** run for:

- Long-form essay on the project → `scholar`.
- Project-level ADR → `decision-logger`.
- Task creation / state change → `task-marshal`.
- Daily journal entry mentioning the project → `journal-writer`.
- External-repo git-diff reports → `repo-reporter`.

## Inputs

| Input | Required | Notes |
|-------|:--------:|-------|
| project slug | ✅ | directory under `05_Projects/` |
| artefact kind | ✅ | readme / vision / architecture / status / checkpoint / log / risk / open_problem |
| narrative content | ✅ | prose + structured fields |
| deltas since prev report | ✅ (status only) | computed from git, task-marshal, decisions |

## Outputs

| Artefact | Path |
|----------|------|
| README | `05_Projects/<slug>/README.md` |
| Vision | `05_Projects/<slug>/Vision.md` |
| Architecture | `05_Projects/<slug>/Architecture.md` |
| Status | `05_Projects/<slug>/Status/YYYY-MM-DD.md` |
| Checkpoint | `05_Projects/<slug>/Checkpoints/<phase>.md` |
| Log | `05_Projects/<slug>/Logs/YYYY-MM-DD_<slug>.md` |
| Risks | `05_Projects/<slug>/Risks.md` |
| Open problem | `05_Projects/<slug>/Open_Problems/<slug>.md` |

Return:

```
artefact: <path>
project: <slug>
kind: <kind>
delta_since: <prev date>
cross_links: [...]
```

## Procedure

### Step 1 — Locate or scaffold the project

Resolve `<project-slug>`. If `05_Projects/<slug>/` does not exist, confirm and scaffold: directory + `README.md` (from template) + `Vision.md` + `Architecture.md` stubs.

### Step 2 — Determine artefact kind

Apply the Quick reference table.

### Step 3 — Compute deltas (status reports only)

Compute what changed since the previous status date:

1. `git log --oneline <prev>..HEAD -- 05_Projects/<slug>/` plus any paths named in `Architecture.md`.
2. Ask `task-marshal` for tasks closed since prev date filtered by project.
3. Grep `20_System_Governance/Decisions/` for ADRs with `affects:` including the project.

If deltas empty → either project is dormant (`health: amber`) or no status warranted; ask.

### Step 4 — Write the artefact

Use canonical body for the kind. Every bullet cites its evidence (commit hash, closed task, ADR path). Every health claim justified in one sentence.

### Step 5 — Maintain cross-links

- Status → link from `README.md` under `## Status timeline`.
- Checkpoint → link from `README.md` under `## Checkpoints`.
- Risk → `Risks.md` + cite in next status.
- Archival → write final checkpoint first, then `/archive`.

### Step 6 — Emit report payload

## Constraints

- **CRITICAL:** README.md always exists first. Before any other project note, scaffold README.
- **CRITICAL:** status reports cite task/commit/decision deltas. A status without deltas is a journal entry.
- **CRITICAL:** no archival without a final checkpoint.
- Risk register is living; every status verifies it.
- Cross-links mandatory. Floating artefacts are defects.

## Reference

Status frontmatter (the most variable):

```yaml
---
title: "<project> — <date> status"
note_type: project_status
project: <slug>
date: YYYY-MM-DD
since: YYYY-MM-DD
health: green | amber | red
commits_since: <int>
tasks_closed_since: <int>
decisions_since: <int>
---
```

## Dependencies

- Template: `18_Templates/Project_State/_template.md`.
- Sibling skills: `task-marshal`, `decision-logger`, `repo-reporter`, `scholar`.
- Dashboards: `17_Dashboards/Projects.md` (Dataview).

## Cross-references

- `CLAUDE.md` §7.
