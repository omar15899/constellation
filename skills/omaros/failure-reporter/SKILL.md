---
name: failure-reporter
description: Write incident notes under 11_Documents_and_Reports/Incidents/ for every refresh, ingestion, or pipeline failure in OmarOS. Use this skill when another skill, agent, or hook raises a structured failure payload (unreachable source, expired token, malformed export, timeout, partial write, schema drift) and requires a durable incident record. Also trigger when the user says "log this incident", "something broke during X", "write an incident for the failure Y", "registra este fallo", or invokes /incident. Incident notes are structured, idempotent per day+slug, carry severity P0..P3, record provenance, reproduce the error verbatim, and propose next actions with named owners. Single owner of the incident format — no other skill writes to Incidents/. Do NOT trigger for post-mortems or retrospectives (scholar or decision-logger), for task creation (task-marshal), or for hook debug output (that lives in docs/hook_logs/).
license: Proprietary. OmarOS internal.
---

# Failure Reporter

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Single owner of `11_Documents_and_Reports/Incidents/`. Every pipeline failure — refresh, ingestion, source probe, repo report — ends as a clean, dated, structured incident with provenance, reproduction, and next actions. **Formats and writes; never investigates.** Diagnosis is not this skill's concern.

## Quick reference

| Trigger | Action |
|---------|--------|
| structured failure payload from another skill | write `Incidents/YYYY-MM-DD_<source_id>_<class>.md` |
| "log this incident manually" | user provides payload inline, same flow |
| status change on existing incident | update frontmatter `status`, append `## Resolution` |

## When this skill runs

- Another skill/agent/hook raises a failure and requests a durable record.
- User invokes `/incident`.
- Callers: `refresh-orchestrator`, `source-scout`, `repo-reporter`, any `ingestion-*`.

Do **not** run for:

- Post-mortem / retrospective → `scholar` or `decision-logger`.
- Task to address → `task-marshal`.
- Hook debug output → `docs/hook_logs/`.

## Inputs

Input contract (from caller):

| Field | Required | Format |
|-------|:--------:|--------|
| `source_id` | optional | from `sources.yaml` |
| `agent` | ✅ | caller name |
| `command` | ✅ | invoking command or capability |
| `started_at` | ✅ | ISO UTC |
| `failed_at` | ✅ | ISO UTC |
| `phase` | ✅ | probe / extract / transform / route / write / commit |
| `error_class` | ✅ | unreachable / auth / schema / timeout / partial_write / unknown |
| `error_message` | ✅ | verbatim, multi-line ok |
| `context.adapter` | optional | adapter type |
| `context.endpoint` | optional | url / path |
| `context.previous_success` | optional | ISO UTC |
| `context.retry_count` | optional | int |

Missing optional fields → record as `null` in frontmatter, note absence in §Context.

## Outputs

| Artefact | Path |
|----------|------|
| incident note | `11_Documents_and_Reports/Incidents/YYYY-MM-DD_<slug>.md` |

Slug: `<source_id>_<error_class>` (or `<agent>_<error_class>` if `source_id` null).

Return:

```
artefact: <path>
severity: P0 | P1 | P2 | P3
status: open
error_class: <class>
source_id: <id or null>
cross_links: [refresh_report, prior_incidents]
```

## Procedure

### Step 1 — Validate payload

Check minimum fields (`agent`, `phase`, `error_class`, `error_message`, `failed_at`). Proceed anyway if optional fields missing, marking them `null`.

### Step 2 — Compute slug, check idempotency

Slug as defined. If `Incidents/<today>_<slug>.md` exists → overwrite (same incident re-reported).

### Step 3 — Classify severity

| Severity | Criterion |
|----------|-----------|
| P0 | data loss, corruption, security exposure |
| P1 | daily-use source offline |
| P2 | weekly-use source offline, or recurring transient |
| P3 | one-off transient on non-critical source |

Cannot determine → default P2 with annotation.

### Step 4 — Cross-reference

- Master refresh report: grep `11_Documents_and_Reports/Refresh/YYYY-MM-DD_*.md`; link if present.
- Prior incidents same `source_id`: grep `Incidents/` last 90 days; link up to 5.
- Prior incidents same `error_class`: grep last 30 days; link up to 3.

### Step 5 — Scaffold the file

Pipe the validated payload to `scripts/new_incident.py`:

```bash
echo '{"agent": "...", "phase": "probe", "error_class": "unreachable", "error_message": "...", "failed_at": "...", "source_id": "..."}' \
  | python3 scripts/new_incident.py
```

The script writes `11_Documents_and_Reports/Incidents/YYYY-MM-DD_<slug>.md` with valid frontmatter, error-verbatim code block, and placeholder sections. **Idempotent per day+slug** — overwrites the same file for re-reports.

Then replace placeholders in Summary, Reproduction, Likely cause (hypothesis), and Next actions with substantive content. Section order stays fixed.

### Step 6 — Emit report payload

## Constraints

- **CRITICAL:** never embellish. Error message copied verbatim, no paraphrase.
- **CRITICAL:** never classify cause as fact. `likely_cause` always labelled hypothesis.
- **CRITICAL:** idempotent per day+slug. Same incident re-reported → overwrite.
- **CRITICAL:** never block. Internal failure of this skill → write raw payload to `docs/hook_logs/failure-reporter_YYYY-MM-DD.log` and exit loud; never silent success.
- Next actions cap: 5. Each has a named owner.
- Always cross-link to master refresh report when present.

## Reference

Incident frontmatter:

```yaml
---
title: "<source or agent> — <error class>"
note_type: incident_report
source_id: <id or null>
agent: <caller>
command: <command>
phase: <phase>
error_class: <class>
severity: P0 | P1 | P2 | P3
status: open | acknowledged | investigating | resolved | wontfix
started_at: YYYY-MM-DDTHH:MM:SSZ
failed_at: YYYY-MM-DDTHH:MM:SSZ
resolved_at: null | YYYY-MM-DDTHH:MM:SSZ
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [incident, refresh, <source_id>, <error_class>]
---
```

Status lifecycle: `open → acknowledged → investigating → resolved` (or `wontfix`). On status change: update frontmatter + append dated bullet under new `## Resolution` section; body byte-exact.

## Scripts

- [`scripts/new_incident.py`](scripts/new_incident.py) — scaffolds the incident from the caller's JSON payload. Validates phase/error_class enums, defaults severity to P2 if absent, computes slug, idempotent per day+slug.

## Dependencies

- Architecture: `20_System_Governance/Architecture/Source_Architecture.md`.
- Callers: `refresh-orchestrator`, `source-scout`, `repo-reporter`, `ingestion-*`.
- Sibling skills: `decision-logger` (for the fix decision), `task-marshal` (for the follow-up task).
- Log path: `docs/hook_logs/failure-reporter_YYYY-MM-DD.log`.

## Cross-references

- `CLAUDE.md` §12 risk classification.
