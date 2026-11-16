# 14 — Failure Behaviour

## The rule

**When the spec is incomplete or contradictory, the agent reports — it never invents.**

The five failure modes below are the only legitimate outputs when full execution is not possible. Each is a *named* state the agent enters, with a defined shape.

## The five failure modes

| Mode | When |
|---|---|
| `COMPLETE_SPEC` | The agent has produced (or possesses) a fully specified artefact. This is the normal success state. |
| `PARTIAL_SPEC_WITH_ASSUMPTIONS` | The agent has produced an artefact but had to fill low-risk gaps with explicitly-labelled assumptions. Each assumption is listed. |
| `MISSING_SPEC_REPORT` | The agent cannot proceed because one or more high-risk fields are undefined. A `MISSING_SPEC:` block is emitted (format below) and the agent stops. |
| `CONTRADICTION_REPORT` | The agent has detected that two layers of the spec disagree (e.g., narration timing vs animation duration). It names the contradiction and stops. |
| `NEEDS_HUMAN_REVIEW` | The agent has detected a high-leverage decision that exceeds its authority (e.g., a new metaphor proposal, a sign-convention conflict). It records the decision and stops. |

## The `MISSING_SPEC:` block

When emitting a `MISSING_SPEC_REPORT`, use exactly this shape, one entry per missing field:

```yaml
MISSING_SPEC:
  - field: shot.IP-S0-F02.objects.right_board.position.x
    why_needed: |
      Required to render the SplitFlapBoard for Frankfurt. Without it,
      the implementer cannot decide whether the boards are arranged
      vertically, side-by-side, or with the right board offset.
    proposed_default: 4.5    # canvas units, mirrored to the left board at -4.5
    risk_if_invented: medium # composition affects the muted test
    requires_human_review: false
  - field: shot.IP-S0-F02.basis_cip.basis_sign_convention
    why_needed: |
      Required to decide whether a "negative basis" should appear as
      BASIS_RED above or below the zero line. Wrong choice teaches
      the inverted convention.
    proposed_default: null   # no safe default — this is the financial convention
    risk_if_invented: high
    requires_human_review: true
```

## Low-risk vs high-risk fields

A field is **low-risk** if a wrong default fails gracefully — the render still parses, the spec layer can correct on review, the viewer would not learn a misconception from the default. Examples:

- font weight, when every other font in the shot has the same weight
- minor padding between two co-located labels
- whether `LaggedStart` or `Succession` is used for two sequential reveals

A field is **high-risk** if a wrong default fails catastrophically — the viewer leaves with a wrong intuition, the convention is inverted, the metaphor is fabricated. Examples:

- any colour choice
- any sign convention (basis, DV01, perspective)
- any numerical value that will be visible on screen
- any new metaphor
- any composition choice that decides the dominant focal point of a high-leverage frame (cold open, climax, essence)
- any deviation from the registered metaphor catalogue

The agent **may** proceed with a labelled assumption when the missing field is low-risk. It **must** stop and report when the missing field is high-risk.

## What "labelled assumption" means

When proceeding under `PARTIAL_SPEC_WITH_ASSUMPTIONS`, the agent records every assumption in the artefact:

```yaml
assumptions:
  - field: shot.IP-S0-F02.objects.right_board.font_weight
    chosen: medium
    rationale: |
      Every other label in the shot uses medium weight; default to consistency.
    risk: low
    requires_review: false
  - field: shot.IP-S0-F02.animation.basis_widening.easing
    chosen: ease_out_cubic
    rationale: |
      Visual language §"easing palette" lists ease_out_cubic as the default
      for divergence motions. Applied here as the default.
    risk: low
    requires_review: false
```

These appear in the spec file itself, not in a sidecar. The render_review agent reads them.

## The `CONTRADICTION_REPORT`

When two layers of the stack disagree, the agent does not pick a winner silently. It names both:

```yaml
CONTRADICTION:
  shot_id: IP-S2-F03
  layer_A:
    file: 05_narration_script.md
    location: row R042
    states: "the basis closes back to zero by 2023"
  layer_B:
    file: 10b_data_manifest.yaml
    location: basis_history_2019_to_2024
    states: "basis values for 2023 are in the range [-18, -12] bps; never reach zero"
  contradiction: |
    The narration claims a return to zero; the data manifest's basis series
    does not contain a zero crossing in 2023.
  proposed_resolutions:
    - update narration to match data ("by 2023 the basis had narrowed but not closed")
    - update data manifest if the narration is informed by a different source
    - introduce a "stylized" classification in the data and label the shot accordingly
  blocking: yes
```

The agent stops at this artefact and waits for the contradiction to be resolved.

## `NEEDS_HUMAN_REVIEW`

Used when the decision is within the agent's role but exceeds its authority. Examples:

- The visual director is asked to introduce a metaphor not in the registered catalogue. They draft the proposal under `07_registered_metaphors.md`'s approval format but tag it `NEEDS_HUMAN_REVIEW`.
- The animation_spec agent encounters a high-leverage frame (cold open, climax, essence) and notes that the spec is complete but the cumulative composition demands human sign-off before implementation.

`NEEDS_HUMAN_REVIEW` is not a failure — it is a *checkpoint*. The agent has done its work; the next step is human.

## Why the discipline

Without these named failure modes, the agent's only path forward when blocked is to *invent*. Inventing is silent; it pollutes the spec with decisions whose authority is opaque. By contrast, a named failure mode is a public record: this is what the agent did not know, this is what it proposes, this is why it stopped. It is reviewable.

The render_review agent treats any artefact lacking explicit `assumptions:` or `MISSING_SPEC:` entries — but produced under ambiguity — as suspect. The audit trail is part of the deliverable.
