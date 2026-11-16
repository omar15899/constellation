---
title: "<Title> — Render Validation Rubric"
note_type: video_render_validation_rubric
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
slug: <topic-slug>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
status: draft
production_track: true
---

# Render Validation Rubric — `<topic>`

The pass/fail rubric the `render_review_agent` applies to every finished shot, against its declared animation spec. **A render can fail even if the code runs.** The quality bar is not "the code renders." The quality bar is *"the animation communicates the intended idea with precision, elegance, and inevitability."*

The rubric has five axes. Every axis is binary at the shot level (pass / fail); the overall shot passes only if **all five** axes pass.

A per-shot validation report lives at `manim/render_tests/validation_scene_<NN>_shot_<id>.md` and uses the same five-axis structure as this rubric.

---

## Axis 1 — Pedagogical validation

For each shot, the reviewer answers:

- **Q1.1** Does the shot advance the intended cognitive transformation declared in `cognitive_goal`?
- **Q1.2** Does it reduce or increase cognitive load relative to what the viewer is holding?
- **Q1.3** Does it address the relevant misconception (if `pedagogical_function` includes `refute_misconception`)?
- **Q1.4** Does it preserve the worked-example structure (if part of a worked-example chain)?
- **Q1.5** Does it support retrieval / self-explanation when the spec calls for it (during a declared retrieval pause)?

Axis 1 passes if every applicable question is "yes". A "no" on any applicable question fails the axis. Inapplicable questions (e.g., Q1.3 in a shot whose pedagogical function is `hook`) do not contribute.

---

## Axis 2 — Cinematic validation

- **Q2.1** Is there one dominant focal point? (The eye must know where to land first.)
- **Q2.2** Is the composition balanced — either symmetric or deliberately asymmetric per the declared `composition.balance`?
- **Q2.3** Is there depth and layering — multiple z-indexes used, the foreground not fighting the background?
- **Q2.4** Is the motion meaningful — every transition mapped to a semantic in the motion vocabulary (`production_track/doctrine/04_semantic_motion.md`)?
- **Q2.5** Is the frame readable when frozen (the **frozen-frame test**, per `production_track/doctrine/08_frozen_frame_and_muted_tests.md`)?
- **Q2.6** Does the shot feel intentional rather than generic — does it pass the anti-aesthetics filter (`production_track/doctrine/11_anti_aesthetics.md`)?

Axis 2 passes if all six are "yes". The frozen-frame test (Q2.5) is the single most discriminating question — a failure here is almost always a spec defect, not an implementation defect.

---

## Axis 3 — Semantic validation

- **Q3.1** Are all colours semantically correct (palette token + correct object kind, per `production_track/doctrine/03_semantic_visual_language.md`)?
- **Q3.2** Are all arrows meaningful — every arrow represents a real flow, force, transformation, or dependency?
- **Q3.3** Are all labels attached to the right objects — no label is floating, no object is unlabelled when it should be labelled?
- **Q3.4** Are formulas linked to visual referents per `production_track/doctrine/12_formula_doctrine.md` — assembled, morphed, or colour-matched?
- **Q3.5** Are metaphors consistent with the registered catalogue in the conceptual blueprint and `production_track/doctrine/07_registered_metaphors.md`?
- **Q3.6** Does the persistent-object ledger hold — every persistent object has the same identity (shape, semantic colour, component) as in earlier shots, modulo declared morph rules?

Axis 3 passes if all six are "yes". A single non-palette colour or a single unregistered metaphor fails the axis.

---

## Axis 4 — Technical validation

- **Q4.1** Are all objects named? (No anonymous `Rectangle(...)` in the scene code.)
- **Q4.2** Are timings explicit? (Every `play()` has an explicit `run_time`; every `wait()` has an explicit duration; defaults come from `manim/constants.py`, not from Manim's library defaults.)
- **Q4.3** Are z-indexes defined? (Every object has an explicit `z_index` or has been added in an order whose stacking is documented.)
- **Q4.4** Are reusable components used? (If `SplitFlapBoard` exists, the shot does not draw a board from `Rectangle` + `Text`.)
- **Q4.5** Are fonts and sizes specified? (No font defaults; everything is a `FONT_TOKEN`.)
- **Q4.6** Are there no unexplained magic constants? (Every `0.85`, `BLUE`, `0.3` is named in `constants.py` or in `10b_data_manifest.yaml`.)
- **Q4.7** Does the animation match the voice-over within the declared tolerance (per `production_track/doctrine/09_synchronization.md`)?

Axis 4 passes if all seven are "yes".

---

## Axis 5 — Manim implementation validation

- **Q5.1** Is the code modular? (Scene `construct()` is a sequence of named methods, not a flat list of `play()` calls — see `production_track/doctrine/02_canonical_pipeline.md` §"Scene file structure".)
- **Q5.2** Are components reusable? (Each component constructor takes semantic parameters; no scene-specific hard-coding inside the component.)
- **Q5.3** Are `ValueTracker`s used for changing numerical values? (Discrete `Transform` from N to M is rejected for a continuously varying quantity.)
- **Q5.4** Are transformations robust? (`TransformMatchingTex` is used for evolving formulas; `ReplacementTransform` for true replacements; not blanket `Transform`.)
- **Q5.5** Is the scene renderable without manual intervention? (Re-running the render produces the same output. No environment-dependent assets are loaded.)
- **Q5.6** Are imports clean? (Imports come from `manim/constants.py`, `manim/components/*`, and the Manim library only. No ad-hoc copies of palette / font tokens.)
- **Q5.7** Are configuration constants centralized? (Palette, fonts, durations, layouts all imported, never inline.)
- **Q5.8** Are object names meaningful? (`board_left`, `basis_ticker` — not `rect1`, `text2`.)

Axis 5 passes if all eight are "yes".

---

## Per-shot validation report format

Each shot's report follows this shape and lives at `manim/render_tests/validation_scene_<NN>_shot_<id>.md`:

```markdown
# Validation — shot <shot_id>

Render path: <path/to/rendered.mp4>
Spec path:   09_animation_spec.yaml#<shot_id>
Reviewed by: render_review_agent
Reviewed at: <timestamp>

## Pedagogical
- Q1.1: pass / fail / n/a — <evidence>
- Q1.2: …
…

## Cinematic
…

## Semantic
…

## Technical
…

## Manim
…

## Overall
- Pedagogical:  pass / fail
- Cinematic:    pass / fail
- Semantic:     pass / fail
- Technical:    pass / fail
- Manim:        pass / fail
- **Shot:       pass / fail**

## Findings & required revisions
- <list of specific revisions, ordered by axis>

## Notes for the visual director (if the failure is at the spec layer)
- <list>
```

## How the rubric is used during production

- The animation_spec_agent reads the rubric and structures the spec to make each axis answerable.
- The component_architect ensures Q4.4 and Q5.2 are answerable by providing the right components.
- The manim_implementation_agent reads the rubric before writing the scene file and self-checks against the technical and Manim axes before declaring the render complete.
- The render_review_agent runs the full rubric against every rendered shot, writes the per-shot report, and either marks the shot `approved` or returns it for revision.

A shot that passes all five axes is `approved`. A shot that passes four and fails one is sent back to the relevant agent (e.g., a Semantic failure goes back to the animation_spec_agent or the visual director; a Manim failure goes back to the manim_implementation_agent). A shot that fails two or more axes is sent back to the visual director — the spec is probably under-specified or contradictory.
