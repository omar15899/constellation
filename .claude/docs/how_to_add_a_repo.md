# Add a repository

1. Identify the actual Git root and read its contracts. A linked worktree is
   another checkout, not a new repository; a `.git` file alone does not settle
   identity. Run `python3 .claude/scripts/discover_repos.py --json` from the hub
   to inspect filesystem drift.
2. Use `repo-discovery` and the cartographer to propose perimeter, tier, role,
   coarse language stack and status from evidence. Tooling profiles in stacks.yaml
   are separate from repos.yaml stack values. Neither `.importlinter` presence
   nor a `quant_core` import alone establishes architectural ownership or tier.
3. If registration is requested, update the repository row, perimeter membership
   and human index together. Preserve unrelated work; run validate_repos.py and
   inspect its findings. Its schema checks are partial.
4. If scaffolding is requested, preview and apply repo-bootstrap for the correct
   adjacent/QuantOS variant. It preserves existing files and creates missing
   templates plus peers.yaml.snapshot. Resolve placeholders and run actual repo
   checks before claiming integration complete.
5. Wire shared resources and generate the target Codex surface only when requested
   or necessary for the authorized setup. Peer updates across other roots need
   that broader scope; do not automatically rewrite every repository.
6. Vault material is handled through OmarOS's workflow. The hub cannot write it.
   Commits/pushes follow established authority, one git root and logical scope
   at a time; multiple repositories can participate in the same authorized task.

See [routing](../contracts/routing.md), [bootstrap](../skills/repo-bootstrap/SKILL.md)
and [Codex parity](codex_parity.md) for detailed procedures.
