# Engineering workflow

## Design the change

Start from inputs, outputs, errors, and observable effects. Follow existing
callers and normal entry points. Identify compatibility promises, stored formats,
units, ordering, and resource ownership where they affect the result.

Choose a design a colleague can follow without reconstructing a framework.
Name concepts in the language of the domain. Keep related operations together,
use focused functions, and make branches and data transformations explicit.
Prefer an ordinary loop or named intermediate value when a compact expression
would hide intent. Reuse the component that already owns the behavior. Introduce
abstractions, dependencies, and compatibility layers only for a demonstrated
requirement; avoid speculative extension points.

Make invalid inputs and failure behavior clear at the boundary that owns them.
Use useful types and specific errors. Explain relevant state transitions,
mutation, resource lifetimes, cancellation, retries, and concurrency. Handle
partial failure and cleanup without silently replacing errors with success.
Measure a claimed performance improvement only when the user has authorized
the required measurement; otherwise leave the claim unmade.

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

## Inspect without assuming permission to test

Do not add, modify, or run tests unless the user explicitly requests them.
Preserve existing test files. A project's usual test command, a desire for
confidence, or a reviewer's request does not override this user preference.
Do not disguise a test suite, behavioral reproduction, or regression experiment
as a static check.

Read the diff and trace affected callers, invariants, and error paths. Use
relevant non-test static checks when available: syntax parsing, schema
validation, type checking, or linting. Record which checks actually ran and what
they establish. Static evidence and review do not establish runtime correctness;
state untested behavior and any unresolved consequence plainly.

If the user explicitly requests tests, keep them proportionate to that request.
Prefer a few deterministic scenarios through normal entry points with readable
inputs and observable outcomes. Reuse existing meaningful coverage before
adding new cases. Do not widen the campaign without a concrete reason.

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
