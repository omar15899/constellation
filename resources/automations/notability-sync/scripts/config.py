"""Persistent location config for notability-sync.

Edit freely. sync.py imports from here. Rationale lives next to each entry.
"""

from __future__ import annotations

from pathlib import Path

HOME = Path.home()

# -----------------------------------------------------------------------------
# CONFIRMED SOURCES (discovered 2026-04-24 by direct filesystem inspection)
# -----------------------------------------------------------------------------

# OneDrive Standalone client on macOS stores synced content inside a Group
# Container (not ~/Library/CloudStorage/). This is Omar's live OneDrive folder
# for Notability: 6344 .note packages organised by subject. NOTE: the files
# here are Files-On-Demand placeholders by default — they must be materialised
# (Finder → "Always keep on this device", or OneDrive prefs → disable FOD)
# before sync.py can read their real bytes. Placeholder files return zeros.
ONEDRIVE_NOTABILITY = (
    HOME / "Library/Group Containers/UBF8T346G9.OneDriveStandaloneSuite"
         / "OneDrive.noindex/OneDrive/Notability"
)

# Notability's dedicated iCloud container — currently empty on this Mac, but
# reserved for when Auto-Backup is eventually pointed at iCloud.
ICLOUD_NOTABILITY_CONTAINER = (
    HOME / "Library/Mobile Documents/iCloud~com~gingerlabs~Notability/Documents"
)

# Standard iCloud Drive root, for an Auto-Backup folder placed there by hand.
ICLOUD_DRIVE_BACKUP = (
    HOME / "Library/Mobile Documents/com~apple~CloudDocs/Notability_Backup"
)

# -----------------------------------------------------------------------------
# WHICH SOURCES TO SCAN (order = preference when dedup merges)
# -----------------------------------------------------------------------------

DEFAULT_SOURCES = [
    ONEDRIVE_NOTABILITY,
    ICLOUD_NOTABILITY_CONTAINER,
    ICLOUD_DRIVE_BACKUP,
]

# Extra OneDrive paths discovered at runtime via these glob patterns.
ONEDRIVE_GLOBS = [
    str(HOME / "Library/CloudStorage/OneDrive-*/Notability*"),
    str(HOME / "Library/CloudStorage/OneDrive-*/Documents/Notability*"),
    str(HOME / "Library/Group Containers/UBF8T346G9.OneDriveStandaloneSuite"
             / "OneDrive.noindex/OneDrive/Notability*"),
]

# -----------------------------------------------------------------------------
# FORMAT HANDLING
# -----------------------------------------------------------------------------

# Extensions the skill recognises as Notability artefacts.
PDF_EXTS = {".pdf"}
NOTE_EXTS = {".note", ".nbn"}   # .nbn is the modern package variant

# pdftotext binary (poppler). Verified present on this machine.
PDFTOTEXT = "/opt/homebrew/bin/pdftotext"

# Minimum file size (bytes) to treat as a non-placeholder. OneDrive placeholders
# read as all-zeros; we detect + skip them by checking the first 512 bytes.
PLACEHOLDER_PROBE_BYTES = 512
