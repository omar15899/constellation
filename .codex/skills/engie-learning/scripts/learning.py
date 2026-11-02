"""Private, bounded learning capture: files are authoritative, no network or Git writes.

The lock coordinates this writer, not arbitrary editors. An atomic exchange keeps
the displaced inode, so an observed external-editor race remains recoverable.
Multi-file updates have a private write-ahead journal and explicit recovery.
"""
from __future__ import annotations

# Only the verified device runner may start a capture. Reject even a
# catalog-shaped copy before Python can import any guest-supplied sibling.
if __name__ == "__main__":
    import sys
    sys.stdout.write('{"status":"error","code":"wrong_project","message":"Usa constellation/run cli skill-run engie-learning learning.","persisted":false}\n')
    raise SystemExit(2)

import argparse
import ctypes
import datetime as dt
import os
if os.name == "posix":
    import fcntl
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import subprocess
import sys
from contextlib import contextmanager
from typing import Any, Iterator
import uuid

PACKAGE = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PACKAGE))
from ecosystem.hooks import HookError, check_vault_registration
import yaml


VAULT_MARKER = Path("05_Projects/OmarOS/Architecture/OmarOS_Architecture.md")
BASE = "06_Knowledge_Base/Mathematics/Finance/ENGIE/Private"
LIMIT = 1024 * 1024
PLAN_LIMIT = 2 * LIMIT
STATE_LIMIT = 32 * LIMIT
SLUG = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z")


class CaptureError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def serialized(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def git_environment() -> dict[str, str]:
    # These queries describe the actual checkout and index, never a caller's
    # alternate index, work tree, config injection or tracing destination.
    return {**{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
            "PATH": os.defpath}


def stamp(value: str) -> dt.datetime:
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise CaptureError("invalid_date", "captured_at requiere una fecha ISO con zona.") from None
    if result.tzinfo is None:
        raise CaptureError("invalid_date", "captured_at requiere zona horaria.")
    return result


def iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise CaptureError("invalid_date", "learned_on requiere YYYY-MM-DD o null.")
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        raise CaptureError("invalid_date", "Fecha de aprendizaje inválida.") from None
    return value


def text(value: Any, name: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value.encode()) > 65536:
        raise CaptureError("invalid_input", f"Campo inválido: {name}.")
    if "<!-- LEARNING:" in value or "<!-- LEARNING-CURRENT:" in value or "\x00" in value:
        raise CaptureError("invalid_input", "El contenido contiene un delimitador reservado.")
    return value


def identifier(value: Any) -> str:
    try:
        result = str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        raise CaptureError("invalid_input", "event_id y correction_of requieren UUID estables.") from None
    if result != value:
        raise CaptureError("invalid_input", "Utiliza el UUID normalizado en minúsculas.")
    return result


def validate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) - {"event_id", "learned_on", "captured_at", "summary", "topics", "correction_of"}:
        raise CaptureError("invalid_input", "Captura desconocida: sólo se admiten campos curados del contrato.")
    required = {"event_id", "learned_on", "captured_at", "summary", "topics"}
    if not required <= payload.keys():
        raise CaptureError("invalid_input", "Faltan campos obligatorios de la captura.")
    result = dict(payload)
    result["event_id"] = identifier(payload["event_id"])
    result["learned_on"] = iso_date(payload["learned_on"])
    stamp(payload["captured_at"])
    text(payload["summary"], "summary")
    if "correction_of" in payload:
        identifier(payload["correction_of"])
        if payload["correction_of"] == payload["event_id"]:
            raise CaptureError("invalid_input", "Una corrección necesita un evento nuevo.")
    topics = payload["topics"]
    if not isinstance(topics, list) or not 1 <= len(topics) <= 12:
        raise CaptureError("invalid_input", "Una captura requiere entre uno y doce temas.")
    seen: set[str] = set()
    normalized = []
    for topic in topics:
        if not isinstance(topic, dict) or set(topic) - {"slug", "title", "body", "provenance", "antecedents", "questions", "contradictions", "conditions", "examples"}:
            raise CaptureError("invalid_input", "Campos de tema desconocidos.")
        if not {"slug", "title", "body", "provenance"} <= topic.keys():
            raise CaptureError("invalid_input", "Cada tema requiere slug, title, body y provenance.")
        slug = topic["slug"]
        if not isinstance(slug, str) or not SLUG.fullmatch(slug) or len(slug) > 100 or slug in seen:
            raise CaptureError("invalid_input", "Slug de tema inválido o repetido.")
        seen.add(slug)
        text(topic["title"], "title")
        if "\n" in topic["title"] or len(topic["title"]) > 240:
            raise CaptureError("invalid_input", "El título debe ocupar una línea breve.")
        text(topic["body"], "body")
        provenance = topic["provenance"]
        if not isinstance(provenance, list) or not provenance:
            raise CaptureError("invalid_input", "Cada tema necesita procedencia explícita.")
        for source in provenance:
            if not isinstance(source, dict) or set(source) != {"kind", "reference"} or not isinstance(source["kind"], str) or source["kind"] not in {"user", "source", "ai_proposal"}:
                raise CaptureError("invalid_input", "Procedencia inválida.")
            text(source["reference"], "reference")
        item = dict(topic)
        for field in ("antecedents", "questions", "contradictions", "conditions", "examples"):
            values = item.setdefault(field, [])
            if not isinstance(values, list) or len(values) > 40:
                raise CaptureError("invalid_input", f"Lista inválida: {field}.")
            for value in values:
                text(value, field)
        normalized.append(item)
    result["topics"] = normalized
    if len(serialized(result)) > LIMIT:
        raise CaptureError("too_large", "La captura supera el límite local.")
    return result


def parts(relative: str) -> tuple[str, ...]:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(p in {".", ".."} for p in path.parts) or "\\" in relative:
        raise CaptureError("unsafe_path", "Ruta relativa inválida.")
    return path.parts


class Store:
    def __init__(self, root: Path | None, *, device_home: Path):
        if os.name != "posix":
            raise CaptureError("unsupported_platform", "La captura privada requiere un entorno POSIX con bloqueo y acceso por descriptor.")
        # The skill may be installed on another filesystem; the vault is always
        # selected through the caller's working directory or explicit --root.
        self.root = (root if root is not None else Path.cwd()).absolute()
        if self.root.is_symlink() or not self.root.is_dir():
            raise CaptureError("unsafe_root", "La raíz debe ser un directorio real.")
        self.root = self.root.resolve()
        origin = self.root
        owner = Path(self.git("rev-parse", "--show-toplevel").stdout.strip()).resolve()
        original_gitdir = Path(self.git("rev-parse", "--absolute-git-dir").stdout.strip())
        if not origin.is_relative_to(owner) or (root is not None and owner != origin):
            raise CaptureError("wrong_owner", "La raíz debe coincidir con su dueño Git.")
        self.root = owner
        self.home = device_home
        self.binding = self.current_registration()
        marker = self.root / VAULT_MARKER
        if marker.resolve() != marker or not marker.is_file():
            raise CaptureError("wrong_project", "La captura requiere el repositorio OmarOS y su mapa de arquitectura.")
        self.gitdir = Path(self.git("rev-parse", "--absolute-git-dir").stdout.strip())
        if original_gitdir != self.gitdir:
            raise CaptureError("wrong_owner", "El directorio de trabajo pertenece a otro dueño Git.")
        self.state = self.gitdir / "omaros-learning"
        self.gitfile = None
        with self.anchor() as fd:
            self.gitfile = self.gitfile_identity(fd)
        self.verify_registered()

    def current_registration(self) -> dict[str, Any]:
        try:
            return check_vault_registration(self.home, str(self.root), require_bound=True)
        except (HookError, ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
            raise CaptureError("wrong_project", "La raíz o su directorio Git no corresponden al vault inscrito.") from error

    def verify_registered(self) -> None:
        if self.current_registration() != self.binding:
            raise CaptureError("wrong_project", "La inscripción cambió durante la captura.")

    @staticmethod
    def gitfile_identity(root_fd: int) -> tuple[int, ...]:
        marker = os.stat(".git", dir_fd=root_fd, follow_symlinks=False)
        if stat.S_ISDIR(marker.st_mode):
            return (marker.st_dev, marker.st_ino)
        if stat.S_ISREG(marker.st_mode):
            return (marker.st_dev, marker.st_ino, marker.st_size, marker.st_ctime_ns)
        raise CaptureError("wrong_project", "La entrada Git del vault no es canónica.")

    @contextmanager
    def anchor(self, *, state: bool = False) -> Iterator[int]:
        """Match both opened directory objects before traversing or creating anything."""
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        root_fd = os.open(self.root, flags)
        try:
            git_fd = os.open(self.gitdir, flags)
            try:
                for fd, key in ((root_fd, "owner"), (git_fd, "git_dir")):
                    info = os.fstat(fd)
                    if [info.st_dev, info.st_ino] != self.binding[key]:
                        raise CaptureError("wrong_project", "La identidad del vault o de su Git cambió.")
                if self.gitfile is not None and self.gitfile_identity(root_fd) != self.gitfile:
                    raise CaptureError("wrong_project", "La entrada Git del vault cambió.")
                yield git_fd if state else root_fd
            finally:
                os.close(git_fd)
        finally:
            os.close(root_fd)

    def git(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(["git", "-C", str(self.root), *arguments], env=git_environment(), text=True, capture_output=True, check=check, timeout=15)
        except (subprocess.SubprocessError, OSError):
            raise CaptureError("git_error", "No se pudo verificar el dueño y la protección Git.") from None

    @contextmanager
    def parent(self, relative: str, *, create: bool = False, state: bool = False) -> Iterator[tuple[int, str]]:
        components = parts(relative)
        with self.anchor(state=state) as anchor:
            fd = os.dup(anchor)
        try:
            for component in components[:-1]:
                if create:
                    try:
                        os.mkdir(component, 0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
            yield fd, components[-1]
        except OSError as error:
            raise CaptureError("unsafe_path", f"No se puede abrir una ruta segura ({error.errno}).") from None
        finally:
            os.close(fd)

    def read(self, relative: str, *, state: bool = False) -> bytes | None:
        try:
            with self.parent(relative, state=state) as (fd, name):
                try:
                    source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                except FileNotFoundError:
                    return None
                try:
                    self.check_file(source)
                    limit = STATE_LIMIT if state else LIMIT
                    chunks = []
                    remaining = limit + 1
                    while remaining:
                        chunk = os.read(source, min(remaining, 65536))
                        if not chunk:
                            break
                        chunks.append(chunk)
                        remaining -= len(chunk)
                    data = b"".join(chunks)
                    if len(data) > limit:
                        raise CaptureError("too_large", "El archivo supera el límite local.")
                    return data
                finally:
                    os.close(source)
        except CaptureError as error:
            if error.code == "unsafe_path":
                # Missing parents are ordinary for the first capture; symlinks
                # and other failures remain errors.
                candidate = (self.gitdir if state else self.root) / relative
                current = self.gitdir if state else self.root
                for component in parts(relative):
                    current = current / component
                    if current.is_symlink():
                        raise
                    if not current.exists():
                        return None
            raise

    def json_read(self, relative: str) -> Any:
        data = self.read(relative, state=True)
        if data is None:
            return None
        try:
            return json.loads(data)
        except (UnicodeDecodeError, ValueError):
            raise CaptureError("corrupt_state", "Estado privado inválido; conservarlo para recuperación.") from None

    def protected(self, relative: str) -> None:
        self.check_private_target(relative)
        self.read(relative)

    def check_private_target(self, relative: str) -> None:
        if not relative.startswith(BASE + "/") or not relative.endswith(".md"):
            raise CaptureError("unsafe_path", "La escritura se limita al área Private de ENGIE.")
        parts(relative)
        self.check_owner(relative)
        tracked = self.git("ls-files", "--error-unmatch", "--", relative, check=False).returncode
        if tracked == 0:
            raise CaptureError("tracked_private", "Un destino privado ya está versionado: no se escribirá.")
        if tracked != 1:
            raise CaptureError("git_error", "No se pudo verificar el índice del vault; se conserva el destino.")
        if self.git("check-ignore", "--no-index", "-q", "--", relative, check=False).returncode != 0:
            raise CaptureError("unprotected_private", "Falta la exclusión Git del área Private.")

    def check_owner(self, relative: str) -> None:
        """Check the nearest real parent, including repositories hidden by ignore.

        Descriptor traversal rejects symlinks before invoking Git. The opened
        parent is revalidated afterwards; root-relative ls-files alone misses
        nested repositories, including an untracked repository in Private.
        """
        components = parts(relative)
        with self.anchor() as anchor:
            fd = os.dup(anchor)
        traversed: list[str] = []
        try:
            for component in components[:-1]:
                try:
                    child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                except FileNotFoundError:
                    break
                os.close(fd)
                fd = child
                traversed.append(component)
            directory = self.root.joinpath(*traversed)
            result = subprocess.run(["git", "-C", str(directory), "rev-parse", "--show-toplevel", "--absolute-git-dir"], env=git_environment(), capture_output=True, text=True, timeout=15)
            with self.anchor() as anchor:
                check = os.dup(anchor)
            try:
                for component in traversed:
                    child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=check)
                    os.close(check)
                    check = child
                original, current = os.fstat(fd), os.fstat(check)
                if (original.st_dev, original.st_ino) != (current.st_dev, current.st_ino):
                    raise CaptureError("edit_conflict", "El padre del destino cambió al verificar su dueño Git.")
            finally:
                os.close(check)
            owners = result.stdout.splitlines()
            if result.returncode or len(owners) != 2 or Path(owners[0]).resolve() != self.root or Path(owners[1]).resolve() != self.gitdir.resolve():
                raise CaptureError("wrong_owner", "El destino pertenece a otro dueño Git; no se leerá ni modificará.")
        except OSError as error:
            raise CaptureError("unsafe_path", f"No se pudo verificar un padre real del destino ({error.errno}).") from None
        except subprocess.SubprocessError:
            raise CaptureError("git_error", "No se pudo comprobar el dueño Git del destino.") from None
        finally:
            os.close(fd)

    @contextmanager
    def lock(self) -> Iterator[None]:
        with self.parent("omaros-learning/lock", create=True, state=True) as (fd, name):
            target = os.open(name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            try:
                self.check_file(target)
                try:
                    fcntl.flock(target, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise CaptureError("busy", "Otra captura está escribiendo; reintenta después.") from None
                yield
            finally:
                os.close(target)

    def state_write(self, relative: str, value: Any) -> None:
        data = serialized(value)
        if len(data) > STATE_LIMIT:
            raise CaptureError("too_large", "La transacción excede el presupuesto de recuperación local.")
        with self.parent(relative, create=True, state=True) as (fd, name):
            temp = f".{name}.{secrets.token_hex(8)}"
            target = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            try:
                self.write_all(target, data)
                os.fsync(target)
            finally:
                os.close(target)
            try:
                os.replace(temp, name, src_dir_fd=fd, dst_dir_fd=fd)
                os.fsync(fd)
            finally:
                try:
                    os.unlink(temp, dir_fd=fd)
                except FileNotFoundError:
                    pass

    @staticmethod
    def check_file(fd: int) -> os.stat_result:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise CaptureError("unsafe_path", "Se requiere un archivo regular sin enlaces adicionales.")
        return info

    @staticmethod
    def write_all(fd: int, data: bytes) -> None:
        remaining = memoryview(data)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise OSError("Escritura incompleta")
            remaining = remaining[written:]

    def receipt(self, event_id: str) -> Any:
        return self.json_read(f"omaros-learning/receipts/{identifier(event_id)}.json")

    def private_paths(self) -> list[Path]:
        directory = self.root / BASE
        if not directory.exists():
            return []
        if directory.is_symlink():
            raise CaptureError("unsafe_path", "El área privada no puede ser un enlace.")
        candidates = []
        def walk_error(error: OSError) -> None:
            raise CaptureError("read_error", f"No se pudo recorrer toda el área privada ({error.errno}).")
        with self.parent(BASE + "/.inventory") as (area_fd, _):
            for folder, directories, files, fd in os.fwalk(".", dir_fd=area_fd, follow_symlinks=False, onerror=walk_error):
                if folder == ".":
                    directories[:] = [name for name in directories if name in {"Topics", "Daily"}]
                    files = []
                if ".git" in directories or ".git" in files:
                    raise CaptureError("wrong_owner", "El área privada contiene otro dueño Git.")
                if any(stat.S_ISLNK(os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode) for name in directories):
                    raise CaptureError("unsafe_path", "Hay un directorio simbólico en el área privada.")
                candidates.extend(directory / folder / name for name in files if name.endswith(".md"))
        return sorted(candidates)

    def event_blocks(self, event_id: str) -> dict[str, str]:
        """Recover identity from Markdown when its small receipt is absent.

        This exceptional identity lookup reads only the explicitly private area,
        never the general vault. It also detects reuse on a different date/topic.
        """
        found = {}
        for path in self.private_paths():
            relative = path.relative_to(self.root).as_posix()
            self.check_owner(relative)
            data = self.read(relative)
            existing = block(data.decode(), event_id) if data else None
            if existing:
                self.protected(relative)
                found[relative] = existing
        return found

    def verify_receipt(self, receipt: dict[str, Any]) -> dict[str, Any]:
        for relative, block_hash in receipt["blocks"].items():
            self.protected(relative)
            content = self.read(relative)
            if content is None or block(content.decode(), receipt["event_id"]) is None or digest(block(content.decode(), receipt["event_id"]).encode()) != block_hash:
                raise CaptureError("diverged", "El evento guardado ha sido editado o está incompleto; no se confirma el reintento.")
        return {"status": "already_applied", "event_id": receipt["event_id"], "paths": list(receipt["blocks"]), "event_hash": receipt["event_hash"]}

    def prepare(self, payload: Any) -> dict[str, Any]:
        self.verify_registered()
        capture = validate(payload)
        if self.json_read("omaros-learning/pending.json"):
            raise CaptureError("pending", "Hay una escritura pendiente. Ejecuta status y recover antes de preparar o confirmar una captura.")
        event_hash = digest(serialized(capture))
        old = self.receipt(capture["event_id"])
        if old:
            if old["event_hash"] != event_hash:
                raise CaptureError("event_conflict", "Este event_id ya identifica otra captura. Una corrección necesita otro ID y correction_of.")
            return self.verify_receipt(old)
        existing = self.event_blocks(capture["event_id"])
        if existing:
            date = capture["learned_on"]
            daily_path = f"{BASE}/Daily/{date[:4]}/{date}.md" if date else f"{BASE}/Daily/unknown.md"
            expected_blocks = {f"{BASE}/Topics/{topic['slug']}.md": topic_block(capture, topic, event_hash, daily_path) for topic in capture["topics"]}
            expected_blocks[daily_path] = daily_block(capture, event_hash)
            if set(existing) - set(expected_blocks) or any(existing[path] != expected_blocks[path] for path in existing):
                raise CaptureError("event_conflict", "Los originales Markdown ya identifican otro contenido con este event_id.")
            if set(existing) != set(expected_blocks):
                raise CaptureError("incomplete_event", "El evento sólo está en parte de sus archivos. Ejecuta status y recupera o concilia la captura.")
            return {"status": "already_applied", "event_id": capture["event_id"], "event_hash": event_hash, "paths": list(existing), "identity_source": "markdown"}
        correction = capture.get("correction_of")
        if correction and not self.receipt(correction) and not self.event_blocks(correction):
            raise CaptureError("unknown_event", "No existe el evento que se desea corregir.")
        changes = self.project(capture, event_hash)
        expected = {path: digest(before) if before is not None else None for path, (before, _) in changes.items()}
        plan = {"schema_version": 1, "capture": capture, "expected": expected, "event_hash": event_hash}
        plan["plan_id"] = digest(serialized(plan))
        result = {"status": "prepared", "plan": plan, "paths": list(changes)}
        if len(serialized(result)) > PLAN_LIMIT:
            raise CaptureError("too_large", "El plan supera el límite de aplicación local.")
        return result

    def project(self, capture: dict[str, Any], event_hash: str) -> dict[str, tuple[bytes | None, bytes]]:
        changes = {}
        event_id = capture["event_id"]
        date = capture["learned_on"]
        daily_path = f"{BASE}/Daily/{date[:4]}/{date}.md" if date else f"{BASE}/Daily/unknown.md"
        titles: dict[str, str] = {}
        for topic in capture["topics"]:
            slug, title = topic["slug"], topic["title"]
            relative = f"{BASE}/Topics/{slug}.md"
            self.protected(relative)
            for antecedent in topic["antecedents"]:
                if not antecedent.startswith("06_Knowledge_Base/") or self.read(antecedent) is None:
                    raise CaptureError("missing_antecedent", "Un antecedente no es una nota local existente de 06_Knowledge_Base.")
            before = self.read(relative)
            content = before.decode() if before else new_note(title, "evergreen", capture["captured_at"], learned_on=None)
            if before and metadata(content).get("classification") != "restricted":
                raise CaptureError("authority_conflict", "El destino no es una nota privada gestionada por este flujo.")
            addition = topic_block(capture, topic, event_hash, daily_path)
            content = append_once(content, event_id, addition)
            content = headers(content, title, capture["captured_at"])
            pointer = f"<!-- LEARNING-CURRENT: {event_id} -->\nRevisión vigente: [[#^learn-{event_id}|última explicación integrada]]. Las revisiones anteriores conservan la historia y su procedencia."
            content = re.sub(r"<!-- LEARNING-CURRENT: [^\n]+ -->\n[^\n]+", lambda _: pointer, content, count=1) if "<!-- LEARNING-CURRENT:" in content else content.replace("\n## Capturas y revisiones\n", f"\n{pointer}\n\n## Capturas y revisiones\n", 1)
            changes[relative] = (before, content.encode())
            titles[slug] = title
        self.protected(daily_path)
        before = self.read(daily_path)
        content = before.decode() if before else new_note("Aprendizajes", "daily", capture["captured_at"], learned_on=date)
        data = metadata(content)
        if before and data.get("classification") != "restricted":
            raise CaptureError("authority_conflict", "El registro diario no es una nota privada gestionada por este flujo.")
        daily_topics = data.get("learning_topics", {})
        if not isinstance(daily_topics, dict):
            raise CaptureError("invalid_note", "learning_topics no es un mapa.")
        daily_topics = {**daily_topics, **titles}
        title = "Aprendizajes: " + "; ".join(list(daily_topics.values())[:3])
        if len(daily_topics) > 3:
            title += f" y {len(daily_topics) - 3} temas más"
        content = headers(content, title, capture["captured_at"], learning_topics=daily_topics)
        daily = daily_block(capture, event_hash)
        content = append_once(content, event_id, daily)
        changes[daily_path] = (before, content.encode())
        for _, after in changes.values():
            if len(after) > LIMIT:
                raise CaptureError("too_large", "Una nota supera 1 MiB; requiere una división semántica explícita.")
        return changes

    def apply(self, supplied: Any) -> dict[str, Any]:
        self.verify_registered()
        plan = supplied.get("plan", supplied) if isinstance(supplied, dict) else supplied
        if not isinstance(plan, dict) or set(plan) != {"schema_version", "capture", "expected", "event_hash", "plan_id"} or plan["schema_version"] != 1:
            raise CaptureError("invalid_plan", "Utiliza el plan devuelto por prepare.")
        bare = {key: value for key, value in plan.items() if key != "plan_id"}
        if digest(serialized(bare)) != plan["plan_id"]:
            raise CaptureError("invalid_plan", "El plan ha cambiado.")
        with self.lock():
            if self.json_read("omaros-learning/pending.json"):
                raise CaptureError("pending", "Hay una escritura pendiente. Ejecuta status y recover.")
            fresh = self.prepare(plan["capture"])
            if fresh["status"] == "already_applied":
                return fresh
            if fresh["plan"] != plan:
                raise CaptureError("edit_conflict", "Los archivos cambiaron después de prepare; conserva las ediciones y prepara de nuevo.")
            changes = self.project(plan["capture"], plan["event_hash"])
            if {path: digest(before) if before is not None else None for path, (before, _) in changes.items()} != plan["expected"]:
                raise CaptureError("edit_conflict", "Los archivos cambiaron durante la preparación; vuelve a preparar sin descartar las ediciones.")
            receipt = {"event_id": plan["capture"]["event_id"], "event_hash": plan["event_hash"], "blocks": {path: digest(block(after.decode(), plan["capture"]["event_id"]).encode()) for path, (_, after) in changes.items()}, "topics": [t["slug"] for t in plan["capture"]["topics"]], "captured_at": plan["capture"]["captured_at"]}
            pending = {"schema_version": 1, "plan_id": plan["plan_id"], "receipt": receipt, "changes": [{"path": path, "before": digest(before) if before is not None else None, "after": after.decode(), "candidate": f".{Path(path).name}.{plan['plan_id'][:20]}.swap"} for path, (before, after) in changes.items()]}
            self.state_write("omaros-learning/pending.json", pending)
            return self._complete(pending)

    @staticmethod
    def candidate_name(change: dict[str, Any], pending: dict[str, Any], revision: int = 0) -> str:
        if type(revision) is not int or not 0 <= revision <= 10000:
            raise CaptureError("corrupt_state", "Revisión de candidato inválida.")
        suffix = f".{revision}" if revision else ""
        return f".{Path(change['path']).name}.{pending['plan_id'][:20]}{suffix}.swap"

    def candidate_path(self, change: dict[str, Any], name: str) -> str:
        return str(PurePosixPath(change["path"]).parent / name)

    def validate_candidates(self, change: dict[str, Any], pending: dict[str, Any]) -> None:
        if change["candidate"] != self.candidate_name(change, pending, change.get("candidate_revision", 0)):
            raise CaptureError("corrupt_state", "El candidato de recuperación no corresponde al destino.")
        for old in change.get("obsolete_candidates", []):
            if old["name"] != self.candidate_name(change, pending, old["revision"]):
                raise CaptureError("corrupt_state", "Un candidato previo no corresponde al destino.")

    def cleanup_obsolete(self, change: dict[str, Any]) -> None:
        for old in change.get("obsolete_candidates", []):
            data = self.read(self.candidate_path(change, old["name"]))
            if data is None:
                continue
            if digest(data) != old["hash"]:
                raise CaptureError("external_race", "Un candidato previo contiene otra edición; se conserva para conciliación.")
            with self.parent(change["path"]) as (fd, _):
                os.unlink(old["name"], dir_fd=fd)
                os.fsync(fd)

    def refresh_write_dates(self, change: dict[str, Any], pending: dict[str, Any]) -> None:
        date = dt.datetime.now(dt.timezone.utc).date().isoformat()
        data = metadata(change["after"])
        if str(data.get("updated")) == date and (change["before"] is not None or str(data.get("created")) == date):
            return
        fields = {"updated": date}
        if change["before"] is None:
            fields["created"] = date
        after = frontmatter_fields(change["after"], fields)
        if after == change["after"]:
            return
        candidate = self.read(self.candidate_path(change, change["candidate"]))
        if candidate is not None:
            if candidate != change["after"].encode():
                raise CaptureError("external_race", "El candidato pendiente contiene otra edición; no se refrescan sus fechas.")
            revision = change.get("candidate_revision", 0)
            change.setdefault("obsolete_candidates", []).append({"name": change["candidate"], "revision": revision, "hash": digest(candidate)})
            change["candidate_revision"] = revision + 1
            change["candidate"] = self.candidate_name(change, pending, revision + 1)
        change["after"] = after
        # A retry on another UTC day must date the actual write, while already
        # installed files retain their real earlier creation/update dates.
        self.state_write("omaros-learning/pending.json", pending)

    def _complete(self, pending: dict[str, Any]) -> dict[str, Any]:
        for change in pending["changes"]:
            relative = change["path"]
            self.validate_candidates(change, pending)
            self.resume_new_link(change)
            self.protected(relative)
            observed = self.read(relative)
            after = change["after"].encode()
            if observed != after:
                if (digest(observed) if observed is not None else None) != change["before"]:
                    raise CaptureError("recovery_conflict", "Un archivo pendiente tiene otra versión; se conserva para resolverla sin sobrescribir.")
                self.refresh_write_dates(change, pending)
                after = change["after"].encode()
                self.cleanup_obsolete(change)
                self._replace(change, observed)
            else:
                self.cleanup_obsolete(change)
            if self.read(relative) != after:
                raise CaptureError("persistence_conflict", "La versión observada después de escribir difiere. No se confirma el guardado.")
            with self.parent(relative) as (fd, _):
                try:
                    candidate = os.open(change["candidate"], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                except FileNotFoundError:
                    continue
                try:
                    self.check_file(candidate)
                    displaced = os.read(candidate, LIMIT + 1)
                    if (change["before"] is not None and digest(displaced) != change["before"]) or (change["before"] is None and displaced != after):
                        raise CaptureError("external_race", "Se conservó una edición concurrente en el archivo .swap privado. Requiere conciliación explícita.")
                finally:
                    os.close(candidate)
                os.unlink(change["candidate"], dir_fd=fd)
                os.fsync(fd)
        receipt = pending["receipt"]
        self.verify_receipt(receipt)
        self.state_write(f"omaros-learning/receipts/{receipt['event_id']}.json", receipt)
        with self.parent("omaros-learning/pending.json", state=True) as (fd, name):
            os.unlink(name, dir_fd=fd)
            os.fsync(fd)
        return {"status": "applied", "event_id": receipt["event_id"], "event_hash": receipt["event_hash"], "paths": list(receipt["blocks"])}

    def resume_new_link(self, change: dict[str, Any]) -> None:
        """Finish an interrupted link/unlink publication without accepting outside aliases.

        During first creation the pending journal names both the candidate and
        target. Exactly two links to the same regular inode, at those two names
        inside one verified private directory, account for every link. An
        arbitrary extra link must remain unreadable, including during recovery.
        """
        relative = change["path"]
        if change["before"] is not None or not os.path.lexists(self.root / relative):
            return
        self.check_private_target(relative)
        with self.parent(relative) as (fd, name):
            try:
                target = os.stat(name, dir_fd=fd, follow_symlinks=False)
                candidate = os.stat(change["candidate"], dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                return
            if (stat.S_ISREG(target.st_mode) and target.st_nlink == candidate.st_nlink == 2
                    and os.path.samestat(target, candidate)):
                # Keep the published target. The normal single-link read then
                # checks its bytes against the frozen recovery plan.
                os.unlink(change["candidate"], dir_fd=fd)
                os.fsync(fd)

    def _replace(self, change: dict[str, Any], observed: bytes | None) -> None:
        with self.parent(change["path"], create=True) as (fd, name):
            candidate_name = change["candidate"]
            try:
                candidate = os.open(candidate_name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            except FileExistsError:
                existing = os.open(candidate_name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    self.check_file(existing)
                    if os.read(existing, LIMIT + 1) != change["after"].encode():
                        raise CaptureError("candidate_exists", "El candidato difiere del plan; se conserva para conciliación explícita.")
                finally:
                    os.close(existing)
            else:
                try:
                    if observed is not None:
                        original = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                        try:
                            info = self.check_file(original)
                            os.fchmod(candidate, stat.S_IMODE(info.st_mode))
                            if sys.platform == "darwin":
                                lib = ctypes.CDLL(None, use_errno=True)
                                if lib.fcopyfile(original, candidate, None, 7) < 0:
                                    raise OSError(ctypes.get_errno(), "No se pudo preservar metadatos")
                        finally:
                            os.close(original)
                    self.write_all(candidate, change["after"].encode())
                    os.fsync(candidate)
                except BaseException:
                    os.close(candidate)
                    os.unlink(candidate_name, dir_fd=fd)
                    raise
                os.close(candidate)
            # Recheck immediately before exchange; the displaced inode remains
            # available if an editor races between this check and the exchange.
            if self.read(change["path"]) != observed:
                os.unlink(candidate_name, dir_fd=fd)
                raise CaptureError("edit_conflict", "El archivo cambió antes de escribir.")
            if observed is None:
                try:
                    os.link(candidate_name, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
                except FileExistsError:
                    os.unlink(candidate_name, dir_fd=fd)
                    raise CaptureError("edit_conflict", "Otro escritor creó el destino.") from None
                os.unlink(candidate_name, dir_fd=fd)
            else:
                exchange(fd, candidate_name, name)
            os.fsync(fd)

    def recover(self, *, abandon: bool = False) -> dict[str, Any]:
        self.verify_registered()
        with self.lock():
            pending = self.json_read("omaros-learning/pending.json")
            if not pending:
                return {"status": "no_pending"}
            if abandon:
                # Archiving the journal must not legitimise an unreconciled
                # displaced editor version as an already-applied capture.
                for change in pending["changes"]:
                    self.validate_candidates(change, pending)
                    self.protected(change["path"])
                    for old in change.get("obsolete_candidates", []):
                        data = self.read(self.candidate_path(change, old["name"]))
                        if data is not None and digest(data) != old["hash"]:
                            raise CaptureError("external_race", "Un candidato previo contiene otra edición; no se puede abandonar sin conciliar.")
                    displaced = self.read(self.candidate_path(change, change["candidate"]))
                    if displaced is not None and digest(displaced) != change["before"] and displaced != change["after"].encode():
                        raise CaptureError("external_race", "No se puede abandonar una edición desplazada sin conciliarla. Conserva pending y el .swap privado.")
                self.state_write(f"omaros-learning/recovery/{pending['plan_id']}.json", pending)
                with self.parent("omaros-learning/pending.json", state=True) as (fd, name):
                    os.unlink(name, dir_fd=fd)
                    os.fsync(fd)
                return {"status": "abandoned_partial", "persisted": False, "paths": [c["path"] for c in pending["changes"]], "recovery": str(self.state / "recovery" / (pending["plan_id"] + ".json"))}
            return self._complete(pending)

    def status(self) -> dict[str, Any]:
        self.verify_registered()
        pending = self.json_read("omaros-learning/pending.json")
        return {"status": "pending" if pending else "ready", "event_id": pending["receipt"]["event_id"] if pending else None, "paths": [c["path"] for c in pending["changes"]] if pending else [], "state": str(self.state)}

    def query(self, query: str = "", *, date: str | None = None, topic: str | None = None, related: str | None = None) -> dict[str, Any]:
        self.verify_registered()
        if date and date != "unknown":
            iso_date(date)
        if topic and not SLUG.fullmatch(topic):
            raise CaptureError("invalid_input", "Slug inválido.")
        results = []
        # The private scope is explicit; no whole-vault index or hidden cap.
        candidates = self.private_paths()
        for path in candidates:
            relative = path.relative_to(self.root).as_posix()
            self.protected(relative)
            content = self.read(relative).decode()
            data = metadata(content)
            if date and (data.get("note_type") != "daily" or (str(data.get("learned_on")) if data.get("learned_on") is not None else "unknown") != date):
                continue
            if topic and path.stem != topic and topic not in data.get("learning_topics", {}):
                continue
            if related and related not in content:
                continue
            if query and query.casefold() not in (str(data.get("title", "")) + "\n" + content + "\n" + path.stem).casefold():
                continue
            results.append({"path": relative, "title": data["title"], "learned_on": str(data["learned_on"]) if data.get("learned_on") else None, "captured_at": str(data.get("captured_at")), "updated": str(data.get("updated"))})
        pending = self.json_read("omaros-learning/pending.json")
        return {"status": "pending" if pending else "ok", "scope": BASE, "partial": bool(pending), "pending_event": pending["receipt"]["event_id"] if pending else None, "scanned": len(candidates), "results": results}


def exchange(fd: int, candidate: str, target: str) -> None:
    lib = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        function = lib.renameatx_np
        flags = 18  # RENAME_SWAP | RENAME_NOFOLLOW_ANY
    elif sys.platform.startswith("linux") and hasattr(lib, "renameat2"):
        function = lib.renameat2
        flags = 2  # RENAME_EXCHANGE
    else:
        raise CaptureError("unsupported_platform", "Se requiere intercambio atómico de archivos para preservar ediciones concurrentes.")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(fd, candidate.encode(), fd, target.encode(), flags) < 0:
        raise OSError(ctypes.get_errno(), "Falló el intercambio atómico")


def metadata(content: str) -> dict[str, Any]:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", content, re.S)
    if not match:
        raise CaptureError("invalid_note", "La nota no tiene metadatos YAML.")
    try:
        result = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        raise CaptureError("invalid_note", "Metadatos YAML inválidos.") from None
    if not isinstance(result, dict):
        raise CaptureError("invalid_note", "Los metadatos deben ser un mapa.")
    return result


def new_note(title: str, kind: str, captured_at: str, *, learned_on: str | None) -> str:
    date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    area = "daily" if kind == "daily" else "topics"
    tags = [f"kb/mathematics/finance/engie/private/{area}", "field/mathematics", f"note_type/{kind}", "topic/finance/markets/engie", "topic/finance/markets/energy", "lang/es", "status/draft", "lifecycle/latex_pending"]
    data = {"title": title, "note_type": kind, "domain": "06_Knowledge_Base", "subdomain": "Mathematics/Finance/ENGIE", "tags": tags, "status": "draft", "created": date, "updated": date, "author": "Omar", "ai_generated": True, "ai_reviewed": False, "latex_pending": True, "classification": "restricted", "publish": False, "captured_at": captured_at, "learned_on": learned_on}
    return "---\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False).rstrip() + f"\n---\n\n# {title}\n\n## Capturas y revisiones\n\n<!-- LEARNING:INSERT -->\n\n## Related notes\n\n### Manual additions\n- [[06_Knowledge_Base/Mathematics/Finance/ENGIE/README|Conocimiento ENGIE]]\n"


def frontmatter_fields(content: str, fields: dict[str, Any]) -> str:
    metadata(content)
    match = re.match(r"\A(---\r?\n)(.*?)(\r?\n---\r?\n)", content, re.S)
    assert match is not None
    front = match.group(2)
    for key, value in fields.items():
        # Use a single-line JSON-compatible YAML value to preserve every other
        # frontmatter line, including user comments and custom fields.
        rendered = f"{key}: " + json.dumps(value, ensure_ascii=False)
        expression = rf"(?m)^{re.escape(key)}:.*(?:\n(?:[ \t]+.*|-(?: .*)?))*"
        if re.search(expression, front):
            front = re.sub(expression, lambda _: rendered, front, count=1)
        else:
            front += "\n" + rendered
    return match.group(1) + front + match.group(3) + content[match.end():]


def headers(content: str, title: str, captured_at: str, **extra: Any) -> str:
    content = frontmatter_fields(content, {"title": title, "updated": dt.datetime.now(dt.timezone.utc).date().isoformat(), **extra})
    match = re.match(r"\A---\r?\n.*?\r?\n---\r?\n", content, re.S)
    assert match is not None
    body = content[match.end():]
    offset = 0
    for line in body.splitlines(keepends=True):
        if line.strip():
            if line.startswith("# "):
                ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
                body = body[:offset] + "# " + title + ending + body[offset + len(line):]
            else:
                # A removed note title must not redirect the replacement into
                # a historical event or a fenced example further down.
                body = "# " + title + "\n\n" + body
            break
        offset += len(line)
    else:
        body += "# " + title + "\n"
    return content[:match.end()] + body


def block(content: str, event_id: str) -> str | None:
    match = re.search(rf"<!-- LEARNING:BEGIN {re.escape(event_id)} [a-f0-9]{{64}} -->\n.*?<!-- LEARNING:END {re.escape(event_id)} -->", content, re.S)
    return match.group(0) if match else None


def append_once(content: str, event_id: str, addition: str) -> str:
    existing = block(content, event_id)
    if existing:
        if existing != addition:
            raise CaptureError("event_conflict", "El evento ya aparece con otro contenido en la nota.")
        return content
    marker = "<!-- LEARNING:INSERT -->"
    if content.count(marker) != 1:
        raise CaptureError("invalid_note", "Falta el marcador único de inserción; conserva la edición y revisa la nota.")
    return content.replace(marker, addition + "\n\n" + marker, 1)


def wrapped(event_id: str, event_hash: str, body: str) -> str:
    return f"<!-- LEARNING:BEGIN {event_id} {event_hash} -->\n{body.rstrip()}\n<!-- LEARNING:END {event_id} -->"


def topic_block(capture: dict[str, Any], topic: dict[str, Any], event_hash: str, daily_path: str) -> str:
    event_id = capture["event_id"]
    learned = capture["learned_on"] or "desconocida"
    body = f"### {topic['title']}\n\n^learn-{event_id}\n\nAprendizaje: {learned}. Captura: {capture['captured_at']}. Evento: `{event_id}`.\n"
    if capture.get("correction_of"):
        body += f"\n**Corrección explícita del evento `{capture['correction_of']}`.** La versión anterior se conserva como historia y queda revisada por esta aportación.\n"
    body += "\n" + topic["body"] + "\n\nProcedencia:\n"
    kinds = {"user": "Aportado por Omar", "source": "Respaldado por fuente", "ai_proposal": "Propuesta de IA pendiente de validar"}
    for source in topic["provenance"]:
        body += f"- {kinds[source['kind']]}: {source['reference']}\n"
    for field, label in (("conditions", "Condiciones y límites"), ("examples", "Ejemplos"), ("questions", "Dudas y lagunas abiertas"), ("contradictions", "Discrepancias sin resolver")):
        if topic[field]:
            body += "\n**" + label + "**\n" + "".join("- " + value + "\n" for value in topic[field])
    body += f"\nRegistro temporal: [[{daily_path}|{learned}]].\n"
    if topic["antecedents"]:
        body += "Antecedentes (sus fuentes conservan autoridad):\n" + "".join(f"- [[{path}|{Path(path).stem}]]\n" for path in topic["antecedents"])
    return wrapped(event_id, event_hash, body)


def daily_block(capture: dict[str, Any], event_hash: str) -> str:
    event_id = capture["event_id"]
    body = f"### Captura {capture['captured_at']}\n\n^learn-{event_id}\n\n{capture['summary']}\n\nAprendido: {capture['learned_on'] or 'fecha desconocida'}. Evento: `{event_id}`.\n"
    if capture.get("correction_of"):
        body += f"Corrección del evento `{capture['correction_of']}`.\n"
    for topic in capture["topics"]:
        body += f"- [[{BASE}/Topics/{topic['slug']}.md#^learn-{event_id}|{topic['title']}]]\n"
        for field, label in (("questions", "Duda"), ("contradictions", "Discrepancia")):
            for value in topic[field]:
                body += f"  - {label}: {value}\n"
    return wrapped(event_id, event_hash, body)


def main(argv: list[str], *, device_home: Path) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Raíz Git exacta de OmarOS; por defecto se descubre desde el directorio actual.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    commands.add_parser("apply")
    commands.add_parser("status")
    recovery = commands.add_parser("recover")
    recovery.add_argument("--abandon", action="store_true", help="Conservar journal en recovery, dejar archivos actuales y liberar el bloqueo pendiente.")
    query = commands.add_parser("query")
    query.add_argument("text", nargs="?", default="")
    query.add_argument("--date")
    query.add_argument("--topic")
    query.add_argument("--related")
    arguments = parser.parse_args(argv)
    try:
        store = Store(arguments.root, device_home=device_home)
        if arguments.command in {"prepare", "apply"}:
            limit = PLAN_LIMIT if arguments.command == "apply" else LIMIT
            raw = sys.stdin.buffer.read(limit + 1)
            if len(raw) > limit:
                raise CaptureError("too_large", "La entrada supera el límite de captura o plan local.")
            payload = json.loads(raw)
            result = store.prepare(payload) if arguments.command == "prepare" else store.apply(payload)
        elif arguments.command == "status":
            result = store.status()
        elif arguments.command == "recover":
            result = store.recover(abandon=arguments.abandon)
        else:
            result = store.query(arguments.text, date=arguments.date, topic=arguments.topic, related=arguments.related)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (CaptureError, OSError, UnicodeError, ValueError) as error:
        result = {"status": "error", "code": error.code if isinstance(error, CaptureError) else "io_error", "message": str(error) if isinstance(error, CaptureError) else "Error de lectura o escritura local; ejecuta status antes de reintentar.", "persisted": False}
        print(json.dumps(result, ensure_ascii=False))
        return 2
