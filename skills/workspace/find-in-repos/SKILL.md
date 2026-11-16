---
name: find-in-repos
description: Locate symbols, patterns and consumers across repositories with scoped ripgrep searches. Use for find X across repos, where is X defined, or searches filtered by repository, perimeter or source language.
---

# Search across repositories

1. Resolve candidate roots from [project registry](../../../profiles/projects.json), applying
   the requested repo/perimeter/stack filter before searching. The hub is a
   separate root; external vendored projects require an explicit target.
2. Start with `rg --files` for paths or `rg -n` for contents in the selected
   roots. Quote each path, use `--` before an untrusted pattern, and use `-F`
   for literal text. Prefer the smallest source directories that answer the task.
3. Exclude `.git`, `.venv`, `node_modules`, caches, build/dist/outputs and
   generated duplicates. Always exclude `.env*`, `*.pem`, `*.key`,
   `credentials.json`, `_conversations`, `.codex/sessions`,
   `.codex/archived_sessions`, `rollout-*.jsonl` and `.claude/run`.
   Do not use `--follow`, unrestricted `-uuu`, or include ignored/hidden trees
   broadly. If a specific hidden source is needed, restrict its path explicitly
   and retain secret/archive exclusions.
4. Rank definitions and production consumers ahead of tests and docs, preserving
   evidence that affects the conclusion. Limit initial output, disclose truncation
   and expand relevant results before claiming consumer coverage.
5. Report repository, source path and line, plus what each match means. Distinguish
   no matches from a failed search and include uninspected or missing roots.

Use native ripgrep arguments; there is no custom `--stack`, `--full` or ranking
engine. Semantic ownership or dynamic references need inspection beyond text matches.
