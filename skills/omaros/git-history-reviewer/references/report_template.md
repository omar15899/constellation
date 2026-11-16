# Project Git History Review Report

| Field | Value |
|---|---|
| Repository | `<absolute path or remote URL>` |
| Branch | `<current branch>` |
| Generated on | `<YYYY-MM-DD HH:MM timezone>` |
| Analysed commit range | `<e.g. <root>..HEAD or <hash>..HEAD>` |
| Number of commits analysed | `<N>` |
| Working tree status | `<clean | dirty: short description>` |
| Remote status | `<none | origin: <url> | upstream: <ref> | published: yes/no>` |
| History rewrite performed | No, unless explicitly requested and confirmed. |

> **Sub-reports.** When the user asks for a PR-style review of the analysed range, this report is accompanied by `pr_review.md`, generated from `templates/pr_review_template.md`. Section 8 of this report links to it.

---

## 1. Executive summary

A concise but informative summary of the repository history.

Cover:

- Main development themes.
- Main features or systems introduced.
- Major refactors.
- Testing / documentation / infrastructure work.
- Overall quality of the commit history.
- Main risks or uncertainties in the interpretation.

Length: 200–500 words. Anchor every concrete claim to a hash or date range.

---

## 2. Chronological development timeline

For each calendar day with at least one commit, in ascending chronological order, emit one block:

### YYYY-MM-DD

**Commits**

- `<short-hash>` `<HH:MM>` — `<original subject>`
- `<short-hash>` `<HH:MM>` — `<original subject>`

**Narrative**
Plain-English paragraph reconstructing what happened during the day, in chronological order. Cautious language for inferred intent.

**Changed areas**

- `<area / module / file group 1>`
- `<area / module / file group 2>`

**Inferred purpose**
Why the work appears to have been done, based only on commits, file paths, and diffs. Cautious language.

**Development interpretation**
How the commits relate. For example: scaffolding → implementation → tests → cleanup. Or: feature work interrupted by a bug fix. Or: pure refactor.

**Uncertainties**

- `<thing that cannot be confidently inferred from Git>`

*(Repeat the block above for every day with commits.)*

---

## 3. Commit-by-commit review

For each commit (newest-to-oldest OR oldest-to-newest, but consistent):

### `<full-hash>`

| Field | Value |
|---|---|
| Original subject | `<original subject line>` |
| Author | `<author name <author email>>` |
| Date | `<YYYY-MM-DD HH:MM timezone>` |
| Files changed | `<count>` |
| Lines | `+<insertions> / -<deletions>` |

**Changed files**

- `<file 1>`
- `<file 2>`

**Summary of changes**
Plain-English explanation of what the commit appears to do, derived from the diff and the file list. Hedge inferred intent.

| Quality field | Value |
|---|---|
| Commit message quality | `<Excellent | Good | Acceptable | Weak | Poor>` |
| Issues detected | `<Vague message | Too broad | Too narrow | Mixed concerns | Missing rationale | Message does not match diff | Inconsistent style | None>` |
| Suggested improved title | `<proposed title, or — if no improvement needed>` |
| Confidence | `<High | Medium | Low>` |

**Suggested improved body**

```
<optional multi-line body, or — for title-only improvement or none needed>
```

**Rationale for suggestion**
Why the proposed message is better. Cite the diff or files supporting the claim. If the original is misleading, say so plainly.

*(Repeat for every commit in the analysed range.)*

---

## 4. Commit message improvement table

A compact table of every commit whose message can be improved. One row per commit. Commits whose original message is already adequate must not appear here.

| Original hash | Original message | Suggested message | Reason | Confidence |
|---|---|---|---|---|
| `<short-hash>` | `<original>` | `<proposed>` | `<why>` | `<H/M/L>` |
| `<short-hash>` | `<original>` | `<proposed>` | `<why>` | `<H/M/L>` |

This table is the actionable digest of section 3.

---

## 5. Daily change history

A polished, more narrative version of section 2. Reads like a development diary reconstructed from Git.

### YYYY-MM-DD

**What changed**
Detailed but concise explanation. Several sentences are fine.

**Why it appears to have changed**
Careful inference based only on Git evidence. Hedge.

**How the work evolved**
Sequence of commits and their relationship across the day.

**Resulting project state**
What the repository appears to have gained by end of day.

*(Repeat for every day with commits.)*

The duplication with section 2 is intentional. Section 2 is structured for quick scanning; section 5 is structured for sequential reading.

---

## 6. Architectural and functional evolution

Describe how the project evolved across the whole history. Span the entire analysed range, not single days.

Cover, where evidence supports it:

- Main modules introduced (with hashes / dates).
- Main abstractions added (interfaces, base classes, schemas, protocols).
- Major design changes (renames, restructures, paradigm shifts).
- Important refactors.
- Testing evolution (when tests were introduced, how coverage grew).
- Documentation evolution.
- Build / deployment / tooling evolution.
- Dependency evolution (when major libraries were added or removed).

If evidence for a category is absent, say so explicitly rather than padding.

---

## 7. Quality of the Git history

Assess the history along these axes:

| Axis | Assessment |
|---|---|
| Commit granularity | `<too large | appropriate | too small | mixed>` |
| Message clarity | `<…>` |
| Chronological coherence | `<…>` |
| Traceability | `<…>` |
| Logical separation of commits | `<…>` |
| Suitability for onboarding | `<…>` |
| Suitability for audit | `<…>` |
| Recommendation | `<rewrite | squash partially | clean partially | leave untouched>` |

Be honest. A polished history reads "left untouched". A messy one says so.

---

## 8. Recommended actions

### Safe actions (read-only or additive, no rewrite)

- `<e.g. add this report to the repository under docs/>`
- `<e.g. introduce a CONTRIBUTING.md commit-message guideline>`
- `<e.g. add a CHANGELOG generated from squashed feature ranges>`
- `<e.g. add commit-msg hook enforcing the chosen style>`

### Potentially risky actions (require explicit user confirmation)

| Action | Danger | Confirmation required? |
|---|---|---|
| Interactive rebase to reword vague subjects on `X..Y` | Rewrites history. Refuses on shared branches. | Yes |
| Squash commits A, B, C into a single feature commit | Removes intermediate state from history; backup tag required. | Yes |
| Reorder commits | May change merge semantics. Backup tag required. | Yes |
| Split a large commit | Requires recreating intermediate trees. Backup tag required. | Yes |

### PR-style review of this range

If the user requested a PR review of the analysed range, the dedicated sub-report is at `pr_review.md`. It complements section 3 with a severity-graded findings table tailored to merge-gate decisions.

---

## 9. Optional cleaned history plan

Include this section only if the user requested a rewrite plan, or the history is sufficiently messy that a plan is genuinely useful. Otherwise write a single line: *Not applicable.* and continue to section 10.

For each proposed commit in the cleaned sequence:

### Proposed commit `<n>`

| Field | Value |
|---|---|
| Title | `<proposed title>` |
| Risk level | `<Low | Medium | High>` |

**Body**

```
<body, or —>
```

**Original commits included**

- `<short-hash>` — `<original subject>`
- `<short-hash>` — `<original subject>`

**Reason for grouping / splitting**
Why these original commits map to this proposed commit.

*(Repeat for every proposed commit. The cleaned sequence must be in chronological order. Total proposed commits should be ≤ the original count unless splitting is justified.)*

This section is a *plan*, not an action. Nothing is mutated.

---

## 10. Limitations

This report is subject to the following limitations, which must always be stated:

- The report is based only on the Git history of the repository.
- Intent is inferred from commits, file paths, and diffs; it is not known.
- Some business context (issues, design docs, conversations) may be missing entirely from Git and therefore from this report.
- Commit messages may be misleading, inaccurate, or out of date relative to what was actually committed.
- Diffs show what changed, but not always why.
- Author identities reflect Git configuration at commit time and may not match the people who actually wrote the code (paired authoring, machine-generated commits, automated tooling).
- The report does not claim completeness regarding code correctness, security implications, or performance characteristics; those require additional analysis outside the scope of Git history review.

Do not trim or summarise this section.

---

*End of report.*
