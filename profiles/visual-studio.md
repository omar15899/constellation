# GitHub Copilot in Microsoft Visual Studio

This target configures Copilot Chat in Microsoft Visual Studio on Windows. It
generates custom agents and instructions from Constellation and installs skills
with their accompanying resources. Visual Studio controls tool availability,
model selection, authentication, trust and permissions.

## Install for one repository

You need Python 3.11 or newer, Git, and a Visual Studio release with Copilot
enabled. Microsoft documents repository custom agents in Visual Studio 2026
18.4 and later and Agent Skills in 18.5 and later. [Custom agents][agents] ·
[Agent Skills][skills]

In PowerShell, from the Constellation checkout, set `$repo` to the exact local
Git root of the solution. Run the first command and inspect the preview before
applying it.

```powershell
$repo = 'C:\Projects\Example'
py -3 .\constellation.py install --client visual-studio --project-root $repo
py -3 .\constellation.py install --client visual-studio --project-root $repo --apply
```

Copilot discovers agents under `.github/agents/`, skills under
`.github/skills/` and instructions in `.github/copilot-instructions.md`. These
paths are part of the worktree. The repository owner determines which changes
may be committed. The [local project mapping](../README.md#projects-on-another-machine)
controls which project-specific skills are available for a registered owner.
If the repository is on another drive, add `--state-dir` to both commands
and point it to a new state path on that drive so the installer can set its
permissions. Use the same project mapping across state directories through
`CONSTELLATION_PROJECTS_FILE`.

## Install for your user profile

Visual Studio 18.5 and later can discover user agents. Read the custom agents
directory in Visual Studio settings. The classic chat experience defaults to
`%USERPROFILE%\.github\agents`. The new Copilot Chat experience defaults to
`%USERPROFILE%\.copilot\agents` and keeps an explicitly configured directory.
[Default folder changes][release-notes]

Pass the actual directory to the installer. This example uses the classic
default. If you use Copilot CLI and Visual Studio, their generated roles have
different tool definitions. Set a dedicated user agents directory in Visual
Studio or use repository-scoped installation to avoid two clients managing the
same files.

```powershell
$agents = Join-Path $env:USERPROFILE '.github\agents'
py -3 .\constellation.py install --client visual-studio --visual-studio-agent-dir $agents
py -3 .\constellation.py install --client visual-studio --visual-studio-agent-dir $agents --apply
```

The personal installation uses `%USERPROFILE%\copilot-instructions.md` and
`%USERPROFILE%\.agents\skills\` for the general skills. Check Copilot Chat's
References list for loaded instructions. [Custom instructions][instructions]

## Confirm discovery and reverse a change

Open a new Copilot Chat session on the target machine. Confirm the Constellation
roles in the agent picker, the installed skills under Tools, and the instructions
under References. Check the selected role's tool panel, since Visual Studio
versions and configurations expose different capabilities.

This target installs the IDE's agents, skills and instructions. Constellation's
GitHub Copilot CLI lifecycle hooks belong to the CLI integration. The IDE's
ability to delegate to custom agents depends on its version and chat experience.
Use the common terminal workflow for Constellation's task and review records.

The installer reports paths it preserved as conflicts. Updates replace the
generated role and skill files it can verify as unchanged since installation.
Use the full receipt path from the successful or interrupted installation to
reverse that installation:

```powershell
py -3 .\constellation.py install --rollback 'C:\path\to\receipt.json'
```

[agents]: https://learn.microsoft.com/en-us/visualstudio/ide/copilot-specialized-agents
[skills]: https://learn.microsoft.com/en-us/visualstudio/ide/copilot-agent-skills
[instructions]: https://learn.microsoft.com/en-us/visualstudio/ide/copilot-chat-context
[release-notes]: https://learn.microsoft.com/en-us/visualstudio/releases/2026/release-notes
