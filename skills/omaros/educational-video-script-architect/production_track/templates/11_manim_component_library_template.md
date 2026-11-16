---
title: "<Title> — Manim Component Library"
note_type: video_manim_component_library
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
slug: <topic-slug>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
status: draft
production_track: true
---

# Manim Component Library — `<topic>`

The reusable Manim primitives the production uses. Every shot in `09_animation_spec.yaml` references components by name from this catalogue. The implementer's job is to *use* these components, not to draw raw shapes that duplicate their capability.

## Where the components live in code

```
manim/
  constants.py            ← palette, fonts, default durations & easings, frame metrics
  components/
    boards.py             ← SplitFlapBoard, BasisTicker, ReferenceLine
    cashflows.py          ← CashflowArrow, NotionalReservoir, PipeSystem, LockedNotionalExchange,
                            Timeline, PaymentPulse
    valuation.py          ← DiscountArrow, PresentValueBar, FXConversionMorph, MTMBalanceScale
    risk.py               ← CoupledTurbines, DV01Dial, SensitivityBar
    macro.py              ← DollarGravityField, CIPTightrope, BasisEKG, FedSwapValve
    typography.py         ← SceneTitle, InlineDefinition, FormulaPanel, DataLabel, SemanticLegend
```

## Component declaration template

For each component, fill the following. Every field is mandatory. A component is "ready" only when every field is filled.

```markdown
## `<ComponentName>`

**Purpose.** _One sentence: the conceptual role this component plays._

**Semantic role.** _Which doctrine category does this component carry? (registered_metaphor / data_display / typography / structural)._

**Constructor signature.**
```python
ComponentName(
    # required
    semantic_arg_1: <type>,
    semantic_arg_2: <type>,
    # optional, defaults from constants.py
    colour_token: str = "<default>",
    size: tuple[float, float] = (<w>, <h>),
    anchor: Point = ORIGIN,
    # …
)
```

**Required inputs.** _What the component cannot be built without._

**Optional parameters.** _Style overrides; never used to inject magic numbers._

**Default style.** _Where the defaults come from in `constants.py`._

**Animation methods.** _The semantic verbs the component exposes. e.g.:_
- `appear()` — `DrawBorderThenFill` over `default_durations.transition_in_s`
- `set_value(v)` — animates a `ValueTracker`-bound digital readout
- `colour_shift(token)` — `colour_morph` from current to declared token

**Validation constraints.** _Conditions the component refuses to render under._

**Example usage.**
```python
from manim.components.boards import SplitFlapBoard
from manim.constants import LAYOUT, COLOR

board = SplitFlapBoard(
    city_label="NEW YORK",
    currency="USD",
    ticker_value_ref=ticker_value_tracker,
    colour_token=COLOR.USD_AMBER,
    anchor=LAYOUT.BOARD_LEFT,
)
self.play(board.appear(), run_time=1.0)
```
```

## The seed catalogue

The following components are the seed library for institutional / financial videos. Each entry below is a stub; fill the full template above when the component is implemented.

### Boards & tickers

#### `SplitFlapBoard`

**Purpose.** A flip-board-style display showing a city / region label and a ticker value, used to anchor a place-with-a-rate.

**Semantic role.** structural display.

**Required inputs.** `city_label: str`, `currency: str`, `ticker_value_ref: ValueTracker | float`, `anchor: Point`.

**Optional parameters.** `size`, `colour_token`, `font_token`, `chrome_visible`.

**Default style.** From `constants.py`: `BOARD_BACKGROUND = DEEP_BACKGROUND`, `BOARD_BORDER = NEUTRAL_GREY`, `BOARD_LABEL_FONT = MONO_FONT`.

**Animation methods.** `appear()`, `set_ticker(v)`, `colour_shift(token)`, `drift(by_x, by_y)`, `disappear()`.

**Validation constraints.** Refuses to render if `currency` is not in `{USD, EUR, GBP, JPY, CHF, EUR_USD_via_basis, …}` declared in `constants.CURRENCY_REGISTRY`. Refuses to render if `colour_token` is `BASIS_RED` and `currency` is not the anomaly carrier.

---

#### `BasisTicker`

**Purpose.** A high-precision digital ticker for a basis value with units in bps; the value reads in real time off a `ValueTracker`.

**Semantic role.** declarative anomaly value.

**Required inputs.** `data_id: str` (must resolve in data manifest), `anchor: Point`.

**Optional parameters.** `units` (default `bps`), `digits` (default 3), `colour_token` (default `BASIS_RED` for negative values, `WHITE` for non-negative — auto-resolved per frame).

**Animation methods.** `appear()`, `bind_to(tracker)`, `flash_when_crosses(threshold)`.

---

#### `GhostTimeSeries`

**Purpose.** A desaturated curve in the background showing a historical series, used for foreshadowing.

**Required inputs.** `data_id: str`, `colour_token`, `opacity`.

**Animation methods.** `appear()`, `colour_morph_segment(start_idx, end_idx, token)`, `bring_to_foreground()`.

---

#### `ReferenceLine`

**Purpose.** A baseline against which deviation is measured (e.g. zero line for basis).

**Semantic role.** invariant structural.

---

### Cashflows

#### `CashflowArrow`

**Purpose.** A directed flow arrow whose length is proportional to the cashflow magnitude and whose colour is the currency token.

**Required inputs.** `currency: str`, `magnitude: float`, `from_point: Point`, `to_point: Point`.

**Animation methods.** `flow(duration)`, `morph_to(other_arrow)`.

---

#### `NotionalReservoir`

**Purpose.** A pooled-capacity visualisation for a notional principal — a reservoir whose level represents the principal at a given time.

---

#### `PipeSystem`

**Purpose.** Linked pipes connecting reservoirs, carrying particles of `CashflowArrow` semantics; the registered metaphor for cashflow streams.

---

#### `LockedNotionalExchange`

**Purpose.** The mechanical-lock metaphor for fixed notional re-exchange — two principals snap together at the start, are held locked, and re-exchange at maturity.

**Semantic role.** registered_metaphor (mechanical lock).

---

#### `Timeline`

**Purpose.** A horizontal axis with ticks at coupon dates, anchored to the bottom safe area; the canonical structural element for any scene that depicts time.

---

#### `PaymentPulse`

**Purpose.** A pulse that travels from one point to another along a path, representing the discrete arrival of a coupon. Used in conjunction with `Timeline`.

---

### Valuation

#### `DiscountArrow`

**Purpose.** The shrinking-arrow metaphor for discounting to present value — an arrow that arrives at present time shorter than the cashflow that produced it.

**Semantic role.** registered_metaphor (discounting).

---

#### `PresentValueBar`

**Purpose.** A vertical bar whose height is the present value of a leg; the registered metaphor for PV.

---

#### `FXConversionMorph`

**Purpose.** A morph animation that takes a USD bar through the FX spot rate and emerges as an EUR bar (or vice versa).

---

#### `MTMBalanceScale`

**Purpose.** A two-pan balance whose left and right pans show the EUR and USD PV bars; tips left or right to indicate net MTM sign.

---

### Risk

#### `CoupledTurbines`

**Purpose.** Two turbines spinning in opposite directions, representing offsetting DV01 sensitivities on the two legs of a CCS.

**Semantic role.** registered_metaphor (coupled turbines).

---

#### `DV01Dial`

**Purpose.** A circular dial showing the current DV01 value, with the needle moving as the shock is applied.

---

#### `SensitivityBar`

**Purpose.** A horizontal bar whose length represents a sensitivity; oriented to make the sign convention legible.

---

### Macro

#### `DollarGravityField`

**Purpose.** A field of small arrows pointing toward USD assets, visualising global dollar funding pressure.

**Semantic role.** registered_metaphor (gravity field).

---

#### `CIPTightrope`

**Purpose.** A taut cable between two reference points representing the CIP equilibrium; small deviations from the cable's line represent basis.

**Semantic role.** registered_metaphor (tightrope / cable).

---

#### `BasisEKG`

**Purpose.** A time-indexed waveform display of the basis, styled like an electrocardiogram; the registered metaphor for the basis as a systemic stress signal.

**Semantic role.** registered_metaphor (EKG).

---

#### `FedSwapValve`

**Purpose.** A valve in the `DollarGravityField` that, when opened, releases USD into the field — the registered metaphor for central bank swap line intervention.

**Semantic role.** registered_metaphor (valve).

---

### Typography & supporting

#### `SceneTitle`

**Purpose.** The canonical scene-title typographic register; one-line, large weight, anchored top-left.

#### `InlineDefinition`

**Purpose.** The `<term> — <8–15 word definition>` register; appears next to its first-mention object and is held while the term is voiced.

#### `FormulaPanel`

**Purpose.** A TeX-rendered formula container that supports token-level colour and `TransformMatchingTex` between forms.

#### `DataLabel`

**Purpose.** A short numeric label attached to a visual object, anchored relative to the object, in `MONO_FONT`.

#### `SemanticLegend`

**Purpose.** A small key panel that names the palette tokens in use in a given scene; appears once per scene if needed.

---

## When to propose a new component

If a shot in `09_animation_spec.yaml` references a component that is not in this library, the implementer **must not** improvise it inline. Either:

1. **Propose it.** Open a new component entry in this file with all fields drafted. Coordinate with the component_architect role to get the signature reviewed. Implement the component under `manim/components/<category>.py`. Use it in the scene file once it exists.
2. **Refactor the spec.** If the new component is exotic enough that it deserves a different metaphor, raise it through the `07_registered_metaphors.md` approval procedure first.

The library grows; it never grows by accident.
