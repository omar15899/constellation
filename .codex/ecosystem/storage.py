"""Private SQLite persistence; transactions never span a subprocess."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import stat
from typing import Any, Iterator


class Error(ValueError):
    """Invalid, stale or incomplete coordination request."""


def encode(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def decode(value: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise Error("Duplicate JSON key.")
            result[key] = item
        return result

    def constant(_: str) -> None:
        raise Error("JSON must not contain nonfinite numbers.")

    try:
        return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError, RecursionError) as exc:
        raise Error("Invalid strict JSON.") from exc


class Store:
    def __init__(self, directory: Path):
        supplied = Path(directory).absolute()
        # Freeze existing ancestor aliases (for example macOS /var -> /private/var)
        # while retaining the final component so a linked state directory is rejected.
        self.directory = supplied.parent.resolve() / supplied.name
        self.path = self.directory / "ecosystem.sqlite3"

    def _safe(self, create: bool) -> bool:
        for parent in (*reversed(self.directory.parents), self.directory):
            if parent.is_symlink():
                raise Error("State directory must not traverse symbolic links.")
        if not self.directory.exists():
            if not create:
                return False
            self.directory.mkdir(mode=0o700, parents=True)
        if not self.directory.is_dir():
            raise Error("State directory must be a directory.")
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = Path(str(self.path) + suffix)
            if path.is_symlink():
                raise Error("State files must not be symbolic links.")
            if path.exists():
                info = path.stat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise Error("State files must be private regular files.")
        return self.path.exists() or create

    @contextmanager
    def connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection | None]:
        if not self._safe(write):
            yield None
            return
        created = False
        if write and not self.path.exists():
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                self._safe(False)
            else:
                os.close(fd)
                created = True
        connection = None
        try:
            connection = sqlite3.connect(self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"),
                                         uri=True, timeout=5, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=5000")
            if write:
                connection.execute("BEGIN IMMEDIATE")
                if created:
                    connection.execute("CREATE TABLE metadata (version INTEGER NOT NULL)")
                    connection.execute("INSERT INTO metadata VALUES (1)")
                    connection.execute("CREATE TABLE tasks (root TEXT NOT NULL, session TEXT NOT NULL, task TEXT NOT NULL, revision INTEGER NOT NULL, state TEXT NOT NULL, PRIMARY KEY(root,session,task))")
                    connection.execute("CREATE TABLE requests (root TEXT NOT NULL, session TEXT NOT NULL, task TEXT NOT NULL, request TEXT NOT NULL, digest TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(root,session,task,request))")
                    connection.execute("CREATE TABLE attempts (root TEXT NOT NULL, session TEXT NOT NULL, task TEXT NOT NULL, attempt TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(root,session,task,attempt))")
                    # Database initialization is independent of a task mutation:
                    # rejecting the first malformed request must not leave a
                    # truncated database that prevents its corrected retry.
                    connection.execute("COMMIT")
                    connection.execute("BEGIN IMMEDIATE")
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"metadata", "tasks", "requests", "attempts"} <= tables:
                raise Error("Incomplete state schema; refusing to reset existing history.")
            version = connection.execute("SELECT version FROM metadata").fetchall()
            if len(version) != 1 or version[0][0] != 1:
                raise Error("Unsupported state schema.")
            yield connection
            if write:
                connection.execute("COMMIT")
        except (sqlite3.Error, OSError) as exc:
            if connection is not None and connection.in_transaction:
                connection.rollback()
            raise Error(f"Cannot access coordination state ({type(exc).__name__}).") from None
        except BaseException:
            if connection is not None and connection.in_transaction:
                connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def load(db: sqlite3.Connection, key: tuple[str, str, str]) -> dict[str, Any] | None:
        row = db.execute("SELECT revision,state FROM tasks WHERE root=? AND session=? AND task=?", key).fetchone()
        if row is None:
            return None
        state = decode(row["state"])
        required = {"revision", "author", "started", "agents", "gate", "checks", "assessments",
                    "status", "closure", "stop_attempts", "observed_agents", "discovered", "contract"}
        if (not isinstance(state, dict) or not required <= state.keys()
                or type(state.get("revision")) is not int or state["revision"] != row["revision"]
                or any(not isinstance(state[name], dict) for name in
                       ("agents", "gate", "checks", "assessments", "observed_agents", "discovered", "contract"))
                or state["status"] not in {"active", "partial", "complete"}
                or not isinstance(state["author"], str)
                or state["agents"].get(state["author"]) != "coordinator"
                or type(state["stop_attempts"]) is not int or not 0 <= state["stop_attempts"] <= 2):
            raise Error("Invalid stored task state.")
        return state

    @staticmethod
    def save(db: sqlite3.Connection, key: tuple[str, str, str], state: dict[str, Any]) -> None:
        db.execute("INSERT INTO tasks VALUES (?,?,?,?,?) ON CONFLICT(root,session,task) DO UPDATE SET revision=excluded.revision,state=excluded.state",
                   (*key, state["revision"], encode(state)))
