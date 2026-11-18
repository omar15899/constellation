---
title: "Rigor Audit — <topic>"
note_type: video_rigor_audit
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
tags: [educational_video, rigor_audit, <topic_tags>]
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

# Rigor Audit — `<topic>`

The mandatory final pass before delivery. Every formal claim is verified. Every informal segment is tagged. Every doctrine pillar is checked against the script.

A failing audit is fixed *in the source artefacts* (00 to 10) and re-run. This file is regenerated each time.

---

## §11.0 — Conceptual preamble

> *Plain-language statement of why a separate rigor artefact exists, and why "the script is rigorous because the author is rigorous" is not enough. The audit is structural, not opinion-based. ~80 words.*

---

## §11.1 — Formal vs informal segment ledger

Every row in `05_narration_script.md` is classified.

| Row range | Tag | Classification | Justification |
|---|---|---|---|
| R001–R002 | `[HOOK]`, `[PREAMBLE]` | INFORMAL (intentional) | scene-setting metaphor; no formal claim |
| R003 | `[INFORMAL]` | INFORMAL (intentional) | extended metaphor |
| R004 | `[FORMAL]` | FORMAL | definition stated with full hypotheses |
| R005 | `[INSTANCE]` | FORMAL (worked) | substitution into the formal definition |
| R006 | `[RETRIEVAL]` | NEUTRAL | pedagogical prompt |
| R007 | `[SELF_EXPLAIN]` | NEUTRAL | pedagogical prompt |
| R008 | `[BOUNDARY]` | FORMAL (counter-example) | explicit failure of weakened condition |
| R009 | `[OBJECT_VS_REP]` | FORMAL (distinction) | object vs representation made visible |
| R010 | `[CROSS_DOMAIN]` | FORMAL (analogy declared partial) | structural correspondence stated, with limits |
| R011 | `[ESSENCE]` | FORMAL (apex) | single-sentence essence voiced verbatim |
| R012 | `[TRANSITION]` | NEUTRAL | inter-scene bridge |

**Discipline:** no row labelled INFORMAL ever carries the rhetorical weight of a FORMAL row. If a metaphor is partial, the script must name its limit.

---

## §11.2 — Mathematical-accuracy checklist

Run through `checklists/mathematical_accuracy_checklist.md`. For each item:

| # | Item | Status | Note |
|---|---|---|---|
| 1 | All hypotheses stated for every theorem | PASS / NOTE / FAIL | `<note>` |
| 2 | All quantifiers explicit | PASS / NOTE / FAIL | `<note>` |
| 3 | No example presented as a definition | PASS / NOTE / FAIL | `<note>` |
| 4 | Object-vs-representation discipline preserved | PASS / NOTE / FAIL | `<note>` |
| 5 | Notation register consistent across script | PASS / NOTE / FAIL | `<note>` |
| 6 | No coordinate-dependent claim presented as invariant | PASS / NOTE / FAIL | `<note>` |
| 7 | Boundary cases honest and accurate | PASS / NOTE / FAIL | `<note>` |
| 8 | Cross-domain echoes name their limits | PASS / NOTE / FAIL | `<note>` |
| 9 | Single-sentence essence is the categorical kernel, not a slogan | PASS / NOTE / FAIL | `<note>` |
| 10 | All `[FORMAL]` rows have full notation | PASS / NOTE / FAIL | `<note>` |

Any FAIL is fixed in the source artefacts and the audit re-run.

---

## §11.3 — Doctrine pillar checklist

| Pillar | Mechanic | Status | Evidence |
|---|---|---|---|
| I — Layered exposition | Every `[FORMAL]` row preceded by `[PREAMBLE]` | PASS / FAIL | `<row pairs>` |
| II — Jargon transparency | Every English technical term defined inline at first use | PASS / FAIL | reference §5.4 of script |
| III — Three-layer definitions | Every load-bearing concept across 3 layers | PASS / FAIL | reference §5.5 of script |
| IV — Cross-domain unification | At least one `[CROSS_DOMAIN]` row + 01_conceptual_blueprint §1.6 | PASS / FAIL | `<row + blueprint section>` |
| Master simplification | Single-sentence essence verbatim across files 00, 05, INDEX | PASS / FAIL | `<paste of the sentence in all three places>` |
| Hard constraint — rigor over engagement | No softened definition; no informal masquerading as formal | PASS / FAIL | `<scan of §11.1>` |

---

## §11.4 — Pedagogical-quality checklist

Run `checklists/pedagogical_quality_checklist.md` and report PASS / NOTE / FAIL per item, with a one-line note.

---

## §11.5 — Visual-quality checklist

Run `checklists/visual_quality_checklist.md` and report PASS / NOTE / FAIL per item.

---

## §11.5b — Visual creativity audit (from `style/visual_creativity_protocol.md`)

For each scene that contains conceptual content (i.e. not a pure transition), confirm:

| Scene | Brainstorm trace present in `03_scene_architecture.md`? | Inevitability test result | Frozen Frame test result | Animation richness (≥1 Layer 2–4 verb)? | Banned phrasings absent? |
|---|---|---|---|---|---|
| S1 | YES / NO | viewer infers: `<one sentence>` | textbook-quality still: YES / NO | YES / NO | YES / NO |
| S2 | … | … | … | … | … |

**Slide-paradigm audit:** scan `05_narration_script.md` "On-screen" column for any of the banned phrasings from `visual_creativity_protocol.md §5`. List occurrences here. Any occurrence is a FAIL until rewritten.

| Row ID | Banned phrasing found | Rewrite required |
|---|---|---|
| — | — | — |

**Distinct-scene audit:** could any two scene visual strategies be swapped without changing the video's meaning? If yes, list the offending pair; the scenes need re-imagination.

---

## §11.5c — Elite explainer audit (from `style/elite_explainer_doctrine.md`)

The video aspires to peerage with 3Blue1Brown, Veritasium, Quantum Fracture, Kurzgesagt, Steve Mould, Real Engineering. Audit the script against the twelve elite properties.

| # | Property | Status | Evidence / row reference |
|---|---|---|---|
| 1 | Narrative momentum: every scene ends raising a question the next answers | PASS / NOTE / FAIL | `<scene pairs checked>` |
| 2 | "I bet you didn't realise" moment present | PASS / FAIL | `<row + one-sentence summary of the surprise>` |
| 3 | Multimodal redundancy at every load-bearing definition (formal + geometric + instance) | PASS / FAIL | `<rows>` |
| 4 | Aesthetic identity consistent first frame to last | PASS / FAIL | `<spot-check stills>` |
| 5 | Patient reveal: foreshadowing → pressure → release | PASS / FAIL | `<foreshadow row, reveal row>` |
| 6 | At least one scale shift (≥1000× across some axis) | PASS / NOTE / FAIL | `<axis + factor>` |
| 7 | Physical correlate named for every load-bearing concept | PASS / FAIL | `<concept → correlate mapping from 00_declaration §0.5>` |
| 8 | Visual proof for every load-bearing claim | PASS / FAIL | `<claim → visual row>` |
| 9 | Cinematic production specified (sound, camera, pacing) | PASS / FAIL | `<reference to 07_voice_direction §X and production notes column>` |
| 10 | Editorial voice present (personality detectable on read-aloud) | PASS / FAIL | `<short paraphrase of the voice>` |
| 11 | Hook discipline: opening 10 s pose question or surprise; no preamble | PASS / FAIL | `<R001–R00X content>` |
| 12 | Iconic visual engineered, present in storyboard, anchored in [ESSENCE] | PASS / FAIL | `<frame ID + row>` |

**Aesthetic commitments cross-check** (against `00_declaration.md` §0.5):

| Commitment | Declared in declaration | Realised in script | Status |
|---|---|---|---|
| Iconic visual | `<copy>` | `<row + frame>` | MATCH / DRIFT |
| Reference creator | `<copy>` | `<scenes that reach for the signature>` | MATCH / DRIFT |
| Hook pattern | `<copy>` | `<opening rows>` | MATCH / DRIFT |
| Reveal moment | `<copy>` | `<row + quotable sentence>` | MATCH / DRIFT |
| Physical correlates | `<copy>` | `<rows where correlate is voiced + shown>` | MATCH / DRIFT |

**Anti-pattern scan** (from `elite_explainer_doctrine.md §11`). List any occurrences. Each occurrence is a FAIL until rewritten.

| Anti-pattern | Found at | Rewrite required |
|---|---|---|
| bullet-point reveals | — | — |
| stock images / icons | — | — |
| "in this video we will learn about…" | — | — |
| narration reading the formula verbatim | — | — |
| static frame > 3 s outside reveal pauses | — | — |
| cliché music swell with no semantic role | — | — |

**Final peerage test** (`elite_explainer_doctrine.md §13`):

> If 3Blue1Brown, Veritasium, Quantum Fracture, Kurzgesagt, and Steve Mould each watched this video, would all five recognise it as a peer's work?

Answer honestly: YES / NO / PARTIAL. If NO or PARTIAL, list the two weakest of the twelve properties and the revision plan.

---

## §11.6 — Production-readiness checklist

Run `checklists/production_readiness_checklist.md` and report PASS / NOTE / FAIL per item. Any FAIL blocks delivery.

---

## §11.7 — Validator script output

Set `CONSTELLATION_CHECKOUT` to your local Constellation checkout and
`PIPELINE_FOLDER` to the pipeline directory. In PowerShell, use `py -3` in
place of `python3`. Paste the output here verbatim. The validator checks file
presence, frontmatter validity, cross-references, ID stability and the
invariants from §11.3.

```
$ python3 "$CONSTELLATION_CHECKOUT/constellation.py" skill-run omaros educational-video-script-architect scripts/validate_pipeline.py "$PIPELINE_FOLDER"
<paste output>
```

---

## §11.8 — Residual concerns

A short list of things the audit cannot mechanically verify but that the auditor flags for the user's attention. Examples:

- "The boundary case in S3 may be too subtle for the chosen audience tier."
- "The cross-domain echo bridges domains the viewer may not know — consider an inline definition in the bridge sentence."
- "The pacing in S4 is tight; if the voice actor adds breath, slack becomes negative."

---

## §11.9 — Delivery decision

- ☐ **CLEAR FOR DELIVERY** — every checklist passes, no residual concerns block the user.
- ☐ **DELIVER WITH NOTES** — minor NOTE items remain; user is informed.
- ☐ **HOLD** — at least one FAIL; pipeline returns to the offending artefact.

Auditor: `<model-id>`
Date: `<YYYY-MM-DD>`
