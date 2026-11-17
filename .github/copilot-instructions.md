# Constellation repository instructions

Read [the shared instructions](../instructions/AGENTS.md), [README](../README.md)
and [the project profile](../profiles/constellation.md) before changing source.
For local Copilot CLI setup, read [the native guide](../profiles/copilot.md).

Keep the eight role definitions in `agents/*.toml` as the single source. Generate
client adapters through `constellation.py install`; do not maintain a second role
catalog or scheduler. Reuse native delegation, the common task ledger and the
existing reversible installer. Write readable, direct code with explicit contracts.

Do not create, change or run tests unless Omar explicitly requests them. Preserve
existing tests. Use static inspection and independent review, recording their limits.
Do not turn missing runtime evidence into a claim that hooks ran successfully.

Private runtime state, conversations, client credentials and personal settings
stay outside Git. Preserve unrelated edits and indexes. A local installation
does not configure a cloud job: cloud work needs its own reachable source,
declared owner and environment before running local-only commands.
