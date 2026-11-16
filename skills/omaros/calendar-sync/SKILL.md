---
name: calendar-sync
description: Reactive, sub-minute mirror of every event in macOS Calendar.app into OmarOS — verbatim raw landing zone in 09_Data_Sources/Calendar/ AND a per-day markdown surface in 01_Daily_Life/Calendar/<YYYY-MM-DD>.md. Runs as a launchd-managed daemon polling every 5 seconds (configurable). Use when the user says "sync calendar", "actualiza el calendario", "agenda", "qué eventos tengo", or whenever today's plan needs the live Calendar view. Skip for past-event archaeology; this skill is the live-window reflector.
---

# calendar-sync

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Live mirror of `Calendar.app` events in a rolling
`[today - LOOKBACK, today + LOOKAHEAD]` window into the vault, refreshed
every few seconds by a launchd daemon.

## Two surfaces

```
09_Data_Sources/Calendar/
├── README.md
├── index.json                ← roll-up: {uid: {path, calendar, summary, start}}
├── snapshots/                ← immutable per-cycle dumps (only when changes occur)
│   └── YYYY-MM-DD_HHMMSS.json
└── by_event/                 ← latest values per UID
    └── <safe_uid>.json

01_Daily_Life/Calendar/
└── YYYY-MM-DD.md             ← per-day markdown (frontmatter + event list)
```

## Pipeline

1. **`fetch_calendar.py`** — AppleScript chunked fetch with per-chunk atomic
   property reads (same alignment guarantees as `reminders-sync`). Output:
   list of event dicts in the configured window.
2. **`sync.py`** — classify each event against the prior `sync_state`:
   `CREATE` / `UPDATE` (content or day moved) / `DELETE` (UID disappeared
   from the window) / `NOOP`. Writes raw landing + per-day markdown only
   when there is at least one non-NOOP action (`--changes-only`).
3. **`daemon.py`** — long-running launchd-managed loop. Default cadence:
   5 seconds. Self-throttles when fetch exceeds the interval.

## Idempotency

The sync state lives at
`02_Tasks_and_Execution/Ledger/.sync_state/calendar.json` and stores, per
UID: `hash`, `day`, `summary`. Running the sync twice in a row with no
calendar change writes nothing. The per-day markdown writer compares the
new content against the on-disk file before writing, so an Obsidian
watcher does not see spurious changes.

## Window

Default `LOOKBACK = 7` days, `LOOKAHEAD = 30` days. Configurable per
invocation via `--lookback` / `--lookahead`. The daemon picks up env var
`SYNC_EXTRA_FLAGS` if you want to widen the window persistently (e.g.
`SYNC_EXTRA_FLAGS="--changes-only --lookback 30 --lookahead 90"`).

## Install / uninstall

```bash
# Install (or reinstall) the daemon under launchd
/Users/omarkhalil/GitHub/Constellation/skills/omaros/calendar-sync/scripts/install_launchd.sh

# Stop and remove
launchctl unload ~/Library/LaunchAgents/com.omaros.calendar-sync.plist
rm ~/Library/LaunchAgents/com.omaros.calendar-sync.plist

# Live logs
tail -f docs/calendar_sync_daemon.log docs/calendar_sync_daemon.err
```

The first run requires granting Calendar access to the process executing
osascript — macOS will prompt once, then remember. If you see
`Not authorized to send Apple events to Calendar`, open
`System Settings → Privacy & Security → Automation` and tick the relevant
box for the parent (Terminal / launchd).

## Manual invocation

```bash
# One-shot sync, full output
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/calendar-sync/scripts/sync.py

# Dry run: classify only, no writes
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/calendar-sync/scripts/sync.py --dry-run

# Wider window
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/calendar-sync/scripts/sync.py --lookback 30 --lookahead 90

# Bench the AppleScript fetch in isolation
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/calendar-sync/scripts/fetch_calendar.py /tmp/cal.json
```

## Event → task automation

Events whose title carries an explicit task marker are auto-logged to the
task ledger via `task-marshal/log_task.py` when `--log-tasks` is set
(daemon plist enables this by default).

Recognised markers:

| Marker | Example title | Resulting task title |
|---|---|---|
| `TODO:` | `TODO: Llamar al banco` | `Llamar al banco` |
| `TASK:` | `TASK:Comprar pan` | `Comprar pan` |
| `[task]` | `[task] Revisar PR de Pedro` | `Revisar PR de Pedro` |
| `[todo]` | `[todo] Mandar el formulario` | `Mandar el formulario` |
| `#hashtag` (anywhere) | `Daily standup #engie` | preserves title, adds `engie` tag |

The resulting task carries:

- `tags: [from_calendar_event, calendar_task, calendar_explicit_task,
  <each-hashtag-as-its-own-tag>, …auto-classified-tags]`
- `when` = event start date (YYYY-MM-DD)
- `body` = verbatim archive of the event (calendar, start, end, location,
  URL, notes)

**Idempotency**: every event UID is logged at most once. The assigned
`task_id` is stored back in `02_Tasks_and_Execution/Ledger/.sync_state/
calendar.json`, so subsequent daemon ticks don't double-log.

## Out of scope

- **Outbound writes** (creating / editing events from the vault). Calendar
  is read-only here.
- **Recurring-event materialisation across years.** AppleScript already
  expands recurrences into individual instances within the window we ask
  for; we do not maintain a separate recurrence graph.
- **Travel-time auto-blocks**, **conflict detection**, **meeting note
  bootstrap**. Those are downstream consumers — they live elsewhere and
  read from `01_Daily_Life/Calendar/`.
