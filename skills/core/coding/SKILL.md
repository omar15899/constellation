---
name: "coding"
description: "Implement, debug, and refactor software with explicit contracts, readable code, and independent review. Use for engineering work that changes or diagnoses behavior, not trivial syntax questions, prose, or mathematical theory merely containing code."
---

# Software engineering

1. **Understand the contract.** Read project instructions, normal entry points,
   callers, and invariants. State the observable result. For a defect, establish
   its cause from the available evidence before editing.
2. **Make the smallest correct change.** Reuse the component that owns the
   behavior. Cover the supported domain and preserve behavior callers rely on.
   Use descriptive domain names, useful types and direct control flow. Make
   ownership, mutation, errors and cleanup visible. Choose a simple algorithm
   suited to the expected inputs and add an abstraction only for a present need.
3. **Document contracts and inspect the result.** Use Google Style docstrings
   for Python public APIs and nontrivial functions. Explain inputs, results,
   assumptions and effects that matter to callers. Follow the project's idiom
   in other languages. Inspect the diff and run relevant static checks.
4. **Deliver grounded evidence.** Follow the project's task and review contract.
   Report meaningful milestones, blockers, and decisions. State the resulting
   behavior, evidence actually obtained, and remaining limitations.

Keep existing coverage and default to no new tests. Use the smallest focused
set when explicitly requested, required by project policy, or necessary for a
specific material regression that existing evidence leaves open. Respect
stricter task and project limits. Report static checks and runtime evidence
separately, along with any required gate that remains unmet.

Read the [engineering workflow](references/workflow.md) for substantive design,
documentation, validation, and review decisions. The
[common protocol](../../../README.md) describes task reuse, evidence, and
authorized publication.

Delegate independent work through the client's native agents with exclusive
file ownership, acceptance criteria, and sufficient context. Inherit the
selected model and reasoning effort within the client's effective limits.
Register returned native identities before edits. If a role is unavailable,
supply its instructions to an available native agent. The roles for
[implementation](../../../agents/coder.toml),
[investigation](../../../agents/researcher.toml),
[review](../../../agents/reviewer.toml),
[security](../../../agents/security-reviewer.toml), and
[finding verification](../../../agents/verifier.toml) have distinct duties.
Reviews may run concurrently on a stable candidate. Authors cannot approve
their own work, and a finding's verifier must also be independent of its finder.
Each mathematical, empirical, or editorial obligation needs its own kind of
evidence.
