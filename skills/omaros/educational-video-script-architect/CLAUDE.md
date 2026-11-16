# CLAUDE.md — Operational guidance for the educational-video-script-architect skill

This file gives Claude Code the operational rules that govern *how* to work inside this skill, in addition to *what* the skill produces (which is in `SKILL.md`). The two files are complementary: `SKILL.md` is the contract with the user; this file is the contract with the harness.

## What this skill is, in one sentence

A **research-informed, mathematically rigorous, scholar-style educational-video architect** that produces a deterministic 13-file production package. The output is ultra-formal *and* ultra-intuitive at the same time — layered exposition, jargon transparency, three-layer definitions, and cross-domain unification — drawing on a curated learning-science collection without burning the session reading every PDF.

## How to use this skill (workflow at a glance)

For the full workflow see `SKILL.md` §3. The pipeline is **deterministic and ordered**:

1. **Phase A — Capture intent**: topic, audience tier, conceptual objective, duration, modality.
2. **Phase B — Consult operational memory**: read `style/ultra_formal_intuitive_doctrine.md`, `learning_research/extracted_principles.md`, `learning_research/video_design_rules.md`. Read `user_style/preferred_learning_style.md` if populated.
3. **Phase C — Scaffold**: run `python scripts/scaffold_pipeline.py <slug> --title "<title>"` to create the folder + 13 templates.
4. **Phase D — Write `00_declaration.md`** (the read-first document, with paper citations). **Wait for user approval** before continuing.
5. **Phase E — `01_conceptual_blueprint.md`** (three-layer definitions, cross-domain echoes).
6. **Phase F — `02_pedagogical_design.md`** (learning principles applied).
7. **Phase G — `03_scene_architecture.md` + `04_visual_language.md`**.
8. **Phase H — Production artefacts**: `05_narration_script.md` → `06_voiceover.md` → `07_voice_direction.md` → `08_storyboard.md` → `09_image_prompts.md` → `10_manim_blueprint.md`.
9. **Phase I — Audit + validate + commit**: write `11_rigor_audit.md`, run `scripts/validate_pipeline.py`, commit with `Add video script: <slug>`.

## Working-memory source of truth (in this exact order)

When the skill is active, treat these as the operational sources, in priority order. Stop reading as soon as you have what you need.

1. `SKILL.md`
2. `style/ultra_formal_intuitive_doctrine.md` — the four pillars (binding)
3. `style/elite_explainer_doctrine.md` — the aesthetic quality bar: 3B1B / Veritasium / Quantum Fracture / Kurzgesagt / Steve Mould / Real Engineering. Twelve properties, creator signatures, hook + reveal doctrines, scale shifts, physical correlates, multimodal redundancy, cinematic production layer. **Binding** — the rigor audit (`11_rigor_audit.md §11.5c`) tests every property.
4. `style/visual_creativity_protocol.md` — the brainstorm protocol and canonical patterns library (binding for animation richness; read **before scene design** and re-consulted **before every scene**)
5. `learning_research/extracted_principles.md`
6. `learning_research/video_design_rules.md`
7. The relevant per-paper summary under `learning_research/summaries/<category>/<paper>.md`
8. The full PDF under `learning_research/papers/<category>/<paper>.pdf` — **only when needed**

Templates are loaded as you reach the phase that produces the corresponding file. `INDEX_template.md` and `00_declaration_template.md` always load early; the rest load by phase. Checklists load at the audit phase only.

## Paper-loading policy (operational core)

Do not open all learning-research PDFs during normal skill use.
Use the following hierarchy:

1. Read `SKILL.md`.
2. Read `learning_research/extracted_principles.md`.
3. Read `learning_research/video_design_rules.md`.
4. Read only the relevant summaries under `learning_research/summaries/`.
5. Open full PDFs only when:
   - the user explicitly asks for a research-grounded deep dive,
   - the summary is insufficient,
   - there is uncertainty about a claim,
   - a new principle must be extracted,
   - or the skill is being updated.

The full PDFs are the **archival source**. The summaries and extracted principles are the **operational memory**.

> The purpose of the paper folder is not to turn every video script into a literature review. The purpose is to distil learning-science principles into operational design rules that improve educational video scripts while preserving rigorous mathematical correctness.

## How to select the relevant summary (when you do open one)

Decide which principle the script's design choice rests on, then load the summaries in that principle's category:

- Retrieval-prompt density / format → `02_retrieval_and_spacing/`
- Spacing of related concepts within a video or series → `02_retrieval_and_spacing/` (Cepeda)
- Discrimination between similar techniques → `03_interleaving_and_discrimination/`
- Visual density, narration overlap, on-screen text → `04_cognitive_load_and_worked_examples/` and `05_multimedia_and_visual_learning/`
- Worked-example sequence and fading → `04_cognitive_load_and_worked_examples/` (Atkinson, Renkl)
- Why-prompts and self-explanation → `06_self_explanation_and_elaboration/`
- The active-learning / engagement justification → `07_active_learning_and_stem/`
- Concrete-to-abstract design pattern → `08_concreteness_to_abstraction/`
- Audience-tier adaptation, scaffolding fade → `09_expertise_and_adaptive_instruction/`
- Calibration prompts, refutation framing → `10_metacognition_and_self_regulation/`

## How to design a video script using the paper-derived principles

The principles do not prescribe content; they shape *how the route into the content is built*. In practice:

- Pick the audience tier first. Tier choice constrains every later decision (R23 in `video_design_rules.md`).
- Default to a problem-first or phenomenon-first opening when concreteness fading applies (R7).
- Use worked examples for novices; replace with structural sketches for experts (R5).
- Insert at least one retrieval prompt per major scene (R2).
- Re-encounter the central object after intermediate material (R3).
- For discrimination tasks, interleave (R4).
- For non-obvious moves, prompt self-explanation (R9 in extracted_principles.md / R1 in video_design_rules.md).
- Synchronise narration and visual change within ±0.3 s (R9 in video_design_rules.md).
- Strip every visual element that does not encode conceptual structure (R12).
- End on a re-encounter with the original question (R21).

When in doubt, the **video_design_rules.md** file gives the operational rule with its citations.

## How to honour the doctrine (the four pillars)

The full mechanics live in `style/ultra_formal_intuitive_doctrine.md`. The pillars are not stylistic preferences — they are **structural invariants** that the validator script checks:

1. **Layered exposition.** Every `[FORMAL]` row in `05_narration_script.md` is preceded by a `[PREAMBLE]` row in the same scene. No notation appears during a `[PREAMBLE]` block. The validator counts mismatches.
2. **Jargon transparency.** Every English technical term (scheduler, placeholder, RTT, GIL, manifold, martingale, ...) is defined inline at first use using the em-dash construction `<term> — that is, <8–15 word working definition>`. The full register lives in `05_narration_script.md` §5.4.
3. **Three-layer definitions.** Layer 1 (fundamental) and Layer 2 (rigorous intuition) live in `01_conceptual_blueprint.md` §1.1; Layer 1 is also voiced in the script's `[FORMAL]` row; Layer 3 (personal vision) is voiced in the synthesis movement and lives in `01_conceptual_blueprint.md` §1.6.
4. **Cross-domain unification.** At least one `[CROSS_DOMAIN]` row in the script + one corresponding section in `01_conceptual_blueprint.md` §1.6. State the structural correspondence precisely; name what is lost in the translation.

Plus: the **single-sentence essence** (≤25 words, the categorical kernel of the concept) appears verbatim in `00_declaration.md` §0.1, in the `[ESSENCE]` row of the script, and in `INDEX.md`. The validator checks the verbatim match.

## How to preserve mathematical rigor

This is non-negotiable.

- Pedagogical optimization may simplify the *route* into a concept; it may not simplify the *concept itself*.
- Distinguish object, representation, notation, and example — visibly (R8).
- Do not soften definitions, do not blur quantifiers, do not present examples as if they were definitions.
- Where a metaphor is partial, name its limit explicitly.
- Tag each scene as **[FORMAL]** or **[INFORMAL]** in the rigor audit; never let an informal segment present itself with the rhetorical weight of a formal one.

The full discipline lives in `style/rigorous_explanation_guide.md` and `checklists/mathematical_accuracy_checklist.md`.

## How to incorporate Omar's reflections from `user_style/`

Omar's reflections and explicit preferences live in `user_style/`. Treat them as **stylistic and pedagogical inspiration**, not as a literary template.

- A video script has its own grammar (timing, visuals, narration sync) — preserve the *intellectual* style without copying the *literary form*.
- Read `user_style/preferred_learning_style.md` first if it is populated. The reflections under `user_reflections.md` are reference material — read them when you need to absorb tone or to confirm a stylistic choice.
- Cite the influence briefly in **Pedagogical design notes** when it visibly shapes the script.

## How to choose between Manim, generative video, motion graphics, or hybrid

The matrix in `SKILL.md` §5 governs this. Summary heuristics:

- **Manim** is the default for mathematical notation, geometric construction, formal animation, plots, algorithm visualisation. Manim is the only modality safe for symbolic precision.
- **Motion graphics** (After Effects, Motion, DaVinci Fusion) is right for typography, transitions between scenes, layered compositions over generative B-roll.
- **3D (Blender, Houdini)** is right for non-trivial geometry, fluid/field visualisation, and 3D manifold work that exceeds Manim's 3D capabilities.
- **Generative video** is right for cinematic context, conceptual metaphors, "open shot" of a phenomenon — *never* for symbolic precision. All formal labels are added in post.
- **Hybrid** is the realistic default: a generative-video establishing shot, Manim for the formal substance, motion graphics for transitions and titles.

## How to produce final outputs

Final outputs must be:

- **Deterministic in shape**: the 13-file deliverable, every file present, frontmatter validated by `scripts/validate_pipeline.py`.
- **Read-first contract**: `00_declaration.md` written, presented, and approved by the user before any other artefact is filled.
- **Second-by-second** in `05_narration_script.md`, with every important visual change specified and every row tagged.
- **Production-ready** in `10_manim_blueprint.md`, with parameter-level implementation notes the developer can act on without further questions.
- **Pedagogically justified** in `02_pedagogical_design.md`, with paper citations.
- **Doctrine-honouring**: every formal beat preceded by `[PREAMBLE]`; every English technical term defined inline at first use; three-layer definitions present; cross-domain echo voiced.
- **Rigorously audited** in `11_rigor_audit.md`, with informal vs formal segments tagged and validator output pasted in.

Default delivery is always the full 13-file structure. Length scales with the topic — a 90-second teaser still produces 13 files, just shorter inside each.

## When to refresh the principles

If a new paper is added to `learning_research/papers/<category>/`, also:

1. Add a per-paper summary under `learning_research/summaries/<category>/`.
2. Update `extracted_principles.md` if the paper introduces a new principle or substantially modifies an existing one.
3. Update `video_design_rules.md` if it implies a new operational rule.
4. Update `00_master_index.md` and `source_notes/doi_mapping.md`.

This is the only time during normal use when full PDFs should be read.

## Risk classification (which actions need confirmation)

- **Low risk** — designing a script, loading summaries, writing per-scene tables.
- **Medium risk** — modifying templates / checklists / style guides; changing the visual language defaults; adding new principles.
- **High risk (confirm before doing)** — replacing or removing a paper file; mass-renaming files in `papers/`; changing the loading hierarchy in `SKILL.md` §7.

## What this skill is *not*

- Not a literature-review generator. Citations in the design notes should be one or two lines, not a paragraph.
- Not a summary engine for papers. Per-paper summaries are written *once* (when a paper is added) and not re-summarised during normal use.
- Not a replacement for the user's mathematical authority. When the user names a result, take it as given; the skill structures the explanation, not the mathematics.
