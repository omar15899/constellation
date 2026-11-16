# PR #<number> Review: <short title>

| Field | Value |
|---|---|
| Title | `<title>` |
| Author | `<author>` |
| Branch | `<source branch> -> <target branch>` |
| State | `<OPEN | MERGED | CLOSED>` |
| Reviewed | `<YYYY-MM-DD>` |
| Description | `<short description or empty>` |

> **Source of truth.** This review is reconstructed from Git history alone (or from the actual GitHub PR if one was provided). Inferred intent uses the same epistemic-caution rules as the parent `git-history-review.md`.

## Files Changed

| File | Type |
|---|---|
| `<path/to/file>` | `<Added | Modified | Deleted>` |

## Findings

| # | Category | Location | Finding | Severity | New? | Suggestion |
|---|---|---|---|---|---|---|
| 1 | `<Dep Hygiene | Robustness | Correctness | Performance | Test Coverage>` | `<file and line>` | `<finding text>` | `<Critical | High | Medium | Low>` | `<NEW | PRE-EXISTING>` | `<actionable suggestion>` |

**Category vocabulary** (stable across reviews; extend only via documented review policy):

- **Dep Hygiene** — dependency hygiene, lockfile consistency, version pinning.
- **Robustness** — error handling, defensive boundaries, defaults, retries.
- **Correctness** — logic bugs, off-by-one, mismatched contracts, broken invariants.
- **Performance** — algorithmic complexity, unnecessary work, allocation hotspots.
- **Test Coverage** — missing, weak, or misaligned tests; flakiness; coverage gaps.

**Severity rubric**:

| Severity | Meaning |
|---|---|
| Critical | Merge-blocker. Production impact, data loss risk, or security exposure. |
| High | Strong objection. Should not merge without resolution or explicit waiver. |
| Medium | Address before merge unless the team accepts a tracked follow-up. |
| Low | Nit, polish, or stylistic preference. Non-blocking. |

**`New?` semantics**:

- **NEW** — the finding is introduced by the changes in this PR / range.
- **PRE-EXISTING** — the finding lives in unchanged code touched only incidentally; surfaced for visibility, not blamed on the PR author.

## Summary

| Severity | NEW | PRE-EXISTING | Total |
|---|---:|---:|---:|
| Critical | `<n>` | `<n>` | `<n>` |
| High | `<n>` | `<n>` | `<n>` |
| Medium | `<n>` | `<n>` | `<n>` |
| Low | `<n>` | `<n>` | `<n>` |
| **Total** | `<n>` | `<n>` | `<n>` |

## Assessment

**Decision:** `<Approve | Request Changes | Comment>`

**Default decision rule** (override only with documented justification):

- Any **NEW Critical** finding → `Request Changes`.
- Any **NEW High** finding → `Request Changes` unless the team has agreed to a tracked follow-up.
- Otherwise, **NEW Medium** alone is reviewer's discretion (`Approve` with comments OR `Request Changes`).
- **NEW Low** alone never blocks.
- **PRE-EXISTING** findings never block on their own; they inform the assessment narrative but do not change the gate.

**Key decision rationale**

- `<Primary blocking issue 1>`
- `<Primary blocking issue 2>`
- `<Optional non-blocking note>`

<!-- ADAPTATION POINT — adjust severity thresholds and blocking criteria to match local repository governance.
     Document any divergence from the default rule above. -->

<!-- PROJECT-SPECIFIC IMPLEMENTATION GOES HERE — add repository-specific checks here, for example:
     - lockfile policy (no manual edits to lockfiles),
     - IDE-settings policy (no committed editor configs),
     - dependency-group policy (no runtime deps in dev group, no dev deps imported in production code),
     - assert-in-production policy (no `assert` statements outside tests). -->

## How this template is filled by the skill

When `git-history-reviewer` produces a PR review (because the user requested one, or because the analysed range maps cleanly to a PR), the agent:

1. Treats the analysed commit range as the PR's diff (`<base>..HEAD`, or the actual PR diff if a number was supplied).
2. Resolves the metadata from `git log` and, if available, the GitHub PR API (`gh pr view <n> --json …`); never invents fields that Git cannot prove.
3. Walks the diff once per category in the rubric, recording one row per real concern. Categories the diff does not exercise are simply absent from the table — do not pad.
4. Marks `NEW` vs `PRE-EXISTING` by checking whether each affected line was introduced or merely contextual in the diff.
5. Computes the summary table by counting rows from the findings table. The totals must be internally consistent — verify before saving.
6. Applies the default decision rule, then writes the rationale bullets.
7. Validates the result against `tests/test_template_contract.md`.

## Output location

The PR review sub-report is written next to the parent report. Recommended paths:

- `pr_review.md` (alongside `git-history-review.md`),
- `docs/pr_review_<short-hash-range>.md` (when the repo already has a `docs/` directory),
- `reports/pr_review_<YYYY-MM-DD>.md` (when reports are dated artefacts).

## Notes

- The PR review never invents business context that Git cannot prove. Use cautious language for inferred intent.
- For a PR with hundreds of files, group them in **Files Changed** by directory and elide unchanged-config noise (lockfiles, generated assets) into a single row, marking the elision explicitly.
- For repositories that do not actually use pull requests (solo projects, vaults), the PR review acts as a *retrospective merge review* over the commit range. The `Author` field becomes the dominant author of the range; `Branch` becomes `<base-hash>..HEAD`.
