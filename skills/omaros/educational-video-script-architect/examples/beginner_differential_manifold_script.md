# Example — "Why a curved space needs many coordinate systems"

A worked example of the full output format. Audience: undergraduate / advanced beginner with high-school calculus and basic linear algebra. Topic: the conceptual need for an atlas on a smooth manifold. Duration: 6:00. Modality: Manim primary, with two generative-video reference clips for the opening cinematic establishment.

This example exists so the skill knows what a complete output actually looks like. Do not copy it verbatim into other scripts — the structural skeleton is in `templates/video_script_template.md`.

---

# Educational Video Script — Why a curved space needs many coordinate systems

## 1. Production brief

- **Topic:** the necessity of an atlas — why a single coordinate chart cannot describe a closed curved surface, and why the data of multiple charts plus their compatibility on overlaps is the right object.
- **Audience level:** undergraduate (mathematical maturity at the level of multivariable calculus + first-year linear algebra; no prior exposure to manifolds).
- **Intended duration:** 6:00 ± 15 s.
- **Educational objective:** the viewer can state, in their own words, why no single chart covers the sphere, what an atlas is, and what compatibility on overlaps means.
- **Core conceptual promise:** a coordinate system is a *partial* description; a curved space is the data of overlapping partial descriptions that agree on their overlaps.
- **Prerequisites:** functions $\mathbb{R}^n \to \mathbb{R}^m$, the idea of a smooth function, the unit sphere as a set in $\mathbb{R}^3$.
- **Chosen explanatory structure:** problem-first (we will not present a definition until the viewer has watched a single chart fail).
- **Reason for choosing that structure:** the atlas is conceptually "obvious" only after the viewer has felt the failure of a single chart. Definition-first would land as arbitrary.
- **Production modality:** Manim 3D for the sphere, charts, and overlap region; one generative-video clip at the open for cinematic establishment; one optional generative reference clip at 03:10 for "two coordinate patches glow on the same region".
- **Visual style:** OmarOS default (see `style/visual_language_guide.md`).
- **Tone of voice:** measured, slightly warm, faintly curious. The narrator is someone who finds the inevitability of the atlas genuinely beautiful.
- **Main mathematical or conceptual objects:** the unit sphere $S^2$, a single chart $\varphi: U \to \mathbb{R}^2$, two overlapping charts $(U, \varphi)$ and $(V, \psi)$, the transition map $\psi \circ \varphi^{-1}$ on $\varphi(U \cap V)$.
- **Expected emotional / intellectual arc:** opens with curiosity (the world is curved, our notation is flat), moves through tension (the chart tears), arrives at recognition (we needed the chart to be partial all along).

## 2. Conceptual abstract

The video addresses a concrete obstacle: the unit sphere cannot be covered, in a continuous and injective way, by a single open subset of the plane. We make this obstacle visible by attempting to wrap a flat coordinate grid onto the sphere and watching it tear. The diagnosis is that "coordinate description" is intrinsically *local*; a closed curved object refuses a single global flat description.

The construction we build in response is the atlas: a collection of charts, each describing only a region of the object, together with the data of how any two charts agree on the region they share. The transition map $\psi \circ \varphi^{-1}$ is the algebraic shadow of "two descriptions of the same region" — and its smoothness is what licenses the entire calculus that will follow in later videos.

The misconception the video dissolves is that a coordinate system *is* the space, or that "needing several coordinate systems" is a defect rather than the structure of the object itself. By the end, the viewer will see that the multiplicity of charts is not a workaround — it is the precise structure that makes calculus on curved spaces possible.

Rigor enters at scene 4 (the formal definition of a chart) and scene 6 (the transition-map condition). Examples enter at scene 2 (the sphere) and scene 5 (two stereographic charts). Abstraction enters at scene 7 (the atlas as the combined data, irrespective of which charts we picked).

## 3. Pedagogical design notes

- **Audience-level assumptions.** The viewer has seen $\mathbb{R}^2$ and $\mathbb{R}^3$, knows what a smooth function is informally, has graphed surfaces. They have *not* seen the formal definition of a topological space, so we avoid that vocabulary entirely.
- **Likely misconceptions.**
  - "A coordinate system is the surface." Addressed in scene 3 by explicitly fading the chart and leaving the sphere visible.
  - "Needing several charts is a workaround." Addressed in scene 7 by reframing multiplicity as structure.
- **Example-selection strategy.** The sphere is the smallest closed curved surface most viewers can hold in mind. Two stereographic charts (north pole, south pole) are the cleanest pair: each covers everything except a single point, and together they cover the sphere with a clean overlap. The transition map between them has a clean closed form.
- **Pedagogy mode.** Problem-first: show the chart failing before introducing the formalism.
- **Cognitive load control.** New objects appear one at a time: sphere → single chart → tear → second chart → overlap → transition map → atlas. Each new object gets a 1–2 s pause after appearing.
- **Narration ↔ visual sync.** Definitions appear on screen at the moment the narration names them. The chart-fails moment (scene 3) is silent for 1.5 s — the visual carries the argument.
- **Intuition→formalism transition.** Two explicit transitions: at 02:00 (informal "coordinate window" → formal "chart") and at 04:30 (informal "they agree" → formal "transition map is smooth").
- **Learning-research influences.** Worked-example effect (we work through the failure of one chart before introducing the abstract definition); refutation framing (the misconception "one chart should be enough" is named explicitly in narration at 01:35); signaling (the colour palette consistently distinguishes the *object* — teal sphere — from a *representation* — amber grid).

## 4. Explanatory architecture

| # | Scene | Time | Purpose | Conceptual role | Visual strategy | Main screen objects | Modality | Transition out |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Curved world | 0:00–0:25 | establish that real curved objects exist | motivation | cinematic establishing shot | generated globe-like object | gen-video reference + Manim title overlay | morph generated globe into clean teal sphere |
| 2 | The flat grid wants in | 0:25–1:10 | introduce the desire to put coordinates on the sphere | motivation | wrap a flat grid around part of the sphere | sphere + amber grid | Manim 3D | grid tries to extend across the whole sphere |
| 3 | The chart tears | 1:10–2:00 | show the obstacle | tension | grid extends globally and visibly tears at the antipodal point | sphere + tearing grid + magenta error highlight | Manim 3D | visual silence; then the formal definition fades in |
| 4 | What a chart actually is | 2:00–3:00 | name the partial description formally | definition | white framed definition box; the chart shrinks to its proper region | sphere + region $U$ + chart $\varphi: U \to \mathbb{R}^2$ + definition text | Manim 3D + 2D | a second chart enters from the other side |
| 5 | Two views of the same place | 3:00–4:00 | introduce the overlap | example | two charts covering the sphere; overlap region glows | sphere + $U$, $V$ + $U \cap V$ glowing + two flat copies | Manim 3D + 2D | zoom into overlap |
| 6 | The translator | 4:00–5:00 | introduce the transition map | formalisation of overlap | the same point in the overlap shown in both charts; arrow connects them; transition formula appears | flat plane $\varphi(U \cap V)$ → flat plane $\psi(U \cap V)$ + transition map label | Manim 2D | zoom out to see the whole sphere again |
| 7 | The whole picture | 5:00–6:00 | name the atlas; return to original question | abstraction + closure | the sphere with both charts attached and the transition map labelled, the whole structure named "atlas" | sphere + both charts + transition arrow + final definition box | Manim 3D + 2D | fade to black |

## 5. Visual language specification

- **Background.** OmarOS default — deep matte near-black `#0a0a0c` with a faint central glow at the sphere's location.
- **Palette.**
  - **Teal `#5BC0BE`** — the invariant object (sphere $S^2$ and points on it).
  - **Amber `#F2C94C`** — the first chart $(U, \varphi)$ and its grid.
  - **Cyan `#56CCF2`** — the second chart $(V, \psi)$ and its grid.
  - **Magenta `#EB5757`** — the tear, the error, the failure of a single chart.
  - **White `#FFFFFF`** — formal definitions and theorem statements.
  - **Grey `#9B9B9B`** — axis labels, scaffolding text.
- **Typography.** Inter 400 for body labels; Computer Modern via `MathTex` for formulas; titles in Inter 600.
- **Notation conventions.** Sphere as $S^2 \subset \mathbb{R}^3$; charts as $\varphi: U \to \mathbb{R}^2$; transition map as $\psi \circ \varphi^{-1}: \varphi(U \cap V) \to \psi(U \cap V)$. Differentials use italic $d$.
- **Definitions appear as.** A floating white-bordered rectangle, fade-in over 1.0 s, with a 1.5 s settle.
- **Examples appear as.** Diagrammatic; the formal definition stays visible in the upper right corner during the example.
- **Transformations animated as.** Continuous morphs (`Transform`, `ReplacementTransform`). No cut-and-replace.
- **Object–representation distinction.** When a chart fades and the sphere remains, the implementer explicitly fades the chart's stroke opacity to zero while preserving the sphere; the camera does not move during this fade so the viewer's eye stays on the sphere.
- **Camera behaviour.** Static during definitions. Slow push-in (3 s) during scene 3 (the tear). Slow pull-out (4 s) during scene 7 (the atlas).
- **Use of pauses, zooms, fades.** 1.5 s silence at the moment of the tear (1:50). 2 s silence after the atlas definition appears (5:50).

## 6. Second-by-second script

| Time | Voice-over (exact) | Screen / animation | Notation | Production notes | Manim notes | Generative-video notes | Asset prompts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0:00–0:05 | (silence) | dark frame; faint central glow brightens slowly | — | open in silence; build atmosphere | n/a — generated clip | GEN-S1-C1 plays full-frame | S1-C1 |
| 0:05–0:15 | "The world is full of curved surfaces. Our notation is flat." | cinematic curved object slowly rotates; title text fades in over 1 s in lower third: "Why a curved space needs many coordinate systems" | title text only | hold title 5 s | overlay `Text` on top of generated clip via `ImageMobject` | continue GEN-S1-C1 | — |
| 0:15–0:25 | "We're going to find out exactly why — and the answer is more interesting than 'because curvature'." | generated globe morphs into clean teal `Sphere` object centred in frame | — | morph from external clip to Manim — composite handoff | `ReplacementTransform(image_globe, sphere_M)`, run_time=2.5 | end GEN-S1-C1 with morph-friendly final frame | — |
| 0:25–0:35 | "Suppose we want to describe positions on this sphere with two numbers — a flat coordinate system." | amber rectangular grid materialises floating beside the sphere | — | grid is flat 2D in the same frame | `NumberPlane(x_range=[-2,2], y_range=[-2,2])`, colour=GOLD_C, place LEFT*4 | n/a | — |
| 0:35–0:55 | "We try to wrap the grid onto the sphere. On a small region, it works — like draping paper on the top of an orange." | grid bends and conforms to the upper cap of the sphere; coordinate lines glow softly on the surface | $U \subset S^2$ region label appears | hold 2 s on successful local wrap | custom `transform_to_surface(grid, sphere_M, region=upper_cap)` helper; tag region with translucent amber overlay | n/a | S2-F1 |
| 0:55–1:10 | "But what if we want the grid to describe the *whole* sphere?" | the grid attempts to extend; it stretches over the equator and toward the south pole | — | the stretching is the visual signal of trouble | animate region expansion via parametric value-tracker; grid lines distort | n/a | — |
| 1:10–1:30 | "Watch what happens." | the grid stretches further; coordinate lines start crowding; amber colour shifts toward warning at the antipodal region | — | begin colour-shift cue | tracker drives both region size and stroke colour interpolation toward magenta | n/a | — |
| 1:30–1:35 | "It tears." | the grid visibly ruptures at the antipodal point; magenta jagged seam appears | — | hard visual emphasis; brief flash | `Flash(seam, color=RED_C)` | n/a | S3-F1 |
| 1:35–1:50 | (silence) | hold on the torn grid for 1.5 s; sphere stays centred; magenta seam remains visible | — | this silence is intentional; do not score with music either | nothing animates; camera holds | n/a | — |
| 1:50–2:00 | "No flat grid can cover a closed curved surface without tearing or folding. The diagnosis is not bad design — it's a structural property of the object." | torn grid fades away; sphere remains alone | — | clean reset for the formal move | `FadeOut(grid, run_time=1.5)`; sphere unaffected | n/a | — |
| 2:00–2:20 | "So we change what we ask for. Instead of one global description, we ask only for *partial* ones." | a small amber patch reappears on the upper cap of the sphere; the words "chart" and "domain" enter as labels | label `(U, ϕ)` appears | re-introduce the chart, smaller, restricted to its proper domain | recreate amber region (`region=upper_cap`); annotate with `MathTex(r"(U, \varphi)")` | n/a | — |
| 2:20–2:40 | "A chart is a pair: a region $U$ on the sphere, and a continuous, invertible map from that region into the flat plane." | white-bordered definition box fades in to the right of the sphere | $\varphi: U \to \mathbb{R}^2$, $U \subset S^2$ open, $\varphi$ continuous and invertible onto its image | hold definition 1.5 s after settle | `DefinitionBox(...)` helper; `Write` the formula | n/a | — |
| 2:40–3:00 | "The chart is not the sphere. Rotate the sphere — the chart still describes the same region. Change the chart — the region is still there." | sphere rotates ~20°; chart rotates with it. Then the chart fades; sphere remains, with the region $U$ still visibly highlighted in dim teal | — | this is the object-vs-representation moment | small `Rotate` of sphere group; then `FadeOut(chart, keep_anchor=True)` | n/a | — |
| 3:00–3:20 | "But one chart isn't enough — we already saw that. So we add a second one." | a cyan grid materialises and conforms to the lower cap of the sphere; cyan region $V$ appears | label `(V, ψ)` appears | symmetric to the first chart, in cyan | second amber-cyan equivalent of the wrap | optional reference: GEN-S3-C1 in production for cinematic flavour, but Manim version is the production asset | S3-C1 ref-only |
| 3:20–3:40 | "Together, they cover the whole sphere. But they overlap — there is a band where both charts describe the same points." | the equatorial band where amber and cyan overlap glows softly in white | $U \cap V$ label appears | hold 2 s on the glow | overlay an extra `VMobject` for the intersection band, glow via `set_glow_factor` (or `set_stroke(opacity=...)` cycle) | n/a | — |
| 3:40–4:00 | "And here's the question that decides everything: do the two charts *agree* on the overlap?" | zoom-in (camera push) onto the overlap band; both chart copies visible side by side in the lower third of the frame as flat 2D rectangles | — | begin slow camera push (3 s) toward overlap | `MoveCamera` with `frame_center=overlap.get_center()` and `zoom=1.4` | n/a | — |
| 4:00–4:20 | "Pick a point in the overlap. The first chart sees it as a pair of numbers. The second chart sees it as a different pair of numbers." | a single sphere-point (small white dot) is highlighted; arrows go down to two dots in the two flat charts; the two flat coordinate values appear | $p \in U \cap V$, $\varphi(p) = (x_1, x_2)$, $\psi(p) = (y_1, y_2)$ | hold 1.5 s on the two pairs of numbers | `Indicate(p)`; `GrowArrow` to the two flat charts; `MathTex` labels at each landing | n/a | S4-F1 |
| 4:20–4:50 | "The translator between the two — the function that takes the first chart's numbers and gives back the second chart's numbers — is called the transition map." | an arrow grows from the first flat chart to the second; the formula for the transition map appears between them | $\psi \circ \varphi^{-1}: \varphi(U \cap V) \to \psi(U \cap V)$ | the formula is the centrepiece of this scene | `MathTex(r"\psi \circ \varphi^{-1}")` placed on the arrow | n/a | — |
| 4:50–5:00 | "We require this translator to be smooth — that is, infinitely differentiable wherever it's defined." | the word "smooth" appears under the formula; small visual cue — a smoothness ribbon — wraps the arrow | label "smooth" | flag this as the formal compatibility condition | `Text("smooth", colour=WHITE).next_to(arrow, DOWN)` | n/a | — |
| 5:00–5:20 | "With these two charts, plus the transition map between them, we have something that does the job a single chart could not." | camera pulls out (4 s) to show the whole sphere with both charts attached and the transition arrow visible | — | begin slow pull-out | `MoveCamera(frame_center=ORIGIN, zoom=1.0)` over 4 s | n/a | — |
| 5:20–5:40 | "This combined data has a name: an atlas." | white definition box fades in: "An atlas on $S^2$ is a collection of charts whose domains cover $S^2$ and whose transition maps on overlaps are smooth." | atlas definition text | hold definition 2 s after settle | `DefinitionBox` for the atlas | n/a | S5-F1 |
| 5:40–5:55 | (1.5 s silence) | hold on the full picture: sphere, two charts, transition arrow, atlas definition box | — | intentional pause for absorption | nothing animates | n/a | — |
| 5:55–6:00 | "The need for several charts isn't a workaround. It is the structure of the curved space." | the words "several charts" and "structure" briefly highlight in the definition box | — | closing emphasis on the reframe | `Indicate` on substring | n/a | — |

## 7. Production implementation blueprint

### Manim segments (primary modality)

- **Scene classes.**
  - `IntroScene(MovingCameraScene)` — 0:00–0:25; loads the generated clip via `ImageMobject`/`VideoMobject`, then morphs to a Manim sphere.
  - `WrapAndTearScene(ThreeDScene)` — 0:25–2:00; the central conceptual scene. Sphere + parametric grid wrap + tear.
  - `ChartDefinitionScene(ThreeDScene)` — 2:00–3:00; introduces the formal chart definition; mixes 3D sphere with 2D definition box.
  - `OverlapScene(ThreeDScene)` — 3:00–4:00; second chart and overlap glow.
  - `TransitionMapScene(MovingCameraScene)` — 4:00–5:00; flat-2D scene zoomed onto the overlap, with the transition map.
  - `AtlasScene(ThreeDScene)` — 5:00–6:00; the synthesis.
- **Main Manim objects.**
  - `sphere_M = Sphere(radius=1.5, resolution=(36, 36), color=TEAL_C)`.
  - `grid_phi = NumberPlane(...)` then a custom `transform_to_surface(grid_phi, sphere_M, region=upper_cap)` helper to bend it onto the sphere.
  - `grid_psi` as the cyan counterpart on the lower cap.
  - `overlap_band = VMobject` constructed parametrically as the intersection of the two chart domains, set with translucent white stroke, animated glow via opacity oscillation.
  - `phi_flat`, `psi_flat` — two `NumberPlane` copies for the 2D-overlap scene.
  - `transition_arrow = Arrow(...)` with `MathTex(r"\psi \circ \varphi^{-1}")` label.
- **Coordinate systems.**
  - 3D scene camera: `phi=70°, theta=-45°, gamma=0°, zoom=1.0` (default).
  - `WrapAndTearScene` 3D scene `frame_center=ORIGIN`.
  - `TransitionMapScene` is purely 2D; `frame_center=overlap_center, zoom=1.4`.
- **Equations and labels.**
  - `MathTex(r"(U, \varphi)")` near the upper cap.
  - `MathTex(r"(V, \psi)")` near the lower cap.
  - `MathTex(r"\varphi: U \to \mathbb{R}^2")` inside the chart definition box.
  - `MathTex(r"\psi \circ \varphi^{-1}: \varphi(U\cap V) \to \psi(U\cap V)")` on the transition arrow.
  - The atlas definition box uses `Tex(...)` (not `MathTex`) for the prose, with the formal symbols inline via `\(...\)`.
- **Animation primitives.** `FadeIn`, `FadeOut`, `Write`, `Create`, `ReplacementTransform`, `Indicate`, `Flash` (for the tear), `GrowArrow`, `MoveCamera`, `Rotate`.
- **Custom helpers.**
  - `transform_to_surface(grid, surface, region) -> Animation` — bends a flat plane onto a region of a parametric surface via a value-tracker.
  - `tear_animation(grid, seam_point) -> Animation` — produces the ruptured-seam effect with magenta highlight.
  - `definition_box(text, position, width=4) -> VGroup` — the standardised white-bordered box.
- **Pure Manim vs imported assets.** The intro 0:00–0:25 mixes a generated reference clip with a Manim title overlay and ends in a morph-to-Manim moment. Everything from 0:25 onward is pure Manim.
- **Performance considerations.** The `transform_to_surface` helper with high mesh resolution can be expensive; render the wrap/tear sequence at `-qm` for previews, `-qk` only for final. The `OverlapScene` with continuous glow oscillation adds per-frame work; consider pre-rendering as a video clip.

### Generative-video segments

- **GEN-S1-C1.** 0:00–0:20, opening cinematic establishment of "a curved object exists in space".
  - Style lock and negative prompt per `templates/generative_video_prompt_template.md`.
  - Action timeline: 0–7 s slow rotation of an unspecified curved object in a dark studio, gentle camera push; 7–12 s the object becomes more sphere-like in shape; 12–20 s it stabilises and is ready to be morphed away.
  - Composite plan: Manim title text overlaid at 0:05; morph-handoff to Manim sphere at 0:20–0:25.
  - Use: reference + final asset (with overlay).
- **GEN-S3-C1 (optional).** 3:00–3:20, two coloured patches glowing on a curved surface.
  - This clip is reference-only; the implementer may prefer to keep the whole 3:00–3:20 segment in Manim for visual continuity. Use the reference if a more cinematic flavour is wanted in the final cut.

### Storyboard frames (image generation, reference-only)

- **S2-F1** (0:35–0:55). The flat amber grid wraps onto the upper cap of the sphere — implementer reference for lighting and grid density.
- **S3-F1** (1:30–1:35). The grid tears at the antipodal point; magenta seam visible. Implementer reference for the visual weight of the tear.
- **S4-F1** (4:00–4:20). The two flat charts side by side with arrows down from a sphere point. Implementer reference for layout.
- **S5-F1** (5:20–5:40). The full atlas: sphere with both charts attached, transition arrow, definition box. Implementer reference for final composition.

Detailed prompts for each frame follow the format in `templates/storyboard_prompt_template.md` and are omitted here for brevity. They can be generated by re-applying the template with the descriptions above.

## 8. Storyboard and image/video-generation prompts

(See §7 — concrete prompts to be expanded from the descriptions using `templates/storyboard_prompt_template.md` and `templates/generative_video_prompt_template.md`. They are omitted in this example file to keep it readable; in a real production output, every prompt would be written out in full.)

## 9. Voice-over-only version

The world is full of curved surfaces. Our notation is flat. We're going to find out exactly why — and the answer is more interesting than "because curvature".

Suppose we want to describe positions on this sphere with two numbers — a flat coordinate system. We try to wrap the grid onto the sphere. On a small region, it works — like draping paper on the top of an orange. But what if we want the grid to describe the whole sphere?

Watch what happens.

It tears.

No flat grid can cover a closed curved surface without tearing or folding. The diagnosis is not bad design — it's a structural property of the object.

So we change what we ask for. Instead of one global description, we ask only for partial ones. A chart is a pair: a region U on the sphere, and a continuous, invertible map from that region into the flat plane. The chart is not the sphere. Rotate the sphere — the chart still describes the same region. Change the chart — the region is still there.

But one chart isn't enough — we already saw that. So we add a second one. Together, they cover the whole sphere. But they overlap — there is a band where both charts describe the same points. And here's the question that decides everything: do the two charts agree on the overlap?

Pick a point in the overlap. The first chart sees it as a pair of numbers. The second chart sees it as a different pair of numbers. The translator between the two — the function that takes the first chart's numbers and gives back the second chart's numbers — is called the transition map. We require this translator to be smooth — that is, infinitely differentiable wherever it's defined.

With these two charts, plus the transition map between them, we have something that does the job a single chart could not. This combined data has a name: an atlas.

The need for several charts isn't a workaround. It is the structure of the curved space.

## 10. Mathematical and conceptual rigor audit

- **Definitions.** The chart is defined as a pair $(U, \varphi)$ with $U \subset S^2$ open and $\varphi: U \to \mathbb{R}^2$ continuous and invertible onto its image. **PASS**, with a NOTE: a fully formal definition would require $\varphi$ to be a homeomorphism onto an open subset of $\mathbb{R}^2$, and the "open" condition relies on the topology of $S^2$, which we have not introduced. The narration uses "continuous and invertible" as a viewer-friendly proxy. Tag this scene as **[INFORMAL]** at the level of the topology, **[FORMAL]** at the level of the chart pair structure.
- **Object vs representation.** Scene 4 (2:40–3:00) explicitly performs the object-vs-representation move: the chart fades, the sphere remains. **PASS.**
- **Notation.** Consistent throughout: sphere $S^2$; charts $(U, \varphi)$, $(V, \psi)$; transition map $\psi \circ \varphi^{-1}$. No symbol is reused with a different meaning. **PASS.**
- **Examples genuinely instantiate definitions.** The sphere is a genuine 2-manifold; the two charts described (north-cap and south-cap) are genuine charts. **PASS.**
- **Special cases / non-examples.** The "single chart fails" sequence (scenes 2–3) is effectively a non-example: it shows what fails to be a global chart and motivates why we restrict to local ones. **PASS.**
- **Metaphors controlled.**
  - "Like draping paper on the top of an orange" (0:48). Partial metaphor. NOTE: paper is rigid; in the picture the grid bends continuously. The metaphor captures the local-coverage idea but suggests the grid is a physical sheet, which it is not. Tag in production notes; do not narrate the limitation here — it would over-extend the scene.
- **Limit / edge cases.** The video deliberately does not address: dimension, the fact that there are infinitely many possible atlases, the equivalence relation defined by maximal atlases, smoothness classes other than $C^\infty$. These are correctly deferred to follow-up videos and not silently elided.
- **Has rigor been preserved across simplification?** Yes — every formal claim made on screen is correct as stated; the simplifications are at the level of the surrounding topology, which is explicitly out of scope for this audience tier.
- **[FORMAL]** vs **[INFORMAL]** classification.
  - 0:00–2:00: **[INFORMAL]** — establishes the phenomenon visually.
  - 2:00–2:40: **[FORMAL]** — chart definition.
  - 2:40–3:00: **[INFORMAL]** — object-vs-representation visual move.
  - 3:00–3:40: **[INFORMAL]** — second chart and overlap shown visually.
  - 3:40–4:50: **[FORMAL]** — transition map definition.
  - 4:50–5:00: **[FORMAL]** — smoothness condition.
  - 5:00–5:55: **[FORMAL]** — atlas definition.
  - 5:55–6:00: **[INFORMAL]** — closing reframe (this is rhetorical, not a theorem).

## 11. Quality-control checklist

- **Pedagogical:** PASS. Necessity-driven; misconception named at 1:50; cognitive load chunked; example-first followed by formalisation.
- **Visual:** PASS. Colour semantics consistent; continuity preserved (sphere persists across all scenes); transitions are morphs not cuts; ~5 distinct elements in the densest frame (5:20–5:40).
- **Mathematical accuracy:** PASS with documented NOTES (see §10).
- **Production readiness:** PASS. Modality declared per scene; Manim object inventory complete; generative clip and reference frames specified; voice-over polished version available; timing sums to 6:00 ± 5 s.

## 12. Optional variants

- **Short-form (90 s, vertical 9:16).** Drop scenes 4 and 6. Keep the tear, then jump straight to "we add a second chart, here's the atlas". Less rigorous but punchier; appropriate for social.
- **Advanced UG follow-up (10 min).** Add the maximal atlas, the equivalence relation between atlases, smoothness classes, and the formal definition of a smooth manifold. Use the same visual identity so the videos belong to one series.
- **Pure-Manim version.** Drop the GEN-S1-C1 opening clip; replace with a Manim-native title scene (`Text` over a slowly forming `Sphere`). Reduces production complexity; loses cinematic warmth.
