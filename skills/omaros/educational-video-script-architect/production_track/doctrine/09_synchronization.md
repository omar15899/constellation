# 09 — Synchronization

## The rule

**Voice-over and visual event must land together within a declared tolerance. Silences are visual events too.**

A spec that does not pin synchronization explicitly is a spec that depends on the implementer's intuition — and intuition is not deterministic.

## Required fields per shot

Each shot's animation spec includes a synchronization block:

```yaml
synchronization:
  voiceover_cues:
    - cue: "por diseño"
      exact_visual_cue: locked_notional.snap_into_place
      time_in_shot: 00:01.8
      allowed_tolerance_seconds: 0.2
    - cue: "el ancla del valor"
      exact_visual_cue: anchor_arrow.indicate
      time_in_shot: 00:03.5
      allowed_tolerance_seconds: 0.2
  silence_policy:
    intervals:
      - from: 00:04.0
        to:   00:05.5
        rationale: retrieval pause — viewer is invited to reconstruct the mechanism
        visual_state: relevant diagram remains visible at 100% opacity; question text held in lower third
  pause_policy:
    during_retrieval_pause: |
      No new conceptual object may be introduced.
      The question must remain visible.
      The relevant diagram must remain visible or ghosted.
      An optional timer may be shown if specified.
      No distracting motion may occur.
      Silence must not be filled by unnecessary animation.
```

## Tolerance discipline

The default tolerance is **±0.2 seconds**. This is tighter than feels necessary but is the threshold at which voice / visual misalignment becomes perceptible. The implementer is responsible for hitting this tolerance; the render_review agent measures it against the rendered timecodes.

If a tolerance must be looser for a specific cue (e.g., a long sustained note where the visual could land anywhere in a 1-second window), the spec must declare it. There is no implicit slack.

## Silence is a visual event

When the narration is silent, the visual cannot be silent in the sense of "lifeless" — it must do whatever the silence is *for*:

- **Retrieval pause.** The visual freezes on the question + the relevant diagram. The viewer's eye has somewhere to land while their working memory does the work. No new conceptual object may be introduced. No distracting motion.
- **Self-explanation pause.** Same as retrieval, but the viewer is invited to reconstruct *why*, not to recall. The diagram remains visible; an optional self-explanation prompt may be displayed.
- **Climax pause.** The voice has just delivered the essence statement. The visual holds on the essence frame (often the formula or the canonical diagram) for the time the line takes to settle in working memory.
- **Transition pause.** The voice is silent between two scenes. The visual either lingers on the outgoing frame or animates the connective tissue.

In all cases, the silence is *specified*. It is not "the voice happens to be quiet here".

## What the implementer does

- The implementer reads the synchronization block alongside the voiceover file (`06_voiceover.md`) and the voice direction (`07_voice_direction.md`).
- Manim's `play` calls have explicit `run_time` parameters. The implementer chooses them so the visual cue lands at the declared `time_in_shot` within tolerance.
- For continuous quantities driven by `ValueTracker`, the tracker's animation duration is set from the spec, not inferred.
- For waiting between events, the implementer uses `self.wait(duration)` with the duration declared in the spec — not a "feels right" default.

## What the render_review agent checks

- Every voiceover cue declared in the spec is matched by a visible visual event at the rendered timecode, within tolerance.
- No new conceptual object appears during a declared silence interval.
- The question / prompt / diagram declared as visible during a pause is in fact visible.
- The visual state during a pause matches the `visual_state` description in the spec.
- The shot's total duration matches the spec's `duration` field within a tight tolerance (≤0.5 s).

## Why this matters

The viewer's working memory is the constraint that all of this protects. Cognitive-load research (see `learning_research/04_cognitive_load_and_worked_examples/`) is consistent on this point: split attention costs comprehension. When the voice says "the basis gap opens" 1.2 seconds before the gap visibly opens (or after — the asymmetry is mild), the viewer spends some of their working memory reconciling the two timelines. They do not absorb the concept; they absorb a misalignment.

Tight synchronization is not aesthetic finesse — it is the elimination of a known cognitive tax.
