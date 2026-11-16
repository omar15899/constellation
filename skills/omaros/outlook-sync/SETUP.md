# outlook-sync — Setup Runbook

A step-by-step guide to wire the OmarOS Outlook email pipeline to the personal
Microsoft account `omar15899@hotmail.com`, run the first dry-run, apply labels,
optionally switch to move mode, run the retroactive backfill, and install the
07:00 launchd daemon.

Everything in this pipeline is **reversible** and **nothing is ever permanently
deleted**. Labels are non-destructive metadata. Moves are recorded into undo
manifests and reversed by `undo.py`. There is no delete path anywhere in the
code — at most a message is moved to the Junk folder (where Outlook keeps it for
weeks) or rescued out of Junk back to the Inbox.

---

## Conventions

- The canonical Python interpreter for everything OmarOS is the vault venv:
  `/Users/omarkhalil/.venvs/omaros/bin/python` (Python 3.12).
- Skill scripts live in:
  `/Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts`
- Config + token cache live in `~/.config/omaros/`.
- Raw email landing lands in `09_Data_Sources/Email_Exports/`.
- Run every command below from any directory — the scripts use absolute paths
  internally and resolve the vault root from their own location.

For brevity, set two shell variables for this session:

```bash
PY=/Users/omarkhalil/.venvs/omaros/bin/python
SKILL=/Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync
```

---

## Step 0 — App registration (OPTIONAL — skip for zero setup)

The pipeline ships with a built-in **public client id** that works out of the
box with personal Microsoft accounts (MSA) via the device-code flow:

```
DEFAULT_PUBLIC_CLIENT_ID = 14d82eec-204b-4c2f-b7e8-296a70dab67e
```

This is the Microsoft Graph CLI public client. It requires **no Azure setup**.
If you are happy using it, **skip to Step 1**.

If you prefer your own app registration (cleaner consent screen, your own
client id), do the following in the [Microsoft Entra admin center](https://entra.microsoft.com):

1. Go to **Identity → Applications → App registrations → New registration**.
2. Name it e.g. `OmarOS Outlook Sync`.
3. Under **Supported account types**, choose
   **Personal Microsoft accounts only**.
4. Leave **Redirect URI** empty (device-code flow needs none).
5. Click **Register**, then copy the **Application (client) ID** from the
   overview page.
6. Under **Authentication → Advanced settings**, set
   **Allow public client flows = Yes** (required for device-code flow).
7. Under **API permissions**, add the delegated Microsoft Graph permissions:
   `Mail.ReadWrite`, `MailboxSettings.ReadWrite`, `User.Read`. No admin consent
   is needed for personal accounts — you consent at first login.

Put the copied client id into the config file in Step 2 (`client_id`).

---

## Step 1 — Install the one dependency (`msal`)

The pipeline depends only on stdlib + `httpx` + `msal` + `pyyaml`. `httpx` and
`pyyaml` are already in the OmarOS venv; install `msal`:

```bash
uv pip install --python /Users/omarkhalil/.venvs/omaros/bin/python msal
```

Verify:

```bash
/Users/omarkhalil/.venvs/omaros/bin/python -c "import msal, httpx, yaml; print('ok', msal.__version__)"
```

---

## Step 2 — Create the config file (OPTIONAL — defaults work)

If you skipped Step 0 and accept the built-in public client, you can **skip this
step entirely** — `load_config()` returns sensible defaults (public client id,
`tenant=consumers`, label mode) when the file is missing.

To pin an explicit config (recommended if you registered your own app), create
`~/.config/omaros/outlook.json`:

```bash
mkdir -p ~/.config/omaros
```

Then write `~/.config/omaros/outlook.json` with content like:

```json
{
  "client_id": "14d82eec-204b-4c2f-b7e8-296a70dab67e",
  "tenant": "consumers",
  "username": "omar15899@hotmail.com",
  "mode": "label",
  "move_confidence_threshold": 0.85,
  "model": "claude-haiku-4-5-20251001",
  "escalation_model": "claude-sonnet-4-6",
  "schedule_hour": 7,
  "schedule_minute": 0,
  "skip_folders": ["Sent Items", "Drafts", "Outbox"]
}
```

Notes:

- `tenant` must be `consumers` for a personal Microsoft account. Do **not** use
  `common` or `organizations`.
- If you used your own app registration in Step 0, replace `client_id` with the
  Application (client) ID you copied.
- `mode` starts at `label` (non-destructive). You switch it to `move` later
  once you trust the classification.
- `username` is filled in automatically after the first successful login, so it
  is fine to omit it now.

---

## Step 3 — Authenticate once (device-code browser login)

Run the interactive auth script. It prints a short URL and a one-time code;
open the URL, paste the code, and sign in as `omar15899@hotmail.com`.

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/auth.py
```

The terminal will show something like:

```
To sign in, use a web browser to open the page https://microsoft.com/devicelogin
and enter the code ABCD-EFGH to authenticate.
```

Complete the login and grant the requested permissions (`Mail.ReadWrite`,
`MailboxSettings.ReadWrite`, `User.Read`). On success the script:

- writes the token cache to `~/.config/omaros/outlook_token_cache.bin` (chmod 600),
- updates `~/.config/omaros/outlook.json` with your `username`,
- prints the signed-in account.

Verify a silent token is available (does **not** prompt):

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/auth.py --status
```

You only need to do this once. The token cache holds a refresh token, so all
later runs (including the daemon) acquire tokens silently. If the cache is ever
invalidated (password change, long inactivity), just re-run `auth.py`.

---

## Step 4 — Preview with a dry run (no writes)

The sync defaults to dry-run: it fetches mail, classifies it, writes the raw
landing + index, but performs **no Graph writes** (no labels, no moves). Start
small with a limit and a single folder to sanity-check, then run the full
preview.

Small probe (Inbox only, 25 messages):

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/sync.py \
  --folder Inbox --limit 25
```

Full preview across all folders (still dry-run):

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/sync.py
```

This prints a concise summary (folders, fetched, classified, and the actions it
*would* take) without touching the mailbox.

---

## Step 5 — Review the classification

Inspect what the dry run decided before applying anything:

- **Roll-up index:** `09_Data_Sources/Email_Exports/index.json`
  — one entry per message: folder, from, subject, received, category,
  confidence, proposed action.
- **Per-message raw + decision:**
  `09_Data_Sources/Email_Exports/by_message/<safe_id>.json`
  — the full Graph message plus the `_omaros` classification block.
- **Immutable batch snapshots:**
  `09_Data_Sources/Email_Exports/snapshots/<UTC timestamp>.json`.
- **Morning digest:**
  `11_Documents_and_Reports/Email/<YYYY-MM-DD>_inbox_digest.md`
  — counts plus the list of `Action`-category messages needing a reply.

The classification engine is two-tier: deterministic rules in `taxonomy.yaml`
handle the bulk for free; only the ambiguous residue is sent to the local
`claude` CLI. If you disagree with a systematic decision, edit the rules
(domains / keywords / priority order) in:

```
/Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/taxonomy.yaml
```

then re-run the dry run from Step 4.

---

## Step 6 — Apply (label mode first)

When the preview looks right, apply. In **label mode** the pipeline only stamps
Outlook categories (non-destructive metadata) and performs Junk handling
(move spam to the Junk folder, rescue good mail out of Junk). No mail is moved
into your category folders yet.

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/sync.py \
  --apply --mode label
```

The run is **idempotent**: a message already recorded in the sync state with the
same category and folder is skipped — re-running performs no extra writes.

Every move (Junk / rescue) is recorded into an undo manifest under
`09_Data_Sources/Email_Exports/backfill/undo_sync_<UTC date>.json`. To reverse a
run:

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/undo.py \
  /Users/omarkhalil/OmarOS/09_Data_Sources/Email_Exports/backfill/undo_sync_<UTC date>.json
```

`undo.py` matches each message by its stable `internetMessageId` (a move changes
the Graph id), moves it back to its original folder, and restores its previous
categories. Entries it cannot locate are skipped and reported — it never errors
out mid-run.

### Switching to move mode (optional, later)

Once you trust the labels and want category folders auto-populated under an
`OmarOS` parent folder in your mailbox, switch to **move mode**. Messages move
only when their confidence is at or above `move_confidence_threshold` (default
0.85). Either set `"mode": "move"` in `~/.config/omaros/outlook.json`
permanently, or override per-run:

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/sync.py \
  --apply --mode move
```

Move mode also creates the target folders (`OmarOS/Personal`, `OmarOS/Action`,
`OmarOS/Archive`, etc.) on demand. All moves go into the same undo manifest and
are fully reversible.

---

## Step 7 — Retroactive backfill (one-time, dry-run first)

The daily sync only sees new mail (it tracks per-folder delta links). To
classify and act on **all existing mail** across every folder, run the backfill.
It always builds a dry-run manifest first and **never applies without `--apply`**.

Build the dry-run manifest (no writes; iterates all folders):

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/backfill.py
```

This prints the path of the generated manifest, e.g.
`09_Data_Sources/Email_Exports/backfill/manifest_<UTC timestamp>.json`, plus a
human-readable summary at `manifest_<UTC timestamp>.md` (counts table + a
sample of proposed actions). Review both.

Optionally scope or cap the build for a first pass:

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/backfill.py \
  --only-folder Inbox --limit-per-folder 100
```

When satisfied, apply that exact manifest:

```bash
/Users/omarkhalil/.venvs/omaros/bin/python \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/backfill.py \
  --apply /Users/omarkhalil/OmarOS/09_Data_Sources/Email_Exports/backfill/manifest_<UTC timestamp>.json
```

The apply step is **idempotent and resumable** — actions whose message already
carries the target category are skipped, so you can safely re-run it if it is
interrupted. It writes its own undo manifest
`backfill/undo_backfill_<UTC timestamp>.json`, reversible with `undo.py` exactly
as in Step 6.

---

## Step 8 — Install the 07:00 launchd daemon

Install the LaunchAgent so the sync runs every morning at the time configured in
`outlook.json` (`schedule_hour` / `schedule_minute`, default 07:00):

```bash
/Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync/scripts/install_launchd.sh
```

The daemon (`daemon.py`) **applies** in the configured mode by default. To make
it preview-only, set the environment override `OUTLOOK_SYNC_DRYRUN=1` (the
installer or the plist documents where). The daemon prints one timestamped
summary line per run to its launchd log, and on a `GraphError` it prints a
"run auth.py" hint and exits cleanly (exit 0) so launchd never crash-loops.

Manage the agent:

```bash
# verify it is loaded
launchctl list | grep -i outlook

# trigger a run immediately (uses the label/qualifier the installer assigned)
launchctl start com.omaros.outlook-sync

# stop / unload
launchctl unload ~/Library/LaunchAgents/com.omaros.outlook-sync.plist
```

If a morning run reports a token error, re-run `auth.py` (Step 3) to refresh the
cache.

---

## Reversibility & safety summary

- **Labels** are Outlook categories — pure metadata. Removing them undoes
  nothing destructive.
- **Moves** (category folders, Junk, rescue) are recorded into undo manifests in
  `09_Data_Sources/Email_Exports/backfill/`. Reverse any run with `undo.py`
  passing the corresponding `undo_*.json`.
- **Nothing is ever permanently deleted.** The pipeline has no delete path. The
  most aggressive action is moving spam into the Junk folder, where it remains
  recoverable.
- **Dry-run is the default** for `sync.py` and for building backfill manifests;
  writes only happen with `--apply`.
- **Idempotent:** re-running produces no duplicate labels or moves.
- **Raw landing is immutable:** every batch is snapshotted under
  `snapshots/` with a UTC timestamp, so you always have the verbatim source
  state of every message the pipeline touched.

---

## Quick reference

| Action | Command |
| ------ | ------- |
| Install dep | `uv pip install --python $PY msal` |
| Authenticate | `$PY $SKILL/scripts/auth.py` |
| Auth status | `$PY $SKILL/scripts/auth.py --status` |
| Dry-run preview | `$PY $SKILL/scripts/sync.py` |
| Apply labels | `$PY $SKILL/scripts/sync.py --apply --mode label` |
| Apply moves | `$PY $SKILL/scripts/sync.py --apply --mode move` |
| Backfill manifest | `$PY $SKILL/scripts/backfill.py` |
| Apply backfill | `$PY $SKILL/scripts/backfill.py --apply <manifest.json>` |
| Undo a run | `$PY $SKILL/scripts/undo.py <undo_*.json>` |
| Install daemon | `$SKILL/scripts/install_launchd.sh` |

where `PY=/Users/omarkhalil/.venvs/omaros/bin/python` and
`SKILL=/Users/omarkhalil/GitHub/Constellation/skills/omaros/outlook-sync`.
