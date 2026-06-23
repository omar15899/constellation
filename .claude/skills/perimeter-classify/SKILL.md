---
name: perimeter-classify
description: Given an arbitrary folder path (typically a freshly cloned repo), determine which perimeter it belongs to under the constellation taxonomy and propose a repos.yaml row. Trigger when the user says "classify this repo", "what perimeter does X belong to", "where does this fit in QuantOS", "clasifica este repo".
---

# perimeter-classify

Wraps `agents/repo-classifier.md` as a one-shot skill.

## When to fire

- "Classify <path>."
- "What perimeter is this?"
- After `repo-discovery` flags a new directory.

## Operating procedure

1. Verify the path exists and contains a `.git/` folder.
2. Dispatch `repo-classifier`.
3. Present the proposal to the user, marking inferred fields.
4. On user confirmation, hand off to `constellation-cartographer` to
   persist the entry to `repos.yaml`.

## Output

Short:

```
Path: /Users/omarkhalil/GitHub/NewRepo
Proposed perimeter: adjacent
Stack: python-light
Status: stub
Vault link: none
Evidence: pyproject.toml minimal deps, no QuantOS imports, no CLAUDE.md.
Inferred fields: [perimeter, stack, status].
Confirm? (y/n)
```

## Invariants

- Adjacent is the default when ambiguous. Never auto-promote to
  `quantos-*` without explicit signals (import-linter contract or
  CLAUDE.md tier declaration).
- Never modifies the target repo.
- Idempotent.
