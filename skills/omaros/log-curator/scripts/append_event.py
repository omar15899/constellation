#!/usr/bin/env python3
"""Shared helper for hook authors — appends a structured event to the stream.

Hooks that produce events should import this module (or invoke it as a
subprocess) so the write path stays consistent. This is NOT used by the
log-curator skill itself (the skill is read-only).

Usage as a module:
    from append_event import append_event
    append_event({"kind": "commit", "source": "post_commit_log_writer", ...})

Usage as a CLI (reads JSON from stdin):
    echo '{"kind": "error", "source": "…", ...}' | python3 append_event.py

Guarantees:
- UTC timestamp added automatically if the event lacks `ts`.
- One JSON object per line, no pretty-printing, UTF-8.
- Never truncates existing content (append-only open mode).
- Idempotency is the caller's concern (this helper does not dedupe).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


OMAROS_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))
EVENT_LOG_DIR = OMAROS_ROOT / "docs" / "event_logs"


def append_event(event: dict) -> Path:
    """Append a single event to today's log file. Returns the log path."""
    if "ts" not in event:
        event = {"ts": datetime.now(timezone.utc).isoformat(), **event}
    EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = EVENT_LOG_DIR / f"{today}.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, separators=(",", ":"), ensure_ascii=False))
        f.write("\n")
    return log_path


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"error: invalid JSON: {exc}\n")
        sys.exit(2)
    if not isinstance(event, dict):
        sys.stderr.write("error: event payload must be a JSON object\n")
        sys.exit(2)
    if "kind" not in event or "source" not in event:
        sys.stderr.write("error: event must include 'kind' and 'source'\n")
        sys.exit(2)
    path = append_event(event)
    print(path)


if __name__ == "__main__":
    main()
