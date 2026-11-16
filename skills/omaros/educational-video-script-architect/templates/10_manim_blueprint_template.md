# Manim Blueprint Template

Use when any portion of the video will be implemented in Manim (Community Edition or 3b1b). The blueprint is a *plan*, not full code, unless the user requests code.

---

## Manim setup assumptions

- Manim Community ≥ 0.18 (default), unless the user names another implementation.
- Resolution: 1920×1080 @ 60 fps unless otherwise specified.
- Render quality: `-qh` for previews, `-qk` for final.
- LaTeX: standard `MathTex` with `amsmath`, `amssymb`. Note any custom preamble.

State any deviations explicitly.

## Scene class plan

| Scene class | Covers timestamps | Inherits from | Notes |
| --- | --- | --- | --- |
| `IntroScene` | 0:00–0:25 | `Scene` | static frame, simple `FadeIn` |
| `MotivationScene` | 0:25–1:30 | `MovingCameraScene` | uses camera frame zoom |
| `DefinitionScene` | 1:30–2:45 | `Scene` | LaTeX-heavy |
| `ManifoldScene` | 2:45–4:30 | `ThreeDScene` | needs 3D camera, `set_camera_orientation` |
| `AbstractionScene` | 4:30–5:30 | `Scene` | morph between sibling examples |

## Object inventory

For each non-trivial Manim object, specify:

- Identifier (variable name in code)
- Type (`Mobject`, `MathTex`, `Surface`, `Axes`, `NumberPlane`, `VGroup`, custom)
- Construction parameters (size, colour, position)
- First appearance timestamp
- Last appearance / fade-out timestamp
- Transformations applied during the video

Example:

```
manifold_M  : ParametricSurface(u_range=[-2,2], v_range=[-2,2], …)
              colour: TEAL_E
              first appears 2:45
              transformed at 3:20 into manifold_M.copy().shift(LEFT*2) overlapped with chart_phi
chart_phi   : NumberPlane(x_range=[-2,2,1], y_range=[-2,2,1])
              colour: GOLD_C with stroke_opacity 0.5
              first appears 3:05
              attached as overlay onto manifold_M at 3:20 via transform_to_surface()
```

## Coordinate systems

List all axes / planes / 3D frames used. Specify `x_range`, `y_range`, `z_range`, axis labels, tick density, units. For 3D scenes, specify camera orientation (`phi`, `theta`, `gamma`, `zoom`, `frame_center`).

## Equations and labels

For every formula displayed:

- Source LaTeX
- Variant (e.g., `MathTex`, `Tex`, `Title`)
- Position
- Substring/index map for partial highlights (`SetColor` on specific subexpressions)
- Animations applied (`Write`, `FadeIn`, `TransformMatchingTex`, `ReplacementTransform`)
- Substitutions over time (e.g., generic → specific values)

Example:

```
eq_def : MathTex(r"f(x) = \int_a^b k(x,y)\,d\mu(y)")
         position: ORIGIN, then move_to(UP*2.5) at 2:10
         indices for highlight: {0..3 = "f(x)", 4..5 = "=", 6..14 = integral op}
         transform at 2:30 into eq_special with TransformMatchingTex
```

## Animation primitives used

List the high-level animations the script depends on:

- `FadeIn`, `FadeOut`, `Write`, `Unwrite`
- `Create`, `Uncreate`, `DrawBorderThenFill`
- `Transform`, `ReplacementTransform`, `TransformMatchingTex`, `TransformMatchingShapes`
- `MoveAlongPath`, `Rotating`, `Rotate`
- `Indicate`, `Flash`, `Wiggle`, `FocusOn`, `ShowPassingFlash`
- `MoveCamera`, `set_camera_orientation`, `begin_ambient_camera_rotation`
- Custom `UpdateFromAlphaFunc`, value-tracker driven updaters

Where standard primitives are insufficient (e.g., morphing a probability cloud), describe the custom animation conceptually.

## Camera motions

Per scene, specify:

- Start and end camera positions / frame
- Push / pull / pan / zoom timing (start ts, duration, easing)
- Whether the camera is locked, slow-drifting, or interactive

## Reusable helper functions

Anything that should be factored out:

```
def discounted_payoff_arrow(payoff: Mobject, rate: float) -> VGroup: ...
def coordinate_chart_overlay(surface: Surface, region: tuple) -> VGroup: ...
def fade_representation_keep_object(rep: VMobject, obj: VMobject) -> Animation: ...
```

These are signatures + one-line descriptions, not implementations.

## Pure-Manim vs imported assets

- **Pure Manim:** equations, geometric primitives, plots, axis-aligned diagrams, formal notation.
- **Imported reference frames:** photographs, cinematic backdrops, hand-drawn metaphors, AI-generated reference frames (loaded via `ImageMobject`).
- **Imported clips:** generative-video B-roll loaded via `ffmpeg` as a video texture or composited in post-production.

Mark each scene as `pure-manim`, `manim+image`, `manim+video`, or `pure-external-with-manim-overlay`.

## Performance considerations

- Long renders: any scene with parametric surfaces, dense particle systems, or many simultaneous transforms — flag with an estimated render time class (`fast` < 30 s/min; `medium` 30 s – 2 min/min; `slow` > 2 min/min).
- Memory: large particle systems, high-res 3D meshes.
- LaTeX compile cost: many distinct `MathTex` objects → consider caching or reuse.
- Recommend partial-render checkpoints for the implementer (`-s` for last frame, `-n start,end` for ranges).

## Open questions for the implementer

If there are choices the implementer must make (e.g., whether to use `Surface` vs `ParametricSurface`, or whether a custom updater is acceptable), list them explicitly. Don't bury them in prose.
