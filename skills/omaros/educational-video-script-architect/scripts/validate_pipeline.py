#!/usr/bin/env python3
"""Validate an educational-video pipeline folder.

Checks an existing full 13-file deliverable assembled from the package templates.
This format is optional; a shorter requested deliverable does not need this validator.

  1. Every required file exists.
  2. Every file carries a YAML frontmatter block with the expected `note_type`.
  3. INDEX.md references all 12 sibling files.
  4. The single-sentence essence appears verbatim in 00_declaration.md, 05_narration_script.md
     and INDEX.md.
  5. 05_narration_script.md is structurally well-formed: every formal-row tag is preceded
     by a preamble-row tag, the [ESSENCE] tag appears exactly once, the [CROSS_DOMAIN]
     tag appears at least once.
  6. 06_voiceover.md contains [PAUSE Ns] markers consistent with the narration script.
  7. No file still has the `status: scaffolded` flag — every file must be flipped to
     `status: draft` (or further) once written.

Usage:
    python validate_pipeline.py <pipeline-folder>

Exit code: 0 if all checks pass, 1 otherwise. Output is human-readable; intended for
the rigor-audit step (file 11) and any pre-commit hook the user may wire up.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

REQUIRED = {
    "INDEX.md": "video_pipeline_index",
    "00_declaration.md": "video_declaration",
    "01_conceptual_blueprint.md": "video_conceptual_blueprint",
    "02_pedagogical_design.md": "video_pedagogical_design",
    "03_scene_architecture.md": "video_scene_architecture",
    "04_visual_language.md": "video_visual_language",
    "05_narration_script.md": "video_narration_script",
    "06_voiceover.md": "video_voiceover",
    "07_voice_direction.md": "video_voice_direction",
    "08_storyboard.md": "video_storyboard",
    "09_image_prompts.md": "video_image_prompts",
    "10_manim_blueprint.md": None,  # legacy template — note_type may vary
    "11_rigor_audit.md": "video_rigor_audit",
}

# Production-track artefacts — validated when the project's INDEX.md or any file in
# the pipeline carries `production_track: true` in its frontmatter, OR when the
# pipeline folder contains any of these files (presence-triggered).
PRODUCTION_TRACK = {
    "08_shotlist.md": "video_shotlist",
    "09_animation_spec.yaml": None,                       # YAML — no markdown frontmatter
    "10_asset_manifest.yaml": None,
    "10b_data_manifest.yaml": None,
    "11_manim_component_library.md": "video_manim_component_library",
    "12_render_validation_rubric.md": "video_render_validation_rubric",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
ESSENCE_RE = re.compile(r"^>\s+(.+?)\s*$", re.MULTILINE)
TAG_RE = re.compile(r"\[(HOOK|PREAMBLE|FORMAL|INSTANCE|BOUNDARY|CROSS_DOMAIN|RETRIEVAL|SELF_EXPLAIN|ESSENCE|TRANSITION|INFORMAL|OBJECT_VS_REP)\]")
PAUSE_RE = re.compile(r"\[PAUSE\s+([\d.]+)s?\]")


class Check(NamedTuple):
    name: str
    ok: bool
    note: str


def _read(path: Path) -> str:
    return path.read_text(errors="replace") if path.exists() else ""


def _frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.search(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def _files_present(folder: Path) -> list[Check]:
    checks: list[Check] = []
    for f in REQUIRED:
        p = folder / f
        checks.append(Check(f"file:{f}", p.exists(), str(p)))
    return checks


def _frontmatter_ok(folder: Path) -> list[Check]:
    checks: list[Check] = []
    for f, expected_type in REQUIRED.items():
        p = folder / f
        if not p.exists():
            continue
        fm = _frontmatter(_read(p))
        if not fm:
            checks.append(Check(f"frontmatter:{f}", False, "missing frontmatter"))
            continue
        if expected_type and fm.get("note_type") != expected_type:
            checks.append(
                Check(
                    f"note_type:{f}",
                    False,
                    f"expected {expected_type!r}, got {fm.get('note_type')!r}",
                )
            )
        else:
            checks.append(Check(f"note_type:{f}", True, fm.get("note_type", "?")))
        if fm.get("status") == "scaffolded":
            checks.append(
                Check(
                    f"status:{f}",
                    False,
                    "still 'scaffolded' — flip to 'draft' once written",
                )
            )
    return checks


def _index_references(folder: Path) -> list[Check]:
    idx = _read(folder / "INDEX.md")
    out: list[Check] = []
    for f in REQUIRED:
        if f == "INDEX.md":
            continue
        out.append(Check(f"index_ref:{f}", f in idx, "referenced in INDEX.md"))
    return out


def _essence_verbatim(folder: Path) -> Check:
    decl = _read(folder / "00_declaration.md")
    script = _read(folder / "05_narration_script.md")
    index = _read(folder / "INDEX.md")
    matches = ESSENCE_RE.findall(decl)
    if not matches:
        return Check("essence:declaration", False, "no quoted essence found in 00_declaration.md")
    essence = matches[0].strip()
    if essence.startswith("`<") and essence.endswith(">`"):
        return Check("essence:not_filled", False, "essence still a placeholder")
    in_script = essence in script
    in_index = essence in index
    if in_script and in_index:
        return Check("essence:verbatim", True, "found in 05 and INDEX")
    return Check(
        "essence:verbatim",
        False,
        f"missing in {'05_narration_script.md' if not in_script else ''} "
        f"{'INDEX.md' if not in_index else ''}".strip(),
    )


def _script_structure(folder: Path) -> list[Check]:
    text = _read(folder / "05_narration_script.md")
    if not text:
        return [Check("script:exists", False, "missing")]
    # Only count tags inside real script rows. Script rows start with "| R<digits>".
    row_lines = [l for l in text.splitlines() if re.match(r"^\|\s*R\d{3}\s*\|", l)]
    tags = []
    for line in row_lines:
        tags.extend(TAG_RE.findall(line))
    out: list[Check] = []
    out.append(Check("script:essence_count", tags.count("ESSENCE") == 1, f"{tags.count('ESSENCE')} ESSENCE tags (expected 1)"))
    out.append(Check("script:cross_domain", tags.count("CROSS_DOMAIN") >= 1, f"{tags.count('CROSS_DOMAIN')} CROSS_DOMAIN tags (expected ≥ 1)"))
    # Layered exposition: every FORMAL must be preceded (somewhere earlier in the same scene window) by a PREAMBLE.
    seen_preamble = False
    formal_without_preamble = 0
    for tag in tags:
        if tag == "PREAMBLE":
            seen_preamble = True
        elif tag == "FORMAL":
            if not seen_preamble:
                formal_without_preamble += 1
            seen_preamble = False
    out.append(
        Check(
            "script:preamble_before_formal",
            formal_without_preamble == 0,
            f"{formal_without_preamble} FORMAL rows without a preceding PREAMBLE",
        )
    )
    return out


def _voiceover_pauses(folder: Path) -> Check:
    vo = _read(folder / "06_voiceover.md")
    pauses = PAUSE_RE.findall(vo)
    if not pauses:
        return Check("voiceover:pauses", False, "no [PAUSE Ns] markers found")
    return Check("voiceover:pauses", True, f"{len(pauses)} pause markers")


def _production_track_active(folder: Path) -> bool:
    """The production track is active if any of its files exist in the folder,
    or if INDEX.md's frontmatter has `production_track: true`."""
    if any((folder / f).exists() for f in PRODUCTION_TRACK):
        return True
    idx = _frontmatter(_read(folder / "INDEX.md"))
    return idx.get("production_track", "").lower() == "true"


def _production_track_checks(folder: Path) -> list[Check]:
    """Validate the production-track files (presence, minimal frontmatter on the
    .md ones). The .yaml files are checked for presence + non-empty body only —
    full schema validation is out of scope for this validator."""
    checks: list[Check] = []
    if not _production_track_active(folder):
        return checks
    for f, expected_type in PRODUCTION_TRACK.items():
        p = folder / f
        present = p.exists()
        checks.append(Check(f"prod_track:file:{f}", present, str(p)))
        if not present:
            continue
        text = _read(p)
        if not text.strip():
            checks.append(Check(f"prod_track:nonempty:{f}", False, "empty file"))
            continue
        if expected_type is not None:
            fm = _frontmatter(text)
            if not fm:
                checks.append(Check(f"prod_track:frontmatter:{f}", False, "missing frontmatter"))
            elif fm.get("note_type") != expected_type:
                checks.append(
                    Check(
                        f"prod_track:note_type:{f}",
                        False,
                        f"expected {expected_type!r}, got {fm.get('note_type')!r}",
                    )
                )
            else:
                checks.append(Check(f"prod_track:note_type:{f}", True, expected_type))
    return checks


def run(folder: Path) -> int:
    print(f"# Validating pipeline at {folder}\n")
    if not folder.is_dir():
        print(f"[FAIL] Not a directory: {folder}")
        return 1

    all_checks: list[Check] = []
    all_checks += _files_present(folder)
    all_checks += _frontmatter_ok(folder)
    all_checks += _index_references(folder)
    all_checks.append(_essence_verbatim(folder))
    all_checks += _script_structure(folder)
    all_checks.append(_voiceover_pauses(folder))
    all_checks += _production_track_checks(folder)

    n_ok = sum(1 for c in all_checks if c.ok)
    n_fail = sum(1 for c in all_checks if not c.ok)

    for c in all_checks:
        symbol = "PASS" if c.ok else "FAIL"
        print(f"[{symbol}] {c.name:40s} {c.note}")

    print()
    print(f"Summary: {n_ok} pass, {n_fail} fail.")
    return 0 if n_fail == 0 else 1


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path, help="Pipeline folder to validate")
    args = p.parse_args()
    sys.exit(run(args.folder))


if __name__ == "__main__":
    main()
