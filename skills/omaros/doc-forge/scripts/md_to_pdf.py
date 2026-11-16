#!/usr/bin/env python3
"""
md_to_pdf.py — Markdown → PDF pipeline for doc-forge.
Improves on the md-to-pdf skill with themes, TOC auto-detection, and a
3-step engine fallback chain (lualatex → xelatex → pdflatex).
"""
import dataclasses
import json
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# LaTeX preamble snippets per theme
# ---------------------------------------------------------------------------
THEME_PREAMBLE = {
    "academic": r"""
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{booktabs}
\usepackage{amsmath,amssymb,amsthm}
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{definition}[theorem]{Definition}
\newtheorem{proposition}[theorem]{Proposition}
\newtheorem{corollary}[theorem]{Corollary}
\theoremstyle{remark}
\newtheorem{remark}[theorem]{Remark}
""",
    "minimal": r"""
\usepackage{lmodern}
\usepackage{microtype}
\usepackage[parfill]{parskip}
\setlength{\parindent}{0pt}
""",
    "tech": r"""
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{fancyvrb}
\usepackage{listings}
\lstset{basicstyle=\ttfamily\small,breaklines=true}
""",
}

THEME_PANDOC_EXTRA = {
    "academic": ["--toc", "--number-sections", "--highlight-style=tango"],
    "minimal":  ["--highlight-style=monochrome"],
    "tech":     ["--toc", "--highlight-style=tango"],
}


# ---------------------------------------------------------------------------
# Known LaTeX error → recovery action
# ---------------------------------------------------------------------------
RECOVERIES = [
    (re.compile(r"font.*not found|fontspec error", re.I),   "no_monofont"),
    (re.compile(r"Unicode char.*not set up",        re.I),  "ascii_safe"),
    (re.compile(r"Missing \$ inserted",             re.I),  "report_math"),
]


@dataclasses.dataclass
class RunLog:
    source: str = ""
    issues: list[dict] = dataclasses.field(default_factory=list)
    transforms: list[dict] = dataclasses.field(default_factory=list)
    compile: dict = dataclasses.field(default_factory=dict)

    def save(self, path: Path):
        path.write_text(json.dumps(dataclasses.asdict(self), indent=2, ensure_ascii=False))


class MdToPdfPipeline:
    ENGINES = ["lualatex", "xelatex", "pdflatex"]

    def __init__(
        self,
        src: Path,
        out: Path,
        *,
        theme: str = "academic",
        keep_intermediate: bool = False,
        dry_run: bool = False,
        log_path: Path | None = None,
        engine: str | None = None,
        margin: str = "1in",
        fontsize: str = "11pt",
        extra_pandoc: str = "",
        no_monofont: bool = False,
    ):
        self.src = src.resolve()
        self.out = out
        self.theme = theme
        self.keep_intermediate = keep_intermediate
        self.dry_run = dry_run
        self.log_path = log_path
        self.preferred_engine = engine or "lualatex"
        self.margin = margin
        self.fontsize = fontsize
        self.extra_pandoc = extra_pandoc.split() if extra_pandoc else []
        self.no_monofont = no_monofont
        self.log = RunLog(source=str(self.src))

    # ------------------------------------------------------------------
    # Stage 1 + 2: analysis + transformation (from md-to-pdf)
    # ------------------------------------------------------------------
    LATEX_CMDS = [
        "mathcal", "mathbf", "mathrm", "mathbb", "mathfrak",
        "mathsf", "mathtt", "text", "operatorname", "boldsymbol",
        "vec", "hat", "tilde", "bar", "dot", "ddot",
    ]

    def _fix_subscript_superscript(self, content: str) -> tuple[str, int]:
        pattern = re.compile(
            r"([_^])(\\(?:" + "|".join(self.LATEX_CMDS) + r")\{)"
        )
        count = 0
        def replacer(m):
            nonlocal count
            count += 1
            return m.group(1) + "{" + m.group(2)
        # Need to close the extra brace — use a balanced-brace approach
        # Simpler: wrap the command+arg in braces
        result = re.sub(
            r"([_^])(\\(?:" + "|".join(self.LATEX_CMDS) + r")\{[^}]*\})",
            r"\1{\2}",
            content,
        )
        changes = sum(1 for a, b in zip(content.split("\n"), result.split("\n")) if a != b)
        return result, changes

    def _normalize_unicode(self, content: str) -> str:
        import unicodedata
        return unicodedata.normalize("NFC", content)

    def _ascii_safe(self, content: str) -> str:
        box_map = str.maketrans("┌┐└┘├┤┬┴┼─│╔╗╚╝╠╣╦╩╬═║", "+++++++++-|+++++++++-|")
        return content.translate(box_map)

    def _analyze(self, content: str) -> list[dict]:
        issues = []
        # Unbraced subscripts/superscripts
        cmds = "|".join(self.LATEX_CMDS)
        if re.search(rf"[_^]\\(?:{cmds})\{{", content):
            issues.append({"severity": "error", "kind": "unbraced_sub_super",
                           "description": "Unbraced LaTeX sub/superscripts detected — will auto-fix"})
        # Unclosed math
        singles = content.count("$") - 2 * content.count("$$")
        if singles % 2 != 0:
            issues.append({"severity": "warning", "kind": "unclosed_math",
                           "description": "Possible unclosed $...$ math delimiter"})
        return issues

    def _transform(self, content: str, *, ascii_safe: bool = False) -> str:
        content = self._normalize_unicode(content)
        content, _ = self._fix_subscript_superscript(content)
        if ascii_safe:
            content = self._ascii_safe(content)
        return content

    # ------------------------------------------------------------------
    # Stage 3: compile
    # ------------------------------------------------------------------
    def _build_cmd(self, engine: str, *, no_monofont: bool = False) -> list[str]:
        cmd = [
            "pandoc", str(self.src),
            "-o", str(self.out),
            f"--pdf-engine={engine}",
            f"-V", f"geometry:margin={self.margin}",
            f"-V", f"fontsize={self.fontsize}",
            "--standalone",
        ]
        cmd += THEME_PANDOC_EXTRA.get(self.theme, [])

        if not no_monofont and engine in ("lualatex", "xelatex"):
            cmd += ["-V", "monofont=JetBrainsMono Nerd Font Mono"]

        preamble = THEME_PREAMBLE.get(self.theme, "")
        if preamble:
            cmd += ["-V", f"header-includes={preamble}"]

        cmd += self.extra_pandoc
        return cmd

    def _try_compile(self, content: str, engine: str, *, no_monofont: bool = False,
                     ascii_safe: bool = False) -> tuple[bool, str]:
        transformed = self._transform(content, ascii_safe=ascii_safe)

        # Write transformed source to temp file
        tmp = self.src.with_suffix(".forge-tmp.md")
        tmp.write_text(transformed, encoding="utf-8")

        cmd = self._build_cmd(engine, no_monofont=no_monofont)
        # Replace source in cmd
        cmd[1] = str(tmp)

        r = subprocess.run(cmd, capture_output=True, text=True)
        tmp.unlink(missing_ok=True)
        return r.returncode == 0, r.stderr

    def _compile_with_recovery(self, content: str) -> bool:
        engine = self.preferred_engine
        engines_to_try = [engine] + [e for e in self.ENGINES if e != engine]

        for eng in engines_to_try:
            ok, stderr = self._try_compile(content, eng)
            if ok:
                self.log.compile = {"success": True, "engine": eng, "retries": 0}
                return True

            # Attempt recovery based on error
            recovery = None
            for pattern, action in RECOVERIES:
                if pattern.search(stderr):
                    recovery = action
                    break

            if recovery == "no_monofont":
                ok, stderr = self._try_compile(content, eng, no_monofont=True)
                if ok:
                    self.log.compile = {"success": True, "engine": eng, "retries": 1, "recovery": "no_monofont"}
                    return True
            elif recovery == "ascii_safe":
                ok, stderr = self._try_compile(content, eng, ascii_safe=True)
                if ok:
                    self.log.compile = {"success": True, "engine": eng, "retries": 1, "recovery": "ascii_safe"}
                    return True
            elif recovery == "report_math":
                print(f"[doc-forge] ⚠ Unclosed math environment detected. Fix `$...$` delimiters in source.",
                      file=sys.stderr)

        self.log.compile = {"success": False, "stderr_tail": stderr[-800:]}
        return False

    # ------------------------------------------------------------------
    # Main
    # ------------------------------------------------------------------
    def run(self) -> None:
        content = self.src.read_text(encoding="utf-8", errors="replace")

        issues = self._analyze(content)
        self.log.issues = issues
        for issue in issues:
            icon = {"error": "✗", "warning": "⚠", "info": "i"}.get(issue["severity"], "•")
            print(f"  {icon} {issue['description']}")

        if self.dry_run:
            print(f"[dry-run] would compile {self.src} → {self.out} (theme={self.theme})")
            return

        self.out.parent.mkdir(parents=True, exist_ok=True)

        ok = self._compile_with_recovery(content)
        if ok:
            print(f"[doc-forge] ✓ {self.out}  (theme={self.theme}, engine={self.log.compile.get('engine')})")
        else:
            print(f"[doc-forge] ✗ compilation failed — see stderr above", file=sys.stderr)
            if self.log_path:
                self.log.save(self.log_path)
            sys.exit(1)

        if self.log_path:
            self.log.save(self.log_path)


# ---------------------------------------------------------------------------
# pdf → md shim (thin wrapper, keeps forge.py clean)
# ---------------------------------------------------------------------------
class PdfToMdPipeline:
    def __init__(self, src, out, *, mode="auto", pages=None, frontmatter=True,
                 dry_run=False, log_path=None):
        self.src = Path(src)
        self.out = Path(out)
        self.mode = mode
        self.pages = pages
        self.frontmatter = frontmatter
        self.dry_run = dry_run
        self.log_path = log_path

    def run(self):
        # Delegate to existing pdf-to-md logic via subprocess for now
        skill_dir = Path(__file__).parent.parent.parent / "pdf-to-md" / "scripts"
        script = skill_dir / "pdf_to_md.py"
        if not script.exists():
            print(f"[doc-forge] pdf-to-md script not found at {script}", file=sys.stderr)
            sys.exit(1)
        cmd = [sys.executable, str(script), str(self.src), "-o", str(self.out)]
        if self.mode != "auto":
            cmd += ["--mode", self.mode]
        if self.pages:
            cmd += ["--pages", self.pages]
        if not self.frontmatter:
            cmd += ["--no-frontmatter"]
        if self.dry_run:
            cmd += ["--dry-run"]
        if self.log_path:
            cmd += ["--log", str(self.log_path)]
        subprocess.run(cmd, check=True)
