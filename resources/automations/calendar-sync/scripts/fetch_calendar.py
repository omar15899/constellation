#!/usr/bin/env python3
"""
Fetch every event in a [today - LOOKBACK, today + LOOKAHEAD] window from
Calendar.app. Sub-second performance via the native EventKit framework.

Why EventKit and not AppleScript:
    AppleScript over Calendar.app issues one AppleEvent per query and
    serialises every per-event field through the AE transport. On a real
    Mac with ~17 calendars, fetching even an 8-day window takes ~85 s
    end-to-end — incompatible with sub-minute polling. EventKit is the
    native API Calendar.app itself uses; an `eventsMatchingPredicate_`
    call returns a fully populated NSArray of EKEvent objects in
    < 50 ms, so a 5-second daemon loop has zero pressure.

Permission: the running process needs the *Calendars* entitlement
(System Settings → Privacy & Security → Calendars). If the binary has
not been granted access yet, EventKit will return zero calendars on
modern macOS instead of prompting from a background context. To make
the prompt fire, run `setup_access.py` interactively from Terminal once
— that triggers the access request from a foreground process and the
permission persists for the binary path thereafter.

Output (one JSON object per event, written as a JSON array):

    {
      "uid":          "EKEvent-stable-id-or-calendarItemIdentifier",
      "calendar":     "Personal",
      "summary":      "Reunión con Pedro",
      "description":  "" | "verbatim notes…",
      "location":     "" | "Imperial College",
      "start":        "2026-04-27T18:00:00",   # local time, ISO 8601
      "end":          "2026-04-27T19:00:00",
      "allday":       false,
      "status":       "none" | "confirmed" | "tentative" | "cancelled",
      "url":          "" | "https://meet.google.com/abc-defg-hij"
    }
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

# EKParticipantStatus / EKEventStatus enums map to integers; we keep our
# strings stable instead of re-exposing Apple's int codes.
_STATUS_MAP = {
    0: "none",
    1: "confirmed",
    2: "tentative",
    3: "cancelled",
}


def _request_access(store, timeout: float = 10.0) -> bool:
    """Block until Calendar access has resolved one way or the other."""
    try:
        from EventKit import EKEntityTypeEvent
    except ImportError:
        return False
    done = threading.Event()
    granted = [False]

    def cb(g, _err):
        granted[0] = bool(g)
        done.set()

    store.requestAccessToEntityType_completion_(EKEntityTypeEvent, cb)
    done.wait(timeout=timeout)
    return granted[0]


def _fmt_nsdate(d) -> str:
    """NSDate → ISO 8601 in local time (no Z, matches AppleScript output)."""
    from Foundation import NSCalendar, NSCalendarUnit
    from Foundation import (
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


def fetch(
    *,
    lookback_days: int = 7,
    lookahead_days: int = 30,
    timeout: float = 30.0,
) -> list[dict]:
    """Return every event in the requested window via EventKit."""
    try:
        from EventKit import EKEventStore, EKEntityTypeEvent
        from Foundation import NSDate
    except ImportError as exc:
        raise RuntimeError(
            "[fetch_calendar] EventKit is unavailable. Install "
            "pyobjc-framework-EventKit (already a project dependency in "
            "OmarOS pyproject.toml — run `uv sync` from the vault root)."
        ) from exc

    store = EKEventStore.alloc().init()
    if not _request_access(store, timeout=min(15.0, timeout)):
        raise RuntimeError(
            "[fetch_calendar] Calendar access not granted to this binary. "
            "Run scripts/setup_access.py interactively from Terminal once "
            "to trigger the macOS permission prompt, then click Allow. "
            "After that the daemon can keep running without prompts."
        )

    cals = list(store.calendarsForEntityType_(EKEntityTypeEvent) or [])
    start = NSDate.dateWithTimeIntervalSinceNow_(-lookback_days * 86400)
    end = NSDate.dateWithTimeIntervalSinceNow_(lookahead_days * 86400)
    pred = store.predicateForEventsWithStartDate_endDate_calendars_(start, end, cals)
    events = list(store.eventsMatchingPredicate_(pred) or [])

    out: list[dict] = []
    for e in events:
        try:
            uid = (
                e.calendarItemExternalIdentifier()
                or e.calendarItemIdentifier()
                or e.eventIdentifier()
                or ""
            )
        except Exception:
            uid = e.eventIdentifier() or ""
        d = {
            "uid": str(uid or ""),
            "calendar": str((e.calendar() and e.calendar().title()) or ""),
            "summary": str(e.title() or ""),
            "description": str(e.notes() or ""),
            "location": str(e.location() or ""),
            "start": _fmt_nsdate(e.startDate()) if e.startDate() else "",
            "end": _fmt_nsdate(e.endDate()) if e.endDate() else "",
            "allday": bool(e.isAllDay()),
            "status": _STATUS_MAP.get(int(e.status() or 0), "none"),
            "url": str((e.URL() and e.URL().absoluteString()) or ""),
        }
        out.append(d)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("output", nargs="?", default=None,
                    help="Output JSON path (default: stdout).")
    ap.add_argument("--lookback", type=int, default=7)
    ap.add_argument("--lookahead", type=int, default=30)
    args = ap.parse_args()

    t0 = time.time()
    events = fetch(lookback_days=args.lookback, lookahead_days=args.lookahead)
    dt = time.time() - t0
    payload = json.dumps(events, indent=2, ensure_ascii=False)
    if args.output and args.output not in ("-", "--stdout"):
        Path(args.output).write_text(payload, encoding="utf-8")
        print(
            f"[fetch_calendar] wrote {len(events)} events → {args.output} "
            f"in {dt*1000:.0f}ms",
            file=sys.stderr,
        )
    else:
        print(payload)


if __name__ == "__main__":
    main()
