# Objects, structure and representations

This reference guides mathematical explanation and review: the reader should be
able to reconstruct which objects are involved, which relations connect them and
why a conclusion about their representations says something about the objects.
Use it where a distinction supports the argument; do not turn every answer into
a formal inventory. The [four worked examples](ontology-examples.md) provide
further detail without burdening the general guidance.

## Choose the generality that explains

Start with the question and the kind of object that can answer it. Present the
relevant general framework before specialising it when that order helps the
reader understand the construction. If the task asks for an example or a
calculation first, respect that order and then place it within the framework
that justifies it. Useful generality makes it possible to recover the requested
cases; it does not require returning to foundations that play no part in the
argument.

Make dependencies visible: constructing an object, adding structure, imposing a
property, choosing a representation and losing information are different
operations. Explain what each transition enables and preserves. A small example
can accompany this progression, but must not replace the general definition with
its finite, Euclidean or matrix special cases.

## Establish the object before operating on it

Introduce the ambient set or space, the type of its elements and the structure
needed for the question. An element may be a number, a function, an equivalence
class or a transformation. Calling something a “point” only asserts that it
belongs to a space; it neither turns it into a tuple of numbers nor requires
that space to be geometric.

Different roles do not imply different objects: the same function can be an
element of a function space. Determine identity from the definitions, not from
the names of the roles. Evaluation and representation are operations that must
be specified; a value can itself be another function if the codomain allows it.
Also distinguish a time index or sensor label from the configuration or reading
it selects.

Separate the carrier from its structure: a set with linear operations, a
topology, a norm, an inner product or a measure determines different problems.
Add only the structures you will use. A norm makes it possible to discuss
continuity and approximation; in general, it does not identify a space with its
continuous dual. If \(H\) has an inner product, then for the induced norm the map
\(J:H\to H^*\), \(J(v)(u)=\langle u,v\rangle\), is injective; here \(H^*\)
denotes the continuous linear functionals. With the inner product linear in its
first entry, \(J\) is linear in the real case and conjugate-linear in the complex
case. If \(H\) is complete for that norm (a Hilbert space), Riesz also guarantees
surjectivity; an incomplete space may have continuous functionals without a
representing vector.
A smooth structure makes differentiation possible; a Riemannian metric is an
additional datum.

Introduce each map with its domain and codomain, and check that compositions
make sense. For a restriction, quotient or local construction, state explicitly
where it is defined and why its value does not depend on choices that the result
is supposed to forget. “Well defined” is an obligation that requires proof.

| Distinction | What must be determined |
| --- | --- |
| Object / name | The symbol designates something defined; renaming it does not change that object. |
| Element / coordinates | If \(v\in V\), specify the map that produces its tuple and the choice that map requires. |
| Function / value | \(f:X\to Y\), \(x\in X\) and \(f(x)\in Y\) have different roles; \(f\) may itself be an element of a function space. |
| Class / representative | \([x]\in X/{\sim}\) contains representatives; a formula in \(x\) defines a function of \([x]\) only if it is constant on each class. |
| Equality / isomorphism | \(X=Y\) asserts equality; an isomorphism is an invertible map that preserves the relevant structure, including in the inverse direction. |
| Isomorphism / chosen identification | If you write one object as another, declare the isomorphism used and the choices on which it depends. |
| Intrinsic / representation | State which property belongs to the structured object and how its description transforms when the representation changes. |

A bijection only guarantees a correspondence between elements. For topological
spaces, the relevant equivalence requires a homeomorphism; for vector spaces, a
linear isomorphism; for metric spaces, preserving distances is an additional
requirement. A continuous bijection can have a discontinuous inverse: the
[example with two topologies](ontology-examples.md#topologia) prevents us from
identifying set equivalence with geometric equivalence.

## Make the representation visible

A representation must come with its map, the operations it respects and its
scope. Do not assume global coordinates on a manifold. A chart is local; an atlas
and its transition maps make it possible to compare descriptions on overlaps.
Two compatible charts describe the same smooth structure; changing that
structure would be a different operation. What is intrinsic is always relative
to the declared data: a gradient is independent of coordinates once the metric
has been fixed, but depends on that metric.

The linear case establishes the discipline. Let \(V,W\) be vector spaces over
\(\mathbb K\in\{\mathbb R,\mathbb C\}\), of finite dimensions \(n,m\),
and let \(L:V\to W\) be linear. Ordered bases \(B=(b_i)\), \(C=(c_j)\)
define reconstruction isomorphisms

\[
e_B:\mathbb K^n\to V,\quad (a_i)\mapsto\sum_i a_i b_i,
\qquad e_C:\mathbb K^m\to W.
\]

The coordinates are \([v]_B=e_B^{-1}(v)\). The matrix \(A\) represents,
in the standard bases of the coordinate spaces, the map
\(e_C^{-1}\circ L\circ e_B\). Thus,

\[
[L(v)]_C=A[v]_B,\qquad L(e_B(a))=e_C(Aa).
\]

The second equality expresses the compatibility that makes the matrix useful:
computing and then reconstructing gives the same result as applying \(L\) to
the object. The concept of the matrix of a map with respect to two bases appears
in [Axler, *Linear Algebra Done Right*, 4th ed., §3C](https://linear.axler.net/LADR4e.pdf).
The following comparison follows directly from that composition.

Let \(B',C'\) be other ordered bases of \(V,W\), respectively. The
change-of-basis matrices \(P\in GL_n(\mathbb K)\), \(Q\in GL_m(\mathbb K)\)
are defined by

\[
e_{B'}(a')=e_B(Pa'),\qquad e_{C'}(b')=e_C(Qb')
\]

for every \(a'\in\mathbb K^n\), \(b'\in\mathbb K^m\). If \(A'\)
represents \(L\) in the bases \(B',C'\), then

\[
[v]_{B'}=P^{-1}[v]_B,\qquad A'=Q^{-1}AP.
\]

The rank remains \(\dim\operatorname{im}L\), because composition with
isomorphisms does not change the dimension of the image. Similarity
\(A'=P^{-1}AP\) corresponds to the case \(V=W\) with the same basis for
input and output. Now assume \(\mathbb K=\mathbb R\). A bilinear form
\(\beta:V\times V\to\mathbb R\) is a different type of object: if
\(\beta(e_B(a),e_B(b))=a^{\mathsf T}Gb\), substituting \(a=Pa'\),
\(b=Pb'\) gives \(G'=P^{\mathsf T}GP\), a congruence. Do not transfer
one transformation law to another merely because their matrices look alike.

## Build the argument

Introduce notation when it clarifies a relation or compresses structure the
argument needs, with stable names and without turning the prose into a code to
be deciphered. When using a formula, explain the relation it expresses, write it
with its types and hypotheses, and develop its consequence. Define a term before
using it as a premise. Introduce an abstract construction when it resolves an
ambiguity or reveals a real dependency.

Distinguish the following commitments without requiring labels in every
sentence:

- A **definition** fixes a meaning or convention; declare conventions that vary,
  such as the order of a tensor's indices.
- **Axioms** determine the class of structures; **modelling assumptions** connect
  a structure to the system being studied. Deducing consequences within the model
  does not prove that this connection describes the system.
- A **hypothesis** restricts the cases considered. It must be present before the
  step that uses it, with its quantifiers and local or global scope.
- A **consequence** requires an argument or a theorem whose hypotheses have been
  checked. Justify the steps on which the conclusion depends.
- An **approximation** requires a regime and an error specification: a norm,
  scale, limit or mode of convergence. A differential symbol does not replace
  that information.
- Numerical or empirical **evidence** informs us about the observed cases;
  by itself, it does not prove a universal claim. A conjecture or inference must
  retain that status.

If the question requires probabilities or expectations, first establish the
probabilistic model, the random object and the observed realisation; preserve
those roles when operating. Unbiasedness is a property of the estimator under a
declared law and relative to a declared target, not of the number returned by a
single observation. Do not add statistical structure when it does not contribute
to the question.

Look for a case that breaks the claim when an important hypothesis is removed.
Also check a change of representation: the same vector must produce the same
value when the same covector acts on it, even if both lists of components change.
For a construction on a quotient, test two representatives of the same class.
For a random limit, distinguish the random variable, the process and a fixed
sample path; declare whether convergence is in probability, in mean square or
almost surely, and over which partitions.

These questions transfer to other domains without imposing geometry on them:

1. What kind of object is each input and each result? Which data belong to the
   object, and which belong to its presentation?
2. Which relations or maps are allowed, and what structure do they preserve?
3. Which equivalence matters for this question? Does the construction respect
   that equivalence, or does it require a chosen representative?
4. Which observation remains unchanged under an admissible change of
   representation, and what calculation proves that invariance?
5. Which hypothesis makes the crucial step valid, and what case would refute it
   if that hypothesis were removed? What evidence is missing to settle the claim?
6. Can the reader obtain the concrete case from the general framework and
   reconstruct the decisive step without mentally supplying a missing premise
   or identification?

## Consult examples and sources

Read only the example that resolves the current difficulty:
[configurations](ontology-examples.md#configuraciones) distinguish function,
element and quotient; [topology](ontology-examples.md#topologia) distinguishes
carrier, structure and generators;
[local geometry](ontology-examples.md#geometria) constructs tangents, duals,
tensors and fields; [calculus](ontology-examples.md#calculo) distinguishes the
differential, gradient and stochastic change of variables. Original calculations
are presented as such; the linked sources support specific definitions and
theorems. A reference does not replace the essential justification.

If the user mentions a reference, first locate it in the context and authorised
sources of the task. Do not request a path that you can already determine;
ask only if a material ambiguity remains or necessary access is missing. A
title does not justify attributing content you have not read: while the original
is missing, distinguish your examples and sources from what you have not yet
checked. Record provenance and, when the chosen cycle requires it, the files as
`inputs` with their hash. Reading material to adapt the standard of explanation
and redistributing that material are different authorisations: keep private
materials outside the publishable package without specific consent. Do not use
incidentally discovered conversations, transcripts or private files to make up
for a missing source.
