#!/usr/bin/env python3
"""Single-flight polling daemon for the private Codex conversation mirror."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

POLL_INTERVAL = max(15, int(os.environ.get("CODEXSYNC_INTERVAL", "120")))
REPO_ROOT = Path(
    os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS"))
).resolve()
SYNC = (
    REPO_ROOT
    / ".agents"
    / "skills"
    / "codex-conversations-sync"
    / "scripts"
    / "sync.py"
)
VENV_PY = Path.home() / ".venvs" / "omaros" / "bin" / "python"


def main() -> None:
    interval = POLL_INTERVAL
    while True:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                [str(VENV_PY), str(SYNC)],
                check=False,
                timeout=max(300, interval * 4),
            )
            if completed.returncode:
                print(
                    f"sync exited with status {completed.returncode}; retrying next tick",
                    file=sys.stderr,
                    flush=True,
                )
        except subprocess.TimeoutExpired:
            print("sync timed out; retrying next tick", file=sys.stderr, flush=True)
        elapsed = time.monotonic() - started
        time.sleep(max(1.0, interval - elapsed))


if __name__ == "__main__":
    main()
