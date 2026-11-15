# Engineering workflow

## Design the change

Start from observable inputs, results, errors and effects. Follow existing
consumers and the entry points through which people use the product. Identify
compatibility contracts, older formats, units, ordering and resource ownership
where they affect the result. Start with a direct design and add an abstraction
when a required variation or shared responsibility justifies it. Use domain
names, clear types and control flow that is easy to follow. In stateful
operations, check that partial failures and retries preserve invariants.
Support performance claims with reproducible measurements of the workload,
environment and baseline.

## Document decisions and data

Follow [Google Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
in Python. Describe the purpose of relevant modules and classes. Public
interfaces and functions of nontrivial size or logic need a docstring with a
summary and enough context to use them. Apply
`Args:`, `Returns:`, `Yields:`, `Raises:` or `Attributes:` as applicable.
Explain semantics the signature cannot express, such as preconditions, side
effects, contractual errors, units, ordering, mutation and resource lifetime.
If the data are hard to interpret, show a small, synthetic and verified
example of the actual structure. Beside the code, comment on reasons, invariants
and decisions a reader would struggle to infer. Self-explanatory tests can omit
docstrings that repeat their names.

## Choose a small set of tests

1. Reuse checks that exercise behavior through its normal entry points. Select
   scenarios that distinguish the solution from a faulty implementation.
   When changing a control, check both admission and rejection.
2. Add a test when the user asks, the project requires it, or existing evidence
   leaves a specific regression or risk uncovered. For an uncovered regression
   that can be automated, demonstrate failure with the bug and success with the
   fix when feasible.
3. Name each test for the scenario and outcome. Set up small inputs, exercise
   the behavior and assert the observable result. Control clocks, randomness and
   external services when they could make it flaky. Group variations of one rule
   where the cases remain easy to distinguish.
4. Preserve the existing suite. Rerun or broaden checks for changes, failures
   or a specific concern. Record what actually ran and any material limits.

For numerical code, define the domain and precision. Check valid extremes,
intermediate overflow and cancellation where they can violate the contract.
Use an independent reference or a relevant bound. Fix the calculation or
identify the outstanding obligation if the required domain remains uncovered.

## Review and close

Use the [common protocol](../../../ecosystem/references/protocol.md) and the
project's policy for recording work, reviewing, resolving findings and
publishing. For substantial work, preserve decisions, evidence and open
items through the [chosen cycle's progress](../../../ecosystem/docs/progress.md).
Protect private data and other people's work during integration. Verify that
each requirement has current artifacts, relevant evidence, actual authors
and applicable independent review. Report the result, executed checks and
outstanding obligations that affect the task.
