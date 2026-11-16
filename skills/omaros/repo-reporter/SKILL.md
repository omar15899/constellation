---
name: repo-reporter
description: 'Write per-repository state reports under 11_Documents_and_Reports/Project_State/ by consuming git diffs from tracked external repositories. Use this skill when the user invokes /repo-report, /project-refresh, /sync-repos, or says "state of repo X", "what happened in Y since last refresh", "repo report for Z", "escribe el estado del repo X". Turns `git log <since>..HEAD` and `git diff --stat` into a structured, idempotent-per-day report: commit themes, files changed by directory, surfaced TODOs/FIXMEs, related vault notes, open tasks, capped next-actions. Read-only on the clone — never commits, never pushes, never modifies the upstream. Do NOT trigger for writing inside the project''s vault tree (project-reporter), for ingesting new content from a repo (ingestion-repos), or for reflective essays on a repo (scholar).'
license: Proprietary. OmarOS internal.
---

# Repo Reporter

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Owns `11_Documents_and_Reports/Project_State/` — the only location for per-repository state reports. One report per repo answers: *what happened since the last refresh, what is in flight, what is blocking*. Idempotent per day: re-running the same day overwrites, never duplicates. Read-only on the clone.

## Quick reference

| Command / intent | Action |
|------------------|--------|
| `/repo-report <slug>` | single-repo report |
| `/project-refresh <slug>` | this skill + follow-up (dashboard refresh, etc.) |
| `/sync-repos` | fan-out to all repos in `tracked_repos.yaml` |
| "state of repo X" | single-repo report for X |

## When this skill runs

- Scheduled or manual refresh of a tracked repo.
- User asks for the state of a specific repo.

Do **not** run for:

- Writing inside `05_Projects/<slug>/` → `project-reporter`.
- Ingesting new content from the repo → `ingestion-repos`, `ingestion-latex`.
- Reflective essay on the repo's trajectory → `scholar`.

## Inputs

| Input | Required | Source |
|-------|:--------:|--------|
| repo slug | ✅ | `tracked_repos.yaml` `id` field |
| `since` anchor | optional | commit hash or date; defaults to prev report's `head` |

## Outputs

| Artefact | Path |
|----------|------|
| state report | `11_Documents_and_Reports/Project_State/<slug>/YYYY-MM-DD.md` |

On failure: dispatch `failure-reporter` with `error_class: unreachable`.

Return:

```
artefact: <path>
project: <slug>
range: <since> → <head>
commits: <int>
files_changed: <int>
todos_surfaced: <int>
open_tasks: <int>
state: active | dormant | blocked | archived
```

## Procedure

### Step 1 — Resolve the source

Read `20_System_Governance/Sources/tracked_repos.yaml`, find entry by `id`. Resolve `clone_path`. Verify it exists and is a git repo.

On failure: dispatch `failure-reporter`, return.

### Step 2 — Resolve the `since` anchor

1. Most recent prior report at `Project_State/<slug>/` → use its `head`.
2. No prior → default `--since="30.days.ago"`.
3. User passed explicit `since` → use that.

### Step 3 — Compute the diff summary

Run the bundled script:

```bash
python3 scripts/compute_diff.py <clone_path> <since> [<until>]
```

It emits a JSON blob on stdout with: `head`, `branch`, `commits[]` (with `hash`, `author`, `date`, `subject`, `theme`), `themes{}` (counts by theme), `files_by_dir{}`, `todos[]` (with `file`, `line`, `text`), and aggregate `counts`. Read-only on the clone; never fetches, commits, or pushes. The skill body then consumes this JSON to produce the canonical report.

### Step 4 — Verify classification

The script classifies commits by subject-line prefix (`feat`/`fix`/`refactor`/`docs`/`test`/`arch`/`release` → theme; otherwise `chore`). Spot-check a handful; re-classify manually if the author uses non-conventional prefixes.

| Prefix / keyword | Theme |
|------------------|-------|
| `feat`, `feature`, `add` | feature |
| `fix`, `bug`, `hotfix` | bug_fix |
| `refactor`, `cleanup` | refactor |
| `docs`, `readme` | docs |
| `test`, `spec` | tests |
| `arch`, `architecture` | architecture |
| `release`, `version`, `bump` | release |
| — | chore |

### Step 5 — Group files by directory

`git diff --name-only <since>..HEAD` → top-level directory → count → one-line purpose (from `README.md` or inferred).

### Step 6 — Surface TODOs

Grep added hunks for `TODO|FIXME|XXX|HACK`. Include `file:line`.

### Step 7 — Cross-reference vault

Grep `05_Projects/<slug>/` for mentions of the changed files. Wikilink matches.

### Step 8 — Fetch open tasks

Invoke `task-marshal` with filter `project: <slug>, status ∉ {completed, cancelled}`.

### Step 9 — Write the report

Overwrite `Project_State/<slug>/YYYY-MM-DD.md` with canonical body (Snapshot, Change summary table, Commits list, Files by directory, Open threads, Related vault notes, Blockers + open tasks, Next actions). Keep prior days' reports.

### Step 10 — Emit report payload

## Constraints

- **CRITICAL:** read-only on the clone. No commits, no pushes, no modifications.
- **CRITICAL:** idempotent per day. Overwrite, never duplicate.
- **CRITICAL:** no hallucinated commits. Every cited commit must exist in `git log`.
- **CRITICAL:** no speculative next actions. Only supported by current state (open TODOs, open tasks, failing CI).
- **CRITICAL:** failure is explicit. Broken clone / failed fetch → `failure-reporter` and return; no partial report.
- One report = one project. Consolidation is `/sync-repos`.
- Next actions capped at 3.

## Reference

State classification:
- `active` if commits in last 7 days.
- `dormant` if none in 30 days.
- `blocked` if explicit blocker in `task-marshal` query.
- `archived` if `tracked_repos.yaml` marks it so.

Frontmatter (see spec in canonical body):

```yaml
---
title: "<project> — project state"
note_type: project_state
project: <slug>
upstream: <git url>
branch: <branch>
head: <sha>
since: <sha or timestamp>
probed_at: YYYY-MM-DDTHH:MM:SSZ
state: active | dormant | blocked | archived
commits_in_range: <int>
files_changed: <int>
---
```

## Scripts

- [`scripts/compute_diff.py`](scripts/compute_diff.py) — read-only git-diff summariser. CLI: `compute_diff.py <clone_path> <since> [<until>]`. Emits structured JSON with commits, theme counts, files by directory, and TODO hits.

## Dependencies

- Registry: `20_System_Governance/Sources/tracked_repos.yaml`.
- Sibling skills: `project-reporter`, `task-marshal`, `failure-reporter`.
- Commands: `/repo-report`, `/project-refresh`, `/sync-repos`.

## Cross-references

- `CLAUDE.md` §7 routing.
