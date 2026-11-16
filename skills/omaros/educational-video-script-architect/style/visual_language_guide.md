# Visual Language Guide

The video has a single coherent visual identity. Pick a language and hold it. Inconsistency reads as carelessness; consistency reads as authority.

## Default OmarOS visual language

Use this as the baseline unless the user asks for something else, or unless the topic justifies a different palette.

### Background

- Deep matte black or near-black (`#0a0a0c` to `#101116`).
- Optional very subtle vertical gradient (no banding).
- Optional faint volumetric glow at the centre to focus attention; never enough to read as "spotlight".
- No textures, no noise, no decorative geometry.

### Palette and semantics

Each colour carries a fixed meaning across the whole video. Pick from this default mapping or override consistently.

| Colour (hex) | Manim constant | Default semantic role |
| --- | --- | --- |
| `#5BC0BE` (teal) | `TEAL_C` | the invariant object (the manifold, the process, the linear map) |
| `#F2C94C` (amber) | `GOLD_C` | a chosen representation (chart, sample path, basis, payoff) |
| `#EB5757` (magenta-red) | `RED_C` | error, approximation, deviation from the target |
| `#FFFFFF` (white) | `WHITE` | formal definition / theorem statement |
| `#9B9B9B` (mid grey) | `GREY_B` | scaffolding, axes, secondary structure |
| `#56CCF2` (cyan) | `BLUE_C` | inputs / domains |
| `#BB86FC` (lavender) | `PURPLE_B` | outputs / codomains |
| `#27AE60` (green) | `GREEN_C` | "this works" / "this preserves the structure" |

When two colours appear together (object + representation, input + output), keep their relative roles consistent across all scenes.

### Typography

- **Body text:** Inter or Helvetica Neue, weight 400; size scales with composition (start ~36 pt at 1080p).
- **Section title:** same font, weight 600 or 700.
- **Mathematical text:** Computer Modern via LaTeX (`MathTex` in Manim). Do not mix math fonts.
- **Code:** JetBrains Mono or Fira Code at the same body size.

### Notation conventions

- Vectors: bold lowercase Roman, $\mathbf{x}$.
- Sets / spaces: blackboard bold or calligraphic, $\mathbb{R}$, $\mathcal{F}$.
- Operators: upright Roman, $\mathrm{Var}$, $\mathrm{tr}$.
- Differentials: italic $d$ for plain differentials ($dx$), upright $\mathrm{d}$ for measure ($\mathrm{d}\mu$). Pick one and hold.
- Indices: subscripts for components, superscripts for tensor / iteration index. Where Einstein summation is used, declare it explicitly.

## Animation richness doctrine

**The default is motion, not appearance.** Every conceptual beat in the video has something continuously transforming — a parameter sweeping, a curve being traced, a field evolving, a space deforming. An object that simply fades in and sits there is a slide. It does not teach.

The key questions for each scene:
- What is the parameter or quantity that drives change?
- What changes as that parameter varies?
- What stays invariant?
- How do I make both the change and the invariant visible simultaneously?

Answer these before writing a single row in the narration script.

## How elements appear and disappear

Every visual element has a defined entry and exit. No "just appears" — entries are an animation, even if subtle. But more importantly: entry is not the main event. The main event is what the element **does** while it is on screen.

| Element | Entry | Active behaviour | Exit |
| --- | --- | --- | --- |
| Definition (white box) | `Write` over 1.0 s, 1.5 s pause | stays in corner while examples animate alongside it | `FadeOut` over 0.6 s when superseded |
| Example / instance | `FadeIn` or `Create` over 0.5–1.0 s | object transforms, traces, deforms — something moves | `FadeOut` over 0.5 s |
| Geometric object | `Create` along its boundary over 0.8–1.5 s | undergoes continuous transformation (morph, rotate, deform, trace) | `FadeOut` or morphs into next object |
| Parametric curve | traces itself via `ParametricFunction` with `t` advancing | continues tracing or holds with label updating | fades or morphs to next representation |
| Arrow / dependence | `GrowArrow` in direction of causation | can pulse (`ShowPassingFlash`) to show information flow | `FadeOut` over 0.4 s |
| Annotation / label | `Write` over 0.4 s, tracking its anchor | follows its anchor with `.add_updater` | dies with anchor |
| Formula | `Write` over 0.8–1.2 s | subexpressions may highlight or transform (`TransformMatchingTex`) | `FadeOut` or transforms into specialised form |

## Visual representation of conceptual moves

These are motion recipes. Use them when the concept in the table below appears in your video.

| Concept | Primary visual motion | What to hold invariant | Key primitive |
| --- | --- | --- | --- |
| **Transformation** $A \mapsto B$ | the space or object continuously deforms from $A$-shape to $B$-shape | the colour / identity of the object | `ApplyFunction(f)` on `NumberPlane` or `Transform(A, B)` |
| **Limit / convergence** | iterates $x_n$ appear sequentially, each closer to the limit; they trail-fade while final object solidifies | the limit point's colour/position | sequence of `Dot` or `FunctionGraph` with `TracedPath` |
| **Approximation** | coarse version overlaid on exact target; residual shown in red and shrinking over time | the exact target stays teal | `always_redraw` on approximation object; `ValueTracker(n)` |
| **Local-to-global** | camera zooms in on a patch, reveals local structure; then zooms out showing the patch tiled across the whole | the structure discovered locally | `MoveCamera` zoom-in then zoom-out; patches appearing via `FadeIn` |
| **Equivalence** | double-headed morphism shown by animating $A \to B$ then $B \to A$ with the same object identity | the object identity | two sequential `Transform` calls; object colour unchanged |
| **Invariance** | coordinate system rotates / rescales / changes while underlying object holds position and colour | the object's position, shape, and colour | `Transform(axes_old, axes_new)` + object has no transform |
| **Causality / dependence** | arrow grows from cause node to effect node in direction of propagation; can pulse to show information flow | direction of arrow | `GrowArrow`; `ShowPassingFlash(arrow)` |
| **Hierarchy / composition** | objects at lower layer first, then higher objects materialise above them; nesting shown with depth or indentation | lower layer persists visibly | `FadeIn` of layers in order; nested `VGroup` |
| **Abstraction** | concrete instance (specific numbers, specific picture) fades out while the structural skeleton is held in invariant colour | the skeleton / pattern | `FadeOut(specific_parts)` while skeleton `Mobject` stays |
| **Composition** $f \circ g$ | first $g$ traced on domain; then $f$ traced on range; finally both swept together showing the composed path | input/output colours consistent | sequential `TracedPath` calls; or two `ParametricFunction` objects |
| **Continuity / deformation** | a family of objects indexed by $t$ deforms continuously from one to another | topological invariant (e.g., winding number) if present | `ValueTracker(t)` + `always_redraw(lambda: f(t.get_value()))` |
| **Symmetry** | rotation / reflection applied to object; fixed locus highlighted | fixed locus stays highlighted | `Rotating(obj, angle=...)`; `Flash(fixed_locus)` |
| **Measure / accumulation** | region fills up from left to right (or radially); running total shown as a number tracker | the boundaries of the region | `area_fill` animation or `Rectangle` growing; `DecimalNumber` updater |
| **Probability / uncertainty** | point cloud with opacity proportional to density; density evolves as evidence accumulates | the sample space boundaries | N `Dot` with opacity updater driven by pdf value |
| **Dimension reduction** | 3D object projected to 2D: rotating projection lines visible; 2D shadow morphs with rotation | the 3D object itself | 3D scene with `MoveCamera` phi sweep; 2D shadow via `get_projection` |
| **Fixed point / equilibrium** | flow lines converging toward fixed point; flows animated; fixed point pulses once when reached | fixed point colour/label | `StreamLines` flowing to attractor; `Flash(fixed_pt)` at convergence |

## Camera

- Default: static frame.
- Slow push-in (over 2–4 s) for emphasis at definition moments.
- Slow pull-out (over 2–4 s) for synthesis or "zoom out to see the whole structure" moments.
- Pan only when following a moving object.
- 3D scenes: declare `phi`, `theta`, `gamma`, `zoom`, `frame_center` per shot. Avoid free-orbit; deliberate keyframed moves only.

## Density rules

- Maximum ~7 distinct elements competing for attention in any single frame. If you need more, group them.
- Every element has a purpose. Decorative ornament is not allowed.
- Negative space is not empty — it is the visual equivalent of a pause.

## Object permanence

When an object survives a scene transition, it should *visibly survive* — same colour, same shape memory, same logical position in the frame. The viewer's mind tracks the object across time.

When an object is replaced by a different object, the replacement is animated (morph, overlay-then-fade), not cut.

## Overrides

Override the defaults when:

- The topic has its own conventional palette (e.g., epidemiology compartments — SIR colour conventions).
- The user requests a brand palette.
- The video belongs to a series with a fixed identity.

When overriding, declare the new mapping in §5 of the script and stick to it for the entire video.

## Anti-patterns

- Slide-style bullet reveals.
- Cut-and-replace where a morph is possible.
- Decorative arrows that point at nothing.
- Random colour drift between scenes.
- "Wallpaper math": equations sitting on screen with no role.
- Generic stock backgrounds (gradients, particles, swirling lines) added for visual interest.
- Text-heavy frames that the viewer can't read at the pacing of the narration.
