---
name: verify-loop
description: Run a task through bounded Plan → Execute → Verify → Refute → Repair loops with an evidence table. The expert-directed verification loop. (Named verify-loop because /loop is the recurring scheduler.)
---

# /verify-loop <task>

Run the requested task through bounded verification loops. **The user owns
planning; Claude owns execution** (see
[`contracts/expert_agent_contract.md`](../contracts/expert_agent_contract.md)).

> Naming: `/loop` is reserved for the recurring-scheduler skill. This command
> is the verification loop. Alias intent: `/loop-task`.

Default maximum loops: **3**.

Each loop must include:

1. **Intent reconstruction** — restate the request; separate explicit vs
   inferred; mark which decisions are the user's (planning) and which are
   Claude's (execution).
2. **Definition of done** — concrete, falsifiable.
3. **Minimal execution step** — smallest change that advances the goal.
4. **Cheap verification** — run the cheapest check that could fail.
5. **Evidence table update.**
6. **Refutation pass** — try to falsify the step (see `/refute`).
7. **Decision:**
   - continue if a user requirement is unmet;
   - continue if evidence is missing;
   - continue if a plausible failure remains untested;
   - stop only if success is verified, or the task is explicitly blocked.

Do not ask the user to approve every execution detail. Ask only when an
ambiguity changes the definition of success or touches irreversible risk.

**Final output (required):**

| requirement | evidence | status | caveat |
|---|---|---|---|

For serious sessions, append an entry to
[`loop_ledger.md`](../loop_ledger.md). Close with `/ship-loop` before finalising.
