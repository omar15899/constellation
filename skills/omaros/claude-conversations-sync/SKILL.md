---
name: claude-conversations-sync
description: Automated mirror of every Claude Code (CLI) conversation into OmarOS — a verbatim raw JSONL backup in 09_Data_Sources/Claude_Conversations/raw/ (gitignored) AND a readable, secret-redacted markdown transcript per session in 09_Data_Sources/Claude_Conversations/rendered/, plus a manifest.json index. Runs as a launchd-managed daemon polling ~/.claude/projects every 120s (configurable). Use when the user says "guarda mis conversaciones con Claude", "archiva los chats de Claude", "sync claude conversations", "back up my Claude sessions", "actualiza el archivo de conversaciones", or whenever the transcript archive needs a manual refresh. CLI sessions only — claude.ai web/desktop is not stored locally.
---

# claude-conversations-sync

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Every Claude Code session is persisted by the CLI as a JSON-lines transcript at
`~/.claude/projects/<encoded-cwd>/<sessionId>.jsonl`. This skill mirrors all of
them into the vault and keeps the mirror live.

## Two surfaces

```
09_Data_Sources/Claude_Conversations/
├── README.md                                          ← explains both surfaces
├── manifest.json                                      ← per-session index [committed]
├── raw/<project>/<sessionId>.jsonl                    ← verbatim mirror [GITIGNORED]
└── rendered/<project>/YYYY-MM-DD_<sid8>_<title>.md    ← readable transcript [committed]
```

- **raw/** is a byte-faithful backup of the source transcript. It is gitignored
  (the corpus is ~800 MB and grows continuously) but lives in the vault so it is
  swept up by Pole A backups (NAS / cloud). If `~/.claude` is ever cleared, this
  is the recovery copy.
- **rendered/** is the committed, human- and AI-readable surface: YAML
  frontmatter (`note_type: claude_conversation`) + merged user/assistant turns,
  with tool calls collapsed to one-liners and `thinking` blocks omitted. Secrets
  are redacted before this surface is written.
- **manifest.json** indexes every session: title, project, cwd, branch, turn
  counts, timestamps, rendered path, redaction flag.

## Pipeline

1. **`scan.py`** — stat every `*.jsonl` under `~/.claude/projects`, derive the
   project slug from the directory name. Cheap; reads no file content.
2. **`render.py`** — parse one transcript's JSONL into markdown. Drops
   harness-injected meta turns (`isMeta`, `<local-command-caveat>`,
   `<system-reminder>`…), merges consecutive same-role messages, collapses
   `tool_use`/`tool_result`, redacts secrets (`sk-…`, `ghp_…`, `Bearer …`,
   `api_key=…`, AWS keys, private-key headers).
3. **`sync.py`** — orchestrates scan → incremental diff → raw mirror → render →
   manifest. Writes only changed files (content-compared before write).
4. **`daemon.py`** — launchd-managed poll loop, default 120 s, single-flight,
   self-throttling.

## Idempotency

State lives at
`02_Tasks_and_Execution/Ledger/.sync_state/claude_conversations.json` and stores,
per source path: `mtime`, `size`, `rendered_path`. A transcript is re-rendered
only when its `(mtime, size)` changes. Running the sync twice with no new
Claude activity writes nothing. The markdown writer compares against the on-disk
file before writing, so Obsidian does not see spurious changes.

## Install / uninstall

```bash
# Install (or reinstall) the daemon under launchd
/Users/omarkhalil/GitHub/Constellation/skills/omaros/claude-conversations-sync/scripts/install_launchd.sh

# Stop and remove
launchctl unload ~/Library/LaunchAgents/com.omaros.claude-conversations-sync.plist
rm ~/Library/LaunchAgents/com.omaros.claude-conversations-sync.plist

# Live logs
tail -f docs/claude_conversations_sync_daemon.log docs/claude_conversations_sync_daemon.err
```

## Manual invocation

```bash
VENV=~/.venvs/omaros/bin/python
S=/Users/omarkhalil/GitHub/Constellation/skills/omaros/claude-conversations-sync/scripts

# Full incremental sync (no commit)
$VENV $S/sync.py

# Dry run: classify only, no writes
$VENV $S/sync.py --dry-run

# Authorized local backfill; keep all transcript artifacts private
$VENV $S/sync.py

# Restrict to one project, or to recent sessions
$VENV $S/sync.py --project OmarOS
$VENV $S/sync.py --since 2026-05-01

# Re-render everything from scratch (ignore state)
$VENV $S/sync.py --force

# Inspect the source corpus
$VENV $S/scan.py

# Render a single transcript to stdout
$VENV $S/render.py ~/.claude/projects/-Users-omarkhalil-OmarOS/<sid>.jsonl
```

## Privacy and publication

Raw and rendered conversations, manifests, synchronization state and daemon logs
are local-only private data. Never stage, commit, push, upload, attach or transmit
them unless Omar explicitly names the exact data and destination. Ordinary
archive or refresh permission does not grant publication permission. Do not use
`--commit` or enable `CCSYNC_COMMIT`; preserve the existing private archive and
verify that the selected operation keeps it out of Git.

## Configuration (env vars)

| Var | Default | Meaning |
|---|---|---|
| `CCSYNC_INTERVAL` | `120` | daemon poll interval, seconds |
| `CCSYNC_COMMIT` | unset | Keep unset; transcript publication is outside this method |
| `CCSYNC_EXTRA_FLAGS` | empty | extra flags appended to every `sync.py` run |

## Out of scope

- **claude.ai web / desktop conversations.** They are not persisted locally;
  there is no automatable source. Manual exports would be a future ingest path.
- **Outbound edits.** The source `~/.claude/projects` tree is read-only here.
- **Semantic search over transcripts.** Requires an explicit private-archive scope; do not feed transcripts into general vault search or publication.
- **`thinking` retention.** Omitted by default (`--include-thinking` to keep).
