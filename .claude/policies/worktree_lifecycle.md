# Policy — Git worktree lifecycle

**Status:** active · **Risk class:** low · **Scope:** constellation plane

## Rule

A directory under `~/GitHub/` that is a **linked git worktree** is *never*
registered in `registry/repos.yaml`, never assigned a perimeter, and never
counted in the constellation repo total. It is a transient checkout of a
branch belonging to an already-registered repo, not a repo of its own.

## How to identify a worktree

A normal repo has a `.git` **directory**. A linked worktree has a `.git`
**file** whose contents point back to the parent repo's
`.git/worktrees/<name>`:

```bash
[ -f ~/GitHub/<dir>/.git ] && echo "worktree" || echo "repo or non-repo"
git -C ~/GitHub/<parent> worktree list   # authoritative listing
```

As of 2026-06-15 the live worktrees are:

| Worktree dir              | Parent repo  | Branch                            |
| ------------------------- | ------------ | --------------------------------- |
| `NewsLab-osint-phase1`    | NewsLab      | `osint-phase1`                    |
| `ResearchLab-volsurface`  | ResearchLab  | `volatility-surface-lab`          |
| `Sweeplab-divs-discretos` | Sweeplab     | `investigation/discrete-dividends`|

The naming convention is `<ParentRepo>-<short-topic>`. This is a convention,
not a guarantee — always confirm with `git worktree list`, not the name.

## Lifecycle

1. **Create** — `git -C <parent> worktree add ../<Parent>-<topic> <branch>`.
   The worktree shares the parent's object store and remote; commits made in
   it land on `<branch>` of the parent repo.
2. **Work** — investigation / feature branches that benefit from living next
   to `main` (e.g. running both checkouts side by side). Dirty state here is
   expected and is the user's, not constellation drift.
3. **Retire** — when the branch merges or is abandoned:
   `git -C <parent> worktree remove <path>` (and prune the branch). The
   directory disappears from `~/GitHub/`; no registry edit is required
   because it was never registered.

## How tooling must treat worktrees

- `discover_repos.py` flags worktrees separately (`is_worktree`) and excludes
  them from the added/removed drift diff. A worktree appearing or disappearing
  is **not** drift.
- `constellation-cartographer` must not propose a classification for a
  worktree, and must not register it.
- `peer_sync.py` writes `peers.yaml.snapshot` into a worktree only incidentally
  (the worktree shares the parent's `.claude/`); that snapshot is gitignored
  like any other and is not tracked.
- `repo-status` may *report* worktree state for
  visibility but must label it as a worktree, never as an unregistered repo.

## Why this is a policy and not just a convention

Without it, every `git worktree add` makes the constellation look like it
grew a new repo, and `discover_repos.py` reports phantom drift. Anchoring the
rule here keeps the registry == repos invariant clean: **the registry tracks
repositories, the filesystem may also hold worktrees of them.**

See also: [`docs/how_to_add_a_repo.md`](../docs/how_to_add_a_repo.md),
[`registry/repos.yaml`](../registry/repos.yaml).
