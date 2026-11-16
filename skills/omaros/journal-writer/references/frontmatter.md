# Daily-note frontmatter — required fields

Use this frontmatter shape for `note_type: daily_note`. Validate the resulting note against the current OmarOS profile and schema before review; a documented shape does not establish that a native hook executed.

## Required fields

| Field       | Type        | Rule                                                                 |
| ----------- | ----------- | -------------------------------------------------------------------- |
| `title`     | string      | Quoted ISO date, e.g. `"2026-04-16"`.                                |
| `note_type` | enum        | Must be exactly `daily_note`.                                        |
| `status`    | enum        | One of `active`, `archived`. Daily notes start `active`.             |
| `created`   | date        | ISO date `YYYY-MM-DD`. Never changes after creation.                 |
| `updated`   | datetime    | ISO `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`. Bumped on every edit.     |
| `author`    | string      | `Omar`.                                                              |
| `tags`      | list[str]   | Must contain `daily` and `journal`. Other tags may be added.         |

## Optional fields

| Field     | Type   | Rule                                                   |
| --------- | ------ | ------------------------------------------------------ |
| `mood`    | string | Free text or empty. If empty, leave as `mood:` with no value. |
| `energy`  | string | Free text or empty. Same convention.                   |
| `weather` | string | Free text or empty. Same convention.                   |

## Rules

- **Never remove** a field once present, even if empty. The enforcer treats missing keys as schema violations, not null values.
- **Never overwrite** a user-supplied `mood` / `energy` / `weather` value. If the user said "mood: calm" yesterday, don't reset it to empty today — but this is for *today's* note only; you never touch prior days' notes here.
- `updated` is a strict monotonic field. Always greater than or equal to the previous value. If the file says `updated: 2026-04-16T23:45:00` and you are appending at 21:00 (because the clock is wrong or you are replaying), use the existing value + 1 second rather than going backwards.
- `tags` is an append-only list. Never remove `daily` or `journal`.

## Canonical block for a new note

```yaml
---
title: "2026-04-16"
status: active
note_type: daily_note
created: 2026-04-16
updated: 2026-04-16
author: Omar
tags: [daily, journal]
mood:
energy:
weather:
---
```

## Validation reference

Source of truth: `19_Metadata_and_Schema/Frontmatter_Standards/` and `19_Metadata_and_Schema/Status_Enums/`. If a field's enum changes upstream, update the schema files first and let the enforcer pick up the change — do not work around it at write time.
