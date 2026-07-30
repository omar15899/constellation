# CLAUDE.md — `~/GitHub/` Constellation Kernel

This file is the **constitutional kernel for any AI agent whose working
directory is `~/GitHub/` or any of its subrepositories**. It supplements
the user-level `~/CLAUDE.md` (Omar's personal contract) and is supplemented
in turn by each repo's own `CLAUDE.md`. The three layers compose:

```
~/CLAUDE.md                  ← user identity, tone, mathematics, git defaults
~/GitHub/.claude/CLAUDE.md       ← THIS FILE — the constellation kernel
~/GitHub/<repo>/CLAUDE.md    ← lab-specific contract
```

When the three conflict, **the most specific layer wins**. When a repo's
`CLAUDE.md` is silent on a topic, fall back here. When this file is silent,
fall back to `~/CLAUDE.md`.

---

## 1. Identity of `~/GitHub/`

`~/GitHub/` is **the executable surface** of Omar's intellectual portfolio.
It hosts:

- **QuantOS** — a 14-repo constellation forming a tiered, type-bound,
  audit-anchored quantitative-finance operating system. Canonical map at
  [`~/GitHub/QUANTOS.md`](../QUANTOS.md). Vault-side governance at
  `~/OmarOS/05_Projects/QuantOS/`.
- **Adjacent repos** — Scilux, MMARV1, KarimSpecificCase, tradinginterface
  (UI), which live on disk next to QuantOS but are **not** bound by its
  tier discipline.
- **Vault-mirrored projects** — repos that exist independently here but
  whose semantic/governance layer lives inside `~/OmarOS/`.

Above this directory is the **OmarOS vault** (`~/OmarOS/`) — the semantic
layer, the vision, the reflection space, the decision log, the project
operations surface. Vault is policy + memory; this directory is action +
code. When the two collide, **policy wins**: vault decisions bind code,
not the other way round.

---

## 2. The two control planes

The constellation has two AI control planes, one above the other.

### 2.1 Constellation plane — `~/GitHub/.claude/`

Owns: discovery, routing, cross-repo composition, shared agents, shared
skills, perimeter policy, bootstrap, audit.

Read-only on individual repos by default. Writes only inside `.claude/`
itself, or — when the user explicitly invokes a bootstrap/refactor —
inside the targeted repo following the documented protocol.

### 2.2 Repo plane — `~/GitHub/<repo>/.claude/`

Owns: lab-specific agents, lab-specific skills, lab-specific commands,
lab-specific hooks. Authoritative for everything lab-internal.

**Doctrine.** The constellation plane composes; the repo plane executes.
A cross-repo agent in `.claude/agents/` may delegate to a per-repo agent in
`<repo>/.claude/agents/`, but never vice versa. The repo plane must not
know about the constellation plane's internals — it must only know about
its own peers, listed in its `.claude/registry/peers.yaml`.

### 2.3 The Codex head — `.codex/` and `AGENTS.md`

Both planes are **dual-headed**. Every `.claude/` surface, at either level,
has a `.codex/` twin and an `AGENTS.md`, so Omar can drive any repo with
Claude Code or OpenAI Codex interchangeably.

**`.claude/` is canonical. `.codex/` is generated.** The projection is
[`.claude/scripts/codex_sync.py`](scripts/codex_sync.py); the mapping and its
empirical basis are in [`docs/codex_parity.md`](docs/codex_parity.md).

There is one implementation of every behaviour, never two:

- agent instruction bodies are embedded from `.claude/agents/<n>.md` into the
  TOML Codex reads;
- `.codex/skills/<n>` is a **symlink** to `.claude/skills/<n>` — the same
  `SKILL.md`, byte for byte, because the frontmatter contract is identical
  in both products;
- `.codex/hooks.json` runs the same `.claude/hooks/` scripts through a shim
  that re-applies Claude's argument-level matchers and exports
  `CLAUDE_PROJECT_DIR`.

Only `.claude/commands/` has no Codex counterpart: Codex 0.146 has no custom
slash commands, so each `/name` is projected onto a skill invoked `$name`.

**Rules.** Never hand-edit `.codex/` or an `AGENTS.md` — both carry a
generated banner. Edit `.claude/` and re-run `/codex-sync`. Codex-only
material lives in `.codex/local/`, which the projection never touches.
`AGENTS.md` must never restate doctrine that belongs in `CLAUDE.md`; it
carries only the Codex translation layer and a directive to read `CLAUDE.md`.

**Two Codex-only prerequisites.** Project trust
(`codex_sync.py --trust`) and a one-time interactive hook approval per repo
(`/hooks` → *Trust all and continue*). Until hooks are trusted Codex runs
**none** of them, silently — including `secret_scan` and the commit gates.

---

## 3. Repo classification (canonical taxonomy)

Every repo under `~/GitHub/` carries exactly one **perimeter**, one
**tier** (if applicable), one **role**, and one **stack profile**. The
authoritative listing is [`registry/repos.yaml`](registry/repos.yaml);
the human-readable mirror is [`REPOS.md`](REPOS.md).

### 3.1 Perimeters

| Perimeter      | Members                                                                                     | Bound by QuantOS tiers? | Vault home                                  |
| -------------- | ------------------------------------------------------------------------------------------- | ----------------------- | ------------------------------------------- |
| `quantos-core` | Shared, BacktestLab, MonteCarloLab, Sweeplab, PricingLab, MarketDataLab                     | Yes (Tier 0–1.5)        | `05_Projects/QuantOS/Labs/`                 |
| `quantos-info` | NewsLab, ResearchLab, IntelligenceLab                                                       | Yes (Tier 2)            | `05_Projects/QuantOS/Labs/`                 |
| `quantos-alloc`| PortfolioLab                                                                                | Yes (Tier 2.5)          | `05_Projects/QuantOS/Labs/PortfolioLab/`    |
| `quantos-prod` | RiskLab, ExecutionLab                                                                       | Yes (Tier 3)            | `05_Projects/QuantOS/Labs/`                 |
| `quantos-orchestration` | StrategyOrchestrationLab                                                           | Yes (Tier 4)            | `05_Projects/QuantOS/Labs/`                 |
| `quantos-ui`   | tradinginterface                                                                            | Yes (UI tier)           | `05_Projects/QuantOS/Labs/tradinginterface/`|
| `adjacent`     | Scilux, MMARV1, KarimSpecificCase                                                           | No                      | varies per repo                             |
| `external`     | ruflo                                                                                       | No (vendored, ungoverned) | n/a                                       |
| `future`       | repos not yet on disk but reserved in the registry                                          | tbd                     | tbd                                         |

### 3.2 Tier discipline (only for `quantos-*` perimeters)

A Tier *k* component may import from Tiers 0..*k*−1, never from *k*..4.
This is **enforced by `import-linter`** in each lab's `.importlinter`
file. The constellation-level auditor agent
[`import-graph-auditor`](agents/import-graph-auditor.md) checks the
contracts hold across labs whenever cross-lab edits are made.

### 3.3 Stack profile

Each repo declares a stack profile in the registry — Python (uv +
ruff + mypy + pytest), TypeScript (React + Vite), Vanilla web, Mixed.
Cross-repo skills consult this field before running stack-specific
operations (linting, building, testing).

---

## 4. Cross-repo agents (the constellation roster)

Defined under [`agents/`](agents/). Full registry in
[`registry/agents.yaml`](registry/agents.yaml). High-level roster:

| Agent                       | Role                                                                                               | Tier        |
| --------------------------- | -------------------------------------------------------------------------------------------------- | ----------- |
| `constellation-cartographer`| Discovers repos on disk, classifies them, updates `repos.yaml` and `REPOS.md`. Read-only on repos. | Opus        |
| `cross-repo-router`         | Front door for any free-form request. Decides which repo(s) and which downstream agent to invoke.  | Opus        |
| `multi-repo-orchestrator`   | Coordinates work spanning ≥2 repos. The only agent authorised to delegate to per-repo orchestrators.| Opus        |
| `cross-repo-search`         | Runs ripgrep / structural / semantic queries across the whole constellation.                        | Sonnet      |
| `repo-classifier`           | Computes the perimeter / tier / role / stack of a new or unknown repo.                              | Sonnet      |
| `perimeter-keeper`          | Watches for drift: a repo declared `adjacent` that starts importing `quant_core`, etc.              | Sonnet      |
| `import-graph-auditor`      | Walks every lab's `.importlinter` contract and the union import graph.                              | Sonnet      |

Conventions:

- The router and the orchestrator are the **only two agents** authorised
  to spawn other constellation-level agents. Everything else is a
  specialist.
- No constellation agent writes inside a repo without an explicit user
  directive routed through the orchestrator.
- All constellation agents are read-only on `~/OmarOS/`. To write into
  the vault, escalate to the vault-side orchestrator.

---

## 5. Cross-repo skills (general-purpose toolkit)

Defined under [`skills/`](skills/). Each skill is a folder with a
`SKILL.md` descriptor. High-level set:

| Skill                  | What it does                                                                            |
| ---------------------- | --------------------------------------------------------------------------------------- |
| `repo-discovery`       | Scan `~/GitHub/` for new / removed / renamed repos and update the registry.             |
| `multi-repo-status`    | Aggregate `git status`, branch state, dirty tree across every repo.                     |
| `cross-repo-grep`      | Ripgrep across the whole constellation with perimeter filters.                          |
| `repo-bootstrap`       | Apply the standard QuantOS layout (or adjacent variant) to a new repo.                  |
| `tier-discipline`      | Verify import graphs respect the tier hierarchy.                                        |
| `cross-repo-refactor`  | Propagate a typed change (rename, signature, schema) across multiple repos.             |
| `perimeter-classify`   | Given an arbitrary folder, decide which perimeter it belongs to.                        |
| `constellation-brief`  | Generate a 1-page brief of the constellation state for fast onboarding.                 |

Skills here **extend**, not replace, the personal skills under
`~/.claude/skills/` and the per-repo skills in `<repo>/.claude/skills/`.
Constellation skills take precedence when the work spans repos.

---

## 6. Slash commands

Defined under [`commands/`](commands/). Designed to work whether the user
is sitting at `~/GitHub/` or inside any subrepo (with appropriate path
resolution).

| Command                | Purpose                                                                |
| ---------------------- | ---------------------------------------------------------------------- |
| `/repos`               | Print the constellation index (REPOS.md mirror).                       |
| `/repo-status`         | Run `multi-repo-status` and return the aggregate.                       |
| `/find-in-repos <q>`   | Cross-repo grep with perimeter filter.                                  |
| `/repo-route <prose>`  | Ask `cross-repo-router` where this request belongs, without executing.  |
| `/constellation`       | Generate a 1-page brief of the current state.                           |
| `/repo-bootstrap <path>` | Apply the standard layout to a new or under-equipped repo.            |

---

## 7. Routing doctrine

Every free-form request that lands inside `~/GitHub/` is routed in two
phases:

**Phase 1 — Perimeter routing.** `cross-repo-router` decides which
perimeter(s) and which repo(s) are relevant. Output: a list of targets
and a recommended downstream entry point.

**Phase 2 — In-repo routing.** Once the target repo is known, control
passes to that repo's `.claude/` infrastructure — typically its own
orchestrator or content router. This hub does not encode repo-internal
routing decisions.

**Special cases:**

- *Pure governance / vision / decision* → escalate to OmarOS (`~/OmarOS/`).
  See [`policies/escalation_to_omaros.md`](policies/escalation_to_omaros.md).
- *Pure cross-repo work* (audit, refactor, bootstrap) → stay at the
  constellation plane; do not descend into individual repos until needed.
- *Adjacent-perimeter request* (Scilux, MMARV1, etc.) → do **not** touch
  QuantOS infrastructure; treat the repo as a standalone project.

---

## 8. Shared-vs-local doctrine

A primitive belongs in `Shared/` (the QuantOS substrate) iff:

1. It is **causally identifying** — different inputs must produce
   different content-addressed roots.
2. It is **deterministically reproducible** — pure function of typed
   inputs, no hidden state.
3. It is **needed by ≥2 labs** — and would otherwise be duplicated.
4. It is **on the audit path** — its output is content-addressed and
   appears in artefact manifests.

A primitive belongs in a lab repo iff it fails any of those four. A
primitive **belongs nowhere yet** if it is exploratory — leave it inside
a `scratch/` directory until it stabilises. Full policy in
[`policies/shared_vs_local.md`](policies/shared_vs_local.md).

---

## 9. Git policy

Inherits from `~/CLAUDE.md` (natural human commit messages, no AI
attribution, no `Co-authored-by`). Constellation-specific overrides:

- **Atomic per repo.** Never commit across repos in one call. Each repo
  is its own git surface and gets its own commit.
- **Cross-repo PRs.** If a feature touches multiple labs, open one PR per
  repo and cross-reference them in the descriptions. CI must pass per
  repo independently.
- **Tier-violating commits are blocked.** `import-linter` in each lab's
  pre-commit gate refuses commits that invert the dependency graph.
- **No force-push to remotes.** Constellation hub never authorises
  `git push --force` on any repo's main branch.

Per-repo commit hooks (`pre_commit_gate.py`, `post_commit_doc_tracer.py`)
remain authoritative for their repo. The constellation hub never
overrides a repo's hook policy.

---

## 10. Risk classification

| Risk     | Examples                                                                                   |
| -------- | ------------------------------------------------------------------------------------------ |
| Low      | Updating `.claude/REPOS.md`, adding a constellation-level note, running discovery.             |
| Medium   | Editing a repo's `.claude/` config, adding a peer entry, applying `repo-bootstrap`.        |
| High     | Restructuring perimeters, retiring a repo, force-pushing, rewriting cross-lab contracts.   |

High-risk operations require explicit confirmation unless Omar has
authorised autonomous execution in the session.

---

## 11. Hooks (constellation-level)

Reusable hook scripts live under [`hooks/`](hooks/). They are *templates*
— a repo opts in by symlinking or copying. The constellation hub does
not install hooks into a repo silently.

- `repo_discovery.py` — refresh `repos.yaml` when invoked.
- `peer_sync.py` — push the canonical peer list down into each repo's
  `.claude/registry/peers.yaml`.

Per-repo hook policy (gates, doc-tracer, session logger, src-change-warn)
stays inside that repo's `.claude/hooks/` and is authoritative for
itself.

---

## 12. Naming conventions for `.claude/` artefacts

- Agents: `<verb>-<noun>.md` (kebab-case), e.g. `cross-repo-router.md`.
- Skills: `<verb>-<noun>/SKILL.md`.
- Commands: `<command-slug>.md`.
- Registry files: `<noun>.yaml`, lower-case singular.
- Policies: `<topic_snake_case>.md`.
- Templates: descriptive, suffix `.template` for files copied verbatim.

All identifiers ASCII, snake or kebab as documented, no emoji.

---

## 13. Authoritative references

- [`REPOS.md`](REPOS.md) — human-readable constellation index.
- [`registry/repos.yaml`](registry/repos.yaml) — machine-readable repo registry.
- [`registry/perimeters.yaml`](registry/perimeters.yaml) — perimeter definitions.
- [`registry/agents.yaml`](registry/agents.yaml) — cross-repo agent roster.
- [`policies/`](policies/) — perimeter doctrine, tier discipline, shared-vs-local,
  cross-repo commits, escalation to OmarOS, AI invariants.
- [`~/GitHub/QUANTOS.md`](../QUANTOS.md) — canonical QuantOS map (tiers + flow).
- [`~/OmarOS/05_Projects/QuantOS/AGENTS.md`](../../OmarOS/05_Projects/QuantOS/AGENTS.md) — vault-side governance.
- [`~/OmarOS/CLAUDE.md`](../../OmarOS/CLAUDE.md) — vault constitutional kernel.

---

## 14. What this hub is NOT

- **Now its own repo: `constellation`.** The surface stabilised, so the control
  plane is versioned as `github.com/omar15899/constellation` (private). The repo
  root is `~/GitHub/` with an allowlist `.gitignore`: it tracks only the control
  plane and ignores the 18 sub-repos, which remain independent git repositories
  that sit *beside* — not inside — this one.
- **Not a replacement for `.claude/`.** Each lab keeps its own.
- **Not the vault.** OmarOS owns vision, reflection, decisions, and
  long-form semantics. This hub is operational only.
- **Not auto-magical.** Nothing here runs unless an agent or the user
  invokes it. The hub is a library + a contract, not a daemon.
