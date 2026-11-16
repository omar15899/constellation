# Self-containment — the definitional discipline

A note produced by `reflection-writer` is an island. The user will consult it in six months without the surrounding vault open. Every term the note depends on must be defined inside the note — or, exceptionally, via a named pointer to a specific prior note.

This file gives the operational discipline: **when** to define, **at what depth**, and **how** to decide.

---

## The three layers of definition

A term can be defined at three layers. Notes should use the minimum layer that serves the argument, and upgrade when necessary.

### Layer 1 — intuition

A short informal characterisation that anchors the word. One or two sentences. No formalism.

> *A measure is a way of assigning sizes to subsets in a consistent manner.*

Layer 1 is always given for any term the reader could plausibly not have active in working memory.

### Layer 2 — formal

The standard formal definition. Symbols, types, axioms.

> *A measure on a measurable space $(X, \Sigma)$ is a function $\mu : \Sigma \to [0, \infty]$ satisfying $\mu(\emptyset) = 0$ and countable additivity: $\mu(\bigsqcup_i A_i) = \sum_i \mu(A_i)$ for any disjoint countable family $\{A_i\} \subseteq \Sigma$.*

Layer 2 is given whenever a term appears in a proof, a derivation, or any claim the note establishes formally. If the note's argument could be misread without Layer 2, Layer 2 is mandatory.

### Layer 3 — abstract / structural

The categorial, topological, or structural view that places the term inside a larger abstraction.

> *Measures are the morphisms in the Kleisli category of the Giry monad; $\mathrm{Meas}$ has measurable spaces as objects and measurable maps as morphisms, and $G X = \{$measures on $X\}$ gives a probabilistic extension of that category.*

Layer 3 is given **only** when the abstract view genuinely clarifies what follows. Never for ornament; never as a flex. If the note does not use the categorial structure, do not introduce it.

---

## The decision procedure

For each technical term $t$ the note uses:

1. **Is $t$ a standard term whose intuitive meaning a mathematically mature reader already holds?** (*metric*, *compact*, *continuous*, *derivative*, *group*.) If yes, no definition needed unless the note uses $t$ in a way that depends on a specific formal property.
2. **Is $t$ load-bearing for the argument of the note?** If yes, give at least Layer 1. Upgrade to Layer 2 if the argument uses properties not recoverable from the intuition.
3. **Does the note's main claim or synthesis use $t$ in its abstract structural form?** If yes, give Layer 3.
4. **Is $t$ used in a specialised sense specific to this note or to OmarOS?** If yes, say so explicitly: *"In this note, we use $t$ to mean…"*.

The working rule: **minimum layer that makes the note correct and unambiguous in isolation.**

---

## The first-use rule

A term is defined on **first use**, not at the end, not in a glossary, not in a footnote. The reader encounters the term and, in the same paragraph or the next one, finds its definition.

Violations to avoid:

- Using a term in Movement I without any definition, and defining it only in Movement II. Movement I can use a term *if* it gives a minimal Layer-1 characterisation in the same breath.
- Defining a term in a footnote or appendix. The reader's eye must not leave the main flow.
- Deferring the formal definition to "later" without saying when. If Layer 2 is needed, give it when the term becomes load-bearing.

---

## Worked audit — before and after

**Before** (bad):

> *Both JSON and YAML admit nested structures. JSON uses strict syntax with braces and brackets; YAML uses indentation. The main difference is parsing determinism.*

Failures: *nested structures* undefined; *strict syntax* undefined; *parsing determinism* undefined; the ambient category unnamed. A reader who opens this note cold cannot tell what the objects are.

**After** (corrected):

> *JSON and YAML are syntactic encodings of elements of $\mathcal{T}$ — the class of **finite labelled trees** whose nodes are either scalars, ordered sequences, or key-value mappings. Both formats provide a codec $\mathrm{enc} : \mathcal{T} \to \Sigma^{*}$ into strings of their respective alphabets; both are invertible via $\mathrm{dec}$. They differ in the properties of those codecs. The first such property is **determinism**: we call $\mathrm{dec}$ deterministic if the recovered tree depends only on the input string, not on the parser used to decode it. JSON's decoder is deterministic; YAML's, in general, is not — the same string can yield different trees under different parsers, because YAML performs type inference on unquoted scalars.*

Every technical term is defined, in layers appropriate to its role.

---

## When to pointer instead of define

Rarely. Use a named pointer only when:

1. The term has a canonical definition already written in a specific vault note, and
2. That definition is itself self-contained, and
3. The current note does not rely on the *detailed* properties of the term but only on its name.

Form of the pointer:

> *See [[measure_theory_foundations#measurable-space]] for the definition.*

Not:

> *(See my notes on measure theory.)*

The first is a specific link to a specific anchor; the second is a vague gesture. Only the first is acceptable.

---

## The self-containment pass

Before declaring a draft finished, run this pass explicitly:

1. Extract every technical noun that appears in the note.
2. For each, locate where it is defined (or pointed to).
3. For any that are used without definition, either define them inline or remove the usage.
4. For the load-bearing terms, check whether Layer 1 suffices or Layer 2 is needed.
5. For any Layer-3 definition, check that it genuinely illuminates; cut if ornamental.

This pass typically adds 10–20% to the note's length. That length is load-bearing: it is the price of durability.
