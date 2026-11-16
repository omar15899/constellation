# Append patterns — diff-safe edits for daily notes

This file exists because the difference between a safe append and a destructive one is a single regex. Every pattern here is idempotent: running it twice on the same input produces the same file.

## General rule

Before any append, read the file. Locate the target section by its exact heading (e.g. `## Narrative`). Operate only on the region between that heading and the next `## ` at the same level (or EOF).

If the target heading is missing, insert it in its canonical position. Canonical order:

1. `## Narrative`
2. `## Tasks today`
3. `## Decisions`
4. `## Commits (last 24h)`
5. `## Reflection prompts`
6. `## Links`

## Section: Narrative

**Placeholder present** (`_Write freely. This section belongs to you, not to the system._`):

Replace the placeholder line with the user's paragraph. The placeholder is an invitation, not a keepable artefact.

**Non-empty section**:

Append the new paragraph at the end of the section, separated by one blank line. Preserve every prior paragraph byte-exact.

**Multiple narrative entries in the same day**:

If the user is writing a second distinct entry later in the day, prefix it with a subheading `### HH:MM` (24h local time). This keeps the narrative chronologically readable without needing timestamps on every line. Do **not** timestamp the first entry of the day — the file is already dated.

## Section: Tasks today

The section contains a Dataview query block by default. Do not modify the Dataview block.

User-authored task narrative (e.g. "closed the migration task") goes as a bullet *above* the Dataview block:

```markdown
## Tasks today

- Closed [[migrate_notes_pipeline]] — moved OneNote ingestion into the formal pipeline.

```dataview
TASK FROM "02_Tasks_and_Execution/Active"
...
```
```

## Section: Decisions

Each decision logged today gets one bullet:

```markdown
- [[2026-04-16_import_anthropics_skills]] — dual-track import of anthropics/skills as reference.
```

Idempotency check: if a bullet already links to the same decision note by name, do not add a second bullet.

If the section contains only the placeholder (`_Link decisions logged today under ...`), replace the placeholder with the first bullet.

## Section: Commits (last 24h)

Auto-populated by `doc-tracer` on `/daily`. Human edits to this section are rare; when they happen, use bullets and preserve any existing entries.

If this skill is asked to add commits before `doc-tracer` has run, append bullets of the form:

```markdown
- `abc1234` — short commit message
```

Keep chronological order (oldest first).

## Section: Reflection prompts

The template ships with three numbered prompts. Answers go **inline** under the relevant item:

```markdown
1. What moved today that mattered?
   - The orientation of OmarOS toward skills.
2. What did I learn that I did not know yesterday?
   - That Anthropic considers skills the primary composition unit, above agents.
```

If the user answers a single prompt, only that one is edited. The others stay untouched.

If the user adds a new reflection prompt, append it as item 4+ rather than inserting in the middle (keeps numbering stable across the vault).

## Section: Links

Bullets, each `[[wikilink]]`. The template ships with `[[YYYY-Www]]` and `[[Home]]`. Never duplicate; check for existing identical links before adding.

## Missing-section insertion

If a target heading is missing, insert it with a preceding blank line and a trailing blank line, in its canonical position (see order above). Do not reorder existing sections — only insert the missing one in its correct slot.

## Atomicity

One read, one write. If you must make multiple edits to the same file (e.g. narrative + decisions + frontmatter `updated`), compose them into a single write. Partial writes are a common source of "updated" timestamps that drift from the actual content.
