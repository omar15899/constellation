"""Deterministic tag classifier for task-marshal.

Loads `/Users/omarkhalil/GitHub/Constellation/skills/omaros/task-marshal/tag_taxonomy.yaml`, compiles every tag's
patterns to regexes, and provides `classify()` to run them against the
concatenated text of a task (title + body + references + project slug).

Rules (contract):

1.  Determinism. Same input always yields the same sorted output. No RNG,
    no clock, no remote calls. Given a fixed taxonomy file, the mapping
    text → tags is a pure function.

2.  Additive. `classify()` receives the user-provided tags (from Rule 2 of
    the extraction rules — `#foo` tokens) and ALWAYS returns them. Auto
    tags are unioned on top; user tags are never dropped.

3.  Hierarchical propagation. When a child tag fires, its `parent` tag
    fires too. Walks the parent chain transitively.

4.  Never fatal. An unreadable taxonomy degrades to "no auto tags"; the
    log pipeline keeps running with just the user's tags.
"""
from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Reuse the venv-aware pyaml import path from parse.py — same bootstrap shape.
# Canonical venv is at ~/.venvs/omaros/; legacy fallback at OMAROS_ROOT/.venv/.
_OMAROS_ROOT = Path(
    os.environ.get("OMAROS_ROOT", Path("/Users/omarkhalil/OmarOS"))
)
_VENV_CANDIDATES = [
    Path.home() / ".venvs" / "omaros",
    _OMAROS_ROOT / ".venv",
]
for _venv_root in _VENV_CANDIDATES:
    _site_root = _venv_root / "lib"
    if _site_root.exists():
        for _child in _site_root.iterdir():
            _sp = _child / "site-packages"
            if _sp.exists() and str(_sp) not in sys.path:
                sys.path.insert(0, str(_sp))
                break
        break

try:
    import yaml
    _HAS_PYYAML = True
except ImportError:
    _HAS_PYYAML = False

TAXONOMY_PATH = Path(__file__).resolve().parent.parent / "tag_taxonomy.yaml"


@lru_cache(maxsize=1)
def _load_taxonomy() -> tuple[tuple[str, tuple[re.Pattern, ...], str | None], ...]:
    """Parse the taxonomy file once, compile regex patterns, cache.

    Returns a tuple of `(tag_name, compiled_patterns, parent)` so it's
    hashable / lru_cache-friendly.
    """
    if not _HAS_PYYAML or not TAXONOMY_PATH.exists():
        return ()
    try:
        raw = yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return ()
    entries = []
    for item in raw.get("tags", []) or []:
        name = item.get("name")
        if not name:
            continue
        parent = item.get("parent")
        compiled: list[re.Pattern] = []
        for pat in item.get("patterns", []) or []:
            try:
                compiled.append(re.compile(pat))
            except re.error:
                # Bad pattern: skip silently; classifier should never raise.
                continue
        entries.append((name, tuple(compiled), parent))
    return tuple(entries)


def _parent_chain(name: str, parents: dict[str, str | None]) -> list[str]:
    chain = []
    cur = parents.get(name)
    seen = {name}
    while cur and cur not in seen:
        chain.append(cur)
        seen.add(cur)
        cur = parents.get(cur)
    return chain


def classify(
    title: str | None = None,
    body: str | None = None,
    references: str | None = None,
    project: str | None = None,
    existing_tags: Iterable[str] | None = None,
) -> list[str]:
    """Return a sorted, deduplicated list of tags for this task.

    The returned list is the union of:
      - every `existing_tags` entry (user's own tags, always kept)
      - every tag whose compiled patterns match the concatenated text
      - every parent of every auto-matched tag (transitive)
      - if `project` is set, a tag `proyecto_<project>` is auto-added so
        project-scoped filtering works even when the ledger entry carries
        the project in its dedicated field rather than as a hashtag.

    All tags are lowercased.
    """
    result: set[str] = set()
    if existing_tags:
        for t in existing_tags:
            if isinstance(t, str) and t.strip():
                result.add(t.strip().lower())

    if project and isinstance(project, str) and project.strip():
        result.add(f"proyecto_{project.strip().lower()}")

    # Build the scan text. Include project slug so a `project: scilux` record
    # gets `proyecto_scilux` via the taxonomy too.
    parts: list[str] = []
    for p in (title, body, references, project):
        if p:
            parts.append(str(p))
    text = "\n".join(parts)
    if not text.strip():
        return sorted(result)

    entries = _load_taxonomy()
    if not entries:
        return sorted(result)

    parents = {name: parent for name, _, parent in entries}

    auto: set[str] = set()
    for name, patterns, _ in entries:
        for pat in patterns:
            if pat.search(text):
                auto.add(name)
                break

    # Parent propagation
    propagated: set[str] = set()
    for t in auto:
        for anc in _parent_chain(t, parents):
            propagated.add(anc)
    auto |= propagated

    result |= auto
    return sorted(result)


# CLI self-test / ad-hoc usage: reads stdin as free text, prints tags JSON.
if __name__ == "__main__":
    import json

    text = sys.stdin.read()
    print(json.dumps(classify(title=text), indent=2, ensure_ascii=False))
