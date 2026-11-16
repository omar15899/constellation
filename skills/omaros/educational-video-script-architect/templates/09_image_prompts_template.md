---
title: "Image Prompts — <topic>"
note_type: video_image_prompts
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, image_prompts, <topic_tags>]
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

# Image Prompts — `<topic>`

DALL-E 3 / ChatGPT / generative-image prompts for the storyboard frames that will be rendered as reference images or production assets. Each prompt is **self-contained**: it works when copy-pasted into a fresh ChatGPT session (after the Global Style Reference has been sent).

Prompt IDs `I<NNN>` correspond to frame IDs `F<NNN>` in `08_storyboard.md`.

---

## §9.0 — Conceptual preamble

> *Plain-language statement of why image prompts must be self-contained, and why mathematically precise notation is **never** delegated to a generative model. Reference frames are for atmosphere, composition, and palette — not for symbolic content. ~80 words.*

---

## §9.1 — Engine and configuration

- **Model:** DALL-E 3 via ChatGPT (gpt-4o) — primary
- **Alternative engines:** Midjourney v6, Imagen, Flux — only if explicitly declared
- **Aspect ratio:** 16:9
- **Quality:** "hd" / "standard" — declare per-asset
- **Style:** "vivid" / "natural" — declare per-asset

---

## §9.2 — Global Style Reference

The user sends this single message first in the ChatGPT session. Every subsequent per-frame prompt assumes the engine has read this.

> ```
> You are generating a sequence of reference frames for a high-end educational video.
>
> Style anchors:
> - Background: <hex from 04_visual_language.md §4.1>, no decorative motion, no grain.
> - Palette (binding): <list every hex+role from 04_visual_language.md §4.2>.
> - Typography: <fonts from 04_visual_language.md §4.3>.
> - Tone: rigorous, technical, restrained. No marketing aesthetic. No gradients except where explicitly requested. No glow halos. No lens flare. No bokeh.
> - Mathematical notation: render at high contrast against the background. Use serif (Computer Modern) for math. Do not stylise the symbols.
> - Composition: clean, generous negative space, single focal element unless the frame is explicitly multi-panel.
> - Anti-patterns: no stock-photo people, no abstract gradient backgrounds, no neon, no cyberpunk vibes, no "AI-art" texture.
>
> When I send a per-frame prompt, render exactly what the prompt describes, applying the anchors above.
> ```

---

## §9.3 — Per-frame prompt blocks

For each frame in `08_storyboard.md` that requires an image asset, include one block. Frame ID and prompt ID are identical.

---

### I`<NNN>` — `<short description>`

| Field | Value |
|---|---|
| Frame | `F<NNN>` (in `08_storyboard.md`) |
| Scene | `S<n>` |
| Time | `<MM:SS>` |
| Tag | `<from script>` |
| Use | Reference-only / Production asset |
| Quality | hd / standard |
| Style | vivid / natural |

#### ChatGPT prompt (copy-paste verbatim)

> ```
> Render a 16:9 frame.
>
> Background: <hex>.
>
> Foreground content:
> - <central object>: <position — left/center/right + top/middle/bottom>, <size relative to canvas>, <colour hex>.
> - <supporting element 1>: <position>, <size>, <colour>.
> - <supporting element 2>: …
>
> On-screen text (render as rendered text, not a transcription):
> - "<exact string>" at <position>, <font>, <size>, colour <hex>.
>
> Composition discipline:
> - Generous negative space.
> - No gradients except <where explicitly allowed>.
> - No shadows, no glow, no flare.
>
> Mathematical notation (if any):
> - "<exact LaTeX>" rendered as Computer Modern serif at <position>, colour <hex>, <size>.
>
> Mood: <one short clause>.
>
> Strict exclusions: no people, no logos, no decorative texture, no AI-art aesthetic.
> ```

#### Manim production note

`<one or two lines stating what the Manim scene produces for this frame, and that the ChatGPT image is reference-only — symbolic precision lives in Manim>.`

---

## §9.4 — Coverage minima

At minimum, generate one image prompt per:

- Scene (cover frame at scene start).
- `[FORMAL]` definition appearance.
- `[INSTANCE]` worked example.
- `[BOUNDARY]` counter-example.
- `[CROSS_DOMAIN]` split-screen frame.
- `[ESSENCE]` apex frame.

For longer videos, add one image prompt per significant transition.

---

## §9.5 — Image-prompt freeze gate

- [ ] Every prompt is self-contained (works without prior context beyond the Global Style Reference).
- [ ] Every prompt is explicit about colours (hex), positions (left/centre/right + top/middle/bottom), exact text strings, and exclusions.
- [ ] No prompt asks the engine to render mathematically precise symbolic content as the production asset (Manim handles that).
- [ ] Prompt IDs match frame IDs in `08_storyboard.md`.
- [ ] At least the §9.4 coverage minima are met.
