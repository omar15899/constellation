---
name: outlook-sync
description: Connects to Outlook (personal Microsoft account omar15899@hotmail.com) via the Microsoft Graph API and manages all mail across every folder with a scalable two-tier classifier — deterministic rules first, an LLM for the ambiguous residue — then labels or moves messages, pulls unwanted mail out of the inbox, and rescues good mail from Junk. Verbatim raw landing in 09_Data_Sources/Email_Exports/ AND a semantic morning digest in 11_Documents_and_Reports/Email/. Runs every morning via launchd and supports a one-time retroactive backfill of the whole mailbox. Use this skill when the user says "sync outlook", "ordena mi correo", "clasifica mis correos", "categoriza emails", "limpia el spam", "saca lo no deseado del inbox", "rescata el correo bueno de spam", "actualiza el correo", "organiza el buzón", "etiqueta mis emails", or invokes "/outlook-sync". Idempotent (a message already at its category+folder is skipped), dry-run by default, never deletes a message, and writes an undo manifest for every move. Sibling of calendar-sync / reminders-sync / claude-conversations-sync. Do NOT use for sending mail or for one-off .eml/.mbox file imports.
license: Proprietary. OmarOS internal.
contract_invariants:
- 'Two surfaces: every processed message lands verbatim in 09_Data_Sources/Email_Exports/by_message/<safe_id>.json (raw Graph resource + _omaros classification) AND is summarised in the per-day digest 11_Documents_and_Reports/Email/<YYYY-MM-DD>_inbox_digest.md.'
- 'Two-tier engine: Tier-0 deterministic rules (rules.py over taxonomy.yaml) classify the bulk for free; only the unmatched residue is sent to the Tier-1 LLM, concurrently, via the local `claude -p` subprocess. No API key is ever used.'
- 'Dry-run by default: sync.py and backfill.py compute and log every action but perform NO Graph writes unless --apply is passed. The launchd daemon is the only path that applies by default (guard with OUTLOOK_SYNC_DRYRUN=1).'
- 'Non-destructive: messages are labelled (non-destructive Outlook categories) and at most MOVED between folders. No message is ever deleted or permanently removed. Junk handling moves to the Junk well-known folder; it never hard-deletes.'
- 'Reversible: every move is recorded in an undo manifest under 09_Data_Sources/Email_Exports/backfill/ (undo_sync_<date>.json / undo_backfill_<ts>.json). undo.py reverses any manifest, matching by internetMessageId because a Graph move changes the message id.'
- 'Idempotent + resumable: a message already in the sync state with the same category+folder is skipped — no re-label, no re-move. Backfill apply skips actions whose message already carries the category. Running twice writes nothing new.'
- 'Audit trail: every non-empty batch writes an immutable timestamped snapshot to 09_Data_Sources/Email_Exports/snapshots/ before any classification or write.'
---

# outlook-sync

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Connects to the personal Outlook mailbox (`omar15899@hotmail.com`) through the
Microsoft Graph API, understands every message with a scalable two-tier
classifier, and keeps the inbox clean — labelling mail, moving it into a tidy
`OmarOS/` folder tree, ejecting unwanted mail, and rescuing good mail that landed
in Junk. It runs automatically each morning via launchd and can backfill the
entire mailbox retroactively in one supervised pass.

## Two surfaces

```
09_Data_Sources/Email_Exports/                 ← raw landing zone (Pole A)
├── index.json                                 ← roll-up: {imid: {id, folder, from, subject, received, category, confidence, action}}
├── by_message/<safe_id>.json                  ← latest verbatim Graph message + _omaros classification
├── snapshots/<UTC-timestamp>.json             ← immutable per-batch dumps (only when non-empty)
└── backfill/                                  ← manifests + undo logs
    ├── manifest_<UTC-timestamp>.json / .md     ← retroactive plan (build) + readable summary
    ├── undo_sync_<UTC-date>.json               ← reversible record of every morning move
    └── undo_backfill_<UTC-timestamp>.json      ← reversible record of every backfill move

11_Documents_and_Reports/Email/                ← semantic surface (Pole B)
└── <YYYY-MM-DD>_inbox_digest.md               ← OmarOS frontmatter + counts + Action-category list
```

- **Raw landing** is the byte-faithful Microsoft Graph message resource, one
  file per `internetMessageId`, with the classification verdict attached under
  `_omaros`. Immutable snapshots preserve each batch so the corpus is
  reconstructable even if a later run misbehaves. This is the recovery copy and
  the substrate for Pole A backups.
- **Semantic digest** is the committed, human- and AI-readable surface: a daily
  markdown report (`note_type: report`, `domain: 11_Documents_and_Reports`,
  `tags: [email, digest]`) summarising the counts (fetched, classified,
  labelled, moved, rescued, junked) and listing the messages classified as
  `Action` (the ones that want a reply). Written only when content differs from
  the on-disk file, so Obsidian sees no spurious changes.

## The two-tier engine (the scalability core)

```
Graph message
     │
     ▼
message_features()                       (from, subject, snippet, list-unsubscribe header, folder)
     │
     ▼
Tier-0  RuleClassifier (rules.py)        deterministic, free, confidence 0.95
     │   from_domains / from_addresses / subject_keywords / header_list_unsubscribe
     │   first matching category in taxonomy.yaml wins (order = priority)
     │
     ├── matched ──────────────────────► Classification(source="rule")
     │
     └── unmatched residue ──────────────┐
                                          ▼
Tier-1  LLM (classify.py)                 `claude -p --model <haiku>` subprocess, ThreadPoolExecutor
     │   prompt lists taxonomy ids+descriptions; returns {category, confidence, reason}
     │   invalid category → fallback to Archive (source="fallback", confidence 0.3)
     ▼
Classification(source="llm")
```

Rules handle the bulk of routine mail (banks, employer, university, receipts,
newsletters) for free; only the genuinely ambiguous remainder ever reaches the
model, and that remainder is classified concurrently. The taxonomy is data, not
code: edit `taxonomy.yaml` to add domains, keywords, or whole categories without
touching a line of Python.

### Categories (taxonomy.yaml, priority order)

`Finance` → `Work_Engie` → `Academic_Imperial` → `Receipts` → `Newsletters` →
`Personal` → `Action` → `Junk` → `Archive`. Specific categories precede generic
ones so the first deterministic match is the right one. Each carries an Outlook
preset colour and an optional `target_folder`.

## Label vs move

Two operating modes, set in `~/.config/omaros/outlook.json` (`mode`) or per
invocation with `--mode`:

- **`label`** (default, fully non-destructive) — applies an Outlook master
  category to each message; nothing changes folder except Junk handling.
- **`move`** — additionally relocates non-Junk messages whose category has a
  `target_folder` into `OmarOS/<target_folder>`, but only when confidence ≥
  `move_confidence_threshold` (default 0.85). The `OmarOS/` parent folder and its
  children are created on demand.

## Junk handling

Independent of mode, and always confidence-gated:

- **Eject** — a message classified `Junk` that is *not* already in Junk and
  clears the threshold is moved to the Junk well-known folder.
- **Rescue** — when `rescue_from_junk: true`, a message sitting in Junk that is
  classified as anything *other* than `Junk` and clears the threshold is moved
  back to the Inbox (or its category's `target_folder`).

Every such move is appended to the undo manifest; nothing is deleted.

## Idempotency

State lives at `02_Tasks_and_Execution/Ledger/.sync_state/outlook.json` and
stores, per folder, the Graph `delta_link`, and per `internetMessageId` the last
`{category, folder, action, ts}`. The morning sync uses Graph delta queries, so
it only ever sees what changed since the last run; and a message already in
`processed` with the same category and folder is skipped outright. Running the
sync twice with no mailbox change writes nothing.

## Setup

Authentication is a one-time, interactive device-code login that Omar runs once;
the token cache then lets every subsequent run acquire a token silently. The full
walkthrough — registering nothing (it uses the Microsoft Graph CLI public
client), running `auth.py`, granting the Graph scopes, and the first dry-run — is
in [SETUP.md](SETUP.md). Read it before the first sync.

## Install / uninstall

```bash
# Install (or reinstall) the morning daemon under launchd (default 07:00)
/Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/install_launchd.sh

# Stop and remove
launchctl unload ~/Library/LaunchAgents/com.omaros.outlook-sync.plist
rm ~/Library/LaunchAgents/com.omaros.outlook-sync.plist

# Live logs
tail -f docs/outlook_sync_daemon.log docs/outlook_sync_daemon.err
```

The daemon (`daemon.py`) runs `run_sync` once per `StartCalendarInterval` tick
and **applies** in the configured mode by default. To make a scheduled run
dry-run, set `OUTLOOK_SYNC_DRYRUN=1` in its environment. It catches `GraphError`,
prints a one-line "run auth.py" hint, and exits 0 so launchd never enters a
crash loop.

## Manual invocation

```bash
VENV=~/.venvs/omaros/bin/python
S=/Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts

# One-time interactive login (run once)
$VENV $S/auth.py
$VENV $S/auth.py --status        # is a silent token available?

# Daily sync — DRY RUN by default (classifies + logs, no Graph writes)
$VENV $S/sync.py
$VENV $S/sync.py --apply                 # actually label / move
$VENV $S/sync.py --apply --mode move     # label + relocate into OmarOS/<folder>
$VENV $S/sync.py --folder Inbox --limit 50   # scope to one folder, cap for testing

# Retroactive backfill — build a plan first (never applies without --apply)
$VENV $S/backfill.py                                   # writes manifest_<ts>.json + .md, prints path
$VENV $S/backfill.py --only-folder Inbox --limit-per-folder 200
$VENV $S/backfill.py --apply 09_Data_Sources/Email_Exports/backfill/manifest_<ts>.json

# Reverse any move manifest (matches by internetMessageId; move changes the id)
$VENV $S/undo.py 09_Data_Sources/Email_Exports/backfill/undo_sync_<date>.json
```

## When to use

- Omar wants his mailbox classified, tidied, or de-spammed, on demand.
- Good mail keeps landing in Junk and needs rescuing, or junk keeps landing in
  the Inbox and needs ejecting.
- A first, supervised pass over the entire historical mailbox is wanted
  (backfill — always dry-run first, inspect the markdown manifest, then `--apply`).
- A previous move went wrong and must be reverted (undo).

Do **not** use for:

- Sending or drafting mail (`Sent Items`, `Drafts`, `Outbox` are skipped).
- One-off `.eml` / `.mbox` file imports — that is a different ingestion pipeline.
- Calendar (→ `calendar-sync`) or reminders/tasks (→ `reminders-sync`).

## Out of scope

This skill reads and reorganises mail; it does not compose, reply, forward, or
delete. It never touches Pole A storage beyond writing the raw landing zone and
digest inside the vault, and it never permanently removes a message — the worst
it does is move one between folders, always reversibly.
