# AGENTS.md — the constellation root

/Users/omarkhalil/GitHub is itself the private git repository `constellation` (github.com/omar15899/constellation) — the AI control plane that sits BETWEEN ~20 independent repos, not a monorepo containing them. Its .gitignore is an allowlist tracking only .claude/, .codex/, CLAUDE.md, AGENTS.md, QUANTOS.md and README.md (107 files tracked today); the sub-repos, caches, .venv and pyproject.toml are ignored and keep their own histories. It owns discovery, routing, cross-repo agents/skills/commands, perimeter and tier policy, the promotion gate, the lever registry, and the verification hooks — its perimeter is 'constellation hub' (it has no entry in its own registry/repos.yaml and no QuantOS tier). The plane is dual-headed: .claude/ is canonical and .codex/ plus every AGENTS.md are its generated projection via .claude/scripts/codex_sync.py, so either agent can drive any repo. Doctrine: the constellation plane composes, the repo plane executes; the hub is a library plus a contract, never a daemon; and the OmarOS vault at ~/OmarOS/ is read-only from here because policy binds code, not the reverse.

This file is the **Codex** entry point for this repository.
Its Claude Code counterpart is `CLAUDE.md`. The two agents are meant to be
interchangeable: same doctrine, same agents, same skills, same guardrails.

## Read this first

**`CLAUDE.md` in this directory is the canonical contract for this repo.**
It is agent-neutral: everywhere it says *Claude*, read *the agent*, and
everywhere it names a `.claude/` path, the Codex equivalent is in the
mapping table below. Read it in full before any non-trivial work.

The long-form Codex kernel — layer composition, construct mapping,
cross-repo entry points, Codex-specific operating rules — is
[`.codex/AGENTS.md`](.codex/AGENTS.md). Codex does not load it
automatically (it is never the working directory); read it explicitly.

Reading order:

1. `CLAUDE.md`
2. `README.md`
3. `.claude/CLAUDE.md`
4. `.claude/REPOS.md`
5. `QUANTOS.md`
6. `.claude/registry/repos.yaml`
7. `.claude/policies/ai_invariants.md`
8. `.claude/policies/perimeter_doctrine.md`
9. `.claude/policies/tier_discipline.md`
10. `.claude/policies/cross_repo_commits.md`
11. `.claude/policies/escalation_to_omaros.md`
12. `.claude/policies/shared_vs_local.md`
13. `.claude/policies/worktree_lifecycle.md`
14. `.claude/contracts/expert_agent_contract.md`
15. `.claude/contracts/promotion_gate.md`
16. `.claude/docs/architecture.md`
17. `.claude/docs/codex_parity.md`
18. `.claude/docs/how_to_add_a_repo.md`
19. `.claude/docs/git_as_research_ledger.md`
20. `.claude/docs/research_pipeline.md`
21. `.claude/hooks/README.md`
22. `.claude/commands/README.md`

## Stack and commands

**Stack:** python (stdlib-only, no dependencies) + markdown/yaml. The 107 tracked files are ~85 markdown/yaml documents plus 13 dependency-free Python hooks and 12 scripts in .claude/scripts/ ('Dependency-free Python 3.12 (only stdlib, plus the system `git`)' — hooks/README.md); YAML is hand-parsed, no PyYAML, and TOML is emitted by hand in codex_sync.py. In practice everything runs on the system `python3`, which is 3.14.6 here and has no pytest. The root pyproject.toml/uv.lock (uv workspace, ruff + mypy strict + pytest for the lab packages) and the shared .venv (Python 3.12.11) are present on disk but GITIGNORED and belong to the sibling repos, not to this one.

```bash
python3 .claude/scripts/doctor.py # hub health; exits 0. Currently prints WARN (not PASS) because the hub working tree is dirty
python3 .claude/scripts/doctor.py --repo ../MarketDataLab
python3 .claude/scripts/doctor.py --json
python3 .claude/scripts/validate_repos.py # verified PASS (rc=0)
python3 .claude/scripts/validate_repos.py --cross-check
python3 .claude/scripts/validate_levers.py # verified PASS (rc=0)
python3 .claude/scripts/validate_settings.py # verified PASS (rc=0)
python3 .claude/tests/test_promotion_enforcement.py # stdlib-only, no pytest; verified all tests pass
python3 .claude/scripts/codex_sync.py --all --check # Codex-plane drift check; exit 1 = drift, exit 0 = planes agree
python3 .claude/scripts/codex_sync.py --repo . --check # same, root surface only (--check REQUIRES --all or --repo)
python3 .claude/scripts/codex_sync.py --all # apply the projection
python3 .claude/scripts/codex_sync.py --trust # register project trust in ~/.codex/config.toml
python3 ~/GitHub/.claude/scripts/discover_repos.py # dry-run (default)
python3 ~/GitHub/.claude/scripts/discover_repos.py --apply # writes (--apply is documented in --help as '(reserved)')
```

_7 further commands omitted. See `~/GitHub/.claude/registry/codex_repo_briefs.json` for the rest._

## Invariants — do not violate these

- No `--no-verify`, no `--force` to main. Ever. (CLAUDE.md §9; ai_invariants.md §3: 'Never bundle, never `--no-verify`, never `--force` to `main`.')
- One commit per repo per logical change, in tier order, each respecting that repo's own pre-commit gate. Never commit across repos in one call. Cross-repo features get one PR per repo, cross-referenced, with CI passing per repo independently. (CLAUDE.md §9, ai_invariants.md §3)
- Tier discipline is load-bearing: a Tier k component may import from Tiers 0..k-1, never from k..4. No tier inversion is committed, ever; the cross-repo orchestrator halts on the first detected inversion. (ai_invariants.md §4)
- Routing before writing: a free-form request does not produce a write until `cross-repo-router` has classified it and, where applicable, `multi-repo-orchestrator` has authorised the work. The router never writes; the orchestrator only writes with explicit user authorisation per operation. (ai_invariants.md §2)
- Discoverability: 'Every repo under `~/GitHub/` is either in `registry/repos.yaml` or it is unknown.' An agent operating on an unknown repo first runs repo-discovery and repo-classifier. No silent operation on undiscovered state. (ai_invariants.md §1 — currently VIOLATED by GasStorageOptimiserEngie/)
- The hub is a library, not a daemon: 'Nothing in `~/GitHub/.claude/` runs unless invoked. There are no background processes, no schedulers, no agents that poll.' (ai_invariants.md §5)
- The vault is read-only from the hub: '`~/OmarOS/` is read-only for every agent acting at the constellation plane.' Vault-class work (vision, decisions, reflections) is escalated, never written. (ai_invariants.md §6, policies/escalation_to_omaros.md)
- Adjacent repos are sovereign: Scilux, MMARV1, KarimSpecificCase and brainteasers-asincronas are independent projects; the hub does not impose QuantOS infrastructure on them without explicit user authorisation. ruflo is external/vendored and excluded from constellation audits entirely. (ai_invariants.md §7)
- Failure surfaces, never bypasses: when a hook, gate, auditor or linter refuses an action, the correct response is to 'surface the refusal and ask'. The wrong response is to disable the hook, suppress the error, or skip the check. (ai_invariants.md §10)
- Secrets are out of bounds: the hub never reads `.env*`, `*.pem`, `*.key`, `credentials.json`, or any file matching common secret patterns. secret_scan.sh enforces this on PreToolUse and PostToolUse and additionally scans the staged diff (`git diff --cached`) when inside a work tree, exiting 2 to block. …
- No emoji, no AI attribution: no emoji in commits, prompts, agent specs, or generated files; no `Co-authored-by`; no 'Generated with Claude'. This applies to the hub itself, not just the repos it manages. (ai_invariants.md §12)
- Idempotence: every constellation script, hook, skill and agent is idempotent — second invocations on unchanged state produce zero writes and zero observable side-effects. (ai_invariants.md §8)
- _4 further invariants omitted. See `~/GitHub/.claude/registry/codex_repo_briefs.json` for the rest._

## The Codex control plane in this repo

`.codex/` is a **generated projection** of `.claude/`. `.claude/` is canonical:
edit there, then re-run

```bash
~/GitHub/.claude/scripts/codex_sync.py --repo /Users/omarkhalil/GitHub
```

| Construct | Claude Code | Codex | How you invoke it here |
| --- | --- | --- | --- |
| root contract | `CLAUDE.md` | `AGENTS.md` | loaded automatically |
| subagents (7) | `.claude/agents/<n>.md` | `.codex/agents/<n>.toml` | ask Codex to spawn `<n>` |
| skills (8) | `.claude/skills/<n>/` | `.codex/skills/<n>` (symlink) | `$<n>` |
| slash commands (22) | `/<n>` | `.codex/skills/<n>/SKILL.md` | `$<n>` |
| hooks (4 events) | `settings.json` | `.codex/hooks.json` | automatic once trusted |
| permissions | `settings.json` `permissions` | `.codex/config.toml` + `.codex/rules/` | automatic once trusted |

Codex 0.146 has no custom slash commands, so everything Claude exposes as
`/name` is a Codex **skill** invoked with `$name`. Hook *scripts* are not
duplicated: `.codex/hooks.json` runs the same `.claude/hooks/` files through
`.codex/hook_shim.py`, which re-applies Claude's argument-level matchers and
exports `CLAUDE_PROJECT_DIR`.

### Subagents available here

`constellation-cartographer`, `cross-repo-router`, `cross-repo-search`, `import-graph-auditor`, `multi-repo-orchestrator`, `perimeter-keeper`, `repo-classifier`

### Route through these

- /repos — print the constellation index; refreshes registry/repos.yaml if drift is detected (wraps repo-discovery skill)
- /repo-status — aggregate git status/branch/ahead-behind/dirty across every repo; --dirty-only, --perimeter (wraps multi-repo-status skill -> scripts/status_all.sh)
- /find-in-repos <q> — ripgrep across the constellation with perimeter/stack/repo filters (wraps cross-repo-grep skill -> scripts/grep_all.sh)
- /repo-route <prose> — inspect the routing decision without executing (wraps cross-repo-router agent)
- /constellation — one-page state brief; the canonical session-start command (wraps constellation-brief skill)
- /repo-bootstrap <path> — apply the standard QuantOS or adjacent layout to an under-equipped repo (wraps repo-bootstrap skill -> scripts/bootstrap_repo.sh). NOTE: collides with the skill of the same name; Codex exposes the command as $cmd-repo-bootstrap and the skill as $repo-bootstrap
- /tier-check — audit the QuantOS import graph against the tier hierarchy (wraps tier-discipline skill -> import-graph-auditor agent)
- /repo-doctor — read-only hub health check; composes the three validators + settings integrity + hub git state (scripts/doctor.py)
- /codex-sync — re-project the canonical .claude/ plane onto .codex/ + AGENTS.md across the constellation; drift-check first, apply, then verify with the codex binary (scripts/codex_sync.py)
- /verify-loop — bounded Plan -> Execute -> Verify -> Refute -> Repair with an evidence table; default max 3 loops. NOT /loop (that is the recurring scheduler)
- /quant-loop — the same loop specialised for quant research: provenance, alignment, lookahead, survivorship, universe, costs, alpha-vs-beta, baseline
- /ship-loop — final verified-success gate before finalising or committing
- /refute — adversarial self-review; tries to falsify the current claim
- /evidence — audit every numeric/completion claim against a backing artifact (hooks/evidence_audit.py; --ledger cross-checks the Bash run ledger)
- /intent-check — reconstruct explicit vs inferred request; separate planning (user's) from execution (agent's) decisions
- /gate-check — run a result through the promotion gate (DSR/PBO/reality-check/BH-FDR/bootstrap-CI) and assign a canonical verdict
- /record-verdict — record a lever verdict into registry/levers.yaml + research_ledger.md via scripts/record_lever_verdict.py; dry-run first, then --apply
- /debug-metric — trace a suspicious/NaN/empty metric from producing code -> input data -> output artifact
- _12 further entry points omitted. See `~/GitHub/.claude/registry/codex_repo_briefs.json` for the rest._

## Two setup steps Codex needs and Claude does not

1. **Trust the project.** Codex ignores a project-local `config.toml`,
   `hooks.json` and `rules/` until the project is trusted.
   Run `~/GitHub/.claude/scripts/codex_sync.py --trust` once.
2. **Trust the hooks.** Codex refuses to run hooks until you approve them:
   start `codex` in this repo, run `/hooks`, choose *Trust all and continue*.
   Until you do, hooks are **silently skipped** — including the secret
   scanner and any commit gate. Re-approve after every `codex_sync.py` run
   that changes `hooks.json`.

## Gotchas

- AGENTS.md and everything under .codex/ are GENERATED by .claude/scripts/codex_sync.py and carry a `DO NOT EDIT BY HAND` banner. Never hand-edit them; edit .claude/ and re-run the projection. Codex-only material with no Claude counterpart belongs in .codex/local/, which the projection neither reads nor removes.
- The root .gitignore is an ALLOWLIST (`/*` then re-includes). It NOW allowlists `!/.codex/` and `!/AGENTS.md` — but that .gitignore edit is itself uncommitted, and .codex/, AGENTS.md, .claude/scripts/codex_sync.py and .claude/docs/codex_parity.md are all still untracked. `.agents/` (the dead 2026-07-17 layout, 28 stale …
- Every skill under .codex/skills/ is a SYMLINK into .claude/skills/ (8 of them; the 22 command-skills are generated files). .codex/ is not self-contained and is not an independent state store: hooks/_common.py hardcodes `HUB = Path.home()/'GitHub'/'.claude'` and evidence_audit.py hardcodes `~/GitHub/.claude/run`, so a …
- Codex hooks run through .codex/hook_shim.py, which re-exports CLAUDE_PROJECT_DIR/CODEX_PROJECT_DIR and re-applies argument-level matchers via --command-glob, passing stdin/stdout/stderr and the exit code through so exit-2 blocking still works. Rewriting .codex/hooks.json invalidates Codex's stored trusted_hash: until …
- `python3` on this machine is 3.14.6 and has NO pytest (`No module named pytest`). Every hub check is deliberately stdlib-only, including .claude/tests/test_promotion_enforcement.py. Do not add a pytest invocation for the hub. The 3.12.11 venv at /Users/omarkhalil/GitHub/.venv belongs to the sibling labs' uv workspace …
- pyproject.toml and uv.lock at the root are NOT part of this repo (gitignored). Reading them tells you about the 27 lab packages in the sibling repos, not about the constellation control plane.
- There is no CI at all for this repo: no .github/, no Makefile, no package.json. `.claude/templates/lint.yml.template` is a template shipped TO other repos, not a workflow for this one.
- `codex_sync.py --check` refuses to run without `--all` or `--repo PATH` (it errors out on `--check` alone). It exits 1 on drift and 0 when the planes agree. `doctor.py` exits 0 even when it reports WARN, so parse its verdict line rather than its exit code.
- The Bash run ledger lives at .claude/run/ and is explicitly gitignored (section 5): 'Ephemeral — never committed. The DURABLE research ledger is the commit-trailer history, not these files.'
- Several hooks are advisory-by-default and only block under an opt-in env flag: LOOP_GUARD_STRICT, DEAD_LEVER_STRICT, METRIC_PROVENANCE_STRICT, COMMIT_GUARD_STRICT. Disable switches: METRIC_PROVENANCE_DISABLE, DEAD_LEVER_GUARD_DISABLE, RESEARCH_LOADER_DISABLE, LOOP_GUARD_DISABLE, BASH_LEDGER_DISABLE. …
- commit_guard.py is NOT wired into settings.json — it is a standalone manual/pre-commit validator. Exactly 7 hook scripts are wired (doctor.py: 'referenced hooks exist — 7/7 present'); the other 6 files in hooks/ are libraries (_common.py, _levers.py) or manual tools (commit_guard.py, evidence_audit.py, peer_sync.py, …
- Every written repo count in this repo is currently wrong. On disk: 20 git repos. registry/repos.yaml: 19. CLAUDE.md and README.md: 18. GasStorageOptimiserEngie/ is an unregistered git repo with its own CLAUDE.md. Do not restate a count — cite registry/repos.yaml as the source of truth and flag the drift.
- _3 further gotchas omitted. See `~/GitHub/.claude/registry/codex_repo_briefs.json` for the rest._

---

<!-- GENERATED BY .claude/scripts/codex_sync.py — DO NOT EDIT BY HAND -->
<!-- sources: CLAUDE.md (doctrine) + .claude/ (plane) + registry/repos.yaml -->
