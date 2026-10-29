# Constellation: shared authority, native execution

Constellation organises work; Codex and Claude Code run models, tools, agents,
sessions, permissions, skills and plugins through their native interfaces.
Projects retain their data, invariants, tests and Git ownership. There is no
second agent runtime or semantic selection service.

## Responsibilities and sources

| Responsibility | Authoritative implementation | Configuration and state | Consumers |
| --- | --- | --- | --- |
| Skill discovery and loading | Native client; session catalogue and its APIs | Native configuration, scope and plugin | Coordinator and agents according to their surface |
| Selection and composition | Model, native descriptions and skill instructions | Task requirements; no parallel registry | Each task |
| Capability diagnostics | `ecosystem/native.py` for Codex; `ecosystem/claude.py verify` and native commands for Claude | Read-only snapshot and integrity; no parallel catalogue | User, installation and maintenance |
| Independent review and continuity | `ecosystem/runtime/review_gate.py` | Shared policy, history, time budget and receiving-project extensions | Git, portable and OmarOS adapters |
| Git delivery and publication | `ecosystem/runtime/workflow.py` | Private contract and evidence in `.git/constellation` | Git repositories and coordinator |
| Coordination across repositories | `ecosystem/runtime/workspace.py` and `dispatch.py` | Declarative workspace registry and task dependencies | Hub and other explicit workspaces |
| Mathematical/editorial evidence without publication | `ecosystem/core.py` | Contracts with hypotheses, checks, evaluations and private SQLite | Research work and documents |
| Recoverable progress | `ecosystem/runtime/progress.py`; existing adapters | `task_progress` in Git JSON or portable SQLite; no new store | Substantial work and resumption |
| Personal journal | OmarOS `progress_journal.py` receiver and shared rendering | Exact personal policy, curated notes and minimal private index | Authorised personal sources and checkpoints only |
| Teaching personalisation | Available teaching skill and explicit user profile | Provisional, editable local profile outside the package | Explanations and intentional reusable feedback |
| Codex events | Stable entry point `CODEX_HOME/constellation/hook.py`, source `ecosystem/hook_entry.py`; adapter `ecosystem/hooks.py` | Receipt and inventory verified under a lock; static guidance and controls over active contracts; native trust | Installed plugin |
| Claude events | `ecosystem/claude_hooks.py`, translation to the same `ecosystem/hooks.py` | `claude-<session_id>` identity, structural metadata and explicit hook owner | Claude plugin or receiving-project adapter |
| Platform primitives | `ecosystem/platform_support.py` | OS-specific locks, private access checks and exclusive filesystem operations | Verified runtime and generated standalone Claude bootstrap |
| Distribution | `ecosystem/build.py`; installers `install.py` and `claude.py` | One allowlisted bundle, hashes, receipts and native projections | Codex, Claude and authorised receivers |
| Domain | Project `AGENTS.md`, tools and validators | Receiving project's own files | Its specialised work |

The public entry point is `ecosystem/cli.py`: `git`, `workspace` and
`agent-policy` select the corresponding shared runtime. The old root launcher
files and empty root hook manifest have been removed. Native hook manifests
inside the distribution remain active resources; existing client sessions must
load changes through the client. The hub maintains its repository registry;
it does not determine Git ownership of OmarOS or a third party.

## Source and distribution organisation

The structure separates four responsibilities: runtime, client adaptation,
maintained documentation and evaluation. `runtime/` retains the common
algorithms; public installation and hook modules adapt their interfaces.
`manifests/` contains their declarative sources, and `docs/` the operational
guides. `references/` retains the method consumed by the skills; it does not
duplicate operational documentation.

Dated reports in `docs/history/` and results in `evals/results/` remain outside
the installable package. They are retained to audit historical claims; they are
not engine inputs. Relevant fixtures and tests do accompany the package so it
can be checked without retrieving the original checkout.

The builder is already the boundary between source and distribution. It projects
plugin manifests to the paths each client requires and TOML role instructions
to Claude Markdown. Distributed hook manifests retain `ecosystem/hooks.json`
and `ecosystem/claude-hooks.json`: those paths form part of native identity and
are not changed for appearance. Keeping them neither preserves nor grants trust:
a modified installation or definition may require fresh client approval. Each
projection comes from one source in `manifests/`; there is no other registry or
architecture generator.

Receipts and checks for previous installations retain the ownership, integrity
and recovery needed for updates. They are data and controls of the current
installer; they do not maintain another active structure or runtime. The OmarOS
adapter and its verified derived copy belong to the current receiving contract.

The `1.4.0-rc.1` candidate adds a `windows-claude` target for native Windows
Claude Code, alongside language selection. It retains one shared engine and
adapts OS primitives; it neither installs WSL nor grants new permissions.
The builder mechanically embeds the canonical platform helper into the standalone
Claude bootstrap, which verifies the package before importing its modules.
The remaining runtime consumes the same resource from the verified distribution.
Actual Windows acceptance remains pending execution there; `docs/windows.md`
distinguishes local checks, replays and native dispatch. This target does not
establish Codex support on Windows or change the OmarOS pin.

## One distribution for several computers

The 1.3 line distributes one core and two native entry points; 1.3.1 reorganises
its sources and guides without replacing those responsibilities. Skills retain
one canonical body in `skills/`. Role instructions remain in
`ecosystem/agents/*.toml`; the builder generates the Markdown Claude requires.
The `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json` manifests
identify the same version and point to allowlisted resources inside the package.
The build and ZIP are deterministic for the same inputs and modules.

Each adapter translates native events and registration. Both consume the
existing contracts, checks, review and progress; they do not coordinate models
through another runtime. Agents remain client processes, with their model,
reasoning effort, permissions and effective capacity. The full distribution
includes all eight roles; a module selection retains the roles that selection
needs.

Claude supports a permanent plugin in `~/.claude/skills/constellation`, without
a marketplace or settings changes. Its installer protects that directory through
ownership and integrity; operational state lives outside it and survives updates.
Codex retains its native registration, receipt and stable entry point.
Installation differences reflect the clients' actual interfaces, without imposing
a single format that neither client guarantees.

Computers share a version, methodological sources and evidence controls.
Accounts, data, local policies, project registries and connectors remain separate.
The package does not carry transcripts, credentials, private profiles or research
state. An identical installation does not guarantee identical responses or that
a provider is available on both computers. Projects retain their original sources
and the Git owner of each delivery.

OmarOS keeps its adapter and its four derived resources pinned to 1.2.0. Version
1.3 identifies the dual-client distribution, rather than implicitly updating
the receiving project's pin. Its current updater only accepts 1.2.0 bundles and
must reject the new one until that contract is explicitly migrated. The
distribution is not copied over the vault's derived resources.

## Discover, select and execute

The **current session's** catalogue is the first source for deciding what the
agent can use. The client exposes metadata and loads a skill's body when it is
relevant. An explicit request takes priority within permissions and higher-level
instructions. The agent explains a selection when doing so helps explain the
work; it should not load irrelevant instructions to show that it knows the
catalogue.

Selection is reconsidered when the task changes or new evidence appears.
The coordinator first identifies the outcome's obligations: implement, prove,
check sources, present an artifact or use an external service. It then
distinguishes necessary, optional and inappropriate capabilities according to
the catalogue actually exposed. It reads the selected instructions before using
them and checks dependencies, permissions and inputs on the surface where they
will run. A subagent receives a concrete scope and verifies its own capabilities;
it is not assumed to have the coordinator's connections.

This discipline should produce observable decisions: an elementary definition
may need no skill; an algorithm with a mathematical justification may need
engineering and mathematics; a report based on someone else's data requires
provenance and authorised access. If a capability is missing, that gap is
preserved, and an alternative is tested before results are attributed to it.
Loading every skill or launching every role does not better satisfy those
obligations.

Negative controls test precisely these decisions: an irrelevant reference must
not activate another workflow, a discovered tool without access does not count
as used, and an agent's incomplete output does not approve delivery. The
[evaluation methodology](evaluation.md) separates relevance of selection,
effective execution and correctness of the outcome. Hooks observe specific
boundaries; they cannot prove that every future semantic decision by the model
will be correct.

The [complete Codex diagnostic](migrations.md#codex-diagnostic) queries a new
app-server from the installed CLI. That surface may differ from the client
hosting the conversation. For example, in 0.163.0, installed remote plugins
were observed that did not appear in the new process's `skills/list`, although
their skills were exposed in this session. Absence from that list does not
prove absence from other surfaces.

In Claude, `claude.py verify` checks the installation and leaves loading, trust
and execution unknown. `/context`, `/skills`, `/agents`, `/hooks` and `/status`
allow inspection of a particular session. Manifest validation likewise does not
run a research experiment. Checks and trials actually observed remain separate
in [observed compatibility](compatibility.md).

Installation, discovery, enablement, authorisation, compatibility and execution
are different facts. An MCP tool list demonstrates discovery, not a successful
call. An enabled and trusted hook still needs an executed event to establish its
behaviour. States without evidence remain unknown. A dependency error is reported
and addressed with an available alternative or a concrete limitation.

For a solver with analysis and a report, engineering, mathematics and the skill
for the requested format can be combined. Actual dependencies order execution;
independent work receives exclusive files. A brief definition is answered
directly. A small correction uses an appropriate change and check, without
ceremonial research or delegation.

Research, learning and engineering are combined according to the objective and
the user's explicit priority; they are not persistent modes or distinct engines.
Research distinguishes hypotheses, proofs, approximations and observations.
Learning applies only relevant personal context and respects the choice between
a complete explanation and guidance without revealing the solution. Generic
procedures never incorporate the personal profile. Calibration retains the scope
and provenance of intentional feedback; synthetic examples do not create real
preferences. Persistence means writing and retrieving context, not training
the model.

Model, reasoning effort and methodology are separate decisions. The package
does not fix a model or a global context window. The hub override imposing
1,000,000/900,000 tokens was removed; each client and model retains its observed
native limits. Changing the model does not modify contracts or local profiles,
but it does not guarantee equal tools, behaviour or capability either.

## Work criteria by responsibility

Writing establishes objects, spaces, hypotheses and relationships before using
notation; it distinguishes a function from its arguments and values and builds
the explanation to the required rigour. A scoped edit preserves voice and
structure with the smallest sufficient change. The authorised financial reference
was consulted as an editorial criterion: neither its content nor the personal
profile is redistributed.

Engineering chooses the design and level of abstraction requested by the task,
reuses the project's actual structures and applies Google Style where appropriate
to the language and its conventions. It makes precision and range explicit,
checks edge cases and repairs failures: documenting a limitation does not make
an incorrect result acceptable.

Research and review use primary sources, adversarial search and reproducible
findings. Their handoffs separate results, evidence and outstanding issues;
before waiting for an agent, they check its actual state. This reinforcement
changes instructions, rather than execution hooks, native formats or contracts.
It does not introduce a keyword classifier or guarantee semantic compliance by
the model.

## One sufficient workflow per objective

Ordinary Git work uses the Git workflow. A mathematical or editorial delivery
that does not require publication uses the portable core. Opening two identical
contracts is not required merely because a skill was selected. The presence of
`.git` does not decide this alone: publication requires an authorised upstream;
a local delivery can use portable within a Git directory.

The two adapters provide different guarantees. The portable core retains fixed
inputs, declared checks, evidence dependencies and evaluations per requirement
that distinguish a proof from an experiment. Basic Git review does not certify
these obligations automatically. Mixed work must declare its semantic
obligations and how they are verified before publication; when it requires a
portable certificate, that certificate is a concrete research result consumed by
the Git delivery, rather than duplicate closure of the same task. No hash proves
a theorem or the relevance of a test.

OmarOS retains the specialised adapter that protects renames, delegates,
private data and durable publication. It consumes the shared review algorithm
with its own policy and path validation. That adapter is not replaced by the
ordinary Git engine: its additional obligations remain necessary.

For small ordinary code changes, policy may allow a `quick_code_reason`
justification before the first round. It is bound to the complete snapshot and
assessed by an independent reviewer. A change in content, scope, authors or
policy invalidates it; it does not reduce established minima or Deep review of
sensitive paths. Stricter receiving-project policies prevail.

## Continuity and personal knowledge

Checkpoints record the objective, state, results, decisions, findings, evidence
and outstanding issues in the existing operational store. They retain identity
and chronology through replanning. Work can be recovered without OmarOS; a
failed delivery neither erases its state nor turns it into completed work.

The coordinator synchronises meaningful milestones permitted by local policy:
exact canonical root and alias, fixed destination and a personal checkpoint.
Registering a project or authorising its parent does not grant export permission.
The OmarOS receiver writes a curated note and dashboard through its own workflow,
with idempotent replay, stale-history rejection and recovery of interrupted
writes. `RECEIVED_LOCAL` establishes local receipt, not remote publication.

Operational state, Git history and scientific notes are distinct responsibilities.
The journal does not copy logs, conversations or learning profiles. Milestone
selection remains the agent's responsibility; there is no new daemon, classifier
or memory database. [Recoverable progress](progress.md) specifies the protocol,
permissions and recovery.

## Verifiable boundaries

The coordinator uses native agents, retains their actual identities and assigns
exclusive ownership. Effective capacity belongs to the session: project maxima
are not added together. A dispatch plan describes dependencies; it does not prove
its agents were launched. Tests with synthetic identities verify the mechanism,
rather than the quality of a review performed by a model.

Review adapts its continuity to observable progress and the actual budget,
without a universal limit of three rounds. The shared algorithm preserves
independence, history, findings and minima; budget extensions and continuations
are explicit. It does not incorporate another classifier or agent scheduler.
The [protocol](../references/protocol.md#review-continuity-and-budget) defines
these fields; receiving projects retain their additional restrictions.

The plugin's scope, review and closure controls observe active contracts.
`UserPromptSubmit` also supplies static guidance to consult the catalogue and
load relevant instructions, including when no contract exists. The common text
`METHOD_GUIDANCE` lives in `hooks.py`; Claude reuses it in its native startup and
context. The adapter processes the event JSON, but does not read prompt or
transcript fields, classify their content or store them. The reminder does not
start, synchronise or publish tasks.

The guidance identifies `constellation:coding`, `constellation:mathematics`,
`constellation:quant-research` and `constellation:writter` as options to be used
only if they exist and the receiving project's instructions permit them. It
includes engineering diagnosis without edits and nontrivial mathematical
arguments; it retains direct answers for brief questions, short translations
and simple arithmetic. A project-selected equivalent prevails where appropriate.
The presence of this text does not demonstrate that the model loaded a skill:
selection and its outcome are evaluated separately.

The hub definitions have been removed to avoid duplicate events. The plugin
command points to the stable entry point outside the versioned cache. A shared
lock protects hook validation and execution; the installer takes that same lock
exclusively to update. A collision or inconsistent installation produces a
controlled response, without running partially updated code. The installation,
trust and first-reload contract is in [README.md](../README.md#install-and-update).
The patch guard does not intercept every shell or MCP write. A bounded migration
bridge recognises active OmarOS contracts as data to authorise only their
explicit paths in the same session and frozen destination. It does not import
vault code or certify its closure, renames or knowledge validation; those
responsibilities remain in its adapter.

The Claude adapter reports the CLI and prefixed identity in `SessionStart`,
without starting a contract. It translates only identity, event, cwd and edit
paths; it does not transmit prompts, transcripts, tool content or agent results.
Claude does not document an equivalent `turn_id`: correlation uses deliberate
structural metadata and does not fabricate an identity from private text.
Agent observations retain the actual native IDs.

A receiving project declaring `CONSTELLATION_HOOK_OWNER=project` retains its
adapter's authority and avoids a second global treatment of events. Translation
does not execute project scripts. `onFailure: "block"` protects the native events
that support it; `Stop` and `SubagentStop` are outside that protection. Closure
requires explicit engine evidence and acceptance, even if the client stops
requesting continuations. File hooks do not confine arbitrary shell or MCP
writes either.

The hub's Git hooks control privacy and diff consistency; **a manual commit or
push does not require Constellation review**. Review and the frozen destination
are required on the workflow's publication path. Sweeplab and GasStorage hooks
retain their own responsibilities. Enforcement is not promised outside the paths
that actually implement it.

## Criteria published by OpenAI and Anthropic

This comparison uses public documentation and experience, consulted on
2026-10-29. It does not describe a universal internal architecture of the labs
or transfer their experimental metrics to Constellation. Package decisions are
tested against their consumers and local tests.

OpenAI describes in [Harness engineering](https://openai.com/index/harness-engineering/)
a brief instruction map, structured documentation and mechanically checked
invariants. Constellation applies that separation: the README provides direction,
guides explain responsibilities, and controls validate scope, evidence and
publication. Folder organisation helps maintain the system; it does not prove
that its agents produce better results.

[Codex personalisation](https://learn.chatgpt.com/docs/customization/overview)
and [Claude skills](https://code.claude.com/docs/en/skills) distinguish available
metadata from instructions loaded when needed.
[Anthropic's context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)
supports progressively retrieving relevant context. Selection therefore uses
the session catalogue and task obligations, without loading every body or
building another persistent selector.

The [Codex subagent](https://learn.chatgpt.com/docs/agent-configuration/subagents)
and [Claude subagent](https://code.claude.com/docs/en/sub-agents) interfaces require
respect for their effective context, tools and permissions. Constellation's
delegation assigns scope and verifiable results, but does not assume the child
inherits the coordinator's connections or skills already read. Published
multiagent evidence does not remove the need to check whether a particular
division of work improves that task.

## Correspondence with designs published by Anthropic

The comparison dated 2026-10-28 concerns observable principles and mechanisms,
rather than product equality or reproduction of Anthropic's internal results.
Its publications support a small structure that composes capabilities and
requires evidence. Incorporating every announced service, process or mode would
add dependencies without demonstrating that it improves this research centre.

| Published design | Constellation correspondence and limitation |
| --- | --- |
| [Effective agents](https://www.anthropic.com/research/building-effective-agents) | Skills and specialists are composed according to actual dependencies. A simple task does not need a team or persistent workflow. The client runs the agents. |
| [Multiagent research system](https://www.anthropic.com/research/multi-agent-research-system) | The coordinator scopes work, assigns files and requires results, sources and independent review. More agents do not prove better conclusions; breadth, citation accuracy and synthesis quality need their own evaluation. |
| [Context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) | The catalogue allows relevant instructions to be loaded, and handoffs retain scope, evidence and outstanding issues. Curated progress is recoverable without distributing complete conversations. Effective limits remain with the client. |
| [Agent Skills](https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills) | Instructions and references live in canonical files, are distributed modularly and are loaded when needed. The presence of a skill does not demonstrate selection or correct use. |
| [Harnesses for long tasks](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) | Explicit requirements, durable progress, current checks and review allow work to resume and determine what remains. Complete mechanical state does not replace a real test of behaviour or an argument. |
| [Agent evaluation](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) | Agent claims, observed outcomes and independent evidence are distinguished. Deterministic checks coexist with intellectual review. Repeated trials must distinguish obtaining some success from maintaining success in every attempt; model differences require representative cases. |
| [Adaptive harness design](https://www.anthropic.com/research/harness-design-long-running-apps) | Native execution and small adapters allow clients to change without duplicating the core. Author/reviewer separation is retained, and each added component must justify its purpose with evidence. |
| [Managed Agents](https://www.anthropic.com/research/managed-agents) | Recoverable state, contracts and execution are separated. State here is local, and each project retains its authority; distributing the package does not install a cloud service or offer its operational guarantees. |

[Claude plugins](https://claude.com/resources/articles/claude-code-plugins)
provide native distribution of skills, agents and hooks. Version 1.3 uses that
mechanism to deliver the same core.
[Dynamic workflows](https://claude.com/resources/articles/introducing-dynamic-workflows-in-claude-code)
can run tasks within the client, but adopting them does not replace the durable
contract or independent acceptance.
[Native plugin evaluations](https://code.claude.com/docs/en/plugin-evals) allow
cases to be tested against a baseline without the plugin; they are an additional
tool requiring availability and model calls, rather than a condition for
installing or verifying the package offline.

The comparison leaves outcome measurement between Codex and Claude open: run
the same scoped question, check sources and counterexamples, provoke missing
or failed evidence, and verify that no synthesis turns it into approval.
Anthropic's published percentages and improvements are not measurements of
Constellation.

The [published measurement of internal action coverage](https://www.anthropic.com/institute/measuring-pace-of-ai-development)
does not transfer to this package either. Its hooks observe particular events
and protect the declared file tools; they do not universally intercept shell,
MCP or every client action. Review and publication check scope again through
their own path.

## Native references

Behaviour is checked against the installed binary and the documented interfaces
for [skills](https://learn.chatgpt.com/docs/build-skills),
[hooks](https://learn.chatgpt.com/docs/hooks) and
[app-server](https://learn.chatgpt.com/docs/app-server), and against the Claude
interfaces for [plugins](https://code.claude.com/docs/en/plugins/create),
[hooks](https://code.claude.com/docs/en/hooks) and
[subagents](https://code.claude.com/docs/en/sub-agents). Newer documentation does
not turn its fields into parameters supported by an older version.
