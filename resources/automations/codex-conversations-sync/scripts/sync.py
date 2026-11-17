#!/usr/bin/env python3
"""Mirror every local Codex rollout into private OmarOS storage.

The byte-faithful raw corpus and the rendered transcript corpus are local-only.
Neither surface is staged or committed by this program.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import render as render_mod
import scan as scan_mod
import state as state_mod

REPO_ROOT = state_mod.REPO_ROOT
BASE = REPO_ROOT / "09_Data_Sources" / "Codex_Conversations"
RAW_DIR = Path(
    os.environ.get(
        "CODEXSYNC_RAW_DIR",
        Path.home() / "OmarOS_RawData" / "codex-conversations-raw",
    )
).expanduser()
RENDERED_DIR = BASE / "rendered"
MANIFEST = BASE / "manifest.json"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)


def write_if_changed(path: Path, content: str) -> bool:
    """Atomically write UTF-8 content when it differs."""
    _private_dir(path.parent)
    if path.exists() and path.read_text(encoding="utf-8", errors="replace") == content:
        os.chmod(path, 0o600)
        return False
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    return True


def mirror_raw(source: Path, destination: Path) -> None:
    """Copy one rollout through an atomic private temporary file."""
    _private_dir(destination.parent)
    tmp = destination.with_name(f".{destination.name}.tmp")
    shutil.copyfile(source, tmp)
    os.chmod(tmp, 0o600)
    tmp.replace(destination)


def load_manifest() -> dict:
    if not MANIFEST.exists():
        return {}
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _rendered_paths(manifest: dict) -> set[str]:
    return {
        value["rendered_path"]
        for value in manifest.values()
        if isinstance(value, dict) and value.get("rendered_path")
    }


def remove_obsolete_rendered(previous: set[str], current: set[str]) -> int:
    """Remove superseded derived views, never raw data or paths outside the corpus."""
    rendered_root = RENDERED_DIR.resolve()
    removed = 0
    for relative in sorted(previous - current):
        candidate = (REPO_ROOT / relative).resolve()
        if not candidate.is_relative_to(rendered_root):
            raise ValueError(f"refusing to remove path outside rendered corpus: {relative}")
        if candidate.is_file():
            candidate.unlink()
            removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="inspect without writing")
    parser.add_argument("--project", help="restrict to one cwd-derived project slug")
    parser.add_argument("--since", help="only sessions started on/after YYYY-MM-DD")
    parser.add_argument("--limit", type=int, help="cap changed transcripts processed")
    parser.add_argument("--force", action="store_true", help="ignore incremental state")
    args = parser.parse_args()

    state = {} if args.force else state_mod.load_state()
    manifest = load_manifest()
    previous_rendered = _rendered_paths(manifest)
    processed = skipped = rendered = raw_copies = redacted_count = 0
    obsolete_removed = 0

    for source in scan_mod.scan():
        if args.limit is not None and processed >= args.limit:
            break
        if not args.force and state_mod.is_unchanged(
            state, source.key, source.mtime, source.size
        ):
            skipped += 1
            continue
        try:
            lines = source.path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        markdown, meta, redacted = render_mod.render_markdown(
            lines,
            source_session_id=source.session_id,
            redact=True,
        )
        if args.project and meta.project != args.project:
            continue
        if args.since and render_mod._date_of(meta.started) < args.since:
            continue

        session_id = meta.session_id or source.session_id
        raw_path = RAW_DIR / meta.project / f"{session_id}.jsonl"
        meaningful = meta.n_user + meta.n_assistant > 0
        rendered_path: Path | None = None
        if meaningful:
            rendered_path = (
                RENDERED_DIR / meta.project / render_mod.rendered_filename(meta)
            )

        if not args.dry_run:
            mirror_raw(source.path, raw_path)
            raw_copies += 1
            if rendered_path is not None and write_if_changed(rendered_path, markdown):
                rendered += 1

        if redacted:
            redacted_count += 1
        manifest[session_id] = {
            "session_id": session_id,
            "project": meta.project,
            "cwd": meta.cwd,
            "title": meta.title or "Untitled Codex session",
            "started": meta.started,
            "ended": meta.ended,
            "model": meta.model,
            "model_provider": meta.provider,
            "cli_version": meta.cli_version,
            "n_user": meta.n_user,
            "n_assistant": meta.n_assistant,
            "raw_path": str(raw_path),
            "rendered_path": (
                str(rendered_path.relative_to(REPO_ROOT)) if rendered_path else ""
            ),
            "source_path": str(source.path),
            "source_mtime": source.mtime,
            "redacted": redacted,
            "local_only": True,
            "synced_at": iso_now(),
        }
        state[source.key] = {
            "mtime": source.mtime,
            "size": source.size,
            "rendered_path": (
                str(rendered_path.relative_to(REPO_ROOT)) if rendered_path else ""
            ),
            "raw_path": str(raw_path),
            "session_id": session_id,
        }
        processed += 1

    if not args.dry_run and processed:
        full_forced_refresh = args.force and not any(
            (args.project, args.since, args.limit is not None)
        )
        if full_forced_refresh:
            obsolete_removed = remove_obsolete_rendered(
                previous_rendered, _rendered_paths(manifest)
            )
        write_if_changed(
            MANIFEST,
            json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        )
        state_mod.save_state(state)

    print(
        f"[{iso_now()}] processed={processed} skipped={skipped} "
        f"raw_copies={raw_copies} rendered={rendered} "
        f"redacted={redacted_count} total_sessions={len(manifest)} "
        f"obsolete_removed={obsolete_removed} "
        f"dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
