---
name: "coding"
description: "Implement, debug and refactor software with observable requirements, tests and independent review. Use for engineering tasks that change or diagnose behavior; not for trivial syntax questions, writing or mathematical theory merely because code is present."
---

# Coding

Carry the requested behavior through to a verified, integrated delivery, and
publication when it forms part of the authorized task. Identify the receiving
project, its instructions, consumers and invariants that could change the
solution; preserve other people's work.

## Choose the work needed

A small local fix can be completed by reading the relevant code, editing it
and running a focused check. If neither an active contract nor a receiving
project's policy requires it, do not create a persistent contract, token, Git
repository or agent team for that edit. Explain the change and its verification;
do not load the extended workflow references by default.

In a Git project, follow the receiving project's workflow and minimum review;
do not also open a portable task because this skill was selected. For substantive
implementation, complex diagnosis or coordinated work, consult the
[engineering workflow](references/workflow.md). Use the
[common protocol](../../ecosystem/references/protocol.md) when you need to choose
or connect evidence cycles; the [portable CLI](../../ecosystem/cli.py) supports
deliveries with persistent evidence without Git. Preserve contracts already active.

## Implement and verify

Define observable behavior and verify the cause before fixing it. Seek powerful
code that is general within the requested domain, simple and exceptionally
readable. Keep the smallest change compatible with the result and actual
contracts; compare a direct solution with a justified abstraction when the
decision matters. If the user asks to build on abstractions, define their
contracts and composition; if they ask for a clean, simple solution, do not
impose incidental layers. Reuse what exists and justify every addition to
complexity through a concrete need.

Make the input → transformation → output path visible through clear names, data
structures and control flow. In Python, document public interfaces and non-obvious
logic in Google Style: useful context, contracts and small verified examples
where needed to understand the data. Develop extensive documentation where the
contract, data or decisions require it; do not repeat signatures or obvious
operations. The [engineering workflow](references/workflow.md#document-decisions-and-data)
details where to explain structures, invariants and decisions. Distinguish reasoned
costs from measured performance; do not claim speed improvements without measurement.

Verify relevant inputs, boundaries and consumers. For controls, test both
rejection and the permitted case. Reuse useful checks; do not add tests that
merely repeat the edit or broaden the suite after it passes without changes,
failures or specific unresolved concerns.

Requirements, current artifacts and evidence must correspond. Adapt review to
risk without lowering the receiving project's minimum; permissions, hooks and
sensitive boundaries can require deep review even with a small diff. Keep review
and finding verification independent of their authors. A passed gate checks
traceability and freshness, not whether a test is relevant.

Delegate separable work when it adds value, with exclusive files, actual identity
and a verifiable result. Available profiles are
[coder](../../ecosystem/agents/coder.toml),
[researcher](../../ecosystem/agents/researcher.toml),
[reviewer](../../ecosystem/agents/reviewer.toml),
[security_reviewer](../../ecosystem/agents/security-reviewer.toml) and
[verifier](../../ecosystem/agents/verifier.toml). Use the names advertised by the
native client's catalogue.
If a profile is not loaded, pass its instructions to the available agent;
inherit model, reasoning effort and permissions without claiming an activation
that has not occurred.

A solver with convergence analysis and a report may also need `mathematics` and
an editorial or format capability: verify each obligation with its own evidence.
Integrate and publish through the receiving project's authorized workflow; in
Constellation, respect `workspace.py`, contracts and hooks. This skill does not
authorize new destinations, private data or external actions. With requirements
or gates pending, deliver the partial result and the specific impediment.
