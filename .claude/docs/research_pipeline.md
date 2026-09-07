# Research workflow

The user defines the objective, methodology and success criteria; the agent
executes and verifies under the [expert contract](../contracts/expert_agent_contract.md).
Use [verify-loop](../commands/verify-loop.md) for execution and evidence discipline,
[quant-loop](../commands/quant-loop.md) for research validity, and
[debug-metric](../commands/debug-metric.md) when a metric needs tracing.
These procedures are instructions, not deterministic state machines.

Before repeating a lever, read [the registry](../registry/levers.yaml) and its
DO-NOT-RE-RUN evidence. [gate-check](../commands/gate-check.md) evaluates the
[promotion bar](../contracts/promotion_gate.md) or records a previously established
verdict. The artifact family, honest search denominator and run class matter;
a successful YAML validation does not prove the statistical judgment.

Hooks provide bounded local checks and supporting evidence. Their actual events,
refusals and advisory modes are specified in [hooks](../hooks/README.md).
Configuration does not prove runtime activation. Syntax compilation is not a
behavioral test; command evidence is not a proof of causality or correctness.

The local run ledger stores command fingerprints, status and bounded signals,
not raw commands or transcripts. It remains private and ignored. Report material
claims with their actual source/artifact, check and limitations. No fixed evidence
table, five-risk quota or loop-ledger entry is required for every task.

When committing or pushing is authorized, use
[commit-research](../commands/commit-research.md) with explicit repositories and
scopes under [commit policy](../contracts/commit_policy.md). Inspect planned paths
and resulting commits. Keep git roots separate and preserve pre-staged work.
