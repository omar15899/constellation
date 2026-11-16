---
name: git-history-reviewer
description: Reconstruct, critically review, and document the complete development history of a Git repository, producing structured Markdown reports (main history review + optional PR-style sub-report) and proposed commit-message improvements. Use this skill whenever the user asks to "review the git history", "audit the commit log", "rewrite commit messages", "document the project history from git", "produce a development timeline", "summarise what happened day by day in this repo", "audit commit quality", "write a project retrospective from git", "generate a changelog from history", "make a development diary from commits", "PR review of this branch", "review this pull request from git", "auditar el historial git", "haz un PR review", or whenever the request requires turning `git log` into a narrative artefact, an onboarding document, a merge-gate decision, or a quality assessment of past commits. Default mode is strictly read-only — never rewrite history unless the user explicitly authorises it and confirms the operation. Treat Git as the single source of truth and do not invent context the commits do not support.
license: Reusable. Agent-agnostic. Designed to run under any AI coding assistant (Claude Code, Copilot-style agents, Codex-style agents, custom orchestrators) that can execute shell commands and read/write files.
---

# Git History Reviewer

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

A portable skill for inspecting the Git log of a repository, critically reviewing the commit history, proposing improved commit messages, and producing complete Markdown reports — a main historical review and an optional PR-style sub-report tailored to merge-gate decisions.

This skill is **agent-agnostic**. It assumes only that the executing agent can:

- run shell commands (`git`, `cat`, `wc`, etc.),
- read and write files,
- and reason over text.

It makes **no assumption about which AI assistant is running it**. There are no Claude-specific tool names, no IDE-specific bindings, no proprietary APIs.

---

## 1. Mission

Given a Git repository, reconstruct its complete development history **purely from the Git log** and produce:

1. A critical review of the commit history.
2. Proposed improvements for weak commit messages.
3. (Only on explicit request) a proposed cleaned-up history — never applied automatically.
4. A complete Markdown report following the canonical structure in [`references/report_template.md`](references/report_template.md).
5. A chronological day-by-day development narrative inferred from commits and diffs.
6. (Optional) a PR-style sub-report following [`templates/pr_review_template.md`](templates/pr_review_template.md), validated against [`tests/test_template_contract.md`](tests/test_template_contract.md). Triggered when the user asks for a PR review of the analysed range, a merge-gate decision, a "review this PR" / "haz un PR review", or whenever a target audience (e.g. a manager or reviewer) needs the severity-graded findings format.

The Git log is the **canonical source of truth**. The agent must not import context from external systems (issue trackers, chat logs, design docs) unless the user explicitly provides it.

---

## 2. Hard rules (non-negotiable)

These rules exist because Git history rewriting is destructive and inferred narratives are seductive. Both fail loudly when carelessly applied.

1. **Default mode is read-only.** Producing the report, the analysis, and the proposed message improvements never requires mutating the repository. If a step would mutate state, stop and ask.
2. **Never rewrite history without explicit user authorisation.** A request like "review the history" is *not* authorisation to rewrite. The user must say something equivalent to "now apply the rewrite" *and* confirm after a dry-run plan.
3. **Never use `--force`, `--force-with-lease`, `git reset --hard`, `git push --force`, `git filter-repo`, `git filter-branch`, or `git rebase -i`** unless the user has authorised the specific operation in the current session and the working tree is clean.
4. **Never invent business motivation.** The agent may infer "this looks like feature work on the auth module" from filenames and diffs, but must not write "the team prioritised auth because of customer X" unless the commits literally say so.
5. **Preserve hashes and dates verbatim.** Every claim about a commit must reference its short or full hash. Dates must come from `git log`, not be reconstructed.
6. **Mark uncertainty.** When intent is inferred, use phrases like *appears to*, *suggests*, *is consistent with*, *cannot be determined from Git alone*. Never feign certainty.
7. **Do not bundle the report's findings with code changes.** The report is documentation. If the user wants it committed, that is a separate, explicit, non-rewriting action.

If any of these rules conflict with what the user just asked, surface the conflict and wait.

---

## 3. Inputs the skill expects

| Input | Required? | Default |
|---|---|---|
| Path to a Git repository | yes | current working directory |
| Commit range to analyse | no | full history reachable from `HEAD` |
| Commit message style preference | no | infer from existing history; otherwise plain descriptive |
| Output directory | no | `./` (root of repo); or `docs/` / `reports/` if those exist |
| Permission to rewrite history | no | **denied by default** |
| Permission to write the report into the repo | no | yes (creating files in the working tree, *not* committing) |

When invoked, ask the user only for what is genuinely missing. Do not interrogate them for things that have a sensible default.

---

## 4. Outputs the skill produces (Markdown by default)

Always produced (read-only, Markdown):

1. **`git-history-review.md`** — the complete human-readable report. Structure is fixed; see [`references/report_template.md`](references/report_template.md).
2. **`commit-message-improvements.md`** — compact list of every proposed message improvement. Format in [`references/improvements_file_format.md`](references/improvements_file_format.md).

Optional (only on user request):

3. **`pr_review.md`** — PR-style sub-report of the analysed range, with severity-graded findings and a final merge-gate decision. Built from [`templates/pr_review_template.md`](templates/pr_review_template.md). Validated against [`tests/test_template_contract.md`](tests/test_template_contract.md). When emitted, section 8 of the main report links to it.
4. **`git-history-analysis.json`** — machine-readable intermediate representation. Schema in [`references/intermediate_schema.md`](references/intermediate_schema.md).
5. **A proposed cleaned-history plan** as section 9 of the main report. Never applied.
6. **An actual rewrite of history** — only after explicit, repeated, in-session authorisation.

Recommended output paths (pick the layout that already exists in the repo; do not invent one):

| Output | Default | Alt (when `docs/` exists) | Alt (dated reports) |
|---|---|---|---|
| Main report | `git-history-review.md` | `docs/git-history-review.md` | `reports/git-history-review-YYYY-MM-DD.md` |
| Improvements | `commit-message-improvements.md` | `docs/commit-message-improvements.md` | `reports/commit-message-improvements-YYYY-MM-DD.md` |
| PR review | `pr_review.md` | `docs/pr_review.md` (or `docs/pr_review_<range>.md`) | `reports/pr_review-YYYY-MM-DD.md` |
| Analysis JSON | `git-history-analysis.json` | `docs/git-history-analysis.json` | `reports/git-history-analysis-YYYY-MM-DD.json` |

All Markdown reports use real Markdown — heading hierarchy, GitHub-flavoured tables, and fenced code blocks. Do not use ASCII separator art (no `=====`, no `-----` outside table delimiters).

### When to emit the PR-review sub-report

Emit `pr_review.md` whenever **any** of the following holds:

- The user explicitly asks for a "PR review", "review of this PR", "merge-gate review", "haz un PR review", "revisión de este PR".
- The user asks for a review of a specific GitHub PR by number (`#123`); fetch the PR via `gh pr view` if available, otherwise reconstruct from `git log <base>..<head>`.
- The analysed range cleanly maps to a single feature branch or pull request and the user wants a merge-gate decision.
- The user mentions a downstream audience that expects the format (e.g. "my manager wants this", "for the review meeting").

When the request is purely a historical retrospective (no merge-gate intent), do not emit `pr_review.md` — section 8 of the main report already covers the recommended-actions surface.

---

## 5. Recommended staged workflow

Run these stages in order. Each stage produces structured intermediate data that the next stage consumes. This staging is the single most important reason the final report is reliable: skipping ahead to "write the report" causes hallucination.

### Stage 1 — Repository safety check

Before reading anything semantically, characterise the repository.

```sh
git rev-parse --is-inside-work-tree           # is this a git repo?
git rev-parse --show-toplevel                 # absolute repo path
git branch --show-current                     # current branch
git status --porcelain                        # working tree clean?
git remote -v                                 # any remotes?
git config --get-all remote.origin.url        # origin URL
git rev-list --count HEAD                     # total commit count
git log -1 --format='%H %ai %an' HEAD         # tip commit identity
```

Record: repo path, current branch, clean/dirty, remote presence, whether the branch is published (`git rev-parse --abbrev-ref --symbolic-full-name @{u}` succeeds), and the head commit metadata.

If the repository is dirty, the report can still be produced (analysis is read-only), but **flag this in the report's preamble**. If the user then asks to rewrite history, refuse until the working tree is clean.

If the branch appears to be published or shared (has an upstream, or has been pushed), record this prominently. **Never rewrite published history without explicit, named authorisation from the user.**

### Stage 2 — Git log extraction

Extract the canonical view of the history. Build the intermediate dataset, do not write the report yet.

Recommended command set, in approximate order of cost:

```sh
git log --oneline --no-merges                                 # compact overview
git log --pretty=format:'%H%x09%ai%x09%an%x09%ae%x09%s'       # tab-separated metadata
git log --shortstat                                           # per-commit summary stats
git log --numstat --format='COMMIT:%H'                        # files + line counts per commit
git log --name-status --format='COMMIT:%H'                    # files + add/modify/delete per commit
git log --merges --oneline                                    # merge structure
```

Optional, expensive — only for commits flagged as important during quality assessment:

```sh
git show --stat <hash>
git show <hash>            # full patch
git log -p -1 <hash>
```

Group the resulting commit objects by calendar day using the **author date** in the repository's local timezone unless the user requests otherwise. Document the chosen timezone in the report preamble.

Persist the extracted data into the intermediate representation defined in [`references/intermediate_schema.md`](references/intermediate_schema.md).

### Stage 3 — Commit quality assessment

For every commit, score the message quality and tag any issues. Use the rubric in [`references/commit_quality_rubric.md`](references/commit_quality_rubric.md).

Each commit gets:

- `quality`: one of `Excellent`, `Good`, `Acceptable`, `Weak`, `Poor`.
- `issues`: zero or more tags from the rubric (e.g. `vague`, `mixed_concerns`, `mismatch_with_diff`, `missing_rationale`, `too_broad`, `too_narrow`, `inconsistent_style`).
- `improvable`: boolean; whether a better message can be proposed from the diff alone.

Do not force Conventional Commits. Detect whether the repository already uses a particular style (Conventional Commits, imperative Git style, freeform descriptive, project-specific) and adopt it for any proposed rewrites.

### Stage 4 — Commit message improvement

For every commit with `improvable = true`, propose:

- a `suggested_title` (always),
- optionally a `suggested_body` for commits whose changes deserve explanation,
- a `rationale` for the suggestion,
- a `confidence` (`High`, `Medium`, `Low`),
- the list of `affected_files`.

Constraints:

- Proposed messages must be derivable from the diff and the original message. Do not invent product context.
- Preserve the original meaning. If the original is wrong (message contradicts the diff), say so explicitly in the rationale and propose a message consistent with the diff, marked `confidence: Medium` or `Low`.
- Match the project's existing style. If the project uses Conventional Commits, keep the type prefix; if not, do not impose one unless the user requested it.
- Distinguish between *title-only* improvements (the subject line is enough) and *full* improvements (a body is justified by the diff size or complexity).

See [`examples/good_vs_bad_messages.md`](examples/good_vs_bad_messages.md) for concrete patterns.

### Stage 5 — Daily development history

Group the analysed commits by calendar day. For each day, build:

- ordered list of commits (`short_hash` `time` `subject`),
- a narrative paragraph in plain English,
- a list of changed areas (directories or modules, derived from file paths),
- an inferred purpose (cautious),
- a development interpretation (how the commits relate — scaffold→implementation→test→cleanup, etc.),
- explicit uncertainties.

Cautious language is mandatory. The day-by-day narrative is the easiest place to slip into hallucination; resist.

### Stage 6 — Final Markdown report generation

Render the main report **exactly** in the structure of [`references/report_template.md`](references/report_template.md): same heading hierarchy, same section order, same table column sets. Do not reorder sections, rename headings, or invent new ones.

Section 9 (cleaned history plan) is conditional: include with content only when useful or when the user requested a rewrite plan; otherwise the section contains a single line *Not applicable.*

If the request triggers a PR review (see "When to emit the PR-review sub-report" above), Stage 6 also renders `pr_review.md` from [`templates/pr_review_template.md`](templates/pr_review_template.md). The PR review must pass every item in [`tests/test_template_contract.md`](tests/test_template_contract.md) before being saved. Section 8 of the main report links to the PR review file.

Before producing any final file, run through the pre-publish checklist in [`assets/pre_report_checklist.md`](assets/pre_report_checklist.md).

---

## 6. Intermediate representation

Building an intermediate structured dataset before writing the report is required. It separates *analysis* from *prose*, which prevents narrative-driven invention.

The intermediate object contains:

- repository metadata (path, branch, remotes, head)
- branch metadata (current, upstream, published?)
- working tree status (clean/dirty + list)
- commit list (full metadata)
- per-commit file changes (name-status)
- per-commit stats (numstat)
- per-commit inferred intent (string + confidence)
- per-commit quality score and issue tags
- daily groups (date → ordered commits)
- daily narrative blocks (drafted before final prose)
- proposed message improvements
- final report (string, only at the end)

Full JSON shape: [`references/intermediate_schema.md`](references/intermediate_schema.md). Persisting this object as `git-history-analysis.json` is optional and only on user request — but the agent should still build it in memory.

---

## 7. Commit message styles

The skill supports four output styles for proposed rewrites, listed in order of preference when the project shows no clear convention:

1. **Project-specific style** — if the existing history shows a clear convention (most messages start with `[ticket-id]`, all use a specific verb pattern, etc.), match it.
2. **Imperative mood Git style** — the canonical convention: subject line in the imperative ("Add", "Fix", "Refactor"), max ~72 chars, optional body separated by blank line, body wrapped at ~72 chars.
3. **Conventional Commits** — `<type>(<scope>): <subject>` with types `feat | fix | refactor | docs | test | chore | perf | build | ci | style | revert`. Use only if the existing history already follows it, or the user requests it.
4. **Plain descriptive** — natural human prose, present tense or imperative, no enforced prefix. Useful for personal projects and vaults.

Detection heuristic: parse subjects of the most recent ~50 non-merge commits. If ≥ 60% match a Conventional Commits prefix, adopt it. If ≥ 60% start with an imperative verb capitalised, adopt the imperative style. Otherwise default to plain descriptive.

Full discussion: [`references/commit_style_guides.md`](references/commit_style_guides.md).

---

## 8. Epistemic discipline

The Git log is partial evidence. It shows *what* the working tree looked like at each commit and what the author chose to write in the subject line. It does **not** show:

- why a feature was prioritised,
- what was discussed in code review,
- what bugs the author was actually trying to fix vs. what they happened to fix,
- whether the project goals at the time were the same as today's.

When the agent infers, it must say so. Acceptable hedges include:

- *appears to introduce …*
- *is consistent with refactoring rather than a bug fix*
- *suggests the author was preparing for …*
- *the commit message claims X; the diff only changes Y, so the relationship is unclear*
- *cannot be determined from Git alone*

Forbidden:

- attributing motivation to people or teams not present in the commit log,
- inventing feature requirements,
- naming users, customers, or stakeholders not mentioned anywhere in the repository,
- presenting inferred intent as fact.

If the agent finds itself writing a paragraph without a hash to anchor it, that paragraph is probably hallucinated. Re-anchor or remove it.

---

## 9. Risk-tiered actions

| Tier | Action | Permission required |
|---|---|---|
| read-only | extract log, build analysis, render Markdown reports | none beyond invocation |
| read-only | write `git-history-review.md`, `commit-message-improvements.md`, and (when triggered) `pr_review.md` to the working tree | none beyond invocation |
| advisory | propose section 9 cleaned-history plan inside the main report | none |
| careful | commit the report files as a documentation commit | explicit user request |
| **risky** | run `git commit --amend` on the tip commit | explicit user request, clean tree, unpushed |
| **dangerous** | `git rebase`, `git rebase -i`, `git filter-repo`, `git filter-branch` | explicit, repeated, in-session authorisation; clean tree; not on shared/published history; pre-flight `git tag` backup recommended |
| **forbidden by default** | `git push --force`, `git push --force-with-lease`, history rewrite of a shared branch | only if the user explicitly states they own the branch and accept the consequences |

When in doubt, propose the action plan in plain English and stop. The skill's value is the *report*, not the rewrite.

---

## 10. Rewriting history (only when explicitly authorised)

If — and only if — the user explicitly authorises a rewrite:

1. Confirm the working tree is clean (`git status --porcelain` empty).
2. Confirm the branch is not shared, or that the user accepts force-pushing it. Record that confirmation in the conversation.
3. Create a backup tag: `git tag pre-rewrite-backup-$(date +%Y%m%d-%H%M%S)`.
4. Print the proposed cleaned-history plan (report section 9) and ask the user to confirm it commit-by-commit.
5. Use `git rebase -i` (or, for non-tip rewrites, an interactive rebase from a chosen base) — but the agent **runs the rebase non-interactively** by preparing the todo file and a sequence of new messages, then executing. Never enter an interactive editor on the user's behalf without their visibility into each step.
6. After the rewrite: print the new `git log --oneline`, instruct the user to inspect, and explain how to restore from the backup tag if needed (`git reset --hard pre-rewrite-backup-…`).
7. Never push automatically. The user pushes.

If any of these steps cannot be satisfied, abort the rewrite and keep only the report.

---

## 11. Pre-publish checklist

Before writing the final report file, verify every item in [`assets/pre_report_checklist.md`](assets/pre_report_checklist.md). At a minimum:

- [ ] All commits in the requested range have been analysed.
- [ ] Commits are correctly grouped by date (timezone documented).
- [ ] Every weak/poor commit appears in the improvement table (section 4).
- [ ] Every inferred claim is hedged.
- [ ] Every commit referenced in prose carries a hash.
- [ ] The report makes no claim unsupported by the log or diffs.
- [ ] No destructive Git operation has been performed.
- [ ] The report is complete, readable as a standalone document, and follows the template structure.

---

## 12. Quick command reference

A more complete cheat sheet lives in [`references/git_commands.md`](references/git_commands.md). The most useful for this skill:

```sh
# safety
git rev-parse --is-inside-work-tree
git status --porcelain
git remote -v
git rev-parse --abbrev-ref --symbolic-full-name @{u}

# overview
git log --oneline --no-merges
git log --pretty=format:'%H%x09%ai%x09%an%x09%s' --no-merges

# per-commit detail
git log --numstat --no-merges --format='COMMIT:%H%n%ai%n%an%n%s%n'
git log --name-status --no-merges --format='COMMIT:%H'
git show --stat <hash>
git show <hash>

# diffs
git diff <hash>^ <hash>
git diff <hash>^ <hash> -- <path>

# context (use sparingly)
git blame <file>
git reflog                # only if recovering from a rewrite
```

---

## 13. Limitations to state in every report

Section 10 of every report must state:

- The report is based only on Git history.
- Intent is inferred, not known.
- Some business context may be missing.
- Commit messages may be misleading or inaccurate.
- Diffs show what changed but not always why.

Never trim this section. It is the contract between the report and its readers.

---

## 14. Layout of this skill

```
git-history-reviewer/
├── SKILL.md                              ← this file
├── references/
│   ├── report_template.md                ← canonical Markdown structure of the main report
│   ├── commit_quality_rubric.md          ← classification rules + vague-message blacklist
│   ├── commit_style_guides.md            ← plain / Conventional / imperative / project styles
│   ├── intermediate_schema.md            ← JSON schema for the intermediate dataset
│   ├── improvements_file_format.md       ← format of commit-message-improvements.md
│   └── git_commands.md                   ← extended command cheat sheet
├── templates/
│   └── pr_review_template.md             ← PR-style sub-report template (the merge-gate format)
├── tests/
│   └── test_template_contract.md         ← contract checklist for any filled pr_review.md
├── examples/
│   └── good_vs_bad_messages.md           ← concrete rewrites with rationale
└── assets/
    └── pre_report_checklist.md           ← pre-publish self-check
```

Read referenced files **on demand**. SKILL.md alone is sufficient for orientation; the references, templates, and tests are loaded only when the corresponding stage is being executed.
