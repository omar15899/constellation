---
title: "Scene Architecture — <topic>"
note_type: video_scene_architecture
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, scene_architecture, <topic_tags>]
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

# Scene Architecture — `<topic>`

Pedagogical decomposition of the video into scenes. Each scene is a distinct **conceptual function**, not a topical chunk. The architecture is the contract the second-by-second script (`05_narration_script.md`) must realise.

---

## §3.0 — Conceptual preamble

> *Plain-language statement of the difference between a scene and a topic, and why this document is written before the second-by-second script. ~80 words.*

A scene corresponds to one cognitive transformation. The viewer enters the scene with one mental state and exits with another. The exit state is what the next scene takes as the entry state. If two adjacent scenes do not change the viewer's state, one of them is unnecessary.

---

## §3.1 — Architecture map

| # | Scene | Duration | Conceptual function | Entry state | Exit state | Modality | Pillar refs (from §0.5) |
|---|---|---|---|---|---|---|---|
| 1 | `<scene name>` | `<MM:SS–MM:SS>` | hook / motivation / informal intuition / definition / example / boundary / abstraction / re-grounding / synthesis | `<viewer state in>` | `<viewer state out>` | manim / motion / generative / hybrid | `<P1, P2, …>` |
| 2 | … | … | … | … | … | … | … |
| … | … | … | … | … | … | … | … |

Total runtime: `<MM:SS>` — must equal target duration in `00_declaration.md` ± 10%.

---

## §3.2 — Scene cards

For each scene, fill one card. The card is the bridge between the conceptual blueprint and the second-by-second script.

### §3.2.S`<n>` — `<scene name>`

#### Identity

- **Index:** `S<n>`
- **Range:** `<MM:SS>` to `<MM:SS>`
- **Duration:** `<MM:SS>`
- **Conceptual function:** `<hook | motivation | preamble | informal intuition | formal definition | worked example | boundary case | abstraction | re-grounding | cross-domain echo | synthesis>`
- **Pillar references:** `<P1, P3>` from `00_declaration.md` §0.5
- **Modality:** `<manim | motion-graphics | generative | hybrid>`

#### Entry state

> What the viewer knows / sees / feels at the start of this scene. One paragraph.

#### Exit state

> What the viewer knows / sees / feels at the end of this scene. One paragraph. Must be the entry state of S`<n+1>` or the closing state of the video.

#### Conceptual move

> The single transformation the scene performs. One sentence. If the scene cannot be reduced to one sentence, it is two scenes.

#### Visual strategy (trace of the Imagination Brainstorm)

> From the brainstorm in `style/visual_creativity_protocol.md §1`. Briefly record:
> - **Candidates considered (one line each):** e.g. "(A) secants collapsing to tangent; (B) local zoom revealing asymptotic straightness; (C) particle on track with velocity arrow".
> - **Chosen candidate:** the winner.
> - **Why it won:** the inevitability / audience-fit / conceptual-purity reasoning in one paragraph.
> - **Elite-creator signature borrowed** (from `style/elite_explainer_doctrine.md §2`): which creator would have scripted this scene and which of their signature techniques is in play — e.g. "3B1B continuous parametric morph + strategic silence; Veritasium predictive-engagement pause".
> - **Iconic frame within this scene:** one sentence describing the still that would represent this scene if it were the only one to survive.

This trace is the single most important record that the scene was *imagined* rather than *defaulted*. A scene whose visual strategy reads "object appears, definition follows" has skipped the brainstorm. Revise before continuing.

#### Visual engine

> Concrete realisation of the chosen candidate: the dominant motion verbs (from `04_visual_language.md §4.5`, preferring Layers 2–4), the driving parameter, the invariant. One paragraph + one ASCII storyboard sketch.

```
[ASCII sketch of the dominant visual — show the motion, not just the final frame]
```

#### Inevitability and frozen-frame checkpoints

- **Inevitability:** with narration muted, what would the viewer at the target tier infer? Write that inference in one sentence; it should match the conceptual move above. If it doesn't, the visual strategy is wrong.
- **Frozen frame:** pick one second of this scene; describe the still as if it were a textbook figure caption. If the description reads "a slide showing X", the visual engine is too static.

#### On-screen objects

| Object | Role | Persists from | Persists to |
|---|---|---|---|
| `<object>` | central / supporting / ephemeral | `<S<n-1>>` or "introduced here" | `<S<n+1>>` or "exits here" |

The persistence column enforces visual continuity across scenes (Doctrine — Pillar I support).

#### Layered exposition tags

| Time within scene | Tag | What is happening |
|---|---|---|
| 0:00–0:08 | `[PREAMBLE]` | metaphor lands |
| 0:08–0:18 | `[FORMAL]` | definition appears |
| 0:18–0:25 | `[INSTANCE]` | concrete example |
| 0:25–0:35 | `[BOUNDARY]` | boundary case |

Adjust per scene. Every scene with formal content has a `[PREAMBLE]` block before it.

#### Pedagogical devices in this scene

- **Retrieval prompt:** `<question + screen freeze duration>` or "none in this scene".
- **Self-explanation prompt:** `<question>` or "none".
- **Worked-example fading step:** step `<n>` of the ladder in `02_pedagogical_design.md` §2.5.
- **Signalling cue:** colour-flash / framed box / split-screen / etc.

#### Transition out

- **Type:** morph / fade / cut / overlay / zoom-out / zoom-in.
- **Visual continuity carried:** which object survives into the next scene.
- **Voice-over bridge:** the literal sentence that hands the viewer over to the next scene.
- **Pause on transition:** `<duration in seconds>`.

#### Risk and fallback

- **Risk if the scene over-runs:** `<consequence>` and `<scene to compress in compensation>`.
- **Risk if the scene under-runs:** `<beat to extend>` and `<duration ceiling>`.

---

## §3.3 — Architecture freeze gate

Before proceeding to `04_visual_language.md` and `05_narration_script.md`, verify:

- [ ] Every scene has a single one-sentence conceptual move.
- [ ] Every scene has a Visual Strategy trace (candidates considered + chosen + why) per `visual_creativity_protocol.md §1`.
- [ ] Every scene's Inevitability checkpoint produces a non-trivial inference from silent animation alone.
- [ ] Every scene's Frozen Frame checkpoint describes a textbook-figure-quality still, not a slide.
- [ ] Every formal scene has a `[PREAMBLE]` block scheduled before it.
- [ ] Every adjacent (S`<n>`, S`<n+1>`) pair has matching exit/entry states.
- [ ] The pillar coverage is complete: every pillar in `00_declaration.md` §0.5 is referenced by at least one scene.
- [ ] The total duration matches the target in `00_declaration.md` ± 10%.
- [ ] Every transition specifies the visual object that carries continuity.
- [ ] No two scenes have a visual strategy so similar that swapping them would not change the video.
