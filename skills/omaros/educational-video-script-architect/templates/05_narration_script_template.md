---
title: "Narration Script — <topic>"
note_type: video_narration_script
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, narration_script, <topic_tags>]
status: draft
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
priority: normal
confidence: high
author: <model-id>
ai_generated: true
ai_reviewed: false
parent: INDEX.md
---

# Narration Script — `<topic>`

The **central deliverable** of the production package. Second-by-second alignment between voice-over, on-screen events, notation, and production notes. Every other artefact resolves against this one.

The discipline of this file is the four pillars of `style/ultra_formal_intuitive_doctrine.md`. Every formal beat is preceded by a `[PREAMBLE]` block. Every English technical term is defined inline at first use. Every load-bearing definition is presented at three layers across this file and `01_conceptual_blueprint.md`. The cross-domain echo appears once, in the synthesis movement.

---

## §5.0 — Conceptual preamble

> *Plain-language statement of how to read this file. The script is a table; each row is an atomic visual event of 1–10 seconds. Tags drive everything else: voice direction, image generation, Manim implementation, rigor audit. Skip the preamble at your peril. ~80 words.*

---

## §5.1 — Reference contract

This script is binding. It references and is constrained by:

- `00_declaration.md` — pillars, single-sentence essence, paper citations.
- `01_conceptual_blueprint.md` — three-layer definitions, notation register, object-vs-representation discipline.
- `02_pedagogical_design.md` — synchronisation contract, retrieval/self-explanation prompts.
- `03_scene_architecture.md` — scene boundaries and conceptual moves.
- `04_visual_language.md` — colour semantics, motion vocabulary, on-screen treatment of tags.

If this script disagrees with any of those, this script is wrong. Update it.

---

## §5.2 — Tag legend

Tags appear in the **Tag** column. They drive downstream tooling.

| Tag | Meaning | Doctrine reference |
|---|---|---|
| `[HOOK]` | opening beat that creates intellectual pressure | scene architecture |
| `[PREAMBLE]` | conceptual preamble before a formal block (no notation) | Pillar I |
| `[FORMAL]` | formal definition, theorem, or precise statement | Pillar III layer 1 |
| `[INSTANCE]` | concrete worked instance of the prior `[FORMAL]` | Pillar III mandatory |
| `[BOUNDARY]` | counter-example or boundary case | Pillar III + rigor audit |
| `[CROSS_DOMAIN]` | the same structure in another domain | Pillar IV |
| `[RETRIEVAL]` | retrieval prompt + screen freeze | pedagogical §2.6.1 |
| `[SELF_EXPLAIN]` | self-explanation prompt | pedagogical §2.6.2 |
| `[ESSENCE]` | the single-sentence essence voiced verbatim | Master simplification |
| `[TRANSITION]` | inter-scene bridge | scene architecture §3.2 |
| `[INFORMAL]` | metaphor / analogy block, formally unrigorous by design | rigor audit |
| `[OBJECT_VS_REP]` | beat that visibly distinguishes object from representation | blueprint §1.5 |

Every row carries exactly one tag (the dominant one). A row that would carry two is two rows.

---

## §5.3 — Master script table

### Granularity rules

| Video length | Row duration |
|---|---|
| ≤ 2 min | 1–3 s |
| 3–10 min | 3–8 s, finer at dense moments |
| > 10 min | 5–10 s, finer at dense moments |

Voice-over text is the **literal** narration recorded or sent to TTS. No stage directions inside quotes. Every English technical term defined inline at first use: `<term> — that is, <8–15 word working definition>`.

### Animation richness mandate

**The "On-screen" column must describe what is changing continuously, not what is appearing.** Every row for a mathematical or conceptual beat must use at least one Layer 2–4 verb from `04_visual_language.md §4.5`. Writing "object appears" or "diagram fades in" for a conceptual row is a specification failure. Specify: (1) what object is present, (2) what parameter or quantity is driving continuous change, (3) the visual outcome of that change.

Even during a `[PREAMBLE]` row — where notation is forbidden — a metaphor visual must still have something continuously moving, growing, or evolving. The moment the viewer sees motion, they are engaged. The moment they see a static frame appear, they are watching slides.

The banned phrasings from `style/visual_creativity_protocol.md §5` apply to this column: "the formula appears", "show the definition", "introduce concept X", "the slide shows…", "we see that…", "an animation showing the relationship", and similar slide-paradigm verbs. If any of these appear in your row, re-brainstorm before writing.

### Pre-scene brainstorm trace (mandatory)

For each major scene, the Visual Imagination Brainstorm from `style/visual_creativity_protocol.md §1` has already produced a winning candidate (the trace lives in `03_scene_architecture.md`). When writing rows here, the chosen candidate must be visible — not generic phrasing. If you find the rows of two different scenes could be swapped without losing meaning, the brainstorm has failed: each scene must have its own visual identity.

### Example rows

These examples show the expected level of animation specificity. Your rows should be at least this specific.

| ID | Time | Tag | Scene | Voice-over (literal) | On-screen (atomic visual event — specify what changes continuously) | Notation | Visual verb (§4.5) | Manim cue | Asset cue | Production note |
|---|---|---|---|---|---|---|---|---|---|---|
| R001 | 0:00–0:04 | `[HOOK]` | S1 | "<…>" | title writes letter by letter from left; simultaneously a teal parametric curve traces itself below the title, left to right, 3 s | `<title text>` | write + parametric-trace | `Write(title, run_time=2)`; `TracedPath(param_fn, t_range=[0,1], run_time=3)` | — | hold 1 s after curve completes |
| R002 | 0:04–0:12 | `[PREAMBLE]` | S1 | "<metaphor — no notation, no formal term>" | 200 amber dots scatter uniformly across canvas, then drift under a slow attractor flow and coagulate into a dense cluster at centre — density visible via colour shift uniform-amber → saturated-teal | none | scatter-coagulate + field-evolve | N=200 `Dot` objects; `ValueTracker(t)` driving position updater toward Gaussian target; colour interpolation on density | I001 | no symbols in preamble |
| R003 | 0:12–0:20 | `[INFORMAL]` | S1 | "<intuitive bridge sentence>" | coordinate plane stretches nonlinearly as parameter p grows from 0 to 1: grid lines bow inward toward attractor, gridlines remain visible throughout | none | space-deform | `NumberPlane` with `ApplyFunction(f_p)` animated by `ValueTracker(p)` from p=0 to p=1 | — | do not freeze at any p |
| R004 | 0:20–0:28 | `[FORMAL]` | S2 | "We define `<term>` — that is, `<8–15 word working definition>`. Precisely: `<formal statement>`." | formal definition writes in white; simultaneously the attractor object from S1 morphs from dot-cloud to clean geometric form (e.g. ellipse), held in right half while definition occupies left | `<formal symbol>` | write + morph | `Write(MathTex(...), run_time=1.5)` on left; `Transform(dot_cloud, ellipse_obj)` on right, synchronized | I004 | 1.5 s pause after definition; definition stays in corner for subsequent rows |
| R005 | 0:28–0:38 | `[INSTANCE]` | S2 | "<concrete instance>" | specific numerical instance: axes appear, a curve traces itself, measurement arrow grows to show the relevant quantity, label animates to show value | `<…>` | construction-live + measurement-grow | `Create(axes)`; `ParametricFunction(f, t_range=...)` drawn; `GrowArrow(meas_arrow)`; `Write(label)` in sequence | — | definition in corner throughout |
| R006 | 0:38–0:44 | `[RETRIEVAL]` | S2 | "Before continuing — what breaks if we remove condition X?" | screen dims to 20% except the condition term in the definition (teal glow); 4 s hold | — | highlight | `FadeToColor(bg, DARK_GREY)`; `Indicate(condition_term, scale_factor=1.3)` | — | 4 s hold; voice stops |
| R007 | 0:44–0:52 | `[SELF_EXPLAIN]` | S2 | "Notice the structure: `<claim>`. Why does this force the conclusion?" | all elements dim except the key structure; arrow grows from premise to conclusion; 3 s hold | — | arrow-grow + highlight | `FadeOut(other_elems, opacity=0.2)`; `GrowArrow(implication_arrow)` | — | 3 s hold |
| R008 | 0:52–1:02 | `[BOUNDARY]` | S3 | "Without `<condition>`, the structure collapses. Concretely: `<counter-example>`." | the ellipse from S2 continuously deforms as p drops below threshold — surface pinches, develops a cusp, finally collapses to a lower-dimensional object; all in crimson tint | `<…>` | parameter-sweep + space-deform | `ValueTracker(p)` from p_threshold to p_degenerate; `always_redraw` on surface object; colour `RED_C` | I008 | show the collapse, not just the end state |
| R009 | 1:02–1:12 | `[OBJECT_VS_REP]` | S3 | "<sentence: 'the object is not its coordinates'>" | coordinate grid around the object rotates (new basis), labels change — but the teal object at centre holds completely still; the object's colour never changes, the grid's colour shifts | `<…>` | coordinate-change + fade-to-invariant | `Transform(axes_old, axes_new)` + `ReplacementTransform(labels)`; teal `Surface` has no transform — it does not move | — | hold 2 s at end to let distinction land |
| R010 | 1:12–1:25 | `[CROSS_DOMAIN]` | S4 | "<bridge: 'the same structure appears in domain Y'>" | split-screen: left panel holds the original object animating; right panel fades in with domain-Y version animated in parallel — same structural motion, different labels; correspondence arrows grow between panel pair | `<…>` | split-screen + comparison-animate | `VGroup` split layout; both panels animate in sync; `GrowArrow(correspondence_arrow_1)` etc. | I010 | per Doctrine Pillar IV |
| R011 | 1:25–1:32 | `[ESSENCE]` | S5 | "<single-sentence essence — verbatim from 00_declaration.md §0.1>" | all elements fade except the central teal object; it slowly rotates or pulses once, then holds; essence sentence writes below it | `<…>` | fade-out + parametric-trace or rotation-3d | `FadeOut(all_except_central)`; `Rotating(central, angle=PI/6)`; `Write(essence_tex)` | — | this is the apex; 2 s silence after |
| R012 | 1:32–1:38 | `[TRANSITION]` | S5 | "<closing sentence>" | essence object dissolves into the next-scene seed or fades to black; no hard cut | — | fade-out or morph | — | — | 1 s pause |

Replace these rows with the actual rows for your topic. Delete this example block from the delivered file.

**Discipline checklist for the table itself:**

- Every `[FORMAL]` row is preceded by a `[PREAMBLE]` row in the same scene.
- Every English technical term used in a voice-over column carries an inline definition on its first occurrence anywhere in the table.
- Every load-bearing definition has at least one `[INSTANCE]` row after it.
- The `[ESSENCE]` row appears exactly once, in the synthesis scene.
- The `[CROSS_DOMAIN]` row appears at least once.
- Row IDs `R001..` are stable; do not renumber on edits, append.
- Asset cues `I001..` correspond to frames in `08_storyboard.md`. Manim cues correspond to scene/object identifiers in `10_manim_blueprint.md`.

---

## §5.4 — Inline-definition register

Track every English technical term with its first-use row and its working definition. The validator script reads this section.

| Term | First-use row | Working definition (8–15 words) |
|---|---|---|
| `<scheduler>` | R0xx | "<def>" |
| `<placeholder>` | R0xx | "<def>" |
| … | … | … |

A term in voice-over without a row in this table is a Pillar II violation.

---

## §5.5 — Three-layer presence map

Confirm that every load-bearing definition appears at all three layers across this file and `01_conceptual_blueprint.md`.

| Concept | Layer 1 (fundamental) | Layer 2 (rigorous intuition) | Layer 3 (personal vision) | `[INSTANCE]` row |
|---|---|---|---|---|
| `<concept>` | R0xx (`[FORMAL]`) | `01_conceptual_blueprint.md` §1.1.2 | R0xx (`[CROSS_DOMAIN]` or `[ESSENCE]`) | R0xx |

A row missing here is a Pillar III violation.

---

## §5.6 — Pacing and word-count audit

Estimated narration speed: 150 words per minute (English) or 145 wpm (Spanish). Adjust per voice register declared in `00_declaration.md`.

| Scene | Duration | Voice-over word count | Estimated speech time | Slack (= duration − speech) |
|---|---|---|---|---|
| S1 | 0:30 | `<n>` | `<m>` | `<delta>` |
| S2 | 1:00 | `<n>` | `<m>` | `<delta>` |
| … | … | … | … | … |

Slack must be positive. Negative slack means the narration is over-stuffed and a row must be split or compressed.

---

## §5.7 — Script freeze gate

- [ ] Every formal beat preceded by a `[PREAMBLE]` row.
- [ ] Every English technical term defined inline at first use, recorded in §5.4.
- [ ] The `[ESSENCE]` row appears exactly once and matches `00_declaration.md` §0.1 verbatim.
- [ ] The `[CROSS_DOMAIN]` row appears at least once and corresponds to the bridge in `00_declaration.md` §0.4.4.
- [ ] At least one `[RETRIEVAL]` per major scene.
- [ ] At least one `[SELF_EXPLAIN]` per non-obvious move.
- [ ] No row tagged both `[FORMAL]` and `[INFORMAL]`.
- [ ] Every row's notation column is consistent with `01_conceptual_blueprint.md` §1.4.
- [ ] Pacing slack is non-negative for every scene.
