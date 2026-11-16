# Constructing a mastery-oriented course

Read this reference when the request is to create a course, handbook, multi-chapter curriculum, or long learning system. Apply it proportionately; it is a design method, not a mandatory visual template.

## 1. Fix the learning contract

Before writing modules, infer or state:

- the learner's current domain vocabulary and transferable knowledge;
- the target capability, including what the learner should be able to derive, decide, build, or diagnose;
- the principal format or baseline that holds nuisance variables fixed;
- the intended depth and any time, safety, or resource constraints;
- what “complete” means and what it does not guarantee.

Do not define completion as “has read every chapter”. Define observable performance and transfer.

## 2. Build a dependency graph, not a topic inventory

Identify the smallest objects and operations needed for later reasoning. Order modules by conceptual dependency:

$$
\text{mechanics}
\to
\text{state and representation}
\to
\text{measurement and uncertainty}
\to
\text{decision rules}
\to
\text{interaction and strategy}
\to
\text{specialisation and professional practice}.
$$

Adapt the graph to the subject. Avoid organising solely by historical chronology or familiar textbook chapter names when that creates hidden prerequisites.

For each proposed module ask:

1. Which later decisions require it?
2. Which earlier objects does it assume?
3. Can it be opened independently with a short recap?
4. What misconception is it designed to remove?
5. What observable task proves mastery?

## 3. Use a stable module contract

Each substantive module should usually contain these functions, though headings may vary:

- **Entry state:** prerequisites and a diagnostic that reveals whether they are present.
- **Promise:** concrete capabilities gained by the end.
- **Minimum vocabulary:** terms needed in this module, defined locally before use.
- **Motivating case:** a decision or phenomenon the learner cannot yet resolve.
- **Ontology and governing principles:** objects, types, relations, invariants, and causal structure.
- **Derivation:** formal treatment with assumptions and units where mathematics clarifies the mechanism.
- **Worked cases:** prototype, boundary, counterexample, and realistic case as appropriate.
- **Practice:** tasks that require reconstruction, prediction, calculation, explanation, or design.
- **Local correction:** answers, derivations, scoring rubric, or an unambiguous comparison procedure.
- **Advance gate:** an observable standard for moving on.

Do not repeat this list mechanically when a more natural narrative serves the same functions.

## 4. Design examples and exercises as a progression

Use increasing cognitive demands:

1. **Recognition:** identify objects and legal states.
2. **Reconstruction:** recover missing steps, state, units, or assumptions.
3. **Calculation:** obtain a result from declared inputs.
4. **Explanation:** justify why a method applies and name its boundary.
5. **Sensitivity:** change one variable and predict the effect before calculating.
6. **Transfer:** solve a new-looking case governed by the same structure.
7. **Synthesis:** combine several modules in a capstone with incomplete or noisy information.

Every graded exercise must be answerable from the supplied course. If multiple answers can be sound, provide a rubric that distinguishes an excellent answer from a plausible but incomplete one.

Use stable identifiers for a large bank so prompts, solutions, error logs, and revisions remain traceable.

## 5. Make capstones executable

A capstone should supply fixed inputs, an explicit output, and a reproducible scoring rule. It should test integration rather than introduce a hidden new topic.

Good capstones may ask the learner to:

- classify and justify a set of states, including impossible ones;
- reconstruct multiple legal histories from ambiguous observations;
- compare decisions after normalising units and constraints;
- build a small model, enumerate outcomes, and audit its assumptions;
- diagnose a flawed explanation and repair it.

Include an answer key or anchored rubric. “Discuss thoughtfully” is not a self-correcting capstone.

## 6. Build a learning loop

Give the learner a repeatable cycle:

$$
\text{attempt}
\to
\text{record confidence}
\to
\text{compare locally}
\to
\text{classify the error}
\to
\text{state a repair rule}
\to
\text{solve a variation}
\to
\text{space the next review}.
$$

Separate knowledge errors, state-reconstruction errors, arithmetic errors, model errors, strategic errors, and execution errors when the subject supports that distinction. A corrected answer is not yet a repaired mental model; require a nearby transfer case.

## 7. Support tools without depending on them

If code, databases, simulators, solvers, calculators, or specialist applications add value:

- first explain what mathematical or procedural operation the tool performs;
- provide a small manual example or pseudocode implementation;
- state inputs, outputs, conventions, and failure modes;
- use the tool for scale, sensitivity, or verification rather than as an oracle;
- distinguish study tools from tools permitted during live or regulated activity.

## 8. Finish with two maps

Provide both:

- a **concept map** showing how objects and principles depend on one another;
- an **execution path** telling the learner what to read, attempt, measure, and repeat next.

The first supports understanding; the second prevents the course from becoming a reference work that nobody knows how to study.
