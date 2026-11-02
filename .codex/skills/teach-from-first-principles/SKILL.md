---
name: "teach-from-first-principles"
description: "Teach a concept in depth, design or audit self-contained learning materials, guide practice, or calibrate a local learner profile from intentional reusable feedback. Use when the learner should be able to reconstruct or transfer the method."
---
# Teach From First Principles

Create explanations that let the learner reconstruct the subject, not merely recognise the answer. Preserve intellectual depth while removing accidental difficulty caused by undefined vocabulary, hidden prerequisites, missing derivations, or examples that omit decisive facts.

Choose this method when the outcome is a capability the learner should demonstrate.
For a standalone essay or ordinary technical explanation, use the general
Constellation writing method when available. Use Scholar when the requested
output belongs to OmarOS and requires its navigational and editorial context.
For a course, calibrate prerequisites, practice, feedback and tests of transfer
against the current learning objective.

## Establish the learning objective

Use the user's current objective, declared background, time constraints and desired
depth. When their instructions identify an accessible personal learning profile,
read only the relevant active entries. Keep the profile outside this generic
skill; the current request takes priority over stored preferences.

Do not infer domain knowledge, cognitive performance or an optimal teaching method
from a name or academic degree. Distinguish unfamiliar vocabulary from reasoning
ability, and presentation preferences from current habits or development goals.

Respect whether the user wants a complete explanation, guided practice without
the solution, or production work with limited pedagogy. Ask only when missing
context would materially change the result and cannot be inferred safely.

## Select the relevant guidance

- **Focused explanation:** Answer one question or teach one concept. Select the elements below at a scale proportionate to the question; do not manufacture a miniature textbook.
- **Course or learning system:** For a multi-module course, handbook, chapter sequence, or long learning artifact, also read [references/course-construction.md](references/course-construction.md).
- **Audit or substantial self-contained artifact:** When reviewing a course, chapter, manual, or any deliverable intended to replace outside teaching sources, also read [references/adversarial-self-containment.md](references/adversarial-self-containment.md) and perform the applicable checks before delivery.
- **Intentional reusable feedback:** For positive or negative teaching references, examples of the user's reasoning, or explicit profile edits, read [references/learner-calibration.md](references/learner-calibration.md). Apply authorized updates with read-back verification; generic praise and one-off corrections do not trigger persistence.

## Choose a sequence that serves the objective

Choose an ontology-first, example-first or mixed sequence from the current request
and applicable profile. The elements below are tools, not a mandatory order or a
checklist for every answer. A motivating case can precede the general structure
when useful; it must not force a particular model to stand in for the concept.

- **Construct the ontology.** Identify the ambient setting, objects, types, relations, invariants and uncertainty. Distinguish an object from its name, representation, observed value, estimate or chosen model.
- **Establish the principle.** Explain the causal, logical or structural dependency. Say what follows from which assumptions and why.
- **Formalise what earns its place.** Declare symbols, domains, hypotheses, units and quantifier scope before use. Derive load-bearing equations. Use prose–formula–prose: introduce the expression, display it, then interpret its consequence.
- **Connect to cases.** Use fully specified examples to ground or test the abstraction. For a heuristic, expose its scope and a relevant failure case. When transfer matters, explain why a changed assumption changes the answer.
- **Support practice when wanted.** Use exercises, predictions, reconstructions or decisions that expose reasoning. Supply solutions or correction criteria when appropriate; withhold the full solution when the user requests guidance only.
- **Make progress explicit.** Distinguish essentials from optional generalisations, state what can now be derived or applied, and identify a useful next step when one is needed.

Do not impose Socratic questioning on a request for a full explanation or add a
course structure to a focused question. Research and engineering may compose with
learning; the explicit priority determines how much pedagogy supports the work.

## Define before depending

- Expand every abbreviation at first use and define every domain-specific word before it carries an argument.
- Use a short local microglossary when several new terms are needed at once. Do not front-load a dictionary whose entries have no immediate role.
- Connect ordinary-language and exact technical meanings, including important non-equivalences; choose their order to suit the request and learner.
- Reintroduce the minimum necessary vocabulary when a chapter or artifact may be opened independently.
- Do not use an internal link as a hidden prerequisite. A link may add practice or navigation; the current explanation must contain the load-bearing definition.
- Detect circular explanations: if A is explained using B and B is explained using A, ground one of them operationally or axiomatically.

## Use mathematics as structure, not theatre

Connect the subject to probability, combinatorics, statistics, optimisation, dynamical systems, information theory, decision theory, or game theory when the connection explains a real dependency. Do not force a mathematical section into a topic that has no useful mathematical model; in that case, formalise categories, constraints, causal structure, or decision criteria instead.

For each mathematical model:

- identify the real object and the mathematical object used to represent it;
- state assumptions and what evidence would violate them;
- keep dimensions and units consistent;
- distinguish exact identity, conditional result, approximation, heuristic, and empirical estimate;
- derive non-trivial steps or provide a reproducible enumeration;
- interpret limiting cases and sensitivity to assumptions;
- do not silently equate probability, frequency, confidence, utility, expected value, or observed outcome.

When computation appears, explain the mechanism without requiring proprietary software. Supply a feasible paper calculation, enumeration, reduced model, or pseudocode route before treating code, a calculator, a solver, or a specialised application as a scaling tool.

## Build examples that actually teach

A worked example should specify enough state that the conclusion is reproducible. Include the initial conditions, information available at the decision time, governing rule or model, calculation or argument, conclusion, and the smallest plausible change that alters it.

Avoid examples that merely rename variables in the preceding formula. Prefer a set with distinct jobs:

- a clean prototype that isolates the mechanism;
- a near-boundary case that tests sensitivity;
- a counterexample to the tempting but false shortcut;
- when valuable, a realistic noisy case where the model's limitations matter.

Do not leak future information into an earlier decision. Do not claim that one successful outcome validates a policy, or that one failure refutes it.

## Preserve epistemic honesty

Label facts, definitions, assumptions, inferences, approximations, conventions, and speculation distinctly. A precise number produced by a toy model remains a toy-model output. A source does not repair an unexplained argument, and mathematical notation does not repair an unspecified model.

For recommendations, distinguish:

- what follows from stated objectives and constraints;
- what depends on uncertain empirical inputs;
- what is a reasonable default;
- what would make the recommendation change.

## Make stable learning self-contained

For a self-contained deliverable:

- carry every stable, load-bearing teaching claim in the artifact itself;
- include local derivations, worked examples, answers, rubrics, and manual alternatives;
- treat external links as optional provenance, further practice, or audit trails, never as the sole explanation;
- separate immutable theory from mutable operational facts such as law, taxation, prices, platform rules, software permissions, medical guidance, or safety procedures;
- verify mutable or high-stakes facts from current authoritative sources when the task requires them, and state exactly what must be revalidated before action.

Do not promise that a static artifact freezes the external world. It can be closed for learning and reasoning while explicitly requiring a current check for facts that can change.

## Match scope and voice

Match the user's language. Write directly, naturally, and with intellectual force. Prefer a connected explanation over template-like fragments. Use headings, bullets, tables, and diagrams only when they materially clarify structure.

Depth should follow the conceptual work, not an arbitrary word count. A short question may need three excellent paragraphs; a complete course may need many files. Do not compress away a load-bearing explanation, and do not repeat a conclusion to simulate depth.

Do not imitate scholarly prose for prestige. Sources may establish provenance or current facts, but the teaching must remain in your own clear explanatory voice.

## Review before delivery

For any substantial teaching artifact, perform a final adversarial pass against the declared prerequisites and learning objective. Check the applicable points:

- every term is defined before it is needed;
- no prerequisite is circular, external, or merely implied;
- examples are legal, internally consistent, and fully specified;
- formulas have declared objects, hypotheses, units, and interpretations;
- numerical conclusions recompute;
- heuristics include scope and failure cases;
- exercises are solvable from supplied information and have local correction;
- navigation, notation, numbering, and cross-references agree;
- optional tools and sources are not hidden dependencies;
- mutable facts are separated from stable theory;
- the learner has an executable next step and a mastery criterion.

For a large course or high-consequence manual, use independent reviewers or subagents when available: split the artifact into coherent scopes, ask for only material errors and dependency gaps, repair them, and run targeted re-audits. Do not call an artifact self-contained while known P0/P1 findings remain.
