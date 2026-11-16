#!/usr/bin/env python3
"""Long-running claude-conversations-sync daemon (launchd-managed).

Polls ~/.claude/projects on a fixed interval and runs the sync pipeline.
Mirrors the calendar-sync daemon contract: single-flight, self-throttling,
logs to stdout (captured by launchd into
docs/claude_conversations_sync_daemon.log).

Transcripts are appended live while a session is open, so a modest interval
(default 120 s) is plenty — the sync is incremental and only touches files
whose (mtime, size) changed.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

POLL_INTERVAL = int(os.environ.get("CCSYNC_INTERVAL", "120"))
REPO_ROOT = Path("/Users/omarkhalil/OmarOS")
SYNC = REPO_ROOT / ".claude" / "skills" / "claude-conversations-sync" / "scripts" / "sync.py"
VENV_PY = Path.home() / ".venvs" / "omaros" / "bin" / "python"


def main() -> None:
    extra = os.environ.get("CCSYNC_EXTRA_FLAGS", "").split()
    if os.environ.get("CCSYNC_COMMIT") == "1" and "--commit" not in extra:
        extra.append("--commit")
    interval = POLL_INTERVAL
    while True:
        start = time.monotonic()
        try:
            subprocess.run(
                [str(VENV_PY), str(SYNC), *extra],
                check=False,
                timeout=max(300, interval * 4),
            )
        except subprocess.TimeoutExpired:
            print("sync timed out; will retry next tick", file=sys.stderr)
        elapsed = time.monotonic() - start
        time.sleep(max(1.0, interval - elapsed))


main()
