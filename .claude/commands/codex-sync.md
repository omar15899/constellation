---
name: codex-sync
description: Project the canonical .claude sources onto the requested Codex surface, check drift and verify discovery without changing global trust or unrelated repositories.
argument-hint: "[--check] [--repo <path>] [--all]"
---

# /codex-sync

Keep one implementation shared by both agents. `.claude/` is canonical;
managed `.codex/` files and `AGENTS.md` are generated. The
[parity guide](../docs/codex_parity.md) defines the mapping and its limits.

Default to the requested repository, or the current repository. Use `--all`
only when the user authorizes a constellation-wide projection.

1. Run `python3 .claude/scripts/codex_sync.py --repo . --check` from the hub
   (substitute the requested target for `.`). Exit 1 with DRIFT indicates
   changed outputs; parse errors need repair before applying.
2. For an authorized update, run the same command without `--check`.
   The manifest checks ownership before writing and retires only unchanged
   managed outputs. Preserve modified/unknown files and resolve conflicts from
   their actual sources; do not force adoption or delete local directories.
   Duplicate generated names fail preflight; a command/skill collision may produce
   a warned `cmd-` alias. Review such duplication instead of adding a second entry
   unnecessarily. Legacy migration requires proof
   of prior ownership as described in the parity guide. A check-only request never writes.
3. Check again for zero drift. For generator/hook changes, run relevant
   standalone tests and verify a second application makes no writes.
4. Use `--repo <target> --verify` to check discovery with the installed Codex.
   Distinguish discovered skills from parsed agent configuration. Report failures;
   never print or publish raw prompt input as an artifact.

Stop when the requested projection and relevant checks succeed. Do not make
commits, push, register global trust or update other repositories unless those
operations are authorized. `--trust` writes user configuration and is not a
routine step.

New or changed hooks may require native review in the target repository's
`/hooks` interface. Explain this when relevant. Neither direct hook tests nor
discovery proves hooks ran in the current session. Do not edit trust hashes or
use bypass settings. `ruflo` remains upstream-owned and outside hub governance.
