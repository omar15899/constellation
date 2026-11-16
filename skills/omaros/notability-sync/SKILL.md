---
name: notability-sync
description: Reactive, lossless, hash-deduped mirror of every PDF exported by Notability's Auto-Backup into OmarOS — from both iCloud Drive and OneDrive destinations simultaneously. Lands raw PDFs in 09_Data_Sources/Notability/pdfs/ and writes a searchable .md sidecar per PDF (frontmatter + pdftotext output) in 09_Data_Sources/Notability/sidecars/ so fast-finder can grep inside handwritten notes. Runs reactively via launchd WatchPaths — fires within seconds of Notability writing a new or updated PDF. Idempotent (same PDF content → zero writes). Use this skill when the user says "sync notability", "pull notability pdfs", "update my notability mirror", "actualiza los apuntes de notability", "import notability", or invokes /notability-sync. Do NOT use for one-off .note bundle imports (→ ingestion-notability agent) or for importing PDFs from other sources (→ ingestion-notes).
license: Proprietary. OmarOS internal.
contract_invariants:
- 'Hash identity: each PDF is keyed by sha256(bytes). The same content from iCloud and OneDrive is one entry, not two. Renames in Notability preserve identity.'
- 'Raw verbatim: pdfs/ holds an unmodified byte-for-byte copy of every PDF Notability produces. The original filename is preserved; collisions on filename are disambiguated by short hash suffix.'
- 'Sidecar coupling: every pdfs/<name>.pdf has a sidecar sidecars/<name>.md with YAML frontmatter (hash, sources, mtime, title slug) + plain-text body extracted via pdftotext. The sidecar is what fast-finder indexes.'
- 'Immutable snapshot: every sync run writes snapshots/YYYY-MM-DD_HHMMSS.json containing {hash, filename, sources, mtime, bytes} for every PDF seen that run — persists even if the rest of the sync crashes.'
- 'No silent deletion: a PDF that disappears from both sources is reported as ''missing from remote'' in the state file but its pdf + sidecar are preserved in the vault (audit history).'
- 'Reactive trigger: a launchd LaunchAgent with WatchPaths on the iCloud and OneDrive Notability Auto-Backup folders invokes sync.py within seconds of any filesystem event there. The periodic fallback (StartInterval) is a safety net, not the primary mechanism.'
---

# Notability Sync

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Reactive PDF mirror from Notability Auto-Backup into OmarOS.

## Why this exists

Notability's internal format is a proprietary sandboxed sqlite + binary blob
store that is not stable, not readable, and not legally extractable. The one
clean contract Notability offers is **Auto-Backup**: it will export a PDF
copy of every note into one or more cloud destinations (iCloud Drive,
OneDrive, Google Drive, Dropbox, Box), refreshed whenever the note changes.

This skill consumes that contract. It assumes Auto-Backup is configured with
**PDF format** to either iCloud, OneDrive, or both. Everything upstream of
that is Notability's responsibility.

## Pipeline

```
Notability app (Mac/iPad/iPhone)
       │  (Auto-Backup, PDF format)
       ▼
┌──────────────────────┐     ┌──────────────────────┐
│ iCloud Drive         │     │ OneDrive             │
│   Notability_Backup/ │     │   Notability_Backup/ │
└──────────┬───────────┘     └──────────┬───────────┘
           │                            │
           └────────────┬───────────────┘
                        ▼
                  launchd WatchPaths
                        │
                        ▼
                  scripts/sync.py
                        │
     ┌──────────────────┼──────────────────┐
     ▼                  ▼                  ▼
 pdfs/<name>.pdf   sidecars/<name>.md  snapshots/<ts>.json
 (verbatim)        (frontmatter +      (immutable audit)
                    pdftotext body)
                        │
                        ▼
               .sync_state.json  (hash → {filename, sources, mtime})
                        │
                        ▼
               index.json  (roll-up for dashboard + fast-finder)
```

## First-time setup (one-time, manual by Omar)

1. **Enable Auto-Backup in Notability.** Settings → Manage Accounts →
   Auto-Backup. Set:
   - Format: **PDF**
   - Destination 1: **iCloud** → folder `Notability_Backup/`
   - Destination 2: **OneDrive** → folder `Notability_Backup/`
2. **Install the LaunchAgent.**
   ```bash
   bash /Users/omarkhalil/GitHub/Constellation/skills/omaros/notability-sync/scripts/install_launchd.sh
   ```
   This copies `launchd/com.omaros.notability-sync.plist` into
   `~/Library/LaunchAgents/` and loads it. From that moment any filesystem
   event in either backup folder fires `sync.py`.
3. **Grant Full Disk Access** to `/bin/bash` (or to the LaunchAgent's
   executable) in System Settings → Privacy & Security, if the agent
   reports permission errors reading the cloud folders.

## Invocation (manual)

```bash
# Full sync (all sources → vault)
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/notability-sync/scripts/sync.py

# Dry-run — scan sources, plan actions, write nothing
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/notability-sync/scripts/sync.py --dry-run

# Skip sidecar regeneration (faster; useful when pdftotext is slow)
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/notability-sync/scripts/sync.py --no-sidecar

# Explicit source paths (override auto-discover)
uv run /Users/omarkhalil/GitHub/Constellation/skills/omaros/notability-sync/scripts/sync.py \
    --source ~/Library/Mobile\ Documents/com~apple~CloudDocs/Notability_Backup \
    --source ~/Library/CloudStorage/OneDrive-Personal/Notability_Backup
```

## Source auto-discovery

`sync.py` looks in these locations by default, accepting any that exist:

- `~/Library/Mobile Documents/com~apple~CloudDocs/Notability_Backup/`
- `~/Library/Mobile Documents/iCloud~com~gingerlabs~Notability/Documents/`
- `~/Library/CloudStorage/OneDrive-Personal/Notability_Backup/`
- `~/Library/CloudStorage/OneDrive-<tenant>/Notability_Backup/` (glob)

Missing sources are skipped silently. Having only one source is legal.

## Data layout

```
09_Data_Sources/Notability/
├── README.md
├── index.json                            roll-up: hash → metadata
├── .sync_state.json                      hash → {filename, sources, mtime, last_seen}
├── pdfs/
│   └── <original_filename>.pdf           verbatim, byte-faithful
├── sidecars/
│   └── <original_filename>.md            frontmatter + pdftotext body
└── snapshots/
    └── YYYY-MM-DD_HHMMSS.json            immutable per-run audit
```

## Sidecar format

```yaml
---
title: "<slug derived from PDF filename>"
note_type: external_artifact
domain: 09_Data_Sources
subdomain: Notability
source: notability
source_path: "Notability_Backup/Math/banach_spaces.pdf"
source_clouds: [icloud, onedrive]
sha256: "<64-hex>"
bytes: 1234567
pdf_mtime: "2026-04-24T12:34:56"
synced_at: "2026-04-24T12:35:02"
ai_generated: false
tags: [notability, pdf, handwritten]
---

# Extracted text

<pdftotext output — one blank line between pages>
```

The sidecar is a first-class vault note: indexed by fast-finder, linkable by
wikilink, and searchable by full text. The canonical artefact is still the
PDF; the sidecar exists so the PDF's content is not opaque to the rest of
OmarOS.

## Dedup semantics

1. **Hash** (primary). `sha256(pdf_bytes)` is the stable identity. Two files
   with identical content — same PDF in iCloud and OneDrive, or a PDF that
   Notability renamed — resolve to one entry. Sources are merged in state as
   a set.
2. **Filename collision**. Two PDFs with the same filename but different
   hashes → second one lands as `<name>__<hash8>.pdf` to keep both. Rare.
3. **Content change**. Same filename, different hash → overwritten in place,
   previous hash recorded in snapshot for audit.

## State file

`09_Data_Sources/Notability/.sync_state.json`:

```json
{
  "version": 1,
  "last_sync": "2026-04-24T12:34:56",
  "entries": {
    "<sha256>": {
      "filename": "banach_spaces.pdf",
      "sources": ["icloud", "onedrive"],
      "mtime": "2026-04-24T12:30:00",
      "bytes": 1234567,
      "last_seen": "2026-04-24T12:34:56"
    }
  }
}
```

Idempotently rewritten. Hand-editable.

## Reactive trigger details

The LaunchAgent plist uses `WatchPaths` on the Auto-Backup folders and a
conservative `StartInterval` of 1800 s as a safety net in case WatchPaths
misses an event (it occasionally does on macOS cloud-provider folders).
`ThrottleInterval` is 30 s so rapid bursts of file writes (Notability often
rewrites all PDFs during a sync) collapse into a single sync run.

## Risk classification

Low. The skill is read-only against cloud folders and only writes inside
`09_Data_Sources/Notability/`, which is a designated landing zone. No
destructive operations. Failed runs leave partial state but the next
successful run reconciles.

## Dependencies

- `pdftotext` (poppler). Verified present at `/opt/homebrew/bin/pdftotext`.
- Python 3 stdlib only for `sync.py` (no external packages).
- macOS launchd for reactive triggering.

## Cross-references

- `/Users/omarkhalil/GitHub/Constellation/skills/omaros/reminders-sync/SKILL.md` — sibling pattern (Apple Reminders).
- For one-shot `.note` imports, inspect the available import tools and preserve the same source and privacy boundaries.
- `CLAUDE.md` §7 — this skill is INFRA + INGEST.
