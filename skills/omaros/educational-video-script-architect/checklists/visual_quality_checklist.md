# Visual Quality Checklist

Run during §11. **PASS / NOTE / FAIL** with a short reason.

## Visual grammar consistency

- [ ] Colour semantics declared in §5 are honoured throughout the video. The colour for "invariant object" never accidentally tags an "approximation".
- [ ] Typography is consistent — no font drift between scenes, no untitled mixing of math fonts.
- [ ] The notation style (indices, vectors, operators, sets, measures) is consistent across all formulas.
- [ ] Definitions, examples, and abstractions enter and exit the screen using their declared visual conventions.

## Continuity

- [ ] Whenever possible, an object from one scene morphs into an object in the next, rather than cutting to an unrelated visual.
- [ ] Object permanence is preserved: an object's identity (colour, shape, position memory) survives transformation.
- [ ] No scene starts cold — each opens with a visual hand-off from the previous scene's closing frame, unless a hard cut is pedagogically justified.

## Dynamism

- [ ] No scene consists primarily of bullet points appearing in sequence.
- [ ] Transformations are animated (morphs), not cut-and-replaced, when the transformation is conceptually meaningful.
- [ ] Limits are shown as sequences stabilizing.
- [ ] Approximations are shown as coarse objects refining toward a target.
- [ ] Local-to-global arguments use zoom or refinement, not text labels.
- [ ] Equivalence is shown as a reversible morphism (often a double-headed arrow or a back-and-forth animation).
- [ ] Invariance is shown by changing the representation while the underlying object holds still.

## Density and breathing room

- [ ] Each definition has a 1–2 s pause after it appears for the viewer to absorb it.
- [ ] No frame contains more than ~7 distinct visual elements competing for attention.
- [ ] Decorative ornament is minimal; every visible element earns its place.
- [ ] Background is not noisy; it does not compete with the foreground.

## Camera

- [ ] The camera is static unless a push, pull, pan, or zoom serves a conceptual function (emphasis, locality, refinement).
- [ ] Camera moves are slow enough to read; no jerky cuts during conceptually dense moments.
- [ ] In 3D scenes, camera orientation is specified for every shot.

## Object–representation distinction

- [ ] When a representation (coordinate chart, sample path, histogram) is shown alongside the invariant object (manifold, process, distribution), the visual distinction is clear.
- [ ] When the representation is meant to fade and the invariant object remains, this is animated explicitly rather than narrated abstractly.

## Notation handling

- [ ] Every formula on screen is intentional. There is no "wallpaper math".
- [ ] Subexpression highlights (colour, underline) are used to direct attention precisely.
- [ ] When a formula transforms (substitutions, simplifications), the transform is animated (`TransformMatchingTex`-equivalent), not cut.

## Asset coordination

- [ ] Generative-video clips contain no formal symbolic content the viewer must read precisely.
- [ ] Storyboard reference frames are not mistaken for production assets.
- [ ] Every imported image / clip has a defined role and a defined exit moment.
- [ ] Compositing layers (when modalities are mixed) are explicitly ordered in §7.

## Visual–audio synchronization

- [ ] Every important visual event has a corresponding voice-over moment within ±0.3 s.
- [ ] Sound design cues (definition appears, abstraction lifts) are declared in §7.
- [ ] No long audio silence over visual activity, no long visual stillness over audio activity, unless deliberate.

## Final-product test

- [ ] If the audio were muted, a knowledgeable viewer could infer the conceptual progression from the visuals alone.
- [ ] If the visuals were hidden, the voice-over still reads as a coherent explanation (necessary but not sufficient).
- [ ] The video looks like it belongs to a single coherent visual identity, not a collage of clips.
