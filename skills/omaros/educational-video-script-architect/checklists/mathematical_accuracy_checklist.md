# Mathematical and Conceptual Accuracy Checklist

Run during §10. **PASS / NOTE / FAIL** with a short reason. For advanced topics, every claim should be classified as **[INFORMAL]** or **[FORMAL]**, and no [INFORMAL] segment may be presented as if it were [FORMAL].

## Definitions

- [ ] Every definition stated is mathematically correct as given.
- [ ] Every definition has the right quantifiers, the right domain of application, the right object type.
- [ ] If a definition is given in a special case (e.g., on $\mathbb{R}^n$), the restriction is stated.
- [ ] No definition silently assumes structure that has not been introduced (e.g., a measure where none exists, smoothness where only continuity is assumed).

## Object versus representation

- [ ] The video distinguishes the *object* from any chosen representation (coordinate chart vs manifold; sample path vs stochastic process; histogram vs distribution; matrix vs linear map; payoff diagram vs random variable).
- [ ] Where a representation-dependent property is shown, the script either flags it explicitly or restricts the claim to the chosen representation.
- [ ] Notation chosen for the object does not conflate it with a representation (e.g., do not write "$M = (U, \varphi)$" as if a manifold *equals* a chart).

## Notation

- [ ] Every symbol is introduced before use.
- [ ] No symbol is reused with a different meaning later in the video.
- [ ] Index conventions (free / bound, summation, multi-index) are consistent.
- [ ] Differentials, measures, and operators use one consistent style ($d\mu$, $dx$, $\mathrm{d}t$ — pick one).
- [ ] Where Einstein summation is used, the convention is announced explicitly.

## Examples

- [ ] Every example genuinely instantiates the definition it is meant to illustrate.
- [ ] No example is presented as a definition by accident.
- [ ] Examples are non-degenerate enough to actually exhibit the relevant structure.
- [ ] Where examples are simplified, the simplification is acknowledged (e.g., "a simplified model — the full statement requires…").

## Special cases

- [ ] Special cases are correctly identified as special cases, not as the general definition.
- [ ] When a special case is generalized, the script names what is being generalized (the constraint being dropped, the structure being relaxed).

## Limit, edge, and boundary cases

- [ ] Where the construction has degenerate or boundary cases (empty set, dimension zero, infinite measure, non-smooth boundary), they are either addressed or explicitly deferred.
- [ ] Convergence claims have explicit modes (pointwise / uniform / $L^p$ / a.s. / in distribution) when the distinction matters.
- [ ] Limits are not silently exchanged ($\lim$ and $\int$, $\sum$ and $\lim$, derivative and limit) without justification or a flag.

## Metaphors and informal language

- [ ] Every metaphor is explicitly tagged (in narration or production notes) as informal.
- [ ] Every metaphor's failure mode is acknowledged at least once if the viewer might over-extend it.
- [ ] No metaphor is allowed to substitute for the formal object — the formal object is shown.

## Proofs and derivations (when present)

- [ ] Each step of a derivation is justified, even if the justification is "by linearity" or "by the previous lemma".
- [ ] Any "without loss of generality" claim is genuine — the special case actually implies the general case.
- [ ] Any informal proof sketch is labelled as such, and the gap between sketch and full proof is identified.
- [ ] Existence claims and uniqueness claims are not silently conflated.

## Quantifier hygiene

- [ ] $\forall$ vs $\exists$ ordering is correct in every statement.
- [ ] Free variables in any displayed equation are bound somewhere visible.
- [ ] "For some" vs "for all" is preserved in the narration.

## Probability / measure / stochastic content (if applicable)

- [ ] Probability spaces, sigma-algebras, and measures are introduced before being used.
- [ ] Random variables are not confused with their realizations.
- [ ] Filtrations are explicit when adapted processes appear.
- [ ] Conditional expectation is treated as a random variable, not a number, where applicable.
- [ ] Stochastic integrals do not use ordinary calculus rules where Itô / Stratonovich corrections apply.

## Geometry / analysis content (if applicable)

- [ ] Smooth vs continuous vs measurable is not blurred.
- [ ] Tangent spaces and cotangent spaces are not silently identified without an inner product.
- [ ] Local vs global statements are clearly tagged.
- [ ] Charts, atlases, transition maps, and pullbacks/pushforwards are used in the right roles.

## Computing / algorithms content (if applicable)

- [ ] Complexity claims are stated with the cost model (RAM, comparison, oracle).
- [ ] Pseudocode and code snippets compile / typecheck conceptually; no silently wrong loops, off-by-one, or undefined behavior.
- [ ] Data-structure invariants stated in narration are consistent with the visualised state.

## Final classification

For every advanced or research-level video, label each scene with:

- **[INFORMAL]** — intuitive description, metaphor, or visual analogy. Not to be cited as a formal claim.
- **[FORMAL]** — precisely stated definition, theorem, or proof step.

Confirm that no [INFORMAL] segment in the script presents itself with the rhetorical weight of a [FORMAL] one.
