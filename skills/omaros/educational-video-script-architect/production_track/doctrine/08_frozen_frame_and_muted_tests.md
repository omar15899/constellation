# 08 — Frozen-Frame and Muted Tests

## The rules

Every important shot must answer:

1. **Frozen-frame test.** *If the animation were paused at the key moment, would the frame still communicate the intended concept?*
2. **Muted test.** *If the narration were removed, what should the viewer still infer? Is that inference correct?*

A shot that fails either test is decoration, not explanation.

## Why these two tests

The narration carries prose. The animation carries structure. The two are redundant on purpose — but each must work on its own.

- If the **muted test** fails, the visual is parasitic on the voice. The medium is wasted: a podcast with pictures rather than an animated explanation.
- If the **frozen-frame test** fails, the animation has no resting state where the viewer's understanding can consolidate. The viewer is being swept along by motion without ever being shown a structure.

A great animation passes both. The voice gives the *story* of the concept; a still from the climax frame would work as a publication-quality figure even with no caption.

## How to apply the tests at spec time

The animation spec template includes two mandatory fields:

```yaml
frozen_frame_test:
  key_moment_time: 00:02:15.4   # the moment of maximum conceptual weight
  what_a_viewer_should_infer: |
    The basis curve has crossed below zero into a regime where USD funding via
    EUR is more expensive than via USD itself. The two boards have separated.
    The right board is highlighted in BASIS_RED. The dotted reference line at
    zero is the baseline against which deviation is measured.
  acceptable_inference_drift: |
    A viewer at the target tier may not yet know the *name* "basis" or *why*
    it deviates. They should infer that something has gone wrong with parity.

muted_test:
  what_carries_without_voice: |
    The opening of the gap. The progression from baseline (boards aligned) to
    divergence. The semantic colour shift from neutral to BASIS_RED.
  what_does_not_carry_without_voice: |
    The institutional context (who is doing what), the historical date, the
    eventual interpretation. These are the narration's job.
  acceptable: yes
```

Both fields are filled by the visual director at spec time. The render_review agent checks them against the finished render.

## Pedagogical boundary cases

Boundary shots — pure transitions, scene starts that exist mostly to establish a frame, retrieval pauses — are permitted to fail the muted test on their own. They cannot be expected to carry meaning in isolation; they are connective tissue. But they must still pass the frozen-frame test, because a still must look like a deliberate frame, not a screen-saver.

The exemption is granted by setting `muted_test_exempt: true` in the spec with a justification.

## What a passing frozen frame looks like

A passing frozen frame, in this medium, looks like a publication-quality figure. It has:

- A clear focal point (one object the eye lands on first).
- Axes, labels, or other anchors that locate the focal point in conceptual space.
- A composition that uses the canvas — objects positioned with intent, not centred-by-default.
- Semantic colour discipline (the palette is doing its job — see `03_semantic_visual_language.md`).
- No clutter (the visual economy doctrine is honoured — see `05_visual_economy.md`).

A failing frozen frame looks like:

- A blurred motion mid-transition with no resting state.
- A frame with too many objects, none of which is the focal point.
- A frame that needs the previous 2 seconds of motion to make sense.
- A title card or section divider parading as content.

## What a passing muted test looks like

A passing muted test is the strongest evidence that the animation is doing pedagogical work. It means that the *structure* of the explanation lives in the visual — that the voice is decorating an already-coherent diagram, not carrying the only coherent thread.

The test you can imagine: hand the muted video to a target-tier viewer and ask "what is this about?" If they get the dominant structural fact of the scene (something is diverging, something is locking together, something is being annihilated by its complement) — even without the precise *name* — the test passes.

## Validation

The render_review agent applies both tests at the validation stage. For frozen-frame, it extracts the frame at the declared `key_moment_time` and evaluates whether the inference described in the spec holds (see `12_render_validation_rubric.md` — cinematic and pedagogical axes). For muted, it imagines (or, in a fuller pipeline, performs) the silent playback and evaluates whether the structural inference holds.

If either test fails and the spec did not declare an exemption, the shot is rejected for revision. The fix is at the spec layer (more deliberate composition, more semantic motion) or at the storyboard layer (this shot may need to be split into two), not at the implementation layer.
