# Production Blueprint Template (Hybrid / Motion Graphics / Live Coding)

Use for the parts of the script that aren't covered by the Manim or generative-video templates — motion-graphics editing (After Effects, Motion, DaVinci Fusion), Blender 3D, screen-capture / live-coding, slide-based segments, or hybrid composition.

---

## Modality matrix

For each scene, declare:

| Scene | Primary modality | Secondary modality | Composite plan |
| --- | --- | --- | --- |
| 1 — Intro | motion graphics (After Effects) | — | text + background loop only |
| 2 — Phenomenon | generative video | motion graphics (overlay) | gen clip → AE composite → final mix |
| 3 — Object | Manim 3D | — | pure |
| 4 — Definition | Manim 2D | — | pure |
| 5 — Examples | Manim 2D | screen-capture (live coding) | side-by-side composite |

## Asset inventory

A flat list of every asset the production needs, regardless of source:

| Asset ID | Type | Source | Used in scenes | Status |
| --- | --- | --- | --- | --- |
| BG-01 | background loop | After Effects | 1, 6, 10 | to produce |
| GFX-tit | title card | After Effects | 1 | to produce |
| GEN-S2-C1 | reference clip | generative video | 2 | to generate |
| MAN-S3-A | manifold scene | Manim | 3 | to render |
| CODE-S5-1 | code snippet capture | OBS / ScreenFlow | 5 | to capture |
| AUD-VO | voice-over track | TTS or recorded | all | pending |
| AUD-BED | ambient audio bed | stock library | all | to license |

## Motion-graphics blueprint (After Effects / Motion / Fusion)

For every motion-graphics segment:

- **Composition name** and resolution / frame rate
- **Layer structure**, top-to-bottom: text, vector shapes, masks, adjustment layers, background
- **Text overlays:** content, font, weight, size, colour, in/out animation (slide, fade, type-on)
- **Diagram assets:** SVG sources, parameter overrides
- **Timing markers:** keyframe positions in seconds
- **Transitions in / out** to neighbouring segments
- **Compositing notes:** blend modes, mattes, track mattes, expressions
- **Render settings:** codec, alpha, frame rate

## 3D blueprint (Blender / Houdini / Cinema 4D)

For every 3D segment:

- **Scene file** name and software version
- **Geometry sources:** primitives, parametric, imported mesh
- **Materials:** PBR roughness / metallic, emission for glowing geometry
- **Lighting setup:** key, fill, rim, environment HDRI (if any)
- **Camera path:** keyframes, FOV, aperture
- **Animation drivers:** procedural (geometry nodes), hand-keyed, simulation
- **Render engine:** Cycles, Eevee, Redshift, etc., with sample count and resolution
- **Export format:** image sequence (PNG with alpha), or .mov
- **Performance:** flag any scene with simulation, particles, or expensive shading

## Live-coding / screen-capture blueprint

For every code-on-screen segment:

- **Editor + theme:** font, font size, colour scheme (must match the video's palette)
- **Window setup:** terminal, browser, REPL, plot pane
- **Capture tool:** OBS, ScreenFlow, native macOS recorder
- **Code snippets to reveal:** literal text, in order, with timing
- **Cursor / camera behaviour:** zoom levels, follow cursor, fixed frame
- **Highlighting logic:** when to underline, when to dim other code, when to expand
- **What to hide:** boilerplate, imports, irrelevant noise
- **What to expose:** the conceptual line(s) that matter

If the live-coding is faked (i.e., pre-typed and animated), say so and switch to motion-graphics blueprint for that segment.

## Slide-based segments (when used)

Only when slides genuinely serve the explanation (rare). Each slide:

- Title (optional)
- Body content (text, equation, image)
- Transition in / out
- Hold duration
- Voice-over alignment

Avoid slide-only videos. The skill's commitment is to dynamic visual explanation, not bullet-point reveals.

## Compositing plan

For scenes with multiple modalities, specify the composite stack from bottom to top:

```
Scene 2 — Phenomenon establishment
  Layer 1 (bottom): generative-video clip GEN-S2-C1 (reference, full-frame)
  Layer 2:          colour grade adjustment (slight warm tint, +5% saturation)
  Layer 3:          Manim overlay MAN-S2-O1 (label "ϕ: U → ℝ²" appears at 0:18)
  Layer 4:          motion-graphics text GFX-S2-T1 ("phenomenon: <name>") at 0:00
  Layer 5 (top):    transition matte to scene 3
```

## Audio plan

- **Voice-over:** mic / TTS engine, target loudness (e.g., -16 LUFS integrated for streaming)
- **Music bed:** licence source, intensity envelope
- **Sound design:** UI clicks, transitions, "definition appears" cue, "abstraction" cue
- **Mix:** ducking VO under SFX/music

Audio is part of the synchronization contract: voice-over must hit the same instant as the visual event it describes.

## Final delivery

- **Master codec:** ProRes 422 HQ (intermediate), H.264 / H.265 (delivery)
- **Resolution / frame rate:** 1920×1080 @ 60 fps (default), or 4K when warranted
- **Captions:** SRT generated from the voice-over-only version (§9 of the script)
- **Thumbnail:** which storyboard frame to use, with a possible re-shoot brief

## Open questions for the production team

If anything depends on a choice the production team must make (modality fallback, asset budget, music licensing), enumerate it here. Do not bury it in prose.
