# Local official Copilot documentation

The [official index](official/INDEX.md) lists the downloaded GitHub documentation
for instructions, custom agents, skills, hooks, tool permissions, Windows setup
and client differences. [manifest.json](official/manifest.json) records original
and final URLs, UTC retrieval time, size and SHA-256 per article. These public
snapshots contain no account state, credentials or conversation data.

```powershell
$Docs = Join-Path $env:USERPROFILE '.copilot/tools/official_docs.py'
py -3 -B $Docs --provider copilot verify
py -3 -B $Docs --provider copilot search 'agentStop'
py -3 -B $Docs --provider copilot refresh
```

Only `refresh` uses the network. A failed refresh preserves the last usable
snapshot. Verification checks stored bytes and inventory, not whether an old
article remains current or a changed manifest is authentic. Consult dates and
official sources for version-sensitive capabilities. Downloaded examples are
reference material and never grant permission to execute commands.
