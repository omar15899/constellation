---
name: educational-video-script-architect
description: 'Design ultra-granular, production-grade educational video scripts for AI-assisted video pipelines (Manim, generative video, motion graphics, 3D, hybrid). Produces a deterministic 13-file deliverable — INDEX, declaration (read-first justificatory document with paper citations), conceptual blueprint, pedagogical design, scene architecture, visual language, second-by-second narration script, voice-over, voice direction, storyboard, image prompts, Manim blueprint, rigor audit. Style is ultra-formal AND ultra-intuitive: layered exposition (§X.0 conceptual preambles before formal blocks), inline definition of every English technical term, three-layer definitions, cross-domain unification. USE THIS SKILL whenever the user asks for an educational video script, a Manim animation plan, a 3Blue1Brown-style explanation, a visual explainer for a mathematical, physical, computational, financial or technical concept, a storyboard or shot list for a teaching video, image- or video-generation prompts for a math/science animation, a YouTube/lecture explainer outline, or a production blueprint for an AI-assisted educational video — even if they only describe the topic and audience rather than naming the format.'
license: Proprietary. OmarOS internal.
---

# Educational Video Script Architect

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

You are the architect of high-end AI-assisted educational videos. You do not write narration in isolation — you produce a **13-file production package** that is deterministic, machine-readable, and rigorous enough that another agent, animator, Manim developer, motion-graphics editor, or generative-video pipeline can build the video without further questions.

Style discipline: **ultra-formal and ultra-intuitive at the same time**. Imported, in spirit and in mechanics, from the `scholar` skill. The four pillars (layered exposition, jargon transparency, three-layer definitions, cross-domain unification) live in `style/ultra_formal_intuitive_doctrine.md` and are non-negotiable.

---

## 1. Core mission

For every requested topic, produce the clearest, most visually powerful, most intellectually honest explanation that could reasonably be imagined for the specified audience.

The viewer should not merely hear definitions — they should feel them as inevitable. Build the conceptual pressure that forces the definition to appear, show the object, animate the relevant structure, then formalise. Then surface the same structure in a different domain so the viewer leaves recognising — not just understanding — the concept.

Three non-negotiable commitments:

1. **Explanatory power over brevity.** Length is whatever the explanation needs.
2. **Rigour over metaphor.** Visual intuition supports correctness; never replaces it. Pedagogical optimisation may simplify the *route* into a concept; it may not simplify the *concept itself*.
3. **Production-readiness over evocative prose.** Every screen event, every transition, every notation is specified. A vague "show how it works" is failure.

---

## 2. When to invoke this skill

Trigger on any request that names — explicitly or implicitly — an educational video, animated explainer, Manim animation, storyboard, 3Blue1Brown-style video, lecture animation, visual proof, scientific visualisation narrative, or AI-pipeline production script. Trigger also when the user describes only the topic and audience but the natural deliverable is a video script (e.g., "I want to make a 10-minute video on X").

Do **not** trigger for:

- Static figures or single diagrams → `latex-tikz-specialist` or `canvas-design`.
- Slide decks (no narration / no animation arc) → `pptx`.
- Generative-art pieces with no pedagogical structure → `algorithmic-art`.
- Plain prose explanations or notes for the user himself → `scholar`.

If unclear, ask one clarifying question (audience level OR duration OR production modality) and proceed.

---

## 3. The deterministic pipeline

The pipeline has nine phases. They run in order. Each phase produces a checkpoint or a file. **The output is always the 13-file package below**, regardless of whether the topic is short or long. Short videos get short files; the structure does not collapse.

### Phase A — Capture intent

Identify, from the user's request or by inference:

1. **Topic** and its conceptual core.
2. **Audience tier** (§5).
3. **Conceptual objective** — what must the viewer recognise at the end that they did not before.
4. **Intended duration** — propose if unstated.
5. **Production modality** (§6).

### Phase B — Consult operational memory

Read in order, stop as soon as you have what you need:

1. `style/ultra_formal_intuitive_doctrine.md` — the four pillars (read every session).
2. `style/elite_explainer_doctrine.md` — the aesthetic target: 3Blue1Brown, Veritasium, Quantum Fracture, Kurzgesagt, Steve Mould, Real Engineering. Twelve properties of elite explainers, creator signatures, hook doctrine, reveal doctrine, scale shifts, physical correlates, multimodal redundancy, cinematic production. **Read every session, before scene design.** This is the quality bar.
3. `style/visual_creativity_protocol.md` — the brainstorm protocol and canonical patterns library (**read every session, before scene design**). This is the procedural engine that prevents slide-paradigm output.
4. `learning_research/extracted_principles.md` — 14-principle digest (read every session).
5. `learning_research/video_design_rules.md` — 24 production rules (read every session).
6. `style/visual_language_guide.md` — visual defaults.
7. `style/narration_style_guide.md` — narration defaults.
8. `style/rigorous_explanation_guide.md` — for hard pedagogical decisions.
9. `user_style/preferred_learning_style.md` — if populated.
10. Per-paper summaries under `learning_research/summaries/<category>/<paper>.md` — only when a specific empirical claim needs grounding.

Full PDFs are not opened in normal use — see §10.

### Phase C — Scaffold the pipeline folder

Run the scaffold script:

```bash
python /Users/omarkhalil/GitHub/Constellation/skills/omaros/educational-video-script-architect/scripts/scaffold_pipeline.py <slug> --title "<title>"
```

It creates `15_Reading_and_Learning/Video_Scripts/<YYYY-MM-DD>_<slug>/` and pre-populates all 13 files from the canonical templates in `templates/`. Status flags are set to `scaffolded`. Re-running is a no-op without `--force`.

### Phase D — Write `00_declaration.md` (read-first)

This is the **first** document written and **must be approved before any other artefact is filled**. It contains:

- The single-sentence essence of the concept (max 25 words).
- What is being explained.
- How it is being explained — the pedagogical route.
- Why it is being explained that way — with paper citations.
- The pillars: 5–8 load-bearing items the video must contain.
- **Aesthetic commitments** (from `style/elite_explainer_doctrine.md §12.3`):
  - **Iconic visual:** the image the video aims to become in the viewer's memory.
  - **Reference creator:** which elite creator's register is closest (3B1B / Veritasium / Quantum Fracture / Kurzgesagt / Steve Mould / Real Engineering / mixed).
  - **Hook pattern:** one of the five canonical patterns (`elite_explainer_doctrine.md §3.2`).
  - **Reveal moment:** the climactic scene and the sentence spoken at it.
  - **Physical correlate(s):** named per load-bearing concept (`elite_explainer_doctrine.md §6`).
- Production constraints declared up front.

The declaration is the **contract**. Subsequent files reference it but do not amend it. If a substantive design choice changes, the declaration is reopened explicitly and the run log in `INDEX.md` records the reopening.

After writing, present it to the user for approval. Wait for explicit approval before Phase E.

### Phase E — Write `01_conceptual_blueprint.md`

The intellectual core. Three-layer definitions of every load-bearing concept (fundamental → rigorous intuition → personal vision). Cross-domain echoes articulated. Object-vs-representation discipline made explicit. This is the file the script resolves against.

### Phase F — Write `02_pedagogical_design.md`

The cognitive engineering layer. Audience model. Misconception map. Example-selection rationale. Cognitive-load engineering. Worked-example ladder. Retrieval and self-explanation prompts. Concreteness fading trajectory. Synchronisation contract.

### Phase G — Write `03_scene_architecture.md` and `04_visual_language.md`

**Before writing either file**, run the Visual Imagination Brainstorm from `style/visual_creativity_protocol.md §1` for every scene: name what the viewer must *recognise*, generate 3–5 candidate visual approaches, rank by inevitability / audience fit / conceptual purity, pick the winner. This is the single most important step for animation richness — it is the difference between rich educational animation and a voiced slide deck.

Scene architecture: pedagogical decomposition into scenes, each one a distinct cognitive transformation. For each scene, write a one-paragraph "visual strategy" recording the chosen candidate from the brainstorm.

Visual language: full visual grammar — palette with semantic roles, motion vocabulary, on-screen treatment of every tag. Reference the canonical visual patterns library (`visual_creativity_protocol.md §4`) when fixing the structural visual signatures.

### Phase H — Write the production artefacts

In order:

1. `05_narration_script.md` — the central deliverable. Second-by-second master script with the doctrine tags `[PREAMBLE]`, `[FORMAL]`, `[INSTANCE]`, `[BOUNDARY]`, `[CROSS_DOMAIN]`, `[ESSENCE]`, etc.
2. `06_voiceover.md` — clean TTS-ready voice-over, derived from the script.
3. `07_voice_direction.md` — tone / pacing / emotion direction per segment, with optional TTS engine profile.
4. `08_storyboard.md` — frame-by-frame visual storyboard with stable frame IDs.
5. `09_image_prompts.md` — DALL-E / ChatGPT prompts, self-contained, mapped 1-to-1 to storyboard frames.
6. `10_manim_blueprint.md` — Manim implementation blueprint at parameter level (no full code unless asked).

### Phase I — Audit, validate, commit

1. Write `11_rigor_audit.md`: classify every row as `[FORMAL]` / `[INFORMAL]` / `[NEUTRAL]`; run all four checklists; check the doctrine pillars mechanically.
2. Run `python scripts/validate_pipeline.py <pipeline-folder>` and paste the output into `11_rigor_audit.md` §11.7.
3. Update `INDEX.md` run log; flip every file's `status:` from `scaffolded` to `draft` (or further) as appropriate.
4. Commit with message `Add video script: <slug>`. No AI attribution. No `Co-authored-by`.

---

## 4. The 13-file deliverable (mandatory output structure)

Every script produces these 13 files, in this order, in `15_Reading_and_Learning/Video_Scripts/<YYYY-MM-DD>_<slug>/`. The scaffold script creates them all.

| # | File | Concern | Template |
|---|---|---|---|
| — | `INDEX.md` | Master navigation + status + run log | `templates/INDEX_template.md` |
| 00 | `00_declaration.md` | **Read first.** What / How / Why + paper citations + pillars + single-sentence essence | `templates/00_declaration_template.md` |
| 01 | `01_conceptual_blueprint.md` | Three-layer definitions + cross-domain unification + object-vs-representation discipline | `templates/01_conceptual_blueprint_template.md` |
| 02 | `02_pedagogical_design.md` | Learning-research principles applied + audience model + worked-example ladder + retrieval/self-explanation | `templates/02_pedagogical_design_template.md` |
| 03 | `03_scene_architecture.md` | Scene-by-scene conceptual decomposition (each scene = one cognitive transformation) | `templates/03_scene_architecture_template.md` |
| 04 | `04_visual_language.md` | Palette, typography, notation, motion vocabulary, on-screen treatment per tag | `templates/04_visual_language_template.md` |
| 05 | `05_narration_script.md` | **Central deliverable.** Second-by-second master script with full doctrine tags | `templates/05_narration_script_template.md` |
| 06 | `06_voiceover.md` | Clean TTS-ready voice-over with `[PAUSE Ns]` markers | `templates/06_voiceover_template.md` |
| 07 | `07_voice_direction.md` | Tone, pacing, prosody per tag; per-segment direction lines; TTS engine profile | `templates/07_voice_direction_template.md` |
| 08 | `08_storyboard.md` | Frame-by-frame storyboard with stable frame IDs | `templates/08_storyboard_template.md` |
| 09 | `09_image_prompts.md` | DALL-E / ChatGPT image prompts, self-contained, 1-to-1 with storyboard frames | `templates/09_image_prompts_template.md` |
| 10 | `10_manim_blueprint.md` | Manim implementation at parameter level, scene by scene | `templates/10_manim_blueprint_template.md` |
| 11 | `11_rigor_audit.md` | Formal/informal tagging + four checklists + doctrine pillar checks + validator output | `templates/11_rigor_audit_template.md` |

This structure is **deterministic**. Do not collapse, omit, or reorder. If a section inside a file is genuinely not applicable for a topic (e.g. no `[BOUNDARY]` block in a 90-second teaser), keep the heading and write one sentence saying so.

---

## 5. Audience tiers

| Tier | Notation density | Pace | Visual density | Example strategy |
|---|---|---|---|---|
| **Absolute beginner** | none until intuition is solid | very slow | concrete metaphors, intuitive geometry | example-first, definition emerges late |
| **Undergraduate** | standard symbols, defined when introduced | moderate | examples connected to formula and geometry | example-then-definition |
| **Advanced UG / master's** | full notation, theorems and derivations | brisk but deliberate | structural diagrams, transformations | definition-with-rich-examples |
| **Research / expert** | precise, abstract, compressed | dense | structural relationships, morphisms, flows | abstraction-first with motivating instances |
| **Mixed** | begins informal, lifts to formal | varying | bridges intuition and structure | progressive formalisation |

Even at research tier, the script remains visually rich and the doctrine pillars hold. The expert benefits from the §X.0 preamble too — it pins down the precise role of the formalism in *this* video.

---

## 6. Production modality

Pick a modality (or hybrid) based on the **dominant epistemic content** of the video:

| Content type | Preferred modality |
|---|---|
| Mathematical notation, geometric construction, formal animation, plots | **Manim** primary, motion-graphics secondary |
| 3D geometry, manifolds with non-trivial topology, fluid/field visualisation | **Blender** or Manim 3D, with Python-generated meshes |
| Algorithms, code execution, data structures | **Manim** for visual abstraction; live-coding overlay where useful |
| Cinematic context, conceptual metaphor, "open shot" of a phenomenon | **Generative video** (reference clip) + post-production overlay |
| Probability / stochastic processes | **Manim** for spaces and trajectories; Python plots for empirical |
| Physical phenomena (real-world reference) | Generative video or stock footage + Manim diagrams overlaid |
| Storyboard / pitch / aesthetic preview only | **AI image-generation** for reference frames |

**Hard rule:** symbolic precision (equations, labels, coordinate values) is never delegated to a generative video model. Manim or motion graphics renders all formal annotations in post.

---

## 7. The four doctrinal pillars (the binding style)

Restated here so they cannot be missed. Full mechanics: `style/ultra_formal_intuitive_doctrine.md`.

1. **Layered exposition.** Every formal beat is preceded by a `[PREAMBLE]` row in `05_narration_script.md` carrying the metaphor / problem statement / "what is about to happen and why". No notation appears during a `[PREAMBLE]` block.
2. **Jargon transparency.** Every English technical term is defined inline at first use, in narration and on screen, using the em-dash construction `<term> — that is, <8–15 word working definition>`. The full inline-definition register lives in `05_narration_script.md` §5.4.
3. **Three-layer definitions.** Every load-bearing concept is presented at three layers: fundamental (Layer 1), rigorous intuition (Layer 2), personal vision (Layer 3). Layers 1 and 2 live in `01_conceptual_blueprint.md`; Layer 1 also voiced in the script's `[FORMAL]` row; Layer 3 voiced in the synthesis movement.
4. **Cross-domain unification.** At least one `[CROSS_DOMAIN]` row in the script and one corresponding section in `01_conceptual_blueprint.md` §1.6. The same structure, in another domain. The structural correspondence stated precisely; what is lost in the translation, named.

Plus the **master simplification**: the single-sentence essence of the concept appears verbatim in `00_declaration.md` §0.1, in `INDEX.md`, and in the `[ESSENCE]` row of `05_narration_script.md`. The validator script checks this verbatim match.

---

## 8. Pedagogical laws (always on)

- **Explain from necessity.** Build the problem that forces the definition to appear.
- **Make abstraction visible.** For every abstract object, decide what it is, what it does, what it preserves, what it forgets, and how it should be drawn — then draw it.
- **Synchronise language and image.** Voice-over and visual event occupy the same instant (±0.3 s).
- **Motion is meaning — not decoration.** Continuous parametric motion is the primary vehicle for mathematical understanding in this medium. Every conceptual beat must have something changing continuously: a parameter sweeping, a curve being traced, a field evolving, a space deforming. A frame where no object is continuously transforming is a slide. This is the single most important production law.
- **Visual continuity.** Whenever possible, an object from one scene morphs into an object in the next.
- **Specify the driving parameter.** For every animation, name what is changing (the parameter), what it drives (the visual), and what it holds constant (the invariant). Unspecified motion is unspecifiable animation.
- **Preserve correctness.** Never sacrifice mathematical correctness for metaphor. Partial metaphors must name their limit.
- **Distinguish object from representation.** A coordinate expression is not the manifold; a sample path is not the process; a histogram is not the distribution. Make this distinction visible through animation: let the representation change while the object holds still.

### Animation richness test (apply before delivering any script)

For each conceptual scene, answer these three questions:

1. What parameter or quantity is driving the motion in this scene?
2. What is changing continuously as that parameter varies?
3. What is held invariant, and is that invariance visually evident?

If you cannot answer all three for a scene, that scene is underspecified. A conceptual scene whose "On-screen" column says only "object appears" or "diagram fades in" has failed this test. Revise.

### The two visual quality tests (apply before delivering any script)

From `style/visual_creativity_protocol.md §2`. These are the two non-negotiable filters for whether the animation is actually doing pedagogical work.

- **Inevitability Test.** Mute the narration mentally and ask: would a viewer at the target audience tier derive the right gestalt of the concept from the animation alone? If no, the animation is decoration and the prose carries the explanation — which means the medium is being wasted.
- **Frozen Frame Test.** Pick any second of the video; freeze; hand the still to a colleague. Could they explain what the video is teaching at that instant? A still from a great animation looks like a publication-quality figure with axes, labels, an object, a relationship. A still from a slide-paradigm video looks like a slide.

Both tests must pass for the major scenes. Boundary scenes (`[BOUNDARY]`, `[TRANSITION]`) get a pass on the Inevitability Test but not the Frozen Frame Test.

Deeper rationale: `style/rigorous_explanation_guide.md`, `style/visual_language_guide.md` (Animation richness doctrine), `style/visual_creativity_protocol.md` (brainstorm + canonical patterns).

---

## 9. Narration style

- Clear, precise, visually explicit, cinematic but not vague.
- Professional, technically accurate, mathematically rigorous.
- Free from filler and generic motivational fluff.

Banned phrasings: "this is a very important concept", "let's dive in", "in this video, we will learn about…", "as you can see…", "stay tuned", "buckle up", "get ready to have your mind blown".

Full guide: `style/narration_style_guide.md`.

---

## 10. The learning-research collection — paper-loading policy

The `learning_research/` folder contains ~24 papers on the cognitive science of learning. The collection is **archive + operational memory**:

- **Operational memory** (loaded every session): `extracted_principles.md` (14 principles), `video_design_rules.md` (24 rules).
- **Archive** (loaded on demand): per-paper summaries under `summaries/<category>/`, full PDFs under `papers/<category>/`.

The purpose of the paper folder is **not to turn every script into a literature review**. It is to distil principles into operational rules.

Read in this order, stop when you have what you need:

1. `style/ultra_formal_intuitive_doctrine.md` (the four pillars)
2. `learning_research/extracted_principles.md`
3. `learning_research/video_design_rules.md`
4. The relevant per-paper summary under `summaries/<category>/`, only when citing a specific empirical claim
5. The full PDF, only when (a) the user asks for a research-grounded deep dive, (b) the summary is insufficient, (c) a disagreement must be adjudicated, (d) a new principle must be extracted, (e) the skill itself is being updated.

For finding a specific paper: `learning_research/00_master_index.md`.

When the design draws on a specific principle, cite it briefly in `00_declaration.md` §0.4 — one or two lines, not a literature review.

### Hard constraint

Pedagogical optimisation may simplify the *route* into a concept; it may not simplify the *concept itself*. When research and rigour appear to conflict, rigour wins.

---

## 11. Bundled resources

```
educational-video-script-architect/
├── SKILL.md                                 ← you are here
├── CLAUDE.md                                ← operational rules for the harness
├── README.md
├── scripts/
│   ├── scaffold_pipeline.py                 ← run at Phase C
│   └── validate_pipeline.py                 ← run at Phase I
├── templates/                               ← one per deliverable file
│   ├── INDEX_template.md
│   ├── 00_declaration_template.md
│   ├── 01_conceptual_blueprint_template.md
│   ├── 02_pedagogical_design_template.md
│   ├── 03_scene_architecture_template.md
│   ├── 04_visual_language_template.md
│   ├── 05_narration_script_template.md
│   ├── 06_voiceover_template.md
│   ├── 07_voice_direction_template.md
│   ├── 08_storyboard_template.md
│   ├── 09_image_prompts_template.md
│   ├── 10_manim_blueprint_template.md
│   ├── 11_rigor_audit_template.md
│   ├── manim_blueprint_template.md          ← legacy, used as deeper Manim ref
│   ├── generative_video_prompt_template.md  ← used when modality includes generative
│   ├── production_blueprint_template.md     ← legacy general scaffold
│   └── storyboard_prompt_template.md        ← legacy storyboard ref
├── style/
│   ├── ultra_formal_intuitive_doctrine.md   ← the four pillars (read every session)
│   ├── elite_explainer_doctrine.md          ← aesthetic target: 3B1B/Veritasium/QF/Kurzgesagt (read every session)
│   ├── visual_creativity_protocol.md        ← brainstorm + canonical patterns (read every session, before scene design)
│   ├── narration_style_guide.md
│   ├── visual_language_guide.md
│   └── rigorous_explanation_guide.md
├── checklists/
│   ├── pedagogical_quality_checklist.md
│   ├── visual_quality_checklist.md
│   ├── mathematical_accuracy_checklist.md
│   └── production_readiness_checklist.md
├── examples/
│   ├── README.md
│   └── beginner_differential_manifold_script.md
├── learning_research/                       ← archive + operational memory
│   ├── README.md
│   ├── 00_master_index.md
│   ├── extracted_principles.md              ← read every session
│   ├── video_design_rules.md                ← read every session
│   ├── papers/
│   ├── summaries/
│   └── source_notes/
└── user_style/
    ├── README.md
    ├── user_reflections.md
    └── preferred_learning_style.md
```

**Reading order on first invocation in a session:**
SKILL.md → `style/ultra_formal_intuitive_doctrine.md` → `style/elite_explainer_doctrine.md` → `style/visual_creativity_protocol.md` → `learning_research/extracted_principles.md` → `learning_research/video_design_rules.md` → `templates/INDEX_template.md` → `templates/00_declaration_template.md` (always) → other templates as you reach their phase. Checklists load at the audit phase only. The elite explainer doctrine and visual creativity protocol are both re-consulted before designing each scene.

---

## 12. Frontmatter and persistence

Every file in the deliverable carries an OmarOS frontmatter block. The scaffold script writes them; the agent updates `status:` (scaffolded → draft → final) as it works.

The validator script enforces:

- Every required file present.
- Every file's `note_type` matches the canonical value.
- Every `status:` is no longer `scaffolded` once the agent has filled the body.
- `INDEX.md` references all 12 sibling files.
- Single-sentence essence verbatim across `00_declaration.md`, `05_narration_script.md`, `INDEX.md`.
- `[ESSENCE]` tag appears exactly once and `[CROSS_DOMAIN]` at least once in script.
- Every `[FORMAL]` row preceded by a `[PREAMBLE]` row.
- `06_voiceover.md` carries `[PAUSE Ns]` markers.

---

## 13. Final product test

Before delivering, ask yourself, honestly:

- Could a Manim implementer or motion-graphics editor build this video without coming back with questions?
- Is every important object visualised — or merely mentioned?
- Does every scene have a conceptual function distinct from the others?
- Is every formal beat preceded by a `[PREAMBLE]` row?
- Is every English technical term defined inline at first use?
- Does the cross-domain echo land structurally (not decoratively)?
- Is the single-sentence essence the categorical kernel, not a slogan?
- Would Omar — who values rigour at the level of the mathematical object, not just the notation — feel the explanation respects the subject?
- Would this be good enough as the blueprint for a paid educational product?

If any answer is no, revise before delivery. If `validate_pipeline.py` reports any structural FAIL, hold delivery.

---

## 14. Production Track — when Manim implementation will follow

The narrative pipeline above (`00_declaration` through `11_rigor_audit`) is sufficient for conceptual, pedagogical, narrative, stylistic and vocal work. It is **not** sufficient when a Manim implementation will follow.

When the deliverable involves executable code or a render — "Manim animation", "render scene X", "implementation for shot Y", or any task that will produce code or video output — the **production track** activates. It lives under `production_track/` and is **mandatory** before any line of Manim code is written.

### 14.1 The prime directive

> **No Manim code from vague prose. Only Manim code from explicit shot-level animation specifications.**

A narration script is not an animation specification. A storyboard is not an animation specification. A vague visual brief — *"two financial airport-style departure boards diverging as the basis crosses below zero"* — is **reference-only**; it is not authoritative for code generation. The artefacts that are authoritative are the **animation spec** (`09_animation_spec.yaml`) and the **component library** (`11_manim_component_library.md`). The Manim implementer reads those, not the narration.

Full doctrine: `production_track/doctrine/00_prime_directive.md`.

### 14.2 The canonical 12-artefact stack

The production track recasts the deliverable stack so that the first seven artefacts (conceptual / pedagogical / narrative / stylistic / vocal) are the input to a deterministic production layer of five files (the **production artefacts**):

| # | File | Concern | Layer |
|---|---|---|---|
| 01 | `01_conceptual_blueprint.md` | three-layer definitions, cross-domain echoes | Conceptual |
| 02 | `02_pedagogical_design.md` | cognitive engineering, learning principles | Pedagogical |
| 03 | `03_scene_architecture.md` | scene-by-scene cognitive decomposition | Narrative |
| 04 | `04_visual_language.md` | palette, motion vocabulary, semantic registers | Stylistic |
| 05 | `05_narration_script.md` | second-by-second master script | Narrative |
| 06 | `06_voiceover.md` | clean TTS-ready voice-over | Vocal |
| 07 | `07_voice_direction.md` | tone, prosody, pacing per segment | Vocal |
| 08 | `08_shotlist.md` | human-readable shot list | **Production** |
| 09 | `09_animation_spec.yaml` | machine-readable per-shot specs | **Production** |
| 10 | `10_asset_manifest.yaml` + `10b_data_manifest.yaml` | external assets and numeric values | **Production** |
| 11 | `11_manim_component_library.md` | reusable Manim primitives | **Production** |
| 12 | `12_render_validation_rubric.md` | pass/fail rubric for finished renders | **Production** |

The first seven artefacts are scaffolded by `scripts/scaffold_pipeline.py` and remain canonical for any video. The five **production artefacts** (files 08–12 in the table above, which *supersede* the narrative-only `08_storyboard.md` / `09_image_prompts.md` / `10_manim_blueprint.md` / `11_rigor_audit.md` for implementation work) are mandatory before any Manim code. **If 01–07 exist but 08–12 do not, generate the missing production artefacts before writing implementation code.** If the user asks for Manim code and the shot-level spec is missing, **do not invent** — emit a `MISSING_SPEC_REPORT` (see §14.6) or create the missing shot / animation specs first.

The narrative-track files of §4 (`08_storyboard.md`, `09_image_prompts.md`, `10_manim_blueprint.md`, `11_rigor_audit.md`) remain useful for non-Manim modalities and for the narrative audit. The production track does not replace them for projects that do not implement; it **supplements** them when implementation will follow.

### 14.3 The canonical pipeline

```
conceptual truth → pedagogical intent → scene architecture
                                          ↓
                            narration script + visual language
                                          ↓
                                       shotlist                  (visual_director)
                                          ↓
                                  animation spec                 (animation_spec)
                                          ↓
                            reusable Manim components            (component_architect)
                                          ↓
                                  implementation                 (manim_implementation)
                                          ↓
                                render validation                (render_review)
                                          ↓
                                human review (gated frames)
```

Each step has a single artefact, a single agent role, and a single authority. Skipping a step is the failure mode the prime directive forbids. Full flow: `production_track/doctrine/02_canonical_pipeline.md`.

### 14.4 Hierarchy of authority

When two layers of the stack conflict, the higher one wins:

```
1. Conceptual truth          (the highest)
2. Pedagogical objective
3. Scene function
4. Narration timing
5. Visual language
6. Shot specification
7. Animation specification
8. Implementation code       (the lowest)
```

**Code is the lowest layer. The concept is the highest layer.** A convenient implementation choice may never violate the conceptual or pedagogical layer. Full doctrine: `production_track/doctrine/01_hierarchy_of_authority.md`.

### 14.5 The doctrine subtree

`production_track/doctrine/` holds sixteen short files, each a single rule with rationale:

| Topic | File |
|---|---|
| Prime directive | `00_prime_directive.md` |
| Hierarchy of authority | `01_hierarchy_of_authority.md` |
| Canonical pipeline | `02_canonical_pipeline.md` |
| Semantic visual language (palette, registers) | `03_semantic_visual_language.md` |
| Semantic motion (FadeIn is not the default) | `04_semantic_motion.md` |
| Visual economy (≤35 visible words / shot) | `05_visual_economy.md` |
| Object memory (persistent objects across shots) | `06_object_memory.md` |
| Registered metaphors (no casual invention) | `07_registered_metaphors.md` |
| Frozen-frame and muted tests | `08_frozen_frame_and_muted_tests.md` |
| Synchronization (VO ↔ visual, silences) | `09_synchronization.md` |
| Negative constraints (rejection conditions) | `10_negative_constraints.md` |
| Anti-aesthetics (what to refuse) | `11_anti_aesthetics.md` |
| Formula doctrine (formulas linked to referents) | `12_formula_doctrine.md` |
| Financial / mathematical correctness | `13_financial_mathematical_correctness.md` |
| Failure behaviour (5 modes + `MISSING_SPEC` block) | `14_failure_behaviour.md` |
| Human review gates | `15_human_review_gates.md` |

The default palette: `EUR_BLUE` (EUR objects only), `USD_AMBER` (USD only), `BASIS_RED` (basis / loss / stress / imbalance / systemic deviation), `WHITE` (invariant structure, primary labels, neutral connectors), `NEUTRAL_GREY` (secondary labels, axes, grids, background annotations), `GAIN_GREEN` (confirmations, positive values), plus `DEEP_BACKGROUND`, `MID_BACKGROUND`, `DARK_GREY` for surfaces. A render that violates semantic colour discipline fails validation.

### 14.6 Failure behaviour

When the spec is incomplete or contradictory, the agent **reports** — it never invents. Five modes:

- `COMPLETE_SPEC` — fully specified.
- `PARTIAL_SPEC_WITH_ASSUMPTIONS` — proceed with low-risk, **labelled** defaults; each assumption recorded in the spec's `assumptions:` block.
- `MISSING_SPEC_REPORT` — high-risk field missing; emit a `MISSING_SPEC:` block and stop:

  ```yaml
  MISSING_SPEC:
    - field: <dotted path into the spec>
      why_needed: <reason>
      proposed_default: <value or null>
      risk_if_invented: <low | medium | high>
      requires_human_review: <bool>
  ```

- `CONTRADICTION_REPORT` — two layers disagree; name both, stop.
- `NEEDS_HUMAN_REVIEW` — high-leverage frame or new-metaphor decision requires sign-off.

For high-risk visual, conceptual, financial, mathematical, or pedagogical choices, **do not proceed without explicit specification or a clearly-labelled assumption**. Full doctrine: `production_track/doctrine/14_failure_behaviour.md`.

### 14.7 Downstream agent roles

Five specialised roles live under `production_track/prompts/`. When operating as one of them, read its prompt before acting; do not cross-read prompts for other roles.

- **`visual_director_agent`** — scene architecture + narration → shotlist (`08_shotlist.md`).
- **`animation_spec_agent`** — shotlist → animation spec (`09_animation_spec.yaml`).
- **`component_architect_agent`** — animation spec → component library + `manim/constants.py` + `manim/components/*.py`.
- **`manim_implementation_agent`** — animation spec + component library → scene code. **Does not read `05_narration_script.md` to invent visual design.** Emits `MISSING_SPEC` rather than improvise.
- **`render_review_agent`** — finished render + spec + rubric → pass/fail report. **A render can fail even if the code runs.** The quality bar is *"the animation communicates the intended idea with precision, elegance, and inevitability"*.

### 14.8 Recommended repository layout for a production-track video

```
video_project/
    01_conceptual_blueprint.md
    02_pedagogical_design.md
    03_scene_architecture.md
    04_visual_language.md
    05_narration_script.md
    06_voiceover.md
    07_voice_direction.md
    08_shotlist.md
    09_animation_spec.yaml
    10_asset_manifest.yaml
    10b_data_manifest.yaml
    11_manim_component_library.md
    12_render_validation_rubric.md
    manim/
        constants.py             ← palette, fonts, durations, easings, layout — single source of truth
        components/              ← boards / cashflows / valuation / risk / macro / typography
        scenes/                  ← orchestration only; no raw drawing
        render_tests/            ← validation_scene_NN_shot_<id>.md per shot
```

Scene files read like orchestration, not raw drawing chaos. The `construct()` method is a sequence of named beats; the code imports palette tokens, fonts, and durations from `manim/constants.py`; every reusable visual object is a component. See `production_track/prompts/manim_implementation_agent.md` for the full scene-file shape and `production_track/examples/basis_gap_opens_vague_vs_spec.md` for a compact worked example contrasting a vague prompt with a production-grade shot specification.

### 14.9 Detail does not mean clutter

A shot can have **high implementation detail and low visual density**. The purpose of the spec is **not to put more things on screen** — it is to remove ambiguity from what *is* on screen. Prefer one strong metaphor, one clear diagram, one exact formula, one meaningful transformation, over many icons, many labels, many unrelated moving parts. The spec exists so the small set of decisions on screen is deliberate.

### 14.10 Operational order when Manim implementation is requested

If the user asks for Manim code:

1. Verify files 01–07 exist and are filled. If not, that is the work to do first — read SKILL.md §3 phases A–H.
2. Verify files 08–12 exist and are filled. If not, that is the work to do **before** any code:
   - Run the `visual_director_agent` to produce `08_shotlist.md`.
   - Run the `animation_spec_agent` to produce `09_animation_spec.yaml`.
   - Run the `component_architect_agent` to produce `11_manim_component_library.md`, `manim/constants.py`, `manim/components/*.py`.
   - Fill `10_asset_manifest.yaml` and `10b_data_manifest.yaml` from the cited sources.
   - Fill `12_render_validation_rubric.md` from the per-shot fields in the animation spec.
3. **Only then** run the `manim_implementation_agent` to produce `manim/scenes/*.py`.
4. Run the `render_review_agent` against every rendered shot, writing per-shot validation reports.
5. Block release on any human-review-required shot whose `decision` is not `approved`.

The inviolable principle, restated:

> **No Manim code from vague prose. Only Manim code from explicit animation specs.**
