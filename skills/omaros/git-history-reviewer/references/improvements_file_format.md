# `commit-message-improvements.md` Format

A compact, plain-text digest of every proposed message improvement. Sister file to the main `git-history-review.txt`. Designed to be consumed quickly by a developer about to run a rewrite, or to be diffed against future runs.

## Header

The file opens with a small header block:

```
COMMIT MESSAGE IMPROVEMENTS
Repository:        <repo path or URL>
Branch:            <branch>
Generated on:      <YYYY-MM-DD HH:MM timezone>
Style applied:     <project_specific | imperative | conventional | plain>
Number of suggestions:  <N>
```

A blank line follows.

## One block per improvement

Each suggested improvement is one block, separated by a blank line. Blocks are ordered chronologically (oldest commit first) so the file can be read alongside `git log --reverse`.

```
--- <short-hash> ---
Original subject:    <verbatim original subject>
Suggested title:     <new subject>
Suggested body:
  <line 1>
  <line 2>
  ...
Affected files:
  - <path>
  - <path>
Rationale:           <short rationale>
Confidence:          <High | Medium | Low>
```

Use `—` (em dash) for `Suggested body:` when only the title is improved.

## Compact-table appendix

After the blocks, append a single pipe-separated table for at-a-glance scanning. Same data, no rationale:

```
| short-hash | original             | suggested                          | conf |
|------------|----------------------|------------------------------------|------|
| abc123d    | fix                  | Reject empty session tokens        | H    |
| def456a    | update auth          | Add CSRF token to login flow       | H    |
| 9f8e7d6    | wip                  | Sketch initial parser combinators  | M    |
```

Truncate long subjects with an ellipsis to keep the table aligned. The full text is already in the per-commit blocks above.

## Worked example

```
COMMIT MESSAGE IMPROVEMENTS
Repository:        ~/projects/example-app
Branch:            main
Generated on:      2026-04-27 15:42 Europe/Madrid
Style applied:     imperative
Number of suggestions:  3

--- abc123d ---
Original subject:    fix
Suggested title:     Reject empty session tokens before parsing
Suggested body:
  The session loader was passing empty strings to the JWT parser, which
  raised on the very first cold-start request before any cookie was set.
  An early return on falsy tokens removes the noisy 500s without changing
  the contract for legitimate clients.
Affected files:
  - src/auth/session.py
Rationale:           Original message conveys nothing; diff is a guard clause.
Confidence:          High

--- def456a ---
Original subject:    update auth
Suggested title:     Add CSRF token to login flow
Suggested body:      —
Affected files:
  - src/auth/login.py
  - templates/login.html
Rationale:           Title-only improvement; diff is small and self-explanatory once named.
Confidence:          High

--- 9f8e7d6 ---
Original subject:    wip
Suggested title:     Sketch initial parser combinators
Suggested body:      —
Affected files:
  - src/parser/combinators.py
Rationale:           File is added in this commit; "wip" gives no signal. The proposal preserves the exploratory nature ("Sketch").
Confidence:          Medium

| short-hash | original    | suggested                                 | conf |
|------------|-------------|-------------------------------------------|------|
| abc123d    | fix         | Reject empty session tokens before…       | H    |
| def456a    | update auth | Add CSRF token to login flow              | H    |
| 9f8e7d6    | wip         | Sketch initial parser combinators         | M    |
```

This is a *suggestion file*. Writing it never modifies the repository.
