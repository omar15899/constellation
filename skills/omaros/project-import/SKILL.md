---
name: project-import
description: 'Import a project into OmarOS on the mandatory dual-track pattern: AI-summarised semantic surface in 05_Projects/<project>/ AND a symlink-bridged zero-copy raw surface in 09_Data_Sources/Project_Repos/. Enforces Project_Import_Dual_Track policy. Use when an existing project (code repo, research, LaTeX, data) must become a first-class OmarOS citizen, or when an existing track-1-only entry needs the track-2 symlink bridge added retroactively.'
---

# Skill — project-import

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

> Operational entry point for the dual-track import invariant. Governed by
> [`20_System_Governance/Policies/Project_Import_Dual_Track.md`](/Users/omarkhalil/OmarOS/20_System_Governance/Policies/Project_Import_Dual_Track.md).

## When to invoke

- A project exists upstream on disk (or on a remote the user has access to) and needs to
  become queryable, summarisable, and navigable from inside OmarOS.
- An existing OmarOS project entry is track-1-only and needs the track-2 symlink bridge
  added retroactively (compliance backfill).
- A brand-new project is being scaffolded and must be born dual-track.

## Inputs

- `project_name` — canonical slug, snake_case, matches `05_Projects/<project>/`.
- `upstream_path` — absolute path to the project's upstream root on disk.
- `kind` — one of `code_repo | research | latex | data | mixed` (determines which AI
  summary agent drives track 1).
- `refresh_cadence` — SLA in hours for the track-1 refresh (default 168 = one week).
- `privacy` — `personal | sensitive`.

## Procedure

### Step 1 — Preconditions

1. Verify the upstream root exists and is readable.
2. Verify `05_Projects/<project>/` does not yet exist OR is track-1-only (no symlink yet).
3. Verify `09_Data_Sources/Project_Repos/<project>/` does not yet exist.
4. Verify no entry for `<project>` in `sources.yaml` yet (unless backfilling).

### Step 2 — Track 2 (symlink bridge)

```
mkdir -p 09_Data_Sources/Project_Repos/<project>
ln -s <upstream_abs_path> 09_Data_Sources/Project_Repos/<project>/source
```

If `<upstream>/logs` exists and is load-bearing:
```
ln -s <upstream_abs_path>/logs 09_Data_Sources/Project_Repos/<project>/logs
```

If `<upstream>/history` (or equivalent) exists:
```
ln -s <upstream_abs_path>/history 09_Data_Sources/Project_Repos/<project>/history
```

Write `.snapshot.json`:
```json
{
  "registry_id": "<project>",
  "upstream_path": "<upstream_abs_path>",
  "last_commit_hash": "<git rev-parse HEAD or null>",
  "last_refresh": "<ISO timestamp>",
  "adapter": "live_symlink",
  "notes": ""
}
```

### Step 3 — Source card + registry entry

Create `20_System_Governance/Sources/cards/<project>.md` using the Reflexiones_a_Latex
card as the structural template (permanent symlink invariant, adapter table, refresh
procedure, failure modes, SLA, cross-references).

Add to `20_System_Governance/Sources/sources.yaml`:
```yaml
  - id: <project>
    name: <human-readable>
    type: repo
    location: <upstream_abs_path>
    adapter: local_git       # or filesystem_scan for non-git projects
    mode: live_symlink
    symlink_path: 09_Data_Sources/Project_Repos/<project>/source
    symlink_target: <upstream_abs_path>
    sync_direction: inbound
    truth_status: authoritative
    semantic_destination:
      - 05_Projects/<project>/
    raw_destination:
      - 09_Data_Sources/Project_Repos/<project>/
    ingestion_agent: <ingestion-repos | ingestion-latex | project-reporter>
    refresh:
      automatic: true
      command: /refresh-source <project>
      sla_hours: <refresh_cadence>
      owner: refresh-orchestrator
    validation:
      checks: [symlink_resolves, git_reachable, last_commit_hash_recorded]
      on_failure: incident
    privacy: <privacy>
    ai_permissions: { read: true, write: false, index: true }
    state: live
    card: cards/<project>.md
    notes: |
      Imported via project-import skill on <date>. Dual-track:
      track 1 (AI summary) at 05_Projects/<project>/, track 2
      (zero-copy symlink) at 09_Data_Sources/Project_Repos/<project>/.
      Upstream is authoritative; vault is a read-only index.
```

### Step 4 — Track 1 (AI-summarised surface)

Invoke `/new-project <project>` (or scaffold manually) to produce under
`05_Projects/<project>/`:

- `README.md` — project MOC
- `Vision.md`
- `Architecture.md`
- `Status/<date>.md` — initial status snapshot
- `Decisions/` (empty, ready for ADRs)
- `Checkpoints/` (empty)
- `Open_Problems/`
- `Summaries/<date>.md` — initial summary of upstream state
- `Tasks.md`

### Step 5 — Initial AI summary

Dispatch the correct agent based on `kind`. For `code_repo`, **ingestion-repos**
runs first to produce the read-only summary card at
`08_Systems_and_Infrastructure/Repos/<repo>.md` (it is the internal subroutine
that owns that specific artefact), then `repo-reporter` writes the per-project
state report, then `project-reporter` writes the project-level status:

| `kind`         | Dispatch chain                                                                  |
| -------------- | ------------------------------------------------------------------------------- |
| `code_repo`    | `ingestion-repos` (summary card) → `repo-reporter` (state) → `project-reporter` |
| `research`     | `scholar` (literature note) → `project-reporter`                                |
| `latex`        | `ingestion-latex` → `project-reporter`                                          |
| `data`         | `ingestion-excel` → `project-reporter`                                          |

`ingestion-repos` is **not a user-facing entrypoint**; it is only invoked from
inside this skill. Inspect the available repository import tool and its
`internal_to: project-import` registry flag.
| `mixed`        | `project-reporter`                   |

The summary reads **through the symlinks** — it must cite specific paths under
`09_Data_Sources/Project_Repos/<project>/source/...` for every factual claim.

### Step 6 — ADR

Write an ADR under `20_System_Governance/Decisions/<date>_import_<project>.md` recording:

- Upstream path and kind
- Track-2 layout (which subtrees are symlinked)
- Track-1 agents responsible for summaries
- Refresh cadence
- Privacy classification
- Risk and reversibility

### Step 7 — Verify and hand off

Validate the imported structure, links and provenance against the declared scope.
An independent reviewer checks the result. The coordinator publishes authorized
paths through the common entry and verifies the exact remote branch and commit.

## Invariants enforced

- **Symlink-not-copy.** Track 2 must be a symlink. A directory of copied files is a defect.
- **Dual-track mandatory.** Track 1 without track 2, or track 2 without track 1, is a defect.
- **Source card mandatory.** No import is complete without a source card entry.
- **Citations mandatory.** Every track-1 claim must cite a track-2 path.
- **Zero-drift.** No sync operation ever copies bytes from track 2 into the vault.

## Opposite pattern

Do **not** use this skill for sources being deprecated (e.g. Apple Notes). Deprecation
uses the `one_shot_migration` adapter and the corresponding procedure; see
`20_System_Governance/Decisions/2026-04-11_apple_notes_one_shot_migration.md`.

## Cross-references

- [`Project_Import_Dual_Track`](/Users/omarkhalil/OmarOS/20_System_Governance/Policies/Project_Import_Dual_Track.md)
- [`cards/reflexiones_latex.md`](/Users/omarkhalil/OmarOS/20_System_Governance/Sources/cards/reflexiones_latex.md) — exemplar
- `project-reporter`, `repo-reporter`, `ingestion-repos`, `ingestion-latex`, `research-scribe`, `source-scout`
