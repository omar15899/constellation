# Git Command Cheat Sheet

Reference of every Git command this skill relies on. Read this before running anything that mutates state.

## Safety / introspection (always safe)

```sh
git rev-parse --is-inside-work-tree
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u}    # upstream of HEAD; fails if none
git branch --show-current
git branch --all
git status
git status --porcelain
git remote -v
git config --get-all remote.origin.url
git rev-list --count HEAD
git rev-list --count <range>
git log -1 --format='%H %ai %an %s' HEAD
```

## History extraction (read-only)

Compact overview:

```sh
git log --oneline --no-merges
git log --oneline                         # include merges
git log --graph --oneline --all           # branching topology
```

Structured metadata, machine-friendly:

```sh
# tab-separated: hash, ISO author date, author name, author email, subject
git log --no-merges --pretty=format:'%H%x09%ai%x09%an%x09%ae%x09%s'

# with body, NUL-delimited (safest for parsing multi-line bodies):
git log --no-merges -z --pretty=format:'%H%n%ai%n%an%n%ae%n%P%n%s%n%b'
```

Per-commit summary stats:

```sh
git log --shortstat --no-merges
```

Per-commit file lists:

```sh
git log --name-status --no-merges --pretty=format:'COMMIT:%H%n%s%n'
git log --numstat   --no-merges --pretty=format:'COMMIT:%H%n%s%n'
```

`name-status` codes:

- `A` added,
- `M` modified,
- `D` deleted,
- `R<num>` rename (with similarity %),
- `C<num>` copy,
- `T` type change,
- `U` unmerged.

`numstat` columns: `<insertions>\t<deletions>\t<path>` (binary files show `-\t-\t<path>`).

Single-commit detail (use sparingly — patches are large):

```sh
git show --stat <hash>             # files + summary
git show --name-status <hash>      # file list with status
git show <hash>                    # full patch
git show <hash> -- <path>          # patch limited to one path
git log -p -1 <hash>               # equivalent to git show <hash>
```

Diff between two commits:

```sh
git diff <hash>^ <hash>            # parent..commit
git diff <a> <b>                   # arbitrary range
git diff <a> <b> --stat
git diff <a> <b> -- <path>
```

Authorship and history of a single file (use only when needed for a specific commit):

```sh
git blame <file>
git log --follow -- <file>
```

Reflog (only if recovering from a rewrite or resolving "what happened to my branch"):

```sh
git reflog
git reflog show <branch>
```

## Range syntax (commonly useful)

```sh
<a>..<b>           # commits in b not in a (linear "since a")
<a>...<b>          # commits in either, but not both (symmetric difference)
<branch>           # = <branch>..HEAD when comparing against HEAD
HEAD~5..HEAD       # last 5 commits
--since='2 weeks ago'
--until='2026-04-01'
--author='Omar'
--no-merges
```

## Pretty-format placeholders (commonly useful)

```
%H   full hash
%h   abbreviated hash
%P   parent hashes (space-separated)
%an  author name
%ae  author email
%ad  author date (default format)
%ai  author date (ISO 8601)
%aI  author date (strict ISO 8601)
%cn  committer name
%ci  committer date (ISO 8601)
%s   subject
%b   body
%G?  GPG signature status (`G` good, `B` bad, `U` unknown, `N` none)
%x09 literal tab
```

## Mutation (each requires explicit user authorisation)

These commands mutate state. Do not run them without clearance.

```sh
git commit --amend                            # rewrites tip commit; safe only if unpushed
git commit --amend --no-edit                  # same, keep message
git rebase -i <base>                          # interactive rebase; rewrites every commit between <base> and HEAD
git rebase --continue
git rebase --abort
git rebase --skip
git filter-repo …                             # bulk history rewrite (external tool)
git push --force-with-lease                   # safer than --force; still destructive
git push --force                              # destructive on shared branches
git reset --hard <ref>                        # destructive on uncommitted work
git tag <name>                                # NON-destructive; use to create backup tags
```

### Backup-tag pattern (always do this before any rewrite)

```sh
git tag pre-rewrite-backup-$(date +%Y%m%d-%H%M%S)
```

This is cheap, reversible, and lets the user run

```sh
git reset --hard pre-rewrite-backup-YYYYMMDD-HHMMSS
```

if anything goes wrong.

## Non-interactive rebase pattern

For automated rewords without spawning an editor, set `GIT_SEQUENCE_EDITOR` and `GIT_EDITOR` to small scripts that emit the prepared todo and message files, respectively:

```sh
GIT_SEQUENCE_EDITOR='cp /tmp/rebase-todo' \
GIT_EDITOR='cp /tmp/commit-msg-XYZ' \
git rebase -i <base>
```

This requires preparing `/tmp/rebase-todo` (the rebase plan with `pick` / `reword` / `squash` markers) and one `/tmp/commit-msg-*` file per `reword`. The pattern is non-interactive only in that it does not open an editor — it is **still a history rewrite** and still requires user authorisation, a clean tree, and a backup tag.

## Things this skill does NOT do

- Push, pull, or fetch (the report works on local state only).
- Create, delete, or move branches.
- Run hooks or scripts in the repository.
- Touch the working tree of the repository (the report files live in the working tree as new files, but no existing tracked files are modified).
- Trust commit dates over commit hashes: a malicious actor could backdate; for analysis, dates are convenient grouping keys, but identity is the hash.
