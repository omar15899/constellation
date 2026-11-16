---
title: "Storyboard — <topic>"
note_type: video_storyboard
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, storyboard, <topic_tags>]
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

# Storyboard — `<topic>`

Frame-by-frame description of the video's visual surface. Each frame is a still image that captures one atomic visual state. The storyboard is the bridge between `05_narration_script.md` (what happens when) and `09_image_prompts.md` / `10_manim_blueprint.md` (how each frame is materialised).

Frame IDs are stable; once assigned, they persist across edits.

---

## §8.0 — Conceptual preamble

> *Plain-language statement of why a frame-by-frame description, even when Manim will animate the in-betweens, is necessary. Frames are the load-bearing visual decisions; in-between motion is how those decisions are connected. ~80 words.*

---

## §8.1 — Frame index

| Frame ID | Time | Scene | Tag (from script) | Purpose | Production target |
|---|---|---|---|---|---|
| F001 | 0:00 | S1 | `[HOOK]` | establishing shot, title card | Manim |
| F002 | 0:05 | S1 | `[PREAMBLE]` | metaphor entry visual | Manim |
| F003 | 0:14 | S2 | `[FORMAL]` | first definition appears | Manim |
| F004 | 0:19 | S2 | `[INSTANCE]` | concrete example diagram | Manim |
| F005 | 0:30 | S3 | `[BOUNDARY]` | counter-example frame | Manim |
| F006 | 0:45 | S4 | `[CROSS_DOMAIN]` | split-screen cross-domain | Manim |
| F007 | 0:55 | S5 | `[ESSENCE]` | apex frame; central object alone | Manim |
| … | … | … | … | … | … |

Coverage rule: every distinct visual state in the video has a frame ID. Frame IDs are referenced from `05_narration_script.md` (Asset cue column) and from `09_image_prompts.md` (per-frame block).

---

## §8.2 — Frame cards

For each frame, fill one card.

### F`<NNN>` — `<short description>`

#### Identity

- **ID:** `F<NNN>`
- **Time:** `<MM:SS>`
- **Scene:** `S<n>`
- **Tag:** `<from §5.2 of narration script>`
- **Production target:** Manim / motion-graphics / generative reference / hybrid
- **Reference image needed?** yes (assigned `I<NNN>` in `09_image_prompts.md`) / no

#### Visual content

> *One paragraph (40–100 words) describing exactly what is on screen at this instant. Read like a museum caption: object, position, colour, motion state, on-screen text. No metaphor. No production lingo.*

#### Composition

```
[ASCII storyboard rectangle showing the rough composition]

  ┌────────────────────────────────────────┐
  │                                        │
  │   <central object>                     │
  │                                        │
  │           <supporting elements>        │
  │                                        │
  │   <on-screen text / formula>           │
  │                                        │
  └────────────────────────────────────────┘
```

#### On-screen text and notation

| Layer | Content | Position | Colour (hex) | Font / size |
|---|---|---|---|---|
| 1 | `<text>` | left/centre/right + top/middle/bottom | `<hex>` | `<font>` `<size>` |

#### Colour and palette references

Pull every colour from `04_visual_language.md` §4.2. A colour not in the palette is forbidden.

#### Motion entering this frame

- **From frame:** F`<NNN-1>`
- **Visual verb:** `<from §4.5 — fade-in / morph / write / etc.>`
- **Duration:** `<seconds>`
- **What changes:** `<concrete description>`

#### Motion leaving this frame

- **To frame:** F`<NNN+1>`
- **Visual verb:** `<…>`
- **Duration:** `<seconds>`
- **What changes:** `<…>`

#### Manim cue (if applicable)

```python
# Pointer to 10_manim_blueprint.md §<scene>.<object>
```

#### Reference-image cue (if applicable)

- **Asset ID:** `I<NNN>` in `09_image_prompts.md`.
- **Use:** reference-only / production asset.

---

## §8.3 — Storyboard freeze gate

- [ ] Every row in `05_narration_script.md` with a non-trivial visual change references a frame ID here.
- [ ] Every frame card has its composition sketched (ASCII or external file pointer).
- [ ] Every colour used is in the `04_visual_language.md` §4.2 palette.
- [ ] Every motion-in / motion-out uses a visual verb from `04_visual_language.md` §4.5.
- [ ] Frame IDs are unique and stable.
