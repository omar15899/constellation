#!/usr/bin/env python3
"""
End-to-end sync: macOS Calendar.app → OmarOS vault.

Two artefacts are produced per run:

  1. Raw landing zone (09_Data_Sources/Calendar/)

       snapshots/<YYYY-MM-DD_HHMMSS>.json   immutable per-cycle dump
       by_event/<UID>.json                  latest values per event
       index.json                           lightweight roll-up

  2. Semantic surface (01_Daily_Life/Calendar/<YYYY-MM-DD>.md)

       One markdown file per day in the [today - LOOKBACK, today + LOOKAHEAD]
       window, regenerated only when the events of that day have changed.
       Frontmatter carries note_type=calendar_day, source=apple_calendar,
       and a content hash for idempotent regeneration.

Idempotency
-----------
A sync_state file at 02_Tasks_and_Execution/Ledger/.sync_state/calendar.json
records, per UID, a content hash. On every run we re-fetch, recompute hashes,
classify into CREATE / UPDATE / DELETE / NOOP, and write only what changed.
With --changes-only, NOOP cycles touch no disk at all.

Flags
-----
--dry-run             : classify only; print the plan; touch nothing.
--lookback DAYS       : window start, days before today (default 7).
--lookahead DAYS      : window end, days after today (default 30).
--changes-only        : skip raw landing + day-file writes when no events
                        changed (used by daemon mode).
--no-landing          : skip raw landing zone unconditionally.
--no-daily            : skip per-day markdown rendering.
--dump PATH           : use a pre-fetched JSON dump instead of live fetch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = Path("/Users/omarkhalil/OmarOS")
TASK_MARSHAL = Path("/Users/omarkhalil/GitHub/Constellation/skills/omaros/task-marshal/scripts")

sys.path.insert(0, str(HERE))
from fetch_calendar import fetch  # noqa: E402

STATE_PATH = VAULT / "02_Tasks_and_Execution/Ledger/.sync_state/calendar.json"
LANDING = VAULT / "09_Data_Sources/Calendar"
SNAPSHOTS = LANDING / "snapshots"
BY_EVENT = LANDING / "by_event"
LANDING_INDEX = LANDING / "index.json"
LANDING_README = LANDING / "README.md"
DAILY_DIR = VAULT / "01_Daily_Life/Calendar"


# ── content hashing ───────────────────────────────────────────────────────────

_HASH_FIELDS = (
    "calendar", "summary", "description", "location",
    "start", "end", "allday", "status", "url",
)


def event_hash(e: dict) -> str:
    blob = json.dumps(
        {k: e.get(k, "") for k in _HASH_FIELDS},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def day_key(e: dict) -> str:
    s = (e.get("start") or "")[:10]
    return s or "0000-00-00"


def safe_uid(uid: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in uid)[:200] or "no_uid"


# ── event → task detection ───────────────────────────────────────────────────
# A calendar event becomes a task if its title (or body) signals user intent
# to do a thing. Two signals are recognised:
#
#   1. Explicit prefix:  ``TODO:``, ``TASK:``, ``[task]`` — case-insensitive,
#      anchored at start of title. The prefix is stripped from the resulting
#      task title; the rest is preserved verbatim.
#   2. Apple-style hashtags inside title or notes (``#tag``). When present,
#      the task is created and tags are extracted into structured form, but
#      only if the user also opted in via the ``--log-tasks`` flag /
#      ``LOG_CALENDAR_TASKS`` env var.
#
# The first signal is unambiguous and always logs. The second is stricter
# (opt-in) because plenty of legitimate calendar entries contain ``#`` for
# numbering ("#1", "#2") that we don't want to mistake for tags.

_TASK_PREFIX_RE = re.compile(
    r"^\s*(?:TODO|TASK|\[task\]|\[todo\])\s*:?\s*",
    flags=re.IGNORECASE,
)
_HASHTAG_RE = re.compile(r"(?:(?<=^)|(?<=\s))#([A-Za-z][\w-]{1,40})")


def _event_to_task(e: dict) -> dict | None:
    """Return a task-marshal envelope for ``e`` if the event signals intent.

    Returns ``None`` when the event is just an ordinary meeting / holiday.
    """
    title = (e.get("summary") or "").strip()
    notes = (e.get("description") or "").strip()
    location = (e.get("location") or "").strip()
    url = (e.get("url") or "").strip()
    if not title:
        return None

    # Signal 1: explicit prefix
    stripped = _TASK_PREFIX_RE.sub("", title, count=1)
    has_prefix = stripped != title
    # Signal 2: hashtags anywhere in title/notes
    hashtags = []
    for src in (title, notes):
        for ht in _HASHTAG_RE.findall(src):
            low = ht.lower()
            if low not in hashtags:
                hashtags.append(low)

    if not has_prefix and not hashtags:
        return None

    # The body collects everything verbatim — original title (so prefix stays
    # auditable), notes, location, URL — task-marshal's body field is a
    # verbatim archive (per its contract_invariants in SKILL.md).
    body_parts: list[str] = []
    body_parts.append(f"From calendar event: {title}")
    if e.get("calendar"):
        body_parts.append(f"Calendar: {e['calendar']}")
    if e.get("start"):
        body_parts.append(f"Start: {e['start']}")
    if e.get("end"):
        body_parts.append(f"End: {e['end']}")
    if location:
        body_parts.append(f"Location: {location}")
    if url:
        body_parts.append(f"URL: {url}")
    if notes:
        body_parts.append("")
        body_parts.append("Notes:")
        body_parts.append(notes)

    when = (e.get("start") or "")[:10] or None
    tags = ["from_calendar_event", "calendar_task"]
    if has_prefix:
        tags.append("calendar_explicit_task")
    for ht in hashtags:
        if ht not in tags:
            tags.append(ht)

    task: dict = {
        "title": stripped.strip() or title,
        "when": when,
        "body": "\n".join(body_parts),
        "status": "open",
        "priority": None,
        "tags": tags,
    }
    return task


def _log_event_tasks(envelopes: list[dict]) -> list[str]:
    """Feed task-marshal's log_task.py via stdin, return assigned task ids."""
    if not envelopes:
        return []
    payload = json.dumps(envelopes, ensure_ascii=False)
    res = subprocess.run(
        ["uv", "run", str(TASK_MARSHAL / "log_task.py")],
        input=payload, capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"[sync] log_task.py failed ({res.returncode}):\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
    out = json.loads(res.stdout)
    ids = out.get("ids") or []
    if len(ids) != len(envelopes):
        raise RuntimeError(
            f"[sync] log_task.py returned {len(ids)} ids for {len(envelopes)} tasks"
        )
    return ids


# ── state ─────────────────────────────────────────────────────────────────────

@dataclass
class SyncState:
    last_sync: str = ""
    events: dict[str, dict] = field(default_factory=dict)  # uid → {hash, day, summary}


def load_state(path: Path) -> SyncState:
    if not path.exists():
        return SyncState()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return SyncState(
        last_sync=raw.get("last_sync", ""),
        events=raw.get("events", {}),
    )


def save_state(state: SyncState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


# ── classification ────────────────────────────────────────────────────────────

@dataclass
class Action:
    kind: str  # CREATE | UPDATE | DELETE | NOOP
    uid: str
    event: dict | None
    old_day: str | None
    new_day: str | None


def classify(remote: list[dict], state: SyncState) -> list[Action]:
    actions: list[Action] = []
    seen: set[str] = set()
    for e in remote:
        uid = e.get("uid", "")
        if not uid:
            continue
        seen.add(uid)
        h = event_hash(e)
        d = day_key(e)
        prev = state.events.get(uid)
        if prev is None:
            actions.append(Action("CREATE", uid, e, None, d))
        elif prev.get("hash") != h or prev.get("day") != d:
            actions.append(Action("UPDATE", uid, e, prev.get("day"), d))
        else:
            actions.append(Action("NOOP", uid, e, prev.get("day"), d))
    # Every UID we knew about that did not appear in this fetch.
    for uid, prev in state.events.items():
        if uid not in seen:
            actions.append(Action("DELETE", uid, None, prev.get("day"), None))
    return actions


# ── raw landing ───────────────────────────────────────────────────────────────

def _ensure_landing() -> None:
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    BY_EVENT.mkdir(parents=True, exist_ok=True)
    if not LANDING_README.exists():
        LANDING_README.write_text(_LANDING_README, encoding="utf-8")


_LANDING_README = """\
---
title: Apple Calendar — Raw Landing Zone
note_type: data_source_index
domain: 09_Data_Sources
subdomain: Calendar
status: active
ai_generated: true
ai_reviewed: false
tags: [data_source, apple_calendar, landing_zone]
---

# Apple Calendar — Raw Landing Zone

Verbatim cache of every event seen by `calendar-sync` in the rolling
[today - LOOKBACK, today + LOOKAHEAD] window. The vault's semantic surface
for the calendar lives at `01_Daily_Life/Calendar/`; this folder is the
pre-normalised data source.

## Layout

```
09_Data_Sources/Calendar/
├── README.md
├── index.json            ← {uid: {path, calendar, summary, start}}
├── snapshots/            ← one immutable JSON per change-bearing sync
│   └── YYYY-MM-DD_HHMMSS.json
└── by_event/             ← one JSON per UID, latest values
    └── <safe_uid>.json
```

Do not edit by hand — these files are regenerated by the sync daemon.
"""


def land(remote: list[dict]) -> dict:
    _ensure_landing()
    name = datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".json"
    snap = SNAPSHOTS / name
    snap.write_text(
        json.dumps(remote, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    now = datetime.now().isoformat(timespec="seconds")
    written = 0
    idx: dict[str, dict] = {}
    for e in remote:
        uid = e.get("uid", "")
        if not uid:
            continue
        fname = safe_uid(uid) + ".json"
        path = BY_EVENT / fname
        payload = dict(e)
        payload["_synced_at"] = now
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        written += 1
        idx[uid] = {
            "by_event_path": str(path.relative_to(VAULT)),
            "calendar": e.get("calendar", ""),
            "summary": (e.get("summary") or "").strip()[:200],
            "start": e.get("start", ""),
        }
    LANDING_INDEX.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": now,
                "count": len(idx),
                "events": idx,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return {
        "snapshot": str(snap.relative_to(VAULT)),
        "by_event_files": written,
    }


# ── per-day markdown rendering ────────────────────────────────────────────────

def _hms(s: str) -> str:
    return s[11:16] if len(s) >= 16 else ""


def render_day(day: str, events: list[dict]) -> str:
    """Render a single 01_Daily_Life/Calendar/<day>.md file as text."""
    events = sorted(events, key=lambda e: (e.get("start") or "", e.get("summary") or ""))
    blob = json.dumps(
        [{k: e.get(k, "") for k in _HASH_FIELDS} for e in events],
        ensure_ascii=False, sort_keys=True,
    )
    content_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    today = date.today().isoformat()
    lines = [
        "---",
        f"title: 'Calendar — {day}'",
        "note_type: calendar_day",
        "domain: 01_Daily_Life",
        "subdomain: Calendar",
        f"date: {day}",
        "source: apple_calendar",
        "tags: [calendar, daily, apple_calendar]",
        "status: active",
        f"event_count: {len(events)}",
        f"content_hash: {content_hash}",
        f"created: {today}",
        f"updated: {today}",
        "ai_generated: true",
        "ai_reviewed: false",
        "---",
        "",
        f"# {day}",
        "",
    ]
    if not events:
        lines.append("_No events._")
        lines.append("")
        return "\n".join(lines)

    for e in events:
        s = _hms(e.get("start") or "")
        en = _hms(e.get("end") or "")
        time_str = "all-day" if e.get("allday") else f"{s}–{en}".strip("–")
        summary = (e.get("summary") or "(untitled)").replace("\n", " ").strip()
        cal = (e.get("calendar") or "").strip()
        loc = (e.get("location") or "").strip()
        url = (e.get("url") or "").strip()
        desc = (e.get("description") or "").strip()
        status = (e.get("status") or "").strip()

        lines.append(f"## {time_str} — {summary}")
        meta_parts: list[str] = []
        if cal:
            meta_parts.append(f"`{cal}`")
        if status and status not in ("none", "confirmed"):
            meta_parts.append(f"_{status}_")
        if loc:
            meta_parts.append(f"**at** {loc}")
        if url:
            meta_parts.append(f"[link]({url})")
        if meta_parts:
            lines.append(" · ".join(meta_parts))
        if desc:
            lines.append("")
            for ln in desc.splitlines():
                lines.append(f"> {ln}")
        lines.append("")

    return "\n".join(lines)


def write_daily_files(remote: list[dict],
                      *,
                      lookback: int,
                      lookahead: int,
                      affected_days: set[str]) -> int:
    """Regenerate the markdown for each day in `affected_days` (only).

    The window of days kept on disk is [today - lookback, today + lookahead].
    For days inside the window with zero events, we still write a file so the
    Obsidian dataview sees an empty-but-present node.
    """
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    by_day: dict[str, list[dict]] = defaultdict(list)
    for e in remote:
        d = day_key(e)
        by_day[d].append(e)

    written = 0
    for d in sorted(affected_days):
        if d == "0000-00-00":
            continue
        try:
            dt = date.fromisoformat(d)
        except ValueError:
            continue
        delta = (dt - today).days
        if delta < -lookback or delta > lookahead:
            continue
        text = render_day(d, by_day.get(d, []))
        path = DAILY_DIR / f"{d}.md"
        # Only write when content actually differs — saves an inotify storm
        # for editors watching the vault.
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing != text:
            path.write_text(text, encoding="utf-8")
            written += 1
    return written


# ── main ──────────────────────────────────────────────────────────────────────

@dataclass
class SyncStats:
    total_remote: int = 0
    created: int = 0
    updated: int = 0
    deleted: int = 0
    noop: int = 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lookback", type=int, default=7)
    ap.add_argument("--lookahead", type=int, default=30)
    ap.add_argument("--changes-only", action="store_true")
    ap.add_argument("--no-landing", action="store_true")
    ap.add_argument("--no-daily", action="store_true")
    ap.add_argument("--dump", type=Path, default=None)
    ap.add_argument("--state", type=Path, default=STATE_PATH)
    ap.add_argument("--log-tasks", action="store_true",
                    help="Convert calendar events whose title carries a "
                    "TODO:/TASK:/[task] prefix or contains #hashtags into "
                    "task-marshal tasks. Idempotent: a given event UID is "
                    "logged at most once (state tracks the assigned "
                    "task_id). Off by default — enable in the daemon plist "
                    "via SYNC_EXTRA_FLAGS=\"--changes-only --log-tasks\".")
    args = ap.parse_args()

    print("[sync] fetching events…", file=sys.stderr)
    if args.dump:
        remote = json.loads(args.dump.read_text(encoding="utf-8"))
    else:
        remote = fetch(lookback_days=args.lookback, lookahead_days=args.lookahead)

    state = load_state(args.state)
    actions = classify(remote, state)

    stats = SyncStats(total_remote=len(remote))
    for a in actions:
        if a.kind == "CREATE":   stats.created += 1
        elif a.kind == "UPDATE": stats.updated += 1
        elif a.kind == "DELETE": stats.deleted += 1
        elif a.kind == "NOOP":   stats.noop += 1

    print(
        f"[sync] plan: create={stats.created} update={stats.updated} "
        f"delete={stats.deleted} noop={stats.noop}",
        file=sys.stderr,
    )

    if args.dry_run:
        for a in actions:
            if a.kind != "NOOP":
                print(json.dumps({
                    "kind": a.kind,
                    "uid": a.uid,
                    "summary": (a.event or {}).get("summary"),
                    "old_day": a.old_day,
                    "new_day": a.new_day,
                }, ensure_ascii=False))
        return 0

    has_changes = (stats.created + stats.updated + stats.deleted) > 0

    # Raw landing.
    if not args.no_landing and not (args.changes_only and not has_changes):
        info = land(remote)
        print(
            f"[sync] raw landing: snapshot={info['snapshot']} "
            f"by_event={info['by_event_files']}",
            file=sys.stderr,
        )

    # Daily files. The set of affected days = old day(s) + new day(s) of every
    # CREATE/UPDATE/DELETE. For a fresh first run with no prior state, every
    # event counts as a CREATE, so all days in the window are in the set.
    affected: set[str] = set()
    for a in actions:
        if a.kind == "NOOP":
            continue
        if a.old_day:
            affected.add(a.old_day)
        if a.new_day:
            affected.add(a.new_day)

    if not args.no_daily and not (args.changes_only and not has_changes):
        n = write_daily_files(
            remote,
            lookback=args.lookback,
            lookahead=args.lookahead,
            affected_days=affected,
        )
        print(f"[sync] daily files written: {n}", file=sys.stderr)

    # New state. Preserve any existing task_id from the prior state so we
    # don't double-log an event that already became a task.
    new_state = SyncState(last_sync=datetime.now().isoformat(timespec="seconds"))
    for e in remote:
        uid = e.get("uid", "")
        if not uid:
            continue
        prev_entry = state.events.get(uid) or {}
        new_state.events[uid] = {
            "hash": event_hash(e),
            "day": day_key(e),
            "summary": (e.get("summary") or "").strip()[:200],
        }
        if prev_entry.get("task_id"):
            new_state.events[uid]["task_id"] = prev_entry["task_id"]

    # Event → task conversion. Only events whose title carries a TODO/TASK
    # prefix (or contains #hashtags) are converted, and only the first time
    # we see them. After logging, the assigned task_id is sticky in state.
    tasks_logged = 0
    if args.log_tasks:
        candidates: list[tuple[str, dict, dict]] = []  # (uid, event, envelope)
        for e in remote:
            uid = e.get("uid", "")
            if not uid:
                continue
            if new_state.events[uid].get("task_id"):
                continue  # already logged in a prior run
            envelope = _event_to_task(e)
            if envelope is None:
                continue
            candidates.append((uid, e, envelope))
        if candidates:
            envelopes = [c[2] for c in candidates]
            try:
                ids = _log_event_tasks(envelopes)
            except Exception as exc:  # noqa: BLE001
                print(f"[sync] event→task logging failed: {exc}",
                      file=sys.stderr)
                ids = []
            for (uid, _e, _env), tid in zip(candidates, ids):
                new_state.events[uid]["task_id"] = tid
                tasks_logged += 1

    save_state(new_state, args.state)

    print(json.dumps({
        "total_remote": stats.total_remote,
        "created": stats.created,
        "updated": stats.updated,
        "deleted": stats.deleted,
        "noop": stats.noop,
        "tasks_logged": tasks_logged,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
