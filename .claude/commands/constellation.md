---
name: constellation
description: One-page brief of the current state of ~/GitHub/ — counts, QuantOS tier table, adjacent state, drift summary. The canonical session-start command.
---

# /constellation

The fastest possible view onto "what's the state of GitHub?".

## Pipeline

1. Invoke the `constellation-brief` skill.
2. The skill composes `repo-discovery`, `multi-repo-status`, and
   `perimeter-keeper` (summary mode).
3. Renders the brief described in
   [`skills/constellation-brief/SKILL.md`](../skills/constellation-brief/SKILL.md).

## When to use

- New session at `~/GitHub/`.
- After cloning a new repo.
- Before opening a multi-repo refactor.
- Whenever Omar wants a state snapshot.

## Aliases

`/brief-repos`, `/state`.
