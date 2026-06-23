# How to add a new repo to the constellation

End-to-end walkthrough. Times: ~5 minutes for an adjacent repo,
~15 minutes for a QuantOS lab.

## 0. Drop the repo on disk

`git clone` or `git init` under `~/GitHub/`. Make sure it actually
contains a `.git/` **directory** (the constellation only sees git repos).

> A linked **git worktree** (`.git` is a *file*, not a directory) is not a
> repo and must never be registered — see
> [`policies/worktree_lifecycle.md`](../policies/worktree_lifecycle.md).

## 1. Discover

```bash
python3 ~/GitHub/.claude/scripts/discover_repos.py
```

You should see the new repo listed under "not in registry (would
propose classification)".

## 2. Classify

Invoke the `perimeter-classify` skill — or, equivalently, run the
classifier logic by hand:

- Has `.importlinter` referencing `quant_core`? → `quantos-*` (tier
  comes from the contract).
- Imports `quant_core` from `Shared` anywhere in `packages/`? → also
  `quantos-*` (tier inferred from imports).
- TypeScript + Vite + React? → `typescript-vite` stack, perimeter
  depends on whether it integrates with QuantOS over HTTP.
- Plain HTML/CSS/JS + Playwright? → `vanilla-web`, adjacent.
- Otherwise → `adjacent`, default.

When in doubt: `adjacent`. Promote later through a vault-side ADR.

## 3. Register

Update `~/GitHub/.claude/registry/repos.yaml`:

1. Add the new entry under `repos:`.
2. Add the name to the appropriate perimeter list under `perimeters:`.
3. Update `~/GitHub/.claude/REPOS.md` (or let
   `constellation-cartographer` re-render it).

## 4. Bootstrap (optional)

To install the standard layout in the new repo:

```bash
# dry-run first
bash ~/GitHub/.claude/scripts/bootstrap_repo.sh ~/GitHub/<NewRepo> --variant adjacent

# then apply
bash ~/GitHub/.claude/scripts/bootstrap_repo.sh ~/GitHub/<NewRepo> --variant adjacent --apply
```

For QuantOS labs, use `--variant quantos`. The script will:

- Create `.claude/{agents,commands,skills,hooks,registry}` if missing.
- Copy `CLAUDE.md.template` to `CLAUDE.md` (only if absent).
- Seed `.claude/registry/peers.yaml` from the master registry.
- (quantos variant) drop `.importlinter` and CI workflow templates.

Then wire the shared surfaces:

```bash
bash ~/GitHub/.claude/templates/claude_subagent_link.sh ~/GitHub/<NewRepo>
```

## 5. Edit `CLAUDE.md`

Open `~/GitHub/<NewRepo>/CLAUDE.md` and replace placeholders:

- `<REPO_NAME>` → the repo name.
- Perimeter + tier values.
- Vault home (if applicable).
- Stack profile.
- Anything lab-specific.

## 6. Refresh peers everywhere

```bash
python3 ~/GitHub/.claude/hooks/peer_sync.py --apply
```

This rewrites `.claude/registry/peers.yaml.snapshot` in every
constellation-aware lab so they see the new sibling.

## 7. (QuantOS only) Open a vault-side vision note

Create:

```
~/OmarOS/05_Projects/QuantOS/Labs/<NewLab>/Vision/00_Mission.md
```

with a one-paragraph mission. This is what other agents will read when
they encounter the lab in the registry. Linking back to the lab's
`CLAUDE.md` is the canonical pattern.

## 8. Verify

```bash
~/GitHub/.claude/scripts/discover_repos.py --state
```

The new repo should appear and the registry should be reported as
in-sync.

## What you do NOT do

- Do **not** commit changes inside multiple repos in the same session.
  The hub's `~/GitHub/.claude/` updates and the repo's own initial commit
  are two different operations.
- Do **not** auto-promote into `quantos-*`. Without `.importlinter`
  evidence or an explicit CLAUDE.md tier declaration, the classifier
  must default to `adjacent`.
- Do **not** force a tier. The tier is a consequence of the import
  contract, not a decision you make in the registry.
