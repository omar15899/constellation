#!/usr/bin/env python3
"""
Long-running daemon for sub-minute Calendar.app polling.

Same shape as reminders-sync/daemon.py: invoke sync.py as a subprocess in a
loop, sleep the remainder of INTERVAL, never let a single bad cycle kill the
daemon. Fault isolation by subprocess. Adaptive cadence: a fetch that runs
longer than INTERVAL just starts the next cycle immediately.

Environment
-----------
INTERVAL_SECONDS       polling period in seconds (default 5)
SYNC_TIMEOUT_SECONDS   per-cycle subprocess timeout in seconds (default 300)
SYNC_EXTRA_FLAGS       extra flags for sync.py (default: --changes-only)
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYNC = HERE / "sync.py"
VAULT = Path("/Users/omarkhalil/OmarOS")

INTERVAL = max(1, int(os.environ.get("INTERVAL_SECONDS", "5")))
TIMEOUT = max(30, int(os.environ.get("SYNC_TIMEOUT_SECONDS", "300")))
EXTRA = os.environ.get("SYNC_EXTRA_FLAGS", "--changes-only").split()

UV = "/opt/homebrew/bin/uv"
if not Path(UV).exists():
    UV = "uv"

_running = True


def _shutdown(signum, _frame) -> None:
    global _running
    _running = False
    print(f"[daemon] received signal {signum}, shutting down after current cycle",
          file=sys.stderr, flush=True)


def _log(msg: str) -> None:
    print(f"[daemon {datetime.now().isoformat(timespec='seconds')}] {msg}",
          flush=True)


def _run_one_cycle() -> tuple[int, float]:
    cmd = [UV, "run", str(SYNC), *EXTRA]
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=str(VAULT),
            capture_output=True, text=True,
            timeout=TIMEOUT, check=False,
        )
        elapsed = time.time() - t0
        if proc.returncode != 0:
            _log(f"sync exit={proc.returncode} elapsed={elapsed:.1f}s")
            if proc.stderr:
                sys.stderr.write(proc.stderr)
                sys.stderr.flush()
        else:
            tail = (proc.stdout or "").strip().splitlines()
            summary = tail[-1] if tail else ""
            _log(f"sync ok elapsed={elapsed:.1f}s {summary}")
        return proc.returncode, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        _log(f"sync TIMEOUT after {elapsed:.0f}s (limit {TIMEOUT}s)")
        return 124, elapsed


def main() -> int:
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    _log(f"starting calendar-sync daemon "
         f"interval={INTERVAL}s timeout={TIMEOUT}s extra={EXTRA}")

    cycle = 0
    while _running:
        cycle += 1
        _, elapsed = _run_one_cycle()
        if not _running:
            break
        sleep_for = max(0.0, INTERVAL - elapsed)
        if sleep_for > 0:
            time.sleep(sleep_for)

    _log(f"daemon stopped after {cycle} cycles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
