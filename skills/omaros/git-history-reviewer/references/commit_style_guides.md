# Commit Message Styles

Four supported styles. The skill detects which one (if any) the project already uses and matches it. The user can override.

## 1. Project-specific style (highest priority)

If the most recent ~50 non-merge commits show a clear convention, match it. Common project-specific patterns:

- Tracker-prefixed: `[ABC-1234] Subject` or `ABC-1234: Subject`.
- Module-prefixed: `auth: do something`, `parser: do something else`.
- Emoji-prefixed: `:sparkles: Add new feature`, `:bug: Fix issue`.
- Mixed prefixes from generated tooling (`auto:`, `chore(deps):`).

Detection rule: if ≥ 60% of recent commits start with the same prefix shape, that's the convention. Match it.

## 2. Imperative mood Git style (canonical default)

This is the convention recommended by the Git project itself.

- Subject in the imperative: "Add", "Fix", "Refactor", "Remove", "Document".
- Capitalised first word.
- No trailing period.
- Subject ≤ 72 characters (50 is the often-quoted target; 72 is the hard ceiling).
- Blank line between subject and body.
- Body wrapped at ≤ 72 characters per line.
- Body explains *why* and *what*, not *how* (the diff shows how).

Example:

```
Cache resolved DNS results for 60 seconds

The DNS resolver was being called once per outbound request, which
became the bottleneck in the latency profile under load. A small
in-memory cache keyed by hostname collapses the lookups for
short-lived bursts. Cache TTL is intentionally short to avoid
masking real DNS changes.
```

## 3. Conventional Commits

`<type>(<scope>): <subject>` where:

- `type` ∈ `feat | fix | refactor | docs | test | chore | perf | build | ci | style | revert`,
- `scope` is optional, in parentheses, lowercase, often a module name,
- `subject` is the imperative description, no trailing period,
- breaking changes are signalled with `!` after the type/scope: `feat(api)!: drop v1 endpoints`.

Example:

```
feat(auth): add refresh-token rotation

Refresh tokens are now rotated on each use, with a 5 second window
where both old and new tokens are accepted to avoid race conditions
during concurrent requests.

BREAKING CHANGE: clients must update to the new token-refresh flow;
old single-use tokens are no longer reissued.
```

Use this style only if the repo already follows it (≥ 60% of recent commits) or the user explicitly requests it. Do not impose Conventional Commits on a repo that doesn't already use it.

## 4. Plain descriptive

Natural human prose. No mandatory prefix. Present tense or imperative. Useful for personal projects, notebooks, and vaults where rigid conventions are noise.

Example:

```
Add a section on PID controllers to the controls notes

Introduces the basic PID structure, the practical issue of integral
windup, and a worked example with the velocity loop from the
quadcopter project.
```

This style is often appropriate for non-code repositories (Obsidian vaults, LaTeX notebooks, research scratchpads).

---

## Subject-line drafting heuristics

When proposing a new subject from a diff:

1. **Lead with a verb that describes the change to the codebase**, not to the diff. Prefer `Cache DNS results` over `Modify resolver.py`.
2. **Name the affected concept**, not the file. Prefer `Refresh-token rotation` over `Update auth.py`.
3. **Be specific about scope**. Prefer `Reject expired refresh tokens` over `Improve auth`.
4. **Don't restate the diff**. The reader can run `git show`. The subject is for the reader who *won't*.
5. **Keep it ≤ 72 chars** unless a project-specific style allows more.

## Body drafting heuristics

A body is justified when:

- the change is non-trivial (> ~30 lines or > 3 files),
- the diff alone does not make the *why* obvious,
- there is a non-obvious tradeoff, constraint, or rejected alternative worth recording,
- the change has follow-ups or known limitations,
- the change is a partial rollback or workaround for something.

A body is *not* justified for:

- one-line fixes whose subject is already self-explanatory,
- cosmetic-only changes,
- commits whose entire purpose is captured in the subject.

When inferring a body from the diff, restrict claims to what the diff supports. If the user has not provided issue context, do not pretend to know the customer story.
