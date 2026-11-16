#!/usr/bin/env python3
"""Locate the current manual and expose source evidence without writing files."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION = re.compile(r"^v(\d+)(?:[_ .-]|$)", re.IGNORECASE)
COMMAND = re.compile(
    r"\\(input|include|figuraexistente|part|chapter|section|subsection|label)"
    r"(\*)?\s*\{"
)
ENTRIES = (
    "latex/main.tex", "main.tex", "latex/main_maestro.tex", "main_maestro.tex",
    "tex/main.tex", "latex/book.tex", "book.tex", "manual.tex",
)


class ContextError(ValueError):
    """An unresolved source choice must remain visible to the caller."""


def fold(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(char)
    )


def uncomment(text: str) -> str:
    """Keep positions intact so evidence refers to original source lines."""
    chars = list(text)
    for match in re.finditer(r"%", text):
        preceding = len(text[:match.start()]) - len(text[:match.start()].rstrip("\\"))
        if preceding % 2 == 0:
            end = text.find("\n", match.start())
            if end == -1:
                end = len(text)
            chars[match.start():end] = " " * (end - match.start())
    return "".join(chars)


def commands(text: str) -> list[tuple[str, str, int, bool]]:
    """Read balanced literal arguments; this deliberately does not execute TeX."""
    cleaned = uncomment(text)
    result: list[tuple[str, str, int, bool]] = []
    for match in COMMAND.finditer(cleaned):
        start = match.end()
        depth = 1
        end = start
        while end < len(cleaned) and depth:
            preceding = len(cleaned[:end]) - len(cleaned[:end].rstrip("\\"))
            if preceding % 2 == 0:
                if cleaned[end] == "{":
                    depth += 1
                elif cleaned[end] == "}":
                    depth -= 1
            end += 1
        if depth == 0:
            result.append((match[1], cleaned[start:end - 1].strip(),
                           cleaned.count("\n", 0, match.start()) + 1, bool(match[2])))
    return result


def inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


@dataclass(frozen=True)
class Selection:
    directory: Path
    entry: Path
    number: int | None
    reason: str


def manual_entry(directory: Path) -> Path | None:
    for name in ENTRIES:
        path = directory / name
        if not path.is_file() or not inside(path, directory):
            continue
        text = uncomment(path.read_text(encoding="utf-8"))
        if (re.search(r"\\documentclass(?:\[[^\]]*\])?\s*\{(?!beamer\})[^}]+\}", text)
                and r"\begin{document}" in text):
            return path.resolve()
    return None


def select(root: Path, version: Path | None = None, entry: str | None = None) -> Selection:
    root = root.resolve()
    if not root.is_dir():
        raise ContextError(f"No existe el proyecto: {root}")
    if version is not None:
        directory = version.resolve()
        if not directory.is_dir() or not inside(directory, root):
            raise ContextError("La versión explícita debe ser una carpeta del proyecto.")
        path = (directory / entry).resolve() if entry else manual_entry(directory)
        if path is None or not path.is_file() or not inside(path, directory):
            raise ContextError("Entrada no reconocida; localiza la fuente y usa --entry.")
        match = VERSION.match(directory.name)
        return Selection(directory, path, int(match[1]) if match else None,
                         "Destino explícito; prevalece sobre la selección automática.")
    if entry:
        raise ContextError("--entry requiere --version para fijar su base.")

    candidates: list[tuple[int, Path, Path | None]] = []
    for directory in sorted(root.iterdir()):
        match = VERSION.match(directory.name)
        if (not match or not directory.is_dir() or not inside(directory, root)
                or "repositorio" in fold(directory.name)):
            continue
        path = manual_entry(directory)
        # Taller/manual folders without an entry may be a new layout or unfinished edition.
        # They must not cause an unnoticed fallback to an older version.
        if path or any(word in fold(directory.name) for word in ("apuntes", "taller", "manual")):
            candidates.append((int(match[1]), directory.resolve(), path))
    if not candidates:
        raise ContextError("No hay manual reconocible; indica --version y --entry.")
    latest = max(item[0] for item in candidates)
    winners = [item for item in candidates if item[0] == latest]
    if len(winners) != 1:
        raise ContextError("Variantes de igual versión; contrasta sus README y fija --version: "
                           + ", ".join(str(item[1]) for item in winners))
    number, directory, path = winners[0]
    if path is None:
        raise ContextError(f"V{number} existe sin entrada reconocible: {directory}. "
                           "Examina sus fuentes y usa --version/--entry; no se elige una anterior.")
    return Selection(directory, path, number, "Máxima versión numérica de la línea de manuales.")


def source_graph(entry: Path, boundary: Path) -> dict[str, Any]:
    files: list[str] = []
    outline: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    warnings: list[str] = []
    active: set[Path] = set()
    seen: set[Path] = set()
    base = entry.parent

    def visit(path: Path) -> None:
        path = path.resolve()
        if not inside(path, boundary):
            warnings.append(f"Dependencia fuera de la versión, no leída: {path}")
            return
        if path in active:
            warnings.append(f"Ciclo de inclusiones: {path}")
            return
        if not path.is_file():
            warnings.append(f"Dependencia ausente: {path}")
            return
        if path in seen:
            warnings.append(f"Inclusión repetida; índice de fuente sin expandir otra vez: {path}")
            return
        seen.add(path)
        active.add(path)
        files.append(str(path))
        text = path.read_text(encoding="utf-8")
        for command, value, line, starred in commands(text):
            if command in ("input", "include", "figuraexistente"):
                if any(char in value for char in ("\\", "#", "{", "}")):
                    warnings.append(f"Inclusión dinámica no resuelta: {path}:{line}: {value}")
                    continue
                relative = Path(value)
                if not relative.suffix:
                    relative = relative.with_suffix(".tex")
                choices = [(base / relative).resolve(), (path.parent / relative).resolve()]
                found = next((candidate for candidate in choices if candidate.is_file()), choices[0])
                visit(found)
            elif command == "label":
                labels.append({"label": value, "path": str(path), "line": line})
            else:
                outline.append({"kind": command, "title": value, "path": str(path),
                                "line": line, "starred": starred})
        active.remove(path)

    visit(entry)
    return {"files": files, "outline": outline, "labels": labels, "warnings": warnings}


def search(files: list[str], queries: list[str], limit: int) -> dict[str, Any]:
    needles = [(query, fold(query.strip())) for query in queries if query.strip()]
    matches: list[dict[str, Any]] = []
    total = 0
    for filename in dict.fromkeys(files):
        original = Path(filename).read_text(encoding="utf-8").splitlines()
        cleaned = uncomment("\n".join(original)).splitlines()
        for index, line in enumerate(cleaned):
            hits = [query for query, needle in needles if needle in fold(line)]
            if not hits:
                continue
            total += 1
            if len(matches) < limit:
                matches.append({"path": filename, "line": index + 1, "queries": hits,
                                "context": "\n".join(original[max(0, index - 2):index + 3])})
    return {"matches": matches, "matching_lines": total, "truncated": total > limit,
            "scope": "Fuentes literales integradas; coincidencia textual, no dictamen semántico."}


def context(selection: Selection, queries: list[str], limit: int = 60) -> dict[str, Any]:
    graph = source_graph(selection.entry, selection.directory)
    extra: dict[str, Any] = {}
    for name in ("latex/practica.tex", "practica.tex", "problemas/main.tex"):
        path = selection.directory / name
        if path.is_file() and path.resolve() != selection.entry:
            extra[name] = source_graph(path, selection.directory)
    files = graph["files"] + [path for item in extra.values() for path in item["files"]]
    return {"version": selection.number, "directory": str(selection.directory),
            "entry": str(selection.entry), "reason": selection.reason,
            "readme": str(selection.directory / "README.md"), "manual": graph,
            "related_documents": extra, "search": search(files, queries, limit),
            "limitations": ["No ejecuta macros, condicionales, import ni numeración TeX.",
                            "El orden refleja inclusiones literales, no asegura el PDF efectivo.",
                            "Leer fuentes y resolver avisos antes de afirmar cobertura completa."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    vault_course = Path.cwd() / "05_Projects/Brainteasers_Quant"
    parser.add_argument("--root", "--project", type=Path, dest="root",
                        default=vault_course if vault_course.is_dir() else Path.cwd(),
                        help="Raíz del curso. Desde OmarOS se usa su proyecto Brainteasers_Quant.")
    parser.add_argument("--version", type=Path, help="Carpeta explícita, absoluta o relativa al cwd")
    parser.add_argument("--entry", help="Entrada relativa a --version")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--limit", type=int, default=60)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit debe ser positivo")
    try:
        result = context(select(args.root, args.version, args.entry), args.query, args.limit)
    except (ContextError, OSError, UnicodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
