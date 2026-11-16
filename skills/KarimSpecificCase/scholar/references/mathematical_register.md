# Mathematical register — notation, formalism, proofs

This file governs the mathematical register. It does two things: prescribe notation and explain *when* to formalise.

---

## When to formalise

Formalism is a tool, not a decoration. Introduce a formal object when one of the following holds:

1. **It sharpens a distinction** the prose cannot make cleanly. (E.g. distinguishing $\mathrm{dec}_{\mathrm{JSON}}$ from $\mathrm{dec}_{\mathrm{YAML}}$ as two different codecs on the same object class.)
2. **It supports a claim** that would otherwise be a hand-wave. (E.g. $\mathcal{L}(\mathrm{JSON}) \subset \mathcal{L}(\mathrm{YAML})$ is a formal statement; "JSON is a subset of YAML" is ambiguous.)
3. **It enables a derivation.** If a step is going to use $\sigma$-additivity, the measure must have been formally defined to have $\sigma$-additivity.
4. **It compresses.** A diagram or a commuting square can replace three paragraphs of prose and say the same thing without ambiguity.

Do **not** introduce formalism when:

1. The prose already carries the content unambiguously.
2. The symbol is introduced and never re-used.
3. The formalism is ornamental — invoking the categorial framing when the note never uses a functor.

---

## Notation conventions

### Sets and spaces

- Generic sets: $X, Y, Z$. Subsets: $A, B \subseteq X$.
- Elements: $x \in X$. Families: $\{x_i\}_{i \in I}$.
- Common spaces: $\mathbb{N}, \mathbb{Z}, \mathbb{Q}, \mathbb{R}, \mathbb{C}$.
- Function spaces: $C(X), L^p(X, \mu), \mathcal{H}$ for a Hilbert space.

### Functions and maps

- Definition: $f : X \to Y$.
- Action on element: $f(x)$ or $x \mapsto f(x)$ when emphasising the rule.
- Composition: $g \circ f$.
- Preimage: $f^{-1}(B)$. Inverse, if $f$ is invertible: also $f^{-1}$, but say so.
- Partial functions: $f : X \rightharpoonup Y$ (half-arrow).

### Categories and morphisms

- Category: $\mathcal{C}, \mathcal{D}$. Objects: $\mathrm{Ob}(\mathcal{C})$. Morphisms: $\mathrm{Hom}_{\mathcal{C}}(A, B)$ or $\mathcal{C}(A, B)$.
- Functor: $F : \mathcal{C} \to \mathcal{D}$.
- Natural transformation: $\eta : F \Rightarrow G$.
- Use categorial language only when it is doing work. *"Let $\mathcal{C}$ be a category"* with no further use of $\mathcal{C}$ is ornament.

### Measure and probability

- Measurable space: $(X, \Sigma)$. Measure: $\mu : \Sigma \to [0, \infty]$.
- Probability space: $(\Omega, \mathcal{F}, \mathbb{P})$. Random variable: $X : \Omega \to \mathbb{R}$, measurable.
- Expectation: $\mathbb{E}[X]$. Conditional: $\mathbb{E}[X \mid \mathcal{G}]$.

### Logic and quantifiers

- $\forall$, $\exists$, $\implies$, $\iff$, $\neg$, $\wedge$, $\vee$.
- Prefer prose over symbols in connecting sentences; reserve symbols for formal statements.

### Typography

- Inline math: `$...$`. Display math: `$$...$$` on its own paragraph.
- Bold for defined terms on first use: **measurable space**.
- `\mathcal{...}` for categories and distinguished spaces.
- `\mathbb{...}` for number sets and canonical spaces.
- `\mathfrak{...}` for $\sigma$-algebras, Lie algebras, ideals — when the convention is standard.

---

## Proofs and sketches

Three permitted modes. Label each.

### Full proof

Only when the result is load-bearing for the note and the proof fits in one screen. Structure:

> **Proposition.** *Statement.*
>
> *Proof.* Step 1: … Step 2: … Hence the claim. $\square$

### Sketch

For results whose full proof would distract. Make the label explicit:

> **Proposition.** *Statement.*
>
> *Sketch.* The key observation is that $\dots$. From this, standard arguments give $\dots$. A full proof appears in [standard reference].

### Pointer

For standard results. Do not reprove what a textbook proves.

> *By [Folland, *Real Analysis*, Theorem 2.14], every continuous function on a compact set is uniformly continuous.*

### What is forbidden

- Writing $\square$ after a non-proof.
- Invoking a theorem whose hypotheses are not checked.
- Using *"clearly"*, *"obviously"*, *"it is easy to see that"* to hide a step. If the step is easy, include it; if it is not, call it a sketch.

---

## Layering — the exposition technique

When a result admits definitions at multiple levels (elementary, formal, abstract), present them in order of increasing abstraction, each building on the last. The reader can stop at any layer and still have a correct understanding.

Template:

> **Layer 1 — intuition.** *Informal characterisation.*
>
> **Layer 2 — formal.** *Definition with symbols and axioms.*
>
> **Layer 3 — abstract** (when load-bearing). *Categorial or structural placement.*

Use this only when the gain is real. A pure definition does not need three layers if Layer 2 suffices.

---

## Diagrams and commutative squares

When a structural claim involves two or more arrows whose relation matters, a diagram compresses the claim. Use LaTeX/TikZ-compatible ASCII for inline diagrams; use the `latex-tikz-specialist` skill for anything formal:

```
      f
  X ─────> Y
  │        │
g │        │ h
  v        v
  Z ─────> W
      k
```

*"The diagram commutes"* means $h \circ f = k \circ g$. Say this explicitly when commutation is the claim.

---

## The labelling convention

- **Definition.** For formal definitions.
- **Proposition / Lemma / Theorem.** For claims, in order of relative importance (local / auxiliary / central).
- **Corollary.** For immediate consequences.
- **Remark.** For observations that are useful but not load-bearing.
- **Example.** For calibration.
- **Counterexample.** For boundaries.
- **Sketch.** For non-rigorous arguments.

The labels matter because the reader uses them to calibrate trust. An unlabelled argument reads as a claim; a sketch labelled *Sketch* reads as a sketch.

---

## Lastly — notational honesty

When a notational abuse is convenient, **say so**. Examples:

- *"We write $f$ for both the function and its image where no confusion arises."*
- *"By abuse, we identify $V$ with its double dual $V^{**}$ via the canonical isomorphism."*

The user is mathematically mature; he can follow an abuse that is declared. He cannot follow one that is silent.
