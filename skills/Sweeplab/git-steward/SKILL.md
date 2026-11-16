---
name: git-steward
description: Git hygiene for SweepLab — ultra-granular commits with rich bodies, review commit quality, stage specific files, run commits so hooks fire, auto-push included. Use this skill for every commit: when the orchestrator finishes a logical unit of work, when /checkpoint runs, after any code change, after any documentation change. Enforces CLAUDE.md §11 ultra-granular policy. Never rewrites history, never force-pushes, never skips hooks.
---

# Git Steward

Enforce commit hygiene and execute the staging → commit → push cycle. Auto-push fires automatically via hook after every commit — this skill handles the commit; the push takes care of itself.

All risky git operations (reset --hard, force-push, rebase -i, clean -f) are denied — never attempt them.

---

## Ultra-granular mandate

**One file = one commit when possible.** This is the default. Break from it only when the files are truly inseparable (e.g. a test file and the source it tests, introduced together in the same logical unit).

**Never batch unrelated changes.** If the staging area contains files from two different concerns (e.g. a bug fix in `src/sdc.py` and an unrelated doc update in `docs/architecture.md`), split them into two commits before proceeding.

**Never commit "everything at once"** unless explicitly instructed. Always inspect `git diff --stat` before staging and ask: "can this be split?"

---

## Commit message standard

Every commit message has a **subject** and a **body**. The body is not optional for code changes.

### Subject line
```
<prefix>: <what changed and why, ≤72 chars>
```

Prefixes:

| Prefix | When |
|--------|------|
| `fix:` | Bug fix |
| `feat:` | New feature, new case, new capability |
| `refactor:` | Code restructure, no behaviour change |
| `test:` | New or modified tests |
| `docs:` | Documentation only |
| `infra:` | .claude/ hooks, skills, commands, settings |
| `skills:` | New or updated skills |
| `perf:` | Performance improvement with evidence |
| `chore:` | Maintenance (dependencies, gitignore, etc.) |
| `review[example]:` | Example execution review package |
| `scholar:` | sdc-scholar report |
| `notes:` | docs/notes/ additions |
| `params:` | Parameter change with empirical evidence |

### Body template

```
What:
  <One paragraph: what exactly changed and in which file(s). Be specific —
  name functions, line numbers, data structures changed.>

Why:
  <One paragraph: the motivation. What was wrong or missing? What test failed?
  What numerical evidence prompted this? What paper/theorem supports the choice?>

Evidence:
  <For numerical/parameter changes: the actual numbers.
   e.g. "dt=0.02 → diverged at snes_it=500+; dt=0.01 → stable, rel_err=1.4e-4"
   For code changes: which tests pass/fail before and after.
   For docs: what was stale and what is now correct.
   Omit for trivial mechanical changes (e.g. path rename).>

Related:
  <KI-XXX if resolving a known issue. Docs updated: yes/no. Tests affected: yes/no.>
```

**Bad commit messages (reject these):**
- `fix stuff`
- `update`
- `WIP`
- `various changes`
- `Co-authored-by: Claude`
- `Added X to Y` (passive voice, no why)

**Good examples:**
```
fix: correct VI bounds not enforced at dt>0.02 — snes_max_it raised to 500

What:
  src/sdc.py:_vi_bounds() — added fresh bounds call at top of every sweep
  method (not just sweep start). Affects _execute_sweep, _sweep_loop, _sweep.

Why:
  Bounds were only fetched at the start of the first sweep. At dt>0.02,
  Newton needed >100 iterations per step, causing bounds to go stale and the
  constraint to be violated on later iterations. Free boundary detection showed
  max violation 3.1e-3 at S*=81.

Evidence:
  Before: max(g−u) = 3.1e-3, American put price 6.051 (CRR: 6.090, err=0.6%)
  After:  max(g−u) = 8.4e-7, American put price 6.090 (CRR: 6.090, err=1.7e-5)
  All 7 core invariants pass.

Related: KI-003. Docs updated: yes (known_issues.md). Tests affected: test_bs_american.py.
```

```
params: raise snes_max_it 200→500 for VI at dt≥0.02

What:
  cases/bs_greeks_american.py:_price_american_vi() — snes_max_it parameter.

Why:
  Empirically, vinewtonrsls needs ~350 Newton iterations per time step when
  dt=0.02 and the free boundary moves significantly. 200 was causing premature
  convergence to an incorrect constraint-violating solution.

Evidence:
  dt=0.02, snes_max_it=200: price=5.98, violation=4.2e-2 (FAIL)
  dt=0.02, snes_max_it=500: price=6.09, violation=9e-7  (PASS)

Related: KI-002.
```

---

## Commit mode — procedure

### Step 1 — Inspect the changeset

```bash
git status
git diff --stat
git diff           # read the full diff for code changes
```

Identify every logical unit in the changeset. If there are multiple units, plan the split before staging anything.

### Step 2 — Test (if code changed)

If `src/`, `cases/`, or `tests/` files are in the changeset:
```bash
source /Users/omarkhalil/Documents/Universidad/ImperialCollege/Project/programming/venv-firedrake/bin/activate
pytest tests/test_bs_american.py -v --tb=short
```
Do not commit if core tests fail.

### Step 3 — Stage specific files

```bash
git add <explicit file paths>   # never git add -A or git add .
git status                      # confirm staged set matches the single logical unit
```

### Step 4 — Write the commit message

For every change in `src/`, `cases/`, `tests/`, or significant `docs/`:
- Fill in the full body template above
- Evidence is mandatory for parameter changes and numerical changes

For mechanical changes (path renames, .gitignore, dependency bumps):
- Subject line only, no body required

### Step 5 — Commit

```bash
git commit -m "$(cat <<'EOF'
<prefix>: <subject>

What:
  <...>

Why:
  <...>

Evidence:
  <...>

Related:
  <...>
EOF
)"
```

`pre_commit_gate.py` (PreToolUse) and `post_commit_doc_tracer.py` (PostToolUse) fire automatically. `auto_push.py` (PostToolUse) fires automatically — do not push manually.

### Step 6 — Handle gate rejection

If `pre_commit_gate.py` blocks the commit, parse the violation and surface it. Repair the issue and retry as a new commit. Never use `--no-verify`.

### Step 7 — Report

```bash
git log -1 --oneline
```

Return: `Committed <sha> — "<subject>"` and confirm whether tests passed.

---

## Review mode

Given one or more recent commit SHAs or messages, check each against:
1. Ultra-granular? (one logical unit per commit)
2. Subject line ≤ 72 chars, prefix correct?
3. Body present for code/numerical changes?
4. Evidence present for parameter/numerical changes?
5. No AI attribution?
6. No passive voice ("Added X")? No vague scope ("various changes")?

```bash
git log --oneline -10
git show <sha> --stat
```

Output per commit:
```
[<sha>] <subject>
  Quality:  PASS | FAIL
  Issues:   <list, or "none">
  Suggest:  <improved message if FAIL>
```

Summary: `N commits reviewed, M pass, K fail.`

---

## Invariants

- Never `git reset --hard`, `git checkout -- .`, `git clean -f`
- Never `git push --force` or `git rebase -i`
- Never `--no-verify`
- Never push directly — `auto_push.py` handles it
- Never rewrite history — rollbacks are forward-only commits
- Never commit without reading the diff first
