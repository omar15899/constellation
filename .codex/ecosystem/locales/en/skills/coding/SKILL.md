---
name: "coding"
description: "Implement, debug and refactor software with observable requirements, tests and independent review. Use for engineering tasks that change or diagnose behavior; not for trivial syntax questions, writing or mathematical theory merely because code is present."
---

# Software engineering

1. **Understand the contract.** Identify the project's instructions, normal
   entry points, consumers and invariants. Define the observable result.
   When fixing a bug, reproduce it or establish its cause before editing.
2. **Implement for the whole domain.** Reuse existing structures. Preserve
   interfaces and older data unless the task calls for a change. Use domain names
   and clear steps to make data flow visible. Each abstraction must serve a
   concrete need. Handle partial failure, retries and concurrency when they
   can affect the result.
3. **Document and check.** In Python, use Google Style for comments and the
   docstrings required by the interface or logic. In other languages, follow the
   project's equivalent convention. Run relevant existing checks first. Add
   tests for explicit requests, project requirements or specific risks left uncovered.
4. **Deliver with evidence.** Follow the project's required workflow and review.
   A small local fix needs only a focused check where the project allows it.
   During work, communicate milestones, blockers and material decisions.
   At the end, summarize the result, evidence and limits.

Consult the [engineering workflow](references/workflow.md) for implementation,
documentation, testing and review decisions in substantial changes. The
[common protocol](../../ecosystem/references/protocol.md) defines how to reuse
an active contract, record evidence and coordinate authorized publication.

When delegating, provide an exclusive scope, acceptance criteria and context.
Use the native catalogue. If a role has not loaded, pass its instructions to an
available agent with inherited model, reasoning effort and permissions. The
[coder](../../ecosystem/agents/coder.toml),
[researcher](../../ecosystem/agents/researcher.toml),
[reviewer](../../ecosystem/agents/reviewer.toml),
[security reviewer](../../ecosystem/agents/security-reviewer.toml) and
[verifier](../../ecosystem/agents/verifier.toml) have distinct responsibilities.
Each mathematical, empirical or editorial obligation needs its own kind of evidence.
