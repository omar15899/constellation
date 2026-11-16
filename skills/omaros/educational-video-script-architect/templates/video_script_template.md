# Video Script Template

The complete output scaffold. Copy this structure and fill every section. Do not omit headings; if a section is genuinely not applicable, leave the heading and write one sentence saying so.

---

# Educational Video Script — `<topic>`

## 1. Production brief

- **Topic:**
- **Audience level:** absolute beginner | undergraduate | advanced UG / master's | research / expert | mixed
- **Intended duration:** `<MM:SS>` (range acceptable)
- **Educational objective:** one sentence — what must the viewer be able to do or see after watching?
- **Core conceptual promise:** one sentence — what insight does this video deliver that the viewer probably did not have?
- **Prerequisites:** bullet list, minimal and honest
- **Chosen explanatory structure:** canonical 10-step | proof-oriented | computational | physics-oriented | finance-oriented | geometry-oriented | custom
- **Reason for choosing that structure:** one paragraph
- **Production modality:** Manim | generative video | motion graphics | Blender / 3D | live coding | slides | hybrid (specify)
- **Visual style:** see §5
- **Tone of voice:** precise, elegant, curious | austere, formal | warm, professorial | other
- **Main mathematical or conceptual objects:** bullet list
- **Expected emotional/intellectual arc:** one paragraph — opens with X (curiosity / tension / surprise), passes through Y (struggle / clarity), closes with Z (recognition / inevitability)

## 2. Conceptual abstract

A dense intellectual blueprint, not marketing copy. Address each:

- What is the central concept?
- Why is it difficult? Where do learners typically get stuck?
- What misconception (if any) will the video dissolve?
- What visual metaphor or construction is the central pedagogical engine?
- What will the viewer understand by the end that they probably did not before?
- Where does rigor enter?
- Where do examples enter?
- Where does abstraction enter?

## 3. Pedagogical design notes

- Audience-level assumptions (concrete: which prerequisites, which symbols, which prior concepts)
- Likely misconceptions and how the script addresses them
- Example-selection rationale — why these examples, in this order
- Pedagogy mode: example-first | definition-first | proof-first | problem-first | phenomenon-first
- Cognitive-load control strategy (chunking, redundancy, signaling, segmenting)
- Narration↔visual synchronization strategy
- Where the explanation moves from intuition to formalism
- Which learning-research principles influenced the design (cite briefly only if the `learning_research/` folder is populated)

## 4. Explanatory architecture

| # | Scene | Duration | Purpose | Conceptual role | Visual strategy | Main screen objects | Modality | Transition out |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | … | 0:00–0:20 | … | motivation | … | … | Manim | morph grid into chart |
| 2 | … | 0:20–1:05 | … | informal intuition | … | … | Manim | fade in formal definition |
| … | … | … | … | … | … | … | … | … |

The breakdown is **pedagogical**, not topical: each scene corresponds to a distinct conceptual function (motivate / show / define / exemplify / abstract / return / synthesize), not merely to a different sub-topic.

## 5. Visual language specification

- **Background:** style, colour, texture, depth
- **Colour palette:** list each colour with its semantic role (e.g., teal = invariant object, amber = chosen representation, magenta = approximation error, white = formal definition)
- **Typography:** body font, mathematical font (e.g., Computer Modern via MathTeX in Manim), weight conventions
- **Mathematical notation style:** LaTeX baseline; convention for indices, vectors, operators, sets, spaces, measures
- **Definitions appear as:** specify (e.g., framed white box, fade-in left, accompanied by a 1.5 s pause)
- **Examples appear as:** specify (e.g., diagrammatic, with the formal definition kept visible in a corner)
- **Transformations animated as:** morphisms with continuous interpolation; never cut-and-replace
- **How the video represents each:**
  - uncertainty → soft glow / probability cloud / opacity
  - abstraction → fading representation, invariant object remains
  - causality / dependence → directional arrows growing in real time
  - hierarchy → nested containers / depth
  - equivalence → reversible morphism (double-headed arrow)
  - invariance → representation changes, object holds still
  - locality → zoom-in on a patch
  - globality → zoom-out from patches to a whole
  - approximation → coarse object refining toward a target
  - structure → shared colour / shared layout across sibling examples
- **Camera behaviour:** static frame by default; slow pushes for emphasis; zooms reserved for local-to-global moments
- **Use of:** pauses (1–2 s after each definition), zooms, fades, highlights, arrows, overlays, morphs, depth, parallax, object permanence

## 6. Second-by-second script

Use this exact column structure. Add rows as needed; keep one row per atomic visual event.

| Time | Voice-over (exact) | Screen / animation | Notation | Production notes | Manim notes | Generative-video notes | Asset prompts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0:00–0:03 | "…" | dark background; title fades in over 1 s | `<title text>` | hold on title 2 s | `Text("…").scale(1.2)`, `FadeIn(run_time=1)` | n/a | — |
| 0:03–0:08 | "…" | … | … | … | … | … | … |

Granularity rules:
- Short videos (≤2 min): 1–3 s rows.
- Standard (3–10 min): 3–8 s rows; finer for dense moments.
- Long (>10 min): 5–10 s rows; finer for dense moments.
- Voice-over column contains the literal narration. No stage directions inside the quotes.

## 7. Production implementation blueprint

Adapt to chosen modality. Use the relevant template files:

- **Manim segments:** see `templates/manim_blueprint_template.md`
- **Generative video segments:** see `templates/generative_video_prompt_template.md`
- **Motion-graphics / hybrid:** see `templates/production_blueprint_template.md`

Cover (for each modality used):

- Scene/clip list with timestamps
- Asset inventory (objects, equations, plots, reference images, generated clips)
- Reusable helper functions / components
- Camera / shot list
- Layer structure (for motion graphics)
- Compositing notes (when modalities are mixed)
- Performance considerations (long Manim renders, expensive 3D)

Do **not** produce full code unless the user asks for it.

## 8. Storyboard and image/video-generation prompts

Use `templates/storyboard_prompt_template.md`. Each prompt:

- ID (e.g., `S2-F3` for Scene 2, Frame 3; `S3-C1` for Scene 3, Clip 1)
- Timestamp / scene reference
- Purpose
- Prompt body
- Negative prompt / constraints
- Reference-only vs production-asset

Group prompts by scene.

## 9. Voice-over-only version

A clean narration block, no markdown remnants, no scene labels, no stage directions. What the voice actor or TTS engine reads, end to end. Use plain paragraphs separated by blank lines. Reading time should match the intended duration ± 5%.

## 10. Mathematical and conceptual rigor audit

Run through `checklists/mathematical_accuracy_checklist.md`. Report each item: PASS / NOTE / FAIL with a short explanation.

For advanced topics, label informal sections with **[INFORMAL]** and formal sections with **[FORMAL]**. Confirm that no [INFORMAL] segment is presented as if it were [FORMAL].

## 11. Quality-control checklist

Run through:
- `checklists/pedagogical_quality_checklist.md`
- `checklists/visual_quality_checklist.md`
- `checklists/production_readiness_checklist.md`

For each: PASS / NOTE / FAIL, with a short explanation. Fix any FAILs before delivery; report any NOTEs.

## 12. Optional variants

Only include variants the user would plausibly want. Each variant: one short paragraph describing what changes (duration, audience, modality, depth).
