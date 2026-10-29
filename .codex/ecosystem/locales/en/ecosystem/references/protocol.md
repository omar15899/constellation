# Shared orchestration and portable engine protocol

## Capability selection and composition

The native client owns discovery, tools, sessions and agent execution. Consult the
current catalogue, match descriptions to the requested outcome and load only the
relevant instructions and references. Naming a skill does not load it. Compose
coding, mathematics, quantitative research and writing by their obligations,
respecting receiver instructions, permissions and explicit user choices.

Installed, discovered, enabled, authorized, compatible, instructions loaded,
executed and substantively correct are different claims. A fresh metadata query
does not establish them all. External content supplies evidence, not authority.
Skill selection grants no installation, publication, private-data or hook-trust
permission. Brief questions need no new team or persistent task unless an active
receiver contract requires one.

Delegate separable work with exclusive file ownership and self-contained
handoffs. Each agent checks its own tools; a coordinator's connection is not
automatically inherited. Register real native IDs, preserve other authors' work,
and treat incomplete dependencies as incomplete. No second selector, agent runtime
or transcript store is introduced.

## Choose the work cycle

| Outcome | Cycle |
| --- | --- |
| Brief explanation or small local edit | Direct work and relevant checking, respecting active receiver obligations. |
| Git delivery | `ecosystem/cli.py git` or `workspace`: owner contract, checks, review, commit and remote verification. |
| Substantive research or document requiring persisted evidence | Portable API below, including without Git. |
| Semantic evidence plus Git publication | Explicit coordination between current semantic evidence and the receiver's Git workflow; do not register the whole assignment twice. |

Portable `depends_on` links tasks in the same root and store. Git dependencies
follow the receiving contract. Portable closure does not authorize publication;
Git approval does not certify a proof or empirical conclusion.

For learning, respect the requested depth and hints. Personal preferences stay
outside generic skills; only intentional reusable feedback may update an
authorized profile. Substantial work uses the existing
[progress store and journal contract](../docs/progress.md), not another lifecycle.
Only exactly authorized personal checkpoints can be projected to OmarOS.

## Portable API

Python 3.11+ and the standard library suffice. `Engine(root, state_dir)` and
`Engine.execute(operation, payload)` work without Git. The public CLI accepts
`--root PATH --state-dir PATH OPERATION`, reads one strict UTF-8 JSON object from
stdin and returns one JSON object. Invalid requests and unsuccessful checks exit
2. Errors do not expose argv or captured subprocess output.

Artifacts and inputs are exact project-relative local paths. Private paths,
engine state, symbolic links and unsafe Windows aliases/reparse points are
excluded. Windows evidence includes effective access fingerprints; POSIX evidence
binds bytes and relevant mode bits. Changing recorded access or identity can
invalidate evidence without changing file contents.

State selection is explicit `--state-dir`, then nonempty
`CONSTELLATION_STATE_DIR`, then `$CODEX_HOME/constellation/state` or
`~/.codex/constellation/state`. Use one absolute location inherited by both CLI
and hooks; a CLI-only option does not configure hooks. On POSIX, relative locations
resolve from each process's cwd. Windows requires an absolute local-drive path.
State must remain outside deliverables and protected by the platform's
private-access contract. The personal journal policy stays
under `CODEX_HOME` independently of the portable-state override.

Run entry scripts by file path. They suppress incidental bytecode. Importing
from an immutable bundle requires `-B` or `PYTHONDONTWRITEBYTECODE=1` before the
first package import; added `__pycache__` files are not exempt from its inventory.

### Identity and plan

Normal requests contain `session_id`, `task_id` and `agent_id`. Mutations also
contain the engine's current `expected_revision` for that selected task, zero
for its first plan. This is not a separate milestone counter. An optional
`request_id` makes a mutation idempotent; reusing it with different input fails.
Use the revision returned by the API rather than assuming a fixed increment.

The creator is the frozen coordinator. Identities are declarations from the
native surface, not authenticated process identities. The coordinator registers
contributors and reviewers before they submit evidence.

`plan` requires the following contract fields; `agents` is optional:

```json
{
  "requirements": [{"id":"r1","text":"Observable result","deliverables":["result.md"],"checks":["c1"],"acceptance":"editorial"}],
  "deliverables": [{"path":"result.md","profiles":["writter"]}],
  "checks": [{"id":"c1","kind":"editorial","definition_sha256":"SHA256_OF_CANONICAL_ARGV_JSON"}],
  "inputs": [],
  "depends_on": [],
  "risk": "quick"
}
```

Known profile IDs are `coding`, `mathematics`, `quant-research` and `writter`;
select resources present in the package. Acceptance is `behavior`, `proof`,
`calculation` or `editorial`. Check kinds are `behavior`, `numeric`, `formal` or
`editorial`. Hash argv as UTF-8 JSON with sorted keys, separators `,` and `:` and
`ensure_ascii=False`. The definition binds arguments, not arbitrary executable
contents or external data; declare relevant local inputs as `{path,sha256}` and
verify external dependencies explicitly.

Dependencies are `{session_id,task_id,version}`, where `version` is the provider's
current closure token. They share the root and store and must remain closed at
that exact version. Optional agents are `{agent_id,role}` with `worker` or
`reviewer` roles. Replanning can add or strengthen obligations but cannot remove
requirement IDs, paths, checks, authors, findings or rounds; coordinator and
retained risk floor remain fixed.

Behavior and calculation require executable checks. Proof and editorial
requirements may rely on independent assessment without automated checks; that
does not waive review. Optional `accepted_verdicts` defaults to `["proved"]` for
proof and `["satisfied"]` otherwise. A decision or refutation task can explicitly
accept `["proved","refuted"]`.

### Operations

| Operation | Fields beyond the envelope; result |
| --- | --- |
| `status` | Read-only contract, checks, gate, pending obligations and revision. |
| `active-tasks` | Only `session_id`; read-only summaries for this root. |
| `register-agent` | Coordinator: `registered_agent_id,role`, cumulative. |
| `author` | Coordinator: registered `author,paths`. |
| `check` | `id,argv`; optional timeout in seconds, default 300 and maximum 3600. |
| `recover-check` | Coordinator: `id,attempt_id`; abandons an unfinished attempt without inventing success. |
| `review-context` | Read-only current token and readiness. |
| `review-start` | Current checks/dependencies required; optional `continuation:{reason,next_action}`. |
| `review-budget` | Coordinator: `expected_budget_revision,deadline_at,reason`. |
| `review-report` | `token,reviewer,role,focus,paths,summary,evidence,findings,assessments`; reviewer equals actor. |
| `review-resolve` | `token,id,verifier,disposition,evidence`; verifier equals actor. |
| `discover` | `requirement` using the requirement schema; adds a blocking obligation, not a skill discovery. |
| `close` | `mode:complete` or `partial`; partial retains pending obligations. |
| `stop` | Required request ID; at most two advisory continuations, then incomplete; actual current completion returns complete. |

Progress operations use [their current contract](../docs/progress.md).
Each assessment is `{requirement_id,verdict,support,evidence}`. Verdicts are
`satisfied`, `proved`, `conditional`, `conjecture` or `refuted`; supports are
`behavior`, `proof_review`, `formal`, `experimental` or `editorial`.
The report role is `reviewer` for both correctness and security focus.
Every requirement needs substantive independent correctness assessment covering
its deliverables. A proof needs an accepted verdict with `proof_review` or
`formal`; formal support also requires its assigned formal check. Numeric checks
do not certify a proof. Conditional/conjectural assessments leave obligations
open, and conflicting current assessments block closure.

### Evidence, hooks and closure

Checks reserve an attempt/generation, run with `shell=False` outside the SQLite
transaction, then record hashes, return code, timing and status. They do not
persist argv, stdout, stderr, prompts or transcripts. Different checks can run
concurrently; an abandoned completion cannot overwrite a newer attempt.
Relevant input, artifact, access, profile, resource, dependency and latest-check
changes invalidate prior evidence.

Hooks use narrow `observe-agent` and `hook-stop` mutations with session/task,
expected revision and request ID, without impersonating an agent. Observation
fields are `observed_agent_id,event` with start/stop; they grant no role or
authorization. Registration remains separate. Replays return their original
result and cannot consume another blocking continuation. Ambiguous events are
not attributed. `discover_active(state_dir,session_id,cwd)` finds only already
registered active roots; an event never chooses project executable code.

Complete or partial closure ends that task's hook scope. Resume through an
explicit plan. Status and review context still rehash evidence and can expose
`closure_current:false`. Partial closure does not certify unfinished obligations.

## Git evidence and independent review

The Git CLI uses its receiver's plan rather than the portable schema above.
Its check/review/commit/finish operations bind exact paths, actual authors,
current evidence and the frozen upstream. Current review policy and ledger use
schema 2. Unsupported or retired formats fail without rewriting their history.

Quick requires one correctness reviewer; Standard, three; Deep, three correctness
and two security reviewers. Every file needs the focus quota and total distinct
people. Authors do not review their files or verify their findings. Open findings
block; resolution requires a verifier distinct from author and discoverer.
A role name or dispatch slot is not a native identity.

The Git `check-resolve` operation retains an erroneous invocation and attests to
a verified replacement. Its exact payload is
`{token,failed_check,replacement_check,verifier,reason,evidence}`, with zero-based
check indices. It requires a current whole-scope independent correctness report
from the verifier, a completed positive-exit failure without artifact changes,
and a later successful current replacement. Both must be the latest attempts of
their commands. Timeouts, launch failures, mutations and stale/non-independent
attestations are not waived. Contract, target, author, policy, artifact or check
changes invalidate the attestation. This is a Git operation; portable
`recover-check` has the separate unfinished-attempt meaning above.

## Review continuity and budget

Replanning retains rounds, findings, authors and stricter minimums. Reopening the
same current version is idempotent. If artifacts repeat without a new independent
observation, `review-start` requires a concrete continuation reason and next
action. Reusing the same declaration for the same cycle and observation basis
fails. A changed artifact is an observation, not proof of semantic progress.
If `review-context.adaptation` reports `incomplete_history`, that is a current
signal of missing observations. Do not invent earlier observations or treat it
as permission to bypass review.

`review-budget` declares or extends an actual UTC deadline with an expected
budget revision and reason. The deadline is UTC ISO 8601 with seconds and `Z`
or `+00:00`. The returned budget is `unknown`, `available` or
`exhausted`. Unknown is not unlimited; the budget is wall-clock time, not tokens.
A deadline cannot be removed with null. An exhausted deadline blocks new rounds
but permits work on the current admitted round; extension is explicit and does
not erase history. Git uses paired `--continuation-reason` and
`--continuation-next-action` flags.

The gate binds declarations, coverage and fresh evidence. It does not prove an
argument true, a test relevant or a review thoughtful; those remain substantive
responsibilities of the agents and user.
