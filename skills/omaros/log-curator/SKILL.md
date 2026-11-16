---
name: log-curator
description: "Query and summarize explicitly authorized existing structured event logs, with source timestamps, bounded coverage and no log mutation."
license: Proprietary. OmarOS internal.
---

# Log Curator

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

The read side of OmarOS's structured event log. Existing records may contain one JSON object per line under `docs/event_logs/YYYY-MM-DD.jsonl`. Check the actual producer and coverage before treating these records as current or complete. This skill queries those files, filters and aggregates the stream, and renders the result as a narrative summary, a markdown table, or a machine-readable JSON blob. It is the answer to *"what happened today / this week / during the auth bug / while I was asleep"*.

**The skill does not write events.** The existing producer owns its records; this method does not activate a logging hook or telemetry. The skill is strictly a reader and synthesiser.

## Quick reference

| User intent | Action |
|-------------|--------|
| "what happened today" | `summarize_day.py <today>` → narrative + counts |
| "commits since Monday" | `query_events.py --kind commit --since 2026-04-13` |
| "errors this week" | `query_events.py --kind error --since 7.days.ago` |
| "commit velocity by domain" | `query_events.py --kind commit --group-by domain` |
| "which skills fired today" | `query_events.py --kind skill_invoked --date today --render table` |
| "/brief-logs" | `summarize_day.py <today> --terse` |
| "weekly rollup" | `summarize_day.py --week YYYY-Www` |

## When this skill runs

- User asks for a log summary, commit velocity, error frequency, or timeline.
- `/logs`, `/events`, `/brief-logs` (future slash commands) invoked.
- Another skill needs a structured event-stream slice (e.g. `execution-tracer` asking for commits in a task's time range).

Do **not** run for:

- Writing a new commit → use the common coordinator publication flow.
- Capturing an inbox fragment → `capture`.
- Logging a decision → `decision-logger`.
- Writing an execution checkpoint → use the current assignment’s curated progress operation.
- Diagnosing a failure (formatting it as an incident) → `failure-reporter`.

## Inputs

| Input | Required | Notes |
|-------|:--------:|-------|
| date range | ✅ | today / yesterday / ISO date / `N.days.ago` / week / month |
| event kinds | optional | filter: `commit`, `error`, `skill_invoked`, `hook_fired`, `incident`, `session_start`, `session_end` |
| filters | optional | domain, author, theme, severity, substring-match |
| aggregation | optional | `group-by: {kind, domain, theme, hour, author}`; `count` / `sum-files-changed` / `sum-insertions` |
| render | optional | `narrative` (default for summaries) / `table` / `json` / `timeline` |

## Outputs

Emitted to stdout (not written to the vault); the caller decides whether to persist. Three render modes:

- **narrative** — prose paragraphs with counts and notable events. Default for "what happened today".
- **table** — markdown table. Default for filtered queries.
- **json** — structured, for composition with other skills.

## Procedure

### Step 1 — Resolve the date range

Accept absolute dates (`2026-04-17`), relative (`today`, `yesterday`, `N.days.ago`, `this_week`, `this_month`), or explicit `--since`/`--until`. Expand to an inclusive list of `YYYY-MM-DD` files.

### Step 2 — Load events

Run `python3 scripts/query_events.py` with the resolved args. It reads each `docs/event_logs/YYYY-MM-DD.jsonl`, filters by kind/domain/author/theme/severity, and emits the result on stdout.

For summaries, run `python3 scripts/summarize_day.py <date>` which produces counts, top themes, domain breakdown, and a notable-events list.

### Step 3 — Render

Per `--render`:

- **narrative**: prose paragraphs. Opens with one sentence: *"On <date>, <N> commits touched <M> files across <K> domains."* Follows with theme breakdown, notable domains, flagged errors, and a closing line.
- **table**: markdown table. Columns depend on kind. For commits: `time | sha | theme | domain | files | subject`.
- **json**: dump the event list as-is, with light decoration.
- **timeline**: chronological bullet list with one line per event: `HH:MM [kind] source — summary`.

### Step 4 — Flag anomalies (summaries only)

Compare the day's counts to the 7-day trailing mean. Flag:

- Commit count ±2σ from trailing mean.
- Any `error` or `incident` events (always surface).
- Any commit with >1000 lines changed (potential bulk op).
- Any domain that received its first commit today (new topology).

### Step 5 — Return

Stdout contains the rendered output. No files written.

## Constraints

- **CRITICAL:** never write to `docs/event_logs/`. The log stream is append-only and hook-owned. This skill is read-only.
- **CRITICAL:** never fabricate events. If a query returns zero results, say so.
- **CRITICAL:** handle malformed lines gracefully. A line that is not valid JSON is skipped with a warning to stderr, never stops the query.
- Summaries are deterministic: re-running on the same date produces the same output (up to trailing-mean anomaly flags, which depend on window).
- Timezones: event timestamps are stored in UTC; display in local time unless `--utc` is passed.

## Reference

- [`references/event_schema.md`](references/event_schema.md) — canonical JSONL event schema (kind, required + optional fields per kind).
- [`references/query_recipes.md`](references/query_recipes.md) — common query patterns.

## Scripts

- [`scripts/query_events.py`](scripts/query_events.py) — filter + aggregate + render. The workhorse.
- [`scripts/summarize_day.py`](scripts/summarize_day.py) — daily narrative summary with anomaly flags.
- [`scripts/append_event.py`](scripts/append_event.py) — **for hook authors only**, not for this skill. Shared helper that hooks call to append events with consistent formatting.

## Evidence and privacy boundaries

Read only the log set named by the user or explicitly authorized by the task.
Daemon logs, conversation data and sync state are private; a general status
question does not authorize archiving or transmitting them. Report the producer,
covered interval, filters and missing periods. An absent event is not proof that
an operation did not happen. Do not enable old hooks, event emitters or telemetry
to fill a gap. Current assignment progress belongs to the common Constellation
entry; preserve historical logs without treating them as active configuration.
