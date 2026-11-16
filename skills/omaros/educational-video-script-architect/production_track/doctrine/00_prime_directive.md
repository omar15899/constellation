# 00 — Prime Directive

## The rule

**No Manim code from vague prose. Only Manim code from explicit shot-level animation specifications.**

## What this means in practice

A narration script is not an animation specification. A storyboard is not an animation specification. A scene description is not an animation specification. Reading any of these and writing Manim code directly is the failure mode this skill exists to prevent.

The four kinds of artefact, in increasing implementation specificity:

| Artefact | Says |
|---|---|
| `05_narration_script.md` | **What happens** — what the viewer hears, what the scene is about |
| `08_shotlist.md` | **How the video is divided into visual units** — one shot = one composition + one cognitive purpose |
| `09_animation_spec.yaml` (per shot) | **How each visual unit is composed and exactly how each object moves** — positions, sizes, colours, keyframes, easing, persistence, semantic role |
| `11_manim_component_library.md` | **What reusable Manim primitives exist** — `SplitFlapBoard`, `BasisTicker`, `CashflowArrow`, … with constructor signatures |

Only the last two are sufficient authority for writing implementation code. If they are missing, the implementer must produce them or report `MISSING_SPEC` (see `14_failure_behaviour.md`) — never silently invent.

## Why this rule exists

Prose is genuinely ambiguous about visual design. A line of narration like *"the basis gap opens"* is compatible with hundreds of legitimate animations:

- A red bar growing downward from a horizontal axis.
- A second curve diverging from a first.
- Two airport-style departure boards drifting apart.
- A pressure gauge sweeping into a red zone.
- A tension line snapping.

If an AI agent reads "the basis gap opens" and renders Manim code, it picks one of these *at random*, with implicit choices about colour, position, timing, ease curve, label placement, and persistence. The result looks plausible the first time, but it is not a *decision* — it is a default. Defaults compounded across 200 shots produce video that is technically functional, visually generic, and pedagogically weak.

The animation spec is the place where these decisions are made *explicitly*, by an agent whose role is visual direction, before any line of code is written. Once the spec exists, implementation is mechanical: the Manim implementation agent has no remaining design freedom and cannot accidentally produce a slide deck.

## The discipline this protects

Specifying the shot before coding it forces the visual director (human or agent) to think at the right level of abstraction:

- **Why this composition?** — what is the viewer's eye supposed to land on first?
- **What is the dominant metaphor?** — is it registered (see `07_registered_metaphors.md`)?
- **What is changing continuously?** — what is the driving parameter?
- **What persists into the next shot?** — what builds continuity of object memory?
- **What does the frame mean when muted?** — can the visual carry the idea without the voice?
- **What does the frame mean when frozen?** — could the still serve as a publication-quality figure?

None of these questions are answerable from prose alone. They demand a separate, deliberate artefact.

## The implementer's contract

If you are writing Manim code and the spec does not resolve a question (where to place the object, what colour, what easing, what duration, what persists into the next shot), you have three legitimate moves:

1. **Stop.** Emit a `MISSING_SPEC:` block (format in `14_failure_behaviour.md`) naming the field, why it is needed, and the proposed default. Wait for the user (or the visual director) to fill the gap.
2. **Mark a proposed default.** If the missing field is low-risk (e.g., a font weight where every other font weight in the spec is consistent), pick the consistent default and annotate it as a proposed default with a comment in the code and an entry in the implementation notes. The render review agent will flag it.
3. **Refuse the high-risk invention.** If the missing field is high-risk (a colour choice, a metaphor, a sign convention, a financial value, a key visual position), do not proceed. The implementer is not authorised to make these decisions silently.

Inventing visual design from `05_narration_script.md` while writing Manim code is **never** the right move. The narration script is read-only at the implementation layer; it explains intent, it does not authorise visual decisions.

## Restatement

A specification removes ambiguity. Prose introduces it. Skipping the spec is not a shortcut — it is the renaming of "I'm guessing" as "I'm implementing." The skill exists to make that renaming impossible.
