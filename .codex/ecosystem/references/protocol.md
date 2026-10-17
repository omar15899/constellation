# Portable engine protocol

Python 3.11+ and its standard library are sufficient. `Engine(root, state_dir)`
and `Engine.execute(operation, payload)` work without Git. The CLI accepts
`--root PATH --state-dir PATH OPERATION`, one strict JSON object on stdin and
returns one JSON object; rejected input and unsuccessful checks exit 2. Errors never include commands
or captured subprocess output. All paths are exact, relative to the declared
root, regular local files; private paths, symlinks and engine state are excluded.

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
`ensure_ascii=False`. Input entries are `{path,sha256}`. Dependencies are
`{session_id,task_id,version}`; `version` is the provider's current closure token
returned by `close`. Dependencies share this root and state store and must remain
closed at that exact version. Optional initial `agents` entries are `{agent_id,
role}`, with role `worker` or `reviewer`. Plans may extend or revise obligations,
but cannot remove requirement IDs, paths, checks, registered authors, findings or
review rounds; the original coordinator and risk floor remain fixed.

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
| `review-start` | Opens a round only after current checks and dependencies pass. |
| `review-report` | Gate fields `token,reviewer,role,focus,paths,summary,evidence,findings`, plus `assessments` below. `reviewer` must equal actor. |
| `review-resolve` | Gate fields `token,id,verifier,disposition,evidence`; verifier must equal actor. |
| `discover` | `requirement` using the requirement schema; adds a stable blocking obligation. |
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
block closure. Quorum remains solely the shared gate's
Quick=1, Standard=3, Deep=3 correctness+2 security, at most three rounds.

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
