#!/usr/bin/env python3
"""claude-conversations-sync: mirror Claude Code transcripts into OmarOS.

Two surfaces under ``09_Data_Sources/Claude_Conversations/``:

  * ``raw/<project>/<sessionId>.jsonl``      — verbatim mirror (gitignored backup)
  * ``rendered/<project>/<date>_<sid8>_<title>.md`` — readable, committed
  * ``manifest.json``                         — per-session index, committed

Incremental: a transcript is only re-processed when its ``(mtime, size)``
changes since the last run (state in
``02_Tasks_and_Execution/Ledger/.sync_state/claude_conversations.json``).
The daemon runs this on a fixed interval; a no-op tick writes nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import render as render_mod
import scan as scan_mod
import state as state_mod

REPO_ROOT = state_mod.REPO_ROOT
BASE = REPO_ROOT / "09_Data_Sources" / "Claude_Conversations"
RAW_DIR = Path(os.environ.get("CCSYNC_RAW_DIR", BASE / "raw"))
RENDERED_DIR = BASE / "rendered"
MANIFEST = BASE / "manifest.json"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_if_changed(path: Path, content: str) -> bool:
    """Write only when content differs; return True if written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        return False
    path.write_text(content)
    return True


def load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def git_commit(paths: list[Path], message: str) -> None:
    rel = [str(p.relative_to(REPO_ROOT)) for p in paths if p.exists()]
    if not rel:
        return
    subprocess.run(["git", "-C", str(REPO_ROOT), "add", *rel], check=False)
    # nothing staged -> skip commit
    staged = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--cached", "--quiet"],
        check=False,
    )
    if staged.returncode == 0:
        return
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "commit", "-m", message],
        check=False,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="classify only, no writes")
    ap.add_argument("--commit", action="store_true", help="git-commit rendered + manifest")
    ap.add_argument("--project", help="restrict to one project slug")
    ap.add_argument("--since", help="only sessions started on/after YYYY-MM-DD")
    ap.add_argument("--include-thinking", action="store_true")
    ap.add_argument("--no-redact", action="store_true")
    ap.add_argument("--limit", type=int, help="cap number of transcripts processed")
    ap.add_argument("--force", action="store_true", help="ignore state, re-render all")
    args = ap.parse_args()

    state = {} if args.force else state_mod.load_state()
    manifest = load_manifest()
    sources = scan_mod.scan()
    if args.project:
        sources = [s for s in sources if s.project == args.project]

    processed = skipped = written_md = redacted_count = 0
    touched: list[Path] = []

    for src in sources:
        if args.limit and processed >= args.limit:
            break
        if not args.force and state_mod.is_unchanged(state, src.key, src.mtime, src.size):
            skipped += 1
            continue

        try:
            lines = src.path.read_text(errors="replace").splitlines()
        except OSError:
            continue

        md, meta, redacted = render_mod.render_markdown(
            lines,
            project=src.project,
            redact=not args.no_redact,
            include_thinking=args.include_thinking,
        )
        if args.since and render_mod._date_of(meta.started) < args.since:
            continue

        # no human-readable turns -> still track state so we don't re-read it
        meaningful = meta.n_user + meta.n_assistant > 0
        rel_md = ""
        if meaningful:
            fname = render_mod.rendered_filename(meta)
            out_md = RENDERED_DIR / src.project / fname
            rel_raw = RAW_DIR / src.project / f"{src.session_id}.jsonl"
            if not args.dry_run:
                rel_raw.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src.path, rel_raw)
                if write_if_changed(out_md, md):
                    written_md += 1
                    touched.append(out_md)
            rel_md = str(out_md.relative_to(REPO_ROOT))

        if redacted:
            redacted_count += 1

        if meaningful:
            manifest[src.session_id] = {
                "session_id": meta.session_id,
                "project": src.project,
                "cwd": meta.cwd,
                "git_branch": meta.git_branch,
                "title": meta.title or "Untitled Claude session",
                "started": meta.started,
                "ended": meta.ended,
                "n_user": meta.n_user,
                "n_assistant": meta.n_assistant,
                "rendered_path": rel_md,
                "source_mtime": src.mtime,
                "redacted": redacted,
                "synced_at": iso_now(),
            }

        state[src.key] = {
            "mtime": src.mtime,
            "size": src.size,
            "rendered_path": rel_md,
            "session_id": src.session_id,
        }
        processed += 1

    if not args.dry_run:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        write_if_changed(
            MANIFEST,
            json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        )
        state_mod.save_state(state)
        touched.append(MANIFEST)

    print(
        f"[{iso_now()}] processed={processed} skipped={skipped} "
        f"rendered={written_md} redacted={redacted_count} "
        f"total_sessions={len(manifest)}"
    )

    if args.commit and not args.dry_run and touched:
        git_commit(
            [RENDERED_DIR, MANIFEST, BASE / "README.md"],
            f"Sync {written_md} Claude conversation transcript(s)",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
