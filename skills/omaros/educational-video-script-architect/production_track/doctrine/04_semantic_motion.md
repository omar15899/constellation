# 04 — Semantic Motion

## The rule

**Every movement corresponds to a meaning. Motion is never decoration.**

If you cannot answer "what does this motion *mean*?" — what concept, relation, or change it encodes — the motion should not happen.

## The semantic motion vocabulary

Every animated transition must map to exactly one of:

| Motion semantic | Visual realisation (typical) |
|---|---|
| `flow` | a directed path traversal (cashflow river, particle along a tube) |
| `transformation` | a morph from form A to form B with shared identity (`Transform`, `ReplacementTransform`) |
| `accumulation` | a quantity growing over time (bar height, integral fill, counter) |
| `comparison` | two objects positioned to make difference visible (side-by-side, overlaid) |
| `revelation` | an object that was hidden becoming visible (`DrawBorderThenFill`, `Create`) |
| `cancellation` | two objects of opposite sign annihilating to invariant |
| `constraint` | an object being held within a region (anchored line, locked pair) |
| `stress` | deviation from a baseline becoming visible (curve bulging, indicator dropping into a red zone) |
| `convergence` | two trajectories approaching one point |
| `divergence` | two trajectories separating |
| `zooming out of conceptual scale` | the frame widening to reveal a larger structure |
| `focusing into conceptual detail` | the frame narrowing to one element |

A motion that does not fit one of these is either (a) genuinely missing from the vocabulary and needs a registered addition in `04_visual_language.md`, or (b) decorative and should be removed.

## FadeIn is not the default

`FadeIn` is acceptable only when the visual meaning is *"appearing as a new object of attention"*. That is a real semantic — for example, when a definition box drops in at the moment its term is voiced. But it is the **rarest** appropriate primitive, not the default.

For structural objects (anything with internal geometry — bars, boards, formulas, diagrams), prefer:

- `DrawBorderThenFill` — for "this shape is being constructed before your eyes"
- `Create` — for "this object is coming into being via its definition"
- `TransformMatchingTex` / `ReplacementTransform` — for "this formula evolves" or "this object becomes that object"
- `MoveAlongPath` — for `flow` semantics, especially cashflow / particle paths
- `GrowArrow` — for `revelation` of a vector
- `Indicate` / `Circumscribe` — for "look here, this is the thing"
- `LaggedStart` / `Succession` — when multiple components reveal in a meaningful sequence
- `AnimationGroup` — when several motions are semantically simultaneous
- `ValueTracker`-driven updates — for any continuously changing numerical quantity (the bar that grows with a parameter, the ticker whose digits roll)

`ValueTracker` is the cleanest way to enforce *continuous parametric motion*, which is the primary vehicle for mathematical understanding in this medium (see the existing skill doctrine in `style/visual_creativity_protocol.md`). If a quantity is changing during a shot, it is almost always wrong to express that as a discrete `Transform` from one number to another. Bind it to a `ValueTracker` and the rest of the diagram updates as the tracker advances.

## Rejection conditions for motion

The render_review agent rejects a shot if:

- The shot uses `FadeIn` for structural objects when a constructive primitive (`DrawBorderThenFill`, `Create`) would carry semantic meaning.
- Every motion in the shot is the same primitive (a sign that the spec was missing easing / motion design).
- Motion happens without a corresponding semantic in the vocabulary above.
- A "transition" is present that has no source-of-truth meaning — e.g., the screen wipes between two unrelated shots just because a wipe was the default.
- Multiple simultaneous motions happen without an `AnimationGroup` or `LaggedStart` rationale — the spec should make explicit when synchronicity matters.

## Easing as semantic

Easing curves carry meaning too. A small set of canonical easings, declared in `04_visual_language.md` and bound in `manim/constants.py`:

- `linear` — physical processes that have no inherent acceleration (e.g., a sweep across a uniformly parameterised axis).
- `ease_in_out` — most "graceful" transitions where the eye should track the motion (the default for `flow`).
- `ease_out` — for `revelation`: the motion lands with finality.
- `ease_in` — for `divergence` after a quiescent state: the gap opens decisively.
- `spring` / overshoot — reserve for moments of structural surprise; use sparingly.

The animation spec resolves easing per keyframe. The implementer reads it and does not re-pick easings.

## Why this matters

A shot with thoughtful motion communicates the *kinematics* of the concept — what is acting on what, what is preserved, what is changing. A shot with arbitrary motion communicates only that the producer used a video editor. The viewer cannot distinguish "this transition matters" from "this transition was the default" if every transition is the same primitive.

The cumulative effect, across hundreds of shots, is the difference between an explanation the viewer can *follow* and a sequence of clips they *watch*.
