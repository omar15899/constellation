"""Read the single project registry for the preserved document automation."""
from __future__ import annotations

import json
from pathlib import Path


def for_hub(hub: Path) -> dict:
    """Project central roots into the existing receiver's relative contract.

    Args:
        hub: Exact workspace root authorized by the local consent policy.

    Returns:
        The native/external entries within that hub. This is a read-only view,
        never a second persisted registry or an enrollment authorization.

    Raises:
        ValueError: The central registry is malformed or contains duplicate roots.
    """
    path = Path(__file__).resolve().parents[2] / "profiles/projects.json"
    data = json.loads(path.read_text())
    if data.get("schema_version") != 1 or not isinstance(data.get("projects"), list):
        raise ValueError("Invalid central project registry")
    seen: set[Path] = set()
    entries = []
    for item in data["projects"]:
        root = Path(item["root"])
        if not root.is_absolute() or root.resolve() != root or root in seen:
            raise ValueError("Noncanonical or duplicate central project root")
        seen.add(root)
        if root.is_relative_to(hub):
            entries.append({"path": root.relative_to(hub).as_posix(),
                            "management": item["management"]})
    return {"schema_version": 1, "repositories": entries}
