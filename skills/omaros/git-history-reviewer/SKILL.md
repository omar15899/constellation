---
name: git-history-reviewer
description: "Reconstruct a Git development timeline, audit commit quality, or review a specified branch/PR range from its actual history and diffs. Produce an evidence-based retrospective or proposed message improvements without rewriting history."
---

# Git history review

Start with the repository, requested range and purpose: timeline, retrospective,
message quality or review of a candidate change. Use the current repository if
unambiguous. For a complete-history request, cover commits reachable from
`HEAD`; otherwise resolve the requested baseline and tip. State exclusions and
sampling explicitly.

Deliver the requested explanation or artifact. A chat review does not require
new files; a saved report follows the owner's existing layout and change
contract. Separate message improvements or machine-readable data only when
useful to the requested output. Templates below are formats to adapt, not a
mandatory collection of reports.

## Collect evidence without changing the repository

Resolve the actual Git owner, exact tip and baseline SHAs, branch, upstream
configuration and working-tree state. Keep uncommitted changes distinct from
the reviewed commits. Use `GIT_OPTIONAL_LOCKS=0` or `git --no-optional-locks`
for read-only Git commands; there is no reason to stash, reset or check out
another branch for this review.

```sh
git --no-optional-locks -C /path/to/repo rev-parse --show-toplevel
git --no-optional-locks -C /path/to/repo status --porcelain=v1
git --no-optional-locks -C /path/to/repo log --format='%H %aI %cI %s' BASE..HEAD
git --no-optional-locks -C /path/to/repo log --name-status --format='COMMIT:%H' BASE..HEAD
git --no-optional-locks -C /path/to/repo show --stat COMMIT
```

Replace `BASE` and `COMMIT` with the resolved objects. `BASE..HEAD` excludes
commits reachable from the baseline. Inspect the graph and merges when they
affect interpretation; `--no-merges` is a filtered view, not complete history.

Read metadata and changed paths before opening relevant patches. Confirm
important message claims against diffs, including the appropriate merge
parents. Inspect large histories in bounded groups and retain hash-linked
notes so prose does not outrun coverage. The
[intermediate schema](references/intermediate_schema.md) is useful for large
analyses; persist that dataset only when requested.

Use primary repository evidence for what changed. Additional supplied or
authorized issue/design context can explain intent, but identify its source
separately. Avoid dumping remote URLs with embedded credentials, author contact
details, unrelated diffs, raw tool output or conversation archives into reports.

## Interpret and assess

- Anchor factual claims to commit hashes and the relevant paths or diff.
  Preserve original hashes and dates. For day-by-day grouping, state whether
  author or committer dates are used and the chosen timezone; Git has no
  universal “repository local timezone.”
- Distinguish the commit message's claim, observable change and inferred intent.
  A diff cannot establish a business priority, successful deployment or runtime
  behavior. Current documentation does not prove what was true at an older SHA.
- For message quality, use the [rubric](references/commit_quality_rubric.md):
  specificity, coherence, agreement with the diff and useful rationale. Do not
  invent missing rationale to improve a score.
- Derive proposed titles/bodies from the diff and original message, preserving
  intent. Record the hash, original, proposal, reason and uncertainty. Follow
  project conventions and natural human wording; do not impose Conventional
  Commits or a new style from a mechanical threshold. See the
  [style guide](references/commit_style_guides.md) and
  [examples](examples/good_vs_bad_messages.md).
- Connect related changes into a timeline when requested. Explain what the
  evidence supports and what remains unknown instead of inventing a development
  story for every calendar day.

For a branch or PR review, record exact base/head SHAs and review the candidate
diff. Findings need severity, location, cause, consequence and evidence; a
historical smell alone is not a current defect. The
[PR template](templates/pr_review_template.md) can structure the result.
A prose recommendation does not approve a Constellation gate or authorize
posting a review to an external service.

## Report and boundaries

Use the [report template](references/report_template.md) for a substantial
retrospective, the [improvement format](references/improvements_file_format.md)
for requested message proposals and the [command reference](references/git_commands.md)
for further inspection. Adapt their sections to the scope; do not create
placeholder files, require unrelated sections or run their test checklist.

Before delivery, check that cited hashes belong to the declared range, the
coverage matches what was inspected, proposals preserve meaning and conclusions
separate facts from inferences. State material gaps and any unverified runtime
claims. Source inspection does not substitute for executed tests, which require
Omar's explicit request.

A review or a proposal to improve messages does **not** authorize an actual
history rewrite. For an explicit rewrite request, first prepare the exact
affected commits, proposed changes, shared-history consequences and recovery
plan; follow the owner's Git contract and the authorization already provided.
Do not auto-amend, rebase, create backup refs, force-push or publish a report.
This skill has no bundled executable scripts.
