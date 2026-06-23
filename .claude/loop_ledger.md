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
