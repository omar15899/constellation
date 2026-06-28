# Research-Modes Contract

*Constellation plane. Three postures — `casual`, `implementation`, `research_strict`
— that name how strict the standing checks are for a piece of work, and which real
environment flags each turns on. The mode names are the `--mode` choices of
[`../scripts/record_lever_verdict.py`](../scripts/record_lever_verdict.py); the env
flags are the ones the hooks actually read (verified in source, listed below). This
contract invents no new switches — it composes existing ones.*

## The standing posture

The constellation's default posture is: **hooks block only on hard, objective,
dangerous signals; methodology heuristics are advisory and opt-in strict.** Each
hook reads its own `*_STRICT` env var to promote its advisory signal to a hard
block, and a `*_DISABLE` var to switch off entirely. The modes below are just named
bundles of those flags.

### Real env flags (from the hook sources)

| Hook | Advisory signal | Strict flag (→ block) | Disable flag |
|---|---|---|---|
| [`../hooks/loop_guard.py`](../hooks/loop_guard.py) | completion language with no concrete evidence token | `LOOP_GUARD_STRICT` | `LOOP_GUARD_DISABLE` |
| [`../hooks/metric_provenance.py`](../hooks/metric_provenance.py) | seedless RNG in a research `.py` | `METRIC_PROVENANCE_STRICT` | `METRIC_PROVENANCE_DISABLE` |
| [`../hooks/dead_lever_guard.py`](../hooks/dead_lever_guard.py) | command re-runs a closed (REFUTED/HOLD) lever | `DEAD_LEVER_STRICT` | `DEAD_LEVER_GUARD_DISABLE` |
| [`../hooks/commit_guard.py`](../hooks/commit_guard.py) | broad claim in message / seedless RNG staged | `COMMIT_GUARD_STRICT` | *(none — validator)* |

`loop_guard` and `metric_provenance` also keep their HARD signals (staged secrets,
`.env`, actionable TODO markers, a report referencing a missing artifact) **always
on**, independent of mode. The strict flag only governs the *advisory* tier.

## The three modes

### `casual`
Quick, exploratory work. All four hooks stay advisory (no `*_STRICT` set); hard
signals still fire. Verdict recording via `record_lever_verdict.py --mode casual`
applies no extra metric requirement. Use for scratch and diagnostics that make no
durable claim.

Flags: *(none set)* — relies on the default advisory posture.

### `implementation` (default)
Building governed code/infrastructure. The default `--mode` of
[`../scripts/record_lever_verdict.py`](../scripts/record_lever_verdict.py). Hard
signals enforced; advisory signals warn but do not block. This is the everyday
posture for committing through `/commit-research`.

Flags: *(none set)* — same advisory posture as `casual`; the distinction is intent
and the verdict-recording path, not extra strictness.

### `research_strict`
Recording a real research verdict that must withstand scrutiny. Promote every
advisory methodology heuristic to a hard block by exporting all four strict flags:

```bash
export LOOP_GUARD_STRICT=1          # completion-without-evidence blocks
export METRIC_PROVENANCE_STRICT=1   # seedless RNG blocks
export DEAD_LEVER_STRICT=1          # re-running a closed lever blocks
export COMMIT_GUARD_STRICT=1        # broad claim / seedless RNG in a commit blocks
```

And record verdicts with `record_lever_verdict.py --mode research_strict`, which
**refuses** to write a `CONFIRMED` verdict unless the four-bar metrics
(`sharpe`, `dsr`, `pbo`, `ci_low`, `p_bh`) are supplied — the bar defined in
[`promotion_gate.md`](promotion_gate.md). Evidence-artifact existence is checked
unless `--external` is passed.

## What each mode guarantees

| Mode | Hard signals | Advisory → block | `CONFIRMED` needs four bars |
|---|---|---|---|
| `casual` | yes | no | no |
| `implementation` | yes | no | no |
| `research_strict` | yes | yes (all four `*_STRICT`) | yes |

## Related enforcement

- The SessionStart brief [`../hooks/research_session_loader.py`](../hooks/research_session_loader.py)
  injects standing lever verdicts so a session never re-runs paid-for work
  (`RESEARCH_LOADER_DISABLE` to silence).
- The Bash run ledger [`../hooks/bash_ledger.py`](../hooks/bash_ledger.py) records
  command provenance (`BASH_LEDGER_DISABLE` to silence).
- The promotion bar itself: [`promotion_gate.md`](promotion_gate.md), recorded via
  [`../commands/gate-check.md`](../commands/gate-check.md) into
  [`../registry/levers.yaml`](../registry/levers.yaml) and
  [`../research_ledger.md`](../research_ledger.md).
- Commit/push strictness folds into the committer — see
  [`commit_policy.md`](commit_policy.md).
