---
title: "Voice-over — <topic>"
note_type: video_voiceover
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, voiceover, <topic_tags>]
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

# Voice-over — `<topic>`

The clean narration block. This file is what the voice actor reads, or what is sent to a TTS engine, end to end. It carries no tables, no tags, no production notes, no markdown remnants. It does carry `[PAUSE Ns]` markers, paragraph breaks, and the occasional inline pronunciation hint.

This file is **derived from** `05_narration_script.md`. If they disagree, the script wins; this file is regenerated.

---

## Header (read once before recording)

- **Topic:** `<topic>`
- **Target duration:** `<MM:SS>` (matches `00_declaration.md`)
- **Total word count:** `<n>`
- **Target speech rate:** `<WPM>` words per minute
- **Voice register:** `<as declared in 00_declaration.md §0.6>`
- **Language:** `<English | Spanish>`
- **Pronunciation hints:** see end of file.

Instructions for the voice actor / TTS:

1. Pause exactly the marked number of seconds at every `[PAUSE Ns]` marker.
2. Render every em-dash (`—`) as a brief breath, not a long pause.
3. Mathematical notation written in plain text — read it as the corresponding mathematics, not the LaTeX source.
4. Italicised terms — emphasise lightly, do not over-pronounce.
5. Where two ways to read are possible, the pronunciation hint at the end of the file is binding.

---

## Voice-over body

> *Plain prose, end to end. Paragraphs separated by blank lines. `[PAUSE Ns]` markers inline. Em-dashes for inline definitions. Italics with `*single asterisks*` for emphasised terms. No headers, no bullets, no tables.*

`<paragraph 1 — opening hook>`

[PAUSE 1s]

`<paragraph 2 — first preamble metaphor>`

[PAUSE 1.5s]

`<paragraph 3 — first definition, with inline em-dash defining each English technical term at first use>`

[PAUSE 1.5s]

`<paragraph 4 — concrete instance>`

[PAUSE 3s — retrieval prompt: ask the listener to recall something, then continue>`

`<paragraph 5 — boundary case>`

[PAUSE 1s]

`<paragraph 6 — abstraction movement>`

[PAUSE 1s]

`<paragraph 7 — cross-domain echo>`

[PAUSE 1.5s]

`<paragraph 8 — single-sentence essence, voiced verbatim>`

[PAUSE 2s]

`<paragraph 9 — closing>`

---

## Pronunciation hints

| Term as written | Pronunciation | Note |
|---|---|---|
| `<term>` | `<phonetic>` | `<context>` |
| `Lebesgue` | "luh-BEG" | French mathematician, not "lee-besg" |
| `Cauchy` | "koh-SHEE" | … |

---

## Validation

- [ ] Total word count × 60 / target_WPM = target_duration ± 5%.
- [ ] Every `[PAUSE Ns]` marker corresponds to a row in `05_narration_script.md`.
- [ ] No markdown remnant (no `**bold**`, no `### header`, no table syntax) survives in the body.
- [ ] Every English technical term that appears is defined inline at first use.
