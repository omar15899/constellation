# Intermediate Analysis Schema

The agent **must** build a structured intermediate dataset before writing the final report. This separation enforces discipline: the analysis is anchored in data, the report is anchored in the analysis, and prose is generated last.

The schema below describes the shape of `git-history-analysis.json`. Even when the user does not request the JSON file, the agent should construct an equivalent in-memory object.

## Top-level shape

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-04-27T14:32:00+02:00",
  "repository": { "...": "see below" },
  "branch": { "...": "see below" },
  "working_tree": { "...": "see below" },
  "analysed_range": { "...": "see below" },
  "style_detection": { "...": "see below" },
  "commits": [ { "...": "per-commit object" } ],
  "daily_groups": [ { "...": "per-day object" } ],
  "improvements": [ { "...": "per-improvement object" } ],
  "summary_metrics": { "...": "see below" },
  "limitations": [ "string", "..." ]
}
```

## `repository`

```json
{
  "path": "/abs/path/to/repo",
  "remotes": [
    { "name": "origin", "url": "git@github.com:owner/repo.git" }
  ],
  "head": {
    "hash": "9f3a2b1c…",
    "short_hash": "9f3a2b1",
    "subject": "…",
    "author_name": "…",
    "author_email": "…",
    "author_date": "2026-04-27T14:00:00+02:00"
  }
}
```

## `branch`

```json
{
  "current": "main",
  "upstream": "origin/main",
  "is_published": true,
  "is_shared_inferred": true
}
```

`is_shared_inferred` is `true` if the branch has an upstream OR if the user has stated the branch is shared. Use it to gate destructive operations.

## `working_tree`

```json
{
  "clean": false,
  "modified": ["path/to/file1", "..."],
  "untracked": ["path/to/file2", "..."],
  "staged": ["path/to/file3", "..."]
}
```

## `analysed_range`

```json
{
  "from_ref": "<root>",
  "from_hash": "abc123…",
  "to_ref": "HEAD",
  "to_hash": "9f3a2b1…",
  "commit_count": 142,
  "include_merges": false,
  "timezone": "Europe/Madrid"
}
```

## `style_detection`

```json
{
  "detected_style": "imperative" ,
  "confidence": "High",
  "evidence": "47 of the last 50 non-merge commits begin with a capitalised imperative verb; no Conventional Commits prefix observed."
}
```

`detected_style` ∈ `project_specific | imperative | conventional | plain | mixed | none`.

## `commits[i]`

```json
{
  "hash": "abc123def456…",
  "short_hash": "abc123d",
  "parent_hashes": ["..."],
  "author_name": "…",
  "author_email": "…",
  "author_date": "2026-04-12T10:14:00+02:00",
  "committer_name": "…",
  "committer_date": "2026-04-12T10:14:05+02:00",
  "subject": "fix",
  "body": "",
  "files": [
    {
      "path": "src/auth/session.py",
      "status": "M",
      "additions": 12,
      "deletions": 3
    }
  ],
  "stats": {
    "files_changed": 1,
    "insertions": 12,
    "deletions": 3
  },
  "is_merge": false,
  "inferred_intent": {
    "summary": "Appears to add a null-check before reading the session token.",
    "kind": "bug_fix",
    "confidence": "Medium"
  },
  "quality": {
    "grade": "Poor",
    "issues": ["vague", "missing_rationale"],
    "improvable": true
  }
}
```

`status` codes follow `git log --name-status`: `A` added, `M` modified, `D` deleted, `R<num>` rename, `C<num>` copy.

`kind` ∈ `feature | bug_fix | refactor | docs | test | chore | build | ci | perf | style | revert | merge | release | unknown`.

## `daily_groups[i]`

```json
{
  "date": "2026-04-12",
  "commit_hashes": ["abc123d", "def456a", "..."],
  "changed_areas": [
    "src/auth/",
    "tests/auth/",
    "docs/"
  ],
  "narrative": "Day starts with a small null-check fix in auth (abc123d), followed by a test added to lock the behaviour (def456a). The afternoon block is a documentation pass on the same module (…).",
  "inferred_purpose": "Stabilising the auth module after a regression — the morning fix and afternoon test together suggest a reactive sequence rather than planned feature work.",
  "interpretation": "scaffold→fix→test→docs",
  "uncertainties": [
    "The reason for the regression is not visible in Git; could be an unrecorded production incident."
  ]
}
```

## `improvements[i]`

```json
{
  "hash": "abc123def…",
  "short_hash": "abc123d",
  "original_subject": "fix",
  "original_body": "",
  "suggested_title": "Reject empty session tokens before parsing",
  "suggested_body": "Adds an early return in SessionLoader when the token is None or empty, instead of letting the parser raise. Prevents a 500 on cold-start requests where the cookie has not yet been set.",
  "rationale": "Original message conveys nothing. Diff shows a guard clause added in src/auth/session.py:42-48. Affected files and the changed lines support the proposed message without invention.",
  "confidence": "High",
  "title_only": false,
  "affected_files": ["src/auth/session.py"]
}
```

## `summary_metrics`

```json
{
  "commits_total": 142,
  "commits_by_grade": {
    "Excellent": 12,
    "Good": 38,
    "Acceptable": 51,
    "Weak": 28,
    "Poor": 13
  },
  "commits_improvable": 41,
  "active_days": 37,
  "first_commit_date": "2025-09-03",
  "last_commit_date": "2026-04-27",
  "top_changed_paths": [
    { "path": "src/auth/", "commits": 22 },
    { "path": "tests/", "commits": 18 }
  ],
  "authors": [
    { "name": "…", "commits": 130 },
    { "name": "…", "commits": 12 }
  ]
}
```

## `limitations`

A free-form list of strings restating the limitations from section 10 of the report. Always populated.

---

## Validation rules

- Every entry in `commits[]` whose `quality.improvable` is `true` must have a corresponding entry in `improvements[]`.
- Every `commit_hashes` value in `daily_groups[i]` must exist in `commits[]`.
- `analysed_range.commit_count` must equal `len(commits)`.
- Sum of `daily_groups[i].commit_hashes` lengths must equal `commit_count` (assuming no commit is dropped).
- All hashes are stored in their full form *and* short form (first 7 chars).

If validation fails, do not write the JSON file and do not write the report — fix the analysis first.
