---
name: repo-route
description: Inspect the routing decision for a free-form request without executing it. Returns class, targets, entry point, and justification.
---

# /repo-route

Read-only routing inspector.

## Usage

```
/repo-route <free-form request>
```

## Pipeline

1. Invoke `cross-repo-router` (agent).
2. Print the routing envelope:
   - class
   - targets
   - entry point
   - justification
   - suggested follow-up command

## Use cases

- "Where would this work belong?" before committing to execute.
- Verifying that a vault-class request would be escalated to OmarOS.
- Debugging routing decisions.

## Aliases

`/route`, `/where`.
