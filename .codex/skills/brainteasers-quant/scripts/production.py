#!/usr/bin/env python3
"""Build and audit Hespérides sessions; bind declared review to current artifacts.

The shared system supplies the base template and its legacy gates.
This course enforces one static PDF page per frame.
No heuristic in this module certifies mathematical or visual quality.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import ExitStack, contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, BinaryIO, Callable, Iterator

PHASES = ("pre", "tex", "compile", "entrega")
REVIEW_CHECKS = ("mathematics", "understanding", "synchronization", "visual_identity",
                 "palette", "tikz_quality")


class ProductionError(RuntimeError):
    """The requested operation cannot produce trustworthy evidence."""


def installed_module(name: str, path: Path) -> Any:
    """Load only modules at fixed locations inside the installed distribution."""
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ProductionError(f"Installed module unavailable: {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
        except BaseException:
            del sys.modules[name]
            raise
    return sys.modules[name]


def trusted_engine(system: Path) -> Any:
    module = installed_module("_constellation_bqt_course_engine", Path(__file__).with_name("course_engine.py"))
    return module.trusted_engine(system)


def platform() -> Any:
    return installed_module("_constellation_bqt_platform",
                            Path(__file__).resolve().parents[3] / "ecosystem/platform_support.py")


def tool_env(**settings: str) -> dict[str, str]:
    """Keep toolchain paths and locale; shell/Python startup hooks do not enter child processes."""
    names = ("PATH", "HOME", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL", "LC_CTYPE")
    return {**{k: os.environ[k] for k in names if k in os.environ}, "PYTHONDONTWRITEBYTECODE": "1", **settings}


def physical(path: Path) -> Path:
    """Normalize spelling without following a project-controlled symlink."""
    path = path.absolute()
    if ".." in path.parts:
        raise ProductionError(f"Use a path without parent traversal: {path}")
    if sys.platform == "darwin" and len(path.parts) > 1 and path.parts[1] in {"tmp", "var"}:
        alias = Path("/") / path.parts[1]
        if alias.is_symlink() and os.readlink(alias) == f"private/{alias.name}":
            path = Path("/private").joinpath(*path.parts[1:])
    return path


@contextmanager
def directory(path: Path, *, create: bool = False) -> Iterator[int]:
    """Pin every directory transition, rejecting a symlink at any component."""
    path = physical(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for component in path.parts[1:]:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def regular(info: os.stat_result, path: Path) -> None:
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ProductionError(f"Expected an unaliased regular file: {path}")


@contextmanager
def read_file(path: Path, *, system_dependency: bool = False) -> Iterator[BinaryIO]:
    with directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(fd)
            if not system_dependency:
                regular(info, path)
            elif not stat.S_ISREG(info.st_mode):
                raise ProductionError(f"TeX dependency must be a regular file: {path}")
            yield stream


def atomic_file(path: Path, write: Callable[[BinaryIO], Any], *, exclusive: bool = False) -> None:
    """Publish complete bytes in one pinned directory; no writable target is followed."""
    with directory(path.parent, create=True) as parent:
        try:
            previous = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            previous = None
        if previous is not None:
            regular(previous, path)
            if exclusive:
                raise ProductionError(f"Output already exists: {path}")
        temporary = ".production-" + secrets.token_hex(24)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        reserved = os.fstat(fd)
        try:
            with os.fdopen(fd, "wb") as stream:
                write(stream)
                stream.flush()
                if previous is not None:
                    os.fchmod(fd, stat.S_IMODE(previous.st_mode) & 0o777)
                os.fsync(fd)
                current = os.stat(temporary, dir_fd=parent, follow_symlinks=False)
                regular(current, path)
                if not os.path.samestat(current, os.fstat(fd)):
                    raise ProductionError(f"Temporary file was replaced: {path}")
                if exclusive:
                    os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent,
                            follow_symlinks=False)
                else:
                    os.replace(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent)
            os.fsync(parent)
        finally:
            try:
                if os.path.samestat(reserved, os.stat(temporary, dir_fd=parent, follow_symlinks=False)):
                    os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass


def entries(root: Path, *, sources_only: bool = False, owner_anchor: Path | None = None) -> Iterator[tuple[Path, bool]]:
    """Enumerate a bounded project tree through open handles, without following aliases."""
    def walk(fd: int, relative: Path) -> Iterator[tuple[Path, bool]]:
        for name in sorted(os.listdir(fd)):
            if name.casefold() == ".git" and owner_anchor is not None and root / relative != owner_anchor:
                raise ProductionError(f"Selected course path crosses a nested Git owner: {root / relative}")
            if sources_only and (name in {"build", "__pycache__"} or name.startswith(".")):
                continue
            rel = relative / name
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                with ExitStack() as stack:
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    stack.callback(os.close, child)
                    if not os.path.samestat(info, os.fstat(child)):
                        raise ProductionError(f"Directory changed during inspection: {root / rel}")
                    yield rel, True
                    if name.casefold() != ".git":
                        yield from walk(child, rel)
            else:
                regular(info, root / rel)
                yield rel, False
    with directory(root) as fd:
        yield from walk(fd, Path())


def copy_file(source: Path, target: Path, *, exclusive: bool = False) -> None:
    with read_file(source) as stream:
        atomic_file(target, lambda output: shutil.copyfileobj(stream, output), exclusive=exclusive)


def copy_sources(source: Path, replica: Path) -> None:
    replica.mkdir(mode=0o700)
    with directory(source) as src, directory(replica) as dst:
        copy_owned_tree(src, dst, sources_only=True)


def sha(path: Path, *, system_dependency: bool = False) -> str:
    with read_file(path, system_dependency=system_dependency) as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value: Any) -> None:
    content = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    atomic_file(path, lambda stream: stream.write(content))


@contextmanager
def locked(output: Path) -> Iterator[None]:
    try:
        import fcntl
    except ImportError:
        raise ProductionError("Production requires a POSIX environment with bash, TeX and file locking.") from None
    with directory(output, create=True) as parent:
        fd = os.open(".lock", os.O_RDWR | os.O_CREAT | os.O_NONBLOCK | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        try:
            regular(os.fstat(fd), output / ".lock")
            fcntl.flock(fd, fcntl.LOCK_EX)
            named = os.stat(".lock", dir_fd=parent, follow_symlinks=False)
            if not os.path.samestat(named, os.fstat(fd)):
                raise ProductionError(f"Lock was replaced: {output}")
            yield
        finally:
            os.close(fd)


@contextmanager
def scope_locked(target: Path, videos: list[Path], boundary: CourseBoundary | None = None) -> Iterator[None]:
    """Session and individual-video runs serialize on the same video locks."""
    outputs = {target / "build/production", *(v / "build/production" for v in videos)}
    if boundary is not None:
        # Validate every sibling before even the first visible lock can be created.
        boundary.check_tree(target)
        for output in outputs:
            boundary.check_path(output)
    with ExitStack() as stack:
        for output in sorted(outputs):
            if boundary is not None:
                boundary.check_path(output)
            stack.enter_context(locked(output))
        yield


def managed_build(video: Path) -> Path:
    build = video / "build"
    with directory(build, create=True):
        pass
    return build


def command(argv: list[str], log: Path, env: dict[str, str]) -> int:
    """Persist unsuccessful output as evidence, including timeouts."""
    # Only the disposable build tree is passed to external tools.
    work = log.parents[2]
    list(entries(work))
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=240,
                                env=env, errors="replace", cwd=work)
        list(entries(work))
        atomic_file(log, lambda stream: stream.write((result.stdout + result.stderr).encode()))
        return result.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        atomic_file(log, lambda stream: stream.write((str(exc) + "\n").encode()))
        return 124 if isinstance(exc, subprocess.TimeoutExpired) else 127


def source_files(root: Path) -> list[Path]:
    if not os.path.lexists(root):
        return []
    return [root / rel for rel, is_dir in entries(root, sources_only=True) if not is_dir]


def sources(target: Path, system: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    script = Path(__file__).resolve()
    tools = (script, script.with_name("course_engine.py"), script.parents[1] / "references/course-engine.json",
             script.parents[3] / "ecosystem/platform_support.py")
    for path in [*source_files(target), *source_files(system), *tools]:
        result[str(physical(path))] = sha(path)
    return result


def tex_installation_roots() -> set[Path]:
    """Identify the installed TeX and font resources a recorder may legitimately name."""
    locations = {Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path("/System/Library/Fonts"),
                 Path("/Library/Fonts"), Path.home() / "Library/Fonts", Path.home() / ".local/share/fonts"}
    executable = shutil.which("kpsewhich")
    if executable:
        for variable in ("TEXMFROOT", "TEXMFLOCAL", "TEXMFSYSVAR", "TEXMFVAR", "TEXMFSYSCONFIG",
                         "TEXMFCONFIG", "TEXMFHOME"):
            result = subprocess.run([executable, "--var-value=" + variable], capture_output=True,
                                    text=True, timeout=10, check=False, env=tool_env())
            if result.returncode == 0:
                locations.update(Path(value) for value in result.stdout.strip().split(os.pathsep)
                                 if Path(value).is_absolute())
    return {p.resolve() for p in locations if p.is_dir() and p.resolve() not in {Path("/"), Path.home()}}


def inventory(target: Path, system: Path, videos: list[Path],
              course_inputs: dict[str, str] | None = None) -> dict[str, str]:
    result = sources(target, system)
    tex_roots: set[Path] | None = None
    for video in videos:
        build = video / "build"
        paths = [build / "presentacion.pdf", build / "main.nav", build / "main.log",
                 build / "main.fls", *sorted((build / "paginas").glob("*.png"))]
        paths += sorted((build / "production").glob("*.log"))
        fls = build / "main.fls"
        if fls.is_file():
            with read_file(fls) as stream:
                records = stream.read().decode(errors="replace").splitlines()
            working = video / "presentacion"
            for line in records:
                if line.startswith("PWD ") and Path(line[4:]).is_absolute():
                    working = Path(line[4:])
                if line.startswith("INPUT "):
                    path = Path(line[6:])
                    if not path.is_absolute():
                        path = working / path
                    path = path.resolve()
                    if not path.is_file() or path.is_relative_to(build.resolve()):
                        continue
                    if path.is_relative_to(target) or path.is_relative_to(system) or str(path) in (course_inputs or {}):
                        paths.append(path)
                    else:
                        if tex_roots is None:
                            tex_roots = tex_installation_roots()
                        if not any(path.is_relative_to(root) for root in tex_roots):
                            raise ProductionError(f"Recorder input outside course, engine and TeX roots: {path}")
                        if str(path) not in result:
                            result[str(path)] = sha(path, system_dependency=True)
        for path in paths:
            if path.is_file():
                result[str(path.resolve())] = sha(path)
    return result


def fingerprint(report: dict[str, Any]) -> str:
    payload = {k: v for k, v in report.items() if k != "audit_fingerprint"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def discover(target: Path) -> tuple[list[Path], bool]:
    if (target / "presentacion/main.tex").is_file():
        return [target], False
    if not re.fullmatch(r"sesion-\d{2}", target.name):
        raise ProductionError("Expected a sesion-SS folder or a video with presentacion/main.tex")
    videos = sorted(p for p in target.glob("video-*") if p.is_dir())
    if not videos:
        raise ProductionError(f"No videos in {target}")
    if any(not (p / "presentacion/main.tex").is_file() for p in videos):
        raise ProductionError("Every direct video-* folder must contain presentacion/main.tex")
    numbers = [re.match(r"video-(\d{2})-", p.name) for p in videos]
    if any(n is None for n in numbers) or len({n[1] for n in numbers if n}) != len(videos):
        raise ProductionError("Invalid or duplicate video numbers")
    return videos, True


def load_parser(system: Path) -> Any:
    spec = importlib.util.spec_from_file_location("brainteasers_guion", system / "hooks/comun.py")
    if spec is None or spec.loader is None:
        raise ProductionError("Cannot load the shared teleprompter parser")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    with read_file(system / "hooks/comun.py") as source:
        exec(compile(source.read(), spec.origin, "exec"), module.__dict__)
    return module


def timeline(guion: Any) -> tuple[int, list[str]]:
    errors: list[str] = []
    end = 0
    if not guion.bloques:
        errors.append("No teleprompter time blocks")
    for block in guion.bloques:
        if block.inicio_s != end or block.fin_s <= block.inicio_s:
            errors.append(f"Non-contiguous or non-positive time block at line {block.linea}")
        end = block.fin_s
    declared = guion.meta_int("duracion_estimada_s")
    target = guion.meta_int("duracion_objetivo_s")
    if declared is None or declared <= 0 or abs(end - declared) > 2:
        errors.append("Time blocks do not match a positive duracion_estimada_s within 2 seconds")
    if target is None or target <= 0 or abs(end - target) > target * 0.05:
        errors.append("Time blocks are outside the target duration ±5%")
    return end, errors


def session_duration(seconds: list[int]) -> list[str]:
    total = sum(seconds)
    return [] if 1800 <= total <= 2160 else [f"Session is {total}s; required range is 1800–2160s"]


def overlay_map(nav: str, page_count: int) -> list[dict[str, int]]:
    ranges = re.findall(r"\\beamer@framepages\s*\{(\d+)\}\s*\{(\d+)\}", nav)
    pages: list[dict[str, int]] = []
    expected = 1
    for frame, (left, right) in enumerate(ranges, 1):
        start, stop = int(left), int(right)
        if start != expected or stop < start or stop > page_count:
            raise ProductionError(f"Invalid frame/page mapping at frame {frame}")
        if start != stop:
            raise ProductionError(f"Static slides require one PDF page per frame; frame {frame} spans pages {start}-{stop}")
        pages.extend({"page": p, "frame": frame, "overlay": p - start + 1,
                      "overlays": stop - start + 1} for p in range(start, stop + 1))
        expected = stop + 1
    if expected != page_count + 1 or not pages:
        raise ProductionError("main.nav does not cover every PDF page")
    return pages


def contact_sheets(pages: list[dict[str, Any]], output: Path) -> list[str]:
    from PIL import Image, ImageDraw

    sheets: list[str] = []
    for start in range(0, len(pages), 12):
        canvas = Image.new("RGB", (1600, 1080), "#e5e5e5")
        draw = ImageDraw.Draw(canvas)
        for i, page in enumerate(pages[start:start + 12]):
            x, y = (i % 3) * 533 + 8, (i // 3) * 270 + 22
            with Image.open(page["png"]) as im:
                im.thumbnail((517, 240))
                canvas.paste(im, (x, y))
            draw.text((x, y - 17), f'{page["id"]} / F{page["frame"]}', fill="black")
        path = output / f"contact-{start // 12 + 1:02d}.png"
        atomic_file(path, lambda stream: canvas.save(stream, format="PNG"))
        sheets.append(str(path))
    return sheets


def inspect_pdf(video: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    import pymupdf

    build = video / "build"
    errors: list[str] = []
    warnings: list[str] = []
    with pymupdf.open(build / "presentacion.pdf") as pdf:
        mapping = overlay_map((build / "main.nav").read_text(), len(pdf))
        pngs = sorted((build / "paginas").glob("*.png"),
                      key=lambda p: int(re.search(r"(\d+)\.png$", p.name)[1]))
        if len(pngs) != len(pdf):
            raise ProductionError("Rendered PNG count differs from the PDF")
        for page, record, png in zip(pdf, mapping, pngs):
            record.update(id=f"{video.name}/p{page.number + 1:03d}", png=str(png))
            if abs(page.rect.width / page.rect.height - 16 / 9) > 0.01:
                errors.append(f'{record["id"]}: PDF is not 16:9')
            small = set()
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        if not span["text"].strip():
                            continue
                        box = pymupdf.Rect(span["bbox"])
                        bounds = page.rect + (-1, -1, 1, 1)
                        if not bounds.contains(box):
                            errors.append(f'{record["id"]}: text extends outside the page: {span["text"][:50]}')
                        if span["size"] < 6:
                            small.add(round(span["size"], 1))
            if small:
                warnings.append(f'{record["id"]}: inspect small text {sorted(small)} pt (indices may be valid)')
    log = (build / "main.log").read_text(errors="replace")
    for match in re.finditer(r"Overfull \\[hv]box \((\d+(?:\.\d+)?)pt too (?:wide|high)\)", log):
        message = f"{video.name}: {match[0]}"
        (errors if float(match[1]) > 12 else warnings).append(message)
    if "Missing character:" in log:
        errors.append(f"{video.name}: missing glyphs in main.log")
    return mapping, errors, warnings


def _compile_copy(target: Path, system: Path, env: dict[str, str]) -> dict[str, Any]:
    videos, complete_session = discover(target)
    for path in [target, *videos]:
        managed_build(path)
    output = target / "build/production"
    with directory(output, create=True):
        pass
    parser = load_parser(system)
    report: dict[str, Any] = {"schema": 1, "target": str(target), "system": str(system),
                             "complete_session": complete_session, "videos": [],
                             "errors": [], "warnings": [], "pages": []}
    durations: list[int] = []
    declared_durations: list[int] = []
    for video in videos:
        logs = video / "build/production"
        logs.mkdir(exist_ok=True)
        result: dict[str, Any] = {"path": str(video), "phases": {}, "seconds": None}
        guion, parse_errors = parser.parsear_guion(video / "guion-teleprompter.md")
        report["errors"].extend(f"{video.name}: {e}" for e in parse_errors)
        if guion is not None:
            seconds, errors = timeline(guion)
            if not parse_errors and not errors:
                durations.append(seconds)
                result["seconds"] = seconds
            declared = guion.meta_int("duracion_estimada_s")
            if declared is not None and declared > 0:
                declared_durations.append(declared)
            result["declared_seconds"] = declared
            report["errors"].extend(f"{video.name}: {e}" for e in errors)
        build_code = command(["bash", str(system / "scripts/build.sh"), str(video)], logs / "build.log", env)
        result["build_exit"] = build_code
        if build_code:
            report["errors"].append(f"{video.name}: build failed; old PDF is not reviewed")
        else:
            render_code = command(["bash", str(system / "scripts/render.sh"), str(video), "305"],
                                  logs / "render.log", env)
            result["render_exit"] = render_code
            if render_code:
                report["errors"].append(f"{video.name}: render failed")
            else:
                try:
                    if not (video / "build/main.fls").is_file():
                        report["errors"].append(f"{video.name}: missing TeX dependency recorder main.fls")
                    pages, errors, warnings = inspect_pdf(video)
                    report["pages"].extend(pages)
                    report["errors"].extend(errors)
                    report["warnings"].extend(warnings)
                    frames = {p["frame"] for p in pages}
                    if guion is not None and {b.slide for b in guion.bloques} != frames:
                        report["errors"].append(f"{video.name}: guion SLIDE coverage differs from compiled frames")
                except (OSError, ValueError, ProductionError) as exc:
                    report["errors"].append(f"{video.name}: {exc}")
        # Even a failing inherited gate is retained verbatim, never relabelled.
        for phase in PHASES:
            if phase in {"compile", "entrega"} and (build_code or result.get("render_exit")):
                result["phases"][phase] = None
                continue
            result["phases"][phase] = command(
                [sys.executable, "-I", "-B", str(system / "scripts/validar.py"), str(video), "--fase", phase],
                logs / f"legacy-{phase}.log", env)
        report["videos"].append(result)
    report["seconds"] = sum(durations) if len(durations) == len(videos) else None
    report["declared_seconds"] = sum(declared_durations) if len(declared_durations) == len(videos) else None
    if complete_session:
        if report["seconds"] is None:
            report["errors"].append("Session duration cannot be verified until all time blocks parse and agree")
        else:
            report["errors"].extend(session_duration(durations))
    report["legacy_passed"] = all(v["phases"].get(p) == 0 for v in report["videos"] for p in PHASES)
    report["mechanical_passed"] = not report["errors"]
    report["contact_sheets"] = contact_sheets(report["pages"], output)
    return report


def directory_identity(path: Path) -> tuple[int, int]:
    with directory(path) as fd:
        info = os.fstat(fd)
        return info.st_dev, info.st_ino


def translated(content: bytes, replacements: dict[Path, Path]) -> bytes:
    for source, destination in replacements.items():
        prefix = re.escape(os.fsencode(source))
        content = re.sub(prefix + rb"(?=[/}\\\s\"']|$)", lambda _: os.fsencode(destination), content)
    return content


def translate_sources(tree: Path, replacements: dict[Path, Path]) -> None:
    """Retarget explicit project references only inside the disposable teaching sources."""
    for rel, is_dir in entries(tree):
        if is_dir or rel.suffix.lower() not in {".md", ".tex", ".sty", ".tikz", ".cls", ".def", ".cfg"}:
            continue
        path = tree / rel
        with read_file(path) as stream:
            original = stream.read()
        result = translated(original, replacements)
        if result != original:
            atomic_file(path, lambda output: output.write(result))


def course_root(target: Path) -> Path | None:
    for ancestor in (target, *target.parents):
        if re.fullmatch(r"sesion-\d{2}", ancestor.name) and ancestor.parent.name == "asincronas":
            return ancestor.parent.parent
    return None


def course_anchor(target: Path) -> Path:
    """A canonical course governs its nested sessions; an explicit standalone unit owns itself."""
    root = course_root(target)
    if root is not None:
        return root
    return next((p for p in (target, *target.parents) if re.fullmatch(r"sesion-\d{2}", p.name)), target)


def git_checkout(folder: Path) -> tuple[Path, Path, tuple[int, int], tuple[int, int]] | None:
    """Identify the real worktree and its per-checkout administration; distinguish standalone folders."""
    with directory(folder):
        env = tool_env(LC_ALL="C", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
        result = subprocess.run(["git", "--no-replace-objects", "-C", str(folder), "rev-parse",
                                 "--show-toplevel", "--absolute-git-dir"], env=env, text=True,
                                capture_output=True, timeout=15)
    if result.returncode:
        if result.returncode == 128 and result.stderr.startswith("fatal: not a git repository") and not any(
                os.path.lexists(p / ".git") for p in (folder, *folder.parents)):
            return None
        raise ProductionError(f"Cannot establish the owning Git checkout for {folder}")
    lines = result.stdout.splitlines()
    if len(lines) != 2 or any(not Path(line).is_absolute() for line in lines):
        raise ProductionError(f"Git reported an ambiguous checkout for {folder}")
    root, admin = (Path(line).resolve(strict=True) for line in lines)
    if not folder.is_relative_to(root):
        raise ProductionError(f"Git worktree does not contain selected path: {folder}")
    return root, admin, directory_identity(root), directory_identity(admin)


class CourseBoundary:
    """Pin the selected course's Git owner while retaining standalone, bounded course fixtures."""

    def __init__(self, anchor: Path) -> None:
        self.anchor = anchor
        self.identity = directory_identity(anchor)
        self.owner = git_checkout(anchor)

    def check_path(self, path: Path) -> None:
        if not path.is_relative_to(self.anchor) or self.identity != directory_identity(self.anchor):
            raise ProductionError(f"Selected path is outside the original course: {path}")
        current = path
        while not os.path.lexists(current):
            current = current.parent
        if not stat.S_ISDIR(current.lstat().st_mode):
            regular(current.lstat(), current)
            current = current.parent
        for candidate in (current, *current.parents):
            if candidate == self.anchor:
                break
            if os.path.lexists(candidate / ".git"):
                raise ProductionError(f"Selected path crosses a nested Git owner: {candidate}")
        if git_checkout(current) != self.owner:
            raise ProductionError(f"Selected path changed or belongs to another Git checkout: {path}")

    def check_tree(self, root: Path) -> None:
        list(entries(root, owner_anchor=self.anchor))
        self.check_path(root)

    def claim(self) -> dict[str, Any]:
        return {"anchor": str(self.anchor), "identity": list(self.identity),
                "git": None if self.owner is None else
                {"worktree": str(self.owner[0]), "administration": str(self.owner[1]),
                 "worktree_identity": list(self.owner[2]), "administration_identity": list(self.owner[3])}}


def course_context(target: Path, engine: Path, destination: Path | None = None,
                   *, boundary: CourseBoundary) -> dict[str, str]:
    """Mirror named sources, image assets and only the problem-bank texts actually used by this lesson."""
    course = course_root(target)
    verifier = engine / "hooks/check_pre.py"
    if course is None or not verifier.is_file():
        return {}
    with read_file(verifier) as stream:
        statements = ast.parse(stream.read()).body
    declaration = next((node.value for node in statements if isinstance(node, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "FUENTES_OBLIGATORIAS" for t in node.targets)), None)
    if declaration is None:
        return {}
    if not isinstance(declaration, (ast.List, ast.Tuple)) or any(
            not isinstance(p, ast.Constant) or not isinstance(p.value, str) for p in declaration.elts):
        raise ProductionError("The verified validator must declare literal project-relative course inputs")
    videos, _ = discover(target)
    problem_bank = False
    for video in videos:
        guion = video / "guion-teleprompter.md"
        if guion.is_file():
            with read_file(guion) as stream:
                if re.search(rb"(?im)^problema_v8:\s*['\"]?(?:M[1-8]|R[1-6]|E[12])-\d{3}", stream.read()):
                    problem_bank = True
                    break
    evidence = {}
    for node in declaration.elts:
        rel = Path(node.value)
        if rel.is_absolute() or not rel.parts or any(p == ".." or p.startswith(".") for p in rel.parts):
            raise ProductionError("The validator's course reference must select a project-relative teaching source")
        source = course / rel
        boundary.check_path(source)
        try:
            with directory(source.parent) as parent:
                info = os.stat(source.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            continue
        children = [(Path(), stat.S_ISDIR(info.st_mode))]
        if children[0][1]:
            with directory(source):
                pass
            if rel.as_posix() == "hesperides-beamer-template/images":
                children.extend(entries(source, sources_only=True, owner_anchor=boundary.anchor))
            elif problem_bank and rel.name in {"enunciados", "soluciones"} and rel.parent.name == "problemas":
                children.extend((p, False) for p, is_dir in entries(source, sources_only=True, owner_anchor=boundary.anchor)
                                if not is_dir and p.suffix == ".tex")
        else:
            regular(info, source)
        for child, is_dir in children:
            member = source / child
            replica = destination / rel / child if destination is not None else None
            if is_dir:
                if replica is not None:
                    replica.mkdir(parents=True, exist_ok=True)
                evidence[str(member)] = "directory"
            else:
                if replica is not None and not replica.exists():
                    copy_file(member, replica, exclusive=True)
                evidence[str(member)] = sha(member if replica is None else replica)
    return evidence


def publish_build(temporary: Path, target: Path, replacements: dict[Path, Path],
                  *, compiled: bool) -> None:
    """Publish generated files only; source files and previous successful renders survive failures."""
    if not temporary.is_dir():
        return
    for relative, is_dir in entries(temporary):
        if (is_dir or relative.name.startswith(".")
                or relative.as_posix() in {"production/acceptance.json", "production/qa.json",
                                           "production/review-template.json"}):
            continue
        if not compiled and not (relative.parent == Path("production") and relative.suffix == ".log"):
            continue
        if relative.suffix in {".fls", ".log"}:
            with read_file(temporary / relative) as stream:
                content = translated(stream.read(), replacements)
            atomic_file(target / relative, lambda output: output.write(content))
        else:
            copy_file(temporary / relative, target / relative)
    if compiled:
        for folder, pattern in (("paginas", r"pag-\d+\.png"), ("production", r"contact-\d+\.png")):
            generated = {p.name for p in (temporary / folder).glob("*.png") if re.fullmatch(pattern, p.name)}
            if generated:
                with directory(target / folder) as parent:
                    for name in os.listdir(parent):
                        if re.fullmatch(pattern, name) and name not in generated:
                            regular(os.stat(name, dir_fd=parent, follow_symlinks=False), target / folder / name)
                            os.unlink(name, dir_fd=parent)


def audit(target: Path, system: Path) -> tuple[Path, dict[str, Any]]:
    """Build in private scratch space, then export verified outputs to the selected course."""
    target = physical(target)
    anchor = course_anchor(target)
    list(entries(target, owner_anchor=anchor))
    boundary = CourseBoundary(anchor)
    boundary.check_path(target)
    with trusted_engine(physical(system)) as engine:
        return _audit(target, engine, boundary)


def _audit(target: Path, engine: Any, boundary: CourseBoundary) -> tuple[Path, dict[str, Any]]:
    system = engine.source
    list(entries(system))
    videos, _ = discover(target)
    output = target / "build/production"
    initial_context = course_context(target, engine.path, boundary=boundary)
    with scope_locked(target, videos, boundary):
        roots = [target, *videos, *(p / "build" for p in [target, *videos]),
                 *(p / "build/production" for p in [target, *videos])]
        pinned = {p: directory_identity(p) for p in roots}

        def verify_destination() -> None:
            if any(directory_identity(p) != identity for p, identity in pinned.items()):
                raise ProductionError("Course or output directory changed during the build")
            boundary.check_tree(target)

        verify_destination()
        attempt = secrets.token_hex(16)
        write_json(output / "acceptance.json", {"attempt": attempt, "artifacts_reviewed": False, "recording_ready": False,
                                               "reason": "A new audit requires a new review"})
        before = sources(target, system)
        real_course = course_root(target)
        # The authenticated engine already owns this private scratch parent.
        with tempfile.TemporaryDirectory(prefix="audit-", dir=engine.path.parent) as tmp:
            workspace = physical(Path(tmp))
            scratch_course = workspace / "course"
            relative = target.relative_to(real_course) if real_course is not None else Path(target.parent.name) / target.name
            replica = scratch_course / relative
            replica.parent.mkdir(parents=True)
            cache, temp, home = (workspace / part for part in ("tex-cache", "tmp", "home"))
            for folder in (cache, temp, home):
                folder.mkdir(mode=0o700)
            env = tool_env(HOME=str(home), TMPDIR=str(temp), TEXMFCACHE=str(cache), TEXMFVAR=str(cache),
                           BRAINTEASERS_ROOT=str(scratch_course))
            context = course_context(target, engine.path, scratch_course, boundary=boundary)
            if context != initial_context:
                raise ProductionError("Selected teaching sources changed before compilation")
            copy_sources(target, replica)
            copied = {str(target / p.relative_to(replica)): sha(p) for p in source_files(replica)}
            if copied != {p: digest for p, digest in before.items() if Path(p).is_relative_to(target)}:
                raise ProductionError("The isolated input copy differs from the selected course sources")
            replacements = {system: engine.path, target: replica}
            if real_course is not None:
                replacements[real_course] = scratch_course
            translate_sources(replica, replacements)
            report = _compile_copy(replica, engine.path, env)
            verify_destination()
            if sources(target, system) != before or course_context(target, engine.path, boundary=boundary) != context:
                raise ProductionError("Course or engine inputs changed during the audit; rerun on stable sources")
            results = {Path(v["path"]): v for v in report["videos"]}
            for p in dict.fromkeys([target, *videos]):
                work = replica / p.relative_to(target)
                result = results.get(work)
                compiled = result is None or (result["build_exit"] == 0 and result.get("render_exit") == 0)
                boundary.check_tree(p / "build")
                publish_build(work / "build", p / "build", {value: key for key, value in replacements.items()},
                              compiled=compiled)
            report["target"] = str(target)
            report["system"] = str(system)
            report["engine_sha256"] = engine.digest
            report["attempt"] = attempt
            report["course_inputs"] = context
            report["course_owner"] = boundary.claim()
            for video in report["videos"]:
                video["path"] = str(target / Path(video["path"]).relative_to(replica))
            for page in report["pages"]:
                page["png"] = str(target / Path(page["png"]).relative_to(replica))
            report["contact_sheets"] = [str(target / Path(p).relative_to(replica))
                                        for p in report["contact_sheets"]]
        verify_destination()
        report["inventory"] = inventory(target, system, videos, context)
        report["audit_fingerprint"] = fingerprint(report)
        qa = output / "qa.json"
        write_json(qa, report)
        write_json(output / "review-template.json", {
            "audit_fingerprint": report["audit_fingerprint"],
            "pages": {p["id"]: "" for p in report["pages"]},
            "checks": dict.fromkeys(REVIEW_CHECKS, ""), "unresolved": [],
            "oral_rehearsal": {v.name: {"confirmed": False, "evidence": ""} for v in videos}})
        return qa, report


def evidence(value: Any) -> bool:
    return isinstance(value, str) and len(value.strip()) >= 24


def validate_review(report: dict[str, Any], review: dict[str, Any], current: dict[str, str]) -> dict[str, bool]:
    if report["audit_fingerprint"] != fingerprint(report) or review.get("audit_fingerprint") != report["audit_fingerprint"]:
        raise ProductionError("Review does not match the audit fingerprint")
    if current != report["inventory"]:
        raise ProductionError("Sources, dependencies or artifacts changed; audit and review again")
    if not report["mechanical_passed"]:
        raise ProductionError("Resolve mechanical errors before accepting artifacts")
    pages = review.get("pages", {})
    required = {p["id"] for p in report["pages"]}
    if not required or not isinstance(pages, dict) or set(pages) != required or not all(evidence(v) for v in pages.values()):
        raise ProductionError("Every physical page requires its own concrete review observation")
    checks = review.get("checks", {})
    if not isinstance(checks, dict):
        raise ProductionError("Review checks must contain concrete evidence for each required dimension")
    missing = [key for key in REVIEW_CHECKS if not evidence(checks.get(key))]
    if missing:
        raise ProductionError("Missing or insufficient review evidence: " + ", ".join(missing))
    if review.get("unresolved") != []:
        raise ProductionError("Unresolved observations prevent acceptance")
    oral = review.get("oral_rehearsal", {})
    rehearsed = all(isinstance(oral.get(Path(v["path"]).name), dict)
                    and oral[Path(v["path"]).name].get("confirmed") is True
                    and evidence(oral[Path(v["path"]).name].get("evidence")) for v in report["videos"]) if isinstance(oral, dict) else False
    return {"artifacts_reviewed": True,
            "recording_ready": bool(report["complete_session"] and report["legacy_passed"] and rehearsed)}


def accept(path: Path, review_path: Path) -> dict[str, Any]:
    path = physical(path)
    if path.parts[-3:] != ("build", "production", "qa.json"):
        raise ProductionError("Accept the current qa.json in its managed build/production directory")
    target = path.parents[2]
    anchor = course_anchor(target)
    list(entries(target, owner_anchor=anchor))
    boundary = CourseBoundary(anchor)
    boundary.check_path(target)
    videos, _ = discover(target)
    with read_file(path) as stream:
        report = json.load(stream)
    if Path(report["target"]) != target or report.get("course_owner") != boundary.claim():
        raise ProductionError("Audit belongs to a different course checkout; audit this owner again")
    system = physical(Path(report["system"]))
    with trusted_engine(system) as engine:
        if report.get("engine_sha256", engine.digest) != engine.digest:
            raise ProductionError("The reviewed course engine has changed")
        context = course_context(target, engine.path, boundary=boundary)
        if context != report.get("course_inputs", {}):
            raise ProductionError("The teaching validator's course inputs have changed")
        with scope_locked(target, videos, boundary):
            with read_file(path) as stream:
                if json.load(stream) != report:
                    raise ProductionError("Audit changed before review; select current evidence")
            with read_file(path.parent / "acceptance.json") as stream:
                previous = json.load(stream)
            if previous.get("attempt") != report.get("attempt"):
                raise ProductionError("A newer audit started; review its complete evidence")
            with read_file(review_path) as stream:
                review = json.load(stream)
            status = validate_review(report, review, inventory(target, system, videos, context))
            boundary.check_tree(target)
            result = {**status, "attempt": report.get("attempt"),
                      "audit_fingerprint": report["audit_fingerprint"], "review": review}
            write_json(path.parent / "acceptance.json", result)
            return result


def session_directory(plan: dict[str, Any], output: Path) -> Path:
    session = plan.get("session")
    if type(session) is not int or not 1 <= session <= 99 or not plan.get("videos"):
        raise ProductionError("Plan requires session 1–99 and videos")
    return output / f"sesion-{session:02d}"


def validate_plan(plan: dict[str, Any], output: Path, *, retry: bool = False) -> list[tuple[Path, dict[str, Any]]]:
    folder = session_directory(plan, output)
    prepared: list[tuple[Path, dict[str, Any]]] = []
    seen: set[int] = set()
    for video in plan["videos"]:
        number, slug = video.get("number"), video.get("slug", "")
        title, seconds = video.get("title", ""), video.get("seconds")
        if type(number) is not int or not 1 <= number <= 99 or number in seen:
            raise ProductionError("Video numbers must be distinct integers from 1 to 99")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ProductionError("Slug must contain lowercase ASCII words separated by hyphens")
        if not isinstance(title, str) or not title.strip() or re.search(r"[|&\\\n\r%{}$#_^~]", title):
            raise ProductionError("Use a plain title without TeX or sed replacement metacharacters")
        if type(seconds) is not int or seconds <= 0:
            raise ProductionError("Each video requires positive integer seconds")
        target = folder / f"video-{number:02d}-{slug}"
        collisions = set(folder.glob(f"video-{number:02d}-*"))
        if collisions and not (retry and collisions == {target}):
            raise ProductionError(f"Video {number:02d} already exists; no overwrite")
        prepared.append((target, video))
        seen.add(number)
    errors = session_duration([v["seconds"] for _, v in prepared])
    if errors:
        raise ProductionError(errors[0])
    return prepared


def _scaffold(plan: dict[str, Any], output: Path, system: Path) -> list[Path]:
    """Run the trusted scaffolder only against a fresh, private output tree."""
    if re.search(r"[|&\\\n\r]", str(system)):
        raise ProductionError("System path contains characters unsupported by the shared scaffolder")
    prepared = validate_plan(plan, output)
    created: list[Path] = []
    for path, video in prepared:
        result = subprocess.run(["bash", str(system / "scripts/nuevo_video.sh"), str(plan["session"]),
                                 str(video["number"]), video["slug"], str(video["seconds"]), video["title"]],
                                capture_output=True, text=True, cwd=output, timeout=240,
                                env=tool_env(ASINCRONAS_OUT=str(output)))
        if result.returncode:
            raise ProductionError(f"Scaffolding failed: {result.stdout}{result.stderr}")
        list(entries(output))
        # Keep the static-slide choice local; the shared template remains untouched.
        main = path / "presentacion/main.tex"
        with read_file(main) as stream:
            content = stream.read().decode()
        match = re.search(r"\\documentclass(?:\[([^\]]*)\])?\{beamer\}", content)
        if match is None:
            raise ProductionError(f"Scaffolded Beamer entry point not recognized: {main}")
        options = [o.strip() for o in (match[1] or "").split(",") if o.strip()]
        if "handout" not in options:
            options.append("handout")
        declaration = "\\documentclass[" + ",".join(options) + "]{beamer}"
        new = (content[:match.start()] + declaration + content[match.end():]).encode()
        atomic_file(main, lambda stream: stream.write(new))
        created.append(path)
    return created


def initialize(plan_path: Path, output: Path, system: Path) -> list[str]:
    with trusted_engine(physical(system)) as engine:
        return _initialize(plan_path, physical(output), engine)


def copy_owned_tree(source: int, destination: int, *, sources_only: bool = False) -> None:
    """Copy a validated, newly generated tree without resolving destination directories by name."""
    for name in sorted(os.listdir(source)):
        if sources_only and (name in {"build", "__pycache__"} or name.startswith(".")):
            continue
        info = os.stat(name, dir_fd=source, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            os.mkdir(name, 0o700, dir_fd=destination)
            with ExitStack() as stack:
                inputs = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source)
                stack.callback(os.close, inputs)
                if not os.path.samestat(info, os.fstat(inputs)):
                    raise ProductionError("Directory changed during copy")
                outputs = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=destination)
                stack.callback(os.close, outputs)
                copy_owned_tree(inputs, outputs, sources_only=sources_only)
        else:
            regular(info, Path(name))
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=source)
            with os.fdopen(fd, "rb") as inp:
                regular(os.fstat(fd), Path(name))
                if not os.path.samestat(info, os.fstat(fd)):
                    raise ProductionError("Generated source changed during export")
                new_fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=destination)
                with os.fdopen(new_fd, "wb") as out:
                    shutil.copyfileobj(inp, out)
                    out.flush()
                    os.fchmod(new_fd, stat.S_IMODE(info.st_mode) & 0o777)
                    os.fsync(new_fd)
    os.fsync(destination)


def promote_tree(source: Path, parent: int, target: str) -> None:
    """Reserve an unpublished sibling, populate it and reveal the entire directory exclusively."""
    stage = ".production-stage-" + secrets.token_hex(24)
    os.mkdir(stage, 0o700, dir_fd=parent)
    try:
        scratch = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            with directory(source) as inp:
                copy_owned_tree(inp, scratch)
            platform().promote_directory_at(parent, stage, parent, target)
        finally:
            os.close(scratch)
        os.fsync(parent)
    except OSError as exc:
        raise ProductionError(f"Cannot finish {target}; inspect unpublished staging name {stage}: {exc}") from exc


def tree_signature(root: Path) -> dict[Path, str | None]:
    return {rel: None if is_dir else sha(root / rel) for rel, is_dir in entries(root)}


def _initialize(plan_path: Path, output: Path, engine: Any) -> list[str]:
    if any(c in r"\{}%#$&^~|" or ord(c) < 32 for c in str(engine.source)):
        raise ProductionError("The course engine path cannot be represented safely in generated TeX")
    with read_file(plan_path) as stream:
        plan = json.load(stream)
    session = session_directory(plan, output)
    anchor = output.parent if output.name == "asincronas" else output
    if os.path.lexists(session):
        list(entries(session, owner_anchor=anchor))
    boundary = CourseBoundary(anchor)
    boundary.check_path(output)
    boundary.check_path(session)
    validate_plan(plan, output, retry=True)
    with directory(output) as parent, platform().file_lock(parent):
        info = os.fstat(parent)
        original = (info.st_dev, info.st_ino)
        # lexists distinguishes an absent session from a dangling symlink.
        session_identity = None
        if os.path.lexists(session):
            session_identity = directory_identity(session)
            boundary.check_tree(session)
        with tempfile.TemporaryDirectory(prefix="init-", dir=engine.path.parent) as tmp:
            staging = physical(Path(tmp))
            created = _scaffold(plan, staging, engine.path)
            translate_sources(staging, {engine.path: engine.source})
            source = created[0].parent
            permitted = {"README.md", *(p.name for p in created)}
            if set(os.listdir(source)) - permitted:
                raise ProductionError("Scaffolder generated an undeclared session entry")
            if directory_identity(output) != original:
                raise ProductionError("Output root changed during scaffolding")
            boundary.check_path(session)
            if session_identity is None:
                promote_tree(source, parent, session.name)
            else:
                with directory(session) as session_fd:
                    observed = os.fstat(session_fd)
                    if (observed.st_dev, observed.st_ino) != session_identity:
                        raise ProductionError("Session changed during scaffolding")
                    boundary.check_tree(session)
                    validate_plan(plan, output, retry=True)
                    pending = []
                    for video in created:
                        target = session / video.name
                        if not os.path.lexists(target):
                            pending.append(video)
                        elif tree_signature(target) != tree_signature(video):
                            raise ProductionError(f"Existing video has different contents; preserved: {target}")
                    for video in pending:
                        boundary.check_path(session / video.name)
                        promote_tree(video, session_fd, video.name)
                    readme = source / "README.md"
                    if readme.is_file() and not os.path.lexists(session / readme.name):
                        boundary.check_path(session / readme.name)
                        copy_file(readme, session / readme.name, exclusive=True)
            return [str(session / p.name) for p in created]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Scaffold a complete session from a JSON plan; no content generation")
    init.add_argument("plan", type=Path)
    init.add_argument("--output", type=Path, required=True,
                      help="Existing output root; production uses the course asincronas directory")
    init.add_argument("--system", type=Path, required=True, help="Trusted course _sistema directory")
    aud = sub.add_parser("audit", help="Compile, render and audit a session or one video")
    aud.add_argument("target", type=Path)
    aud.add_argument("--system", type=Path, required=True, help="Trusted course _sistema directory")
    acc = sub.add_parser("accept", help="Validate evidence and freshness of an actual review")
    acc.add_argument("audit", type=Path)
    acc.add_argument("review", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "init":
            print(json.dumps({"created": initialize(args.plan, args.output, args.system)}, indent=2))
        elif args.command == "accept":
            result = accept(args.audit, args.review)
            print(json.dumps({k: v for k, v in result.items() if k != "review"}, indent=2))
        else:
            path, report = audit(args.target, args.system)
            print(json.dumps({"report": str(path), "verified_seconds": report["seconds"],
                              "declared_seconds": report["declared_seconds"],
                              "pages": len(report["pages"]), "mechanical_passed": report["mechanical_passed"],
                              "legacy_passed": report["legacy_passed"], "errors": report["errors"],
                              "warnings": len(report["warnings"])}, ensure_ascii=False, indent=2))
            return 0 if report["mechanical_passed"] and report["legacy_passed"] else 1
    except (ProductionError, OSError, ValueError, KeyError, ImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
