# Production Track

This subtree holds the **production-grade animation layer** of the skill. It exists because the narrative pipeline (files 01–07) is not, on its own, a contract a Manim implementer can act on without inventing visual design. The production track closes that gap.

The prime directive lives in [doctrine/00_prime_directive.md](doctrine/00_prime_directive.md):

> **No Manim code from vague prose. Only Manim code from explicit shot-level animation specifications.**

## When does the production track activate

Whenever the deliverable involves Manim code or render validation. If the user asks for "a Manim animation", "a render of scene X", "implementation for the basis-gap shot", or anything that will produce executable code or video output, the production track is mandatory. The narrative-only pipeline (storyboard, image prompts, narration) is preserved for projects where no implementation will follow.

## The canonical artefact stack

| # | File | Concern | Track |
|---|---|---|---|
| 01 | `01_conceptual_blueprint.md` | Three-layer definitions, cross-domain echoes | Conceptual |
| 02 | `02_pedagogical_design.md` | Cognitive engineering, learning principles applied | Pedagogical |
| 03 | `03_scene_architecture.md` | Scene-by-scene decomposition | Narrative |
| 04 | `04_visual_language.md` | Palette, motion vocabulary, semantic registers | Stylistic |
| 05 | `05_narration_script.md` | Second-by-second master script | Narrative |
| 06 | `06_voiceover.md` | Clean TTS-ready voice-over | Vocal |
| 07 | `07_voice_direction.md` | Tone, prosody, pacing per segment | Vocal |
| 08 | `08_shotlist.md` | Human-readable shot list (visual units) | **Production** |
| 09 | `09_animation_spec.yaml` | Machine-readable shot specs (one per shot) | **Production** |
| 10 | `10_asset_manifest.yaml` + `10b_data_manifest.yaml` | Assets and data values | **Production** |
| 11 | `11_manim_component_library.md` | Reusable Manim component plan | **Production** |
| 12 | `12_render_validation_rubric.md` | Pass/fail rubric for finished renders | **Production** |

Files 01–07 are conceptual, pedagogical, narrative, stylistic, vocal. Files 08–12 are the **production artefacts** and are **mandatory before any Manim code is written**. If 01–07 exist but 08–12 do not, generate the missing production artefacts first.

## Subtree map

```
production_track/
  README.md                          ← you are here
  doctrine/
    00_prime_directive.md            ← no Manim code from vague prose
    01_hierarchy_of_authority.md     ← 8-layer authority stack
    02_canonical_pipeline.md         ← the full 12-step flow
    03_semantic_visual_language.md   ← colours are semantic, not decorative
    04_semantic_motion.md            ← every movement has a meaning
    05_visual_economy.md             ← ≤35 visible words per shot
    06_object_memory.md              ← persistent objects across shots
    07_registered_metaphors.md       ← only approved metaphors
    08_frozen_frame_and_muted_tests.md
    09_synchronization.md            ← VO ↔ visual tolerance, pause policy
    10_negative_constraints.md       ← explicit rejection conditions
    11_anti_aesthetics.md            ← what to refuse (corporate, crypto, particle-field, …)
    12_formula_doctrine.md           ← how formulas appear and connect to objects
    13_financial_mathematical_correctness.md
    14_failure_behaviour.md          ← 5 failure modes + MISSING_SPEC block
    15_human_review_gates.md         ← high-leverage frames
  templates/
    08_shotlist_template.md
    09_animation_spec_template.yaml
    10_asset_manifest_template.yaml
    10b_data_manifest_template.yaml
    11_manim_component_library_template.md
    12_render_validation_rubric_template.md
  prompts/
    visual_director_agent.md         ← scene arch + narration → shotlist
    animation_spec_agent.md          ← shotlist → animation_spec.yaml
    component_architect_agent.md     ← define reusable components
    manim_implementation_agent.md    ← spec + components → code (only)
    render_review_agent.md           ← render vs spec
  examples/
    basis_gap_opens_vague_vs_spec.md ← IP-S0-F02 worked example
```

## How to read this subtree

On every production-track invocation, read in order:

1. `doctrine/00_prime_directive.md` (binding)
2. `doctrine/01_hierarchy_of_authority.md` (binding)
3. `doctrine/02_canonical_pipeline.md` (binding)
4. The templates you are about to fill (lazy)
5. The doctrine files relevant to the current shot (semantic visual language for any colour decision, formula doctrine for any formula appearance, etc.)
6. The prompt for the agent role you are currently playing (visual_director / animation_spec / component_architect / manim_implementation / render_review)

The doctrine files are short on purpose. Each one is a single rule, with its rationale, applied to the production track. Reading them all is fast.

## Recommended project layout for a video using the production track

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
        constants.py           ← palette, fonts, durations, easing — single source of truth
        components/
            boards.py          ← SplitFlapBoard, BasisTicker, …
            cashflows.py       ← CashflowArrow, PaymentPulse, …
            valuation.py       ← PresentValueBar, FXConversionMorph, MTMBalanceScale, …
            risk.py            ← DV01Dial, SensitivityBar, …
            macro.py           ← DollarGravityField, CIPTightrope, BasisEKG, FedSwapValve, …
            typography.py      ← SceneTitle, InlineDefinition, FormulaPanel, DataLabel, …
        scenes/
            scene_00_anomaly.py
            scene_01_problem.py
            scene_02_machine.py
            …
        render_tests/
            validation_scene_00.md
```

The Manim scene files should read like orchestration, not raw drawing chaos. See `doctrine/02_canonical_pipeline.md` §"Scene file structure" and `examples/basis_gap_opens_vague_vs_spec.md`.
