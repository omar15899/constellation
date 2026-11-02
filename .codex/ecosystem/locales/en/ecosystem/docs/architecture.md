# One Constellation installation per device

Constellation maintains the methods and software that coordinate work. Codex
and Claude Code run models, agents and tools under the effective permissions
of each client. Documents, data and software changes belong to the project
that contains them.

## Source, installation and project

The Constellation repository holds the canonical source. On Omar's computer,
the checkout occupies the root of `~/GitHub`, which also contains independent
child repositories. Skill instructions live in `.codex/skills/`. The engine,
eight canonical roles, native adapters and tests live in `.codex/ecosystem/`.

The builder selects the resources for an edition and generates the inventory
of files, digests and permissions. The English and Spanish editions share the
same engine. Claude roles are generated from the same TOML definitions used
for Codex. The package carries instructions and code. Each device supplies its
own data, accounts, permissions, client configuration and project context.

In Codex, projects on a device use a **shared installation**. Hooks enter
through `CODEX_HOME/constellation/run`. The installer generates that launcher
for the device's selected absolute Python path, its physical executable and
the expected contents of `hook.py`. Startup can therefore use the selected
virtual environment even when the client has a different `PATH`. The launcher
reads and verifies `hook.py` before executing those same bytes. The entry
then checks the receipt and the package and holds a shared lock throughout
the operation. Installation needs the exclusive lock. An operation that
encounters a busy installation can be retried.

| Owner | Responsibility |
| --- | --- |
| Constellation | Skills, roles, Git engine, workspace routing, review, progress, hooks and vault profile. |
| Project | Identity, local instructions, reference documents, restrictions and project commands. Git determines the owner of each file. |
| Device | Client installation, module selection, registered vault root, configuration and hook trust. |
| Session | Loaded catalogue, available tools, effective permissions and agents actually run. |

## GitHub and OmarOS

From the hub or one of its children, `workspace route` resolves the Git owner,
branch, upstream and applicable instructions. For example, a README in Shared
and another in ResearchLab can belong to the same assignment and land on
different branches. Each goes through its owner's checks, review and
publication. The checkout provides a development entry for work on the
engine itself, while ordinary commands use the device installation.

Distribution 1.4.0 includes four general methods, `coding`, `mathematics`,
`quant-research` and `writter`. The full personal edition adds the `omaros`
module, which contains seven skills and the vault runtime profile. Its
catalogue therefore contains eleven skills. The module selection determines
the resources and roles in a particular package.

Profile enrollment identifies the precise OmarOS root and its Git repository
on the device. The adapter maintains the active contract, metadata and privacy
rules, renames, review and authorized delegates there. Git hooks are installed
for that owner. The vault's local entry sends its operations to the verified
engine. A query with no files or delegates can therefore close locally, while
a delivery with changes requires publication and verification of its owner's
remote.

## Updates and native discovery

Synchronization selects a published revision of the canonical repository,
builds the selected package and verifies the installation. Projects using
that installation receive the same version on subsequent invocations. Each
device promotes its own installation. An open chat may need a new session
to load the updated catalogue. Hook definitions are reviewed for trust in
the client on each device. The [installation guide](migrations.md),
[updates](updates.md) and [compatibility matrix](compatibility.md) describe
the steps and their boundaries.

The formats have independent version numbers. The bundle inventory uses
schema 1, the Codex receipt uses 4, the Claude receipt uses 1 and the review
policy and ledger use 2. The Codex receipt binds the interpreter, its physical
target and the launcher's digest and mode to that device installation. The
installer checks the inventory and the files it already owns before promoting
a new edition. A mismatch requires reconciling the existing files.

## Evidence and review

A Git assignment retains requirements, authorized paths, check results,
authorship, review and publication evidence per repository. The portable
engine stores evidence in SQLite for work delivered outside Git. The
coordinator judges which check satisfies each requirement, records real native
identities and opens review on the current artifacts.

Quick requires one correctness reviewer per file. Standard requires three.
Deep requires three correctness reviewers and two security reviewers.
Open findings prevent closure and resolution needs a verifier independent of
the author and the finder. The [protocol](../references/protocol.md) defines
freshness conditions. The [evaluation guide](evaluation.md) distinguishes
package integrity, observed client execution and quality of the result.

Guards handle the events and editing operations exposed by the client.
Shell and MCP writes remain subject to its effective permissions. Exclusive
promotion and filesystem access controls depend on operating system
primitives. The [Windows guide](windows.md) describes the evidence for the
Claude Code target.

In the Git, workspace and vault workflows, each `Stop` rechecks current
closure conditions, including when an earlier event is replayed. If the task
is still incomplete, a recognized event identity avoids consuming another
continuation. The retry history keeps at most three SHA-256 digests of
identified incomplete events. Each digest comes from event metadata and
recognizes a replay without storing the prompt or transcript.

## Progress and personal journal

Operational progress is stored in the project's private Git state, or in
SQLite for portable delivery. A journal milestone requires an exactly
authorized root and alias, a permitted destination and content explicitly
classified as personal. Each root, including a nested root, requires its own
authorization. The teaching profile and corporate material remain under their
receiver's rules. The receiver rechecks authorization and issues a
local receipt. Subsequent publication in OmarOS is established through the
vault workflow. The [progress guide](progress.md) describes recovery at the
source and how to retry interrupted delivery.
