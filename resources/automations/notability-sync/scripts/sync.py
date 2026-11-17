#!/usr/bin/env python3
"""Notability → OmarOS sync. Reactive, hash-deduped, sidecar-augmented.

Reads PDFs from one or more Auto-Backup source folders (iCloud, OneDrive),
mirrors them byte-faithfully into 09_Data_Sources/Notability/pdfs/, extracts
plain text via pdftotext into a parallel .md sidecar under sidecars/, and
maintains a hash-indexed state file plus an immutable per-run snapshot.
Safe to run repeatedly; no-op when inputs haven't changed.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    DEFAULT_SOURCES, ONEDRIVE_GLOBS,
    PDF_EXTS, NOTE_EXTS, PDFTOTEXT, PLACEHOLDER_PROBE_BYTES,
)

VAULT = Path(os.environ.get("OMAROS_VAULT", "/Users/omarkhalil/OmarOS"))
LANDING = VAULT / "09_Data_Sources" / "Notability"
PDFS = LANDING / "pdfs"
SIDECARS = LANDING / "sidecars"
NOTES_RAW = LANDING / "notes_raw"
PDFS_IMPORTED = LANDING / "pdfs_imported"
SNAPSHOTS = LANDING / "snapshots"
STATE_FILE = LANDING / ".sync_state.json"
INDEX_FILE = LANDING / "index.json"


def source_label(path: Path) -> str:
    s = str(path).lower()
    if "onedrive" in s:
        return "onedrive"
    if "icloud" in s or "com~apple~clouddocs" in s or "mobile documents" in s:
        return "icloud"
    return "other"


def discover_sources(cli_sources: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    candidates = list(cli_sources) if cli_sources else list(DEFAULT_SOURCES)
    if not cli_sources:
        for pattern in ONEDRIVE_GLOBS:
            candidates.extend(Path(p) for p in glob.glob(pattern))
    for c in candidates:
        c = c.expanduser().resolve()
        if c in seen:
            continue
        seen.add(c)
        if c.is_dir():
            found.append(c)
    return found


@dataclass
class PdfRecord:
    hash: str
    filename: str
    bytes_: int
    mtime: str
    sources: set[str] = field(default_factory=set)
    source_paths: list[str] = field(default_factory=list)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_placeholder(path: Path) -> bool:
    """OneDrive Files-On-Demand stubs read as all-zero bytes."""
    try:
        with path.open("rb") as f:
            head = f.read(PLACEHOLDER_PROBE_BYTES)
    except OSError:
        return True
    return len(head) == 0 or head == b"\x00" * len(head)


def scan_source(root: Path) -> list[tuple[Path, Path, str]]:
    """Yield (file, root, kind) where kind ∈ {'pdf','note'}.

    `.note` packages on modern Notability are directories (bundles), not files.
    We detect both regular-file .note and directory .note.
    """
    out: list[tuple[Path, Path, str]] = []
    for p in root.rglob("*"):
        suffix = p.suffix.lower()
        if suffix in PDF_EXTS and p.is_file():
            out.append((p, root, "pdf"))
        elif suffix in NOTE_EXTS:
            out.append((p, root, "note"))
    return out


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def atomic_write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
    tmp.replace(path)


def extract_text(pdf: Path) -> str:
    try:
        proc = subprocess.run(
            [PDFTOTEXT, "-layout", "-enc", "UTF-8", str(pdf), "-"],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode == 0:
            return proc.stdout
        return f"[pdftotext exit {proc.returncode}] {proc.stderr.strip()}"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return f"[pdftotext error: {e}]"


def write_sidecar(dest_pdf: Path, rec: PdfRecord, body: str) -> Path:
    sidecar = SIDECARS / (dest_pdf.stem + ".md")
    slug = dest_pdf.stem
    fm_lines = [
        "---",
        f'title: "{slug}"',
        "note_type: external_artifact",
        "domain: 09_Data_Sources",
        "subdomain: Notability",
        "source: notability",
        f'source_path: "{rec.source_paths[0] if rec.source_paths else ""}"',
        f"source_clouds: [{', '.join(sorted(rec.sources))}]",
        f'sha256: "{rec.hash}"',
        f"bytes: {rec.bytes_}",
        f'pdf_mtime: "{rec.mtime}"',
        f'synced_at: "{datetime.now().isoformat(timespec="seconds")}"',
        "ai_generated: false",
        "tags: [notability, pdf, handwritten]",
        "---",
        "",
        "# Extracted text",
        "",
        body.rstrip() + "\n",
    ]
    sidecar.write_text("\n".join(fm_lines))
    return sidecar


def disambiguate_filename(filename: str, new_hash: str, taken: dict[str, str]) -> str:
    """taken: filename → hash. Returns a filename unique vs taken and different-hash."""
    existing_hash = taken.get(filename)
    if existing_hash is None or existing_hash == new_hash:
        return filename
    stem, ext = os.path.splitext(filename)
    return f"{stem}__{new_hash[:8]}{ext}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Notability → OmarOS PDF sync")
    ap.add_argument("--source", action="append", type=Path, default=[],
                    help="Explicit source folder (repeatable). Overrides auto-discover.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-sidecar", action="store_true",
                    help="Skip pdftotext sidecar generation.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    log = (lambda *a, **k: None) if args.quiet else print

    for d in (LANDING, PDFS, SIDECARS, SNAPSHOTS):
        d.mkdir(parents=True, exist_ok=True)

    sources = discover_sources(args.source)
    if not sources:
        log("no notability source folders found — see SKILL.md setup section", file=sys.stderr)
        return 2

    log(f"[notability-sync] {len(sources)} source(s): {[str(s) for s in sources]}")

    state = load_json(STATE_FILE, {"version": 1, "entries": {}})
    entries: dict[str, dict] = state.get("entries", {})

    records: dict[str, PdfRecord] = {}
    note_count, note_placeholder, note_mirrored = 0, 0, 0
    NOTES_RAW.mkdir(parents=True, exist_ok=True)

    for src in sources:
        label = source_label(src)
        for pdf_path, root, kind in scan_source(src):
            if kind == "note":
                note_count += 1
                if pdf_path.is_file() and is_placeholder(pdf_path):
                    note_placeholder += 1
                    continue
                if not args.dry_run:
                    rel = pdf_path.relative_to(root) if pdf_path.is_relative_to(root) else Path(pdf_path.name)
                    dest = NOTES_RAW / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if pdf_path.is_dir():
                        if not dest.exists():
                            shutil.copytree(pdf_path, dest)
                            note_mirrored += 1
                    else:
                        if not dest.exists() or dest.stat().st_size != pdf_path.stat().st_size:
                            shutil.copy2(pdf_path, dest)
                            note_mirrored += 1
                continue
            if pdf_path.is_file() and is_placeholder(pdf_path):
                log(f"  skip placeholder {pdf_path}", file=sys.stderr)
                continue
            try:
                h = sha256_file(pdf_path)
            except OSError as e:
                log(f"  skip {pdf_path}: {e}", file=sys.stderr)
                continue
            rec = records.get(h)
            if rec is None:
                try:
                    st = pdf_path.stat()
                except OSError:
                    continue
                rec = PdfRecord(
                    hash=h,
                    filename=pdf_path.name,
                    bytes_=st.st_size,
                    mtime=datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                )
                records[h] = rec
            rec.sources.add(label)
            rel = str(pdf_path.relative_to(root)) if pdf_path.is_relative_to(root) else str(pdf_path)
            if rel not in rec.source_paths:
                rec.source_paths.append(rel)

    now_iso = datetime.now().isoformat(timespec="seconds")

    filename_map: dict[str, str] = {}
    for existing_pdf in PDFS.glob("*.pdf"):
        entry = next((e for e in entries.values() if e.get("filename") == existing_pdf.name), None)
        if entry:
            filename_map[existing_pdf.name] = entry.get("hash", "")
        else:
            try:
                filename_map[existing_pdf.name] = sha256_file(existing_pdf)
            except OSError:
                pass

    created, updated, noop, sidecars_written = 0, 0, 0, 0

    for h, rec in records.items():
        dest_name = disambiguate_filename(rec.filename, h, filename_map)
        dest_pdf = PDFS / dest_name

        prev = entries.get(h)
        need_copy = not dest_pdf.exists() or (prev is None) or (prev.get("filename") != dest_name)

        if args.dry_run:
            if need_copy:
                log(f"  would copy {rec.filename} → {dest_name}")
            continue

        if need_copy:
            src_path = sources[0] / rec.source_paths[0] if rec.source_paths else None
            chosen = None
            for src in sources:
                for rel in rec.source_paths:
                    cand = src / rel
                    if cand.is_file():
                        chosen = cand
                        break
                if chosen:
                    break
            if chosen is None:
                log(f"  !! lost track of source file for {rec.filename}", file=sys.stderr)
                continue
            shutil.copy2(chosen, dest_pdf)
            filename_map[dest_name] = h
            if prev is None:
                created += 1
            else:
                updated += 1
        else:
            noop += 1

        if not args.no_sidecar:
            sidecar_path = SIDECARS / (dest_pdf.stem + ".md")
            if need_copy or not sidecar_path.exists():
                body = extract_text(dest_pdf)
                rec.filename = dest_name
                write_sidecar(dest_pdf, rec, body)
                sidecars_written += 1

        entries[h] = {
            "hash": h,
            "filename": dest_name,
            "sources": sorted(rec.sources),
            "source_paths": rec.source_paths,
            "mtime": rec.mtime,
            "bytes": rec.bytes_,
            "last_seen": now_iso,
        }

    missing = [h for h in entries if h not in records]
    for h in missing:
        entries[h]["missing_since"] = entries[h].get("missing_since") or now_iso

    if args.dry_run:
        log(f"[dry-run] remote={len(records)} state={len(entries)} missing={len(missing)}")
        return 0

    state.update({"version": 1, "last_sync": now_iso, "entries": entries})
    atomic_write_json(STATE_FILE, state)

    snapshot = {
        "synced_at": now_iso,
        "sources": [str(s) for s in sources],
        "count": len(records),
        "entries": [
            {
                "hash": r.hash, "filename": r.filename, "bytes": r.bytes_,
                "mtime": r.mtime, "sources": sorted(r.sources),
            }
            for r in records.values()
        ],
    }
    snap_name = SNAPSHOTS / (datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".json")
    atomic_write_json(snap_name, snapshot)

    index = {
        "generated_at": now_iso,
        "total": len(entries),
        "missing": len(missing),
        "by_hash": {h: entries[h] for h in entries},
    }
    atomic_write_json(INDEX_FILE, index)

    summary = {
        "total_remote_pdfs": len(records),
        "created": created,
        "updated": updated,
        "noop": noop,
        "missing": len(missing),
        "sidecars_written": sidecars_written,
        "notes_seen": note_count,
        "notes_placeholder_skipped": note_placeholder,
        "notes_mirrored": note_mirrored,
        "snapshot": str(snap_name),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
