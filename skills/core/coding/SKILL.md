---
name: "coding"
description: "Implement, debug, and refactor software with explicit contracts, readable code, and independent review. Use for engineering work that changes or diagnoses behavior, not trivial syntax questions, prose, or mathematical theory merely containing code."
---

# Software engineering

1. **Understand the contract.** Read project instructions, normal entry points,
   callers, and invariants. State the observable result. For a defect, establish
   its cause from the available evidence before editing.
2. **Write for the next maintainer.** Reuse existing owners and structures. Use
   domain names, focused functions, useful types, and straightforward control
   flow. Make data ownership, mutation, errors, and cleanup clear. Add an
   abstraction only for a concrete need. Cover the supported domain and preserve
   interfaces and data unless the requested change requires otherwise.
3. **Document decisions and inspect the result.** Use Google Style for Python
   public APIs and nontrivial code; use the project's idiom in other languages.
   Explain contracts and reasons rather than narrating statements. Read the
   actual diff and use relevant non-test static checks.
4. **Deliver grounded evidence.** Follow the project's task and review contract.
   Report meaningful milestones, blockers, and decisions. State the resulting
   behavior, evidence actually obtained, and remaining limitations.

Do not add, modify, or run tests unless the user explicitly requests them.
Preserve existing test files. Do not relabel suites, regressions, or behavioral
experiments as static checks. Do not claim runtime correctness from reading,
syntax checks, or an independent review.

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
