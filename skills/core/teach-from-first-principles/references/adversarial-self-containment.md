# Adversarial self-containment audit

Read this reference when the user explicitly requests adversarial review, when a substantial artifact claims to be self-contained, or before finalising a course or high-consequence teaching manual.

The audit asks a hard question: could an intelligent learner with the declared background reconstruct, practise, and correct every stable load-bearing part without inventing knowledge or consulting an unmentioned source?

## Severity

- **P0:** A dangerous, destructive, legally critical, or foundationally false statement; an error that invalidates a major part of the artifact.
- **P1:** A material conceptual, mathematical, procedural, or dependency gap that can produce a wrong mental model or prevents self-contained learning.
- **P2:** A local clarity, consistency, or polish issue that does not block correct reconstruction.

Do not declare the artifact complete with known P0 or P1 findings. Record P2 issues when useful, but do not inflate cosmetic preferences into blockers.

## Audit lenses

### 1. Zero-vocabulary traversal

Read from the declared entry point and mark every technical noun, abbreviation, symbol, action, and unit at first use. For each one, locate a prior operational definition. Look especially at introductions, tables, examples, and exercise prompts, where authors often assume vocabulary they define later.

Test isolated entry too: if a module is meant to stand alone, confirm its recap closes the necessary dependencies.

### 2. Ontological and type integrity

For every load-bearing claim, identify the type of each object. Check for silent substitutions such as:

- object versus numerical value or coordinate representation;
- actual state versus observed information;
- set or distribution versus one element or sample;
- probability versus frequency, equity, confidence, or utility;
- gross quantity versus net change;
- physical unit versus dimensionless ratio;
- policy versus realised action;
- model output versus empirical fact.

Definitions should not be circular, and symbols should not change type between sections.

Choose a passage on which the conclusion depends and reconstruct it using only
the prerequisites granted to the reader. If reconstruction requires a new
hypothesis, a change of space or an unstated identification, repair the point
where that dependency enters. For a dual pairing in a finite-dimensional real
vector space, changing the basis must change vector and covector coordinates
compatibly while preserving the scalar evaluation. Identifying the functional
with a vector requires the additional choice of an inner product; the text
must explain what that choice contributes.

In a probabilistic argument, follow the random variable from its outcome space
to its values. Changing the available information differs from changing the
law. For an integrable real random variable, a conditional expectation is taken
under a probability measure and relative to a conditioning sigma-algebra. A
finite example should let the reader verify its defining integral identity on
events in that sigma-algebra. Use the analogous decisive distinction in the
actual subject rather than imposing these examples everywhere.

### 3. Derivation and arithmetic

Recompute representative formulas and all numbers that carry a decision. Check denominators, conditioning information, units, boundary conditions, card or state compatibility, conservation laws, and off-by-one conventions.

For stochastic or strategic models, declare independence, stationarity, information, action order, utility, and future-policy assumptions. A correct equation under an unstated model is still a self-containment failure.

### 4. Example legality and information discipline

Reconstruct every important example from its initial state. Confirm that:

- the sequence of actions or transformations is legal;
- all required inputs are present;
- totals and conserved quantities agree;
- no impossible state or collision is overlooked;
- the answer uses only information available at the decision time;
- future outcomes are not used to justify past decisions;
- the stated conclusion follows from the declared model rather than an intuitive story.

### 5. Heuristic breakage

For each rule of thumb, ask for the smallest change that makes it false. Ensure the artifact states its domain of validity and includes at least one failure case when misuse would be likely.

Watch for universal language attached to defaults: “always”, “never”, “obviously”, “standard”, and “optimal” require a precisely declared scope.

### 6. Exercise closure

Attempt a sample from every exercise family. Check that each prompt supplies enough information, has a reachable answer, and points to a local solution or anchored rubric. Verify identifiers, cross-references, and prompt–solution correspondence mechanically when the bank is large.

A requirement to use a proprietary tool, hidden chart, undisclosed dataset, or external answer key is a P1 unless that dependency is itself the learning objective and is explicitly supplied.

### 7. Source and tool dependency

List every external URL, book, paper, application, dataset, and internal link. Classify it as:

- optional provenance;
- optional extension or additional practice;
- scaling or verification tool with a local manual route;
- mutable operational source that must be current;
- hidden pedagogical dependency.

Repair the last class by carrying the stable explanation locally. Do not remove necessary current verification for law, medicine, safety, prices, platform policy, or other mutable facts merely to claim closure.

### 8. Navigation and global consistency

Check manifests, contents pages, prerequisites, numbering, notation, terminology, file names, links, answer keys, and mastery gates. Search mechanically for stale versions of corrected examples and definitions; repeated material often preserves an old error after the main passage is fixed.

### 9. Forward test

For a large artifact, give an independent reviewer a realistic learning task and only the declared artifact. Do not tell the reviewer what should work. Observe where they must guess, search outside, or choose among ambiguous interpretations.

When several independent scopes are available, divide by conceptual region rather than file count—for example foundations, strategy, and advanced application. After repairs, request targeted re-audits of every P0/P1 rather than assuming the patch solved the issue.

## Closure report

Report:

- the declared learner and scope;
- what “self-contained” covers;
- the mutable boundary that still requires current verification;
- P0/P1 findings and their repairs;
- structural and numerical checks actually run;
- residual limitations that are honest boundaries rather than missing teaching;
- an explicit pass only when no known P0/P1 remains.

Never equate word count, number of citations, or successful file parsing with pedagogical closure. They are supporting evidence, not the conclusion.
