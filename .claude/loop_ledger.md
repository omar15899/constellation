# Loop Ledger

Append an entry for serious code/research sessions. Skip tiny tasks. This is the
persistent record of how the user's planning constraints were met, loop by loop.

---

## Template

```
## YYYY-MM-DD HH:MM — <task>

### User request
...

### Explicit requirements
- ...

### Inferred intent
- ...

### User-owned planning decisions
- ...

### Claude-owned execution decisions
- ...

### Definition of verified success
- ...

### Loops run
| loop | action | evidence | refutation considered | outcome |
|---|---|---|---|---|

### Final evidence table
| claim | artifact/source | check performed | result | residual caveat |
|---|---|---|---|---|

### Remaining caveats
- ...
```

---

## 2026-06-23 — Expert-directed agentic workflow upgrade

### User request
Upgrade the existing Claude Code workflow in `~/GitHub/.claude/` into a
semi-deterministic, expert-directed agentic coding system, explicitly inspired
by Anthropic's "Agentic coding and persistent returns to expertise" report.

### Explicit requirements
- Inspect existing setup before editing; do not overwrite blindly (Phase 0).
- Encode the human (planning) / Claude (execution) division of labour.
- Add a deterministic task contract.
- Add loop commands: verify-loop, intent-check, refute, evidence, quant-loop,
  ship-loop, review-claude-system (+ debug-metric).
- Add deterministic hooks: secret_scan, changed_python_syntax, evidence_audit,
  loop_guard, and wire them in settings.json.
- Add a persistent loop ledger.
- Validate (syntax checks, manual hook runs, a negative secret test).
- Do not commit without explicit approval.

### Inferred intent
- Make verified success require hard evidence; block "done" without proof.
- Turn the user's quant methodology into persistent repo rules.

### User-owned planning decisions
- The four report principles; what counts as verified success; quant invariants
  (no survivorship bias, no lookahead, alpha vs beta); whether to commit.

### Claude-owned execution decisions
- Hook implementation (stdin file_path + git staged diff; python for portability
  on macOS); the `/loop` → `/verify-loop` rename to preserve the scheduler; the
  loop_guard default posture (hard checks block; completion heuristic opt-in).

### Definition of verified success
- All workflow files created without clobbering existing ones; shell hooks pass
  `bash -n`; python hooks pass `py_compile`; secret_scan exits 2 on a fake
  secret and 0 when clean; evidence_audit flags an unsupported claim; settings
  wires the hooks; nothing committed.

### Loops run
| loop | action | evidence | refutation considered | outcome |
|---|---|---|---|---|
| 1 | Phase 0 inspect | tree + reads (no git, no settings.json, no clashes) | wrong target dir? | proceed at `~/GitHub/.claude/` |
| 2 | author hooks/contracts/commands/ledger | files created | name clash on `/loop` | renamed to `/verify-loop` |
| 3 | wire settings.json + validate | see final evidence table | hooks no-op / self-trip / brick Stop | resolved |

### Final evidence table
| claim | artifact/source | check performed | result | residual caveat |
|---|---|---|---|---|
| 16 workflow files added, zero overwrites | `ls -l` of contracts/commands/hooks | Phase 0 inspect: none pre-existed | created clean | `/loop`→`/verify-loop` to preserve scheduler |
| shell hooks parse | secret_scan.sh, changed_python_syntax.sh | `bash -n` | OK | — |
| python hooks compile | evidence_audit.py, loop_guard.py | `python3 -m py_compile` | OK | — |
| settings.json valid, wires Pre/Post/Stop | settings.json | `json.load` + read | valid | fires only for sessions rooted at ~/GitHub |
| secret_scan blocks secrets, no false positives | driver: 7 block + 5 clean | exit codes | all PASS | no entropy detector (SHA roots would FP) |
| secret_scan prevents the write (PreToolUse) | driver content case | exit 2 on pending content | PASS | — |
| python syntax gate | driver: valid/broken | exit 0/2 | PASS | — |
| evidence_audit flags unsupported claims | driver: bad/good report | exit 1/0 | PASS | advisory unless `--strict` |
| loop_guard blocks staged secrets + workflow TODOs | driver: 7 LG cases incl. scope | exit codes | PASS | completion gate opt-in via LOOP_GUARD_STRICT |
| nothing committed / no marker left behind | not a git repo; probe cleanup | grep markers + `git` absent | clean | ~/GitHub intentionally not git |

### Remaining caveats
- `~/GitHub/` is not a git repo, so the staged-diff paths of secret_scan /
  loop_guard are inert at the root; they enforce via the written-file path and
  become full when governing a real repo.
- The completion-language heuristic in loop_guard is advisory unless
  `LOOP_GUARD_STRICT=1` — it depends on prose and must not brick every Stop.
- The commands are prompt-discipline: they instruct Claude, they are not
  deterministically enforced. Only the hooks are deterministic.

---

## 2026-06-23 — Research-grade workflow upgrade (lever registry + gate + provenance + loader)

### User request
Keep refining the `.claude` AI structure (hooks etc.) so it genuinely serves
*research*, not just code safety. After diagnosis the user chose ALL FOUR
refinements with a BALANCED enforcement posture.

### Definition of verified success
- A lever registry seeded from the real research history, machine-readable
  without PyYAML; a promotion-gate contract + `/gate-check` recording verdicts;
  a metric-provenance hook; a SessionStart research-loader + dead-lever guard;
  all wired in settings.json and validated; nothing claimed without evidence.

### User-owned planning decisions
- Which refinements to build (all four); the enforcement posture (balanced:
  hooks block only hard signals, methodology advisory); the promotion bar itself.

### Claude-owned execution decisions
- Stdlib hand-parse of levers.yaml (`_levers.py`) to honour the no-PyYAML
  convention; `rerun_guard` as an opt-in per-lever field so the dead-lever guard
  is precise; metric_provenance scoped to filesystem existence (no overlap with
  evidence_audit's prose audit); SessionStart via `additionalContext` JSON.

### Loops run
| loop | action | evidence | refutation considered | outcome |
|---|---|---|---|---|
| 1 | reconstruct prior session + inspect on-disk system | reads of contracts/commands/hooks/settings; git clean | wrong target / stale memory | confirmed: all prior files committed |
| 2 | build levers.yaml + research_ledger.md + _levers.py | `_levers.py` → 12 levers, 3 strategies, verdicts correct | yaml unparyable w/o PyYAML | hand-parser passes |
| 3 | promotion_gate contract + /gate-check | files created; bar matches ltr-promotion-gate memory | bar relaxed silently | contract forbids lowering m |
| 4 | metric_provenance.py | 8/8 test cases (existing/missing/glob/seed/strict/disable) | false positives on examples | scoped out .claude/ + globs |
| 5 | session loader + dead_lever_guard + settings | loader JSON valid; guard advisory/strict/no-FP; settings 4 events | guard bricks legit re-run | advisory by default, strict opt-in |

### Final evidence table
| claim | artifact/source | check performed | result | residual caveat |
|---|---|---|---|---|
| levers.yaml parses w/o PyYAML | `hooks/_levers.py` run | 12 levers, verdict histogram | PASS | hand-parser covers only this file's shape |
| metric_provenance blocks dangling artifact refs | test_provenance.sh | 8 cases incl. strict/disable/glob | all PASS | only hard data-suffix/results-named paths |
| dead_lever_guard surfaces dead-lever re-runs | test_session.sh | advisory/strict/2×no-FP | all PASS | matches only levers with `rerun_guard` |
| SessionStart loader emits valid additionalContext | test_session.sh | json.load + content | PASS (2262 chars) | brief grows with the registry |
| settings.json wires SessionStart/Pre/Post/Stop | settings.json | json.load + structure | 4 events PASS | fires only for sessions rooted at ~/GitHub |
| all new python compiles | py_compile | 4 hooks | PASS | — |

### Remaining caveats
- Verdicts in levers.yaml are seeded from auto-memory (point-in-time); the
  ResearchLab paths in the promotion-gate contract should be verified live before
  asserting.
- `/gate-check` writing to levers.yaml is prompt-discipline, not deterministic —
  the registry is only as current as the discipline of recording verdicts.
- Nothing committed yet (awaiting approval).

---

## 2026-06-28 — Git-as-research-ledger layer (policy-driven committer)

### User request
Add a robust "Git as historical research ledger" layer: granular per-repo/per-scope
commits, verbose traceable messages, controlled auto-push; each repo with its own
`.git` committed independently without mixing unrelated changes; `git log`
reconstructs what/why/evidence/checks/artifacts. Not a "commit all" — safe,
auditable, deterministic. Verify adversarially before committing.

### Definition of verified success
- `docs/git_as_research_ledger.md`, `registry/repo_commit_policy.yaml`,
  `scripts/research_committer.py`, `commands/commit-research.md`,
  `hooks/commit_guard.py`, doc integration; all adversarial repros pass; granular
  commits with parseable trailers; pushed to constellation/main only if checks pass.

### Loops run
| loop | action | evidence | refutation considered | outcome |
|---|---|---|---|---|
| 1 | inspect state + discover 19 git repos | branches/dirty/pre-staged table | stale assumptions | 6 sub-repos pre-staged, 3 on feature branches → only constellation is this task's surface |
| 2 | build policy + committer + command + validator + docs | files created; YAML parser + scope grouping verified | parser double-nests lists; -uall collapse | fixed; first suite 19/19 |
| 3 | 4-agent adversarial workflow (wb7nk2kaj) | 8 HIGH + 6 MED/LOW real findings | secret bypass via binary/flush-list/typo/glob; real-index residue | all fixed; second suite 16/16 |
| 4 | apply granular commits + record + push | hashes below; both suites 35/35 | generic subjects | reset, redid with human subjects |

### Final evidence table
| claim | artifact/source | check performed | result | residual caveat |
|---|---|---|---|---|
| committer enforces all hard rules | `scratchpad/verify_committer.sh` | 19 repros | 19/19 PASS | — |
| adversarial findings fixed | `scratchpad/verify_fixes2.sh` | 16 repros (flush-list, byte-secret, literal pathspec, fail-closed checks, name-collision, real-index residue, commit_guard fail-closed) | 16/16 PASS | — |
| granular per-scope commits, human subjects, trailers | `git log d41f684..e0ab8aa` | 5 commits, each one scope | PASS | — |
| dry-run safe on real repos | dry-run vs ~/GitHub (agent end_to_end PASS) | no mutation; pre-staged sub-repos ABORT | PASS | — |

### Commits (this task — `git log --grep 'Task: research-git-ledger'`)
- `d41f684` add per-repo commit policy for the git-as-ledger layer (registry)
- `7cef3b6` add the policy-driven research committer (scripts)
- `054b8ae` add the commit_guard validator and document it (hooks)
- `d6dce69` add the /commit-research command and index the git-ledger commands (commands)
- `e0ab8aa` document Git as the research ledger (docs)
- (this ledger update — docs scope — committed last, then pushed to constellation/main)

### Remaining caveats
- The stdlib YAML parser covers the policy file's subset (maps, block + flow lists,
  quoted-value comment stripping, tab→space); it is not a general YAML implementation.
- `secret_scan` is a pattern/entropy-free scan over staged blob bytes (no generic
  entropy detector — QuantOS SHA roots would false-positive); novel secret formats
  not in the token regex would pass.
- Sub-repos with pre-existing pre-staged dirt were intentionally NOT committed (not
  this task); the committer correctly ABORTS them until `--include-prestaged`.
