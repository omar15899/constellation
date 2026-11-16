---
title: "Visual Language — <topic>"
note_type: video_visual_language
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, visual_language, <topic_tags>]
status: draft
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
priority: normal
confidence: high
author: <model-id>
ai_generated: true
ai_reviewed: false
parent: INDEX.md
---

# Visual Language — `<topic>`

The full visual grammar of this video. Every visual choice is declared once here and is binding across `08_storyboard.md`, `09_image_prompts.md`, `10_manim_blueprint.md`, and the visual columns of `05_narration_script.md`. Consistency is not stylistic; it is a load-bearing pedagogical mechanism (Mayer signalling).

The defaults are inherited from `style/visual_language_guide.md`. Override only what the topic requires.

---

## §4.0 — Conceptual preamble

> *Plain-language statement of why a video that uses two unrelated visual idioms in adjacent scenes loses the viewer, and why the visual language is the second-most binding artefact after the conceptual blueprint. ~80 words.*

---

## §4.1 — Frame, canvas, motion register

| Property | Value | Rationale |
|---|---|---|
| Aspect ratio | 16:9 | standard |
| Resolution | 1920×1080 | Manim default; bump to 4K for 3D scenes |
| Frame rate | 60 fps | high-quality motion |
| Background | `<dark navy #0E1116 / off-black #050507 / paper #F8F4EE / etc.>` | matches register declared in `00_declaration.md` |
| Background motion | static / slow gradient / particle drift / none | none during dense formal blocks |

---

## §4.2 — Palette and colour semantics

Every colour carries one and only one semantic role. A colour used decoratively breaks the contract.

| Hex | Name | Semantic role | Where used |
|---|---|---|---|
| `#5BC0EB` | teal-cyan | invariant object | central concept |
| `#F4C95D` | amber | chosen representation / coordinates | examples, charts |
| `#E94F37` | crimson | failure / boundary / counter-example | `[BOUNDARY]` blocks |
| `#9B59B6` | violet | abstraction / category-level structure | abstraction movements |
| `#FFFFFF` | white | formal definition / theorem | `[FORMAL]` blocks |
| `#7A8C99` | slate | secondary structure / supporting machinery | helpers, axes, grids |
| `#3DDC97` | mint | cross-domain echo / unification | Pillar IV moments |
| `<more>` | … | … | … |

Override only when the topic genuinely requires it (e.g. physics quantities with conventional colours).

---

## §4.3 — Typography

| Use | Font | Weight | Size relative to canvas height |
|---|---|---|---|
| Body / narration captions | Inter / SF Pro | 400 | 4% |
| Headings | Inter / SF Pro | 600 | 6% |
| Mathematical notation | LaTeX (Computer Modern) via Manim `MathTex` | regular | 5% |
| Code | JetBrains Mono / Fira Code | 400 | 3.8% |
| Inline definition tags (Doctrine Pillar II) | Inter Light Italic | 300 | 3% — appears below first-use term, fades after 3 s |

---

## §4.4 — Notation discipline

- Notation registered in `01_conceptual_blueprint.md` §1.4 is binding.
- Every formula appears once in its primary form; subsequent appearances may compress (e.g. drop subscripts) only when the compression is signalled (e.g. with a brief overlay showing the full form).
- No equation appears during a `[PREAMBLE]` beat (Doctrine Pillar I).
- Equations enter via `Write` or `FadeIn`, never `Create` — the latter draws stroke-by-stroke and visually claims more than the formula deserves.

---

## §4.5 — Motion vocabulary

The motion vocabulary is the verb set of the video. Each verb encodes a **meaning**, not a transition. Mixing verbs costs cognitive coherence. More critically: **every verb must describe continuous parametric change, not appearance/disappearance of a static object.** A frame in which nothing is continuously transforming is a slide — never acceptable.

The vocabulary has four layers: object lifecycle, continuous 2D animation, continuous 3D animation, and structural dynamics. Pick the verb that encodes the conceptual meaning, then spec its parameters.

---

### Layer 1 — Object lifecycle (use sparingly; prefer Layer 2–4)

These verbs are for entry/exit only, not for conveying mathematical content. If you reach for one of these to describe a conceptual moment, that is a signal you need a richer verb from Layers 2–4.

| Visual verb | Encoded meaning | Manim primitive | Duration |
|---|---|---|---|
| **fade-in** | new object enters the scene | `FadeIn` | 0.6–1.0 s |
| **fade-out** | object exits the scene | `FadeOut` | 0.6–1.0 s |
| **write** | text or formula materialises as authored | `Write` | 0.8–1.2 s |
| **unwrite** | formula or object dismantled from right to left | `Unwrite` | 0.8–1.2 s |
| **draw-border** | geometric figure traced outline-first | `DrawBorderThenFill` | 0.8–1.5 s |
| **highlight** | attention flash on a specific element | `Indicate` / `Flash` / `FocusOn` | 0.3–0.5 s |
| **arrow-grow** | directional dependence / causality | `GrowArrow` (direction of causation) | 0.5–0.8 s |
| **morph** | one representation of an object becomes another | `Transform` / `ReplacementTransform` | 1.0–1.5 s |
| **fade-to-invariant** | representation fades, underlying object held in place | layered `FadeOut` on representation, object persists | 1.5–2.0 s |
| **morph-cross-domain** | same structural diagram, axes relabelled | `Transform` on labels only, structure held | 2.0–2.5 s |
| **split-screen** | comparison / cross-domain echo | `VGroup` side by side | 1.0 s entry |

---

### Layer 2 — Continuous 2D animation (the primary vocabulary for mathematical content)

These verbs describe objects undergoing **continuous parametric change** over time. Every scene that contains a mathematical idea should use at least one verb from this layer.

| Visual verb | Encoded meaning | Manim implementation | Duration | Spec required |
|---|---|---|---|---|
| **parametric-trace** | a curve/path being drawn in real time as the parameter advances | `MoveAlongPath`, `TracedPath`, `ParametricFunction` with `ValueTracker(t)` driving endpoint | 2–8 s | param range, step density, trail fade/persist |
| **field-evolve** | a vector or scalar field updating continuously as a parameter changes | `VectorField` or `NumberPlane` with colour-map updater; `ValueTracker(p)` | 2–6 s | parameter meaning, field component specs, colour encoding |
| **space-deform** | the entire coordinate plane/space warped by a linear or nonlinear map | `NumberPlane` morphed via `ApplyFunction(f)` or `ApplyMatrix(M)` | 2–5 s | map f / matrix M, what invariants are preserved |
| **flow-lines** | integral curves / gradient flow / ODE solutions drawn as moving particles or streaks | `StreamLines` or custom `Dot` updaters following dx/dt = f(x) | 3–8 s | ODE, density, arrow periodicity |
| **converge-sequence** | iterative sequence approaching a limit, each iterate visible | sequence of objects each fading to near-target, final solidifies | 3–6 s | iteration count, visual distance per step |
| **construction-live** | geometric construction unfolding step by step | `Create` of circle, `Dot` at intersection, label appearing, etc. | 2–10 s | exact construction steps in order |
| **level-set-evolve** | contour curves moving as parameter changes | `ImplicitFunction` updated via `ValueTracker` | 3–6 s | function f(x,y,p)=c, contour value range |
| **scatter-coagulate** | points drawn from a distribution and drifting toward a target (e.g., convergence, conditioning) | N `Dot` objects with updaters driven by interpolation toward target positions | 3–8 s | N, initial distribution, target distribution |
| **color-map-animate** | heatmap or colour field updating continuously | `NumberPlane` with color function updater | 2–6 s | what quantity drives the colour |
| **measurement-grow** | a quantity visually accumulating (area filling, arc length extending, probability mass building) | `area_fill`, filled region expanding, sector growing | 2–5 s | quantity being measured, fill direction |
| **label-track** | annotation or formula label following a moving object | `.add_updater(lambda m: m.next_to(obj, ...))` | continuous | which label, which object |
| **substitute-highlight** | expression transformed term by term, highlighting each substitution | `TransformMatchingTex` with `SetColor` on sub-expressions | 1.5–4 s | source expression, target expression, substitution order |
| **coordinate-change** | axes + grid relabelled/rescaled to a new coordinate system while objects held fixed | `Transform` on `Axes` + `ReplacementTransform` on labels | 2–4 s | old and new coordinate systems |

---

### Layer 3 — Continuous 3D animation

Use when the concept requires non-trivial 3D geometry. Default to Manim 3D (`ThreeDScene`) or note a Blender handoff.

| Visual verb | Encoded meaning | Manim / Blender primitive | Duration | Spec required |
|---|---|---|---|---|
| **surface-build** | parametric surface materialising from its boundary curves or parameter sweep | `ParametricSurface` with animated u-range or v-range | 3–8 s | (u,v) parameterisation, colour convention, which direction builds first |
| **orbit-reveal** | camera orbiting around a 3D object to expose its structure | `begin_ambient_camera_rotation` or keyframed `move_camera` | 4–10 s | start φ/θ, end φ/θ, orbit axis, what the orbit reveals |
| **section-cut** | a cutting plane sweeping through a 3D solid, revealing cross-sections | animated `Intersection` with moving plane | 3–6 s | plane normal, sweep range |
| **fiber-reveal** | fibers of a bundle appearing one by one above their base point | per-fiber `Create` triggered by base-point cursor moving | 4–8 s | total space, base space, fiber type |
| **embed-project** | abstract object materialising in ambient space; or high-dimensional object projected down | `ParametricSurface` appearing; or projection animation | 3–6 s | ambient dimension, projection direction |
| **field-3d-evolve** | 3D vector field or scalar field evolving in time | 3D `VectorField` or `Dot` cloud with colour-updater | 4–8 s | field F(x,y,z,t), visual density |
| **rotation-3d** | object rotating around a given axis to expose orientation / handedness | `Rotating(obj, axis=...)` | 2–5 s | axis, angle, speed |
| **geodesic-trace** | a geodesic drawn on a surface in real time | `TracedPath` on a `ParametricSurface` | 3–6 s | start point, direction, arc length |

---

### Layer 4 — Structural dynamics

| Visual verb | Encoded meaning | Implementation | Duration | Spec required |
|---|---|---|---|---|
| **diagram-commute** | commutative diagram traced: arrows highlighted in sequence proving the square commutes | sequential `ShowPassingFlash` on arrows + `FocusOn` at nodes | 2–5 s | diagram layout, composition order |
| **dependency-grow** | computation/dependency graph growing node by node | sequential `Create(node)` + `GrowArrow(edge)` | 3–8 s | DAG structure, evaluation order |
| **layer-peel** | abstraction layers peeled back or built up | depth-ordered `FadeOut` / `FadeIn` of layer groups | 2–5 s | which layers, which direction |
| **comparison-animate** | two structurally parallel objects side by side, both animated simultaneously | symmetric layout, parallel animations in sync | 3–8 s | what the parallel structure is |
| **parameter-sweep** | single parameter swept over its range while the object continuously changes | `ValueTracker` + `always_redraw` | 3–10 s | parameter range, what changes |
| **accumulate-sum** | discrete sum building term by term (Riemann sum, Taylor partial sums, etc.) | add `Rectangle`/`MathTex` per term, animate each | 4–10 s | function, partition, n_terms |

---

### Animation richness contract

Every row in `05_narration_script.md` that corresponds to a mathematical or conceptual beat must use at least one verb from Layers 2–4. A row that uses only Layer 1 verbs for a conceptual beat is a specification failure. In the script table, the **"On-screen (atomic visual event)"** column must describe **what is changing continuously**, not what is appearing or disappearing — even if an object is entering, specify what it is doing while it enters.

**Forbidden patterns** — these are slide-paradigm failures:
- "definition appears on screen" (use **write** + specify what else is animating in context)
- "diagram fades in" with no further motion spec
- "text slides in from left" (pure decoration)
- any scene where the only verbs are fade-in / fade-out with no Layer 2–4 verb also present
- "show the formula" without specifying what is being animated around it
- bullet-point reveals in any form
- gratuitous camera shake, lens-flares, particle bursts with no semantic role

---

## §4.6 — Representation of structural concepts

Every abstract structural concept the video carries has a fixed visual signature. Reuse the signature whenever the concept reappears.

| Concept | Visual signature |
|---|---|
| Uncertainty | soft glow / probability cloud / opacity gradient |
| Abstraction | representation fades; invariant object remains |
| Causality / dependence | directional arrow growing in real time |
| Hierarchy | nested containers / depth |
| Equivalence | reversible morphism (double-headed arrow) |
| Invariance | representation changes, object holds still |
| Locality | zoom-in on a patch |
| Globality | zoom-out from patches to whole |
| Approximation | coarse object refining toward target |
| Structure | shared colour / shared layout across siblings |
| Cross-domain echo | split-screen with parallel axes |
| Object-vs-representation distinction | representation fades; object persists in invariant colour |

---

## §4.7 — Definition / example / boundary on-screen treatment

| Tag | On-screen treatment |
|---|---|
| `[PREAMBLE]` | metaphor visual only; no notation; soft motion |
| `[FORMAL]` | framed white box, fade-in left, 1.0–1.5 s held pause after appearance |
| `[INSTANCE]` | diagrammatic, formal definition kept visible in corner |
| `[BOUNDARY]` | crimson tint; "fails because…" tag below |
| `[CROSS_DOMAIN]` | split-screen; same diagram with axes relabelled to other domain |
| `[RETRIEVAL]` | screen freeze with on-screen question; 3–5 s hold |
| `[SELF_EXPLAIN]` | dim everything except the highlighted hypothesis; "why?" pop-up |

---

## §4.8 — Camera behaviour

- Default frame is static.
- Slow camera pushes (0.05× zoom over 5 s) for emphasis only — at most twice per minute.
- Hard zooms reserved for local-to-global moments.
- 3D scenes: use `MoveCamera` rather than rotating the world; the world is what is being studied.

---

## §4.9 — Pause and breath

| Where | Duration |
|---|---|
| After every formal definition | 1.0–1.5 s |
| After every theorem statement | 1.0–1.5 s |
| After every retrieval prompt | 3.0–5.0 s |
| After every self-explanation prompt | 2.0–4.0 s |
| Before a cross-domain echo | 1.0 s |
| Between scenes | 0.5–1.0 s |

Pauses are written into the script as `[PAUSE Ns]` markers in `06_voiceover.md`.

---

## §4.10 — Visual language freeze gate

- [ ] Every colour has exactly one semantic role.
- [ ] Every motion verb in §4.5 is the only verb used for its encoded meaning.
- [ ] Every structural concept the video uses has a fixed visual signature.
- [ ] No notation appears during any `[PREAMBLE]` block.
- [ ] All inline definition tags (Doctrine Pillar II) follow the typography rule in §4.3.
- [ ] The visual language file is referenced once at the top of `05_narration_script.md`, `08_storyboard.md`, `09_image_prompts.md`, and `10_manim_blueprint.md`, with this file as the binding authority.
