# 10 — Negative Constraints (Rejection Conditions)

Positive rules tell the implementer what to do. Negative rules tell them what they may not do. These are the conditions under which a shot is **rejected** at the render_review stage. Each is unconditional unless the spec has declared an explicit exemption with a written rationale.

## Rejection conditions

A shot is rejected if **any** of the following holds:

1. **More than `max_visible_words` words visible at any frame.** Default 35. The spec may raise the limit; the render must respect the declared limit (see `05_visual_economy.md`).
2. **A decorative financial icon appears with no semantic role.** No clip-art dollar signs, no skyline silhouettes, no faux-3D coins. Every icon must be a registered component with a documented semantic role.
3. **A number appears on screen that is not in the data manifest.** Every visible numeric value must be sourced from `10b_data_manifest.yaml` (whether exact, illustrative, or stylized). Inline magic numbers are not permitted.
4. **A colour violates the semantic palette.** Either a non-palette colour is rendered, or a palette colour appears on the wrong kind of object. See `03_semantic_visual_language.md`.
5. **Arrows move without representing a real flow, force, transformation, or dependency.** Decorative arrows that are merely there to "make it dynamic" fail.
6. **A formula appears disconnected from its visual referents.** Formulas must morph, emerge, or be assembled from the visible quantities they summarise — see `12_formula_doctrine.md`. Formulas dropped in as overlay text fail.
7. **All objects enter by a generic `FadeIn`.** This signals that the motion vocabulary was not exercised. `FadeIn` is the rarest legitimate primitive, not the default — see `04_semantic_motion.md`.
8. **The frame resembles a PowerPoint slide rather than an animated explanation.** A title at the top, three bullet points in the middle, a chart at the bottom, and a logo in the corner is a slide. The medium is wasted.
9. **The visual cannot be understood when muted** (and `muted_test_exempt` is not set for this shot). See `08_frozen_frame_and_muted_tests.md`.
10. **The frozen frame cannot communicate the main idea** at the declared `key_moment_time`. See `08_frozen_frame_and_muted_tests.md`.
11. **The implementation invents layout not present in the spec.** Positions, sizes, and z-indexes are resolved in the spec. If the implementer chose them, the shot fails until the spec is amended.
12. **A new metaphor is introduced without registration.** See `07_registered_metaphors.md`.
13. **A persistent object is re-drawn without honouring its memory ledger.** See `06_object_memory.md`.
14. **A voiceover cue lands outside its declared tolerance.** See `09_synchronization.md`.
15. **A retrieval / self-explanation pause is filled with new motion or new content.** See `09_synchronization.md`.
16. **A magic constant appears in scene code that is not imported from `manim/constants.py`.** Even one hard-coded `0.85` or `BLUE` is enough.
17. **A non-component shape is hand-drawn where the library has a component.** If `SplitFlapBoard` exists and the shot draws a board with raw `Rectangle` / `Text`, the shot fails.

## How to declare an exemption

An exemption is a written acknowledgement in the spec that the shot deliberately violates one of the conditions for a documented reason:

```yaml
rejection_conditions:
  exemptions:
    - condition: max_visible_words
      override: 60
      rationale: |
        This is the final essence frame. It deliberately holds the
        single-sentence essence (25 words) plus the formula
        V_CCS = PV_EUR - S · PV_USD (10 tokens) plus 4 object labels
        for the viewer to consolidate the explanation across an 8-second hold.
```

The render_review agent reads exemptions before applying the rules. An exemption with no rationale, or a rationale that is generic ("looks better this way"), is treated as if the exemption were absent.

## Why a list and not a feeling

This is the kind of doctrine that tends to drift. Without a list, every project starts respecting it and slowly erodes — the third project has one decorative dollar sign, the fifth has six, by the tenth the discipline is gone. With a list, every rejection is a *named* condition, not a stylistic disagreement. The conversation between visual director and implementer becomes: "this shot fails condition 4 — the EUR bar is green instead of blue" — actionable, not subjective.

## The list grows

When a new failure mode appears in practice that this list does not name, add it. The conditions are stable enough to be load-bearing and editable enough to absorb new failure modes. New conditions are added to `04_visual_language.md` if they are project-specific, or to this file (with a brief explanation) if they are general.
