---
title: "AI setup audit manifest — schema"
status: active
note_type: template
domain: 07_AI_and_Agents
subdomain: Setup_Audits/Templates
created: 2026-04-10
updated: 2026-04-10
author: Omar
source: ai_setup_inspector
tags: [ai_setup, audit, manifest, schema]
ai_generated: false
ai_reviewed: false
---

# AI setup audit manifest — schema

Canonical JSON shape for the manifest files written by
`.claude/hooks/ai_setup_inspector.py`. A manifest is the serialised
result of one walk over a target. Two manifests of the same target can
be compared file-by-file via sha256 to produce the `diff` snapshot.

## `latest_manifest.json` / `history/<ts>_manifest.json`

```json
{
  "target_id": "omaros",
  "scan_started": "2026-04-10T21:00:00",
  "maturity": "advanced",
  "counts": {
    "ai_docs": 0,
    "automation": 0,
    "claude_infrastructure": 0,
    "logs_and_runs": 0,
    "prompts": 0,
    "registry": 0,
    "settings": 0,
    "structural_dependencies": 0,
    "unrelated": 0
  },
  "totals": {
    "files": 0,
    "ai_files": 0,
    "agents": 0,
    "commands": 0,
    "hooks": 0
  },
  "records": [
    {
      "rel": ".claude/agents/ai-setup-inspector.md",
      "size": 1234,
      "mtime": 1776002400.123,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "category": "claude_infrastructure"
    }
  ]
}
```

## `history/<ts>_diff.json`

```json
{
  "target_id": "omaros",
  "scan_started": "2026-04-10T21:00:00",
  "added": [ { "rel": "...", "size": 0, "mtime": 0, "sha256": "...", "category": "..." } ],
  "modified": [
    {
      "prev": { "rel": "...", "size": 0, "mtime": 0, "sha256": "...", "category": "..." },
      "curr": { "rel": "...", "size": 0, "mtime": 0, "sha256": "...", "category": "..." }
    }
  ],
  "removed": [ { "rel": "...", "size": 0, "mtime": 0, "sha256": "...", "category": "..." } ]
}
```

## `.state/pending_reinspection.json`

```json
{
  "omaros": {
    "target_path": "/Users/omarkhalil/OmarOS",
    "first_flagged": "2026-04-10T21:05:00",
    "last_flagged": "2026-04-10T21:15:00",
    "changed_files": [
      ".claude/agents/ai-setup-inspector.md",
      ".claude/hooks/ai_setup_inspector.py"
    ],
    "categories": {
      "claude_infrastructure": 1,
      "automation": 1
    }
  }
}
```

## Special sha256 values

| Value       | Meaning |
| ----------- | ------- |
| `symlink`   | File is a symlink; not followed. Used so the watcher and diff still track it by path, without reading the target. |
| `oversize`  | File exceeds `MAX_FILE_BYTES` (2 MB). Size and mtime are recorded; the body is not hashed. Binary assets usually fall here. |
| hex string  | Normal sha256 over the file bytes, lowercase. |

## Invariants

1. `records` is sorted lexicographically by `rel`.
2. Every `category` is one of the ten canonical values.
3. Every `rel` is POSIX-style, relative to the target path.
4. `size` and `mtime` come from `os.stat` (or `os.lstat` for symlinks).
5. `sha256` is always either 64 lowercase hex chars, `"symlink"`, or `"oversize"`.
6. `scan_started` is a local ISO-8601 timestamp without timezone suffix.
