#!/usr/bin/env python3
"""
tex_to_md.py — LaTeX → Markdown pipeline for doc-forge.

Stages:
  1. Input resolution  — inline \\input{} / \\include{}
  2. Pre-processing    — strip comments, expand simple macros, normalize math
  2b. TikZ extraction  — compile tikzpicture blocks to PNG, replace with image links
  3. Pandoc            — latex → gfm+tex_math_dollars
  4. Post-processing   — clean pandoc artefacts
  5. Frontmatter       — generate OmarOS YAML from LaTeX metadata + path heuristics
"""
import dataclasses
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

VAULT_MARKER = Path("05_Projects/OmarOS/Architecture/OmarOS_Architecture.md")

# Minimal standalone preamble for compiling isolated tikzpicture blocks.
# Loads the most common tikz libraries to maximise compatibility.
_TIKZ_STANDALONE_PREAMBLE = r"""\documentclass[tikz,border=4pt]{standalone}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=newest}
\usetikzlibrary{
  arrows,arrows.meta,
  positioning,calc,
  shapes,shapes.geometric,shapes.multipart,shapes.symbols,
  fit,backgrounds,
  decorations,decorations.pathmorphing,decorations.markings,decorations.text,
  patterns,matrix,
  trees,graphs,
  3d,perspective,
}
\usepackage{amsmath,amssymb}
"""


# ---------------------------------------------------------------------------
# Vault routing heuristics
# ---------------------------------------------------------------------------
DOMAIN_MAP: list[tuple[str, str, str]] = [
    # path fragment          domain                   subdomain
    ("reflexiones_filosof",  "01_Daily_Life",         "Reflections/Philosophy"),
    ("ai_claude_code",       "07_AI_and_Agents",      "Reference/Claude_Code"),
    ("engie",                "03_Work",               "ENGIE"),
    ("mathematical_finance", "06_Knowledge_Base",     "Mathematics/Finance"),
    ("power_market",         "06_Knowledge_Base",     "Mathematics/Finance"),
    ("markov",               "06_Knowledge_Base",     "Mathematics/Stochastic_Processes"),
    ("stochastic",           "06_Knowledge_Base",     "Mathematics/Stochastic_Processes"),
    ("rough_paths",          "06_Knowledge_Base",     "Mathematics/Stochastic_Processes"),
    ("probability",          "06_Knowledge_Base",     "Mathematics/Probability"),
    ("analisis_funcional",   "06_Knowledge_Base",     "Mathematics/Functional_Analysis"),
    ("complex_analis",       "06_Knowledge_Base",     "Mathematics/Complex_Analysis"),
    ("topologia",            "06_Knowledge_Base",     "Mathematics/Topology"),
    ("teoria_medida",        "06_Knowledge_Base",     "Mathematics/Measure_Theory"),
    ("teoria_categor",       "06_Knowledge_Base",     "Mathematics/Category_Theory"),
    ("geometria_difer",      "06_Knowledge_Base",     "Mathematics/Differential_Geometry"),
    ("ecuaciones_dif",       "06_Knowledge_Base",     "Mathematics/ODEs_PDEs"),
    ("finite_elements",      "06_Knowledge_Base",     "Mathematics/Numerical_Methods"),
    ("optimis",              "06_Knowledge_Base",     "Mathematics/Optimisation"),
    ("calculo_multi",        "06_Knowledge_Base",     "Mathematics/Calculus"),
    ("calculo_uni",          "06_Knowledge_Base",     "Mathematics/Calculus"),
    ("algebra",              "06_Knowledge_Base",     "Mathematics/Algebra"),
    ("ecuaciones",           "06_Knowledge_Base",     "Mathematics/Algebra"),
    ("funciones",            "06_Knowledge_Base",     "Mathematics/Algebra"),
    ("representaciones",     "06_Knowledge_Base",     "Mathematics/Algebra"),
    ("conjuntos",            "06_Knowledge_Base",     "Mathematics/Logic_Set_Theory"),
    ("hesperides",           "06_Knowledge_Base",     "Mathematics/Combinatorics"),
    ("brainteaser",          "06_Knowledge_Base",     "Mathematics/Combinatorics"),
    ("ml",                   "06_Knowledge_Base",     "Computing/ML"),
    ("csharp",               "06_Knowledge_Base",     "Computing/CSharp"),
    ("git",                  "06_Knowledge_Base",     "Computing/Git"),
    ("informatica",          "06_Knowledge_Base",     "Computing"),
    ("scientific_comp",      "06_Knowledge_Base",     "Computing/Scientific"),
    ("computational_math",   "06_Knowledge_Base",     "Computing/Scientific"),
    ("fisica_apuntes",       "06_Knowledge_Base",     "Physics"),
    ("construccion_fisica",  "06_Knowledge_Base",     "Physics"),
]


# ---------------------------------------------------------------------------
# Post-processing helpers (module-level so they can be reused by callers)
# ---------------------------------------------------------------------------

def _expand_one_arg_macro(content: str, cmd: str, template: str) -> str:
    """Expand \\cmd{arg} → template with #1 replaced by arg (balanced-brace aware)."""
    parts: list[str] = []
    i = 0
    pattern = re.compile(rf"\\{re.escape(cmd)}(?!\w)\{{")
    while True:
        m = pattern.search(content, i)
        if not m:
            parts.append(content[i:])
            break
        parts.append(content[i : m.start()])
        j = m.end() - 1  # index of the opening {
        depth = 0
        k = j
        while k < len(content):
            if content[k] == "{":
                depth += 1
            elif content[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        arg = content[j + 1 : k]
        parts.append(template.replace("#1", arg))
        i = k + 1
    return "".join(parts)


def _divs_to_callouts(content: str) -> str:
    """Convert <div class="X">...</div> blocks to Obsidian > [!X] callouts.

    Also handles divs that appear inside existing callout lines (> <div ...>).
    """
    def _to_callout(m: re.Match) -> str:
        cls = m.group(1)
        inner = m.group(2).strip()
        lines = inner.splitlines()
        prefixed = []
        for line in lines:
            if line.strip():
                prefixed.append(f"> {line}")
            else:
                prefixed.append(">")
        return f"> [!{cls}]\n" + "\n".join(prefixed)

    # Standard top-level divs
    content = re.sub(
        r'<div class="([^"]+)">\s*(.*?)\s*</div>',
        _to_callout,
        content,
        flags=re.DOTALL,
    )
    # Divs that appear inside callout lines (prefixed with "> ")
    content = re.sub(
        r'^(>\s*)<div class="([^"]+)">',
        lambda m: f'{m.group(1)}[!{m.group(2)}]',
        content,
        flags=re.MULTILINE,
    )
    # Orphan closing tags (bare </div> or > </div>)
    content = re.sub(r'^>\s*</div>\s*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*</div>\s*$', '', content, flags=re.MULTILINE)
    return content


def _fix_dead_latex_refs(content: str) -> str:
    """Replace <a href="#sec:...">...</a> Pandoc artifacts with readable italic text."""
    def _replace(m: re.Match) -> str:
        ref_id = m.group(1)
        name = re.sub(r"^sec:", "", ref_id).replace("_", " ")
        return f"*(→ {name})*"

    return re.sub(r'<a\s+href="#([^"]*)"[^>]*>\[[^\]]*\]</a>', _replace, content)


def infer_domain(filepath: Path, content: str) -> dict:
    path_lower = str(filepath).lower().replace(" ", "_").replace("-", "_")
    for fragment, domain, subdomain in DOMAIN_MAP:
        if fragment in path_lower:
            return {"domain": domain, "subdomain": subdomain}
    # Content-based fallback: if theorem-like envs exist → math KB
    if re.search(r"\\begin\{(theorem|lemma|proof|definition|proposition|corollary)\}", content):
        return {"domain": "06_Knowledge_Base", "subdomain": "Mathematics"}
    return {"domain": "06_Knowledge_Base", "subdomain": "General"}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
@dataclasses.dataclass
class RunLog:
    source: str = ""
    stages: list[dict] = dataclasses.field(default_factory=list)
    route: dict = dataclasses.field(default_factory=dict)
    compile: dict = dataclasses.field(default_factory=dict)

    def add(self, stage: str, **kw):
        self.stages.append({"stage": stage, **kw})

    def save(self, path: Path):
        path.write_text(json.dumps(dataclasses.asdict(self), indent=2, ensure_ascii=False))


class TexToMdPipeline:
    def __init__(
        self,
        src: Path,
        out: Path,
        *,
        resolve_inputs: bool = True,
        frontmatter: bool = True,
        keep_intermediate: bool = False,
        dry_run: bool = False,
        log_path: Path | None = None,
        base_dir: Path | None = None,
        route_only: bool = False,
    ):
        self.src = src.resolve()
        self.output_lookup = out.absolute()
        self.out = out.resolve()
        self.resolve_inputs = resolve_inputs
        self.frontmatter = frontmatter
        self.keep_intermediate = keep_intermediate
        self.dry_run = dry_run
        self.log_path = log_path
        self.base_dir = base_dir or self.src.parent
        self.route_only = route_only
        self.log = RunLog(source=str(self.src))

    # ------------------------------------------------------------------
    # Stage 1: input resolution
    # ------------------------------------------------------------------
    def _resolve(self, content: str, base: Path, depth: int = 0) -> str:
        if depth > 10:
            return content  # guard against circular includes
        def replace_input(m):
            rel = m.group(1).strip()
            if not rel.endswith(".tex"):
                rel += ".tex"
            candidate = base / rel
            if candidate.exists():
                child = candidate.read_text(encoding="utf-8", errors="replace")
                if self.resolve_inputs:
                    child = self._resolve(child, candidate.parent, depth + 1)
                return child
            return m.group(0)  # leave unchanged if not found
        content = re.sub(r"\\(?:input|include)\{([^}]+)\}", replace_input, content)
        return content

    # ------------------------------------------------------------------
    # Stage 2: pre-processing
    # ------------------------------------------------------------------
    def _preprocess(self, content: str) -> str:
        # Strip line comments (not inside math)
        content = re.sub(r"(?<!\\)%[^\n]*", "", content)

        # Strip spacing args from \\ line-breaks: \\[6pt] → \\ (must run before \[ → $$)
        content = re.sub(r"\\\\(\[[\d.]+[a-zA-Z]*\])", r"\\\\", content)

        # Normalize \[ ... \] → $$ ... $$ (negative lookbehind skips \\[)
        content = re.sub(r"(?<!\\)\\\[", r"$$", content)
        content = re.sub(r"(?<!\\)\\\]", r"$$", content)

        # Extract 0-arg and 1-arg \newcommand definitions BEFORE stripping them.
        # 0-arg: \newcommand{\cmd}{body}
        # 1-arg: \newcommand{\cmd}[1]{body}  — body may contain one level of nested braces
        simple_macros: dict[str, str] = {}
        for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", content):
            simple_macros[m.group(1)] = m.group(2)

        one_arg_macros: dict[str, str] = {}
        for m in re.finditer(
            r"\\(?:re)?newcommand\*?\{\\(\w+)\}\[1\]\{((?:[^{}]|\{[^{}]*\})*)\}",
            content,
        ):
            one_arg_macros[m.group(1)] = m.group(2)

        # Strip ALL \newcommand / \renewcommand lines (simple and complex).
        content = re.sub(r"\\(?:re)?newcommand\*?\{[^}]*\}[^\n]*\n?", "", content)

        # Strip TeX primitives that pandoc's LaTeX reader can't handle.
        content = re.sub(r"\\def\\[a-zA-Z@]+[^\n]*\n?", "", content)
        content = re.sub(r"\\let\\[a-zA-Z@]+[^\n]*\n?", "", content)

        # Apply 0-arg macro expansions.
        for cmd, expansion in simple_macros.items():
            content = re.sub(rf"\\{cmd}(?!\w)", lambda _m, e=expansion: e, content)

        # Apply 1-arg macro expansions (balanced-brace argument matching).
        for cmd, template in one_arg_macros.items():
            content = _expand_one_arg_macro(content, cmd, template)

        return content

    # ------------------------------------------------------------------
    # Stage 2b: TikZ → PNG
    # ------------------------------------------------------------------
    def _extract_tikz_blocks(self, content: str) -> tuple[str, list[str]]:
        """Replace every tikzpicture block with a TIKZ_N marker; return (modified, blocks)."""
        blocks: list[str] = []

        def _replace(m: re.Match) -> str:
            blocks.append(m.group(0))
            return f"TIKZBLOCK{len(blocks) - 1}END"

        modified = re.sub(
            r"\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}",
            _replace,
            content,
            flags=re.DOTALL,
        )
        return modified, blocks

    def _user_macros_from_raw(self, raw: str) -> str:
        """Extract newcommand/renewcommand/def lines from raw source for tikz preamble."""
        lines = []
        for m in re.finditer(r"\\(?:re)?newcommand\*?\{\\[a-zA-Z]+\}\{[^}]*\}", raw):
            lines.append(m.group(0))
        return "\n".join(lines)

    @staticmethod
    def _plain_attachment_path(path: Path, *, directory: bool, allow_missing: bool = False) -> bool:
        """Check a local path without accepting links or Windows reparse points.

        Args:
            path: Absolute path retaining the spelling supplied by the caller.
            directory: Whether the leaf must be a directory or a regular file.
            allow_missing: Permit a path below an existing plain directory.

        Returns:
            Whether the existing components satisfy the attachment policy.
        """
        if not path.is_absolute() or ".." in path.parts:
            return False
        if os.name == "nt":
            if not re.fullmatch(r"[A-Za-z]:", path.drive):
                return False
            if any(":" in part or part.endswith((" ", ".")) for part in path.parts[1:]):
                return False
        for component in (*reversed(path.parents), path):
            try:
                metadata = component.lstat()
            except FileNotFoundError:
                return allow_missing
            except OSError:
                return False
            attributes = getattr(metadata, "st_file_attributes", 0)
            if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                return False
            if component != path or directory:
                if not stat.S_ISDIR(metadata.st_mode):
                    return False
            elif not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                return False
        return True

    def _tikz_vault(self) -> Path | None:
        """Select the explicit vault or the nearest marked output ancestor."""
        configured = os.environ.get("OMAROS_VAULT_ROOT")
        if configured is not None:
            vault = Path(configured)
            if not self._plain_attachment_path(vault / VAULT_MARKER, directory=False):
                print(
                    "[doc-forge] Invalid OMAROS_VAULT_ROOT. Keeping TikZ as LaTeX.",
                    file=sys.stderr,
                )
                return None
            candidates = (vault,)
        else:
            candidates = self.output_lookup.parents

        if not self._plain_attachment_path(self.output_lookup, directory=False, allow_missing=True):
            return None
        for vault in candidates:
            if (self.output_lookup.is_relative_to(vault)
                    and self._plain_attachment_path(vault / VAULT_MARKER, directory=False)):
                return vault
        return None

    def _program(self, name: str) -> str:
        """Select an explicit executable on Windows, where bare names search cwd."""
        if os.name != "nt":
            return name

        work_directories = (Path.cwd().resolve(), self.src.parent, self.out.parent)
        worktrees = {
            parent
            for directory in work_directories
            for parent in (directory, *directory.parents)
            if (parent / ".git").exists()
        }
        for entry in os.get_exec_path():
            directory = Path(entry.strip('"'))
            if not directory.is_absolute():
                continue
            try:
                directory = directory.resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if directory in work_directories or any(
                    directory.is_relative_to(root) for root in worktrees):
                continue
            candidate = directory / (name + ".exe")
            if self._plain_attachment_path(candidate, directory=False):
                return str(candidate)
        raise FileNotFoundError(f"{name}.exe was not found in an absolute tools directory on PATH")

    def _matches_tikz(self, existing: Path, rendered: Path) -> bool:
        """Reuse an unchanged regular image only if its bytes match this render."""
        if not self._plain_attachment_path(existing, directory=False):
            return False
        before = existing.lstat()
        if before.st_size != rendered.stat().st_size:
            return False
        flags = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                 | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0))
        with os.fdopen(os.open(existing, flags), "rb") as previous, rendered.open("rb") as current:
            opened = os.fstat(previous.fileno())
            if (not os.path.samestat(before, opened) or not stat.S_ISREG(opened.st_mode)
                    or opened.st_nlink != 1):
                return False
            while chunk := current.read(64 * 1024):
                if previous.read(len(chunk)) != chunk:
                    return False
            if previous.read(1):
                return False
        after = existing.lstat()
        return (
            os.path.samestat(before, after)
            and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            and self._plain_attachment_path(existing, directory=False)
        )

    def _publish_tikz(self, candidate: Path, out_png: Path, vault: Path) -> None:
        """Stage a rendered image beside its destination and publish without replacement."""
        directory = out_png.parent
        if not self._plain_attachment_path(directory, directory=True, allow_missing=True):
            raise ValueError("TikZ attachment directory has a linked or invalid component")
        directory.mkdir(parents=True, exist_ok=True)
        if not self._plain_attachment_path(directory, directory=True):
            raise ValueError("TikZ attachment directory changed before staging")
        if self._tikz_vault() != vault:
            raise ValueError("TikZ output no longer identifies the selected vault")

        with tempfile.TemporaryDirectory(prefix=".doc-forge-", dir=directory) as stage:
            staged = Path(stage) / out_png.name
            shutil.copyfile(candidate, staged)
            if not self._plain_attachment_path(staged, directory=False):
                raise ValueError("TikZ staging path changed before publication")
            # A hard link publishes the complete file or fails if any destination
            # entry already exists, including a broken symlink or existing figure.
            try:
                os.link(staged, out_png)
            except FileExistsError:
                if not self._matches_tikz(out_png, staged):
                    raise

    def _compile_tikz(self, block: str, index: int, user_macros: str, vault: Path) -> Path | None:
        """Compile one TikZ block into a vault attachment, or keep its source on failure."""
        att_dir = vault / "90_Attachments" / "tikz" / self.src.stem
        out_png = att_dir / f"fig_{index:02d}.png"
        if not self._plain_attachment_path(att_dir, directory=True, allow_missing=True):
            return None
        if not self._plain_attachment_path(out_png, directory=False, allow_missing=True):
            return None

        doc = _TIKZ_STANDALONE_PREAMBLE
        if user_macros.strip():
            doc += user_macros + "\n"
        doc += "\\begin{document}\n" + block + "\n\\end{document}\n"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                scratch = Path(tmpdir).resolve()
                tex = scratch / "fig.tex"
                tex.write_text(doc, encoding="utf-8")
                latex = subprocess.run(
                    [self._program("lualatex"), "--no-shell-escape", "--interaction=nonstopmode",
                     "--output-directory", tmpdir, str(tex)],
                    capture_output=True, cwd=tmpdir, timeout=60,
                )
                pdf = scratch / "fig.pdf"
                if latex.returncode or not pdf.is_file():
                    return None

                poppler = subprocess.run(
                    [self._program("pdftoppm"), "-r", "200", "-png", "-singlefile",
                     str(pdf), str(scratch / "fig")],
                    capture_output=True, cwd=tmpdir, timeout=30,
                )
                if poppler.returncode:
                    return None
                candidate = scratch / "fig.png"
                if not self._plain_attachment_path(candidate, directory=False):
                    candidate = scratch / "fig-1.png"
                if not self._plain_attachment_path(candidate, directory=False):
                    return None

                self._publish_tikz(candidate, out_png, vault)
                return out_png
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return None

    def _render_tikz(self, blocks: list[str], raw: str) -> dict[str, str]:
        """Render attachments for converted Markdown, retaining unrendered LaTeX."""
        if not blocks:
            return {}

        vault = self._tikz_vault()
        user_macros = self._user_macros_from_raw(raw) if vault is not None else ""
        self.log.add("tikz_found", count=len(blocks))
        replacements: dict[str, str] = {}

        for i, block in enumerate(blocks):
            marker = f"TIKZBLOCK{i}END"
            if vault is not None:
                png = self._compile_tikz(block, i, user_macros, vault)
                if png is not None:
                    rel = png.relative_to(vault)
                    replacements[marker] = f"![[{rel.as_posix()}]]"
                    self.log.add(f"tikz_{i}", status="compiled", path=str(rel))
                    continue
            replacements[marker] = "```latex\n" + block + "\n```"
            self.log.add(f"tikz_{i}", status="fallback_code_block")

        return replacements

    # ------------------------------------------------------------------
    # Stage 3: pandoc
    # ------------------------------------------------------------------
    def _pandoc(self, content: str) -> str:
        cmd = [
            self._program("pandoc"),
            "-f", "latex",
            "-t", "gfm+tex_math_dollars-tex_math_gfm",
            "--wrap=none",
        ]
        r = subprocess.run(cmd, input=content, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            print(f"[doc-forge] pandoc stderr:\n{r.stderr}", file=sys.stderr)
            raise RuntimeError(f"pandoc exited {r.returncode}")
        self.log.compile = {"success": True, "returncode": 0, "stderr_tail": r.stderr[-500:]}
        return r.stdout

    # ------------------------------------------------------------------
    # Stage 4: post-processing
    # ------------------------------------------------------------------
    def _postprocess(self, content: str) -> str:
        # Remove pandoc :::div artefacts
        content = re.sub(r"^:::\s*\{[^}]*\}\s*$", "", content, flags=re.MULTILINE)
        content = re.sub(r"^:::\s*$", "", content, flags=re.MULTILINE)

        # Convert <div class="X">...</div> → Obsidian > [!X] callouts
        content = _divs_to_callouts(content)

        # Fix dead LaTeX cross-reference anchors (<a href="#sec:...">...</a>)
        content = _fix_dead_latex_refs(content)

        # Remove \hypertarget artefacts
        content = re.sub(r"\\hypertarget\{[^}]*\}\{[^}]*\}", "", content)
        content = re.sub(r"\{#[a-zA-Z0-9_-]+\}", "", content)

        # Fix escaped underscores inside $...$ math (pandoc over-escapes)
        def fix_math_underscores(m):
            return m.group(0).replace(r"\_", "_")
        content = re.sub(r"\$[^$\n]+\$", fix_math_underscores, content)
        content = re.sub(r"\$\$[\s\S]*?\$\$", fix_math_underscores, content)

        # Collapse 3+ blank lines → 2
        content = re.sub(r"\n{4,}", "\n\n\n", content)

        # Strip trailing whitespace per line
        content = "\n".join(line.rstrip() for line in content.splitlines())

        return content.strip() + "\n"

    # ------------------------------------------------------------------
    # Stage 5: frontmatter
    # ------------------------------------------------------------------
    def _extract_latex_meta(self, content: str) -> dict:
        meta: dict = {}
        m = re.search(r"\\title\{([^}]+)\}", content)
        if m:
            meta["title"] = m.group(1).strip()
        m = re.search(r"\\author\{([^}]+)\}", content)
        if m:
            meta["author"] = m.group(1).strip()
        # Derive title from first \chapter or filename
        if "title" not in meta:
            m = re.search(r"\\chapter\{([^}]+)\}", content)
            if m:
                meta["title"] = m.group(1).strip()
            else:
                meta["title"] = self.src.stem.replace("_", " ").title()
        return meta

    def _build_frontmatter(self, raw_tex: str, slug: str) -> str:
        meta = self._extract_latex_meta(raw_tex)
        route = infer_domain(self.src, raw_tex)
        self.log.route = route

        today = date.today().isoformat()
        fm = {
            "title": meta.get("title", slug),
            "note_type": "knowledge_note",
            "domain": route["domain"],
            "subdomain": route["subdomain"],
            "tags": [],
            "status": "active",
            "created": today,
            "updated": today,
            "priority": "medium",
            "confidence": "high",
            "author": meta.get("author", "Omar"),
            "ai_generated": True,
            "ai_reviewed": False,
            "source": str(self.src),
            "latex_pending": False,
        }

        lines = ["---"]
        for k, v in fm.items():
            if isinstance(v, bool):
                lines.append(f"{k}: {'true' if v else 'false'}")
            elif isinstance(v, list):
                lines.append(f"{k}: []")
            else:
                quoted = json.dumps(str(v), ensure_ascii=False)
                # YAML treats these characters as controls or line separators.
                quoted = re.sub(
                    r"[\x7f-\x9f\u2028\u2029]",
                    lambda char: f"\\u{ord(char[0]):04x}",
                    quoted,
                )
                lines.append(f"{k}: {quoted}")
        lines.append("---")
        return "\n".join(lines) + "\n\n"

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------
    def run(self) -> None:
        # Read source
        raw = self.src.read_text(encoding="utf-8", errors="replace")
        self.log.add("read", chars=len(raw), lines=raw.count("\n"))

        # Route-only shortcut
        if self.route_only:
            route = infer_domain(self.src, raw)
            slug = self.src.stem + ".md"
            suggestion = f"{route['domain']}/{route['subdomain']}/{slug}"
            print(f"→ Vault route: {suggestion}")
            return

        # Stage 1
        if self.resolve_inputs:
            resolved = self._resolve(raw, self.base_dir)
            n_resolved = resolved.count("\n") - raw.count("\n")
            self.log.add("resolve_inputs", lines_added=max(0, n_resolved))
        else:
            resolved = raw

        # Stage 2
        preprocessed = self._preprocess(resolved)
        self.log.add("preprocess", ok=True)

        if self.dry_run:
            print(f"[dry-run] would convert {self.src} → {self.out}")
            route = infer_domain(self.src, raw)
            print(f"[dry-run] vault route: {route['domain']}/{route['subdomain']}/{self.out.name}")
            return

        # Keep the source blocks until Pandoc has successfully converted the document.
        preprocessed, tikz_blocks = self._extract_tikz_blocks(preprocessed)

        # Stage 3
        try:
            converted = self._pandoc(preprocessed)
        except (RuntimeError, OSError) as e:
            print(f"[doc-forge] ✗ {self.src.name}: {e}", file=sys.stderr)
            self.log.compile = {"success": False, "error": str(e)}
            if self.log_path:
                self.log.save(self.log_path)
            sys.exit(1)

        self.log.add("pandoc", chars=len(converted))

        # Stage 4
        final_md = self._postprocess(converted)

        # Publish figures only after Pandoc and postprocessing have succeeded.
        for marker, replacement in self._render_tikz(tikz_blocks, raw).items():
            final_md = final_md.replace(marker, "\n\n" + replacement + "\n\n")

        self.log.add("postprocess", ok=True)

        # Stage 5
        if self.frontmatter:
            fm = self._build_frontmatter(raw, self.out.stem)
            final_md = fm + final_md

        # Write
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.out.write_text(final_md, encoding="utf-8")

        # Vault routing hint
        route = self.log.route or infer_domain(self.src, raw)
        suggestion = f"{route.get('domain','?')}/{route.get('subdomain','?')}/{self.out.name}"
        print(f"[doc-forge] ✓ {self.out}")
        print(f"  → Vault route: {suggestion}")

        if self.log_path:
            self.log.save(self.log_path)
