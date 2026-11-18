# GitHub Copilot

Constellation owns the role definitions, engineering guidance, skills and review
ledger. Copilot CLI supplies the model, permissions, tools and native subagents.
This integration targets the local CLI on Windows, macOS and Linux. For the
Copilot extension bundled with Microsoft Visual Studio, see the
[Visual Studio guide](visual-studio.md). The definitions are in English.

## Source and native layout

```text
Constellation/
├── agents/*.toml                    # eight canonical roles, shared by all clients
├── instructions/AGENTS.md           # common ownership, quality and privacy rules
├── skills/core/coding/              # readable engineering and permitted evidence
├── constellation/copilot.py         # generated native documents and install plan
├── constellation/copilot_hooks.py   # native event translation, shared scope checks
├── .github/copilot-instructions.md  # this repository's Copilot entry point
└── profiles/copilot.md              # this guide and official source map

~/.local/state/constellation/
├── native/copilot/                  # generated adapters, never a second source
├── tasks/                          # exact ownership, evidence and review records
└── installations/                  # reversible installation receipts

~/.copilot/
├── agents/*.agent.md                # links to generated role adapters
├── hooks/constellation.json         # link to the generated hook configuration
├── copilot-instructions.md          # owned block plus preserved personal content
└── docs/official/                   # public reference snapshots with provenance

~/.agents/skills/                   # existing shared personal skills
```

`COPILOT_HOME` or `install --copilot-home PATH` can select a different native
home. Documentation snapshots stay under `HOME/.copilot/docs/official`:
the documentation command's `--home` selects that parent home, not `COPILOT_HOME`.
Project skills remain under their existing owners. Copilot-only installation
does not copy other projects' skills or change their Git configuration.

## Install and inspect

From the canonical checkout:

```sh
python3 constellation.py install --client copilot
python3 constellation.py install --client copilot --apply
python3 constellation.py docs --provider copilot refresh
python3 constellation.py docs --provider copilot verify
python3 constellation.py docs --provider copilot search 'include-custom-instructions'
```

On Windows use `py -3 .\constellation.py` as the entry point in PowerShell.
Generated roles, the hook configuration and skills are installed as regular
files or directories on Windows. The private state default is
`%LOCALAPPDATA%\Constellation`. The separate `docs` commands in this
example require macOS or Linux.

The first command shows exact planned paths. Applying it preserves unrelated
files, reports conflicts and records a rollback receipt. A conflict is not a
successful installation of that entry. No authentication, model, telemetry,
Memories, trust or permission setting is changed. No test suite runs.

Open a new Copilot CLI session after installation. Use `/agent`, `/instructions`
and `/skills` to inspect discovery. A native CLI binary, an eligible account and
the client's admission of hooks are separate requirements. File generation alone
does not prove discovery, hook execution or successful parallel review. Do not
run a model session or a behavioral probe and call it static inspection.

Rollback uses the existing installer: `python3 constellation.py install
--rollback RECEIPT`. Later native edits cause rollback to refuse replacement.

## Roles and readable engineering

| Canonical role | Responsibility |
| --- | --- |
| `ecosystem_coder` | Implement assigned behavior with readable data flow and explicit failure handling. |
| `ecosystem_reviewer` | Inspect correctness, contracts, maintainability and evidence without editing. |
| `ecosystem_security_reviewer` | Inspect trust boundaries, privacy, loss of work and publication scope. |
| `ecosystem_verifier` | Independently resolve a finding with evidence; neither author nor discoverer. |
| `ecosystem_researcher` | Investigate a bounded decision using primary sources and competing explanations. |
| `ecosystem_editor` | Write and revise coherent prose with explicit scope and justified claims. |
| `ecosystem_mathematician` | Develop arguments with ambient spaces, hypotheses and essential steps. |
| `ecosystem_counterexample` | Seek valid counterexamples and expose missing hypotheses. |

The generated profiles include repository instructions and constrain their native
tools. Review roles have reading/search capabilities, with no edit, shell or agent
delegation tool. This is a client capability choice, not an operating-system
sandbox. Model and effort are inherited rather than pinned by Constellation.

Human-readable code means names from the problem, focused functions, visible
ownership and a straightforward sequence of operations. Abstractions must solve
a present need. Types clarify boundaries; errors explain what failed; comments
explain decisions. Handle the supported domain and partial failures without
inventing frameworks or compatibility layers for imaginary callers.

Follow the [shared engineering rules](../instructions/AGENTS.md#engineering).
Preserve existing tests and start with static inspection and independent review.
Keep any test work focused on the requested behavior, a required project gate or
a concrete regression. Report which evidence establishes runtime behavior.

## Parallel work and independent review

Use the default native coordinator or an author role with delegation capability.
For suitable independent work, `/fleet` can dispatch custom agents concurrently.
The available capacity belongs to Copilot and the account; Constellation does not
install a scheduler or promise a fixed agent count.

1. Identify owners, existing behavior and an observable requirement. Open a
   `begin` contract with exact files and the native identities returned by the
   client. Register child event IDs in `actor_sessions` when names differ.
2. Run independent authors on exclusive files. Research and read-only examination
   may run beside implementation; each agent returns its scope and evidence.
3. Integrate the candidate and record only permitted checks. Run correctness and
   security reviews concurrently where both have a concrete purpose, against the
   same fingerprint. An author cannot approve their own work.
4. Resolve findings through a separate verifier. Later edits invalidate previous
   checks and approval. The coordinator records the resolution and closes the
   local task, or uses the existing Git gates for authorized publication.

Before a worker may edit, its real execution ID must be registered. A shared
`sessionId`, an agent profile name or a guessed ID cannot stand in for its
`agentId`. A worker can first receive a read-only reconnaissance assignment and
wait for registration before a writing assignment. Do not evade a scope denial
through shell writes. A review with no findings is bounded evidence, not a
guarantee that the result is perfect.

## Hook responsibilities

| Event | Constellation action |
| --- | --- |
| `sessionStart` | Supply the common workflow reminder and associated pending task IDs. |
| `subagentStart` | Remind the worker to wait for registered ownership and follow the shared engineering rules. |
| `preToolUse` | Translate recognized edits into the existing exact-path/actor guard and retain shell guard rules. |
| `agentStop` | Remind the coordinator about pending work once; keep the ledger open until properly closed. |
| `subagentStop` | Preserve the worker's response and prepend pending-review status for the coordinator. |

These commands use the common Python entry point and never launch models, run
tests, read transcript files or persist prompts, responses or tool arguments.
No-op logging hooks, telemetry exporters and automatic permission grants are not
installed. A child's handoff is allowed while the parent's review is pending.

The rest of the documented event surface is deliberately left to native behavior:

| Available event | Configuration decision |
| --- | --- |
| `postToolUse`, `postToolUseFailure` | Preserve tool results; the coordinator records curated evidence explicitly. |
| `permissionRequest` | Keep the client's permission decisions and user approval flow. |
| `userPromptSubmitted`, `userPromptTransformed` | Preserve the user's input without inspection, rewriting or retention. |
| `errorOccurred`, `notification` | Keep native error reporting and notifications without an extra logging service. |
| `preCompact`, `sessionEnd` | Recover from the existing curated ledger without reading or archiving conversations. |

The adapter handles documented camelCase envelopes and known tool argument
shapes. Unknown shapes on recognized writes are denied. Unknown tools and
arbitrary shell writes remain governed by native permissions and the separate
Git publication gate. Hook timeouts can fall through to native permissions;
hooks are cooperative controls, not isolation. General-purpose native subagents
can omit the start/stop events; use the named custom roles for this workflow.

## Surface boundaries and official sources

Reviewed 2026-11-16. The local public library contains the relevant official
GitHub topics, not the entirety of GitHub documentation. Its manifest records
source/final URLs, retrieval dates and hashes. Integrity verification establishes
local consistency, not perpetual freshness.

| Topic | Primary reference |
| --- | --- |
| Customization choices | [Customization comparison](https://docs.github.com/en/copilot/concepts/customizations/comparing-customizations) |
| Agent files and tool capabilities | [Creating CLI agents](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli), [configuration reference](https://docs.github.com/en/copilot/reference/custom-agents-configuration) |
| Native settings and instruction inheritance | [CLI reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference) |
| Personal and project instructions | [Instruction locations](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions) |
| Shared skill discovery | [CLI skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) |
| Hook payloads and decisions | [Hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference) |
| Native parallel delegation | [Fleet operation](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/speed-up-task-completion) |
| Additional discovery directories | [Discovery locations](https://docs.github.com/en/copilot/how-tos/copilot-sdk/features/customization-locations) |
| Plugins | [CLI plugin reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference) |

Repository discovery directories cannot escape their checkout. The personal
native locations therefore carry this local integration. Generated instructions
inline the common source, avoiding conflicting official descriptions of absolute
`@imports`. Reinstall after editing canonical instructions or roles.

GitHub cloud jobs cannot see this machine's paths or personal settings. No cloud
hook, Actions workflow, MCP credential or external service is enabled here. A
cloud deployment would need portable source and its own declared environment.
VS Code harnesses and the Copilot app have their own discovery/admission rules;
this local installation does not certify them. Use their current native
documentation before extending the installation to those surfaces.
