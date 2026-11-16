# 03 — Semantic Visual Language

## The rule

**Colour is semantic, not decorative.** Each token in the palette has a meaning. A colour appears on screen because of what the object is, not because it would look nice. An animation that violates this discipline fails validation.

## Default palette

Unless the project's `04_visual_language.md` overrides it, the production track uses:

| Token | Hex | Meaning |
|---|---|---|
| `EUR_BLUE` | `#4A9EFF` | EUR objects only |
| `USD_AMBER` | `#F0A500` | USD objects only |
| `BASIS_RED` | `#E85D5D` | Basis, loss, stress, imbalance, systemic deviation |
| `WHITE` | `#FFFFFF` | Invariant structure, primary labels, neutral connectors |
| `NEUTRAL_GREY` | `#CCCCCC` | Secondary labels, axes, grids, background annotations |
| `GAIN_GREEN` | `#4CAF50` | Confirmations, positive values |
| `DEEP_BACKGROUND` | `#0F0F1A` | Primary background |
| `MID_BACKGROUND` | `#1A1A2E` | Panels, secondary surfaces |
| `DARK_GREY` | `#2A2A3E` | Tertiary surfaces, dividers |

These tokens live in `manim/constants.py`. Scenes import them; they are never hard-coded.

## The semantic rules

- `EUR_BLUE` appears **only** for EUR objects (cashflows, bars, labels, tickers, curves).
- `USD_AMBER` appears **only** for USD objects.
- `BASIS_RED` appears **only** for basis, loss, stress, imbalance, or systemic deviation. Never decorative red. Never red for a generic warning unrelated to the basis story.
- `WHITE` is reserved for **invariant structure** (axes that persist, frame divisions, scene titles), **primary labels**, and **neutral connectors** (lines that join two semantically tagged objects without themselves carrying a currency or sign).
- `NEUTRAL_GREY` carries secondary information — grid lines, minor axes, background annotations the eye should not land on first.
- `GAIN_GREEN` appears only for confirmations or positive values. Never for "moving forward in the explanation"; never for a generic "good" event.

If your shot needs a colour the palette does not name, do not invent one. Either:

1. Use `NEUTRAL_GREY` or `WHITE` if the object is structural.
2. Propose a palette extension in `04_visual_language.md`, justify the semantic role, and update the constants. Do not introduce a one-off colour in code.

## Why this matters

Across a 200-shot video, viewers learn the palette implicitly within the first minute. After that, when they see a flash of `BASIS_RED`, they expect something about the basis, the loss, or the systemic deviation — even before the narration says so. This is part of what makes the animation legible when muted (see `08_frozen_frame_and_muted_tests.md`).

If `BASIS_RED` is also used for a generic "warning" or a "danger" zone or "a thing we are about to delete", the viewer's implicit mapping breaks. The video loses its semantic grip, and every individual shot has to re-explain itself from scratch.

## Validation

The render_review agent checks every visible colour against the palette and against the object's semantic role. Findings:

- **Colour outside palette.** Fail.
- **Palette colour on the wrong kind of object** (e.g., `EUR_BLUE` on a USD ticker, `GAIN_GREEN` on a generic transition object). Fail.
- **`BASIS_RED` used for anything other than basis / loss / stress / imbalance / systemic deviation.** Fail.

The implementer is not authorised to substitute a "close enough" colour. The palette is the surface contract.

## Beyond colour

The semantic-visual-language doctrine extends past colour to other visual registers:

- **Stroke width** carries hierarchy: primary objects (the spine of the diagram) use the canonical primary stroke, secondary objects (annotations, references) use thinner strokes.
- **Opacity** carries persistence: ghosted objects (semitransparent) are present-but-recessive, used during a retrieval pause or as continuity with a previous shot.
- **Typography** carries register: a `SceneTitle` is one font/weight/size; an `InlineDefinition` is another; a `FormulaPanel` uses TeX; a `DataLabel` uses the canonical numeric font. Mixing these registers within a shot creates noise; reserve a register for its role.

All of these are tokenised in `manim/constants.py` and resolved by components, not by scenes.
