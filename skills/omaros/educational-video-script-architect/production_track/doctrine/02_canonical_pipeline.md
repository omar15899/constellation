# 02 — Canonical Pipeline

The full flow from concept to validated render. Each step has a single artefact, a single agent role, and a single authority. Skipping a step is the failure mode the prime directive forbids.

## The flow

```
conceptual truth
    ↓
pedagogical intent
    ↓
scene architecture
    ↓
narration script
    ↓
visual language
    ↓
shotlist                       ← visual_director agent
    ↓
animation spec                 ← animation_spec agent
    ↓
reusable Manim components      ← component_architect agent
    ↓
implementation                 ← manim_implementation agent
    ↓
render validation              ← render_review agent
    ↓
human review (gated frames)
```

The first five steps are conceptual / narrative / stylistic (files 01–07). The last six are the production track (files 08–12 + code + review).

## What each step produces

| Step | Artefact | Authority over |
|---|---|---|
| Conceptual truth | `01_conceptual_blueprint.md` | what the concept *is* |
| Pedagogical intent | `02_pedagogical_design.md` | what the viewer must come to recognise |
| Scene architecture | `03_scene_architecture.md` | the cognitive arc, scene-by-scene |
| Narration script | `05_narration_script.md` | what the viewer hears, second by second |
| Visual language | `04_visual_language.md` | palette, motion vocabulary, semantic registers |
| Shotlist | `08_shotlist.md` | the division of the video into shots, each with cognitive purpose |
| Animation spec | `09_animation_spec.yaml` | every object, every keyframe, every easing — per shot |
| Reusable components | `11_manim_component_library.md` | the catalogue of reusable Manim primitives |
| Implementation | `manim/scenes/*.py` | the executable code |
| Validation | `manim/render_tests/validation_scene_*.md` against `12_render_validation_rubric.md` | pass / fail per shot |
| Human review | inline in the artefact and the render | sign-off on high-leverage frames |

## The role / artefact / authority binding

Each agent role has **one input authority** and **one output artefact**. Crossing this boundary is a violation.

- **visual_director** reads `03_scene_architecture.md` + `04_visual_language.md` + `05_narration_script.md` + the conceptual blueprint. Produces `08_shotlist.md`. Does not produce code.
- **animation_spec** reads `08_shotlist.md` + `04_visual_language.md` + `01_conceptual_blueprint.md`. Produces `09_animation_spec.yaml` (one shot per YAML document, multiple documents in the file). Does not produce code.
- **component_architect** reads `09_animation_spec.yaml` and identifies repeated structural patterns. Produces `11_manim_component_library.md`. May produce skeleton component code under `manim/components/` but does not implement scene logic.
- **manim_implementation** reads `09_animation_spec.yaml` + `11_manim_component_library.md` + `10_asset_manifest.yaml` + `10b_data_manifest.yaml`. Produces `manim/scenes/scene_NN_*.py` and any new components requested by the spec. **Does not read** `05_narration_script.md` to invent visual design. Reads it only for narration cues that the synchronization block of the spec references.
- **render_review** reads the finished render + `09_animation_spec.yaml` + `12_render_validation_rubric.md`. Produces a per-shot pass / fail report in `manim/render_tests/validation_scene_NN.md`. Does not edit the spec or the code.

## Scene file structure (Manim implementation discipline)

Manim scene files should read like **orchestration**, not raw drawing chaos. The spec resolves what happens; the code expresses *how*, in a structure a human reader can follow.

**Good:**

```python
class Scene00Anomaly(Scene):
    def construct(self):
        self.setup_palette()        # from manim/constants.py
        self.create_background()    # from manim/components/typography.py
        self.create_boards()        # from manim/components/boards.py — SplitFlapBoard
        self.animate_gap_opening()  # the central shot
        self.hold_final_frame()
        self.transition_out()
```

**Bad:**

```python
class Scene(Scene):
    def construct(self):
        rect1 = Rectangle(...)
        text1 = Text(...)
        text2 = Text(...)
        self.play(FadeIn(...))
```

Why the bad version is bad:

- No reusable components — `Rectangle(...)` is drawing a `SplitFlapBoard` from scratch each time.
- No semantic colour discipline — colours hard-coded inline rather than imported from `constants.py`.
- No shot decomposition — `construct()` is one flat sequence rather than a sequence of named beats.
- Default `FadeIn` for structural objects — violates the semantic motion doctrine (`04_semantic_motion.md`).
- Magic constants — sizes, fonts, positions all inline rather than centralised.

## Centralisation discipline

Inside `manim/`:

- `constants.py` holds the palette tokens, fonts, default durations, default easings, frame dimensions, safe areas. **Single source of truth** — scenes import from here, never hard-code.
- `components/*.py` hold reusable Manim primitives. Constructors take semantic parameters (`currency="EUR"`, `magnitude=75`) and resolve their own styling from `constants.py`.
- `scenes/*.py` are orchestrations of components. They contain almost no raw `Rectangle`, `Text`, `Line` calls — those are inside components.
- `render_tests/*.md` are the validation reports.

The component library is the structural defence against hard-coded chaos. If a shot needs something the library cannot produce, the right move is to **propose a new component** (via the component_architect role) before writing scene code.

## Detail does not mean clutter

A shot can have **high implementation detail and low visual density**. The purpose of the spec is not to put more things on screen — it is to remove ambiguity from what is on screen.

Prefer:

- one strong metaphor
- one clear diagram
- one exact formula
- one meaningful transformation

over:

- many icons
- many labels
- many unrelated moving parts
- many simultaneous explanations

A 35-page spec for a single shot that contains two objects and one transition is *correct*. A 2-line spec for a shot containing eight objects and four simultaneous animations is *wrong*. The spec exists to make the small set of decisions deliberate.
