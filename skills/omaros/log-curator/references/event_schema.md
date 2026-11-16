# Event schema — `docs/event_logs/YYYY-MM-DD.jsonl`

Append-only JSONL. One event per line. Every event carries the following core fields; kind-specific fields extend them.

## Core fields (every event)

| Field | Type | Notes |
|-------|------|-------|
| `ts` | ISO-8601 UTC datetime | timestamp of the event, set at write time |
| `kind` | enum | `commit` / `error` / `skill_invoked` / `hook_fired` / `incident` / `session_start` / `session_end` |
| `source` | string | identifier of the producing hook or process |

## Kind-specific fields

### `commit` (emitted by `post_commit_log_writer.py`)

```json
{
  "ts": "2026-04-17T15:42:03+00:00",
  "kind": "commit",
  "source": "post_commit_log_writer",
  "sha": "abcdef0123456789…",
  "short_sha": "abcdef0",
  "author": {"name": "Omar", "email": "…"},
  "author_date": "2026-04-17T15:41:58+01:00",
  "commit_date": "2026-04-17T15:41:58+01:00",
  "subject": "Add log-curator skill",
  "theme": "feature",
  "is_merge": false,
  "files_changed": 3,
  "insertions": 140,
  "deletions": 2,
  "domains": {".claude": 2, "docs": 1},
  "paths": ["…"],
  "truncated_paths": false,
  "push_state": "pushed" | "ahead_by_N" | "no_upstream" | "unknown"
}
```

Theme enum (classified from commit subject prefix): `feature`, `bug_fix`, `refactor`, `docs`, `tests`, `architecture`, `release`, `auto_commit`, `adr`, `chore`.

### `error` (future hook)

```json
{
  "ts": "…",
  "kind": "error",
  "source": "<hook or tool>",
  "tool_name": "Bash" | "Edit" | …,
  "error_class": "permission" | "timeout" | "schema" | "unknown",
  "error_message": "…",
  "severity": "P0" | "P1" | "P2" | "P3"
}
```

### `skill_invoked` (future hook)

```json
{
  "ts": "…",
  "kind": "skill_invoked",
  "source": "skill_invocation_log",
  "skill": "reflection-writer",
  "trigger": "user_phrase" | "slash_command" | "inter_skill",
  "session_id": "…"
}
```

### `hook_fired`

```json
{
  "ts": "…",
  "kind": "hook_fired",
  "source": "<hook name>",
  "event": "PreToolUse" | "PostToolUse" | "Stop" | …,
  "matcher": "Bash(git commit*)" | null,
  "outcome": "ok" | "blocked" | "warn" | "error"
}
```

### `incident`

Mirror of the frontmatter of an incident note produced by `failure-reporter`. Emitted so the event stream aggregates what already lives as a narrative note.

### `session_start` / `session_end`

```json
{"ts": "…", "kind": "session_start", "source": "session_logger", "host": "…", "user": "…"}
{"ts": "…", "kind": "session_end", "source": "session_logger", "duration_s": 1234}
```

## Invariants

- **Append-only.** Never modify existing lines. New events always go at the end of today's file.
- **UTC timestamps.** The `ts` field is always UTC with explicit offset; localisation happens at render time.
- **One event per line.** No pretty-printed JSON. Each line is a single complete JSON object.
- **Schema additivity.** New fields may be added to any kind; consumers must ignore unknown fields. Removing a field is a breaking change and requires a schema version bump.
- **Malformed-line tolerance.** Readers skip lines that fail `json.loads` with a warning; they never raise.
