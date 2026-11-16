# Manual length and reordering — enforced discipline

This reference encodes two invariants of the `reflection-writer` skill that are easy to violate under token pressure or under superficial fidelity to the user's input:

1. **Length discipline** — notes are long-form manuals, not summaries.
2. **Ordering discipline** — disordered input is reordered before writing.

Both are *critical* constraints in `SKILL.md`. This file describes what the rules mean, how to detect violations, and how to apply the corrective procedure.

---

## 1. Length discipline — the manual standard

### What "manual" means here

A manual is a long-form document that a reader opens **once, in isolation**, and walks through end-to-end. By the end, the reader:

- Knows every technical term that appears in the note.
- Has seen at least one concrete example for each load-bearing mechanism.
- Has seen at least one diagram for each structural relationship.
- Has seen the formalism and the informal intuition in sequence.
- Can point to caveats, edge cases, and "gotchas" that any serious user will hit.
- Could reproduce the claims of the note on their own, consulting only the explicit prerequisites.

A summary, by contrast, compresses to keywords and one-line claims. Omar does not need summaries. OmarOS has indexes and MOCs for that. The reflection-writer exists to produce the *long-form thing an index points to*.

### Quantitative hints (not hard limits)

These are calibration points, not targets:

| Subject kind | Typical manual length |
|---|---|
| Tight two-object comparison (e.g. `yaml_vs_json`) | 400–700 lines |
| Deep single-object reference (e.g. `python_classes`) | 1000–2000 lines |
| Full subsystem manual (e.g. `python_asyncio`) | 1500–3000+ lines |
| Cross-language comparative synthesis | 800–2000 lines |
| Personal reflection | 200–800 lines |

If the draft is coming in under these ranges for a serious technical subject, the default assumption is that it is underdeveloped, not that it is "tight".

### Symptoms of under-development

Before emitting, sweep the draft for these signals:

- A mechanism is named without being *explained*. ("`await` cedes control to the loop" — but there is no paragraph on *what* the loop does with that control.)
- A consequence is stated without its cause. ("Therefore all ancestors in the call graph must be async" — without the prior derivation of *why*.)
- A formal object is introduced without its informal picture. (A monad with unit and multiplication, but no prose on what it feels like to *use*.)
- A formula appears but no example is worked through.
- A diagram appears but the prose does not reference or reconstruct it.
- A subsection is one or two paragraphs where peer subsections are four or five. (Usually a sign the author lost context mid-draft.)
- Cross-references are dropped ("see §V") where the current section needed the content *inlined*.

Each such signal triggers an expansion pass — not a rewrite, an *insertion*.

### What expansion looks like

Expansion is not padding. It is the addition of one of the following:

- A definition the text presupposed.
- An example that instantiates a formula.
- A counter-example that shows why a simpler claim fails.
- A derivation step the author skipped ("it follows that" → show the step).
- A caveat or edge case the reader will hit in practice.
- A diagram of a relationship that was only described in prose.
- A historical or architectural note that explains why the design is what it is.

If none of these apply, do not expand. But the honest default is that several do apply, and the discipline forces you to find them.

### The comprehensibility test

Before emitting, apply this test mentally: *a careful reader with the listed prerequisites, and nothing else, will understand this note end to end*. If you would need to tell that reader anything orally — "oh, and also Y, which I didn't write down" — then Y belongs in the note.

---

## 2. Ordering discipline — restore pedagogical order

### The problem

User input is almost never ordered like the output should be. Typical failure modes:

- **Forward reference without definition.** The user writes "and then `asyncio.run(main())` does X" three paragraphs before any introduction to what `asyncio` even is.
- **Consequence before mechanism.** The user concludes "therefore async is contagious" before having defined `await`.
- **Example before general.** The user pastes an `aiohttp` snippet before the reader has seen the primitive it builds on.
- **Technical aside in the orientation.** The user drops a deep detail about `nest_asyncio` in the opening paragraphs.
- **Scattered across a conversation.** The user pastes an AI chat that rediscovered the topic in a non-pedagogical order: what was discovered last belongs first.

Fidelity to the user's *content* is a core invariant. Fidelity to the user's *sequence* is not. The skill is expected to reorder.

### The topological sort procedure

Before drafting prose, perform this procedure:

1. **Atomize.** Go through the input and extract every atomic unit: a claim, a definition, an example, a diagram, a caveat, a cross-reference, a formula. Write each as a bullet. Do not merge yet.

2. **Mark prerequisites.** For each bullet, list the *other* bullets (or prerequisite concepts not yet in the list) that the reader must already have to parse this one. Add any missing prerequisites as new bullets. The graph is a DAG.

3. **Topologically sort.** Apply a topological sort. Ties are broken by pedagogical principle: orientation before comparison; informal intuition before formal definition; simple example before general case; mechanism before consequence; primitive before composite.

4. **Cluster into Movements.** Assign each sorted bullet to Movement I (orientation), II (terrain / prerequisites), III (substantive derivation), or IV (synthesis). Within each Movement, keep the topological order strict.

5. **Promote material up.** If a bullet that the user placed late in the input is a prerequisite for bullets the user placed early, it moves up. Aggressively. This is the operation the user usually cannot do themselves because they are already expert in the subject.

6. **Retire redundancies.** If two bullets say the same thing, keep the stronger statement and drop the other.

7. **Insert missing bullets.** If the DAG has dangling edges — a bullet depends on a prerequisite that is not in the input at all — the skill is responsible for generating that prerequisite. This is usually the bulk of the "filling gaps" work.

Only now draft prose against the sorted skeleton.

### Quick rules of thumb

- The first substantive section after the opening must be the *informal picture*, not the deepest technical detail.
- Every API name mentioned in the first two sections must either be *defined in those sections* or *forward-referenced with a brief one-line gloss*.
- A section that contains `asyncio.run` (or analogous API call) must not precede a section that introduces the module's overall shape.
- A formal monadic structure for a subject must not precede the concrete operational picture of that subject.
- Caveats and edge cases belong *after* the mainline mechanism, not interleaved with it.

### Signals the user wants aggressive reordering

Explicit triggers:

- "no está bien ordenado" / "está desordenado" / "not well ordered"
- "reordena esto" / "reorder this"
- "mételo donde toque" / "put it where it belongs"
- "haz un manual" / "make it a manual"
- "sin perder información" / "without losing information"

When any of these fire, the reordering pass is *mandatory*, even if the existing section numbering must be rewritten end-to-end and content promoted across section boundaries. The output numbering, the section headings, and the cross-references are all the skill's responsibility to re-derive.

Absence of these triggers does not mean ordering is fine. Still apply Step 1b. The procedure is cheap and catches silent disorder.

---

## 3. Interaction between the two disciplines

Length and ordering compound. A well-ordered short draft reveals gaps that the user did not notice were gaps; filling them grows the length. A long but disordered draft hides those gaps behind the clutter of misplaced material; reordering surfaces them.

So the pipeline is always:

```
atomize  →  topological sort  →  cluster into Four Movements
          →  detect gaps (missing prerequisites, missing informal picture,
                         missing examples, missing diagrams)
          →  fill gaps
          →  draft prose against the ordered skeleton
          →  comprehensibility sweep
          →  emit
```

A note that came in at 500 lines and goes out at 500 lines after this pipeline is a failure *unless* the 500 lines were already perfectly ordered and comprehensive. That case exists but is rare.

---

## 4. What this discipline is NOT

- It is not a licence to pad. Every added line must pass the expansion test (§1, "what expansion looks like").
- It is not a licence to invent content unfaithful to the source. Filling gaps means supplying prerequisites and derivations the user omitted, not inventing claims they never made.
- It is not a licence to ignore the user's conceptual framing. The content stays; the sequence changes.
- It is not a licence to be verbose for verbosity's sake. Prose should be dense — "every paragraph earns its place". Manual-length means no compression against comprehensibility, not bloat for its own sake.
