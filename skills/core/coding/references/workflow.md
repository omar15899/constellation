# Engineering workflow

## Design the change

Start from inputs, outputs, errors, and observable effects. Follow existing
callers and normal entry points. Identify compatibility promises, stored formats,
units, ordering, and resource ownership where they affect the result.

Make the smallest change that meets the complete contract. Reuse the
component that owns the behavior, and make each touched file serve the
requirement. Keep related operations together, use domain names and show
branches and data transformations explicitly. An ordinary loop or a named
intermediate value earns its lines when it makes the intent easier to read.
Add an abstraction when it captures a current invariant or removes meaningful
duplication. Add dependencies or compatibility layers only for a demonstrated
requirement.

Choose the simplest algorithm and representation that fit the expected input
sizes. Remove repeated work, allocation or I/O when the improvement follows
directly from the design. Support performance claims with measurements within
the user's authorized scope.

Make invalid inputs and failure behavior clear at the boundary that owns them.
Use useful types and specific errors. Explain relevant state transitions,
mutation, resource lifetimes, cancellation, retries, and concurrency. Handle
partial failure and make cleanup and error propagation explicit.

## Document contracts and decisions

Use [Google Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
for Python. Describe the purpose of relevant modules and classes. Document public
APIs and nontrivial functions with the context a caller or maintainer needs.
Use `Args:`, `Returns:`, `Yields:`, `Raises:`, and `Attributes:` as appropriate,
without filling sections that repeat the signature.

Explain semantics the types do not express: preconditions, effects, error
contracts, units, ordering, mutation, and resource lifetime. Put the reason for
an otherwise surprising decision beside the code. Comments should explain
invariants or tradeoffs; they should not narrate ordinary statements. Use a
small, clearly labeled example when a data structure is difficult to interpret.
In other languages, follow the project's idiomatic documentation format.

## Verify in proportion to the change

Read the diff and trace affected callers, invariants and failure paths. Start
with inspection, independent review and relevant static checks such as syntax
parsing, schema validation, type checking or linting.

Keep existing coverage and default to no new tests. Add, change or run only
the smallest focused set needed for an explicit request, an applicable project
requirement, or a specific material regression that existing evidence leaves
open. Prefer a relevant existing case. Add a small deterministic regression
case through the normal entry point only when the gap warrants it. Reserve
broad suites for explicit requests or mandatory gates. Stricter task and
project limits still apply.

Record what each check establishes. Label tests and behavioral experiments as
execution evidence. State the remaining runtime uncertainty and any required
gate you could not meet under the task's limits.

For numerical code, reason about the declared domain, precision, overflow,
cancellation, and approximation assumptions. Use an appropriate reference or
bound for the mathematical claim. Distinguish proof, static inspection, and
executed numerical evidence.

## Coordinate independent review and delivery

Use the [common protocol](../../../../README.md) and project policy for task
records, review, finding resolution, and authorized publication. Keep meaningful
decisions, evidence, and outstanding work in the existing task ledger.

Delegate independent tasks with exclusive paths and a clear result. Use native
agents, inherit the selected model and reasoning effort, and respect the
client's actual capacity. Register native identities before edits. Authors
preserve others' changes and leave integration and publication to the
coordinator.

Correctness, readability, and security reviews may proceed concurrently on the
same completed candidate. Reviewers inspect the artifact itself and quote its
current fingerprint. Feedback obtained during implementation is advisory; a
later edit invalidates approval. A finding's resolution needs a verifier who
neither authored the change nor discovered that finding.

Protect private data, foreign edits, and the existing index during integration.
Check that each requirement has current artifacts and appropriate evidence.
Describe the delivered result, checks actually performed, unresolved findings,
and material limits without promising perfection or implying unperformed tests.
