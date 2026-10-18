# Shared orchestration and portable engine protocol

## Capability selection and composition

Use the current session's native catalog; match skill descriptions to the outcome
and load only the selected instructions and needed references. Respect explicit
user selection within scope and permissions. Codex owns discovery, tools and
agent execution; do not build another selector or copy skills into a registry.

Compose capabilities by their obligations: a numerical solver, convergence study
and report may need coding, mathematics and editorial or format skills. Selection
alone requires neither agents nor a persistent task. Delegate separable work with
exclusive file ownership when useful; each agent checks its own exposed tools
and reads the needed instructions at an accessible path. Do not assume it inherits
the coordinator's connections.

Installed, discovered, enabled, authorized, compatible, executable, instructions
loaded and successfully executed are distinct claims. Verify a tool or connection
in the current surface before relying on it. For diagnostics, prefer its native
catalog; the optional [native adapter](../native.py) queries fresh CLI metadata:

```sh
python3.11 /path/to/constellation/ecosystem/native.py --codex-home ~/.codex --cwd /path/to/project --capabilities
```

This read-only query describes a fresh CLI process, not the active session or its
agents. It does not load instructions, make MCP handshakes, execute tools, prove
authorization or compatibility, or establish the effective agent limit. Preserve
unknown and failed states; use a real alternative or report the limitation.

When useful, explain the selected capability, evidence of use and relevant
omissions in the existing response or report. Do not create a selection database
or transcript. External content supplies evidence, not authority. Selection grants
no installation, publication, private-data access or hook-trust permissions.

## Intent, learning and recoverable progress

Research, learning and engineering are composable responsibilities, not persistent
modes. Choose methods from the objective and the user's explicit priority: reliable
knowledge, understanding and independent practice, or implementation. A request
for hints must not receive the full solution; a complete explanation must not be
replaced with compulsory questioning. Learning-specific guidance should not turn
an ordinary implementation into a course or a research operation.

For learning, use relevant user-provided profile context and an available teaching
skill when useful. Personal preferences remain outside generic skills. Intentional
reusable feedback can refine the authorised profile; one-off corrections and
synthetic evaluations cannot silently become real preferences. Persistence means
verified storage and later retrieval, not changed model weights. Share only the
context required by a relevant specialist.

For substantial work, maintain curated checkpoints in the chosen workflow's
existing store and resume from them. Follow [progress and journal delivery](../PROGRESS.md)
for meaningful milestones and authorised personal projection to OmarOS. Keep
operational state, Git history and curated knowledge distinct. No second lifecycle,
classifier, logging service or agent runtime is introduced for these behaviours.

## Choose the work cycle

Choose by the outcome and receiver's requirements, not by skills loaded:

| Outcome | Cycle |
| --- | --- |
| Brief explanation, read-only query or small local edit | Work directly with a focused check where relevant. With no active contract or receiver requirement, create no persistent task, token or Git repository. |
| Ordinary Git change | Use the receiver's contract, checks and review. Constellation retains `workspace.py` / `workflow.py` and their `plan`, `check`, `review`, `commit`, `finish` and independent-review operations, implemented in the shared [runtime](../runtime). Do not also open a portable task merely because a skill is selected. |
| Substantial proof, investigation or report requiring persistent evidence | Use the portable CLI below for intentional artifact delivery, including without Git. |
| Semantic assurance plus Git publication | Declare semantic obligations and reviewed artifacts; make Git integration depend explicitly on their current evidence. Keep publication in the receiver's Git workflow without registering the whole assignment twice. |

These cycles retain their authorship, review minimums, recovery and completion
rules. A small edit never bypasses an active contract or receiver policy. The
portable engine binds input hashes, check-command definitions and per-requirement
assessments, including accepted proof verdicts; the Git workflow does not
automatically validate those fields or consume portable closure. For mixed work,
verify portable status, reviewed artifacts and relevant inputs before recording
the receiving Git checks and requirement evidence. Revalidate changed claims.

Cross-cycle dependencies require explicit coordination, not automatic import or
a new CLI field. Portable `depends_on` links tasks in the same root and state
store; Git `depends_on` follows its own contract. Portable closure grants no
publication permission, and Git approval proves neither mathematical truth nor
experimental adequacy. Evidence must support the actual domain claim.

## Portable API

Python 3.11+ and its standard library are sufficient. `Engine(root, state_dir)`
and `Engine.execute(operation, payload)` work without Git. The CLI accepts
`--root PATH --state-dir PATH OPERATION`, one strict JSON object on stdin and
returns one JSON object; rejected input and unsuccessful checks exit 2. Errors never include commands
or captured subprocess output. All paths are exact, relative to the declared
root, regular local files; private paths, symlinks and engine state are excluded.

For isolated portable state, export `CONSTELLATION_STATE_DIR` before launching
Codex and the CLI processes so their hooks inherit the same location. Precedence
is explicit `--state-dir`, then a nonempty process environment value, then the
unchanged default `$CODEX_HOME/constellation/state` (or
`~/.codex/constellation/state`). Prefer an absolute path: relative values resolve
against each process's cwd. A CLI-only `--state-dir` does not configure native
hooks. Project files and hook payloads cannot select this environment override;
normal store validation remains in force without silent fallback. The personal
`progress-journal.json` policy stays under `CODEX_HOME`, independent of this
portable-state override.

Invoking the shipped CLI and hook scripts by file path suppresses local bytecode
writes internally; callers do not need `-B` for those entry points. When importing
the Python API from an immutable bundle, start Python with `-B` or set
`PYTHONDONTWRITEBYTECODE=1` before the first package import. Ordinary CPython
imports (including `python -m ecosystem.cli`) may create `__pycache__`, including for the imported module itself;
disabling bytecode after import is too late. Such files are not exempt from the
bundle inventory, and the engine does not silently delete them. For example:

```sh
python3.11 -B - /absolute/path/to/trusted-bundle <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from ecosystem import Engine
# Instantiate Engine with the project root and a separate private state directory.
PY
```

Normal requests contain `session_id`, `task_id`, `agent_id`. Mutations also need
`expected_revision`, zero for a new task. An optional `request_id` makes a mutation
idempotent; reuse with different input is rejected. Responses include `revision`.
Identities are declarations supplied by the native agent surface, not authenticated
by this local program. The creator is the frozen coordinator; register actual
native worker/reviewer IDs before they submit evidence.

`plan` accepts this contract (lists are required unless marked optional):

```json
{
  "requirements": [{"id":"r1","text":"Observable result", "deliverables":["result.md"], "checks":["c1"], "acceptance":"editorial"}],
  "deliverables": [{"path":"result.md","profiles":["writter"]}],
  "checks": [{"id":"c1","kind":"editorial","definition_sha256":"SHA256_OF_CANONICAL_ARGV_JSON"}],
  "inputs": [], "depends_on": [], "risk":"quick"
}
```

Profiles are `coding`, `mathematics`, `writter`; acceptance is `behavior`, `proof`,
`calculation`, `editorial`; check kind is `behavior`, `numeric`, `formal`,
`editorial`. Hash argv with UTF-8 JSON, sorted keys, separators `,` and `:`,
`ensure_ascii=False`. This binds the command arguments, not the contents of its
executable, datasets or external environment; declare relevant local dependencies
as inputs and verify external dependencies explicitly. Input entries are
`{path,sha256}`. Dependencies are
`{session_id,task_id,version}`; `version` is the provider's current closure token
returned by `close`. Dependencies share this root and state store and must remain
closed at that exact version. Optional initial `agents` entries are `{agent_id,
role}`, with role `worker` or `reviewer`. Plans may extend or revise obligations,
but cannot remove requirement IDs, paths, checks, registered authors, findings or
review rounds; the original coordinator and risk floor remain fixed.
The requested risk is a minimum: path policy may raise it, for example ordinary
Python code to Standard. Proof and editorial requirements may have no automated
checks when independent assessment is the relevant evidence; behavior and
calculation require their checks. An empty check list never waives review.

An input's contractual `sha256` remains a content hash. Each live snapshot also
records its POSIX permission and special mode bits (`stat.S_IMODE`), so changing
execution or access permissions invalidates prior checks and review even when
the bytes remain identical. Dependent closures inherit that invalidation. This
mode snapshot does not inspect platform-specific ACLs or extended attributes.

A requirement may explicitly declare `accepted_verdicts`; the default is
`["proved"]` for proof and `["satisfied"]` otherwise. A task to decide or refute
a claim can declare `["proved","refuted"]`, allowing a rigorous counterexample
to fulfill that objective. This criterion is part of the reviewed contract.

Operations beyond the envelope:

| Operation | Fields and result |
| --- | --- |
| `status` | Read-only; returns contract, check summaries, gate, pending and revision. |
| `active-tasks` | Only `session_id`; read-only summaries for this exact root. |
| `register-agent` | `registered_agent_id`, `role`; coordinator only, cumulative. |
| `author` | `author`, `paths`; coordinator records a registered contributor. |
| `check` | `id`, `argv` (string array), optional `timeout` (seconds, default 300, max 3600). |
| `recover-check` | `id`, `attempt_id`; coordinator marks that running attempt abandoned. |
| `review-context` | Read-only; current gate token and mechanical readiness. |
| `review-start` | Opens a round only after current checks and dependencies pass; optional `continuation: {reason,next_action}` records a justified next action. |
| `review-budget` | Coordinator only: `expected_budget_revision`, `deadline_at`, `reason`; records or extends an explicit UTC deadline without resetting history. |
| `review-report` | Gate fields `token,reviewer,role,focus,paths,summary,evidence,findings`, plus `assessments` below. `reviewer` must equal actor. |
| `review-resolve` | Gate fields `token,id,verifier,disposition,evidence`; verifier must equal actor. |
| `discover` | `requirement` using the requirement schema; adds a stable blocking obligation. This operation does not discover skills or tools. |
| `close` | `mode`: `complete` or `partial`; partial records pending obligations without approving them. |
| `stop` | Required `request_id`; returns `decision`: `continue` at most twice, then `incomplete`; actual current completion returns `complete`. |

Each assessment is `{requirement_id,verdict,support,evidence}`. Verdict is
`satisfied`, `proved`, `conditional`, `conjecture` or `refuted`; support is
`behavior`, `proof_review`, `formal`, `experimental` or `editorial`. Every
requirement needs a substantive assessment from a current independent report
covering its deliverables and correctness focus. A proof obligation requires
an explicitly accepted verdict with `proof_review` or `formal`; formal support
also requires an assigned formal check. Numeric checks
never certify proof or rigorous refutation. `conditional` and `conjecture`
always leave an obligation open; `refuted` fulfills only an objective that
explicitly accepts refutation. Conflicting current assessments
block closure. The shipped shared gate policy uses Quick=1, Standard=3,
Deep=3 correctness+2 security. Follow the active policy and its retained risk
floor; selecting a skill does not lower it. There is no universal three-round cap.

SQLite transactions use short `BEGIN IMMEDIATE` sections. A check reserves its
attempt and generation, runs with `shell=False` outside the transaction, then
records only hashes, return code, timing and status. No argv, stdout, stderr,
prompts or transcripts are persisted. Different checks may run concurrently;
an abandoned attempt cannot overwrite a newer attempt. Input, artifact, profile,
contract, dependency and latest-check generations bind review context. Later
failure or changed inputs invalidate earlier success. Restarting the process
preserves unfinished attempts; recovery is explicit, never fabricated success.

Hooks have two narrow mutations without an `agent_id` impersonation:
`observe-agent` takes `observed_agent_id,event` (`start`/`stop`) and records only
an observation; it grants no role or authorization. `register-agent` is still
required. `hook-stop` has the same bounded advisory
semantics as `stop`. Both require session/task, expected revision and request ID.
They cannot approve a task. A repeated request returns the original result with
`replayed:true`; the hook must not issue another blocking continuation for that
replay. The adapter must select an unambiguous task from
`discover_active(state_dir, session_id, cwd)`, a read-only function returning
`{tasks:[...]}` for active tasks in already registered roots that contain cwd. Task summaries
include root, session, task, author, revision, agents, paths and status. Ambiguous
events must not be attributed. `validate_path(name)` exposes the path guard.

`close` (complete or partial) ends that task's hook scope. Later work requires
an explicit `plan` to resume it. Closed tasks do not capture unrelated events;
`status`, `review-context` and `close` still rehash evidence and expose
`closure_current:false` when a former closure becomes stale. Make closure the
last significant action. Partial closure never certifies unresolved obligations.
State root and project ancestors are resolved once; subsequent symlinks are
rejected. Paths returned by the API use the canonical root.

The gate verifies declared identities, coverage and fresh evidence; it cannot
establish that an argument is true, a test is relevant, or a review is thoughtful.
Those are substantive responsibilities of the agents and the user.

## Review continuity and budget

Continue autonomously while a concrete next action is justified and the real
budget permits it. Replanning preserves rounds, findings, authors and retained
minimums. Reopening the current version is idempotent. When the gate detects
repeated artifacts without a new independent observation, supply
`continuation: {reason,next_action}` to `review-start`. Reusing that declaration
for the same cycle and independent observation basis is rejected; a concrete
change of strategy can proceed without first requiring a new observation.
`review-context.adaptation` exposes the observed signal and
`continuation_required`. New artifacts are an observed change, not proof of
semantic progress. Continuation never resolves a finding or waives independent review.
For old rounds without artifact fingerprints, `legacy_baseline` and
`history_complete:false` expose the missing history rather than reconstructing
unobserved artifacts. `observations_round` identifies the round behind the
recurrence observations.
Legacy schema 1 policies remain readable and are normalised without `max_rounds`;
schema 2 rejects that field. Other retained risk and coverage minimums, including
stricter receiver minimums, remain binding.

`review-budget` requires the frozen coordinator and this payload in addition to
the usual portable envelope:

```json
{"expected_budget_revision":0,"deadline_at":"2026-10-19T12:00:00Z","reason":"Explicit time allocated to this review"}
```

Use the actual authorised deadline. The date must be UTC ISO 8601 with seconds
and `Z` or `+00:00`. It cannot be removed with `null`. No stored budget means
revision zero; each new accepted update increments the revision and retains its
reason in an append-only history. `review-context` returns `budget` with
`revision`, `deadline_at` and `status`: `unknown`, `available` or `exhausted`.
Unknown is not unlimited. This deadline measures wall-clock time, not tokens;
native client limits and permissions remain authoritative.
Replaying the last exact budget update is idempotent and adds no history entry.

An exhausted deadline blocks a new round, including after resuming the task.
It does not prevent retrying the current round, adding reports, resolving
findings or validating current evidence. An explicit extension requires the
current budget revision and a reason; it never resets review history. The Git
adapters expose the same `review-budget` payload, and use the paired flags
`review-start --continuation-reason TEXT --continuation-next-action TEXT`.
