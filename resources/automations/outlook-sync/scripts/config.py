from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VAULT_ROOT = Path(os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS")))

RAW_DIR = Path(
    os.environ.get(
        "OUTLOOK_EXPORT_DIR", VAULT_ROOT / "09_Data_Sources" / "Email_Exports"
    )
)
BY_MESSAGE_DIR = RAW_DIR / "by_message"
SNAPSHOTS_DIR = RAW_DIR / "snapshots"
BACKFILL_DIR = RAW_DIR / "backfill"
INDEX_PATH = RAW_DIR / "index.json"

DIGEST_DIR = VAULT_ROOT / "11_Documents_and_Reports" / "Email"
SYNC_STATE_PATH = VAULT_ROOT / "02_Tasks_and_Execution" / "Ledger" / ".sync_state" / "outlook.json"

TAXONOMY_PATH = SKILL_DIR / "taxonomy.yaml"

CONFIG_DIR = Path.home() / ".config" / "omaros"
CONFIG_PATH = CONFIG_DIR / "outlook.json"
TOKEN_CACHE_PATH = CONFIG_DIR / "outlook_token_cache.bin"

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
AUTHORITY_TEMPLATE = "https://login.microsoftonline.com/{tenant}"
SCOPES = ["Mail.ReadWrite", "MailboxSettings.ReadWrite", "User.Read"]

DEFAULT_PUBLIC_CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
ESCALATION_MODEL = "claude-sonnet-4-6"
# Haiku handles the bulk; only LLM verdicts below this confidence are re-asked
# to the (stronger, slower) escalation model. Set high enough that escalation
# stays rare — empirically ~1% of the LLM residue.
ESCALATION_CONFIDENCE_THRESHOLD = 0.70

MOVE_CONFIDENCE_THRESHOLD = 0.85
# Pulling mail OUT of Junk back into the user's view is the only direction that
# can surface spam, so it demands a much higher bar than an ordinary move.
RESCUE_CONFIDENCE_THRESHOLD = 0.95
ROOT_FOLDER_NAME = "OmarOS"

# Outgoing/system folders to skip, by language-independent well-known name.
# (Display-name skipping via OutlookConfig.skip_folders is locale-specific and
# misses non-English mailboxes, e.g. "Elementos enviados".)
SKIP_WELL_KNOWN = {"sentitems", "drafts", "outbox"}

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]")


@dataclass
class OutlookConfig:
    client_id: str = DEFAULT_PUBLIC_CLIENT_ID
    tenant: str = "consumers"
    username: str | None = None
    mode: str = "label"
    move_confidence_threshold: float = MOVE_CONFIDENCE_THRESHOLD
    rescue_threshold: float = RESCUE_CONFIDENCE_THRESHOLD
    model: str = DEFAULT_MODEL
    escalation_model: str = ESCALATION_MODEL
    escalation_threshold: float = ESCALATION_CONFIDENCE_THRESHOLD
    schedule_hour: int = 7
    schedule_minute: int = 0
    skip_folders: list[str] = field(
        default_factory=lambda: ["Sent Items", "Drafts", "Outbox"]
    )
    # The daily/incremental sync only WATCHES these well-known folders (where new
    # mail lands). It never reprocesses the OmarOS/ destination folders nor the
    # user's own curated folders. A manual --folder run overrides this.
    watch_folders: list[str] = field(default_factory=lambda: ["inbox"])


def load_config() -> OutlookConfig:
    if not CONFIG_PATH.exists():
        return OutlookConfig()
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return OutlookConfig()
    if not isinstance(raw, dict):
        return OutlookConfig()
    known = {f.name for f in fields(OutlookConfig)}
    data = {k: v for k, v in raw.items() if k in known}
    return OutlookConfig(**data)


def save_config(cfg: OutlookConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)
    CONFIG_PATH.write_text(
        json.dumps(asdict(cfg), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.chmod(CONFIG_PATH, 0o600)


def ensure_dirs() -> None:
    for d in (
        RAW_DIR,
        BY_MESSAGE_DIR,
        SNAPSHOTS_DIR,
        BACKFILL_DIR,
        DIGEST_DIR,
        SYNC_STATE_PATH.parent,
    ):
        d.mkdir(parents=True, exist_ok=True)


def safe_id(internet_message_id: str) -> str:
    stripped = internet_message_id.strip().strip("<>")
    stripped = stripped.replace("@", "_")
    slug = _SAFE_ID_RE.sub("_", stripped)
    return slug or "unknown"


def odata_quote(value: str) -> str:
    """Escape a string literal for an OData $filter (single quote -> doubled)."""
    return value.replace("'", "''")
