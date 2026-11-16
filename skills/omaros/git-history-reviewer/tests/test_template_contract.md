# PR-Review Template — Contract Checklist

A completion checklist that any filled-in `pr_review.md` must pass before publication. Use this as a manual gate, or wire it into a CI lint as instructed below.

## Required structure

- [ ] **Title heading** of the form `# PR #<number> Review: <short title>` exists.
- [ ] **PR metadata table** exists and contains rows for: `Title`, `Author`, `Branch`, `State`, `Reviewed`. The `Description` row is also present, but its value may be the literal `empty` if the PR genuinely has no description.
- [ ] All metadata cells are non-empty *except* `Description` when it is explicitly the literal word `empty`.
- [ ] **Files Changed** section exists with a table containing at least one row.
- [ ] Every Files Changed row has a `Type` value in `{Added, Modified, Deleted}`.

## Findings table

- [ ] **Findings** section exists with a table whose header contains the columns: `#`, `Category`, `Location`, `Finding`, `Severity`, `New?`, `Suggestion`.
- [ ] At least one finding row exists *or* the section explicitly states "No findings." If the section is empty without that statement, the contract fails.
- [ ] Every `Severity` value is one of `Critical | High | Medium | Low`.
- [ ] Every `New?` value is one of `NEW | PRE-EXISTING`.
- [ ] Every `Category` value comes from the documented vocabulary (`Dep Hygiene`, `Robustness`, `Correctness`, `Performance`, `Test Coverage`) **or** is documented as a project-specific extension elsewhere in the file.
- [ ] Every `Location` cell points to a concrete file path; line numbers are present where applicable.
- [ ] Every `Suggestion` cell is actionable (an instruction or change), not a description.

## Summary table

- [ ] **Summary** section contains a table with rows for `Critical`, `High`, `Medium`, `Low`, and `Total`.
- [ ] Columns include `NEW`, `PRE-EXISTING`, and `Total`.
- [ ] **Numerical consistency:** for every severity row, `Total = NEW + PRE-EXISTING`.
- [ ] The bottom `Total` row equals the column sums of the four severity rows.
- [ ] The summary row counts match the actual rows in the Findings table.

## Assessment

- [ ] **Assessment** section exists with a final decision in `{Approve, Request Changes, Comment}`.
- [ ] The decision matches the default rule unless an override rationale is provided in writing:
  - Any `NEW Critical` ⇒ `Request Changes`.
  - Any `NEW High` without tracked follow-up ⇒ `Request Changes`.
  - Otherwise the decision is reviewer's discretion.
- [ ] **Key decision rationale** lists at least one bullet — either a primary blocking issue, or, for `Approve`, an explicit non-blocking note explaining why the residual findings are acceptable.

## Project-specific extensions

- [ ] If the template's `<!-- ADAPTATION POINT -->` comment was modified, the modifications are documented and consistent with the team's review policy.
- [ ] If `<!-- PROJECT-SPECIFIC IMPLEMENTATION GOES HERE -->` was filled, every added check is named, has stable category labels, and produces deterministic outcomes (no "reviewer feels" criteria).

## Epistemic discipline

- [ ] No finding invents business context not supported by the diff or the PR description.
- [ ] Every inferred claim uses cautious language (`appears to`, `is consistent with`, `cannot be determined from Git alone`).
- [ ] No claim attributes blame to people who are not named in the Git metadata.
- [ ] Hashes and dates that appear in the report are preserved verbatim from `git log`.

## Cross-document consistency

When a `pr_review.md` is published alongside the parent `git-history-review.md`:

- [ ] Section 8 of the parent report links to `pr_review.md`.
- [ ] No commit hash that the PR review marks as `NEW` is missing from the parent report's commit-by-commit review.
- [ ] The PR review's `Reviewed` date is not earlier than the parent report's `Generated on` date.
- [ ] The PR review's commit range is a subset of the parent report's `Analysed commit range`.

## Wiring into CI (optional)

Replace this manual checklist with an automated check by:

1. Parsing the markdown into a header tree (any markdown parser).
2. Asserting the presence of each section heading listed above.
3. Parsing each table into rows and validating the column-set, severity enum, `New?` enum, and category enum.
4. Recomputing the summary table from the findings rows and asserting equality cell-by-cell.
5. Asserting the assessment value is in the allowed set and consistent with the default decision rule (or an override rationale is present).

A 60-line Python script using `mistune` or `markdown-it-py` is sufficient.

> **USER-INTEGRATION POINT:** if your team already lints PR reviews as part of CI (GitHub Actions, GitLab CI, Buildkite), wire the rules above into that pipeline rather than running them by hand.
