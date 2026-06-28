# The Research Pipeline — canonical SOP

The single deterministic flow every serious research / implementation session
in `~/GitHub/` follows. It is **deterministic at the edges** (SessionStart +
PreToolUse + PostToolUse + Stop hooks, plus the lever registry and the commit
trailers) and **expert-directed in the middle** (the loop commands). The user
owns planning; Claude owns execution; "done" means hard evidence, not assertion
(see [`../contracts/expert_agent_contract.md`](../contracts/expert_agent_contract.md)).

```
new Claude session
   │
   ▼
SessionStart ── research_session_loader.py ──────────────────────────────────┐
   │   injects the standing research brief from registry/levers.yaml:         │
   │     · CONFIRMED edges (incumbents to beat)                               │ DETERMINISTIC
   │     · REFUTED / CAPPED / NO_IMPROVEMENT / HOLD  → DO-NOT-RE-RUN          │ (hook + registry)
   │     · OPEN  → the real next steps                                        │
   ▼                                                                          ┘
/intent-check ── reconstruct the request; split planning (user) vs execution (Claude);
   │             mark ambiguities that change "done" vs ones resolvable from the repo
   ▼
/quant-loop   (research validity-first)   OR   /verify-loop  (generic Plan→Execute→Verify→Refute→Repair)
   │   execute the smallest change / experiment that advances the goal
   │
   ├─▶ PreToolUse(Bash)  ── dead_lever_guard.py ── surfaces a re-run of a CLOSED lever  ── DETERMINISTIC
   │
   ├─▶ PostToolUse(Bash) ── bash_ledger.py ── append {cmd, exit, ok, signals} to        ── DETERMINISTIC
   │                        ~/GitHub/.claude/run/<session>.jsonl  (the run ledger)
   │
   ├─▶ PreToolUse(Write/Edit)  ── secret_scan.sh ── block writing secrets/.env/keys     ── DETERMINISTIC
   │
   └─▶ PostToolUse(Write/Edit) ── secret_scan.sh + changed_python_syntax.sh (py_compile) ── DETERMINISTIC
                              + metric_provenance.py ── HARD-block a report citing a
                                result artifact that does not exist on disk
   │
   ▼
/evidence  ── evidence_audit.py --ledger ── every metric/completion claim needs a nearby
   │          artifact AND, for "tests pass" claims, a real test invocation in the run ledger
   ▼
/gate-check ── promotion gate (DSR / PBO / reality-check / BH-FDR / bootstrap-CI at the
   │           honest family m, see contracts/promotion_gate.md) → assign a verdict
   ▼
registry/levers.yaml  +  research_ledger.md   ── the verdict is recorded; the lever is now
   │                                              paid for and will surface DO-NOT-RE-RUN
   ▼
/refute  ── adversarial self-review: try to falsify the result, run ≥1 cheap test,
   │         downgrade the claim if evidence is weak
   ▼
/ship-loop ── final gate, in order: git status · diff · syntax · focused tests · secret scan ·
   │          evidence_audit --strict --ledger · /refute audit · artifacts exist · reports updated
   ▼
/commit-research ── scripts/research_committer.py ── policy-driven, ONE commit per repo per
   │   SCOPE (hooks/commands/registry/scripts/docs/reports/…), per-repo checks before each commit,
   │   pre-staged protection, verbose message (Context/Changes/Evidence/Risk/Rollback + trailers:
   │     Task · Scope · Run-Class · Checks · Artifacts · Lever · Session). Governed by
   │   registry/repo_commit_policy.yaml. (/commit-constellation = lighter tier-ordered variant.)
   ▼
policy-gated push (only if auto_push AND HEAD==expected_branch; never --force/--no-verify)
   │
   ▼
git history = the durable research ledger
   query it:  git log --grep 'Lever: short-leg-cost'
   │
   ▼
Stop ── loop_guard.py ── block completion on staged secrets / workflow-dir TODO markers     ── DETERMINISTIC
        (+ completion-claim-without-evidence heuristic when LOOP_GUARD_STRICT=1)
```

## The determinism boundary

| Layer | Mechanism | Enforced? |
|---|---|---|
| Research state machine | `levers.yaml` + `research_session_loader` + `dead_lever_guard` + `/gate-check` | **Hard.** A verdict is paid once; closed levers re-surface; OPEN steps load every session. |
| Command evidence | `bash_ledger.py` (PostToolUse Bash) → run ledger consumed by `evidence_audit --ledger` | **Hard** (logging always on); the cross-check is advisory unless `--strict`. |
| Artifact provenance | `metric_provenance.py` | **Hard** for dangling-artifact references; seedless-RNG is advisory (`METRIC_PROVENANCE_STRICT=1`). |
| Secrets | `secret_scan.sh` (Pre+Post) + `loop_guard.py` staged-diff | **Hard** by default. |
| Syntax | `changed_python_syntax.sh` | **Hard** (py_compile only — not a test). |
| Commit discipline | `research_committer.py` (+ `constellation_commit.py`) | **Hard:** one repo + one scope per commit, pathspec-only staging, per-repo checks gate the commit, pre-staged protection, secret-abort, branch-gated push, no `--force`/`--no-verify`. Policy: `registry/repo_commit_policy.yaml`. Doctrine: [`git_as_research_ledger.md`](git_as_research_ledger.md). |
| The loop bodies | `/intent-check`, `/quant-loop`, `/verify-loop`, `/refute`, `/ship-loop` | **Advisory** — markdown SOP. The Stop guard backs them; completion-claim blocking is opt-in (`LOOP_GUARD_STRICT=1`). |

The loops are prompts, not state machines: their rigor is backed — not replaced —
by the hooks. Turn the soft guards hard for a session with:

```bash
export LOOP_GUARD_STRICT=1 METRIC_PROVENANCE_STRICT=1 DEAD_LEVER_STRICT=1
```

Each **Python** hook honours a `*_DISABLE=1` switch (`LOOP_GUARD_DISABLE`,
`METRIC_PROVENANCE_DISABLE`, `DEAD_LEVER_GUARD_DISABLE`, `RESEARCH_LOADER_DISABLE`,
`BASH_LEDGER_DISABLE` — exact names in [`../hooks/README.md`](../hooks/README.md)).
The two shell hooks (`secret_scan.sh`, `changed_python_syntax.sh`) are
intentionally not disableable.

## The run ledger

`bash_ledger.py` appends one JSON record per Bash call to
`~/GitHub/.claude/run/<session_id>.jsonl` (git-ignored). Each record carries the
command, exit code (when the harness exposes one), an `ok` flag, and detected
`signals` (`test-runner`, `pass-token`, `fail-token`). This is what makes
"the tests pass" checkable: `evidence_audit --ledger` reads the newest ledger,
prints `N commands, M test runs, K failed, U unverified`, and flags any test-pass
claim in a report when the ledger shows **no** test run, a test run that **failed**,
or test runs none of which recorded a pass. It is **ephemeral session evidence** —
the durable record is the commit-trailer history.

## Git as the research ledger

Every commit `constellation_commit.py` writes carries a trailer block, so the
research program is reconstructable from `git log` alone:

```
git log --all --grep 'Lever: multisleeve-hrp-book'   # every commit advancing a lever
git log --grep 'Session: <id>'                        # everything one session landed
git log --grep 'Task: short-leg-cost'                 # one task across repos
```

The lever registry holds the *verdict*; the commit trailers hold the *trail of
edits* that produced it. Together they make the research history queryable from
both ends. The full doctrine — the four ledgers, the commit message contract,
scope grouping, the auto-push rules, and the hard/advisory boundary — is
[`git_as_research_ledger.md`](git_as_research_ledger.md).

## See also

- [`git_as_research_ledger.md`](git_as_research_ledger.md) — the Git-as-ledger doctrine + committer.

- [`../contracts/expert_agent_contract.md`](../contracts/expert_agent_contract.md) — planning vs execution.
- [`../contracts/task_contract.md`](../contracts/task_contract.md) — per-task checklist.
- [`../contracts/promotion_gate.md`](../contracts/promotion_gate.md) — the verdict bar.
- [`../hooks/README.md`](../hooks/README.md) — every hook, its event, its effect.
- [`../commands/README.md`](../commands/README.md) — every command.
