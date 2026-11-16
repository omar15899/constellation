#!/usr/bin/env python3
"""Scaffold a new educational-video pipeline folder.

Creates `15_Reading_and_Learning/Video_Scripts/<YYYY-MM-DD>_<slug>/` and pre-populates
all 13 deliverable artefacts from the canonical templates in `templates/`. Each artefact
gets a frontmatter block with the topic slug, today's date, and a `status: scaffolded`
marker that is flipped to `draft` as the agent fills the body.

Usage:
    python scaffold_pipeline.py <slug> [--title "<title>"] [--vault <path>]
    python scaffold_pipeline.py cashflows_financial_mathematics --title "Cashflows in Financial Mathematics"

The script is deterministic. Re-running with the same slug on the same day is a no-op
unless `--force` is passed, which overwrites the folder.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"

PIPELINE_FILES: list[tuple[str, str]] = [
    ("INDEX.md", "INDEX_template.md"),
    ("00_declaration.md", "00_declaration_template.md"),
    ("01_conceptual_blueprint.md", "01_conceptual_blueprint_template.md"),
    ("02_pedagogical_design.md", "02_pedagogical_design_template.md"),
    ("03_scene_architecture.md", "03_scene_architecture_template.md"),
    ("04_visual_language.md", "04_visual_language_template.md"),
    ("05_narration_script.md", "05_narration_script_template.md"),
    ("06_voiceover.md", "06_voiceover_template.md"),
    ("07_voice_direction.md", "07_voice_direction_template.md"),
    ("08_storyboard.md", "08_storyboard_template.md"),
    ("09_image_prompts.md", "09_image_prompts_template.md"),
    ("10_manim_blueprint.md", "10_manim_blueprint_template.md"),
    ("11_rigor_audit.md", "11_rigor_audit_template.md"),
]

SLUG_RE = re.compile(r"^[a-z0-9_]+$")


def _slugify(raw: str) -> str:
    s = raw.strip().lower().replace("-", "_").replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"__+", "_", s).strip("_")
    return s


def _stamp_frontmatter(text: str, slug: str, title: str, today: str) -> str:
    """Replace the canonical placeholders in the template frontmatter."""
    text = text.replace("<topic>", slug)
    text = text.replace("<topic-slug>", slug)
    text = text.replace("<topic_tags>", slug)
    text = text.replace("<title>", title)
    text = text.replace("<YYYY-MM-DD>", today)
    text = text.replace("<model-id>", "claude-opus-4-7")
    return text


def scaffold(slug: str, title: str, vault: Path, force: bool) -> Path:
    if not SLUG_RE.match(slug):
        raise SystemExit(
            f"Invalid slug {slug!r}: must match {SLUG_RE.pattern} (ASCII snake_case)."
        )
    today = dt.date.today().isoformat()
    folder_name = f"{today}_{slug}"
    target = vault / "15_Reading_and_Learning" / "Video_Scripts" / folder_name

    if target.exists() and not force:
        print(f"[scaffold] Folder already exists: {target}")
        print("[scaffold] Pass --force to overwrite. No changes made.")
        return target
    if target.exists() and force:
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=False)

    written: list[str] = []
    for outfile, tmpl in PIPELINE_FILES:
        src = TEMPLATES / tmpl
        if not src.exists():
            raise SystemExit(f"Missing template: {src}")
        body = _stamp_frontmatter(src.read_text(), slug, title, today)
        # Flip status to scaffolded so validate_pipeline can find the file
        body = body.replace("status: draft", "status: scaffolded", 1)
        (target / outfile).write_text(body)
        written.append(outfile)

    print(f"[scaffold] Created {target}")
    for f in written:
        print(f"  + {f}")
    print(
        "\nNext step: read INDEX.md, then start filling 00_declaration.md. "
        "When the declaration is approved, proceed to 01_conceptual_blueprint.md."
    )
    return target


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("slug", help="ASCII snake_case slug for the topic")
    p.add_argument(
        "--title",
        default=None,
        help='Working title (defaults to a humanised version of the slug)',
    )
    p.add_argument(
        "--vault",
        default="/Users/omarkhalil/OmarOS",
        type=Path,
        help="Vault root (default: OmarOS)",
    )
    p.add_argument("--force", action="store_true", help="Overwrite if folder exists")
    args = p.parse_args()

    slug = _slugify(args.slug)
    title = args.title or slug.replace("_", " ").title()
    scaffold(slug, title, args.vault, args.force)


if __name__ == "__main__":
    main()
