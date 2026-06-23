# `.claude/` — GitHub Constellation AI Hub

This directory is the **master AI control surface for every repository under
`~/GitHub/`**. It is the unifying layer above the individual `.claude/`
configurations that already live inside each lab.

It exists because the repos under `~/GitHub/` are *not* independent projects.
They form a coherent constellation — QuantOS labs, adjacent repos, mirrors of
OmarOS subprojects — and an AI session opened at `~/GitHub/` must be able to:

1. **See the whole.** Know every repo, its perimeter, its tier, its role, its
   stack, and its relationship to the others.
2. **Route work.** Decide which repo (or which subset) is the right home for
   any incoming request, before any specialist agent is invoked.
3. **Compose work.** Run agents and skills that operate *across* repos —
   search, refactor, status, audit, bootstrap, mirror.
4. **Reuse infrastructure.** Provide general-purpose agents, skills, hooks,
   commands, and templates that every repo can pull from, instead of each
   reinventing them.
5. **Stay coherent.** Encode the invariants that bind the constellation:
   tier discipline, perimeter doctrine, shared-vs-local, vault-mirror rules,
   commit policy, escalation paths to OmarOS.

The kernel document is [`CLAUDE.md`](CLAUDE.md). Read it first.

## Layout

| Path                | Role                                                          |
| ------------------- | ------------------------------------------------------------- |
| `CLAUDE.md`         | Constitutional kernel for any agent invoked at `~/GitHub/`.   |
| `REPOS.md`          | Human-readable index of every repo on disk.                   |
| `registry/`         | Machine-readable YAML: repos, perimeters, stacks, agents.     |
| `agents/`           | Cross-repo agent specs (cartographer, router, orchestrator…). |
| `skills/`           | Cross-repo skills (status, grep, bootstrap, tier-check…).     |
| `commands/`         | Slash commands wired to the cross-repo agents/skills.         |
| `hooks/`            | Reusable Python hook scripts repos can pull in.               |
| `scripts/`          | CLI utilities — discovery, status, grep, bootstrap.           |
| `templates/`        | Bootstrap material for new repos.                             |
| `policies/`         | Cross-repo doctrine: tiering, perimeters, commits, vault.     |
| `docs/`             | Architecture notes and how-to guides.                         |

## Two horizontal layers

The constellation is layered:

```
┌───────────────────────────────────────────────────────────────┐
│  ~/GitHub/.claude/  ←  this directory: cross-repo AI control plane │
└───────────────────────────────────────────────────────────────┘
            │ catalogues, routes, composes, bootstraps
            ▼
┌───────────────────────────────────────────────────────────────┐
│  ~/GitHub/<repo>/.claude/  ←  per-repo AI surface (lab-local)  │
└───────────────────────────────────────────────────────────────┘
```

Per-repo `.claude/` directories stay authoritative for lab-specific work.
This hub never overrides them; it composes them.

## Above the constellation: OmarOS

The vault at [`~/OmarOS/`](file:///Users/omarkhalil/OmarOS) is the
governing layer above this hub. Vision documents, decisions, project logs,
research notes for repos under `~/GitHub/` live there. When a request
requires writing semantic / reflective / governance content, escalate to
OmarOS. See [`policies/escalation_to_omaros.md`](policies/escalation_to_omaros.md).

## Entry points

- New session at `~/GitHub/` → read `CLAUDE.md`, then `REPOS.md`.
- Don't know which repo to touch? → invoke `cross-repo-router`.
- Need to find code anywhere → `cross-repo-grep` skill.
- Need status across the constellation → `multi-repo-status` skill.
- New repo joining the family → `repo-bootstrap` skill + `templates/`.
- Cross-lab refactor → `cross-repo-refactor` skill + `multi-repo-orchestrator`.

## Authority

This hub is **policy + composition**. It does not own the source of truth for:

- Individual lab implementations (lives in each `<repo>/`).
- QuantOS tier hierarchy and data flow (canonical at `~/GitHub/QUANTOS.md`).
- Vault-side vision and governance (canonical at `~/OmarOS/`).

This hub binds those sources together and gives AI sessions a coherent
view onto them.
