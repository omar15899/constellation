# The Four Movements — structural template

Every note produced by `reflection-writer` follows the same four-movement structure. It is the document-level encoding of the *object-before-comparison* discipline. The structure is not flexible; its contents are.

---

## Movement I — Orientation

**Purpose.** Tell the reader what class of objects we are in, what the specific objects are, and what question or claim the note is about.

**Length.** One to three paragraphs. Never longer. Never skipped.

**Must contain, in this order:**

1. **The ambient category.** The *class* the objects belong to. (*"JSON and YAML are representation systems for finite labelled trees."* / *"A hedge is a functional approximation applied to a map from market states to portfolio value."*)
2. **Minimal definitions of the objects in play.** One sentence each, enough to anchor the noun. Full definitions live in Movement II.
3. **The claim or question.** The single load-bearing sentence the rest of the note will justify or refine.

**Failure modes.**

- Starting with a comparison *before* the category is named. This is the default failure and the one we are explicitly correcting.
- Starting with history, motivation, or a hook. Strip these; they belong in an afterword, if anywhere.
- Stating the claim so vaguely that the reader cannot tell what the note will establish.

**Example — the opening of a note on JSON vs YAML:**

> JSON and YAML are both syntactic systems for representing the same mathematical object: finite labelled trees with scalar, sequence, and mapping nodes. JSON is the canonical, rigid, machine-oriented encoding; YAML is the expressive, human-oriented encoding that includes JSON as a proper subset. This note establishes the precise sense in which the two encode the same structures while differing in determinism, ambiguity, and operational role, and catalogues the full set of syntactic constructs each accepts.

Three sentences. Category → objects → claim. Movement I complete.

---

## Movement II — Terrain

**Purpose.** Lay out the formal and structural landscape. Define every load-bearing term. Introduce the formalism that will carry the analysis.

**Typical contents.**

- Formal definitions of the objects introduced in Movement I.
- The ambient mathematical structure (space, category, algebra, graph, language, …).
- Primitive constructors and composition rules.
- Invariants, equivalences, admissible transformations.
- Tables of correspondences.
- Enumerated properties.

**Rule of thumb.** A reader who reads only Movements I and II should already possess the landscape, even if they stop there. Movement II is the skeleton; Movement III is the muscle.

**Worked mini-example.** For a note on *measurable functions*:

> A **measurable space** is a pair $(X, \Sigma)$ where $\Sigma \subseteq 2^X$ is a $\sigma$-algebra on $X$ — a collection closed under countable unions, intersections, and complements. A **measurable function** $f : (X, \Sigma_X) \to (Y, \Sigma_Y)$ is a map such that $f^{-1}(B) \in \Sigma_X$ for every $B \in \Sigma_Y$. Equivalently, the preimage map $f^{-1} : \Sigma_Y \to \Sigma_X$ is a morphism of $\sigma$-algebras. Two structural observations are load-bearing for what follows. First, measurability is a property of the pair $(f, \Sigma_X, \Sigma_Y)$, not of $f$ alone; the same set-function can be measurable under one pair of $\sigma$-algebras and not under another. Second, the composition of measurable functions is measurable, so measurable spaces form a category with measurable functions as morphisms.

Notice the pattern: definition, alternative formulation, structural observation, categorial placement. Four moves in one paragraph.

---

## Movement III — The Substantive Content

**Purpose.** Do the actual work. Answer the question. Draw the distinction. Prove the claim. Perform the comparison. Exhibit the example.

**Shape depends on note type.**

| Note type                | Movement III contains                                                        |
| ------------------------ | ---------------------------------------------------------------------------- |
| Comparative              | The comparison proper, tables, formal relations ($\subset$, $\cong$, …), shared structure, divergence points, calibration examples. |
| Derivation               | Steps, each with justification or sketch; clear markers between rigorous and heuristic.   |
| Synthesis                | The unifying abstraction, the specialisations that fall out, the new perspective it affords. |
| Philosophical reflection | The argument, with distinctions drawn explicitly (object/representation, syntax/semantics, …). |
| Exposition               | The careful walk-through, with worked examples, counterexamples, and edge cases.         |

**Rules that apply to all shapes.**

- Every non-trivial claim is either proved, sketched, or pointed to a reference.
- Every formal symbol introduced has been defined in Movement II or is defined on first use.
- Examples earn their place by forcing a distinction, not by illustrating.

---

## Movement IV — Synthesis and Outward Connections

**Purpose.** Close the note with the refined claim, the outward connections, and the honesty note.

**Must contain.**

1. **The precise formulation.** One or two sentences stating, as cleanly as possible, the claim the note has established. This is the sentence the user will reread in six months and understand instantly.
2. **Outward connections.** Wikilinks or named references to topics where the same structure, the same failure mode, or the same distinction appears. No hand-waves; only connections that survive the *"would an expert say yes?"* test.
3. **Honesty note.** What has been assumed? What has been left unformalised? What is the next object of study if this thread is pulled further?

A note without Movement IV is a draft, not a note. The synthesis is the reason the note is a durable artefact rather than a conversation.

---

## A full worked skeleton

Here is the canonical skeleton of a note on a topic $T$, applied to a comparison of objects $A$ and $B$:

> **I. Orientation.** *[Category $\mathcal{C}$ that contains both $A$ and $B$.] [One-sentence $A$.] [One-sentence $B$.] [The load-bearing claim about their relation.]*
>
> **II. Terrain.** *[Full definition of $A$.] [Full definition of $B$.] [The ambient structure $\mathcal{C}$ in detail.] [Table of corresponding primitives.] [Inclusion or relation between them as subclasses of $\mathcal{C}$.]*
>
> **III. The substantive content.** *[The comparison along the load-bearing axes.] [Calibration examples.] [The formal relation.] [Cases where the distinction matters operationally.]*
>
> **IV. Synthesis.** *[Refined claim.] [Connections to $D_1, D_2, \dots$.] [Assumptions / limitations / next objects.]*

This skeleton is applied in `06_Knowledge_Base/Computing/yaml_vs_json.md`. Read it as a calibration example.

---

## Nested structure within a Movement

Each Movement is a container, not a flat section. When a Movement carries multiple load-bearing components, subdivide with `### I.1`, `### I.2`, `### II.1`, `### II.2`, etc. The numbering is fractal: `I`, `I.1`, `I.1.a` are all legitimate levels when the content warrants them.

**When to subdivide:**

- Movement I has multiple prerequisite definitions that each deserve their own anchor.
- Movement II has a formal core and a structural/illustrative core that should not be mixed (e.g. `II.1 Definiciones formales`, `II.2 Taxonomía`, `II.3 Correspondencias`).
- Movement III has multiple axes of analysis, each meriting its own subsection (`III.1 Memoria`, `III.2 Polimorfismo`, `III.3 Genéricos`).

**When not to subdivide:** a single-paragraph Movement needs no heading beyond the roman numeral. Subdivision is a response to content volume, never a decorative move.

**Canonical exemplars of nested structure** (read before writing a technical note):

- `06_Knowledge_Base/Computing/type_vs_class_cpp_csharp_python.md` — deep nesting (I.1, I.2, I.3, II.1, …, VII.N) over a comparative synthesis across three languages.
- `06_Knowledge_Base/Computing/python_classes.md` — exhaustive reference nesting; each Movement carries ~5–10 subsections with their own sub-subsections.
- `06_Knowledge_Base/Computing/yaml_vs_json.md` — tight comparative with minimal nesting; the calibration lower bound.

The three together bracket the register: tight comparison → deep comparison → exhaustive reference. Match the target density to the content, and lean toward the deeper end when the topic has earned it.

---

## The most common failure

By far: starting with the comparison before naming the category. The symptom is a note that opens with *"JSON is strict; YAML is flexible"* and only later — if at all — tells the reader that both are syntactic encodings of the same object. The reader is left to reverse-engineer the category from the comparison. This is backwards.

**The corrective** is mechanical: **always write Movement I first, in full, before anything else**. Even if the user's prompt starts mid-comparison, write the orientation first, then continue.
