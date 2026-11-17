#!/usr/bin/env python3
"""
Fetch every reminder from the macOS Reminders app via the native EventKit
framework. Sub-second performance, replacing the previous AppleScript
implementation which took ~6 minutes for ~1300 reminders.

Why EventKit and not AppleScript:
    AppleScript over Reminders.app issues one AppleEvent per bulk getter
    per chunk. With 1300+ reminders chunked at 50, that is ~27 chunks ×
    8 getters × ~1.5 s/AE ≈ 5–6 min per fetch — incompatible with a
    sub-minute polling daemon. EventKit's
    ``fetchRemindersMatchingPredicate_completion_`` returns the entire
    population in 200–400 ms, so a 5-second daemon loop sleeps most of
    the time even on a heavy reminder set.

Identifier compatibility:
    The vault's prior sync_state uses keys of the form
    ``x-apple-reminder://<UUID>`` because that is what AppleScript
    returned for ``id of reminder``. EventKit's
    ``calendarItemExternalIdentifier`` returns the bare UUID. We prefix
    on the way out so existing state entries continue to dedup correctly
    — there is no migration step.

Output schema is identical to the AppleScript version (the dedup,
classify, and downstream task-marshal code paths consume the same dict
shape):

    {
      "id":              "x-apple-reminder://UUID",
      "list":            "Recordatorios",
      "name":            "Test desde Claude",
      "body":            "" | "verbatim notes…",
      "completed":       false,
      "priority":        0 | 1 | 5 | 9,
      "due_date":        "2026-04-25T18:00:00" | None,   # local time, ISO 8601
      "creation_date":   "2026-04-23T09:14:21" | None,
      "completion_date": None | "..."
    }

Permission: the calling binary must have the *Reminders* entitlement
(System Settings → Privacy & Security → Reminders). Grant happens
automatically the first time `requestAccessToEntityType_` runs from a
foreground UI session — the daemon thereafter inherits the grant.
"""
from __future__ import annotations

import argparse
import glob
import json
import sqlite3
import sys
import threading
import time
from pathlib import Path

# ── parent-child enrichment ──────────────────────────────────────────────────
# EventKit's `predicateForRemindersInCalendars_` returns sub-reminders in the
# flat result list, but does NOT expose the parent relationship in the public
# API (`parentID()` always comes back None for our 410+ sub-tasks). The
# Reminders.app local SQLite store DOES carry the link in
# `ZREMCDREMINDER.ZCKPARENTREMINDERIDENTIFIER`. We open it read-only,
# build a {ck_id → parent_ck_id} map, and enrich the EventKit fetch.
#
# This is best-effort and degrades gracefully: if the store is unreadable
# (Full Disk Access not granted to the binary, or the path layout changed
# between macOS versions), we just return an empty map and `parent_id`
# stays None on every reminder.

_REMINDERS_STORE_GLOB = str(
    Path.home() /
    "Library/Group Containers/group.com.apple.reminders/Container_v1/Stores/Data-*.sqlite"
)


def _load_parent_map() -> dict[str, str]:
    """Return ``{child_ck_identifier: parent_ck_identifier}`` across every
    Reminders store on disk."""
    out: dict[str, str] = {}
    for db_path in glob.glob(_REMINDERS_STORE_GLOB):
        try:
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
        except sqlite3.OperationalError:
            continue
        try:
            cur = con.execute(
                "SELECT ZCKIDENTIFIER, ZCKPARENTREMINDERIDENTIFIER "
                "FROM ZREMCDREMINDER "
                "WHERE ZMARKEDFORDELETION = 0 "
                "  AND ZCKIDENTIFIER IS NOT NULL "
                "  AND ZCKPARENTREMINDERIDENTIFIER IS NOT NULL"
            )
            for cid, pid in cur.fetchall():
                if cid and pid:
                    out[cid] = pid
        except sqlite3.OperationalError:
            pass
        finally:
            con.close()
    return out


def _request_access(store, entity_type: int, timeout: float = 10.0) -> bool:
    done = threading.Event()
    granted = [False]

    def cb(g, _err):
        granted[0] = bool(g)
        done.set()

    store.requestAccessToEntityType_completion_(entity_type, cb)
    done.wait(timeout=timeout)
    return granted[0]


def _fmt_nsdate(d) -> str:
    if d is None:
        return ""
    from Foundation import (
        NSCalendar,
        NSCalendarUnitYear,
        NSCalendarUnitMonth,
        NSCalendarUnitDay,
        NSCalendarUnitHour,
        NSCalendarUnitMinute,
        NSCalendarUnitSecond,
    )
    cal = NSCalendar.currentCalendar()
    units = (
        NSCalendarUnitYear | NSCalendarUnitMonth | NSCalendarUnitDay |
        NSCalendarUnitHour | NSCalendarUnitMinute | NSCalendarUnitSecond
    )
    c = cal.components_fromDate_(units, d)
    return (
        f"{c.year():04d}-{c.month():02d}-{c.day():02d}T"
        f"{c.hour():02d}:{c.minute():02d}:{c.second():02d}"
    )


def _fmt_date_components(dc) -> str:
    """NSDateComponents (for due dates) → ISO 8601 string in local time.

    Reminders may store a date-only due (no time) — we render midnight
    in those cases to match the AppleScript behaviour.
    """
    if dc is None:
        return ""
    try:
        y = int(dc.year())
        m = int(dc.month())
        d = int(dc.day())
        if y <= 0 or m <= 0 or d <= 0:
            return ""
        # Hour/minute/second may come back as NSUndefinedDateComponent
        # (a large negative); coerce to 0 if not in [0,59].
        def _safe(v: int) -> int:
            return v if 0 <= v < 60 else 0
        try:
            hh = _safe(int(dc.hour()))
            mm = _safe(int(dc.minute()))
            ss = _safe(int(dc.second()))
        except Exception:
            hh = mm = ss = 0
        return f"{y:04d}-{m:02d}-{d:02d}T{hh:02d}:{mm:02d}:{ss:02d}"
    except Exception:
        return ""


def fetch(timeout: float = 30.0, **_legacy_kwargs) -> list[dict]:
    """Return every reminder from every list, in the AppleScript-compatible
    schema. ``_legacy_kwargs`` swallows old call sites that passed
    ``chunk=`` to the AppleScript implementation.
    """
    try:
        from EventKit import EKEventStore, EKEntityTypeReminder
    except ImportError as exc:
        raise RuntimeError(
            "[fetch_reminders] EventKit unavailable. Run `uv sync` from "
            "the vault root."
        ) from exc

    store = EKEventStore.alloc().init()
    if not _request_access(store, EKEntityTypeReminder,
                           timeout=min(15.0, timeout)):
        raise RuntimeError(
            "[fetch_reminders] Reminders access not granted. Enable access for "
            "this Python interpreter in System Settings > Privacy & Security > "
            "Reminders, then retry from Terminal."
        )

    cals = list(store.calendarsForEntityType_(EKEntityTypeReminder) or [])
    pred = store.predicateForRemindersInCalendars_(cals)

    results = [None]
    done = threading.Event()

    def cb(reminders):
        results[0] = list(reminders or [])
        done.set()

    store.fetchRemindersMatchingPredicate_completion_(pred, cb)
    if not done.wait(timeout=timeout):
        raise RuntimeError(
            f"[fetch_reminders] EventKit fetch timed out after {timeout}s"
        )

    parent_map = _load_parent_map()

    out: list[dict] = []
    for r in results[0] or []:
        ext = r.calendarItemExternalIdentifier()
        if not ext:
            ext = r.calendarItemIdentifier() or ""
        if ext and not str(ext).startswith("x-apple-reminder://"):
            rid = f"x-apple-reminder://{ext}"
        else:
            rid = str(ext or "")

        creation = r.creationDate()
        completion = r.completionDate()
        due_components = r.dueDateComponents()

        priority = 0
        try:
            priority = int(r.priority() or 0)
        except Exception:
            priority = 0

        cid = r.calendarItemIdentifier()
        parent_ck = parent_map.get(str(cid)) if cid else None
        parent_id = (
            f"x-apple-reminder://{parent_ck}" if parent_ck else None
        )
        out.append({
            "id": rid,
            "list": str((r.calendar() and r.calendar().title()) or ""),
            "name": str(r.title() or ""),
            "body": str(r.notes() or ""),
            "completed": bool(r.isCompleted()),
            "priority": priority,
            "due_date": _fmt_date_components(due_components) or None,
            "creation_date": _fmt_nsdate(creation) or None,
            "completion_date": _fmt_nsdate(completion) or None,
            "parent_id": parent_id,
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("output", nargs="?", default=None)
    ap.add_argument("--timeout", type=float, default=30.0)
    # Kept for backwards CLI compatibility — the AppleScript chunk arg is
    # meaningless under EventKit but we accept and ignore it so existing
    # callers keep working.
    ap.add_argument("--chunk", type=int, default=50,
                    help="(legacy, no-op under EventKit)")
    args = ap.parse_args()

    t0 = time.time()
    rs = fetch(timeout=args.timeout)
    dt = time.time() - t0
    payload = json.dumps(rs, indent=2, ensure_ascii=False)
    if args.output and args.output not in ("-", "--stdout"):
        Path(args.output).write_text(payload, encoding="utf-8")
        print(
            f"[fetch_reminders] wrote {len(rs)} reminders → {args.output} "
            f"in {dt*1000:.0f}ms",
            file=sys.stderr,
        )
    else:
        print(payload)


if __name__ == "__main__":
    main()
