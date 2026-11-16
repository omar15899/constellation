#!/usr/bin/env python3
"""Validate a 8-section isomorph-rebind reintegration map.

Checks performed:

  1. All eight required H1 headings present, in order, spelled exactly.
  2. Section 1 contains the four required sub-groups (`## Known from the generic scaffold`,
     `## Known about the private system`, `## Unknown about the private system`,
     `## Assumptions made to proceed`), each with at least one bullet.
  3. Section 2 has a table with at least one row; every row carries a confidence
     label matching one of {`high confidence`, `medium confidence`, `low confidence`}.
  4. Section 3 has at least one `## AP-<N>` subsection; every such subsection carries
     a `**Tag**:` line with at least one recognised marker.
  5. Section 4 has at least one `## PB-<N>` subsection (unless Section 3 contained
     only `SAFE TO KEEP GENERIC` / `LOCAL NAME REBINDING` markers with no bindings
     needed — emits a warning, not a problem, in that case).
  6. Every AP-id referenced in Section 4 (`implements AP-<N>`) actually exists in
     Section 3.
  7. Section 5 has at least one `## <path>` subsection; every subsection has an
     **Action** from the six closed dispositions.
  8. Section 6 has a numbered list with at least one item.
  9. Section 7 has a table; every row carries a severity + detectability value
     from the closed sets.
 10. Section 8 has a numbered list; each step should reference a Section 6 item
     (warning if not).

Emits prose summary by default, `--json` for machine-readable output.

Exit codes:
  0  all hard checks passed
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
    "# 1. Reintegration assumptions",
    "# 2. System correspondence map",
    "# 3. Adaptation points",
    "# 4. Required private bindings",
    "# 5. File-level integration strategy",
    "# 6. Validation and regression checklist",
    "# 7. Reintegration risks",
    "# 8. Minimal safe integration order",
]

REQUIRED_SECTION1_SUBGROUPS = [
    "## Known from the generic scaffold",
    "## Known about the private system",
    "## Unknown about the private system",
    "## Assumptions made to proceed",
]

CONFIDENCE_VALUES = {"high confidence", "medium confidence", "low confidence"}

MARKERS = {
    "USER-INTEGRATION REQUIRED",
    "ADAPTATION POINT",
    "PRIVATE BINDING REQUIRED",
    "LOCAL NAME REBINDING",
    "SCHEMA REBINDING REQUIRED",
    "INFRASTRUCTURE SUBSTITUTION REQUIRED",
    "SAFE TO KEEP GENERIC",
    "PROJECT-SPECIFIC IMPLEMENTATION GOES HERE",
}
NO_BINDING_MARKERS = {"SAFE TO KEEP GENERIC", "LOCAL NAME REBINDING"}
MARKER_RE = re.compile("|".join(re.escape(m) for m in MARKERS))

FILE_ACTIONS = {
    "keep as is",
    "keep with renaming",
    "keep with local adapter injection",
    "merge manually into an existing private file",
    "use only as a design reference",
    "do not integrate directly",
}

SEVERITY_VALUES = {"low", "medium", "high", "critical"}
DETECTABILITY_VALUES = {"easy", "moderate", "hard", "invisible-until-production"}

AP_ID_RE = re.compile(r"^##\s+AP-(\d+)\b", re.MULTILINE)
PB_ID_RE = re.compile(r"^##\s+PB-(\d+)\b", re.MULTILINE)
IMPLEMENTS_RE = re.compile(r"implements\s+AP-(\d+)", re.IGNORECASE)


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


def _check_headings(lines: list[str], problems: list, warnings: list) -> None:
    h1s = [ln.strip() for ln in lines if ln.startswith("# ")]
    idxs: dict[str, int] = {}
    for i, h in enumerate(REQUIRED_HEADINGS):
        if h not in h1s:
            problems.append(f"missing required heading: {h!r}")
        else:
            idxs[h] = h1s.index(h)
    # Order check among the ones we found.
    ordered = [h for h in REQUIRED_HEADINGS if h in idxs]
    for i in range(1, len(ordered)):
        if idxs[ordered[i]] < idxs[ordered[i - 1]]:
            problems.append(f"section order violated: {ordered[i]!r} appears before {ordered[i - 1]!r}")


def _check_section1(lines: list[str], span, problems, warnings):
    if span is None:
        return
    s, e = span
    body_lines = lines[s + 1:e]
    # Find sub-group headings within Section 1.
    for sub in REQUIRED_SECTION1_SUBGROUPS:
        if sub not in [ln.strip() for ln in body_lines]:
            problems.append(f"Section 1 missing required sub-group: {sub!r}")
            continue
        # Check the sub-group has at least one bullet before the next ## or end.
        sub_idx = next(i for i, ln in enumerate(body_lines) if ln.strip() == sub)
        next_h2 = len(body_lines)
        for j in range(sub_idx + 1, len(body_lines)):
            if body_lines[j].startswith("## "):
                next_h2 = j
                break
        bullet_found = any(
            body_lines[k].lstrip().startswith("-")
            for k in range(sub_idx + 1, next_h2)
        )
        if not bullet_found:
            warnings.append(f"Section 1 sub-group {sub!r} has no bullets — is this genuinely empty?")


def _check_section2_confidence(lines, span, problems, warnings):
    if span is None:
        return
    s, e = span
    in_table = False
    row_count = 0
    missing_confidence_rows: list[str] = []
    for ln in lines[s + 1:e]:
        stripped = ln.rstrip()
        if stripped.startswith("|") and "---" in stripped:
            in_table = True
            continue
        if not in_table:
            continue
        if stripped.startswith("|") and stripped.count("|") >= 5:
            row_count += 1
            low = stripped.lower()
            if not any(cv in low for cv in CONFIDENCE_VALUES):
                missing_confidence_rows.append(stripped[:120])
        elif not stripped.startswith("|") and stripped:
            in_table = False
    if row_count == 0:
        problems.append("Section 2 has no correspondence-map rows")
    for r in missing_confidence_rows:
        problems.append(f"Section 2 row missing confidence label: {r!r}")


def _check_section3(lines, span, problems, warnings):
    if span is None:
        return set(), set()
    s, e = span
    body = "\n".join(lines[s + 1:e])
    ap_ids = {m.group(1) for m in AP_ID_RE.finditer(body)}
    if not ap_ids:
        problems.append("Section 3 has no `## AP-<N>` subsections")
    # Check each AP subsection has a tag.
    ap_tags: dict[str, set[str]] = {}
    for ap in ap_ids:
        start_rx = re.compile(rf"^##\s+AP-{ap}\b", re.MULTILINE)
        m = start_rx.search(body)
        if not m:
            continue
        subsection_start = m.start()
        # end = next ## AP- or end of section
        next_m = AP_ID_RE.search(body, m.end())
        subsection_end = next_m.start() if next_m else len(body)
        sub = body[subsection_start:subsection_end]
        tag_match = re.search(r"\*\*Tag\*\*\s*:\s*(.+)", sub)
        if not tag_match:
            problems.append(f"Section 3 AP-{ap} missing `**Tag**:` line")
            continue
        tags = {m.group(0) for m in MARKER_RE.finditer(tag_match.group(1))}
        if not tags:
            problems.append(f"Section 3 AP-{ap} has `**Tag**:` but no recognised marker on it")
        ap_tags[ap] = tags
    return ap_ids, ap_tags


def _check_section4(lines, span, ap_ids, ap_tags, problems, warnings):
    if span is None:
        return
    s, e = span
    body = "\n".join(lines[s + 1:e])
    pb_ids = {m.group(1) for m in PB_ID_RE.finditer(body)}
    # AP→PB coverage: every AP whose tag requires a binding must have a matching PB.
    needs_binding = {
        ap for ap in ap_ids
        if not ap_tags.get(ap, set()).issubset(NO_BINDING_MARKERS)
    }
    # Extract "implements AP-<N>" references.
    referenced = {m.group(1) for m in IMPLEMENTS_RE.finditer(body)}
    uncovered = needs_binding - referenced
    for ap in sorted(uncovered, key=int):
        problems.append(
            f"Section 4 missing PB that implements AP-{ap} (tag requires a binding)"
        )
    # Every PB must reference an existing AP.
    orphan_refs = referenced - ap_ids
    for ap in sorted(orphan_refs, key=int):
        problems.append(
            f"Section 4 references AP-{ap} which does not appear in Section 3"
        )
    if not pb_ids and needs_binding:
        problems.append("Section 4 has no `## PB-<N>` subsections but Section 3 has adaptation points requiring bindings")


def _check_section5(lines, span, problems, warnings):
    if span is None:
        return
    s, e = span
    body = "\n".join(lines[s + 1:e])
    subs = re.findall(r"^##\s+\S.*$", body, re.MULTILINE)
    if not subs:
        problems.append("Section 5 has no file-subsections")
        return
    for sub in subs:
        start_rx = re.compile(re.escape(sub), re.MULTILINE)
        m = start_rx.search(body)
        next_h2 = re.compile(r"^##\s+\S", re.MULTILINE).search(body, m.end())
        end = next_h2.start() if next_h2 else len(body)
        sub_text = body[m.start():end]
        action_match = re.search(r"\*\*Action\*\*\s*:\s*`?([^`\n]+)`?", sub_text)
        if not action_match:
            problems.append(f"Section 5 {sub.strip()[:80]!r}: missing `**Action**:` line")
            continue
        action = action_match.group(1).strip().strip("`").lower()
        if not any(va in action for va in FILE_ACTIONS):
            problems.append(
                f"Section 5 {sub.strip()[:80]!r}: action {action!r} not in closed set {sorted(FILE_ACTIONS)}"
            )


def _check_section6(lines, span, problems, warnings):
    if span is None:
        return
    s, e = span
    numbered = [ln for ln in lines[s + 1:e] if re.match(r"^\s*\d+\.\s", ln)]
    if not numbered:
        problems.append("Section 6 has no numbered checklist items")


def _check_section7(lines, span, problems, warnings):
    if span is None:
        return
    s, e = span
    in_table = False
    row_count = 0
    for ln in lines[s + 1:e]:
        stripped = ln.rstrip()
        if stripped.startswith("|") and "---" in stripped:
            in_table = True
            continue
        if in_table and stripped.startswith("|") and stripped.count("|") >= 5:
            row_count += 1
            low = stripped.lower()
            if not any(v in low for v in SEVERITY_VALUES):
                problems.append(f"Section 7 row missing severity value: {stripped[:120]!r}")
            if not any(v in low for v in DETECTABILITY_VALUES):
                problems.append(f"Section 7 row missing detectability value: {stripped[:120]!r}")
        elif in_table and not stripped.startswith("|"):
            in_table = False
    if row_count == 0:
        problems.append("Section 7 has no risk rows")


def _check_section8(lines, span, problems, warnings):
    if span is None:
        return
    s, e = span
    numbered = [ln for ln in lines[s + 1:e] if re.match(r"^\s*\d+\.\s", ln)]
    if not numbered:
        problems.append("Section 8 has no numbered integration-order steps")
        return
    # Warn if no step references a Section 6 item.
    has_gate = any(re.search(r"Section 6|item\s+\d+", ln, re.IGNORECASE) for ln in numbered)
    if not has_gate:
        warnings.append("Section 8 steps do not reference Section 6 items — gates are missing")


def validate(text: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    problems: list[str] = []
    warnings: list[str] = []

    _check_headings(lines, problems, warnings)

    s1 = _section_span(lines, "# 1. Reintegration assumptions")
    s2 = _section_span(lines, "# 2. System correspondence map")
    s3 = _section_span(lines, "# 3. Adaptation points")
    s4 = _section_span(lines, "# 4. Required private bindings")
    s5 = _section_span(lines, "# 5. File-level integration strategy")
    s6 = _section_span(lines, "# 6. Validation and regression checklist")
    s7 = _section_span(lines, "# 7. Reintegration risks")
    s8 = _section_span(lines, "# 8. Minimal safe integration order")

    _check_section1(lines, s1, problems, warnings)
    _check_section2_confidence(lines, s2, problems, warnings)
    ap_ids, ap_tags = _check_section3(lines, s3, problems, warnings)
    _check_section4(lines, s4, ap_ids, ap_tags, problems, warnings)
    _check_section5(lines, s5, problems, warnings)
    _check_section6(lines, s6, problems, warnings)
    _check_section7(lines, s7, problems, warnings)
    _check_section8(lines, s8, problems, warnings)

    return problems, warnings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("artefact", help="path to the 8-section reintegration map")
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
            print("OK — reintegration map conforms to the 8-section contract.")
        elif not problems:
            print(f"OK with {len(warnings)} warnings.")

    if problems:
        sys.exit(1)
    if args.strict and warnings:
        sys.exit(1)


if __name__ == "__main__":
    main()
