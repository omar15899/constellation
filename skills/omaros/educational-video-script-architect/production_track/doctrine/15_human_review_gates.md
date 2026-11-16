# 15 — Human Review Gates

## The rule

**Some frames are high-leverage. They cannot ship without explicit human sign-off.**

The shotlist and the animation spec mark these frames with `human_review_required: true`. The render_review agent flags them, blocks downstream automation, and requires a sign-off before the render is approved.

## The canonical high-leverage frames

A frame is high-leverage if its rendering carries disproportionate weight in the viewer's eventual understanding. The default high-leverage frames in any educational video:

1. **Cold open / opening shot.** Sets the aesthetic, register, and pace of the video. A wrong cold open colours everything that follows.
2. **First definition of the instrument.** The shot in which the central object is named and shown. The viewer's mental model of "what this thing is" begins here.
3. **First complete mechanism diagram.** The first shot where the mechanism is shown in full, with all parts labelled. This becomes the canonical figure the viewer recalls.
4. **First valuation formula.** The shot where the central formula is introduced. The choice of how the formula appears (assembly, morph, colour-matching) determines whether the viewer perceives it as a derivation or a slogan.
5. **Misconception refutation.** Any shot whose explicit purpose is to correct an expected misconception. If the refutation is unclear, the misconception survives the video.
6. **Climax / revelation.** The peak moment of the conceptual arc. Often involves the registered metaphor at full force.
7. **Final essence frame.** The shot where the single-sentence essence is voiced and held. This is the frame the viewer leaves with.

Project-specific frames may be added: a particularly hard derivation step, the moment when two domains are unified, the shot where a sign convention is established for the rest of the video.

## How the gates are recorded

In the shotlist:

```markdown
| Shot ID    | Scene | Time          | Purpose                          | Human review |
|------------|-------|---------------|----------------------------------|--------------|
| IP-S0-F01  | S0    | 00:00–00:08   | Cold open: ghost basis curve     | yes          |
| IP-S0-F02  | S0    | 00:08–00:18   | The basis gap opens              | yes          |
| IP-S1-F03  | S1    | 00:48–01:02   | First definition of CCS          | yes          |
| IP-S3-F05  | S3    | 04:12–04:30   | First complete mechanism diagram | yes          |
| IP-S5-F02  | S5    | 07:08–07:22   | Climax: basis EKG reveal         | yes          |
| IP-S6-F04  | S6    | 09:40–10:00   | Essence frame                    | yes          |
```

In the animation spec for those shots:

```yaml
shot_id: IP-S0-F02
human_review_required: true
human_review_checklist:
  - The cold-open ghost curve identity matches the data manifest's basis_history_2019_to_2024 array (no resampling, no smoothing).
  - The right-board basis ticker reaches exactly -30 bps at t=00:13.4 (declared time-in-shot for the climax of this shot).
  - The colour transition NEUTRAL_GREY → BASIS_RED occurs only on the negative excursion segment, not on the whole curve.
  - The composition's dominant focal point is the basis ticker, not the boards as a whole.
  - The frozen-frame test passes at t=00:13.4 — a still must communicate "two places, one measure, divergence" to a target-tier viewer.
  - The muted test passes — the colour shift and the gap opening must carry the structural fact without the voice.
human_reviewer:
  name: <pending>
  decision: <pending>            # approved | revisions_requested | rejected
  decision_timestamp: <pending>
  notes: <pending>
```

## What the reviewer is checking

Not the *render quality* in a generic sense — the render_review agent's rubric handles that. The human reviewer checks the things that require human judgement:

- **Is the explanation correct on the conceptual layer?** Does the metaphor actually map the concept faithfully? Is the sign convention the one we want to teach?
- **Does the cold open earn its weight?** Will a target-tier viewer find the opening *engaging* and *legible* — not flashy, not flat?
- **Is the essence statement the right essence?** Does the voiced line, paired with the held frame, capture the categorical kernel of the concept, or has it drifted to a slogan?
- **Is the climax actually a climax?** Does the moment feel earned by the preceding shots, or does it land flat because the arc was not built?

These are the questions Claude cannot answer reliably without a human to confirm.

## The gating discipline

When a shot is marked `human_review_required: true`:

- The animation_spec agent does not finalise the spec until the conceptual layer (the parts the reviewer cares about) has been signed off.
- The component_architect agent may still scaffold components based on a draft spec, since component design is rarely high-leverage.
- The manim_implementation agent may render a *preview* for the reviewer to evaluate. It does not mark the shot `final` until the `decision` field is `approved`.
- The render_review agent reports any high-leverage shot still at `decision: pending` and refuses to mark the project as complete.

## Why this matters

Most shots in a video are intermediate — they connect, transition, scaffold. The high-leverage shots are different in kind: they *decide* how the viewer remembers the video. Skipping human review on those is the most expensive shortcut in this pipeline. The cost of bad cold opens, drifted essence statements, or off-key climax frames cannot be repaired by improving the surrounding shots — those shots are the surrounding shots' raison d'être.

The gating discipline is the cheap version of the expensive realization-after-shipping. Pay the review cost up front.
