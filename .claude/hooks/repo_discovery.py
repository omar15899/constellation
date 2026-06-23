#!/usr/bin/env python3
"""repo_discovery.py — thin hook wrapper around scripts/discover_repos.py.

Wraps the discovery script so it can be wired into a Claude Code
session-start hook configuration. The script itself is dependency-free
and idempotent.

Usage from a hook:
    python3 ~/GitHub/.claude/hooks/repo_discovery.py [--state] [--json]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    hub = Path.home() / "GitHub" / ".claude"
    script = hub / "scripts" / "discover_repos.py"
    if not script.exists():
        sys.stderr.write(f"[constellation:repo_discovery] missing {script}\n")
        return 1
    os.execvp("python3", ["python3", str(script), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
