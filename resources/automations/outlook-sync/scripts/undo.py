from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config import ensure_dirs, odata_quote
from graph_client import GraphClient, GraphError


@dataclass
class UndoEntry:
    internet_message_id: str
    message_id: str
    action: str
    from_folder_id: str | None
    to_folder_id: str | None
    prev_categories: list[str]
    ts: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> UndoEntry:
        prev = raw.get("prev_categories")
        return cls(
            internet_message_id=str(raw.get("internet_message_id") or ""),
            message_id=str(raw.get("message_id") or ""),
            action=str(raw.get("action") or "move"),
            from_folder_id=raw.get("from_folder_id"),
            to_folder_id=raw.get("to_folder_id"),
            prev_categories=list(prev) if isinstance(prev, list) else [],
            ts=str(raw.get("ts") or ""),
        )


@dataclass
class UndoReport:
    reverted: int
    skipped: int
    not_found: list[str]
    errors: list[str]


def _load_entries(manifest_path: Path) -> list[UndoEntry]:
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("entries"), list):
            items = raw["entries"]
        elif isinstance(raw.get("actions"), list):
            items = raw["actions"]
        else:
            items = [raw]
    else:
        raise ValueError(
            f"Unrecognized undo manifest shape in {manifest_path}"
        )
    return [UndoEntry.from_dict(item) for item in items if isinstance(item, dict)]


def _locate_message(client: GraphClient, entry: UndoEntry) -> dict | None:
    """Resolve the current message resource for an entry.

    A move changes the message id, so prefer locating by the stable
    internetMessageId; fall back to the stored message_id best-effort.
    """
    if entry.internet_message_id:
        try:
            data = client._request(
                "GET",
                "/me/messages",
                params={
                    "$filter": (
                        "internetMessageId eq "
                        f"'{odata_quote(entry.internet_message_id)}'"
                    ),
                    "$select": "id,internetMessageId,parentFolderId,categories",
                    "$top": 1,
                },
            )
        except GraphError:
            data = None
        if data is not None:
            values = data.get("value") or []
            if values:
                return values[0]

    if entry.message_id:
        try:
            return client.get_message(entry.message_id)
        except GraphError:
            return None
    return None


def _revert_entry(client: GraphClient, entry: UndoEntry) -> tuple[str, str]:
    """Return (outcome, detail). outcome in {reverted, skipped, not_found, error}."""
    label = entry.internet_message_id or entry.message_id or "<unknown>"

    if entry.action != "move":
        return "skipped", f"{label}: unsupported action '{entry.action}'"

    msg = _locate_message(client, entry)
    if msg is None:
        return "not_found", label

    current_id = msg.get("id", "")
    if not current_id:
        return "not_found", label

    if not entry.from_folder_id:
        return "skipped", f"{label}: no from_folder_id recorded"

    current_folder = msg.get("parentFolderId")
    try:
        if current_folder != entry.from_folder_id:
            moved = client.move_message(current_id, entry.from_folder_id)
            current_id = moved.get("id", current_id)
        client.set_categories(current_id, entry.prev_categories)
    except GraphError as exc:
        return "error", f"{label}: {exc}"

    return "reverted", (
        f"{label}: moved back to {entry.from_folder_id}, "
        f"categories restored to {entry.prev_categories}"
    )


def undo_manifest(manifest_path: Path) -> UndoReport:
    ensure_dirs()
    entries = _load_entries(manifest_path)
    client = GraphClient.from_config()

    reverted = 0
    skipped = 0
    not_found: list[str] = []
    errors: list[str] = []

    try:
        # Reverse chronological order so the most recent action is undone first.
        for entry in reversed(entries):
            outcome, detail = _revert_entry(client, entry)
            if outcome == "reverted":
                reverted += 1
                print(f"reverted  {detail}")
            elif outcome == "skipped":
                skipped += 1
                print(f"skipped   {detail}")
            elif outcome == "not_found":
                not_found.append(detail)
                print(f"not-found {detail}")
            else:
                errors.append(detail)
                print(f"error     {detail}")
    finally:
        client.close()

    return UndoReport(
        reverted=reverted,
        skipped=skipped,
        not_found=not_found,
        errors=errors,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Reverse a previously-recorded undo manifest: move messages back "
            "to their original folders and restore their prior categories. "
            "Messages are located by stable internetMessageId because a move "
            "changes the Graph message id; entries that cannot be located are "
            "reported and skipped."
        )
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to an undo manifest JSON "
        "(e.g. undo_sync_<date>.json or undo_backfill_<ts>.json)",
    )
    args = parser.parse_args()

    manifest_path: Path = args.manifest
    if not manifest_path.exists():
        print(f"Undo manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    try:
        report = undo_manifest(manifest_path)
    except GraphError as exc:
        print(f"Graph error: {exc}", file=sys.stderr)
        print("Hint: run auth.py to (re)authenticate.", file=sys.stderr)
        sys.exit(1)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Could not parse manifest {manifest_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        "\nUndo complete: "
        f"{report.reverted} reverted, "
        f"{report.skipped} skipped, "
        f"{len(report.not_found)} not found, "
        f"{len(report.errors)} errors."
    )
    if report.not_found:
        print("Not located (could not be reversed):")
        for label in report.not_found:
            print(f"  - {label}")
    if report.errors:
        print("Errors:")
        for detail in report.errors:
            print(f"  - {detail}")


if __name__ == "__main__":
    main()
