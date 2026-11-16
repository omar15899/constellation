---
title: "Pedagogical Design — <topic>"
note_type: video_pedagogical_design
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, pedagogical_design, <topic_tags>]
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

# Pedagogical Design — `<topic>`

The cognitive engineering layer. Translates the conceptual blueprint (`01_conceptual_blueprint.md`) into pedagogical decisions: which examples, in which order, with which retrieval prompts, with which fading schedule, with which self-explanation moments. Every decision here is justified by either a learning-research principle (cited) or by Omar's stylistic taste (cited).

---

## §2.0 — Conceptual preamble

> *Plain-language statement of what pedagogical design adds beyond the conceptual blueprint, and why it sits between the blueprint and the script. ~80 words.*

The blueprint says **what is true**. The script says **what to say at second 47**. The pedagogical design says **why second 47 holds an example rather than a definition**. Without this layer, the script becomes a sequence of locally good decisions that fail to add up to a globally good explanation.

---

## §2.1 — Audience model

### §2.1.1 — Tier and assumed background

- **Tier:** `<absolute_beginner | undergraduate | advanced_ug | research_expert | mixed>`
- **Concrete prerequisites assumed:** `<bullet list>`
- **Symbols assumed familiar:** `<list — every other symbol is defined on first use, per Doctrine Pillar II>`
- **Concepts assumed familiar:** `<list — every other concept gets a §X.0 preamble in the script>`

### §2.1.2 — Cognitive baseline

- **Attention budget:** `<minutes of dense focus the audience tier can sustain>` — aligns with target duration in `00_declaration.md`.
- **Working memory load tolerance:** `<low | medium | high>` — drives chunking decisions in §2.4.
- **Expertise reversal risk** (Kalyuga 2003): `<which scaffolding might harm experts and how it is removed at the right tier>`.

---

## §2.2 — Misconception map

For each misconception the typical viewer arrives with, give:

| # | Misconception | Source / why it is common | How the script dissolves it | Scene reference |
|---|---|---|---|---|
| 1 | `<…>` | `<…>` | `<beat / contrast / counter-example>` | `<scene>` |

The dissolve mechanism is **not** "tell the viewer they are wrong". It is to construct, visually, the situation in which the misconception fails — and let the viewer see it fail.

---

## §2.3 — Example-selection rationale

For each example used in the video, justify it.

| Example | Role | Why this example, in this order | Pedagogical principle invoked |
|---|---|---|---|
| `<example>` | introductory / structural / boundary / unification | `<one sentence>` | concreteness fading / interleaving / worked-example / etc. |

The discipline: an example is not chosen because it is "intuitive". It is chosen because it makes a specific structural feature **visible**, and because it occurs at a specific point in the concrete-to-abstract trajectory.

---

## §2.4 — Cognitive-load engineering (Sweller, Mayer)

### §2.4.1 — Chunking

- **Chunk granularity:** `<8–25 second beats>` — driven by audience tier.
- **Inter-chunk pauses:** `<1.0–2.5 s>` — at every definition, every result, every change of representation.
- **Re-encounter cadence:** the central object reappears at scenes `<list>` to lock the schema.

### §2.4.2 — Multimedia coherence (Mayer 2005, 2024)

- Voice and on-screen change are synchronised within ±0.3 s. (R9 in `learning_research/video_design_rules.md`.)
- No element on screen exists without a conceptual function.
- Background carries no decorative motion during dense moments.
- On-screen text duplicates voice-over only where signalling demands it; otherwise voice carries the prose, screen carries the structure.

### §2.4.3 — Signalling

| Signal | When deployed | Visual / audio device |
|---|---|---|
| New definition | every `[FORMAL]` block | colour-flash + 1 s pause + framed box |
| Boundary case | every `[BOUNDARY]` block | warning-tinted colour, "fails because…" voice-over |
| Cross-domain echo | once per major concept | split-screen + parallel-axis morph |
| Retrieval prompt | every major scene | screen freeze + on-screen question |

---

## §2.5 — Worked-example ladder (Atkinson 2000, Renkl 2002)

For novice-tier videos, the worked-example sequence is explicit. For expert-tier videos, this section justifies why the ladder is replaced by structural sketches.

| Step | Step type | Faded element | Why faded here |
|---|---|---|---|
| 1 | full worked example | nothing | establish the procedure |
| 2 | partial worked example | last step | viewer completes by mental rehearsal |
| 3 | partial worked example | last two steps | … |
| … | … | … | … |
| N | problem alone | all steps | confidence in pattern |

If the topic does not admit a worked-example ladder (e.g. an existence theorem), state so and describe the alternative scaffolding.

---

## §2.6 — Retrieval and self-explanation

### §2.6.1 — Retrieval prompts (Roediger & Karpicke 2006a/b)

| # | Where | Prompt | Time on screen | Voice-over treatment |
|---|---|---|---|---|
| 1 | end of scene `<n>` | `<question>` | `<3–5 s>` | "Pause for a moment — `<question>`" |

At least one retrieval prompt per major scene. The prompt is genuine: a viewer who pauses must be able to answer it without proceeding.

### §2.6.2 — Self-explanation prompts (Chi 1989/1994)

| # | Where | "Why" question | Visual cue |
|---|---|---|---|
| 1 | after definition `<n>` | "Why is this hypothesis necessary?" | dim the rest, highlight the hypothesis |

Used at every non-obvious move: a definition where the obvious weaker version fails; a proof step where a skipped detail matters; a representation shift where the choice is not forced.

### §2.6.3 — Calibration / metacognition (Panadero 2017, Metcalfe 2009)

Optional, used in longer videos. A 10–20 second beat where the viewer is asked to predict what happens next, before the script reveals it.

---

## §2.7 — Concreteness fading (McNeil & Fyfe 2012; Fyfe 2014; Kokkonen 2022)

The concrete-to-abstract trajectory of the video, scene by scene.

| Scene | Mode | Visual register | Notation density |
|---|---|---|---|
| 1 | concrete | intuitive metaphor | none |
| 2 | concrete | metaphor + diagram | sparse |
| 3 | bridging | metaphor fading + symbolic structure | growing |
| 4 | abstract | structural diagram only | dense |
| 5 | re-grounding | fresh concrete instance illustrating the abstraction | moderate |

The abstraction fades the concrete; the concrete returns at the end so the viewer can re-anchor.

---

## §2.8 — Interleaving and discrimination (Kornell & Bjork 2008; Birnbaum 2013; Rohrer 2012)

Used when the video distinguishes objects easily confused (manifold vs surface, martingale vs Markov, type vs class, etc.). For each distinction:

| Pair | Distinguishing structural feature | Interleaved presentation? | Where |
|---|---|---|---|
| `<A>` vs `<B>` | `<feature>` | yes / no | `<scene>` |

Interleaved presentation alternates A and B in the same scene rather than presenting all of A first. Use only when the distinction is the pedagogical point.

---

## §2.9 — Synchronisation contract

The narration↔visual sync rules that the script in `05_narration_script.md` must honour.

- **Definition appears on screen** at the *start* of the voice-over sentence that names it. Not after.
- **Visual change** that supports a sentence appears within ±0.3 s of the corresponding voice-over phrase.
- **Pauses** of 1.0–1.5 s after every definition, every result, every change of representation.
- **No notation appears during a `[PREAMBLE]` beat.** The preamble's only on-screen elements are the metaphor and any non-symbolic visual support.
- **Retrieval prompts** include a screen freeze of 3–5 s after the question lands.

---

## §2.10 — Pedagogical design freeze gate

Before proceeding to `03_scene_architecture.md`, verify:

- [ ] Every learning-research principle invoked is cited with paper and one-sentence rationale.
- [ ] Every example is justified by role and structural feature, not by appeal to "intuitive".
- [ ] The retrieval-prompt density is at least one per major scene.
- [ ] At least one self-explanation prompt at every non-obvious move.
- [ ] The concreteness-fading trajectory is named scene by scene.
- [ ] The synchronisation contract is explicit and is what the script will honour.
