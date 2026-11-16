---
name: sdc-doc-tracer
description: Post-commit documentation maintenance for SweepLab — update investigation logs, known issues, and cross-references so the repository remains self-contained after every change. Use this skill after every commit, when /refresh-docs is invoked, or whenever the user asks to update or check the documentation state. Trigger automatically after any git commit completes.
---

# SDC Doc Tracer

Maintain SweepLab's documentation as a live technical record. Every commit must leave a documentation trace. The repository must be self-contained — future sessions should understand the current state from code + docs alone.

Never modify source code. Write documentation only.

## Step 1: Read the last commit

```bash
git log -1 --format="%H %s"
git diff HEAD~1 HEAD --stat
git diff HEAD~1 HEAD
```

## Step 2: Classify the change

| Category | What changed |
|----------|-------------|
| **mathematical/numerical** | PDEs, formulations, convergence behaviour, parameters |
| **infrastructure** | Solver architecture, I/O, lab API, preconditioners |
| **test** | New or modified tests |
| **case** | New or modified case scripts |
| **documentation** | docs/ changes — log the entry only, do not recurse |
| **configuration** | settings, hooks, agent/skill definitions |

## Step 3: Update documentation

### For mathematical/numerical changes

1. Append to `docs/investigation_logs/YYYY-MM-DD_session.md` (create if absent):

```markdown
## [HH:MM] [Brief description]

**Context:** [what problem was being worked on]
**Change:** [files modified and how]
**Motivation:** [why this change]
**Result:** [outcome — tests pass/fail, numerical results]
**Implications:** [what this means going forward]
**Related:** [links to relevant docs, issues, or prior entries]
```

2. Check `docs/known_issues.md`:
   - Does this commit resolve a known issue? Update its status and add a Resolved date.
   - Does it introduce a new limitation? Add an entry using the format below.

3. If empirical results changed:
   - `docs/american_option_methods.md` — if method comparison data changed
   - `docs/numerical_validation.md` — if validation data changed

### For infrastructure / configuration changes

One-line entry in today's investigation log:
```markdown
## [HH:MM] Infrastructure: [brief description]
```

If module structure changed, check `docs/architecture.md` for staleness.

### For test changes

Brief entry noting what tests were added/modified and why.

### For case changes

Entry noting the new case and purpose. Check if `docs/architecture.md` needs updating.

## Step 4: Commit documentation

Each documentation file gets its own commit:

```bash
git add docs/investigation_logs/YYYY-MM-DD_session.md
git commit -m "docs: update investigation log — [brief description]"

git add docs/known_issues.md
git commit -m "docs: update known issues — [what changed]"
```

One file = one commit. Never batch documentation commits.

## Step 5: Check cross-references

Quick scan for broken references:
- Does CLAUDE.md reference files that still exist?
- Do docs/ files reference source files that still exist?
- Are there docs/ entries for recently added modules?

Flag broken references. Only fix them if the fix is trivial and obvious.

## Formats

### Investigation log entry
```markdown
# Investigation Log — YYYY-MM-DD

## [HH:MM] [Title]

**Context:** ...
**Change:** ...
**Motivation:** ...
**Result:** ...
**Implications:** ...
**Related:** ...
```

### Known issue entry
```markdown
### [Issue Title]

**Status:** open | resolved | wontfix | investigating
**Severity:** critical | high | medium | low
**Discovered:** YYYY-MM-DD
**Resolved:** YYYY-MM-DD (if applicable)

**Description:** ...
**Reproduction:** ...
**Impact:** ...
**Workaround:** ...
**Resolution:** ...
```

## Scope

Documentation only. No source code modifications. No speculative entries — only record what was actually changed and observed.
