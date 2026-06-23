#!/usr/bin/env python3
"""peer_sync.py — propagate the master peer list to every per-repo registry.

The master registry at ~/GitHub/.claude/registry/repos.yaml is the source
of truth for which repos exist and how they are classified. Each lab's
.claude/registry/peers.yaml is a derived snapshot that some per-repo
orchestrators read on session start. This hook keeps the snapshots
fresh.

Idempotent: a second run produces zero writes if nothing changed.

Usage:
    peer_sync.py                 # dry-run (default)
    peer_sync.py --apply         # actually write
    peer_sync.py --repo <name>   # only this repo

Discovery rule for "is this repo eligible":
    - The repo is on disk AND in the master registry.
    - The repo has a .claude/registry/ directory.

Files written:
    <repo>/.claude/registry/peers.yaml.snapshot
        — verbatim copy of master, prefixed with a header.
        — sibling to the lab's own peers.yaml (never overwrites it).

This hook never overwrites a hand-maintained peers.yaml. It writes
peers.yaml.snapshot alongside, leaving the lab to merge if it wants.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from _common import HUB, iter_repos, log, registry_path  # type: ignore


def plan() -> list[tuple[str, Path, Path]]:
    """Return [(name, master_path, target_snapshot_path)] for eligible repos."""
    master = registry_path()
    out: list[tuple[str, Path, Path]] = []
    for name, path in iter_repos():
        reg_dir = path / ".claude" / "registry"
        if not reg_dir.exists():
            continue
        snap = reg_dir / "peers.yaml.snapshot"
        out.append((name, master, snap))
    return out


def _body_of(text: str) -> str:
    """Strip the generated header block (everything up to the first blank line)."""
    sep = "\n\n"
    idx = text.find(sep)
    return text[idx + len(sep) :] if idx != -1 else text


def write_snapshot(master: Path, snap: Path) -> bool:
    """Return True if snap was (re)written.

    Idempotent w.r.t. the header timestamp: the snapshot is only rewritten
    when the mirrored registry body actually changes, not merely because a
    new run produces a fresh timestamp. Without this the snapshot churned on
    every hook invocation, leaving 14 repos perpetually dirty.
    """
    body = master.read_text()
    if snap.exists() and _body_of(snap.read_text()) == body:
        return False
    header = (
        "# peers.yaml.snapshot — verbatim mirror of ~/GitHub/.claude/registry/repos.yaml\n"
        f"# Refreshed by ~/GitHub/.claude/hooks/peer_sync.py on "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}.\n"
        "# This file is auto-generated. Do not edit by hand.\n"
        "# The lab's authoritative peers.yaml lives next to this file.\n"
        "\n"
    )
    snap.write_text(header + body)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--repo", action="append", default=[])
    args = parser.parse_args()

    targets = plan()
    if args.repo:
        wanted = set(args.repo)
        targets = [t for t in targets if t[0] in wanted]

    if not targets:
        log("peer_sync", "no eligible repos.")
        return 0

    changed = 0
    for name, master, snap in targets:
        if args.apply:
            if write_snapshot(master, snap):
                log("peer_sync", f"wrote {snap}")
                changed += 1
            else:
                log("peer_sync", f"unchanged {snap}")
        else:
            log("peer_sync", f"plan: refresh {snap}")
    log("peer_sync", f"done. eligible={len(targets)} written={changed}")
    return 0


if __name__ == "__main__":
    # Local-style import for _common.py living next to this file.
    sys.path.insert(0, str(Path(__file__).parent))
    raise SystemExit(main())
