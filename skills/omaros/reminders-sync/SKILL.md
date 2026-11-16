---
name: reminders-sync
description: 'Atomic, lossless, byte-faithful import of every reminder from the macOS Reminders app into OmarOS — with a verbatim raw landing zone in 09_Data_Sources/Apple_Reminders/ AND a semantic copy in 02_Tasks_and_Execution/Ledger/ (the canonical task-marshal format), bound 1-to-1 by reminder UUID. Use this skill whenever the user says "sync reminders", "actualiza los recordatorios", "pull Apple Reminders", "import reminders into the ledger", "sync my reminders app", "actualiza mis reminders y tasks", "reminders → tasks", or invokes /reminders-sync. Idempotent (running twice produces zero writes), propagates title/body/completion changes from Reminders to the ledger, never deletes a task when its reminder disappears (the orphan is reported instead). Uses chunked atomic AppleScript bulk getters so per-record alignment is guaranteed even on >1000-reminder lists where naive JXA bulk getters silently cross-assign bodies. Do NOT use for: logging new ad-hoc tasks from prose (→ task-marshal); one-off file-based OPML/JSON imports (→ ingestion-reminders agent).'
license: Proprietary. OmarOS internal.
outputSchema:
  $ref: 19_Metadata_and_Schema/Agent_Output_Schemas/writer_result.json
contract_invariants:
- '1-to-1 binding: each Apple reminder UUID maps to exactly one OmarOS task id, recorded in 02_Tasks_and_Execution/Ledger/.sync_state/reminders.json. Running the sync twice with no Reminders-side change produces zero writes and zero new tasks.'
- 'Two parallel copies: every synced reminder lives both in 09_Data_Sources/Apple_Reminders/by_reminder/<UUID>.json (raw verbatim) AND in 02_Tasks_and_Execution/Ledger/Daily/YYYY-MM-DD.md (task-marshal format). The state file is the bridge.'
- 'Atomic alignment: each AppleScript chunk is a single selector resolution shared by 8 bulk-getter AEs, so within a chunk ids[k] aligns with names[k] aligns with bodies[k] etc. We never zip across chunks — cross-chunk reconciliation is by UUID, not by index.'
- 'Completion propagation: a reminder marked complete in Apple → status:done + closed_at stamped in the ledger. A reminder un-completed → status:open + closed_at:null.'
- 'Title/body propagation: edits in Reminders rewrite the corresponding task in place via task-marshal''s update_task.py.'
- 'No silent deletion: a reminder removed from the app is reported as ''missing from remote'' but the corresponding task in the ledger is preserved (audit history).'
- 'Audit trail: every sync writes an immutable timestamped JSON snapshot to 09_Data_Sources/Apple_Reminders/snapshots/YYYY-MM-DD_HHMMSS.json before any classification or write. The snapshot persists even if the rest of the sync crashes.'
---

# Reminders Sync

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Live, deterministic, alignment-safe sync from the macOS Reminders app to the
OmarOS task ledger.

## Pipeline

```
Apple Reminders
       │
       ▼
fetch_reminders.py            (chunked atomic AppleScript)
       │           ┌─────────────────────────────────────────────┐
       ├──────────►│ 09_Data_Sources/Apple_Reminders/             │
       │           │   • snapshots/YYYY-MM-DD_HHMMSS.json (immut.)│
       │           │   • by_reminder/<UUID>.json (latest)         │
       │           │   • index.json (roll-up)                     │
       │           └─────────────────────────────────────────────┘
       ▼
dedup.classify()              (CREATE / UPDATE_STATUS / UPDATE_CONTENT / NOOP / missing)
       │
       ▼
log_task.py / update_task.py  (task-marshal pipeline → Daily/*.md)
       │
       ▼
state file rewrite            (.sync_state/reminders.json)
       │
       ▼
sync report                   (11_Documents_and_Reports/Reminders_Sync/YYYY-MM-DD.md)
```

## Why so much care

Apple's bulk getters in JXA (`reminders.id()`, `reminders.body()`, …) are
*not* atomic across separate property accessors when the source list is
large. We have first-hand evidence: a 1317-reminder import with the JXA
fetcher silently cross-assigned ~15 % of bodies to the wrong reminders.
This skill replaces that with a chunked AppleScript fetcher that issues the
8 bulk getters within a single tell block per slice — they share one
selector resolution and therefore one in-memory snapshot — so per-record
alignment is guaranteed by construction inside each chunk. Cross-chunk
reconciliation is always by stable UUID, never by list index.

## Files

- `scripts/fetch_reminders.py` — AppleScript wrapper. Chunked, atomic.
- `scripts/dedup.py` — pure classifier: hash, state I/O, action plan.
- `scripts/raw_landing.py` — writes the 09_Data_Sources/Apple_Reminders/ artefacts.
- `scripts/sync.py` — orchestrator. Fetch → land → classify → write → state → report.
- `scripts/verify_alignment.py` — read-only audit: are the ledger bodies the
  ones their reminders actually have? Use after a sync to certify correctness.
- `scripts/link_existing.py` — fuzzy-match pre-existing tasks (no
  `reminders_app` tag) against current reminders. Outputs a review report;
  proposes merges, never auto-applies.
- `tests/test_dedup.py` — 16 unit tests on the pure dedup layer.

## When to use

- User wants to import every reminder into the ledger (first sync).
- User toggled completion or edited a reminder in the app and wants the
  ledger to catch up (subsequent sync).
- User wants to certify ledger ↔ reminders alignment is intact after past
  drift or recovery.
- User wants candidate links between pre-existing tasks and reminders.

Do **not** use for:

- Free-form prose → tasks (→ `task-marshal`).
- File-based OPML/JSON imports of Reminders exports (→ `ingestion-reminders`
  agent — different pipeline).

## Invocation

```bash
# Full live sync (writes raw landing + ledger updates)
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts/sync.py

# Plan only — fetch + classify, no writes
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts/sync.py --dry-run

# Restrict to specific Apple lists
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts/sync.py --only-lists Tareas,Compras

# Skip already-completed reminders on first import (years of done items)
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts/sync.py --skip-completed

# Use a cached fetch JSON (faster iteration)
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts/fetch_reminders.py /tmp/r.json
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts/sync.py --dump /tmp/r.json

# Verify ledger ↔ reminders alignment after a sync
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts/verify_alignment.py \
    --remote /tmp/r.json --write-report

# Surface candidate matches between pre-existing tasks and reminders
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/scripts/link_existing.py \
    --remote /tmp/r.json --threshold 0.85 --write-report
```

## The two parallel copies

Every reminder that has ever passed through this skill exists in two places
simultaneously:

1. **Raw verbatim** — `09_Data_Sources/Apple_Reminders/by_reminder/<UUID>.json`
   contains the un-normalised dict the fetcher returned (id, list, name,
   body, completed, priority, due_date, creation_date, completion_date) plus
   a `_synced_at` timestamp. Overwritten on every sync. Plus an immutable
   `snapshots/YYYY-MM-DD_HHMMSS.json` of the full fetch for audit.
2. **Semantic** — `02_Tasks_and_Execution/Ledger/Daily/YYYY-MM-DD.md` holds
   the task in canonical task-marshal yaml-block form. Tagged
   `reminders_app` and `reminder_<list-slug>`.

The two copies are bound by `02_Tasks_and_Execution/Ledger/.sync_state/reminders.json`
which maps reminder UUID → ledger task id. That state is the system of
record for the binding; both folders can be regenerated from it plus a
fresh fetch.

## Field mapping

| Apple field        | Ledger task field    | Notes                                              |
| ------------------ | -------------------- | -------------------------------------------------- |
| `name`             | `title`              | stripped                                           |
| `body`             | `body`               | verbatim; "" → null                                |
| `completed`        | `status`             | true → done, false → open                          |
| `completion_date`  | `closed_at`          | only when completed                                |
| `creation_date`    | `created_at`         | truncated to minute                                |
| `due_date`         | `when`               | date portion only                                  |
| `priority`         | `priority`           | 1→P0, 5→P1, 9→P2, 0→null                           |
| `list` name        | tags `reminder_<slug>` + `reminders_app` | always |

After CREATE, the task also passes through task-marshal's
`classify_tags.py`, gaining the standard auto-tag taxonomy on top.

## Dedup semantics (deep)

Two layers, applied in order:

1. **UUID** (primary). State maps `reminder_id → task_id`. This is the 1-to-1
   binding.
2. **Content hash** = `sha256(norm(title) | norm(body))`. `norm()` does
   unicode NFC + whitespace collapse + casefold. This is the *safety net*
   used when:
   - State file is lost or corrupted → rebuild bindings against existing
     ledger tasks instead of duplicating.
   - A reminder is deleted in Apple and recreated with the same content →
     don't dupe.
   - A user manually logged a task with the same content before first sync →
     don't dupe.

The classifier is a pure function of `(remote, state, existing_tasks)`.
Same inputs → same outputs. See `tests/test_dedup.py`.

## State file

`02_Tasks_and_Execution/Ledger/.sync_state/reminders.json`:

```json
{
  "version": 1,
  "last_sync": "2026-04-24T12:34:56",
  "reminders": {
    "x-apple-reminder://UUID": {
      "task_id": "2026-04-18-003",
      "hash": "<sha256 of (norm(title)|norm(body))>",
      "completed": false,
      "last_seen": "2026-04-24T12:34:56",
      "list": "Recordatorios",
      "title": "<short echo for debugging>"
    }
  }
}
```

Hand-editable, idempotently rewritten on every sync.

## macOS permissions

The running process needs the "Reminders" entitlement
(System Settings → Privacy & Security → Reminders). Without it, osascript
returns an empty array silently — no error.

## Reports

Every non-dry-run sync writes:

- `11_Documents_and_Reports/Reminders_Sync/YYYY-MM-DD.md` — sync report
  (counts + per-task one-liners + missing reminders).
- An immutable raw snapshot in
  `09_Data_Sources/Apple_Reminders/snapshots/YYYY-MM-DD_HHMMSS.json`.

`verify_alignment.py --write-report` adds:

- `11_Documents_and_Reports/Reminders_Sync/Verify_<timestamp>.md`.

`link_existing.py --write-report` adds:

- `11_Documents_and_Reports/Reminders_Sync/Link_Candidates_<timestamp>.md`.

## Recovery (cherry-pickable, no destructive ops)

The coordinator may publish independently reviewed, authorized phases as separate
commits; private raw landing files remain local. If a phase produces wrong results, `git revert <hash>` rolls back
that phase only — nothing else is affected. The skill never runs
`git reset --hard`, never amends, never rewrites history.

## Procedure (agent)

1. On request to sync: `uv run scripts/sync.py`. The fetch is slow
   (~5–7 min for ~1300 reminders due to AppleEvent overhead) — that's
   inherent, not a bug.
2. Parse stdout JSON `{"total_remote": N, "created": …, "updated_status": …,
   "updated_content": …, "noop": …, "missing": …}` and report counts +
   report path.
3. Hand authorized deliverables to the coordinator for review and granular publication; keep private snapshots and logs out of Git.
4. After significant runs, optionally `verify_alignment.py` to certify
   ledger ↔ reminders consistency.

## Dependencies

- `task-marshal/scripts/log_task.py`, `update_task.py`, `aggregate.py`.
- `osascript` (ships with macOS).
- "Reminders" privacy entitlement granted to the running process.

## Cross-references

- `task-marshal/SKILL.md` — downstream consumer; canonical ledger schema.
- For file-based Reminders imports, use the available import tool with the same ledger and provenance contract.
  (different use case).
- `CLAUDE.md` §7 — routing taxonomy. This skill is INFRA + INGEST.
