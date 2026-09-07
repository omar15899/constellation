# AI Invariants

The non-negotiable rules that bind every AI agent acting inside
`~/GitHub/`. These are the things that, if violated, make the
constellation incoherent. Everything else is policy and can be
debated; these cannot.

## 1. Discoverability

Every repo under `~/GitHub/` is either in `registry/repos.yaml` or it
is unknown. An agent that operates on an unknown repo first runs
`repo-discovery` and resolves classification with the cartographer. No silent operation on
undiscovered state.

## 2. Routing before writing

The current agent establishes target and authority using
[`routing`](../contracts/routing.md) before writing. Use
`multi-repo-orchestrator` for the cases defined there. User authority persists
through necessary implementation and verification; routing is not an approval.

## 3. One commit per repo

A multi-repo change produces one commit per repo, in tier order,
each respecting that repo's own pre-commit gate. Never bundle, never
`--no-verify`, never `--force` to `main`.

## 4. Tier discipline is load-bearing

No tier inversion is committed, ever. The cross-repo orchestrator
halts on the first detected inversion. The vault decides whether to
rewire or rewrite; the hub does not paper over.

## 5. Hub is library, not daemon

Nothing in `~/GitHub/.claude/` runs unless invoked. There are no background
processes, no schedulers, no agents that poll. The hub is a contract
+ a library, executed on demand.

## 6. Vault is read-only from the hub

`~/OmarOS/` is read-only for every agent acting at the constellation
plane. Vault writes happen via the vault's own routing pipeline,
authored by the user (possibly with vault-side AI assistance).

## 7. Adjacent repos are sovereign

`adjacent` perimeter members (Scilux, MMARV1, KarimSpecificCase, and
any future addition) are independent projects. The hub does not
impose QuantOS infrastructure on them without explicit user
authorisation. Bootstrapping an adjacent repo uses the `adjacent`
variant, which is minimal.

## 8. Idempotence

Every constellation script, hook, skill, and agent is idempotent when
run against a state that already satisfies the invariants. Second
invocations on unchanged state produce zero writes and zero observable
side-effects (other than reporting "no change").

## 9. Stderr is loud, stdout is clean

Hooks and scripts log to stderr with a `[constellation:<name>]` tag.
Stdout is reserved for primary output or the client's structured hook response.
Report failures and material findings; an irrelevant event or successful
no-op may exit quietly so routine checks do not flood the agent context.

## 10. Failure surfaces, never bypasses

When a hook, a gate, an auditor, or a linter refuses an action, the
correct response is to surface the refusal and repair its cause within the
authorized task. Ask when repair requires a new decision, broader authority
or a change to the contract. Do not disable the hook, suppress the error or
skip the check. A failed test does not itself revoke permission to fix code.

## 11. Secrets are out of bounds

The hub never reads `.env*`, `*.pem`, `*.key`, `credentials.json`, or
any file matching common secret patterns. Scripts use the standard
exclude globs declared in `find-in-repos`, including private conversation paths.

## 12. No emoji, no AI attribution

Inherits from `~/CLAUDE.md`. No emoji in commits, prompts, agent
specs, or generated files. No `Co-authored-by`. No "Generated with
Claude". This applies to the hub itself, not just the repos it
manages.
