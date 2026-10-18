# Constellation AI hub

This directory owns the shared control plane for independent repositories under
`~/GitHub/`. QuantOS labs share architecture; adjacent projects retain their own
contracts. Read the [kernel](CLAUDE.md), then only the context needed for the task.

| Source | Responsibility |
| --- | --- |
| registry/repos.yaml and REPOS.md | Canonical repository metadata and human index |
| contracts/routing.md | Scope selection in the current agent |
| agents/ | Metadata, dependency audit and multi-repository coordination |
| skills/ and commands/ | Distinct procedures selected by their descriptions |
| policies/ and contracts/ | Architecture, authority, privacy and evidence rules |
| hooks/, scripts/ and tests/ | Executable checks and verification |
| templates/ | Bootstrap drafts and compatibility projection sources |
| docs/ | Architecture, operation and audit evidence |

Use `repo-status` for git state or a brief, `find-in-repos` to locate code,
`repo-discovery` for classification and index changes, and `repo-bootstrap` for
requested setup. `cross-repo-refactor` coordinates changes to multiple consumers;
`tier-check` audits dependency boundaries. The [command catalog](commands/README.md)
covers verification, research, Codex projection and scoped commits.

`.claude/` owns Claude Code's implementation and operating contract. The hub
and its own child repositories use independent
[native Codex profiles](../.codex/README.md); `.codex/profile.json` prevents
projection from replacing them. [codex_sync.py](scripts/codex_sync.py) supports
repositories that still retain the Claude-to-Codex projection.
[Codex projection](docs/codex_parity.md) documents that compatibility surface
and its native hook activation limits. No global trust or neighboring
projection update is implied.

Each target's local AGENTS.md and CLAUDE.md govern its implementation. The hub
has its own Git history and no QuantOS tier. OmarOS is read-only from this plane;
vault writing follows its own workflow. No background processes or automatic
session-start registry rewrites are part of this design.
