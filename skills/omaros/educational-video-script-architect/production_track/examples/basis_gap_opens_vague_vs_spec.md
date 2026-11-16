# Example — `IP-S0-F02 — The basis gap opens`

A compact worked example to demonstrate the difference between a **vague visual prompt** (the input the skill was historically given, from which AI agents produced under-specified Manim code) and a **production-grade shot specification** (the artefact the production track requires before any code is written).

> **Read this if you are tempted to write Manim code from a sentence.**

## The vague prompt (what NOT to act on directly)

> *Two financial airport-style departure boards side by side on a black background. The left board is New York and the right board is Frankfurt. The right board shows the basis moving to -30 bps.*

The vague prompt is **reference-only** for the visual director. It is **not** authoritative for code generation. An AI agent that reads this and writes Manim immediately is doing one of:

- guessing every position, size, colour, font, easing, persistence rule
- silently choosing whether the basis goes "to -30 bps" instantly, linearly, with overshoot, or via a ValueTracker
- silently choosing whether the colour of the Frankfurt board changes, or whether the basis ticker carries the colour, or whether nothing changes colour
- silently choosing whether the boards have visible tickers showing USD funding rates, or are abstract typographic blocks
- silently choosing whether the ghost time-series exists at all
- silently choosing the synchronization with the (unspecified) voiceover

The result is technically a video. It is not a deliberate explanation.

## The production-grade shot specification (what to act on)

What the **animation_spec_agent** produces and the **manim_implementation_agent** binds to:

```yaml
shot_id: IP-S0-F02
maps_to:
  shotlist_row: 08_shotlist.md#IP-S0-F02
  scene_id: S0_anomaly
  narration_range:
    file: 05_narration_script.md
    rows: ["R004", "R009"]
time_range:
  start_in_video: "00:00:08.4"
  end_in_video:   "00:00:18.1"
  duration_s: 9.7

doctrine_tags: ["HOOK", "INSTANCE", "BOUNDARY"]

cognitive_goal: |
  The viewer registers that "two places, one measure" have diverged into a
  red regime — even before they know the word "basis" or why it deviates.

viewer_should_notice:
  - The basis ticker crosses zero into BASIS_RED.
  - The two boards visibly separate.
  - The ghost curve in the background has the same shape as the ticker
    sweep (foreshadow).

viewer_should_not_notice:
  - The exact -30 bps value.
  - The chrome date "2018-Q4" in the lower third.

composition:
  dominant_focal_point: BasisTicker
  balance: asymmetric_right_heavy
  max_visible_words: 35
  style_reference:
    positive_anchor: "Institutional financial visualisation, Bloomberg Terminal at rest."
    negative_anchor: "Stock-market YouTube intro with floating coins and climbing arrows."

canvas:
  width: 16.0
  height: 9.0
  background_token: DEEP_BACKGROUND

layout:
  named_anchors:
    board_left:    { x: -4.5, y:  1.5 }
    board_right:   { x:  4.5, y:  1.5 }
    zero_line_y:                       0.0
    ticker_center: { x:  4.5, y:  3.6 }
    chrome_date:   { x:  0.0, y: -4.0 }

objects:
  - id: ghost_curve
    component: GhostTimeSeries
    inputs:
      data_id: basis_history_2019_to_2024
      colour_token: NEUTRAL_GREY
      opacity: 0.35
      stroke_width: 1.6
    z_index: 1
    semantic_role: foreshadow_anomaly
    initial_state: { opacity: 0.0 }
    final_state:   { opacity: 0.35 }
    persistence_into_next_shot: ghost_at_0_35
  - id: board_left
    component: SplitFlapBoard
    inputs:
      city_label: "NEW YORK"
      currency: "USD"
      ticker_value_ref: data.usd_funding_rate
      anchor: layout.board_left
      size: { width: 4.2, height: 2.4 }
    z_index: 2
    semantic_role: invariant_left_anchor
    initial_state: { opacity: 0.0, x: layout.board_left.x }
    final_state:   { opacity: 1.0, x: layout.board_left.x }
    persistence_into_next_shot: keep
  - id: board_right
    component: SplitFlapBoard
    inputs:
      city_label: "FRANKFURT"
      currency: "EUR_USD_via_basis"
      ticker_value_ref: data.eur_funding_via_basis
      anchor: layout.board_right
      size: { width: 4.2, height: 2.4 }
    z_index: 2
    semantic_role: anomaly_carrier
    initial_state: { opacity: 0.0, colour_token: EUR_BLUE }
    final_state:   { opacity: 1.0, colour_token: BASIS_RED }
    persistence_into_next_shot: keep
  - id: basis_ticker
    component: BasisTicker
    inputs:
      data_id: basis_history_2019_to_2024
      anchor: layout.ticker_center
      units: bps
      digits: 3
    z_index: 3
    semantic_role: declarative_anomaly_value
    initial_state: { opacity: 0.0, displayed_value: 0 }
    final_state:   { opacity: 1.0, displayed_value: -30 }

text:
  - id: chrome_date
    content: "2018-Q4"
    font: monospace
    colour_token: NEUTRAL_GREY
    anchor: layout.chrome_date
    initial_state: { opacity: 0.0 }
    final_state:   { opacity: 0.6 }

data:
  references_to_manifest:
    - data_id: basis_history_2019_to_2024     # → 10b_data_manifest.yaml
    - data_id: usd_funding_rate
    - data_id: eur_funding_via_basis

animation:
  keyframes:
    - t: 0.0
      action: appear
      object: ghost_curve
      semantic: revelation
      primitive: opacity_morph
      from: { opacity: 0.0 }; to: { opacity: 0.35 }
      duration_s: 0.8
      easing: ease_out_cubic
    - t: 0.8
      action: appear
      object: [board_left]
      semantic: revelation
      primitive: DrawBorderThenFill
      duration_s: 1.0
    - t: 1.0
      action: appear
      object: board_right
      semantic: revelation
      primitive: DrawBorderThenFill
      duration_s: 1.0
    - t: 3.0
      action: appear
      object: basis_ticker
      semantic: revelation
      primitive: opacity_morph
      from: { opacity: 0.0 }; to: { opacity: 1.0 }
      duration_s: 0.6
    - t: 4.0
      action: open_gap
      object: basis_ticker
      semantic: divergence
      primitive: value_tracker_driven
      from: { displayed_value: 0 }; to: { displayed_value: -30 }
      duration_s: 4.2
      easing: ease_in_cubic
    - t: 6.5
      action: colour_shift
      object: board_right
      semantic: stress
      primitive: colour_morph
      from: { colour_token: EUR_BLUE }; to: { colour_token: BASIS_RED }
      duration_s: 1.0
    - t: 8.2
      action: hold
      duration_s: 1.5

synchronization:
  voiceover_cues:
    - cue: "Aquí, Nueva York. Y aquí, Frankfurt."
      time_in_shot_s: 0.8
      exact_visual_cue: board_left.DrawBorderThenFill.end
      allowed_tolerance_s: 0.2
    - cue: "Algo se rompe entre ellos."
      time_in_shot_s: 5.0
      exact_visual_cue: board_right.colour_morph.start
      allowed_tolerance_s: 0.2
    - cue: "Por diseño, no debería ocurrir."
      time_in_shot_s: 8.2
      exact_visual_cue: basis_ticker.displayed_value == -30
      allowed_tolerance_s: 0.2

quality_constraints:
  max_visible_words: 35
  one_focal_point: true
  motion_must_have_semantic: true
  no_FadeIn_for_structural_objects: true
  forbidden_substitutions:
    - swap EUR_BLUE for any non-EUR object
    - swap USD_AMBER for any non-USD object

rejection_conditions:
  inherited_from: production_track/doctrine/10_negative_constraints.md
  exemptions: []

frozen_frame_test:
  key_moment_time_s: 8.2
  what_a_viewer_should_infer: |
    Two places, one measure, divergence into a red regime. Even without
    the name "basis", the viewer infers something has gone wrong with parity.

muted_test:
  what_carries_without_voice: |
    The opening of the gap; the colour shift from neutral / EUR_BLUE to BASIS_RED;
    the drift of the right board.
  acceptable: yes

implementation_notes: |
  Use a ValueTracker for basis_ticker.displayed_value. The colour morph on
  board_right is a callback on the same tracker: when the tracker crosses
  basis_negative_threshold (from data manifest), trigger colour_morph.
  Do not hard-code the threshold in the scene file.

human_review_required: true
human_review_checklist:
  - The ghost curve identity matches data manifest basis_history_2019_to_2024 — no resampling.
  - The basis ticker reaches exactly -30 bps at t=8.2 s.
  - The colour transition occurs only after the threshold crossing.
  - The composition's dominant focal point is the basis ticker, not the boards.
  - Frozen-frame test at t=8.2 s passes.
  - Muted test passes.

assumptions: []
```

## Why this difference matters

| Concern | Vague prompt | Production spec |
|---|---|---|
| Where boards are | "side by side" — implementer guesses | `board_left: (-4.5, 1.5)`, `board_right: (4.5, 1.5)` |
| What colour they are | unspecified | `board_left.USD_AMBER`, `board_right.EUR_BLUE → BASIS_RED` |
| How the basis moves to -30 | "moves to -30 bps" — instant? linear? overshoot? | `ValueTracker`-driven, `ease_in_cubic`, 4.2 s |
| What the basis ticker even is | not mentioned — implementer invents it | `BasisTicker` component, bound to the same `data_id` as the ghost curve, 3-digit precision |
| What is in the background | "black background" | `DEEP_BACKGROUND` + `GhostTimeSeries` of the actual basis history at 35% opacity |
| When colour changes | unspecified | At threshold crossing, derived from `basis_negative_threshold` in the data manifest |
| When the voice and the visual align | unspecified | Three explicit cues with 0.2 s tolerance |
| What this shot is for | a visually-driven hook | declared `cognitive_goal`, registered as `human_review_required`, with checklist |
| Frozen-frame test | undefined | declared at `t=8.2 s` with the precise inference the still must carry |
| Muted test | undefined | declared with what carries and what does not |

The spec is **longer** than the vague prompt because the spec is **doing the work the prompt was hiding**. Length here is not bloat — it is the deferred decisions of the vague prompt, written down so they are reviewable.

## The implementer's view

When the production spec above is the input, the Manim code becomes mechanical orchestration (see `production_track/prompts/manim_implementation_agent.md` for the full scene file shape). The implementer:

- imports palette tokens, fonts, durations, easings from `manim/constants.py`
- instantiates `GhostTimeSeries`, `SplitFlapBoard`, `BasisTicker` from `manim/components/`
- writes `construct()` as a sequence of named methods (`setup_palette`, `create_background`, `create_boards`, `animate_gap_opening`, `hold_final_frame`, `transition_out`)
- has no remaining design decisions

The implementer's code passes the technical and Manim validation axes by construction. The pedagogical, cinematic, and semantic axes are passed by the spec being correct — not by the implementer's intuition.

This is the discipline the production track exists to install.
