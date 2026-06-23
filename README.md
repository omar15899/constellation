# constellation

The AI control plane for a constellation of independent repositories.

`~/GitHub/` hosts 18 registered repos — 14 QuantOS labs (Shared, BacktestLab,
MonteCarloLab, Sweeplab, PricingLab, MarketDataLab, NewsLab, ResearchLab,
IntelligenceLab, PortfolioLab, RiskLab, ExecutionLab, StrategyOrchestrationLab,
tradinginterface) plus four adjacent/external repos (Scilux, MMARV1,
KarimSpecificCase, ruflo). This repository is the orchestration layer that sits
*between* those repos: discovery, routing, cross-repo agents, shared skills,
slash commands, perimeter/tier policy, and the verification hooks.

## What this repo intentionally does NOT contain

The 18 sub-repos are **not** vendored here. Each is its own independent git
repository with its own history, CI, and `.claude/` plane. The `.gitignore` is
an allowlist: it ignores everything at the root and re-includes only the
orchestrator surface (`.claude/`, `CLAUDE.md`, `QUANTOS.md`, `README.md`). The
sub-repos, local caches (`.venv`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`,
`.playwright-mcp`), `__pycache__`, `.DS_Store`, and runtime lock files are never
tracked. Cloning this repo gives you the control plane alone.

## Start here

- `.claude/CLAUDE.md` — the constitutional kernel (constellation long-form).
- `.claude/REPOS.md` — human-readable repo index (perimeter + tier + stack).
- `QUANTOS.md` — canonical QuantOS map (tier hierarchy + production data flow).

The three CLAUDE.md layers compose, most-specific-wins:
`~/CLAUDE.md` (user) -> `~/GitHub/CLAUDE.md` (root pointer) ->
`~/GitHub/.claude/CLAUDE.md` (this kernel) -> `<repo>/CLAUDE.md` (lab contract).

## What it provides

- **Cross-repo agents** (`.claude/agents/`) — cartographer, router,
  orchestrator, cross-repo search, repo-classifier, perimeter-keeper,
  import-graph-auditor.
- **Cross-repo skills** (`.claude/skills/`) — repo-discovery, multi-repo-status,
  cross-repo-grep, repo-bootstrap, tier-discipline, cross-repo-refactor,
  perimeter-classify, constellation-brief.
- **Slash commands** (`.claude/commands/`) — `/repos`, `/repo-status`,
  `/find-in-repos`, `/repo-route`, `/constellation`, `/repo-bootstrap`,
  `/tier-check`.
- **Registry** (`.claude/registry/`) — machine-readable `repos.yaml`,
  `perimeters.yaml`, `stacks.yaml`, `agents.yaml`.
- **Policies** (`.claude/policies/`) — perimeter doctrine, tier discipline,
  shared-vs-local, cross-repo commits, escalation, AI invariants.
- **Scripts** (`.claude/scripts/`) — `discover_repos.py --state`,
  `status_all.sh`, `grep_all.sh`, `bootstrap_repo.sh`.

## Expert-directed verification workflow

The control plane enforces a validity-first, evidence-anchored loop:

- `/verify-loop` — bounded Plan -> Execute -> Verify -> Refute -> Repair with an
  evidence table.
- `/quant-loop` — the same loop specialised for quantitative research
  (provenance, alignment, lookahead, survivorship, costs, alpha-vs-beta).
- `/ship-loop` — the final verified-success gate before committing.
- `/refute` — adversarial self-review; tries to falsify the current claim.
- `/evidence` — audits every numerical or completion claim against hard evidence.
- `.claude/contracts/` — the expert-agent and task contracts the loops bind to.

## Deterministic hooks

Wired in `.claude/settings.json` (`$CLAUDE_PROJECT_DIR`-relative):

- `secret_scan.sh` — blocks staged/written secrets (token prefixes, PEM keys,
  credential assignments).
- `changed_python_syntax.sh` — syntax-checks changed Python.
- `evidence_audit.py` — checks completion/numeric claims carry evidence.
- `loop_guard.py` — guards against unsupported completion language; the
  prose-heuristic enforcement is **opt-in** via `LOOP_GUARD_STRICT=1` (off by
  default so a misjudged Stop never bricks a turn).

Because this root is now a git repository, the `secret_scan` staged-diff path is
live: the hook scans the staged diff on commit, not just individual file writes.

## Not a daemon, not the vault

Nothing here runs unless an agent or the user invokes it — this is a library
plus a contract. Vision, decisions, and long-form governance live in the OmarOS
vault (`~/OmarOS/`), which is read-only from any session running here.
