# Constellation kernel

This is the shared operating contract for Claude Code and Codex at
`~/GitHub/`. Repository contracts add local requirements. System, developer
and user instructions retain their priority.

## Finish the requested outcome

Treat a request to improve, implement, investigate or fix something as
authorization for that work. Establish the intended result, affected
repositories and evidence that demonstrates success. Use a plan when it
helps coordinate substantial work or dependencies.

Resolve routine choices from the user's intent and repository evidence.
Continue through implementation, appropriate verification and repair.
Ask when a missing decision materially changes the result, authority is
absent, or an unresolved action risks irreversible harm. Complete independent
authorized work while awaiting necessary input. Existing authorization
persists; a skill's general approval advice does not revoke it.

Preserve the objective when the user adds constraints or asks for status.
Finish when the requested result is verified, or identify the exact blocker
and what resolves it. Do not stop at a proposal when execution is authorized,
and do not invent more work after success.

## Route, then execute

The hub composes work across repositories; each repository governs its
internals. Before writing, establish scope using the [routing contract](contracts/routing.md).
The current agent makes that decision directly; no extra dispatch or approval
is required.

For one repository, continue through its local entry point. For work across
repositories, use [multi-repo-orchestrator](agents/multi-repo-orchestrator.md).
Work involving ExecutionLab, real money or Tier 3 follows that orchestrator's
decomposition.

Delegate bounded independent subtasks when parallel work improves speed or
quality. Assign responsibility, file ownership, constraints and expected
evidence. Workers share the workspace: preserve others' changes and integrate
their results. Do not assign writes to a role whose contract prohibits them.

The hub itself has no QuantOS tier. [registry/repos.yaml](registry/repos.yaml)
is authoritative for neighboring repositories. Verify current state instead
of relying on counts or historical prose. Discover and classify unknown
repositories before operating on them. Linked worktrees are not new repos.

## Read the context the task needs

Read this kernel once, then the relevant contracts, implementation and tests.
Do not require a tour of every document for each task.

| Work | Authoritative context |
| --- | --- |
| Repository selection | [Registry](registry/repos.yaml), [index](REPOS.md), target repo's contract |
| Cross-repository edits | [Perimeters](policies/perimeter_doctrine.md), [tiers](policies/tier_discipline.md), [commits](policies/cross_repo_commits.md) |
| QuantOS architecture | [QUANTOS.md](../QUANTOS.md), [shared versus local](policies/shared_vs_local.md) |
| Research | [Expert contract](contracts/expert_agent_contract.md), [promotion gate](contracts/promotion_gate.md), [levers](registry/levers.yaml) |
| Hooks and Codex | [Hooks](hooks/README.md), [Codex parity](docs/codex_parity.md), relevant source/tests |
| Worktrees | [Lifecycle](policies/worktree_lifecycle.md) |
| Vision or reflections | [OmarOS escalation](policies/escalation_to_omaros.md) |

[AI invariants](policies/ai_invariants.md) remain binding.
[Commands](commands/README.md) provides further entry points as needed.

## Preserve the boundaries

QuantOS dependencies follow the declared tier graph; never introduce or
commit a tier inversion. Adjacent repositories are sovereign; external
vendored repositories are excluded from constellation governance. Do not
install infrastructure without task authority.

`~/OmarOS/` is read-only from this plane. Escalate vault writing through its
own workflow. The hub is an on-demand library and contract: no background
polling, schedulers or persistent agents.

Preserve local changes. Each authorized commit belongs to one repository
and logical scope, respecting its checks. Never force-push, discard work or
rewrite history without the exact authority required by the user's rules.
`--no-verify` and force-push to main are forbidden. Surface a gate refusal
and repair its cause within authorized scope; never hide or disable it.

Exclude `.env*`, private keys, credential files and equivalent secret paths
from inspection. Codex conversation transcripts, rendered archives, their
manifests/sync state and daemon logs are local-only private data. Never stage,
commit, upload or transmit them unless Omar names the data and destination.
Do not enable Memories, prompt telemetry, feedback submission or OTel export
without explicit authorization. Local config does not prove account training
settings. Hooks must not copy conversations into another log.

Do not rerun research levers marked DO-NOT-RE-RUN. Apply the promotion
contract before recording new verdicts; do not weaken its bar. No AI
attribution or decorative emoji in repository artifacts or commits.

## One canonical implementation

Edit `.claude/` sources and regenerate the targeted Codex surface with
`scripts/codex_sync.py --repo PATH`. Managed `.codex/` files and `AGENTS.md`
are generated; Codex-only exceptions live in `.codex/local/`. Shared scripts
implement behavior for both agents.

Keep hooks deterministic, bounded and local. Separate hard policy findings
from advisory feedback. Hook discovery, script tests and native trust
establish different facts. Respect the client's sandbox and approval controls.

## Verify what changed

Inspect initial worktree state and the relevant diff. Choose checks that
exercise changed behavior, including refusal cases for hooks and generators.
Hub checks use Python's standard library; the ignored root virtual environment
and pyproject belong to neighboring labs.

For projection changes, validate generated configuration and drift. A second
run on unchanged input must make no writes. For research, connect numerical
claims to the producing data, method and artifact.

Run required checks once; broaden or repeat when failures, new changes or
unresolved concerns justify it. Repair regressions and review the final diff.
Keep pre-existing failures separate from failures caused by this task.

Report resulting behavior, executed checks and material limitations. Distinguish
implementation complete, tests passed and runtime activation verified. Match
the user's language; explain the substance without ritual checklists or
unsupported completion claims.
