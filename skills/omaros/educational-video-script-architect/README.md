# educational-video-script-architect

A research-informed, mathematically rigorous skill for designing **production-grade educational video scripts** for AI-assisted video pipelines (Manim, generative video, motion graphics, 3D, hybrid).

The skill produces a complete production blueprint per video: production brief → conceptual abstract → pedagogical design notes → scene architecture → visual language specification → second-by-second narration with on-screen actions and notation → modality-specific implementation notes → storyboard and image/video-generation prompts → polished voice-over → mathematical rigor audit → quality-control pass.

## Folder structure

```
educational-video-script-architect/
  SKILL.md                                 ← user-facing contract (when, what, how)
  CLAUDE.md                                ← operational rules for the harness
  README.md                                ← you are here
  examples/
    README.md
    beginner_differential_manifold_script.md   ← canonical worked example
  templates/
    video_script_template.md               ← the 12-section output scaffold
    storyboard_prompt_template.md
    production_blueprint_template.md
    manim_blueprint_template.md
    generative_video_prompt_template.md
  checklists/
    pedagogical_quality_checklist.md
    visual_quality_checklist.md
    mathematical_accuracy_checklist.md
    production_readiness_checklist.md
  style/
    narration_style_guide.md
    visual_language_guide.md
    rigorous_explanation_guide.md
  learning_research/
    README.md
    00_master_index.md                     ← map of the whole collection
    extracted_principles.md                ← 14-principle digest (operational)
    video_design_rules.md                  ← 24 production rules (operational)
    papers/                                ← archival PDFs by category
    summaries/                             ← per-paper .md (load on demand)
    source_notes/
      doi_mapping.md
      missing_papers.md
      duplicate_resolution.md
  user_style/
    README.md
    user_reflections.md
    preferred_learning_style.md
```

## How to invoke the skill

The skill triggers on any request that names — explicitly or implicitly — an educational video, animated explainer, Manim animation, storyboard, 3Blue1Brown-style video, lecture animation, visual proof, scientific visualization narrative, or AI-pipeline production script. It also triggers when the user describes only the topic and audience but the natural deliverable is a video script.

Typical invocation:

```
Use educational-video-script-architect.
Topic: <topic>
Audience: <beginner / undergraduate / advanced UG / research / mixed>
Duration: <MM:SS>
Production modality: <Manim / generative video / motion graphics / hybrid / pick the best>
```

The skill will read SKILL.md, then `learning_research/extracted_principles.md`, then `learning_research/video_design_rules.md`, then the relevant templates and style guides. It will not open the underlying PDFs unless the request requires a research-grounded deep dive.

## How to add new papers

1. Place the PDF in `~/Downloads/` (or directly into the right `learning_research/papers/<category>/` slot).
2. Pick the right category folder (the 10 categories under `learning_research/papers/` correspond to the 10 principle areas in `extracted_principles.md`).
3. Rename to the canonical scheme: `YEAR__firstauthor__short_title__principle.pdf`.
4. Create a per-paper summary under `learning_research/summaries/<category>/<same-name>.md`. Use the structure mandated in `extracted_principles.md` and existing summaries (frontmatter + Core claim / What it's useful for / Actionable principles / How the skill should use this / Risks / Keywords).
5. If the paper introduces a new principle or modifies an existing one, update `extracted_principles.md` and (if applicable) `video_design_rules.md`.
6. Update `00_master_index.md` and `source_notes/doi_mapping.md`.

A helper script (`/tmp/move_papers.py` was used for the initial seed) can be adapted for batch-add operations.

## How to add new user reflections

1. Add a section to `user_style/user_reflections.md` with the topic as the heading.
2. If the reflection implies a stylistic preference not yet captured, add a bullet to `user_style/preferred_learning_style.md`.
3. The skill reads `preferred_learning_style.md` first; the reflections are reference material.

## Coverage

- 24 papers integrated across 10 categories (cognitive load, multimedia learning, retrieval/spacing, interleaving, worked examples, self-explanation, active learning, concreteness fading, expertise/adaptive instruction, metacognition).
- 2 papers missing: Bjork & Bjork (2011) desirable-difficulties chapter (no DOI, no PDF located); Mayer (2022) Cambridge Handbook 3rd ed. chapter (not yet downloaded).
- See `learning_research/source_notes/missing_papers.md` for the slot reservations.

## Hard commitment

Pedagogical optimization may simplify the *route* into a concept; it may not simplify the *concept itself*. Mathematical and conceptual correctness are non-negotiable. Learning science is the route into the concept, not a permission to soften it.
