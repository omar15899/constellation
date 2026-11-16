from __future__ import annotations

import os
from datetime import datetime, timezone

from config import load_config
from graph_client import GraphError
from sync import run_sync


def _dry_run_from_env() -> bool:
    return os.environ.get("OUTLOOK_SYNC_DRYRUN", "0") == "1"


def main() -> None:
    cfg = load_config()
    dry_run = _dry_run_from_env()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        summary = run_sync(dry_run=dry_run, mode=cfg.mode)
    except GraphError as exc:
        print(
            f"[{ts}] outlook-sync FAILED: {exc} "
            "— run scripts/auth.py to (re)authenticate."
        )
        return
    print(
        f"[{ts}] outlook-sync mode={cfg.mode} dry_run={summary.dry_run} "
        f"folders={summary.folders} fetched={summary.fetched} "
        f"classified={summary.classified} labeled={summary.labeled} "
        f"moved={summary.moved} rescued={summary.rescued} "
        f"junked={summary.junked} errors={len(summary.errors)}"
    )


if __name__ == "__main__":
    main()
