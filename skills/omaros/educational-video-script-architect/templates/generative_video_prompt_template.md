# Generative Video Prompt Template

Use when any portion of the video is produced by a generative video model (Runway, Sora, Veo, Kling, Pika, or equivalent), or when generating reference clips for a Manim/motion-graphics composite.

---

## Hard rules

1. **No mathematical text inside generated video.** Generative models invent equations, smear symbols, and cannot be trusted with notation. All formal labels are added in post-production (Manim overlay, motion-graphics text).
2. **Every clip is reference-only by default.** Promote a clip to "production asset" only when there is no formal symbolic content in it.
3. **Style is locked across clips.** Define the style once, repeat the lock phrasing in every prompt.
4. **Continuity is fragile.** If two consecutive clips must depict the same object, either generate them as one continuous shot or use the model's image-to-video / first-frame conditioning. Note this explicitly per clip.
5. **Negative prompts are not optional.** Always include the standard negative prompt (below) plus clip-specific exclusions.

## Style lock (paste into every clip prompt)

> "Cinematic minimal mathematical studio. Deep dark background, soft volumetric lighting. Clean glowing geometry, vector-like quality, smooth motion. Educational scientific aesthetic. No people unless requested. No text overlays. No clutter. High contrast. 24 fps cinematic motion."

Adjust the style lock per project, but keep it identical across all clips of one video.

## Standard negative prompt (paste into every clip)

> "no text, no captions, no watermarks, no equations, no formulas, no labels, no human faces unless explicitly requested, no clutter, no random symbols, no distorted geometry, no flickering, no surreal artifacts, no melting forms, no inconsistent perspective, no chromatic aberration, no fisheye distortion."

## Per-clip prompt format

```
Clip ID:        S<scene>-C<clip>            e.g. S3-C1
Timestamp:      MM:SS–MM:SS
Duration:       <seconds>
Purpose:        <one sentence — why this clip exists in the video>
Use:            reference-only | production-asset
Continuity:     standalone | continues from <prior clip ID> | sets up <next clip ID>
First frame:    <image path or "model-decided">
Last frame:     <image path or "model-decided">

Prompt body:
"<style lock>. <subject and action over time, second by second>."

Action timeline:
0–<t1> s : <what is on screen>
<t1>–<t2> s : <what changes>
<t2>–<t3> s : <what changes>

Negative prompt:
"<standard negative prompt>, <clip-specific exclusions>."

Composite plan (post-production):
- Manim overlays added at: <timestamps within clip>
- Audio bed: <none | ambient pad | none — full mix in post>
```

## Worked example

```
Clip ID:        S3-C1
Timestamp:      01:10–01:18
Duration:       8 s
Purpose:        Establish a smooth curved surface receiving two overlapping coordinate patches; viewer should sense that two descriptions can coexist on the same region.
Use:            reference-only (Manim will add coordinate-line precision and labels in post)
Continuity:     standalone; sets up S3-C2
First frame:    model-decided
Last frame:     model-decided

Prompt body:
"Cinematic minimal mathematical studio. Deep dark background, soft volumetric lighting. Clean glowing geometry, vector-like quality, smooth motion. Educational scientific aesthetic. No people. No text overlays. No clutter. High contrast. 24 fps cinematic motion. A smooth curved two-dimensional surface floats centered in the frame; a translucent blue rectangular grid wraps onto a region of the surface; a second translucent amber rectangular grid wraps onto an overlapping region; the overlap area glows softly; the camera makes a slow steady push-in over the full duration."

Action timeline:
0–2 s  : the curved surface is alone, lit, slowly rotating by ~5 degrees
2–4 s  : the blue translucent grid materializes and conforms to the surface on the left side
4–6 s  : the amber translucent grid materializes and conforms on the right side, overlapping the blue grid in the central region
6–8 s  : the overlap region brightens softly; camera continues its slow push-in

Negative prompt:
"no text, no captions, no watermarks, no equations, no formulas, no labels, no human faces, no clutter, no random symbols, no distorted geometry, no flickering, no surreal artifacts, no melting forms, no inconsistent perspective, no chromatic aberration, no fisheye distortion, no inscribed numbers on the grid lines."

Composite plan (post-production):
- Add coordinate axis labels (x, y) on the blue patch and (u, v) on the amber patch via Manim overlay at 4 s and 6 s
- Add a small label "U ∩ V" on the overlap region at 6.5 s
- Audio: silent; full mix in post
```

## Generation strategy notes

- **Image-to-video conditioning:** for clips that must continue a prior shot, generate a single high-quality reference frame first (image model), then feed it as the first frame to the video model.
- **Multi-take strategy:** generate 3–5 takes per clip; pick the one with the best continuity and lowest artifact density.
- **Resolution:** request the highest the model supports; downsample only in final render.
- **Duration limits:** most current models cap at 5–10 s. For longer "shots", plan as a sequence of micro-clips with conditioning continuity.
- **Frame-rate normalization:** match the project's frame rate in post (typically 24, 30, or 60 fps).

## When NOT to use generative video

- The shot contains formal mathematical content the viewer must read precisely.
- The shot must depict a specific manifold, distribution, or object whose identity matters mathematically.
- The shot is a diagram with labelled parts.
- The shot is short enough that Manim or motion graphics can produce it cleanly.

In all these cases, switch the modality to Manim, motion graphics, or 3D, and remove the clip from the generative-video shot list.
