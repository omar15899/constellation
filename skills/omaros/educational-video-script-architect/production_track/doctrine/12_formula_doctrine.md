# 12 — Formula Doctrine

## The rule

**Formulas are not overlays. A formula must be visually connected to the objects it summarises.**

A formula that drops onto the screen as a standalone TeX block, disconnected from the diagram it abstracts, is decoration. The pedagogical move is not "here is the formula" — it is "the formula is what these objects, together, *are*". The animation must show the second.

## The four legitimate appearance mechanisms

A formula may appear by one and only one of the following mechanisms:

1. **Morphing from visual objects.** The bars, arrows, or labels on screen `Transform` into the formula. The viewer sees the diagrammatic quantities literally *become* the formula's tokens.
2. **Emerging after the corresponding quantities have appeared.** The bars representing `PV_EUR` and `PV_USD` are already on screen, with labels. The formula is then assembled above them, with each token positioned over its corresponding bar.
3. **Being assembled term by term from already visible components.** `V_CCS = ___` appears first. Then `PV_EUR` slides up from the EUR bar. Then `-S · PV_USD` is built from the FX rate marker and the USD bar.
4. **Being colour-matched to its visual referents and anchored near the diagram it abstracts.** If 1–3 are not possible (e.g., the formula appears in a recap shot), it still arrives with semantic colours and a clear spatial relationship to its referents.

## What is forbidden

- Dropping the formula in as a freestanding TeX block in the upper-right.
- Showing the formula *before* its visible referents exist.
- Using a different colour for `PV_EUR` in the formula than the EUR bar uses on screen.
- Animating the formula as a unit when it should be assembled term-by-term.
- A formula that "decorates" the shot without being the focus or the summary.

## A worked example

> Formula: `V_CCS = PV_EUR - S · PV_USD`

| Token | Colour | Visual referent |
|---|---|---|
| `V_CCS` | `WHITE` | the value of the swap — the dependent quantity |
| `PV_EUR` | `EUR_BLUE` | the EUR present-value bar |
| `S` | `WHITE` or `NEUTRAL_GREY` | the FX rate marker / converter |
| `PV_USD` | `USD_AMBER` | the USD present-value bar |
| `-` | `WHITE` | the minus sign, an operator |

The formula's appearance, in spec form:

```yaml
formula_appearance:
  formula_id: V_CCS_decomposition
  tex: "V_{CCS} = PV_{EUR} - S \\cdot PV_{USD}"
  appearance_mechanism: assembly_from_components
  preconditions:
    - PV_EUR_bar visible at full opacity
    - PV_USD_bar visible at full opacity
    - FX_rate_marker visible
  assembly_keyframes:
    - t: 0.0
      visible: "V_{CCS} ="
      colour_per_token:
        V_{CCS}: WHITE
        =: WHITE
    - t: 0.6
      visible: "V_{CCS} = PV_{EUR}"
      animation:
        token: PV_{EUR}
        source: PV_EUR_bar
        action: morph_to_formula_position
      colour_per_token:
        PV_{EUR}: EUR_BLUE
    - t: 1.4
      visible: "V_{CCS} = PV_{EUR} - S \\cdot"
      animation:
        token: "- S \\cdot"
        source: FX_rate_marker
        action: morph_to_formula_position
      colour_per_token:
        S: WHITE
        '-': WHITE
        '\\cdot': WHITE
    - t: 2.0
      visible: "V_{CCS} = PV_{EUR} - S \\cdot PV_{USD}"
      animation:
        token: PV_{USD}
        source: PV_USD_bar
        action: morph_to_formula_position
      colour_per_token:
        PV_{USD}: USD_AMBER
  final_position:
    anchor: above_bars
    centred_horizontally_over: PV_EUR_bar, PV_USD_bar
  persistence_into_next_shot: hold full opacity for 1.5 s then ghost to 50%
```

By the time `t = 2.0`, the formula is *literally* the diagram, rewritten in symbols. The viewer has watched the bars become the tokens. The formula is not a summary slide; it is the final state of the animation.

## When the formula is the focal point

Some shots exist *to* introduce or transform a formula. For those, the formula is the dominant focal point and the visual referents are subordinate. The same rules apply — semantic colour, anchored to referents — but the composition is reversed: the formula is centred, large; the diagram is small or off to one side.

For transformations of a formula (deriving one form from another), use `TransformMatchingTex` so the viewer sees which tokens persist and which change. A `FadeOut` of the old formula followed by a `FadeIn` of the new one severs the connection between them.

## Why this matters

The single most common AI-explainer failure is treating formulas as *captions* on the visual. A caption is information the visual delivers in case the viewer missed it; a formula is the *thing the visual was building toward*. Treating it as a caption demotes the entire animation to illustration. Treating it as the assembled summary of the visual elevates the entire animation to a derivation.

The render_review agent checks: does every visible token of the formula have a documented visual referent in the spec? Is the token's colour the same as its referent's colour? Did the formula appear by one of the four legitimate mechanisms? If any answer is no, the shot fails.
