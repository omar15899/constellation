---
name: scilux-lessons
description: Create, revise, render and prepare Scilux educational lessons while preserving their briefs, sources, phase artifacts, pedagogical requirements and independent delivery review.
---
# Scilux lessons

Read the [Scilux profile](../../../profiles/scilux.md), `config/context-registry.yaml` and `config/style-canon.yaml` in `/Users/omarkhalil/GitHub/Scilux`. They own the phase and quality contracts. Use native roles with inherited client settings; phase labels describe work and artifacts, not another agent runtime.

## Select and scope the lesson

Establish the lesson ID, requested outcome, audience, duration, languages, sources and affected phases/scenes/frames. Apply `naming.lesson_id_regex` from the current configuration. Reuse `inputs/briefs/_template.yaml` and `lessons/_template/` for new lessons without overwriting an existing lesson. Keep the lesson's `brief.yaml` mirror consistent with the selected brief.

Keep the requested or declared duration explicit rather than introducing another default. Topic, audience and usable sources must be grounded. Image inputs exist, but the current start gate counts papers, books, YouTube, narration and links; an image-only brief may leave that prerequisite unmet. Report the actual blocker instead of inventing a source or bypassing the gate.

## Follow artifact dependencies

| Phase | Responsibility | Principal artifacts |
| --- | --- | --- |
| P0 | Setup | `workspace/LESSON/manifest.json` |
| P1 | Source normalization | `workspace/LESSON/sources.json` |
| P2 | Audience and learning design | `workspace/LESSON/pedagogy/` |
| P3 | Knowledge and notation | Workspace `knowledge_base.json`, `notation_local.yaml`, `terminology.yaml`, `bibliography.bib` |
| P4 | Narrative structure | Workspace `story_blueprint.yaml`, `analogies.yaml`, `pacing_curve.json`, `emotional_arc.json` |
| P5 | Script | `lessons/LESSON/script/scenes/`, `full_script.md`, `narration_track.md` |
| P6 | Storyboard planning | `workspace/LESSON/storyboard_plan.yaml` |
| P7 | Visual artifacts | `lessons/LESSON/storyboard/{tikz,frames,png}/`, `manifest.yaml` |
| P8 | Independent review | `logs/LESSON/review_report.md` |
| P9 | Assembly and delivery | `lessons/LESSON/delivery/`, `companion.md`, `logs/LESSON/changelog.md` |

Read existing entry artifacts before a revision. Limit changes to the requested surface and affected dependants. Source additions reuse the applicable `inputs/` location or URL sidecar, update the brief and normalized source records, and mark affected downstream work in `logs/LESSON/staleness.md`. Audience changes use the selected `config/audience-profiles/AUDIENCE.yaml`. Preserve completed work and revision history.

The workspace manifest is an existing artifact; do not substitute an old playbook schema or invent a new schema for it. The storyboard template owns its `version`, `lesson_id`, `total_frames`, `duration_s` and `frames` fields. Preserve per-frame identity and links between TikZ source, frame sheet and render.

## Preserve teaching quality

Each learning objective needs a definition, example or claim beat; each misconception needs a counterexample or bridge; factual claims need source records. Definition beats combine formal structure, rigorous intuition and intellectual interpretation. Preserve declared notation, bilingual parity, accessibility and semantic colours. Each frame retains narration, on-screen text, motion intent and source.

Use structural analogies with explicit limits (`breaks_when`), precise speakable claims and visual arguments tied to the learning objective. Apply the owner's current style canon instead of universal word-count or formatting quotas.

## Validate and deliver within authorization

Declare applicable artifact gates in the task's `required_checks`. The profile lists the maintained start, ingestion, notation, timing, TikZ and release commands. Set `SCILUX_ROOT` and the exact `SCILUX_LESSON_ID`; verify actual artifact coverage rather than accepting an empty success or inference from the latest file.

Current independent review must be `PASS`, and applicable artifact gates must be satisfied before delivery. A historical waiver is not new approval. Create, change or run tests only when Omar explicitly requests them; report any unmet test-dependent gate without bypassing it.

Keep curated evidence and references, not raw prompts or conversations. Workspace/reference trees remain private. The coordinator handles authorized publication through Constellation; this method never stages, commits or pushes automatically.
