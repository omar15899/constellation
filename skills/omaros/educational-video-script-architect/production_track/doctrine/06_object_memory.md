# 06 — Object Memory

## The rule

**An object that appears once and matters is a persistent semantic object. It must keep its identity across the video.**

If the ghost time series appears in the cold open as a desaturated curve in the background, and returns 8 minutes later as a fully annotated chart, the viewer should *recognise* it. Same curve shape, same colour, same position cues. Re-introducing it as a "new" object breaks continuity and squanders the narrative leverage built in the cold open.

## The object memory ledger

`08_shotlist.md` and `09_animation_spec.yaml` jointly maintain an **object memory ledger** — a small table that tracks every persistent semantic object across the video. The template:

```yaml
object_id: ghost_time_series_basis
first_appearance:
  shot_id: IP-S0-F02
  visual_form: desaturated curve, NEUTRAL_GREY, 35% opacity, background z-index, no labels
semantic_role: the unexplained anomaly the cold open establishes — the basis curve before the viewer knows what the basis is
later_reappearances:
  - shot_id: IP-S4-F01
    morph: opacity 35% → 100%, colour NEUTRAL_GREY → BASIS_RED on the negative excursions only, axis labels appear
  - shot_id: IP-S6-F03
    morph: chart re-frames, BasisEKG component takes over, ticker reappears
morph_rule: the curve shape is invariant — its identity is the shape, never resampled or smoothed
continuity_constraints:
  - shape data drawn from data manifest entry `basis_history_2019_to_2024` — never regenerated
  - never reflected, scaled, or re-sampled
  - z-index must be ≤ scene foreground at all times
  - when re-introduced, must enter via opacity / colour morph, never via FadeIn from blank
human_review_required: true
```

The implementer reads this ledger before drawing the object. They do not improvise — the same `DataLabel`, the same `EUR_BLUE` shade, the same axis ticks.

## What "identity" means for different object kinds

- **Curves drawn from data** keep their underlying data array. If the basis history is `[0, -5, -12, -30, -45, …]`, that exact array is the curve's identity. A "stylised" or "smoothed" version is a *different* object and would need its own ledger entry.
- **Components instantiated from the library** keep their constructor arguments. The `EUR/USD SplitFlapBoard` initialised with `currency_pair="EURUSD"` is one object; calling `SplitFlapBoard(currency_pair="USDEUR")` is another.
- **Formulas** keep their TeX identity. `V_{CCS} = PV_{EUR} - S \cdot PV_{USD}` is the same formula whenever it appears; if the formula evolves (e.g., a term is added), the evolution is a `TransformMatchingTex`, not a re-creation.
- **Metaphor instances** keep their components. The `LockedNotionalExchange` mechanism, once drawn, is the same lock — its parts may animate, but the lock is the lock.

## Continuity primitives

When a persistent object re-enters a shot, the animation spec specifies *how*. Legitimate continuity primitives:

- **Opacity morph.** From ghosted (35–60%) to full opacity. Most natural for objects that "come into focus".
- **Colour morph.** From `NEUTRAL_GREY` to its semantic colour. Used when the viewer learns *what the object is* — the basis curve becomes red the moment we learn this *is* the basis.
- **Annotation reveal.** Labels and axes appear with `Create` / `DrawBorderThenFill` while the underlying shape holds.
- **Component composition.** A bare curve becomes a fully annotated chart by composing it with a `BasisEKG` overlay, ticks, a legend.
- **Frame re-anchor.** The whole canvas shifts so the object lands at a new position with the same identity.

The primitive **must not be `FadeOut` followed by `FadeIn`** of a re-drawn version. That destroys continuity and signals to the viewer that this is a new object.

## The viewer's experience

Object memory is what makes the climax of a video feel earned. When the basis curve becomes red 8 minutes after appearing as a ghost, the viewer has been quietly carrying it the whole time. The "reveal" is not the moment a new object appears — it is the moment a familiar object is named.

Without object memory, the climax is just another shot.

## Validation

The render_review agent compares the rendered form of every ledger object across its appearances. If the shape data, semantic colour, or component identity changes without a documented `morph_rule` in the ledger, the rendering fails. The agent also flags ledger entries with `human_review_required: true` for explicit sign-off before the render is approved.
