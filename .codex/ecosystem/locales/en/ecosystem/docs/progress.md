# Recoverable progress and personal journal

The coordinator maintains curated checkpoints for substantive work: objectives,
current state, results, decisions, findings, evidence, open issues and next steps.
Record them when something important changes, before a handoff or closure, and
when resuming work. A small correction does not need another lifecycle. The agent
judges relevance; the runtime validates structure, identity and freshness, rather
than classifying the intellectual value of a result itself.

## Three responsibilities

Operational state remains in its existing store: private Git JSON or the portable
engine's SQLite database. `task_progress` belongs to the task and survives
replanning. Source history remains in Git. OmarOS receives a readable synthesis
and references; it does not replace source state or copy conversations, commands,
logs or raw results. Reusable scientific knowledge remains in OmarOS's own domain
notes and workflow, linked from the journal; there is no additional knowledge
system.

A task receives a UUID when its first checkpoint is saved. A new assignment has
a different UUID even if it reuses a session. Milestones have stable identities
and dates: repeating an ID and its content is idempotent; reusing an ID with
different content fails. Record a correction as another milestone, preserving
the chronology. Narrative does not approve checks, reviews, publications or
scientific results.

## Save at the source first

From a Git project, use the receiving workflow; from the hub, add `--repo` to
`ecosystem/cli.py workspace` commands. First query:

```sh
python3 .codex/ecosystem/cli.py workspace progress-show --repo .
```

This returns `task_progress`, `expected_task_start` and `revision`. The first
update uses the observed start and revision zero, without `task_uid`:

```json
{
  "expected_task_start": "START_RETURNED_BY_PROGRESS_SHOW",
  "expected_revision": 0,
  "source_alias": "personal-project",
  "checkpoint": {
    "id": "first-result",
    "summary": "First verified result and next decision",
    "visibility": "unknown",
    "snapshot": {
      "objectives": ["Result to achieve"],
      "current": "Current state and limitations",
      "completed": ["Work actually completed"],
      "decisions": ["Decision and reason"],
      "findings": ["Finding with its epistemic scope"],
      "verification": ["Check performed and result"],
      "unresolved": ["Issue that remains open"],
      "next_steps": ["Concrete next action"],
      "references": []
    }
  }
}
```

Send this object to `progress-update` through stdin. `source_alias` is optional
in the first checkpoint and immutable afterwards; it must match export
authorization where one exists. For subsequent updates, use `task_uid` and the
current revision, without `expected_task_start` or `source_alias`. An exact retry
of a lost first checkpoint preserves later milestones and creates no new UUID.

Fields contain plain-text syntheses, rather than executable blocks,
transclusions or embedded URLs. References use `{kind, label, value}` objects
with types `repository`, `commit`, `experiment` or `documentation`. Use precise
references to the repository, revision, result or documentation; do not include
URLs containing credentials, secret parameters or conversation paths. Format
limits are not a universal secret detector: responsible curation remains
necessary.

The portable engine uses the same `progress-show`, `progress-update`,
`progress-export` and `progress-ack` operations with `session_id`, `task_id` and
`agent_id`. Update and ack use the engine revision returned for the selected
task as `expected_revision`, rather than a separate milestone counter, and retain
replay through `request_id`; they do not use `expected_task_start`. Consult the
[protocol](../references/protocol.md) for the portable contract. Do not open a
second Git or portable contract to record the first contract's progress.

## Authorize a personal synthesis

The policy is local to the user, at `$CODEX_HOME/progress-journal.json`
(default `~/.codex/progress-journal.json`). An explicit `--policy` supports
another authorized configuration or isolated fixtures; never select it from a
checkpoint's content. Illustrative example:

```json
{
  "schema_version": 1,
  "target": {"root": "/absolute/path/to/vault"},
  "sources": [
    {"root": "/absolute/path/to/project", "alias": "personal-project", "visibility": "personal"}
  ]
}
```

The canonical root and alias must match exactly. Registering a repository as
`native` does not authorize its export; a nested repository does not inherit its
parent's permission either. An unknown or `restricted` source is excluded.
Furthermore, the latest checkpoint must be declared `personal` after its content
has been reviewed; earlier non-personal milestones are never exported. Do not
infer this classification from the project's name, data provider or remote.

The personal learning profile and its examples are not automatically exported
to the journal. A milestone may report its maintenance without copying its
content. Corporate or restricted data is not sent to the personal vault. Adding
a source requires explicit personal authorization for that scope; do not copy
the entire project registry into the policy.

## Deliver through the OmarOS receiver

After saving the checkpoint, prepare the projection:

```sh
python3 .codex/ecosystem/cli.py workspace progress-export --repo . --task-uid UUID
```

The result contains `envelope`. This operation **does not write to OmarOS**.
Retain or send the receiver only that curated object, rather than the complete
`status` result. The envelope fixes the UUID, personal history, content, note
path and destination. Hashes detect changes; they do not authenticate the sender.

Using the Python runtime and session of the OmarOS workflow, query
`journal-paths --source-root CANONICAL_PATH`, passing the envelope through stdin.
Declare the two returned paths in the receiver's plan, preserving an active
contract if one exists. Then run `journal-import --source-root CANONICAL_PATH`
with the same object. The policy is revalidated at the receiver. The note is
anchored to its creation day under
`11_Documents_and_Reports/Execution_Traces/`; the human-readable index is
`17_Dashboards/Constellation.md`.

The receiver validates Git ownership, the frozen destination, scope and metadata.
It rejects history regressions, milestone replacement, symbolic links,
independently owned notes and edits to the managed segment. Manual text after
the segment is preserved. Do not pre-create the dashboard with a placeholder:
let the receiver create the first managed document. Coordinate writers and
publication of the shared dashboard centrally; the lock serializes imports,
rather than creating a distributed transaction across all projects.

Receipt prepares a recoverable intent in Git's private directory before changing
the note or dashboard. If interrupted, resend **the same envelope** before
another milestone. Temporary files remain in that private directory. Atomic
replacement requires the vault and Git state to share a filesystem; a failure
preserves the source checkpoint and does not use an unsafe alternative write.

`journal-import` returns a `RECEIVED_LOCAL` receipt. At the source, send it to
`progress-ack` as `{task_uid, expected_revision, receipt}`. The current policy
and envelope are recomputed: an old receipt, or one for another note or
destination, does not confirm the current checkpoint. Remote publication still
passes through OmarOS's own checks, review, commit and finish; the local receipt
does not claim it. The closure indicator comes from the current workflow,
rather than a narrative sentence, and does not turn a hypothesis into a proven
result either.

## Recover without the vault

`progress-show` allows work to continue even when OmarOS or its remote is
unavailable. Read the latest results and outstanding issues, verify evidence
that may have changed, and save the next checkpoint when appropriate. Recover a
lost response through identity/replay, rather than restarting the assignment or
erasing rounds. A delivery failure does not erase local progress. Retry delivery
at the next milestone or resumption, and report any limitation that remains open.
