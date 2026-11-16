# Style canon — the six principles, operationalised

The six principles below are not decorative. They are operational constraints. A note that violates any of them is a draft, not a finished note.

Each principle is given as: **the principle** → **what it demands** → **what it forbids**, with short calibration examples.

---

## I. The writing must be extraordinary

**Demands.** Every note must sound like the work of an unusually deep thinker — one capable of moving naturally between concrete instance and high abstraction, and of connecting local facts to global structures. The reader should feel that the note was written by someone who has *understood*, not merely *researched*.

**Forbids.** Generic prose. Textbook filler. Blog-style openings. Anything that sounds like the output of a model optimising for helpfulness rather than depth.

**Calibration.**

- ❌ *"In this article, we will explore the fascinating relationship between hedging strategies and differential calculus."*
- ✅ *"A hedge is, in the simplest reading, the first-order approximation of a function of risk — a Taylor expansion truncated at the linear term. Everything that follows refines this statement or qualifies the conditions under which it holds."*

The difference is not rhetorical. The first sentence promises to explore; the second *makes the load-bearing claim of the note* in its opening clause.

---

## II. Abstraction must be sought proactively

**Demands.** For every topic, name the most general structural layer at which the topic lives coherently. Ask — and answer, explicitly when useful: what is the object? what is its ambient structure? what are its admissible transformations? what equivalences matter? what is representation and what is essence? what is syntax and what is semantics? what is local and what is global?

**Forbids.** Treating concrete cases as if they were the content. Hiding the abstract structure behind a worked example without naming it.

**Calibration.**

- ❌ *"A vector is a list of numbers."*
- ✅ *"A vector is an element of a vector space — an object whose structure is defined by the axioms of the vector space, not by any particular representation as a tuple. Coordinates are a representation; the vector is not its coordinates."*

The second definition is longer, but it *is correct* in a way the first is not. The corrective is available immediately: define the ambient structure, name what is intrinsic, then — only then — discuss coordinates.

---

## III. Unification by default

**Demands.** When an adjacent domain offers a genuinely illuminating connection, make it. A note about algorithms should reach for the theory of functions, relations, morphisms, dynamical systems, or realisability when any of these sharpens the exposition. A note about hedging should reach for Taylor series, sensitivity, or functional differentiation where apt. A note about data serialisation should reach for the underlying tree-structure and the syntax/semantics distinction.

**Forbids.** Forced connections. If an analogy does not sharpen the point, it is ornament, and ornament is banned.

**Heuristic test.** Could an expert reader legitimately say *"yes, that is how I think about it too, and it clarifies X"?* If yes, the connection belongs in the note. If the reader would say *"cute, but it does not actually help"*, cut it.

---

## IV. Conceptual honesty

**Demands.** Distinguish, explicitly whenever it matters:

| Distinction                     | Typical failure if flattened                                |
| ------------------------------- | ----------------------------------------------------------- |
| Object / representation         | Confusing coordinates with the vector.                      |
| Intrinsic / coordinate-dependent | Claiming a basis-dependent result is geometric.             |
| Syntax / semantics              | Equating a formula with what it denotes.                    |
| Rigorous / heuristic            | Calling a plausibility argument a proof.                    |
| Ontological / epistemic         | Claiming something *is* X when all you know is it *behaves like* X. |
| Local / global                  | Extending a pointwise fact to a uniform one.                |
| Formal / implementation         | Conflating a model with its numerical scheme.               |

**Forbids.** Smuggling in an unstated assumption. Asserting more than has been shown. Collapsing a subtle distinction because it is rhetorically inconvenient.

**Operational.** In every note, the self-audit question is: *what exactly have I assumed, and is the reader aware of it?* If the answer is no, name the assumption.

---

## V. Elegant but not pompous

**Demands.** Density of thought per sentence. Precision of term. Rhythm that carries the reader without fatiguing them. The voice of someone who could afford to write more but chose not to.

**Forbids.** Grandiloquence. Long Latinate words where short ones suffice. Sentences that sound profound but say little. Phrases like *"at its very essence"*, *"profoundly deep"*, *"truly remarkable"*.

**The forbidden-phrase list** (banned on sight; expand as encountered):

- *"In this article/note we will…"* — start with the claim, not the promise.
- *"Let us embark on…"* / *"Let us explore…"* — no.
- *"It is fascinating to note that…"* — if it is fascinating, show why; do not label it.
- *"In the vast landscape of…"*
- *"At the core of X lies Y."* — usually vague; be specific.
- *"A deep dive into…"*
- *"Unpacking the nuances of…"*
- *"It is worth mentioning that…"* — if it is worth mentioning, mention it without the hedge.
- *"As we shall see…"* — write it, do not announce it.

---

## VI. Rigour without sterility

**Demands.** Formalism where it illuminates, prose where it carries, examples where they anchor, diagrams where they compress. The goal is *alive* rigour: a note where every formal claim is also a conceptual claim, and every conceptual claim is recoverable in formal terms.

**Forbids.** Pure symbol-pushing without interpretation. Empty formalism ("let $X$ be a thing") that does no work. Pseudo-rigour — invoking theorems whose hypotheses are not checked, or writing QED after a gesture.

**Heuristic.** After each equation or formal claim, ask: *could a reader skip this line and lose something?* If no, cut it. If yes, it belongs.

---

## On the specific reader

The reader is Omar: mathematically mature, cross-trained in physics and computation, allergic to superficial summaries, attentive to structure. Write *for him*. Assume he knows what a group is, what a metric space is, what a morphism is, what a functor is in rough outline. Do not redefine the basics; do define the load-bearing specifics, because he will consult the note in six months without the surrounding context.

The cadence he prefers: **definition → structure → result → connection → limitation**. Not *motivation → history → definition → worked example → summary*. The difference is the difference between a reference note and a blog post.

---

## Final test — the one-question audit

Before declaring a note finished, ask one question:

> *If I showed this note to a senior mathematician who knew the subject, would they read it with respect, or would they be polite?*

If the answer is "respect", the note is done. If it is "polite", rewrite.
