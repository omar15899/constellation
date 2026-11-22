"""Create a new OmarOS Markdown note without mutating the task ledger."""

from __future__ import annotations

from contextlib import ExitStack
import os
from pathlib import Path, PurePosixPath
from uuid import uuid4

from .git import private_path
from .projects import load_projects
from .state import IS_WINDOWS, SOURCE, StateError, Store, require_unowned_paths, validate_paths


def _create(root: Path, path: PurePosixPath, content: bytes) -> None:
    """Publish complete bytes to a new name without following links or overwriting."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with ExitStack() as handles:
        directory = os.open(root, flags)
        handles.callback(os.close, directory)
        for part in path.parts[:-1]:
            if part not in os.listdir(directory):
                raise StateError("The note path must use the exact spelling of existing directories")
            directory = os.open(part, flags, dir_fd=directory)
            handles.callback(os.close, directory)

        candidate = ".constellation-note-" + uuid4().hex
        descriptor = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o644, dir_fd=directory)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(candidate, path.name, src_dir_fd=directory, dst_dir_fd=directory,
                        follow_symlinks=False)
            except FileExistsError:
                raise StateError("The note already exists; use a local change contract to edit it") from None
        finally:
            os.unlink(candidate, dir_fd=directory)


def save_note(store: Store, relative: str, content: bytes) -> dict[str, str]:
    """Create an ordinary Markdown note in the registered OmarOS knowledge base.

    Args:
        store: Read-only view of the regular Constellation task ledger.
        relative: Exact vault-relative Markdown path with an existing parent.
        content: Nonblank UTF-8 Markdown bytes.

    Returns:
        A local receipt with the relative path of the newly created note.

    Raises:
        StateError: The platform, path, content, or current task scope disallows
            this save, or the destination already exists.
        OSError: The vault or read-only task ledger could not be accessed.
    """
    if IS_WINDOWS:
        raise StateError("Read-only ledger note creation requires a POSIX filesystem")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise StateError("A note requires valid UTF-8 Markdown") from None
    if not text.strip() or "\0" in text:
        raise StateError("A note requires nonblank UTF-8 Markdown without NUL")

    project = next((project for project in load_projects(SOURCE, state_dir=store.root)
                    if project.get("id") == "omaros"), None)
    if project is None:
        raise StateError("The registered OmarOS vault could not be located")
    root = Path(project["root"])
    path = PurePosixPath(relative)
    if (len(path.parts) < 3 or path.parts[0] != "06_Knowledge_Base"
            or path.suffix.casefold() != ".md" or path.name.casefold() == "agents.md"
            or any(part.startswith(".") for part in path.parts)
            or private_path(relative, project)):
        raise StateError("Local note creation requires ordinary Markdown under 06_Knowledge_Base")

    with store._observe(required=True):
        validate_paths(root, {relative: "save-note"})
        if not (root / path.parent).is_dir():
            raise StateError("The note's parent directory must already exist")
        require_unowned_paths(root, [relative], store.list_tasks())
        _create(root, path, content)
    return {"status": "saved", "path": relative}
