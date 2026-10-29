# Constellation

Constellation coordinates requirements, evidence, review and publication on
Codex and Claude Code. The clients run models, tools and agents; each project
retains its files, data, permissions and Git ownership. One distribution brings
together four skills and eight canonical roles, with native entry points for
both clients.

The coordinator starts from the requested outcome, consults its session's
catalogue and loads the relevant capabilities. Discovering a tool does not prove
access or execution; a missing capability is reported or replaced with a tested
alternative. The [architecture](docs/architecture.md) explains these
responsibilities, and [evaluation](docs/evaluation.md) defines how to test them.

This English edition is generated from the same source and retains the same
plugin ID and version. Install it instead of the Spanish edition on the target
computer, rather than loading both copies. Accounts and personal configuration
are not transferred with the package.

## Choose the workflow

| Work | Execution |
| --- | --- |
| Brief question | Direct answer and an appropriate check. |
| Change in a repository | One contract in the receiving project, tests, review and publication by its Git owner. |
| Research or document with persisted evidence | Portable core, even without a repository or publication. |
| Mixed work | Capabilities and dependencies according to their obligations, without registering the same delivery twice. |

When available and consistent with the receiving project's instructions, the
skills `constellation:coding`, `constellation:mathematics`,
`constellation:quant-research` and `constellation:writter` cover substantive
engineering, mathematical arguments, systematic research and writing. An
engineering diagnosis without file edits or a nontrivial proof also requires
its relevant method. Brief questions, simple arithmetic and short translations
do not need that workflow. In Codex they can be invoked with
`$constellation:name`; in Claude, with `/constellation:name`. Naming a skill
does not load its instructions.

`UserPromptSubmit` supplies a static reminder to consult the catalogue, even
without a contract. It does not read, classify or store prompt text, and it does
not start a task. Scope and closure controls continue to act on active contracts.
Effective selection requires observation; the presence of the reminder does not
establish it. Formats and connectors remain with their providers; the
quantitative module does not activate real orders.

The [work criteria by responsibility](docs/architecture.md#work-criteria-by-responsibility)
make teaching explanations, the requested code design and adversarial research
concrete. Their [directed instruction trials](docs/evaluation.md#directed-instruction-trials)
check application of the method; they are distinct from automatic selection.

## Structure

| Source location | Responsibility |
| --- | --- |
| `.codex/skills/` | Canonical body of each skill and its specific references. |
| `.codex/ecosystem/runtime/` | Shared Git workflow, coordination, dispatch, review and progress. |
| `.codex/ecosystem/core.py`, `storage.py`, `cli.py` | Portable evidence, local persistence and public entry point. |
| `.codex/ecosystem/manifests/` | Source native plugin and hook manifests. |
| `.codex/ecosystem/agents/` | Eight canonical roles; the builder projects Claude's format. |
| `.codex/ecosystem/references/` | Protocol and methodological foundations used by the skills. |
| `.codex/ecosystem/docs/` | Maintained architecture, installation, progress, compatibility and evaluation guides. |
| `.codex/ecosystem/tests/`, `evals/` | Behaviour tests and evaluation cases. |
| `docs/history/`, `evals/results/`, within `ecosystem/` | Historical reports and results retained only in the sources. |

The modules `build.py`, `install.py`, `native.py`, `claude.py` and the hook
adapters retain their public entry points. Within the package, `skills/` and the
native manifests are projected from those sources. The two distributed hook
files retain their paths because those paths participate in their native trust
identity; they are not additional source copies. Keeping a path neither
preserves nor grants trust: the client may require fresh approval. Private
execution files and personal configuration remain outside the distribution.

## Install and update

Python 3.11+ and the chosen client are required; Git is used for publication.
The default target retains macOS/Linux. Candidate 1.4.0-rc.1 adds native
Windows for Claude Code; actual Windows acceptance remains pending. See the
[Windows guide](docs/windows.md). Building a package does not establish that
execution. For the POSIX target, build from published sources into a new destination:

```sh
python3 .codex/ecosystem/build.py --language en --output /tmp/constellation-1.4.0-rc.1-en \
  --archive /tmp/constellation-1.4.0-rc.1-en.zip
shasum -a 256 /tmp/constellation-1.4.0-rc.1-en.zip
```

Copy the package through an authorised channel and check its hash. The
[installation guide](docs/migrations.md#install-and-update) contains the commands
for both clients, preflight checks, updates and recovery. Do not copy the entire
personal Codex or Claude directories. Each computer retains its own accounts,
data, connectors and local policies.

The 1.3.1 reorganisation retains the native interfaces and separates guides from
historical evidence. Acceptance requires checking the update from 1.3.0 as well
as a fresh installation. Consult the [observed state](docs/compatibility.md): a
version number does not establish installation, trust or execution. Open new
sessions after updating.

## Work and check

In the hub, use `.codex/ecosystem/cli.py git --session ID` or
`.codex/ecosystem/cli.py workspace --session ID`. The old root launchers
have been removed; an open client session must load the changes through its
normal reload process. In a standalone package:

```sh
python3 /path/to/package/ecosystem/cli.py git --root /path/to/project --session ID begin
python3 /path/to/package/ecosystem/cli.py git --root /path/to/project --session ID plan < contract.json
```

In Claude, the workflow uses `claude-<session_id>`; authors and reviewers retain
their native IDs. The [protocol](references/protocol.md) distinguishes Git and
portable workflows, checks, review and limitations. Substantial work retains
[recoverable progress](docs/progress.md) in its existing store.

The [complete Codex diagnostic command](docs/migrations.md#codex-diagnostic)
queries a new CLI process; it does not automatically represent this chat.
For Claude, `claude.py verify` checks installation integrity. Then check the
catalogue, trust and events in the actual client. The
[compatibility matrix](docs/compatibility.md) separates this evidence from tests
and from the quality of model responses.
