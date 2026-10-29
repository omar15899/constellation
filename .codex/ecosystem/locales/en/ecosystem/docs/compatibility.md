# Observed compatibility

## Candidate 1.4.0-rc.1: native Windows Claude

The candidate adds a native Windows adaptation for Claude Code without WSL.
Actual Windows execution remains pending: a macOS build or static review does
not establish locks, ACLs, recovery or event dispatch on that operating system.
The [Windows guide](windows.md) separates isolated backend acceptance, direct
event replays and the real native-client workflow. Native Windows Codex is
outside that target.

Before the platform changes, the English baseline passed 368 tests and five
exported suites of 351 tests each, with explicit module-specific skips. Temporary
English installation, repetition and updates between languages also passed for
both installers. That is POSIX baseline evidence, not acceptance of the Windows
candidate or a new model evaluation.

The installer reports whether directory flushing is supported. An
`unsupported` result does not imply POSIX-equivalent directory `fsync` or
power-loss durability. Windows checks that have not run remain pending.

## Acceptance of 1.3.1

Evidence recorded on 2026-10-29: **code checked, with explicit acceptance
limits**. The battery before the last oracle correction passed 353 direct tests.
That run omitted only the recursive harness for five exports, which had already
passed in the earlier integrated suite of 349 tests. The subsequent probe delta
passed five focused tests; the 353 are not presented as a complete reevaluation
of the code after that change. Groups and retries are not added together as
independent cases. Each finding separately retains its repair, independent
verification and formal resolution against the current review token. This
checkpoint does not anticipate closure of new or still-pending findings. This
document does not establish publication: workflow closure certifies it.

| Surface | Candidate or baseline observation | Limit |
| --- | --- | --- |
| Predecessor 1.3.0 | The original package of 78 resources was reconstructed; its `bundle.json` matches SHA-256 `316b0ac84300291a0409776f95c78c140b38bf3e33e30e965e34be1b1540ffce`, without executing code from the previous copy. | The match establishes the artifact used for migration, rather than its execution in a client. |
| Package 1.3.1 | The distribution contains 77 resources, with paths and content different from the historical 78. The executable probe is distributed; its security test belongs only to development. | Inventory size does not certify behavior. Trial hashes identify their snapshots, rather than a later distribution including this documentation. |
| Update 1.3.0 → 1.3.1 | Both installers updated temporary homes; Codex used its real native CLI and Claude verified file replacement and its receipt. | File testing is distinguished from the native dispatch observed later. |
| Codex baseline | Codex CLI 0.164.0 showed package 1.3.0, four skills and five trusted hooks. | This describes the earlier version, rather than the candidate's trust. |
| Codex 1.3.1 | Following user approval, the native query confirmed that all five hooks were `trusted` and enabled. | Trust was approved by the user; preserving paths or passing tests does not grant it. |
| Real Codex path | CLI 0.165.0 ran parent and child: declared `apply_patch` allowed the exact bytes; an undeclared patch was blocked by `preToolUse` with “outside the registered scope” and left the file absent. Start, end and final `observed_agents` value `stop` were observed. | The parent's only registered contract remained `active` with `closed=false`; no nonexistent closure was approved. The child's `threadId` does not establish a payload `session_id`, its role or persistence. |
| Claude probe | The oracle correction uses an explicit allowlist and passed the five current focused tests. The five native cases with Claude Code 2.1.301 and locally simulated HTTP responses belong to the earlier trial. | Validation of the latest delta is distinguished from the earlier native execution. Simulated responses do not measure the quality of a remote model. |
| Real Claude subagent | A `constellation:ecosystem-coder` child wrote the declared bytes; its undeclared `Write` received a `PreToolUse` deny and left the file absent. Both operations retained the parent session; `SubagentStart`, `SubagentStop` and final `observed_agents` value `stop` were observed. | The portable contract correctly remained `active` after two Stop attempts. Closure was not fabricated, and neither Git publication nor autonomous role selection was tested. |
| Engine concurrency | 132 focused tests passed, and a trial processed 64 starts and 64 stops in 3.317 seconds. | This does not represent 64 model agents running or support extrapolating performance. |
| Claude semantic selection | On a single candidate, three of four substantive cases invoked their skill: engineering, mathematics and quantitative research. The writing case produced 179 words without invoking it. | The writing deviation is preserved; it is not replaced with its success under another guidance variant. The sample does not establish perfect selection or general causality. |
| Controls and responses | The two negative controls were resolved without tools; all six responses were complete according to their structural checks. | Completing a response or passing a structural oracle does not demonstrate its truth, general quality or correct selection. |

The semantic trial belongs to the acceptance snapshot whose `bundle.json` has
SHA-256 `102355132d6bb9831c93faae28306dbd083ea2bed6e8e84e53f3a2385af4a505`.
Its hooks match the evaluated code; subsequent instruction and documentation
changes do not make that hash the final distribution's hash. The 3/4 result
predates the strengthened instructions and does not measure automatic selection
of the expanded version. Its [directed instruction trials](evaluation.md#directed-instruction-trials)
are recorded separately, preserving the initial overflow failure and the
mathematical findings; the expansion does not change hooks, grant trust or
publish. The real Claude child-scope trial previously used snapshot
`0c0ed70f4b2cd31a32d05905d9fd456246d281ea2de21a185c23cdc9db871714`.
The static selection guidance changed afterwards, rather than the scope guard.
These are distinct observations and are not presented as a single execution.

The real Codex path belongs to the bundle whose `bundle.json` has SHA-256
`cdab498632f9e4f019840ee27baf8fa2c0872fb523dcd794ecfcbd3b4798ccf1`.
It used an ephemeral app-server; the parent inherited `gpt-6-astra` and `max`
effort. There was no timeout or unexpected approval. The child's `threadId`
was observed, but its payload `session_id`, role or persistence were not directly
observed; those fields are not inferred from acceptance of the operations or
the parent contract.

The native Claude editorial trial on snapshot `cdab4986…` used an explicit
`--agent`, invoked `writter` through `Skill` and performed two package `Read`
operations. Its text opened `NE-ONTO-01` and `NE-PROB-02`; instruction corrections
do not turn that first result into a pass. The first repetition attempt with
bundle `1d649b6f77b16523f9a863428696e71527a339022530d9fa03334e1d74ef5fac`,
verified locally with 77 resources, was rejected by automatic review before
process creation because explicit authorization for transmission to Anthropic
was missing. That attempt involved no model, sent stimulus or result; the
rejection was respected without switching routes.

The user then authorized repeating the same stimulus. That autonomous trial,
before the guided correction and with the role selected explicitly, completed
the process with bundle `1d649b6f…` fixed: four turns, one `writter` invocation
through `Skill` and one `Read`. Process success did not mean text acceptance:
`NE-ONTO-01` persisted, and `NE-PROB-NECESSITY-01`—also recorded as
`NE-ERROR-MODEL-03`—and `NE-PROB-REPETITION-01` were identified. Their failures
are not replaced by the result of the later pass.

A subsequent correction attempt with the text and findings received a second
automatic rejection before process creation: the initial authorization did not
cover that new transmission to Anthropic. There was no execution or new artifact,
and no switch of route. The user then explicitly authorized that correction of
the same trial using its text and findings. The real call completed in Claude
Code 2.1.301, with inherited model `sonnet-5-5` and explicit role, kept that bundle
fixed: one turn, zero tools, reads or denials, and three hooks completed
successfully. This is a **directed revision with feedback**, rather than blind
generation or a new automatic-selection test. The complete artifact has SHA-256
`2ffbd46ca500f63c027e454d15a296a114e93fac6e86e0ba256a7002cdd9a679`.

Verifiers independent of the authors and discoverers confirmed the repairs of
`NE-ONTO-01`, `NE-PROB-02`, `NE-PROB-NECESSITY-01` and `NE-PROB-REPETITION-01`,
with no new material errors in that text. `NE-ERROR-MODEL-03` identifies the
same failure as `NE-PROB-NECESSITY-01` and is not counted as another finding.
The directed revision is accepted for that artifact; the earlier block and
failures are preserved. No causal improvement is attributed exclusively to the
latest editorial guidance, and general perfection is not claimed. Execution
code and hooks did not change in that last guidance adjustment. Integration and
publication are established through the workflow, rather than text acceptance.

The probe distinguishes the trusted Claude binary from a candidate CLI. For the
former, HOME, Keychain and external networking are denied, and writes are limited
to the trial's temporary area. The candidate adds a clean environment, fixed cwd
and strict read policy. The candidate's additional restrictions are not
attributed to execution of the trusted binary. Focused probe tests check these
boundaries, the tool allowlist and the canaries.

The static guidance includes engineering diagnosis without editing and nontrivial
mathematical arguments; it conditions use of the four entries on their
availability and the receiver's instructions. Its tests establish that it does
not inspect private fields or open contracts. The six earlier real cases
measure adherence separately and preserve the case in which the skill was not
loaded.

Observation distinguishes inventory, installation, catalogue, trust, event and
result. A new process does not automatically represent an open chat. The
[acceptance matrix](evaluation.md#acceptance-of-131) preserves these obligations;
earlier results do not constitute a universal guarantee of the orchestrator.

## Dual distribution 1.3 — 2026-10-28

This section preserves the evidence for 1.3.0 from 2026-10-28. The real subagent
trial for 1.3.1 appears above; it is not retrospectively attributed to this
baseline.

This distribution aims to install the same research sources and the same
evidence core on several laptops, with native entries for Codex and Claude Code.
The package version, its integrity, what a client loads and hook execution are
distinct forms of evidence. Structural equivalence does not demonstrate equal
results or available connectors.

| Surface | Evidence and limit |
| --- | --- |
| Installed Claude Code | The real CLI 2.1.301 ran the isolated trials. It is the conservative reference for this integration; it does not establish earlier versions or other laptops. |
| Native bundle validation | `claude plugin validate --strict --json` exited with code 0, without errors or warnings. Four namespaced skills and eight roles were observed. |
| Permanent plugin in the skills directory | In an isolated home with spaces, the first installation returned `installed` and repetition returned `unchanged`; verification confirmed the 1.3.0 receipt. The CLI listed `constellation@skills-dir` as enabled and, without `--plugin-dir`, loaded the four skills and eight roles. |
| Observed native events | The CLI dispatched `SessionStart`, `UserPromptSubmit`, `PreToolUse` and `Stop`. Schema validation and actual execution were checked separately. |
| Editing denial and permission | An out-of-scope `Write` was denied and its file remained absent. A declared `Write` was allowed and created the file. Permanent loading also rejected the undeclared edit. |
| Incomplete portable closure | A pending contract produced exactly two Stop continuations and then `INCOMPLETE`, without approving its closure. This does not demonstrate the correctness of a scientific conclusion. |
| Operational hook failure | A hook that exited with code 17 was blocked through the native failure policy. Protection for Stop and SubagentStop remains different. |
| Native subagent events | `SubagentStart` and `SubagentStop` were not verified in the CLI. Loading roles and the adapter's 17 focused tests do not substitute for that dispatch. |
| Another laptop | The ZIP and its hash allow installation to be repeated. Using two temporary directories has not established a test on different hardware. |
| Platforms | Python 3.11+ and POSIX locks. macOS/Linux are the implementation scope; WSL requires validation in that environment. Native Windows is outside coverage. |
| OmarOS | Its four derived resources remain pinned to 1.2.0. The receiving updater does not accept 1.3.0 bundles without an explicit migration. |

The native trials used an exclusively local simulated HTTP response and a
synthetic credential. External networking, the real HOME and Keychain were
blocked. No remote model calls occurred. Client integration and operation
control were checked, rather than research capability or response quality.

The attempt to exercise the Agent tool received a rejection from automatic
approval review: the auto-mode classifier could not evaluate the action with
the local simulated response. Permissions were not changed and no retry was
made through another mode. Consequently, that 1.3.0 trial did not establish
native execution of the two subagent events, although their roles were loaded
and the adapter had tests.

Portability acceptance also requires repeated builds, isolated destinations at
different paths, updates, preservation of independently owned configuration,
file tampering and interruption of replacement. Engine and package checks are
recorded separately from native dispatch. Research tests add missing evidence,
failed agents, changed sources and independent review. None alone certifies the
truth of a proof or the validity of an empirical conclusion.

The documented semantics of `onFailure: "block"` require Claude 2.1.295 or later,
but do not protect Stop or SubagentStop. The implementation must preserve
acceptance in deterministic commands. Each client's settings, managed policies
and personal authorizations may affect actual loading. Local configuration does
not demonstrate account training or retention controls. Its data is not copied
to the bundle.

The [official 2.1.312 release](https://github.com/anthropics/claude-code/releases/tag/v2.1.312)
was published on 2026-10-27; the observed local binary remains at 2.1.301. This
assignment does not update it. Current publications and documentation may
describe capabilities later than that binary. In particular,
[dynamic workflow recovery](https://code.claude.com/docs/en/workflows#which-agents-run-again)
distinguishes behavior before 2.1.305; its new guarantees are not attributed
to 2.1.301.

The [comparison with published designs](architecture.md#correspondence-with-designs-published-by-anthropic)
relates Constellation's method to official articles on composition, multiagent
research, context, skills, recovery and evaluation. It compares mechanisms and
obligations, rather than demonstrating their experimental results in our system.
Native plugin evaluations are not run as an innocuous check: they require models
and may publish a report. An authorized trial with local data must keep its
report local through `--no-publish` and explicit limits.

Primary references for this integration:
[permanent Claude plugin loading](https://code.claude.com/docs/en/plugins/create#make-a-plugin-load-in-every-session),
[schema and components](https://code.claude.com/docs/en/plugins/manifest-reference),
[hook failures](https://code.claude.com/docs/en/hooks#block-the-action-when-a-hook-fails)
and [native agents](https://code.claude.com/docs/en/sub-agents).

## Current compatibility conditions

Capabilities belong to the observed surface and version. Model, effort, context
and permissions are inherited; agent maxima are not consumption targets.
Unobserved telemetry remains unknown. Clients must reload a session when an
update requires it; the installer neither grants trust nor changes its hashes
to obtain approval. Update and recovery steps are in the
[installation guide](migrations.md#install-and-update).

Isolated portable state needs the same `CONSTELLATION_STATE_DIR` inherited by
CLI and hooks; `--state-dir` affects only that invocation. It must be an absolute
path. The setting does not change permissions or personal policy; its contract
is in the [protocol](../references/protocol.md#portable-api). Reading state through
the CLI does not establish that hooks used the same state.

Old matrices and metrics for 1.0, 1.1 and 1.2 are preserved only in the sources,
at `ecosystem/docs/history/constellation-1.1.md`, alongside their evaluation
context. They are not part of the installable bundle and do not describe current
capabilities.
