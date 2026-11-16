#!/usr/bin/env python3
"""Validate a project-isomorph dossier against the 8-section contract.

Reads a markdown file and applies a battery of checks. Exits non-zero if any
hard invariant is violated; emits warnings for soft issues.

Checks performed:

  1. All 8 required H1 sections present, in order, with exact spelling.
  2. Section 4 contains at least one component subsection, and every
     component subsection carries both "Input Signature" and
     "Output Signature" markers.
  3. Section 3 subsections carry "Role", "Dependencies", "Interfaces exposed",
     "Invariants" markers.
  4. Section 5 subsections carry "Structure" and "Constraints" markers.
  5. No code fence in the dossier looks like real source code. A fence is
     flagged if it contains at least two of: `def `, `function `, `class `,
     `import `, `return ` — that combination signals copied code rather
     than pseudocode / mermaid / yaml.
  6. Leak heuristic: flag tokens that look like real business identifiers —
     camelCase names longer than 5 chars that don't start with the
     canonical placeholder prefixes (`Module_`, `Dataset_`, `Schema_`,
     `Concept_`, `ExternalService_`, `Database_`, `Topic_`, `Queue_`,
     `ENV_`, `FLAG_`, `SECRET_HANDLE_`, `Runtime_`).

Usage:
    python3 validate_output.py <dossier.md>
    python3 validate_output.py <dossier.md> --strict    # warnings fail too
    python3 validate_output.py <dossier.md> --json      # machine-readable output

Exit codes:
  0  all checks pass (warnings may be present)
  1  one or more hard invariants violated
  2  bad CLI / file not readable
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    "# 1. Project Abstract Overview",
    "# 2. Global Architecture Graph",
    "# 3. Folder / Module Structure",
    "# 4. Component Specifications",
    "# 5. Data Structures & Schemas",
    "# 6. Execution Flow",
    "# 7. Integration Points",
    "# 8. Reconstructability Notes",
]

PLACEHOLDER_PREFIXES = (
    "Module_", "Dataset_", "Schema_", "Concept_", "Component",
    "ExternalService_", "Database_", "Topic_", "Queue_",
    "ENV_", "FLAG_", "SECRET_HANDLE_", "Runtime_",
    "Dataset", "Service", "Record", "RecordType", "Enum",
)

# Tokens starting with these are considered generic placeholders
# even if they don't carry a listed prefix — they are named after roles.
PLACEHOLDER_SUFFIXES = (
    "Component", "Service", "Record", "Enum", "Handle",
)

CODE_FENCE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
CODE_HINTS = (
    re.compile(r"^\s*def\s+\w+\s*\(", re.MULTILINE),
    re.compile(r"^\s*class\s+\w+\s*[:\(]", re.MULTILINE),
    re.compile(r"^\s*function\s+\w+\s*\(", re.MULTILINE),
    re.compile(r"^\s*import\s+\w+", re.MULTILINE),
    re.compile(r"^\s*from\s+\S+\s+import\s+", re.MULTILINE),
    re.compile(r"^\s*const\s+\w+\s*=", re.MULTILINE),
    re.compile(r"^\s*return\s+", re.MULTILINE),
)
ALLOWED_FENCE_LANGS = {"mermaid", "yaml", "json", "toml", "bash", "text", "", "markdown"}

CAMEL_TOKEN_RE = re.compile(r"\b[a-z][a-zA-Z0-9]{4,}[A-Z][a-zA-Z0-9]*\b")
# Matches identifiers like `bloombergClient`, `pricingEngine`, etc. — real
# source code naming conventions the dossier should NOT contain.


def _check_sections(text: str, problems: list, warnings: list) -> None:
    # find all H1 lines (start of line `# `), preserve order
    h1_lines = [ln.strip() for ln in text.splitlines() if ln.startswith("# ")]
    for i, required in enumerate(REQUIRED_SECTIONS):
        if required not in h1_lines:
            problems.append(f"missing required section: {required!r}")
            continue
        idx = h1_lines.index(required)
        # Check it's after all previous required sections
        for prev in REQUIRED_SECTIONS[:i]:
            if prev not in h1_lines:
                continue
            if h1_lines.index(prev) > idx:
                problems.append(
                    f"section {required!r} appears before {prev!r} "
                    "(required order violated)"
                )


def _section_body(text: str, heading: str) -> str:
    """Return the text between `heading` and the next H1, or '' if not found."""
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
    except StopIteration:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("# "):
            end = j
            break
    return "\n".join(lines[start:end])


def _check_module_structure(text: str, problems: list, warnings: list) -> None:
    body = _section_body(text, "# 3. Folder / Module Structure")
    if not body:
        return
    module_h2 = re.findall(r"^##\s+.+$", body, re.MULTILINE)
    if not module_h2:
        problems.append("Section 3: no module subsections found (expected at least one `## Module_...` entry)")
        return
    for h2 in module_h2:
        sub = _subsection_body(body, h2)
        for tag in ("Role", "Dependencies", "Interfaces exposed", "Invariants"):
            if f"**{tag}**" not in sub and f"{tag}:" not in sub:
                warnings.append(f"Section 3 subsection {h2.strip('# ').strip()!r}: missing field {tag!r}")


def _check_component_signatures(text: str, problems: list, warnings: list) -> None:
    body = _section_body(text, "# 4. Component Specifications")
    if not body:
        return
    comp_h2 = re.findall(r"^##\s+.+$", body, re.MULTILINE)
    if not comp_h2:
        problems.append("Section 4: no component subsections found (expected at least one `## ...Component` entry)")
        return
    for h2 in comp_h2:
        sub = _subsection_body(body, h2)
        if "Input Signature" not in sub:
            problems.append(f"Section 4 subsection {h2.strip('# ').strip()!r}: missing `Input Signature`")
        if "Output Signature" not in sub:
            problems.append(f"Section 4 subsection {h2.strip('# ').strip()!r}: missing `Output Signature`")


def _check_data_schemas(text: str, problems: list, warnings: list) -> None:
    body = _section_body(text, "# 5. Data Structures & Schemas")
    if not body:
        return
    ds_h2 = re.findall(r"^##\s+.+$", body, re.MULTILINE)
    if not ds_h2:
        warnings.append("Section 5: no dataset subsections found")
        return
    for h2 in ds_h2:
        sub = _subsection_body(body, h2)
        for tag in ("Structure", "Constraints"):
            if f"**{tag}**" not in sub and f"{tag}:" not in sub:
                warnings.append(f"Section 5 subsection {h2.strip('# ').strip()!r}: missing field {tag!r}")


def _subsection_body(section_body: str, heading: str) -> str:
    lines = section_body.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == heading.strip())
    except StopIteration:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end])


def _check_code_fences(text: str, problems: list, warnings: list) -> None:
    for m in CODE_FENCE_RE.finditer(text):
        lang = (m.group(1) or "").lower()
        body = m.group(2)
        # Mermaid diagrams and declarative formats are fine.
        if lang in ALLOWED_FENCE_LANGS:
            continue
        hits = sum(1 for rx in CODE_HINTS if rx.search(body))
        if hits >= 2:
            problems.append(
                f"code fence (lang={lang or 'none'!r}) appears to contain real source "
                f"code — {hits} code indicators matched. "
                "Isomorph dossiers must not include verbatim code."
            )


def _check_leaked_identifiers(text: str, problems: list, warnings: list) -> None:
    # Strip out fenced blocks so mermaid/yaml/bash don't get falsely flagged.
    stripped = CODE_FENCE_RE.sub("", text)
    # Also strip out obvious template tokens like `<something>` placeholders.
    stripped = re.sub(r"<[^>\n]+>", "", stripped)
    suspicious: dict[str, int] = {}
    for tok in CAMEL_TOKEN_RE.findall(stripped):
        # Skip canonical placeholder shapes
        if tok.startswith(PLACEHOLDER_PREFIXES):
            continue
        if any(tok.endswith(suf) for suf in PLACEHOLDER_SUFFIXES):
            continue
        # Skip common non-identifying English words that happen to camelCase
        # in compound contexts ("IoT", "readOnly", "setUp" — harmless here).
        suspicious[tok] = suspicious.get(tok, 0) + 1
    # Surface the top offenders only (noisy otherwise).
    for tok, n in sorted(suspicious.items(), key=lambda kv: -kv[1])[:25]:
        warnings.append(
            f"possible real identifier leak: {tok!r} appears {n}× (expected generic placeholder form)"
        )


def validate(text: str) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    _check_sections(text, problems, warnings)
    _check_module_structure(text, problems, warnings)
    _check_component_signatures(text, problems, warnings)
    _check_data_schemas(text, problems, warnings)
    _check_code_fences(text, problems, warnings)
    _check_leaked_identifiers(text, problems, warnings)
    return problems, warnings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dossier", help="path to the project-isomorph markdown dossier")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as failures")
    ap.add_argument("--json", action="store_true",
                    help="emit a machine-readable JSON report instead of prose")
    args = ap.parse_args()

    p = Path(args.dossier).expanduser()
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
            print("OK — dossier conforms to the 8-section contract.")
        elif not problems:
            print(f"OK with {len(warnings)} warnings.")

    if problems:
        sys.exit(1)
    if args.strict and warnings:
        sys.exit(1)


if __name__ == "__main__":
    main()
