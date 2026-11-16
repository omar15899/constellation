---
name: codex-conversations-sync
description: Private, lossless local archive of locally persisted Codex conversations. Mirrors native rollout JSONL from ~/.codex/sessions and ~/.codex/archived_sessions into a private raw corpus and creates secret-redacted readable Markdown under 09_Data_Sources/Codex_Conversations. Runs incrementally through launchd. Use when Omar asks to save, archive, back up, refresh, or inspect Codex conversations. The archive is local-only and never auto-commits transcript content.
license: Proprietary. OmarOS internal.
---

# Codex conversations sync

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Mirror every locally persisted Codex rollout without confusing local retention, account privacy, and model-training controls.

## Storage contract

```text
~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl       read-only source
~/.codex/archived_sessions/**/*.jsonl            read-only source
        │
        ├── ~/OmarOS_RawData/codex-conversations-raw/<project>/<id>.jsonl
        │       byte-faithful, mode 600, outside the vault
        │
        └── 09_Data_Sources/Codex_Conversations/
                README.md                          committed documentation only
                manifest.json                     local-only, gitignored
                rendered/<project>/*.md            local-only, gitignored, redacted
```

Incremental state lives at `02_Tasks_and_Execution/Ledger/.sync_state/codex_conversations.json` and is local-only.

## Privacy invariants

1. Never read `~/.codex/auth.json`, credentials, keychains, `.env` files, or account databases.
2. Treat the raw JSONL as sensitive. Create its directories with mode `700` and files with mode `600`.
3. Never stage, commit, push, upload, or attach raw, rendered, manifest, state, or daemon-log content.
4. Render only user-visible user/assistant turns. Encrypted reasoning remains only in the raw local copy.
5. Redact common API keys, bearer tokens, GitHub tokens, Slack tokens, AWS access keys, and private-key blocks from Markdown.
6. The sync is one-way. Never edit or delete a source rollout.
7. Local archival does not change OpenAI account data controls. ChatGPT training opt-out remains an account-level setting.

## Pipeline

1. `scan.py` recursively stats `*.jsonl` below `~/.codex/sessions` and `~/.codex/archived_sessions`; it does not read content.
2. `sync.py` skips unchanged `(mtime, size)` fingerprints.
3. Changed files are parsed with `render.py`, then copied atomically to the raw store.
4. Human-visible messages are rendered into redacted Markdown.
5. Manifest and incremental state are written atomically.
6. `daemon.py` repeats the operation every 120 seconds under launchd.

The source filename supplies the session identifier, including the final UUID
in fork filenames containing an ancestor UUID. Only the first `session_meta`
record supplies session metadata. Later inherited records must never replace
the identifier or cause separate conversations to overwrite one raw archive.
After upgrading identity handling, run `sync.py --force` once to repair the
existing incremental archive from the surviving local sources.

This pipeline covers Codex rollouts available on this Mac and previously
mirrored sessions. It does not fetch ChatGPT web/mobile history, API application
logs, or conversations on other devices without local rollouts. Those require
a separate available source or an explicit export; do not claim total OpenAI
history coverage from this mirror alone.

## Commands

```bash
PY="$HOME/.venvs/omaros/bin/python"
S="$HOME/OmarOS//Users/omarkhalil/GitHub/Constellation/skills/omaros/codex-conversations-sync/scripts"

# Inspect the source corpus without reading message bodies
"$PY" "$S/scan.py"

# Verify the incremental pipeline without writing
"$PY" "$S/sync.py" --dry-run

# Backfill or refresh now
"$PY" "$S/sync.py"

# Reprocess every rollout
"$PY" "$S/sync.py" --force

# Restrict the refresh
"$PY" "$S/sync.py" --project OmarOS
"$PY" "$S/sync.py" --since 2026-07-01

# Install or replace the launchd service
"$S/install_launchd.sh"
```

Set `CODEXSYNC_RAW_DIR` before installation to choose a different private raw location. The default is `~/OmarOS_RawData/codex-conversations-raw/`.

## Validation

```bash
for test_file in "$HOME/OmarOS//Users/omarkhalil/GitHub/Constellation/skills/omaros/codex-conversations-sync/tests"/test_*.py; do
  "$PY" "$test_file"
done

plutil -lint \
  "$HOME/OmarOS//Users/omarkhalil/GitHub/Constellation/skills/omaros/codex-conversations-sync/launchd/com.omaros.codex-conversations-sync.plist"

launchctl print "gui/$(id -u)/com.omaros.codex-conversations-sync"
```

After installation, verify that a second unchanged sync reports `processed=0`, that transcript files are ignored by Git, and that the daemon logs contain no message bodies.

## Account privacy boundary

The daemon guarantees only local archive behavior. For consumer ChatGPT/Codex accounts, the account-level **Settings → Data Controls → Improve the model for everyone** switch governs training use. The Codex configuration additionally disables OTel export, prompt logging, feedback submission, and Memories, but none of those settings substitutes for the account-level switch.
