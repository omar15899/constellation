# Pre-Publish Checklist

Run this checklist before writing the final `git-history-review.md`. Every item must pass. If any item fails, fix it and re-run the checklist — do not publish.

## Coverage

- [ ] Every commit in the requested range has been retrieved (`commit_count` matches `git rev-list --count <range>`).
- [ ] Every retrieved commit appears once and only once in the analysis.
- [ ] Merges are either included consistently or excluded consistently (whichever the user requested), and the choice is documented in the report preamble.
- [ ] All commits are grouped into `daily_groups` by **author date** in a documented timezone.
- [ ] No commit is silently dropped — if a commit was excluded, the reason is stated in the report preamble.

## Correctness

- [ ] Every commit hash is preserved verbatim (full hash in the analysis, short hash in the report). No transcription errors.
- [ ] Every author name and email is preserved verbatim from `git log` output.
- [ ] Dates in the report match the dates from `git log` (after the chosen timezone conversion).
- [ ] Subjects are quoted verbatim. If the original subject contains characters that confuse the report layout, escape them rather than rewrite them.
- [ ] No commit has been confused with another (cross-check by hash, not subject).

## Quality assessment

- [ ] Every commit has a `quality.grade` ∈ {`Excellent`, `Good`, `Acceptable`, `Weak`, `Poor`}.
- [ ] Every commit with `improvable = true` has a corresponding entry in section 4 (improvement table) and a per-commit suggested message in section 3.
- [ ] No commit graded `Excellent` or `Good` appears in the improvement table.
- [ ] The detected commit-message style is recorded, with the evidence that supports the detection.
- [ ] If the project has no clear style and the user did not specify one, plain descriptive style was used as the default and that fact is stated.

## Epistemic discipline

- [ ] Every inferred claim in prose uses cautious language (*appears to*, *suggests*, *is consistent with*, *cannot be determined from Git alone*).
- [ ] No claim names a person, customer, ticket, or stakeholder unless they are present in the commit metadata or commit body.
- [ ] No claim invents business motivation that the diff does not support.
- [ ] When the original commit message contradicts its diff, the discrepancy is surfaced explicitly and the proposed message reflects what the diff actually does.
- [ ] Sections 6 and 7 (architectural evolution, history quality) make no claim outside what the log and diffs support; absent evidence is stated as absent rather than padded.

## Anchoring

- [ ] Every paragraph in section 1 (executive summary), section 2 (timeline), section 5 (daily diary), and section 6 (architectural evolution) cites at least one hash or date.
- [ ] No paragraph reads as a free-floating narrative without a Git anchor. If one does, either re-anchor it or remove it.

## Safety

- [ ] No destructive Git operation has been performed.
- [ ] If a rewrite was authorised: the working tree was clean, a backup tag was created, the proposed plan was confirmed by the user, and the user — not the agent — pushed the result.
- [ ] If a rewrite was *not* authorised: the report's preamble states "History rewrite performed: No, unless explicitly requested and confirmed."
- [ ] No file in the existing working tree has been modified by this skill except the new report files (`git-history-review.md`, `commit-message-improvements.md`, optionally `git-history-analysis.json`).

## Structure

- [ ] The main report follows the Markdown structure of `references/report_template.md` exactly: heading hierarchy (`#`, `##`, `###`), section order, table column sets.
- [ ] No ASCII separator art (no `=====` or stray `-----` outside table delimiters) leaked into the rendered Markdown.
- [ ] Section 9 (cleaned history plan) is either present with content, or contains a single line *Not applicable.*
- [ ] Section 10 (limitations) is present, complete, and not summarised.
- [ ] The header metadata table at the top is fully populated: repository, branch, generated-on timestamp, range, commit count, working-tree status, remote status, history-rewrite status.
- [ ] The report closes with the *End of report.* line.

## PR-review sub-report (only when emitted)

When `pr_review.md` is also produced, run through the contract in `tests/test_template_contract.md` in addition to the items below. Specifically verify:

- [ ] Title heading exists (`# PR #<n> Review: <short title>`).
- [ ] PR metadata table is populated; `Description` is either non-empty or the literal `empty`.
- [ ] Files Changed table contains at least one row, every row has a `Type` in `{Added, Modified, Deleted}`.
- [ ] Findings table columns match the contract; every `Severity` is in `{Critical, High, Medium, Low}` and every `New?` is in `{NEW, PRE-EXISTING}`.
- [ ] Summary table totals are internally consistent (`Total = NEW + PRE-EXISTING` per severity row; bottom `Total` row equals column sums).
- [ ] Final assessment matches the default decision rule, or an explicit override rationale is recorded.
- [ ] Section 8 of the main report links to `pr_review.md`.

## Readability

- [ ] The report is readable without access to the repository — a reader who has never seen the project should be able to understand the development arc, the main themes, and the main quality concerns from the document alone.
- [ ] Hashes, dates, and file paths are formatted consistently throughout the report.
- [ ] Long lists (changed files, daily commits) are bulleted rather than prose-jammed.
- [ ] The improvement table in section 4 is alphabetically scannable by hash and visually aligned.

## Files

- [ ] `git-history-review.md` is written to a path that exists in the repo (root, `docs/`, or `reports/`), chosen to match the repo's existing layout.
- [ ] `commit-message-improvements.md` is written alongside the main report.
- [ ] `git-history-analysis.json` is written only if the user requested a machine-readable artefact.
- [ ] None of the new files overwrite an existing tracked file without the user's explicit consent.

When every box is checked, publish.
