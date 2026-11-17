#!/usr/bin/env python3
"""
One-time interactive helper to grant Calendar access to the OmarOS Python
binary, so calendar-sync can run as a launchd daemon without manual prompts.

How macOS Calendar permission works
-----------------------------------
TCC (Transparency, Consent and Control) tracks Calendar access per-binary.
The first time a process calls
    EKEventStore.requestAccessToEntityType_completion_(EKEntityTypeEvent, ...)
from a foreground UI session, macOS shows a "<binary> wants to access your
calendars" prompt. After the user clicks Allow, the grant is persisted
keyed to the binary path, and every future invocation — including
launchd-spawned background processes — has access without prompting.

A background launchd daemon cannot trigger that prompt itself (no UI
session attached). So we run this script *once* from Terminal:

    cd ~/OmarOS
    uv run /Users/omarkhalil/GitHub/Constellation/resources/automations/calendar-sync/scripts/setup_access.py

The script triggers the request, waits for the user to click Allow, then
prints the result. After that the daemon will work end-to-end.

If you click Deny by mistake, re-grant from
    System Settings → Privacy & Security → Calendars
and tick the row for `python3.12` (or whatever the venv's python binary
resolves to).
"""
from __future__ import annotations

import sys
import threading
import time


def main() -> int:
    try:
        from EventKit import EKEventStore, EKEntityTypeEvent
        from Foundation import NSDate
    except ImportError:
        print(
            "EventKit module not available. Run `uv sync` from the vault "
            "root first.", file=sys.stderr,
        )
        return 2

    store = EKEventStore.alloc().init()
    print("Requesting Calendar access. If this is the first run, macOS "
          "will show a permission prompt — click Allow.")

    done = threading.Event()
    granted_holder = [None]

    def cb(granted, err):
        granted_holder[0] = bool(granted)
        done.set()

    t0 = time.time()
    store.requestAccessToEntityType_completion_(EKEntityTypeEvent, cb)
    done.wait(timeout=120)
    elapsed = time.time() - t0

    granted = granted_holder[0]
    if granted is None:
        print(f"  → no response after {elapsed:.0f}s. Is the prompt hidden "
              f"behind another window? If you saw no prompt, the binary "
              f"may already be in System Settings → Privacy → Calendars.")
        return 1
    if not granted:
        print(f"  → access DENIED ({elapsed:.1f}s). Re-enable in System "
              f"Settings → Privacy & Security → Calendars and re-run.")
        return 1

    cals = list(store.calendarsForEntityType_(EKEntityTypeEvent) or [])
    start = NSDate.dateWithTimeIntervalSinceNow_(-1 * 86400)
    end = NSDate.dateWithTimeIntervalSinceNow_(7 * 86400)
    pred = store.predicateForEventsWithStartDate_endDate_calendars_(start, end, cals)
    events = list(store.eventsMatchingPredicate_(pred) or [])

    print(f"  → access GRANTED ({elapsed:.1f}s).")
    print(f"  → calendars visible: {len(cals)}")
    print(f"  → events in next 7 days: {len(events)}")
    print()
    print("You can now load the daemon:")
    print("  /Users/omarkhalil/GitHub/Constellation/resources/automations/calendar-sync/scripts/install_launchd.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
