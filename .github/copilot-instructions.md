# Constellation repository instructions

Read [the shared instructions](../instructions/AGENTS.md), [README](../README.md)
and [the project profile](../profiles/constellation.md) before changing source.
For local Copilot CLI setup, read [the native guide](../profiles/copilot.md).

Keep the eight role definitions in `agents/*.toml` as the single source. Generate
client adapters through `constellation.py install`; do not maintain a second role
catalog or scheduler. Reuse native delegation, the common task ledger and the
existing reversible installer. Make the smallest complete change and keep contracts
and control flow easy to read.

Follow the shared engineering rules for focused testing. Preserve existing tests,
start with static inspection and independent review, and record the limits of the
evidence.

Private runtime state, conversations, client credentials and personal settings
stay outside Git. Preserve unrelated edits and indexes. A local installation
does not configure a cloud job: cloud work needs its own reachable source,
declared owner and environment before running local-only commands.
