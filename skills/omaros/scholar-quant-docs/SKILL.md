---
name: scholar-quant-docs
description: Generate or extend scholar-grade documentation for the QuantOS quantitative research system (BacktestLab, MonteCarloLab, and the surrounding labs). Use this skill when the user says "document this MC module", "generate a scholar explanation of the X estimator", "write a deep report on the backtester architecture", "explain the stochastic driver hierarchy", "extend the QuantOS documentation corpus", "add a chapter on <model> to the corpus", "document the new RNG family I just added", or any request that produces a chapter under 05_Projects/QuantOS/Documentation/. Enforces the eight-section template, mathematical rigour, separation of implemented behaviour from target design, cross-linking discipline, and the distinguished voice of the QuantOS Vision documents. Produces output that another agent (or future-Omar) can pick up cold. Do NOT use this skill for (a) writing inside a Vision document directly — Vision is doctrinal and edited only by humans + decision-logger; (b) writing a research report on a study — use the research-pipeline templates (see research_pipelines/reports.md); (c) writing prose outside the QuantOS corpus — use scholar; (d) creating ADRs — use decision-logger.
license: Proprietary. OmarOS internal.
contract_invariants:
- Read first, write second. The skill never writes a chapter without first reading the relevant Vision document(s), the existing chapter (if any), and the implementation status in current_vs_target.md.
- 'Eight-section template is mandatory: §1 Problem statement, §2 Mathematical content, §3 Architectural realisation, §4 Invariants, §5 Failure modes (guarded vs not guarded), §6 Tests, §7 Extension points, §8 Cross-references. Sections may be merged in short chapters but never silently omitted.'
- 'Separation of implemented vs target. A chapter that documents code uses status flags (✓ implemented / ◐ partial / ▢ declared / ✗ contradiction) per current_vs_target.md. A chapter that documents target design carries status: target frontmatter.'
- Quote the slogan. Every chapter opens with a doctrinal or slogan-style blockquote attributed to the Vision document it operationalises.
- Frontmatter discipline. Every chapter carries title, status, note_type=documentation, domain=05_Projects, subdomain=QuantOS, project=QuantOS, component=BacktestLab|MonteCarloLab|... (when applicable), priority, confidence, ai_generated, ai_reviewed, created, updated, author, tags.
- Math is real. Every mathematical claim is stated with proper notation. Every non-trivial claim has at least a sketched proof or a reference to one. No vibes-based mathematics.
- Code paths are anchored. When a component is named, its code path under ~/GitHub/<Lab>/ is given. When a test is named, its file is given.
- 'Cross-references are explicit. Every chapter ends with a §Cross-references that links to: parent Vision document(s), sibling chapters in the corpus, ADRs, OPs.'
- Obsidian math syntax. $...$ inline, $$...$$ display. Never \(...\) or \[...\]. The Obsidian MathJax renderer treats backslash-paren as literal.
- Two-pass discipline. The skill first proposes the section outline + section-by-section plan; only after confirmation does it write the chapter. For continuous extensions of an existing chapter, the outline pass may be implicit.
- AI reading order updates. A new chapter that introduces a new task class or a new failure mode triggers an update to ai_reading_order.md.
- 'Scholar voice, not marketing voice. No ''this is robust''; instead ''this is robust because invariant I-X enforces …''. No ''this is general''; instead ''these specific assumptions were removed: …''.'
- When in doubt, link rather than restate. Vision docs and ADRs are canonical; the corpus links to them rather than re-stating them.
---

# Scholar Quant Docs

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Reusable protocol for generating or extending scholar-grade documentation
in the QuantOS corpus at `05_Projects/QuantOS/Documentation/`.

This skill is the *style-enforcer* for the corpus. Future agents tasked
with extending the documentation invoke this skill (explicitly or
implicitly) and inherit the corpus's voice, structure, and invariants.

The complete method and chapter template are defined below. Read the current
corpus and implementation as project data; the common Constellation entry owns
assignment, independent review and publication.

---

## When to invoke this skill

Use this skill when the user asks for any of:

- a new chapter in `05_Projects/QuantOS/Documentation/`;
- an extension of an existing chapter;
- a deep documentation pass on a newly implemented MC or BT module;
- a scholar-grade explanation of a stochastic process / numerical scheme
  / estimator / backend / metric within the QuantOS scope;
- a documentation-only response to a question like "explain X" where
  the answer should be permanent and corpus-resident.

Do **not** use this skill when:

- The destination is a Vision document. Vision is doctrinal; edits go
  via `decision-logger` (for ADR-bearing changes) or via human edit.
- The destination is an ADR. Use `decision-logger`.
- The destination is a research report on a specific study. Use the
  templates in `research_pipelines/reports.md`.
- The destination is outside QuantOS. Use `scholar` or `doc-coauthoring`.

---

## The protocol

### Stage 1 — Read

Before drafting, read:

1. `05_Projects/QuantOS/Documentation/index.md` — the corpus map.
2. `05_Projects/QuantOS/Documentation/ai_reading_order.md` — find the
   matching task class (B / C / D / F).
3. The relevant Vision document(s):
   - `05_Projects/QuantOS/Vision/00_Master_Vision.md`
   - `05_Projects/QuantOS/Labs/<Lab>/Vision/00_Doctrine.md`
   - `05_Projects/QuantOS/Labs/<Lab>/Vision/01_Architecture.md`
   - `05_Projects/QuantOS/Labs/<Lab>/Vision/05_Invariants.md`
4. Any existing version of the chapter being extended.
5. `05_Projects/QuantOS/Documentation/current_vs_target.md` — to know
   what flags (✓ / ◐ / ▢ / ✗) to apply.
6. The relevant code paths under `~/GitHub/<Lab>/` to anchor
   the chapter to reality.

If the relevant Vision document declares something the user is now
asking to document differently, **do not silently overwrite**. Surface
the contradiction; propose an ADR.

### Stage 2 — Outline

Propose the chapter's outline using the eight-section template:

1. Problem statement
2. Mathematical content (or architectural specification)
3. Architectural realisation (code-anchored)
4. Invariants
5. Failure modes (guarded vs not guarded)
6. Tests
7. Extension points
8. Cross-references

In short chapters, sections 4–7 may merge. They may **never be silently
omitted**. The outline is presented to the user for confirmation
unless the request is a continuous extension of an existing chapter.

### Stage 3 — Write

Write the chapter. Anchor every claim:

- Mathematical claims → notation + sketched proof + reference.
- Architectural claims → component name + code path + status flag.
- Invariant claims → invariant ID (I-N) + property test name.
- Cross-references → wikilinks to Vision and explicit ADR/OP IDs.

Voice: **scholar-grade, not marketing-grade**. No "this is robust";
say *because invariant I-X enforces …*. No "this is general"; say
*these specific assumptions were removed: …*.

Length: as long as needed; no shorter. The corpus's exemplar chapter
length is 200–500 lines for a substantive subsystem chapter; 100–200
lines for a shorter chapter (e.g. a single transform).

### Stage 4 — Cross-link

Update sibling chapters that should now link to the new chapter. At
minimum:

- The parent index (e.g. `monte_carlo/index.md`).
- The corpus root index (`index.md`).
- `current_vs_target.md` if the new chapter changes a status flag.
- `ai_reading_order.md` if the new chapter introduces a new task class.

### Stage 5 — Commit

Commit with a precise human message. Examples:

- `docs(monte-carlo): add chapter on Heston QE simulation`
- `docs(backtester): expand accounting chapter with multi-currency conservation`
- `docs(quantos): refresh current_vs_target after M1 RNG`

Granular: one chapter per commit (or one cohesive set of cross-links per
commit). Never bundle.

---

## The eight-section template (canonical form)

Copy this skeleton when starting a new chapter. Replace `<...>` markers
and remove sections only after confirming with the user.

```markdown
---
title: "<Subcorpus> — <Topic>"
status: active                # or: target
note_type: documentation
domain: 05_Projects
subdomain: QuantOS
project: QuantOS
component: <BacktestLab|MonteCarloLab|...>
priority: P1
confidence: high
ai_generated: true
ai_reviewed: false
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
author: Omar
tags: [project, quantos, <component>, documentation, <topic>, scholar]
---

# <Subcorpus> — <Topic>

> <doctrinal slogan or quote, attributed to a Vision document>

<one or two paragraphs introducing the chapter and its place in the corpus>

---

## 1. The problem

<state the problem the abstraction solves, in language a strong reader
who is new to QuantOS can follow>

## 2. <Mathematical / Architectural content>

<the substantive content of the chapter — definitions, propositions,
sketched proofs, derivations, or architectural specifications>

## 3. Architectural realisation

| Component | Status | Code path | Notes |
| --------- | ------ | --------- | ----- |
| ...       | ✓ / ◐ / ▢ / ✗ | ... | ... |

## 4. Invariants

<which named invariants this chapter touches; how they are operationalised>

## 5. Failure modes

**Guarded.**
- ...

**Not guarded.**
- ...

## 6. Tests

| Invariant | Test | Tolerance | File |
| --------- | ---- | --------- | ---- |

## 7. Extension points

<how a future agent should extend>

## 8. Cross-references

- Vision: [[../../Vision/...]]
- Sibling chapters: ...
- ADRs: ...
- OPs: ...
```

---

## Anti-patterns (do not produce)

The following patterns are **rejected** at review:

- A chapter that describes code without explaining the abstraction's
  *purpose*.
- A chapter that lists what the code does without explaining *why this
  abstraction and not an alternative*.
- A chapter that says "robust" without naming the invariant.
- A chapter that says "general" without listing the assumptions removed.
- A chapter that hides uncertainty (e.g. silently presents a target as
  implemented).
- A chapter that omits the Cross-references section.
- A chapter that uses `\(...\)` or `\[...\]` math delimiters (Obsidian
  treats these as literal).
- A chapter that introduces a new task class without updating
  `ai_reading_order.md`.
- A chapter that introduces a new invariant without updating the relevant
  Vision Invariants document.

---

## Authoritative references

- Corpus root: `05_Projects/QuantOS/Documentation/index.md`
- AI reading order: `05_Projects/QuantOS/Documentation/ai_reading_order.md`
- Current vs target: `05_Projects/QuantOS/Documentation/current_vs_target.md`
- First-principles overview: `05_Projects/QuantOS/Documentation/quantos_from_first_principles.md`
- Conceptual map: `05_Projects/QuantOS/Documentation/conceptual_map.md`
- Skill (this file): `/Users/omarkhalil/GitHub/Constellation/skills/omaros/scholar-quant-docs/SKILL.md`
- ADR introducing the corpus: `05_Projects/QuantOS/Decisions/ADR-0028-documentation-corpus.md`

---

## Cross-references to other skills

- `scholar` — the general long-form writing surface for the OmarOS vault.
  This skill is the QuantOS-specific specialisation.
- `decision-logger` — for ADRs, including ADRs that authorise corpus
  structural changes.
- `doc-coauthoring` — for documents whose primary reader is *not* a
  future agent or future-Omar.
- `latex-tikz-specialist` — for any TikZ figures in the corpus.
- `md-grapher` — for Mermaid diagrams in the corpus.
