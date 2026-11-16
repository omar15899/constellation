# user_style/

Drop folder for Omar's reflections, notes, and explanations of how he likes to learn. The skill consults this folder, when non-empty, to absorb the user's intellectual style and pedagogical taste — but it does **not** copy the format of the reflections into the script. A video script has its own grammar.

## Layout

```
user_style/
  README.md                       ← you are here
  user_reflections.md             ← representative reflections / explanations
  preferred_learning_style.md     ← explicit preferences and anti-patterns
```

## How the skill uses this folder

When invoked, the skill checks whether `preferred_learning_style.md` exists and is non-empty. If so:

- It reads the file as a list of stylistic and pedagogical commitments (motivation from necessity, object-vs-representation discipline, abstraction emerging from examples, special cases, the pill of abstraction, …).
- It reads `user_reflections.md` (when present) for tone, register, and the kinds of intellectual moves Omar values.
- It applies these as design constraints — the script will *feel* like something Omar would respect, even though the script form differs from a written reflection.
- It does **not** quote, paraphrase, or imitate the literary form of the reflections in the narration.

If the folder is empty, the skill falls back to the defaults distilled in §7–8 of `SKILL.md`.

## Recommended seed content for `preferred_learning_style.md`

```markdown
# Preferred Learning Style

## Things I value
- Concepts motivated from necessity, not declared by fiat.
- Definitions arriving as the answer to a problem the viewer feels.
- Visual intuition that *leads to* formalism, not that replaces it.
- Rigor at the level of the mathematical object (not just the notation).
- Object vs representation kept explicitly distinct.
- A "pill of abstraction" after enough examples — the structural pattern revealed.
- Special cases used to illuminate the general; non-examples used when the boundary is subtle.
- A return to the original question at the end, with the new construction available.

## Things I dislike
- Generic explainer fluff: "buckle up", "let's dive in", "this is super important".
- Bullet-point reveals masquerading as explanation.
- Metaphors that are never reconciled with the formal object.
- Examples presented as if they were definitions.
- Hedging and apology in mathematical language.
- Slick visuals with no conceptual function.

## Audience self-model
- I am comfortable with high mathematical density.
- I learn best when an idea is built from necessity, then formalised, then exercised on a non-trivial example.
- I do not need motivational framing.
- I prefer the narrator to assume I am intelligent and to compress accordingly.
```

## Recommended structure for `user_reflections.md`

A small set of representative reflections (3–8 entries), each labelled by topic. The skill reads them for tone — vocabulary, sentence length, kinds of conceptual moves, balance of formal and informal — not as templates.

```markdown
# User Reflections

## On manifolds
<your written reflection>

## On stochastic integration
<your written reflection>

## On algorithm design
<your written reflection>
```

The skill will draw on these as a stylistic compass when designing the conceptual arc and choosing how to frame definitions. It will not copy the format.

## Hard constraint

Even when this folder is fully populated, mathematical correctness wins over stylistic alignment. If a stylistic preference would soften a definition or blur a quantifier, the preference is overruled.
