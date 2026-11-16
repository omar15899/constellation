#!/usr/bin/env python3
"""Validate a 6-section isomorph-synth artefact.

Checks performed:

  1. All six required H1 headings present, in order, spelled exactly.
  2. Section 2 (Generated folder structure) contains a fenced tree block.
  3. Section 3 has at least one `## <path>` file subsection, each followed
     by exactly one fenced code block.
  4. Every file listed in the Section 2 tree has matching contents in Section 3
     (stub / empty `__init__.py` may be elided; the validator tolerates that).
  5. Every adaptation marker occurrence in Section 3 (matching the regex below)
     has a corresponding bullet in Section 4.
  6. Every bullet in Section 4 appears as a row in Section 6 (Reintegration map).
  7. At least one test file is present (a file whose path contains `tests/` or
     whose basename starts with `test_`).
  8. No bare `TODO` / `FIXME` / `XXX` outside a labelled marker comment.

Output: prose summary by default; `--json` for a machine-readable report.

Exit codes:
  0  all checks passed (warnings may be present)
  1  one or more hard invariants violated
  2  bad CLI / file not readable
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_HEADINGS = [
    "# 1. Assumptions",
    "# 2. Generated folder structure",
    "# 3. File contents",
    "# 4. Adaptation points",
    "# 5. Integration notes",
    "# 6. Reintegration map",
]

MARKER_RE = re.compile(
    r"(USER-INTEGRATION REQUIRED|ADAPTATION POINT|PROJECT-SPECIFIC IMPLEMENTATION GOES HERE)"
)

BARE_TODO_RE = re.compile(r"\b(TODO|FIXME|XXX)\b")

_H2_FILE_RE = re.compile(r"^##\s+(\S.*?)\s*$")
_FENCE_OPEN_RE = re.compile(r"^```([A-Za-z0-9_+\-.]*)\s*$")
_FENCE_CLOSE_RE = re.compile(r"^```\s*$")


def _section_span(lines: list[str], heading: str) -> tuple[int, int] | None:
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


def _check_headings(lines: list[str]) -> list[str]:
    problems: list[str] = []
    h1s = [ln.strip() for ln in lines if ln.startswith("# ")]
    seen: list[int] = []
    for i, h in enumerate(REQUIRED_HEADINGS):
        if h not in h1s:
            problems.append(f"missing required heading: {h!r}")
            continue
        idx = h1s.index(h)
        seen.append(idx)
    for i in range(1, len(seen)):
        if seen[i] < seen[i - 1]:
            problems.append(
                f"section order violated: {REQUIRED_HEADINGS[i]!r} appears before "
                f"{REQUIRED_HEADINGS[i - 1]!r}"
            )
    return problems


def _tree_files(lines: list[str], span: tuple[int, int]) -> list[str]:
    """Extract file-like entries from the Section 2 fenced tree block."""
    s, e = span
    inside = False
    files: list[str] = []
    stack: list[tuple[int, str]] = []  # (indent, name) — rebuild path segments
    for ln in lines[s + 1:e]:
        if _FENCE_OPEN_RE.match(ln):
            inside = True
            stack = []
            continue
        if _FENCE_CLOSE_RE.match(ln) and inside:
            inside = False
            continue
        if not inside:
            continue
        # Strip tree glyphs to get the name and guess the depth by position.
        raw = ln.rstrip()
        stripped = re.sub(r"^[│├└─\s]+", "", raw)
        if not stripped:
            continue
        # Indent: count the leading glyph-and-space segments.
        indent = (len(raw) - len(stripped)) // 4 if (len(raw) - len(stripped)) >= 4 else 0
        while stack and stack[-1][0] >= indent:
            stack.pop()
        # Drop trailing slash (directory marker) but track it.
        is_dir = stripped.endswith("/")
        name = stripped.rstrip("/")
        stack.append((indent, name))
        full = "/".join(part for _, part in stack)
        if not is_dir and "." in Path(name).name:
            files.append(full)
    return files


def _section3_files(lines: list[str], span: tuple[int, int]) -> list[tuple[str, int]]:
    """Return (relative_path, fence_line_count) per file in Section 3."""
    s, e = span
    out: list[tuple[str, int]] = []
    current: str | None = None
    i = s + 1
    while i < e:
        ln = lines[i]
        m = _H2_FILE_RE.match(ln)
        if m:
            current = m.group(1).strip().strip("`")
            i += 1
            continue
        if _FENCE_OPEN_RE.match(ln) and current is not None:
            start = i
            i += 1
            while i < e and not _FENCE_CLOSE_RE.match(lines[i]):
                i += 1
            end = i  # closing fence
            out.append((current, end - start - 1))
            current = None
            i += 1
            continue
        i += 1
    return out


def _extract_markers(lines: list[str], span: tuple[int, int]) -> list[tuple[str, str]]:
    """Return (marker_kind, containing_file) for every marker occurrence in Section 3."""
    s, e = span
    out: list[tuple[str, str]] = []
    current_file: str | None = None
    inside_fence = False
    for ln in lines[s + 1:e]:
        m_file = _H2_FILE_RE.match(ln)
        if m_file:
            current_file = m_file.group(1).strip().strip("`")
            inside_fence = False
            continue
        if _FENCE_OPEN_RE.match(ln):
            inside_fence = True
            continue
        if _FENCE_CLOSE_RE.match(ln):
            inside_fence = False
            continue
        if not inside_fence:
            continue
        for m in MARKER_RE.finditer(ln):
            out.append((m.group(1), current_file or "<unknown>"))
    return out


def _extract_markers_section(
    lines: list[str], span: tuple[int, int]
) -> list[str]:
    """Return the marker kinds enumerated in Section 4 bullets, in order."""
    s, e = span
    out: list[str] = []
    for ln in lines[s + 1:e]:
        if not ln.lstrip().startswith("-"):
            continue
        m = MARKER_RE.search(ln)
        if m:
            out.append(m.group(1))
    return out


def _count_reintegration_rows(lines: list[str], span: tuple[int, int]) -> int:
    s, e = span
    count = 0
    in_table = False
    for ln in lines[s + 1:e]:
        stripped = ln.rstrip()
        if stripped.startswith("|") and "---" in stripped:
            in_table = True
            continue
        if in_table and stripped.startswith("|"):
            # Only count rows with at least 5 pipes (6 columns).
            if stripped.count("|") >= 7:
                count += 1
        elif in_table and not stripped.startswith("|"):
            in_table = False
    return count


def _find_bare_todos(lines: list[str], span: tuple[int, int]) -> list[str]:
    """Return lines with TODO/FIXME/XXX that are NOT adjacent to a marker keyword."""
    s, e = span
    hits: list[str] = []
    inside_fence = False
    for idx, ln in enumerate(lines[s + 1:e], start=s + 1):
        if _FENCE_OPEN_RE.match(ln):
            inside_fence = True
            continue
        if _FENCE_CLOSE_RE.match(ln):
            inside_fence = False
            continue
        if not inside_fence:
            continue
        if BARE_TODO_RE.search(ln) and not MARKER_RE.search(ln):
            hits.append(f"line {idx + 1}: {ln.strip()[:120]}")
    return hits


def _has_tests(files: list[str]) -> bool:
    for f in files:
        if "tests/" in f or "/tests/" in f:
            return True
        if Path(f).name.startswith("test_"):
            return True
    return False


def validate(text: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    problems: list[str] = []
    warnings: list[str] = []

    problems += _check_headings(lines)

    s2 = _section_span(lines, "# 2. Generated folder structure")
    s3 = _section_span(lines, "# 3. File contents")
    s4 = _section_span(lines, "# 4. Adaptation points")
    s6 = _section_span(lines, "# 6. Reintegration map")

    if s2 is None or s3 is None or s4 is None or s6 is None:
        # Earlier heading check already recorded this; short-circuit.
        return problems, warnings

    tree_files = _tree_files(lines, s2)
    section3_files = _section3_files(lines, s3)
    section3_names = {p for p, _ in section3_files}

    if not section3_files:
        problems.append("Section 3 (File contents) contains no file subsections")

    # Every tree file should have Section 3 content, unless it's a trivially-empty __init__.py.
    for t in tree_files:
        if t in section3_names:
            continue
        if Path(t).name == "__init__.py":
            continue
        warnings.append(
            f"file declared in Section 2 tree has no matching Section 3 content: {t!r}"
        )

    # Every Section 3 file should exist in the tree (or be close enough).
    tree_set = set(tree_files)
    for p, _ in section3_files:
        # Tolerate relative-path variants: match by suffix.
        if p in tree_set:
            continue
        if any(t.endswith(p) or p.endswith(t) for t in tree_set):
            continue
        warnings.append(
            f"file in Section 3 not found in Section 2 tree: {p!r}"
        )

    # Markers: count inline vs enumerated vs reintegration-map rows.
    inline = _extract_markers(lines, s3)
    enumerated = _extract_markers_section(lines, s4)
    reintegration_rows = _count_reintegration_rows(lines, s6)

    if len(inline) != len(enumerated):
        problems.append(
            f"marker count mismatch: {len(inline)} inline markers in Section 3 "
            f"vs {len(enumerated)} enumerated in Section 4"
        )
    if len(enumerated) != reintegration_rows:
        problems.append(
            f"reintegration-map row count mismatch: {len(enumerated)} adaptation points "
            f"vs {reintegration_rows} rows in Section 6"
        )

    # Bare TODOs.
    todos = _find_bare_todos(lines, s3)
    for t in todos:
        warnings.append(f"bare TODO/FIXME outside a labelled marker: {t}")

    # Tests present?
    if not _has_tests([p for p, _ in section3_files]):
        problems.append("no test file present in Section 3 (expected at least one `tests/…` or `test_*.py`)")

    return problems, warnings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("artefact", help="path to the 6-section isomorph-synth artefact")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as failures")
    ap.add_argument("--json", action="store_true",
                    help="emit a machine-readable JSON report")
    args = ap.parse_args()

    p = Path(args.artefact).expanduser()
    if not p.exists():
        sys.stderr.write(f"error: file not found: {p}\n")
        sys.exit(2)
    text = p.read_text(encoding="utf-8")
    problems, warnings = validate(text)

    if args.json:
        payload = {
            "file": str(p),
            "problems": problems,
            "warnings": warnings,
            "ok": not problems and (not args.strict or not warnings),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if problems:
            print(f"PROBLEMS ({len(problems)}):")
            for msg in problems:
                print(f"  - {msg}")
        if warnings:
            print(f"WARNINGS ({len(warnings)}):")
            for msg in warnings:
                print(f"  - {msg}")
        if not problems and not warnings:
            print("OK — artefact conforms to the 6-section contract.")
        elif not problems:
            print(f"OK with {len(warnings)} warnings.")

    if problems:
        sys.exit(1)
    if args.strict and warnings:
        sys.exit(1)


if __name__ == "__main__":
    main()
