#!/usr/bin/env python3
"""Parse a 6-section isomorph-synth artefact and materialize its files on disk.

Reads a markdown document produced by the isomorph-synth skill (or hand-written
following the same 6-section contract), reconstructs the file tree declared in
Section 2 / Section 3, and writes every file to a target directory.

Usage:
    python3 materialize_scaffold.py <artefact.md> --out <target-directory>
    python3 materialize_scaffold.py <artefact.md> --out <dir> --force
    python3 materialize_scaffold.py <artefact.md> --out <dir> --dry-run

Exit codes:
    0  success — every declared file written (or would-be-written in --dry-run)
    2  bad CLI arguments or unreadable artefact
    3  malformed artefact (missing section, file without fence, etc.)
    4  collision detected (target file exists and non-empty, --force not set)

Safety:
  - The target directory is created if missing (parents included).
  - Files are written using UTF-8 without BOM.
  - Existing non-empty files are NOT overwritten unless --force is passed.
  - Existing empty files ARE overwritten (treated as placeholders).
  - No file outside the target directory is ever touched.
  - The script does NOT execute any generated file. Materialisation is content-only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTION_HEADINGS = [
    "# 1. Assumptions",
    "# 2. Generated folder structure",
    "# 3. File contents",
    "# 4. Adaptation points",
    "# 5. Integration notes",
    "# 6. Reintegration map",
]

# Fenced block inside Section 3: each file is announced by a `## <path>` H2,
# followed by a fenced code block containing the file content. We capture both.
_H2_FILE_RE = re.compile(r"^##\s+(\S.*?)\s*$")
_FENCE_OPEN_RE = re.compile(r"^```([A-Za-z0-9_+\-.]*)\s*$")
_FENCE_CLOSE_RE = re.compile(r"^```\s*$")


def _section_span(lines: list[str], heading: str) -> tuple[int, int] | None:
    """Return [start_idx, end_idx) covering the section under `heading`.

    start_idx points at the heading line; end_idx at the next H1 or len(lines).
    """
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
    except StopIteration:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("# ") and lines[j].strip() != heading:
            end = j
            break
    return start, end


def _extract_file_contents(lines: list[str], span: tuple[int, int]) -> list[tuple[str, str]]:
    """Walk Section 3 and return a list of (relative_path, content) pairs.

    Each `## <path>` H2 introduces a file; the next fenced block is its content.
    Prose between fences is ignored. Language tag on the opening fence is
    discarded (the path extension is authoritative).
    """
    s, e = span
    out: list[tuple[str, str]] = []
    i = s + 1
    current_path: str | None = None
    while i < e:
        line = lines[i]
        m = _H2_FILE_RE.match(line)
        if m:
            current_path = m.group(1).strip().strip("`")
            i += 1
            continue
        if _FENCE_OPEN_RE.match(line) and current_path is not None:
            # Consume until the matching closing fence.
            buf: list[str] = []
            i += 1
            while i < e and not _FENCE_CLOSE_RE.match(lines[i]):
                buf.append(lines[i])
                i += 1
            # Skip the closing fence if present.
            if i < e:
                i += 1
            content = "\n".join(buf)
            if not content.endswith("\n"):
                content += "\n"
            out.append((current_path, content))
            current_path = None
            continue
        i += 1
    return out


def _safe_join(root: Path, rel: str) -> Path:
    """Resolve `root / rel` and refuse paths that escape `root`."""
    rel_norm = rel.lstrip("/")
    target = (root / rel_norm).resolve()
    root_resolved = root.resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError:
        raise ValueError(f"path escapes target root: {rel!r}")
    return target


def materialize(
    artefact_path: Path,
    target: Path,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    text = artefact_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Validate all 6 sections present.
    missing: list[str] = []
    for h in SECTION_HEADINGS:
        if h not in (ln.strip() for ln in lines):
            missing.append(h)
    if missing:
        raise RuntimeError(f"malformed artefact: missing section(s) {missing!r}")

    s3 = _section_span(lines, "# 3. File contents")
    if s3 is None:
        raise RuntimeError("Section 3 not locatable (should have been caught above)")

    files = _extract_file_contents(lines, s3)
    if not files:
        raise RuntimeError("Section 3 contains no parseable files")

    target.mkdir(parents=True, exist_ok=True)
    collisions: list[str] = []
    written: list[str] = []
    skipped: list[str] = []

    for rel, content in files:
        try:
            full = _safe_join(target, rel)
        except ValueError as exc:
            raise RuntimeError(str(exc))
        existing_non_empty = full.exists() and full.is_file() and full.stat().st_size > 0
        if existing_non_empty and not force:
            collisions.append(rel)
            continue
        if dry_run:
            written.append(rel)
            continue
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        written.append(rel)

    return {
        "artefact": str(artefact_path),
        "target": str(target),
        "files_declared": len(files),
        "files_written": written,
        "collisions": collisions,
        "skipped": skipped,
        "dry_run": dry_run,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("artefact", help="path to the 6-section isomorph-synth markdown artefact")
    ap.add_argument("--out", required=True, help="target directory to materialize into")
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing non-empty files (default: refuse)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be written; touch nothing on disk")
    args = ap.parse_args()

    artefact = Path(args.artefact).expanduser()
    target = Path(args.out).expanduser()

    if not artefact.exists():
        sys.stderr.write(f"error: artefact not found: {artefact}\n")
        sys.exit(2)
    if target.exists() and not target.is_dir():
        sys.stderr.write(f"error: target exists and is not a directory: {target}\n")
        sys.exit(2)

    try:
        result = materialize(artefact, target, force=args.force, dry_run=args.dry_run)
    except RuntimeError as exc:
        sys.stderr.write(f"error: {exc}\n")
        sys.exit(3)

    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["collisions"] and not args.force:
        sys.stderr.write(
            f"\n{len(result['collisions'])} file(s) already exist and were not overwritten. "
            "Re-run with --force to overwrite, or materialize into an empty directory.\n"
        )
        sys.exit(4)


if __name__ == "__main__":
    main()
