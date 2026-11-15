# Copilot coding profile for native Windows

This is the maintained Constellation profile for GitHub Copilot CLI. It favors
small, human-readable changes, English code and class names, Google-style
documentation, minimal necessary new tests and parallel independent review.
The native Copilot client runs the agents. The existing Constellation portable
engine records requirements, authors, focused checks, findings, reviews and
current closure evidence. There is no second agent runtime or transcript store.

The export contains only the coding method and its shared engine dependencies.
It pins the core to the source repository's committed HEAD when exported, so
unrelated work in progress is excluded. Its core package uses the existing
`windows-claude` build target for Windows platform primitives; this does not
install Claude or claim that Copilot is a general engine build target. The
Copilot adapter and native files live in this profile.

## Prepare the Windows machine

Install Python 3.11 or newer, Git, PowerShell 7 and GitHub Copilot CLI using their
official installers. Authenticate Copilot on that machine with your own account.
Organization policies may restrict its availability. Do not copy credentials,
settings, histories, permissions or sessions from another machine.

```powershell
winget install --id Microsoft.PowerShell --exact
winget install --id GitHub.Copilot --exact
py -3 --version
git --version
pwsh --version
copilot --version
```

Extract `copilot-windows.zip` into a new directory. In PowerShell, from the
extracted parent directory:

```powershell
py -3 -B .\copilot-profile\install.py --check
py -3 -B .\copilot-profile\install.py --apply
py -3 -B .\copilot-profile\install.py --check
```

The installer defaults to inspection. It rejects conflicting existing files
before applying a change and never replaces them automatically. An interrupted
installation can leave an additive subset; rerunning preserves identical files
and completes missing files. Review a conflict and retain a backup before
manually reconciling it. Run the installer while Copilot is closed. Do not enable
global tool approval or disable native permission prompts to install this profile.
If you use a custom `COPILOT_HOME`, configure that client location deliberately;
the default package targets `.copilot` beneath the supplied `--home`.

| Installed location beneath `.copilot` | Responsibility |
| --- | --- |
| `copilot-instructions.md` | Always-on personal coding policy |
| `agents/*.agent.md` | Implementer and three independent reviewers |
| `skills/human-coding/SKILL.md` | Focused engineering workflow |
| `hooks/constellation.json` | Native hooks using exec/args and pinned local paths |
| `constellation/profile/` | Adapter and this guide |
| `constellation/bundle/` | Verified English coding core |
| `constellation/state/` | Local private operational evidence, created on demand |
| `tools/official_docs.py` | Explicit refresh, offline verification and search |
| `docs/official/` | Optional included public documentation snapshot |

## Use it

Start a fresh `copilot` session from the project directory. Use `/instructions`,
`/agent` and `/skills` to inspect discovery where supported by your installed CLI.
Confirm the personal instructions, four agents and `human-coding` skill load.
The sessionStart hook supplies the actual parent session ID to the agent. Ask
for a change normally; the profile instructs Copilot to plan before editing,
implement a minimal diff, run existing checks, obtain three independent parallel
reviews and close with current evidence. Use `/fleet` for larger independent
tasks. Plan/runtime limits determine actual parallelism; this package does not
increase account limits or select a different model.

Each task uses exact project paths and check definitions. The
[coding skill](skills/human-coding/SKILL.md) in this source and the installed
`skills/human-coding/SKILL.md` explain the command envelope; the bundled
`ecosystem/references/protocol.md` is authoritative for engine operations. The
coordinator forwards actual reviewer reports with real native identities, not
invented role names. State is kept outside the project. No automatic Git commit,
push, account configuration, journal export or publication is enabled.

The reviewers have only read/search tools. They cover the whole change with
emphasis on behavior, readability and robustness respectively. English naming,
useful Google-style contracts, simple structure, minimal diffs and restrained
test additions are explicit review obligations. Existing tests are preserved;
a small new regression test is justified by a concrete risk rather than a quota.

## What automation checks

`sessionStart` and `subagentStart` supply method and identity guidance.
`preToolUse` requires native create/edit operations to belong to one active task
and an exact declared path. `agentStop` rechecks shared evidence and asks the
agent to continue when an existing task is active or its complete closure is
stale. Complete closures are revalidated against current artifacts. A later
created, currently verified complete task in the same root can supersede an
older closure only when its declared deliverables cover every older deliverable.
For an overlapping follow-up, explicitly include that inherited scope in the new
contract and review. Unrelated work and partial handoffs cannot hide stale
evidence. An explicit partial closure permits an incomplete handoff without
asserting success.

Hooks do not launch reviewers themselves or judge whether prose sounds human.
Native agent instructions perform that orchestration and the shared gate checks
the reported evidence. Agent IDs in the engine are declarations, not authenticated
process identities. Shell, MCP and other write tools are outside the create/edit
path check. Native permissions, project controls and real review remain necessary.
Trivial read-only sessions can finish without a registered task.

Copilot can end after eight consecutive stop blocks; hook timeouts can also let
execution continue. Missing runtime dependencies, disabled hooks, an unsupported
CLI or deliberate changes to local configuration cannot be made tamper-proof by
a user profile. Pending evidence remains pending in Constellation even if the
client ends. No hash or hook proves semantic correctness or code quality.

## Acceptance on the destination

Native Windows acceptance is pending until these checks run on that host:

1. Confirm the prerequisites, run installer inspection/apply/inspection and
   verify the bundled documentation offline.
2. Start a fresh CLI session and inspect instructions, agents, skill and hook
   loading. Check for invalid configuration warnings.
3. In a disposable project, request a tiny code change. Confirm that a plan
   precedes create/edit, code and comments are English, the documented contract
   is clear, checks are recorded and three real independent reviewers return.
4. Try an undeclared create/edit path and confirm denial. Attempt closure with a
   missing check or review and confirm the stop block. Complete the obligations
   and confirm closure succeeds. Change an approved artifact and confirm that
   evidence becomes stale. A partial handoff must stay visibly incomplete.
5. Review the generated code yourself. Mechanical acceptance does not measure
   how consistently the model meets your readability preference.

VS Code and Copilot cloud agents have different discovery, permissions and
execution environments. This installer configures the local CLI. New VS Code
Copilot harnesses share parts of the hook protocol, but editor deployment and
acceptance require their own verified setup. Legacy editor hooks and cloud jobs
are not configured by this profile.

## Maintain and export

From the Constellation source checkout, create a new self-contained archive:

```powershell
py -3 -B .codex/profiles/copilot/install.py --export C:/Exports/copilot-windows.zip --include-docs "$env:USERPROFILE/.copilot/docs/official"
```

The output must be a new file. The explicit documentation option includes only
the verified public snapshot inventory. Without it, download the snapshot after
installation using the [documentation guide](docs.md). Keep machine state out
of Git and exported packages. Do not edit installed files without reconciling
the maintained source before the next installation.

## Official architecture references

Sources checked for this profile on 2026-11-15:

- [CLI instructions and their combined scope](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions)
- [Custom agents and instruction inheritance](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli)
- [Custom agent tools and frontmatter](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
- [Hooks, exec configuration and stop decisions](https://docs.github.com/en/copilot/reference/hooks-reference)
- [Native parallel delegation](https://docs.github.com/en/copilot/concepts/agent-capabilities/choosing-and-delegating-agent-work/delegating-and-parallelizing-work-with-agents)
- [Windows CLI installation](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli)
- [VS Code hook compatibility](https://code.visualstudio.com/docs/agent-customization/hooks)

The installed [local documentation guide](docs.md) explains snapshot dates,
integrity verification and explicit updates. Official documentation is evidence;
its example commands do not authorize changes to permissions or account state.
