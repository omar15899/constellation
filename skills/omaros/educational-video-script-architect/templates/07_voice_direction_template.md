---
title: "Voice Direction — <topic>"
note_type: video_voice_direction
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, voice_direction, <topic_tags>]
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

# Voice Direction — `<topic>`

The companion file to `06_voiceover.md`. Tells a voice actor (or a TTS engine with style controls — ElevenLabs, OpenAI TTS, Cartesia, etc.) **how** to speak each segment: tone, pacing, intensity, emotional register, micro-pauses, prosody.

Every row corresponds to a row range in `05_narration_script.md` and a paragraph or `[PAUSE]` marker in `06_voiceover.md`.

---

## §7.0 — Conceptual preamble

> *Plain-language statement of why a perfectly-written voice-over still fails if the voice direction is wrong, and why we treat voice direction as a separate artefact instead of inline annotations. ~80 words.*

The voice carries the rhetorical weight that the words alone cannot. A `[FORMAL]` block read with the same prosody as a `[HOOK]` block tells the listener that the formal definition is no different from the hook — and the explanation collapses. Voice direction encodes the score on top of the lyrics.

---

## §7.1 — Master register

The video-wide voice register is set in `00_declaration.md` §0.6. Restate it here for the voice actor.

- **Persona:** `<precise & curious | austere & formal | warm & professorial | other>`
- **Reference voices (for calibration):** `<e.g. Robert Sapolsky lecturing; Matthew Walker; 3Blue1Brown; Steven Strogatz; …>`
- **Default tempo:** `<WPM>`
- **Default pitch range:** `<low / mid / high>` and `<narrow / wide>` modulation.
- **Breath discipline:** `<slow audible breath at every paragraph break | invisible breath only | …>`

---

## §7.2 — Tag-driven prosody atlas

A direct mapping from the tag system in `05_narration_script.md` to vocal treatment. Apply automatically wherever the tag appears.

| Tag | Tempo | Pitch | Intensity | Modulation | Pause profile |
|---|---|---|---|---|---|
| `[HOOK]` | medium-fast | mid, slight rise | 0.75 | wide | none before; hard punctuation |
| `[PREAMBLE]` | slow | mid-low, soft | 0.55 | medium | 0.5 s breath before |
| `[FORMAL]` | very slow | low, deliberate | 0.85 | narrow (precision) | 1.5 s pause after |
| `[INSTANCE]` | medium | mid, anchored | 0.7 | medium | 0.5 s after |
| `[BOUNDARY]` | medium-slow | mid-low, weighted | 0.75 | narrow | 1.0 s after |
| `[CROSS_DOMAIN]` | medium, brightening | rising mid | 0.8 | wide (excitement under control) | 1.5 s before |
| `[ESSENCE]` | very slow, weighted | low, near-monotone | 0.95 | very narrow (gravitas) | 2.0 s before, 2.0 s after |
| `[RETRIEVAL]` | medium | mid, slight invitation | 0.6 | medium | 3.0 s after |
| `[SELF_EXPLAIN]` | slow | mid-low, contemplative | 0.6 | narrow | 2.0 s after |
| `[INFORMAL]` | medium | mid, animated | 0.65 | wide | natural |
| `[OBJECT_VS_REP]` | slow | low, emphatic | 0.8 | narrow | 1.0 s after |
| `[TRANSITION]` | medium-fast | mid, descending | 0.5 | medium | 1.0 s after |

Intensity is a 0–1 scalar for emotional pressure, not volume. Volume is roughly constant across the whole video; pressure varies.

---

## §7.3 — Segment table (per-row direction)

For every row range in `05_narration_script.md`, give the voice actor a one-line note that overrides or refines the tag-driven default.

| Script row(s) | Tag | Direction (one line) | Pronunciation flag |
|---|---|---|---|
| R001 | `[HOOK]` | "Curious, slightly conspiratorial — like inviting a friend into a puzzle." | — |
| R002 | `[PREAMBLE]` | "Quiet, almost confiding. Slow the metaphor down." | — |
| R004 | `[FORMAL]` | "Drop pitch and tempo. Let the definition land alone." | "Lebesgue" — see pronunciation hints |
| R006 | `[RETRIEVAL]` | "Genuine invitation, not rhetorical. The pause is for the listener, not for you." | — |
| R010 | `[CROSS_DOMAIN]` | "Surface delight at the recurrence — the same shape, in a new costume." | — |
| R011 | `[ESSENCE]` | "Slowest line of the entire video. Treat it as the apex it is." | — |
| … | … | … | … |

---

## §7.4 — TTS profile (when narration is synthesised)

If the voice-over will be sent to a TTS engine, declare the profile here so the engine call is reproducible.

- **Engine:** `<ElevenLabs | OpenAI TTS | Cartesia | Azure | other>`
- **Voice ID:** `<voice id>`
- **Stability / similarity / style sliders:** `<exact values>`
- **Speed:** `<scalar>`
- **Pause handling:** `<engine-specific syntax — e.g. ElevenLabs `<break time="1.5s"/>` SSML>`
- **Per-tag overrides:** if the engine supports style prompts mid-text, embed them in `06_voiceover.md`'s body using the engine's syntax. Document the mapping here.

---

## §7.5 — Voice direction freeze gate

- [ ] Every tag from §7.2 has explicit prosody parameters.
- [ ] Every `[ESSENCE]` and `[CROSS_DOMAIN]` row in `05_narration_script.md` has a per-row direction line in §7.3.
- [ ] If a TTS engine is used, the §7.4 profile is complete and reproducible.
- [ ] Pause durations in §7.2 are consistent with `[PAUSE Ns]` markers in `06_voiceover.md`.
