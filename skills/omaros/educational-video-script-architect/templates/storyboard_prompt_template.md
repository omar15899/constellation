# Storyboard / Image-Generation Prompt Template

Use for reference frames produced by an image-generation model (Midjourney, Imagen, FLUX, Stable Diffusion, DALL·E, or equivalent). These frames serve as visual references for the implementer; they are **not** production assets unless explicitly marked as such.

---

## Hard rules

1. **No mathematical text in generated images.** Image models invent symbols and corrupt notation. All formal labels are added later by Manim or motion graphics.
2. **Style must be locked across all frames of one video.** Define the style once, repeat it in every prompt.
3. **Negative prompts are not optional.** Always include the standard negative block plus frame-specific exclusions.
4. **Reference-only by default.** Mark a frame as production-asset only when you are certain there is no formal symbolic content that the model could corrupt.

## Style lock (paste into every frame prompt)

> "Clean mathematical visualization, minimal dark studio background, deep space aesthetic, glowing vector-like geometry, high contrast, soft volumetric lighting, scientific educational style, no people, no text, no clutter, precise composition, suitable as storyboard reference for a mathematical animation."

Adjust per project, but keep identical across the frames of a single video.

## Standard negative prompt (paste into every frame)

> "no text, no captions, no labels, no watermarks, no equations, no formulas, no random symbols, no human faces, no clutter, no chromatic aberration, no fisheye distortion, no melted geometry, no incorrect mathematical notation, no handwritten text, no photorealistic classroom, no books, no whiteboards."

## Per-frame prompt format

```
Frame ID:       S<scene>-F<frame>           e.g. S2-F3
Timestamp ref:  MM:SS–MM:SS                 (the moment in the video this frame supports)
Purpose:        <one sentence>
Use:            reference-only | production-asset
Aspect ratio:   16:9 (default) | other
Conditioning:   none | based on frame <ID> | based on object <name>

Prompt body:
"<style lock>. <subject + composition + lighting>."

Negative prompt:
"<standard negative prompt>, <frame-specific exclusions>."

Implementer notes:
- <how the implementer should use this frame: rotoscope, trace as Manim guide, composite as background, etc.>
```

## Worked example

```
Frame ID:       S2-F3
Timestamp ref:  00:28–00:34
Purpose:        Reference for a coordinate chart wrapping a curved manifold; implementer will use this as a visual guide when composing the Manim 3D scene.
Use:            reference-only
Aspect ratio:   16:9
Conditioning:   none

Prompt body:
"Clean mathematical visualization, minimal dark studio background, deep space aesthetic, glowing vector-like geometry, high contrast, soft volumetric lighting, scientific educational style, no people, no text, no clutter, precise composition, suitable as storyboard reference for a mathematical animation. A smooth two-dimensional curved surface floats centered in the frame, gently lit from above-left. A translucent rectangular coordinate grid bends and conforms to a region of the surface, with glowing teal coordinate lines. The composition is open and uncluttered. The camera is slightly above the surface, angled down by ~25 degrees."

Negative prompt:
"no text, no captions, no labels, no watermarks, no equations, no formulas, no random symbols, no human faces, no clutter, no chromatic aberration, no fisheye distortion, no melted geometry, no incorrect mathematical notation, no handwritten text, no photorealistic classroom, no books, no whiteboards, no inscribed numerals on the grid."

Implementer notes:
- Use the lighting and palette as a colour reference for the Manim 3D scene.
- Do not import the image as a texture; rebuild the geometry in Manim's ParametricSurface.
- Keep camera angle and grid density consistent with this reference.
```

## Frame-batch generation

When generating reference frames for an entire video at once, group them by scene and supply a single shared style/negative prompt block, followed by per-frame deltas:

```
Video: <title>
Style lock: "<style lock>"
Negative prompt: "<standard negative prompt>"

Frames:
  S1-F1 — Title moment. <prompt body>
  S1-F2 — Phenomenon establishment. <prompt body>
  S2-F1 — Object in isolation. <prompt body>
  S2-F2 — Object with first chart applied. <prompt body>
  S2-F3 — Object with overlapping charts. <prompt body>
  ...
```

This keeps the visual identity consistent across frames and makes batch generation cheap.
