---
title: "Video Pipeline Index — <topic>"
note_type: video_pipeline_index
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, pipeline_index, <topic_tags>]
status: draft
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
priority: normal
confidence: high
author: <model-id>
ai_generated: true
ai_reviewed: false
pipeline_version: 2.0
---

# Video Pipeline Index — `<topic>`

This is the master navigation file for the production package. The 13 artefacts below are the complete deliverable; each one specialises in a single concern. Read in order — file `00` is the declarative justificatory document and must be consumed before any technical artefact.

## Pipeline contract

| # | Artefact | Concern | Status | Read order | Consumer |
|---|---|---|:---:|:---:|---|
| — | `INDEX.md` | Navigation + status | ☐ | 1 | Human, agent |
| 00 | `00_declaration.md` | What / How / Why + paper citations + main pillars | ☐ | 2 | Human (read first) |
| 01 | `01_conceptual_blueprint.md` | Three-layer definitions + cross-domain unification | ☐ | 3 | Designer agent |
| 02 | `02_pedagogical_design.md` | Learning principles applied + audience analysis | ☐ | 4 | Designer agent |
| 03 | `03_scene_architecture.md` | Scene-by-scene conceptual decomposition | ☐ | 5 | Director agent |
| 04 | `04_visual_language.md` | Visual grammar, palette, typography, motion vocabulary | ☐ | 6 | Visual designer |
| 05 | `05_narration_script.md` | Second-by-second master script (central deliverable) | ☐ | 7 | Director, Manim dev |
| 06 | `06_voiceover.md` | Clean TTS-ready voice-over | ☐ | 8 | Voice actor / TTS |
| 07 | `07_voice_direction.md` | Tone, pacing, emotion direction per segment | ☐ | 9 | Voice actor / TTS |
| 08 | `08_storyboard.md` | Frame-by-frame visual storyboard | ☐ | 10 | Visual designer |
| 09 | `09_image_prompts.md` | DALL-E / ChatGPT image prompts | ☐ | 11 | Image generator |
| 10 | `10_manim_blueprint.md` | Manim implementation blueprint | ☐ | 12 | Manim developer |
| 11 | `11_rigor_audit.md` | [FORMAL]/[INFORMAL] tagging + checklist results | ☐ | 13 | Reviewer agent |

Mark each box ☑ as the corresponding file is completed and validated. The file `scripts/validate_pipeline.py` checks completeness mechanically.

## Topic-level metadata

- **Topic slug:** `<topic-slug>`
- **Working title:** `<title>`
- **Audience tier:** absolute_beginner | undergraduate | advanced_ug | research_expert | mixed
- **Target duration:** `<MM:SS>`
- **Production modality:** manim | manim+motion | manim+generative | 3d_blender | hybrid
- **Pedagogical mode:** problem_first | phenomenon_first | example_first | definition_first | proof_first
- **Cross-domain bridge:** `<which canonical bridge from doctrine Pillar IV>`

## Single-sentence essence

> `<the one-sentence essence statement of the concept the video teaches; max 25 words; must match §The single-sentence essence in 00_declaration.md verbatim>`

## Run log

| Phase | Started | Completed | Notes |
|---|---|---|---|
| A — Capture intent | | | |
| B — Consult operational memory | | | |
| C — Choose architecture | | | |
| D — Design visual language | | | |
| E — Write declaration (file 00) | | | |
| F — Write conceptual blueprint (file 01) | | | |
| G — Write pedagogical design (file 02) | | | |
| H — Write scene architecture (file 03) | | | |
| I — Write visual language (file 04) | | | |
| J — Write narration script (file 05) | | | |
| K — Derive voiceover (file 06) | | | |
| L — Write voice direction (file 07) | | | |
| M — Write storyboard (file 08) | | | |
| N — Write image prompts (file 09) | | | |
| O — Write Manim blueprint (file 10) | | | |
| P — Run rigor audit (file 11) | | | |
| Q — Run validate_pipeline.py | | | |
| R — Commit | | | |

## Open invariants

- [ ] Doctrine Pillar I — every formal beat preceded by `[PREAMBLE]` in file 05.
- [ ] Doctrine Pillar II — every English technical term defined inline at first use in files 05 and 06.
- [ ] Doctrine Pillar III — every load-bearing definition presented at three layers across files 01 + 05.
- [ ] Doctrine Pillar IV — at least one cross-domain echo in files 01 and 05.
- [ ] Master simplification — single-sentence essence appears verbatim in files 00, 05 and INDEX.
- [ ] Rigor constraint — no `[INFORMAL]` segment carries the rhetorical weight of a `[FORMAL]` one.

## Cross-references out

- Source vault reference at `05_Projects/OmarOS/` in the local vault
- Knowledge base entry (if applicable): `<path>`
- Reflexiones LaTeX chapter (if applicable): `<path>`
- Related research notes (if applicable): `<paths>`
