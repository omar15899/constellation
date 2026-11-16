# Rigorous Explanation Guide

The deepest question this skill faces is: *how do you stay rigorous while also being maximally clear?* The answer is not to choose. The answer is to discipline the relationship between intuition and formalism so that intuition leads to formalism rather than substituting for it.

This guide collects the principles you should apply when designing the conceptual arc of any video.

## 1. Explain from necessity

A definition is the answer to a problem. The viewer should *want* the definition to exist before it appears.

**Anti-pattern:**
> "An atlas is a collection of charts whose transition maps are smooth."

The viewer has no idea what an atlas is *for*. They learn a label, not a concept.

**Pattern:**
> "One flat coordinate grid can describe only a limited region of a curved object without tearing or folding. So if we want the entire curved object to be locally coordinate-like, we need several coordinate windows — and we need them to agree on the regions where they overlap. The data of all these windows, plus the agreement on overlaps, is what we will call an atlas."

The viewer constructs the necessity. The definition arrives as a name for something they already see they need.

## 2. Build abstractions out of examples that demand them

Three concrete examples that all share a hidden structure are the strongest possible motivation for the abstract definition that captures that structure.

When designing the example sequence, ask:

- Are the examples genuinely different surface-level objects?
- Do they share *exactly* the structure the abstraction will capture?
- After seeing them, can the viewer almost predict the abstraction?

If the answer is yes, the abstraction lands as recognition rather than as imposition.

## 3. Distinguish object from representation

This is the single most undervalued discipline in mathematical exposition. Every time you draw a representation, name it as a representation.

| Object | Representation | Common confusion |
| --- | --- | --- |
| Linear map $T: V \to W$ | matrix in a chosen basis | "the matrix is the linear map" |
| Smooth manifold $M$ | coordinate chart $\varphi$ | "the chart is the manifold" |
| Random variable $X$ | a sample $x_1, x_2, \ldots$ | "those numbers are $X$" |
| Distribution | histogram | "the histogram is the distribution" |
| Stochastic process | sample path | "the wiggly line is the process" |
| Function | graph | "the graph is the function" |
| Group element | matrix in a representation | "the matrix is the element" |
| Polynomial | sequence of coefficients | "the coefficients are the polynomial" |

In the video, when a representation appears, signal it. When the representation could be replaced by another (different basis, different chart, different sample), show the swap. Then fade the representation while the invariant object remains.

## 4. Make abstraction visible

For every abstract object, decide:

- **What is it?** — its formal type.
- **What does it do?** — what operation it performs.
- **What does it preserve?** — invariants under transformation.
- **What does it forget?** — what it abstracts away.
- **What does it transform?** — its action on a domain.
- **What would it look like if drawn?** — its visual representation.

Then draw it. If it has no visual, you have not understood the object well enough yet.

## 5. Control your metaphors

Metaphors are useful but dangerous. They smuggle in false implications.

For every metaphor, decide:

- What aspect does it correctly capture?
- What aspect does it falsify?
- When the viewer over-extends it, where will they go wrong?

State the limit. Either:

- Verbally: "This picture is helpful for the static structure; the dynamics behave differently."
- Visually: show the metaphor breaking at exactly its failure point.

A metaphor whose failure mode is invisible is worse than no metaphor.

## 6. Stage the formalism

Formalism is not the enemy of clarity — but it should arrive at the right time. The formal definition should appear *after* the conceptual pressure has been built and *before* the viewer's intuition has had time to crystallize wrong.

Common stages:

1. **Phenomenon / problem.** Show the thing that the formalism will eventually address.
2. **Failed naïve attempt.** What happens if we try to handle it informally? Where does it break?
3. **Conceptual diagnosis.** What structure is missing? What needs to be made precise?
4. **Definition.** The formal object, stated precisely, with all the structure that was missing now made explicit.
5. **Sanity check.** Recover the naïve case and verify it still works.
6. **Power demonstration.** Show what the formalism now lets us do that the informal version couldn't.

This is the rhythm: pressure → diagnosis → definition → recovery → leverage.

## 7. Where rigor enters and exits

Mark, in your own design, which segments are **[FORMAL]** and which are **[INFORMAL]**. The viewer should never be allowed to mistake a metaphor for a theorem or an intuition for a definition.

Concretely, in the script:

- A formal definition should be on screen as text, in white, in standard mathematical notation, with full quantifiers and types.
- An informal intuition should be carried by the visuals and the narration, with no formal text on screen, OR with text on screen that is explicitly marked as a sketch.

When transitioning from informal to formal, the narration can flag it: "Now let us state this precisely." When transitioning from formal back to informal: "Stepping back from the formal statement, the picture is…"

## 8. Special cases vs general cases

Special cases are pedagogically powerful. Use them to:

- Build intuition before the general case.
- Recover the general case as a limit, generalization, or unification of special cases.
- Show what happens at the boundary of the general case (degeneracies, edge cases).

But never present a special case *as if it were* the general case. If the video shows the construction in $\mathbb{R}^2$, narration must say so, and the general statement must arrive afterwards.

## 9. Non-examples and counterexamples

A non-example clarifies the boundary of the definition: "Here is something that almost satisfies the definition but fails because…"

Use a non-example when:

- The definition has a subtle condition that beginners often miss.
- A boundary case is conceptually illuminating.
- The viewer is likely to assume more structure than the definition actually requires.

Do not use a non-example for everything; it adds cognitive load. Pick the one or two non-examples that genuinely sharpen the definition.

## 10. Proofs and proof sketches

If the video includes a proof, decide which mode:

- **Full proof:** every step justified. Use only when the proof is short or when proof is the whole point of the video.
- **Proof sketch:** state the key lemma, the strategy, and the structure of the argument. Skip routine steps. Tag as **[SKETCH]**.
- **Picture proof:** the visual makes the argument. Tag as **[PICTURE]**. Reserve for cases where the picture really is rigorous (e.g., a geometric bijection).

Never present a sketch as a proof. Never present a picture as a proof unless it is one.

## 11. Recovering the original question

The video should end with an explicit return to the opening problem, now with the new construction available. The viewer should feel:

- The original question is now well-defined.
- The construction we built actually answers it.
- The same construction will keep answering related questions in future videos.

This is the "conceptual transformation" the script promised in §2 of its output.

## 12. The final test

Ask: would Omar — who values rigor at the level of the mathematical object, not just the notation — find this explanation respectful of the subject?

If the answer is no, the explanation is not yet ready.
