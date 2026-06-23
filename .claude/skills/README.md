# `~/GitHub/.claude/skills/`

Cross-repo skills. Each is a folder with a `SKILL.md` that declares
when to fire and how to operate.

| Skill                 | What it does                                            |
| --------------------- | ------------------------------------------------------- |
| `repo-discovery`      | Scan `~/GitHub/` and refresh the registry.              |
| `multi-repo-status`   | Aggregate `git status` across the constellation.        |
| `cross-repo-grep`     | Search across every repo with filters.                  |
| `repo-bootstrap`      | Bring an under-equipped repo up to the standard layout. |
| `tier-discipline`     | Verify the import graph respects the tier hierarchy.    |
| `cross-repo-refactor` | Propagate a typed change across multiple repos.         |
| `perimeter-classify`  | Classify an unknown folder into a perimeter.            |
| `constellation-brief` | One-page state of the whole constellation.              |

## Composition

Skills compose freely. A typical session looks like:

```
/constellation        →  constellation-brief
   (sees drift)
/repo-status          →  multi-repo-status
   (sees a dirty repo)
/find-in-repos X      →  cross-repo-grep
   (locates the symbol)
"refactor rename X"   →  cross-repo-refactor
                          →  multi-repo-orchestrator
                            →  tier-discipline
```

## Above and below

- **Above**: vault-side OmarOS skills handle vision/decision/reflection
  writes.
- **Below**: per-repo skills under `<repo>/.claude/skills/` handle
  lab-internal work once the cross-repo skill descends into a single
  repo.
