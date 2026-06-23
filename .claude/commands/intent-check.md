---
name: intent-check
description: Reconstruct the user's request — explicit vs inferred, planning vs execution, ambiguities resolvable from the repo vs ambiguities needing a caveat. Prevents Claude from silently drifting off the user's plan.
---

# /intent-check <task>

Preserve the user's expertise and stop Claude from drifting. Extract:

- explicit user requirements;
- inferred intent;
- non-goals;
- planning decisions reserved to the user;
- execution decisions delegated to Claude;
- ambiguity resolvable from repo inspection;
- ambiguity that requires asking or a caveat.

**Output:**

| user requirement | source / context | interpreted action | evidence needed | status |
|---|---|---|---|---|

Rule (from [`contracts/expert_agent_contract.md`](../contracts/expert_agent_contract.md)):
proceed without asking when the ambiguity is repo-resolvable or a conservative
assumption that does not change success; ask or caveat when it would change the
definition of success, the universe, or the risk surface.
