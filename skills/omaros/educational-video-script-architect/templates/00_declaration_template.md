---
title: "Declaration — <topic>"
note_type: video_declaration
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, declaration, <topic_tags>]
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

# Declaration — `<topic>`

This is the **read-first** document. It is the contract between the user (Omar), the agent that produced the script, and any downstream agent or human collaborator who will execute the production. No technical artefact (files 01 to 10) should be consumed before this document is read in full.

The declaration answers four questions in order: **what** is being explained, **how** it is being explained, **why** it is being explained that way, and **what** the viewer must walk out understanding. Citations to the learning-research collection (see `learning_research/extracted_principles.md`) are provided where they shape the design.

---

## §0.1 — The single-sentence essence

> `<one sentence — max 25 words — stating the concept at maximum compression>`

This sentence is the apex of the synthesis movement in `05_narration_script.md` and is voiced verbatim. It is the categorical, universal-property, variational-principle, conservation-law or fixed-point statement that the entire video has been preparing the viewer to recognise. If this sentence is not yet truly minimal, the video does not yet understand the concept it is teaching — iterate.

---

## §0.2 — What is being explained

### §0.2.1 — Conceptual core

`<one paragraph — what the central object, theorem, phenomenon, algorithm or construction actually is. Stated at the rigorous-intuition layer — what it is, not yet how it is constructed.>`

### §0.2.2 — The misconception this video dissolves

`<one paragraph — what the typical learner believes (or implicitly assumes) that is wrong, partial, or coordinate-dependent, and that the video will replace with the correct invariant view.>`

### §0.2.3 — The promise to the viewer

`<one paragraph — what the viewer will be able to see, recognise, or compute by the end that they could not before.>`

### §0.2.4 — Prerequisites the viewer must already have

| Prerequisite | Layer | Where to acquire it if missing |
|---|---|---|
| `<topic>` | familiarity / working / fluent | `<reference>` |

Be honest. If a real prerequisite is missing, name it. Do not pretend the video is more accessible than it is.

---

## §0.3 — How it is being explained (the pedagogical route)

### §0.3.1 — Chosen explanatory structure

`<canonical 10-step | proof-oriented | computational | physics | finance | geometry | custom>`

### §0.3.2 — Pedagogical mode

`<problem-first | phenomenon-first | example-first | definition-first | proof-first>`

### §0.3.3 — The conceptual route in five beats

| Beat | Function | Visual engine | Tag |
|---|---|---|---|
| 1 | Necessity — build the conceptual pressure that makes the definition inevitable | `<visual>` | `[PREAMBLE]` |
| 2 | Object — show the central object before naming it | `<visual>` | `[INSTANCE]` |
| 3 | Definition — formalise; the object now has a name | `<visual>` | `[FORMAL]` |
| 4 | Boundary — show what fails when conditions are weakened | `<visual>` | `[BOUNDARY]` |
| 5 | Echo — surface the same structure in a different domain | `<visual>` | `[CROSS_DOMAIN]` |

### §0.3.4 — Concrete-to-abstract trajectory

`<one paragraph — where the explanation starts on the concrete-abstract axis, how it climbs, and what triggers each climb. Cite McNeil & Fyfe / Fyfe / Kokkonen on concreteness fading where it shapes the design.>`

### §0.3.5 — Layered exposition (Doctrine Pillar I)

For every dense formal beat in the script, name the metaphor that will carry the §X.0 conceptual preamble:

| Formal beat | §X.0 preamble metaphor | Visual support | Duration |
|---|---|---|---|
| `<definition / theorem / construction>` | `<analogy or working metaphor>` | `<visual element>` | `<8–25 s>` |

---

## §0.4 — Why it is being explained this way (the justification)

### §0.4.1 — Learning-science principles in play

Cite the principles from `learning_research/extracted_principles.md` and the rules from `learning_research/video_design_rules.md` that *visibly* shape the design. One or two sentences each — not a literature review.

| Principle | Source | How it shapes this video |
|---|---|---|
| Worked-example effect | Sweller 1988; Atkinson 2000; Renkl 2002 | `<scene where it applies>` |
| Concreteness fading | McNeil & Fyfe 2012; Fyfe 2014; Kokkonen 2022 | `<scene where it applies>` |
| Retrieval practice | Roediger & Karpicke 2006a/b | `<retrieval prompts in the script>` |
| Self-explanation | Chi 1989/1994 | `<why-prompt locations>` |
| Multimedia coherence + signalling | Mayer 2005/2024 | `<visual decision>` |
| Expertise reversal | Kalyuga 2003 | `<audience-tier adjustment>` |
| `<other>` | `<source>` | `<scene>` |

### §0.4.2 — Specific paper citations (only those actually consulted)

For each paper whose summary or full text was consulted while designing this video, give:

- **Citation:** `<AuthorYear, journal>`
- **Path:** `learning_research/papers/<category>/<file>.pdf` (or `summaries/<...>.md` if the summary was sufficient)
- **Claim relied upon:** `<one sentence>`
- **Where it appears in the script:** `<scene reference in 03_scene_architecture.md>`

### §0.4.3 — Why this route over alternatives

`<one paragraph — what other route was considered (e.g. definition-first), why it was rejected for this audience and topic, and what the chosen route preserves that the alternative would have lost.>`

### §0.4.4 — Cross-domain unification (Doctrine Pillar IV)

The bridge this video will surface — at least once, in the synthesis movement:

- **Bridge:** `<canonical bridge from style/ultra_formal_intuitive_doctrine.md §Pillar IV>`
- **Same-structure observation:** `<the precise correspondence — what the morphism, isomorphism, or analogy is>`
- **Where it appears in the script:** `<scene reference>`

---

## §0.5 — The pillars: what the video must contain (mandatory checklist)

Five-to-eight load-bearing items that the video must carry. This is the **content backbone**: if any pillar is not visibly addressed somewhere in `05_narration_script.md`, the video has failed. Each pillar receives its own row in `03_scene_architecture.md` and is tagged in `11_rigor_audit.md`.

| # | Pillar | Type | Mandatory artefact |
|---|---|---|---|
| 1 | `<load-bearing definition or theorem>` | definition / theorem / construction / principle | three-layer definition + concrete instance + boundary |
| 2 | `<…>` | … | … |
| 3 | `<…>` | … | … |
| 4 | `<…>` | … | … |
| 5 | `<…>` | … | … |

A pillar is not a topic. It is a **specific cognitive transformation** the viewer must undergo. "Define a manifold" is not a pillar; "see why a manifold is not its coordinate chart" is.

---

## §0.5b — Aesthetic commitments (from `style/elite_explainer_doctrine.md`)

The video aspires to peerage with 3Blue1Brown, Veritasium, Quantum Fracture, Kurzgesagt, Steve Mould, Real Engineering. These commitments are as binding as the conceptual pillars in §0.5 — the rigor audit (`11_rigor_audit.md §11.5c`) checks every one against the delivered script.

### §0.5b.1 — Iconic visual

> `<one sentence — the still image this video aspires to become in the viewer's memory. The image that, five years from now, will be recognisable as "the X video".>`

Examples of strong iconic visuals from the reference library: the slinky frozen mid-air with its bottom not yet falling (Veritasium); the stack of rotating circles tracing an arbitrary curve (3B1B Fourier); the grid deforming under a linear map with two eigenvectors held fixed on their lines (3B1B linear algebra); the cell zoomed-in scrolling out to the immune system (Kurzgesagt); the chain rising out of a beaker against gravity (Steve Mould).

### §0.5b.2 — Reference creator (the closest aesthetic register)

`<3Blue1Brown | Veritasium | Quantum Fracture | Kurzgesagt | Steve Mould | Real Engineering | Stand-up Maths | Two Minute Papers | mixed-with-dominant-X>`

One paragraph: why this creator's register fits the topic; which two or three signature techniques from `elite_explainer_doctrine.md §2.<i>` will be borrowed; which scenes carry them.

### §0.5b.3 — Hook pattern (the opening 10 seconds)

`<Puzzle | Wait-What Reveal | Promised Journey | Historical Anchor | Strange Phenomenon>`

One paragraph: what the opening visual is; what question or surprise it poses; why this pattern fits the topic. The script's `[HOOK]` row(s) must realise this commitment.

### §0.5b.4 — Reveal moment (the engineered climax)

- **Scene:** `<S<n>>`
- **Visual at the moment of reveal:** `<one sentence>`
- **Quotable sentence spoken at the reveal:** `<≤15 words, declarative, contains the categorical kernel>`
- **Foreshadowing rows earlier in the video:** `<R<x>, R<y>>`

The reveal is the engineered apex of the video. It is foreshadowed at least twice before it lands; it occupies its scene with deliberate pacing (silence on either side); it is the most cinematically composed frame in the video.

### §0.5b.5 — Physical correlate(s)

For every load-bearing concept in §0.5 above, name its physical correlate from `elite_explainer_doctrine.md §6.1` (or invent a new one with the same grounding role):

| Pillar # | Concept | Physical correlate | First on-screen at |
|---|---|---|---|
| 1 | `<concept>` | `<correlate>` | R`<NNN>` |
| 2 | `<concept>` | `<correlate>` | R`<NNN>` |

If a pillar has no plausible physical correlate, name that limitation here — and supply a *perceptual* correlate instead (a visual pattern the eye recognises) so the abstraction has at least one anchor.

### §0.5b.6 — Scale shift

`<axis (spatial / temporal / count / magnitude / resolution / dimensionality) — factor — scene>`

At least one scale shift somewhere in the video, of factor ≥1000× along some dimension. The shift is named here and realised in the script with the appropriate visual verb (`elite_explainer_doctrine.md §5.1`).

### §0.5b.7 — Multimodal redundancy layout

`<thirds split | main + sidebar | stacked | layered>`

The layout used at every load-bearing definition. Three registers (formal / geometric / instance) updating in lockstep. The chosen layout is binding for `04_visual_language.md` and `08_storyboard.md`.

---

## §0.6 — Production constraints declared up front

- **Modality:** `<manim | manim+motion | manim+generative | hybrid>`
- **Modality justification:** one sentence per modality used.
- **Hard exclusion:** symbolic precision is never delegated to a generative-video model. Every equation, label, coordinate, or formal annotation is rendered by Manim or motion graphics in post.
- **Estimated render budget:** `<low | medium | high>` Manim render time.
- **Voice register:** `<precise+curious | austere+formal | warm+professorial | conversational+wry | other>` (cross-check against the chosen reference creator in §0.5b.2)
- **Visual register:** `<dark+technical | bright+expository | cinematic+formal | flat-design-dense | hand-drawn-prop | other>` (cross-check against the chosen reference creator in §0.5b.2)
- **Cinematic production layer** (from `elite_explainer_doctrine.md §8`):
  - **Sound design:** ambient pad? music swells at the reveal? sound cues at scale shifts?
  - **Camera language:** dominant move (static / slow push-in / orbit / mixed)?
  - **Pacing curve:** declared per-scene WPM target in `07_voice_direction.md`?

---

## §0.7 — Risks and known weak points

Honest list of where this video might underperform and what would need to happen to fix it. Examples of the right granularity:

- *Risk:* the boundary case in §0.5 pillar 3 may be unintuitive to the target tier; consider an additional 20-second beat between scenes 4 and 5.
- *Risk:* the cross-domain echo bridges domains the viewer may not know; consider narrating "if you have not seen X, the analogy still works because…".

---

## §0.8 — What this declaration is *not*

- Not a literature review. Citations in §0.4 are one or two lines each.
- Not marketing copy. Every sentence must be defensible to a domain expert.
- Not the script. The script lives in `05_narration_script.md`. This document declares the intent that the script must realise.

---

## §0.9 — Approval gate

Before the agent proceeds to write files 01–10, the user reviews this document. The gate has three states:

- ☐ **APPROVED** — proceed to file 01.
- ☐ **REVISE** — adjust pillars / route / cross-domain bridge before proceeding.
- ☐ **REWRITE** — fundamental issue with the chosen direction; reopen Phase A.

Once approved, this document is frozen. Subsequent files reference it but do not amend it; if a substantive design choice changes, this document is reopened explicitly and the run log in `INDEX.md` records the reopening.
