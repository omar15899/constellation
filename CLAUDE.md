# CLAUDE.md — constellation

This repository owns the shared tools for independent repositories under
`~/GitHub/`. Claude Code starts with the [kernel](.claude/CLAUDE.md) and loads
the contracts relevant to its task. [README.md](README.md) describes the hub.

Codex uses its independent [AGENTS.md](AGENTS.md) and native `.codex/` profile.
The `.codex/profile.json` marker excludes this repository from Claude-to-Codex
projection. Claude's system remains in `.claude/`; the generator continues to
support other repositories that have not selected a native profile.
