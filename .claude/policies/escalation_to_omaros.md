# Escalation to OmarOS

`~/GitHub/` is the **executable surface** of Omar's intellectual
portfolio. `~/OmarOS/` is the **semantic surface** — vision,
decisions, reflections, project logs, research notes, governance.

When a request lands at `~/GitHub/` whose primary output is semantic
(not code), it must be escalated to the vault. This policy prescribes
when, how, and what to escalate.

## When to escalate

| Request type                                            | Action                                                |
| ------------------------------------------------------- | ----------------------------------------------------- |
| Vision / roadmap / architecture writeup                 | Escalate → vault `05_Projects/QuantOS/Vision/`        |
| Decision / ADR / trade-off recorded for future-self     | Escalate → vault `05_Projects/QuantOS/Decisions/`     |
| Reflection / essay / "what did I learn from this"       | Escalate → vault `01_Daily_Life/Reflections/`         |
| Research note / hypothesis / open problem               | Escalate → vault `04_Research/` or `06_Knowledge_Base/`|
| Project log / status report / checkpoint                | Escalate → vault `05_Projects/<project>/`             |
| Bug write-up that includes "why" (not just the fix)     | Code fix in repo; reflection in vault                 |
| Cross-lab refactor outcomes documented                  | ADR in vault                                          |
| Task / TODO that survives beyond this session           | Escalate → vault `02_Tasks_and_Execution/Ledger/`     |
| Reading note on a paper / book / lecture                | Escalate → vault `15_Reading_and_Learning/`           |

## How to escalate

The constellation hub **does not write into the vault**. It
recommends the escalation and either:

1. Hands the user a vault-side command to run (e.g. `/decision`,
   `/reflect`, `/project-log`, `/research`), or
2. Stages a snippet under `~/GitHub/.claude/docs/escalation_drafts/` for
   the user to pick up and route via the vault's `content-router`.

The actual vault write is performed by the vault's own routing
pipeline (`semantic-kernel` → `content-router` → specialist writer).

## Vault has priority over hub

When the vault and the hub disagree:

- Vault decisions bind code. The hub does not override an ADR.
- Vault vision documents bind the constellation. A vision update is
  cause for a hub update, not the other way round.
- Vault metadata enums bind any frontmatter the hub generates.

This means a vault-side decision can constrain `~/GitHub/` work, but
no `~/GitHub/` action can constrain vault work without a vault-side
decision to ratify it first.

## What the hub may write under `.claude/`

To keep the asymmetry clean:

- The hub may write inside `~/GitHub/.claude/` freely.
- The hub may propose vault edits as drafts under
  `~/GitHub/.claude/docs/escalation_drafts/` — these are never published
  into the vault automatically.
- The hub may not write inside `~/OmarOS/` for any reason. Read-only.

## Escalation envelope

When the router or orchestrator recommends escalation, it emits an
envelope like:

```yaml
escalation:
  reason: "Decision to lift KnownAt → WithTime is project-level, not
           a code change."
  vault_target: ~/OmarOS/05_Projects/QuantOS/Decisions/
  suggested_command: /decision
  draft_path: ~/GitHub/.claude/docs/escalation_drafts/2026-05-15_rename_known_at.md
  next_step: "Run /decision at the vault to materialise the draft."
```

Drafts under `escalation_drafts/` are short — title, motivation,
proposed text — and survive across sessions until the user picks them
up.
