#!/usr/bin/env python3
"""
md_to_pdf.py — Deterministic Markdown→PDF compiler via Pandoc+LuaLaTeX.

Pipeline stages:
  1. Ingestion      — read source, enforce UTF-8
  2. Analysis       — detect issues, classify severity
  3. Transformation — apply idempotent fixes, log every change
  4. Compilation    — pandoc → lualatex → PDF
  5. Recovery       — parse LaTeX errors, retry with automatic fallbacks

Usage:
  python md_to_pdf.py input.md
  python md_to_pdf.py input.md -o output.pdf --keep-tex --log transform.json
  python md_to_pdf.py input.md --dry-run
  python md_to_pdf.py input.md --ascii-safe --engine xelatex
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


# ─── Data types ───────────────────────────────────────────────────────────────

@dataclass
class Issue:
    severity: str        # "error" | "warning" | "info"
    kind: str
    description: str
    line: Optional[int] = None


@dataclass
class TransformRecord:
    name: str
    count: int
    examples: list[str] = field(default_factory=list)


@dataclass
class CompileResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str
    retries: int = 0


# ─── Stage 1: Ingestion ───────────────────────────────────────────────────────

def ingest(path: Path) -> str:
    """Read source, enforce UTF-8. Falls back to latin-1 then re-encodes."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_bytes()
        text = raw.decode("latin-1")
        return text


# ─── Stage 2: Analysis ────────────────────────────────────────────────────────

# Box-drawing and block-element Unicode chars that break pdflatex
BOX_DRAWING: frozenset[str] = frozenset(
    "┌┐└┘│─├┤┬┴┼╭╮╰╯║═╔╗╚╝╠╣╦╩╬"
    "┃━┏┓┗┛┣┫┳┻╋"
    "▲▼◄►▶◀"
)

# LaTeX math-font commands that are commonly misused in subscripts/superscripts
MATH_CMD_NAMES = (
    "mathcal", "mathbf", "mathrm", "mathbb", "mathfrak",
    "mathsf", "mathtt", "text", "operatorname", "boldsymbol",
    "vec", "hat", "tilde", "bar", "dot", "ddot",
)
MATH_CMD_ALT = "|".join(MATH_CMD_NAMES)

# Matches  _\cmd{  or  ^\cmd{  — the unbraced form that LaTeX rejects
_BAD_SUBSUP_RE = re.compile(
    r'([_^])\\(' + MATH_CMD_ALT + r')(\{)'
)


def _mask_code_regions(text: str) -> str:
    """Replace code fences and inline code with spaces, preserving line count."""
    # Fenced blocks (``` or ~~~, with optional language tag)
    fenced = re.compile(r'(`{3,}|~{3,}).*?\1', re.DOTALL)
    text = fenced.sub(lambda m: re.sub(r'[^\n]', ' ', m.group()), text)
    # Inline code
    inline = re.compile(r'`[^`\n]+`')
    text = inline.sub(lambda m: ' ' * len(m.group()), text)
    return text


def analyze(text: str) -> list[Issue]:
    """Inspect text for known LaTeX/Pandoc failure patterns."""
    issues: list[Issue] = []
    lines = text.splitlines()
    masked = _mask_code_regions(text)

    # ── Unclosed display math $$...$$  ───────────────────────────────────────
    display_delimiters = len(re.findall(r'\$\$', masked))
    if display_delimiters % 2 != 0:
        issues.append(Issue(
            "warning", "unclosed_display_math",
            f"Odd number of $$ delimiters ({display_delimiters}) — possible unclosed display math"
        ))

    # ── Unclosed inline math $...$ ───────────────────────────────────────────
    # Remove $$ first so we don't double-count
    inline_text = re.sub(r'\$\$', '  ', masked)
    # Count unescaped $
    inline_dollars = len(re.findall(r'(?<!\\)\$', inline_text))
    if inline_dollars % 2 != 0:
        issues.append(Issue(
            "warning", "unclosed_inline_math",
            f"Odd number of $ delimiters ({inline_dollars}) — possible unclosed inline math"
        ))

    # ── Unbraced LaTeX subscript/superscript with math command ───────────────
    bad_lines: list[int] = []
    for i, line in enumerate(lines, 1):
        if _BAD_SUBSUP_RE.search(line):
            bad_lines.append(i)
    if bad_lines:
        sample = bad_lines[:5]
        issues.append(Issue(
            "error", "bad_subscript_superscript",
            f"Unbraced _\\cmd{{}} or ^\\cmd{{}} on line(s) {sample}"
            f"{'...' if len(bad_lines) > 5 else ''}. Will be auto-fixed.",
        ))

    # ── Box-drawing characters ────────────────────────────────────────────────
    box_lines: list[int] = []
    for i, line in enumerate(lines, 1):
        if any(c in BOX_DRAWING for c in line):
            box_lines.append(i)
    if box_lines:
        sample = box_lines[:3]
        issues.append(Issue(
            "info", "unicode_box_drawing",
            f"Box-drawing characters on line(s) {sample}"
            f"{'...' if len(box_lines) > 3 else ''}. "
            "lualatex + Nerd Font handles these; use --ascii-safe to convert to ASCII.",
        ))

    # ── Unclosed code fences ──────────────────────────────────────────────────
    fence_lines = [l.strip() for l in lines if l.strip().startswith('```') or l.strip().startswith('~~~')]
    if len(fence_lines) % 2 != 0:
        issues.append(Issue(
            "warning", "unclosed_code_fence",
            f"Odd number of code fence delimiters ({len(fence_lines)}) — possible unclosed code block"
        ))

    # ── Non-UTF-8-printable bytes warning (heuristic) ─────────────────────────
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as e:
        issues.append(Issue(
            "error", "encoding_issue",
            f"Text contains characters that cannot be encoded as UTF-8: {e}"
        ))

    return issues


# ─── Stage 3: Transformation ──────────────────────────────────────────────────

# Box-drawing → ASCII fallback table
BOX_TO_ASCII: dict[str, str] = {
    '┌': '+', '┐': '+', '└': '+', '┘': '+',
    '│': '|', '─': '-',
    '├': '+', '┤': '+', '┬': '+', '┴': '+', '┼': '+',
    '╭': '+', '╮': '+', '╰': '+', '╯': '+',
    '║': '|', '═': '=',
    '╔': '+', '╗': '+', '╚': '+', '╝': '+',
    '╠': '+', '╣': '+', '╦': '+', '╩': '+', '╬': '+',
    '┃': '|', '━': '-', '┏': '+', '┓': '+', '┗': '+', '┛': '+',
    '┣': '+', '┫': '+', '┳': '+', '┻': '+', '╋': '+',
    '▲': '^', '▼': 'v', '◄': '<', '►': '>', '▶': '>', '◀': '<',
}


def _find_matching_brace(text: str, start: int) -> int:
    """Return index of the } matching the { at position start. Returns -1 on failure."""
    assert text[start] == '{', f"Expected '{{' at position {start}, got {text[start]!r}"
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1


def fix_subscript_superscript(text: str) -> tuple[str, TransformRecord]:
    """
    _\\cmd{arg} → _{\\cmd{arg}}   (and same for ^).

    Uses balanced-brace matching so nested braces in args are handled correctly.
    Idempotent: already-braced forms _{ ... } are not matched.
    """
    record = TransformRecord(name="fix_subscript_superscript", count=0)
    result: list[str] = []
    i = 0
    while i < len(text):
        m = _BAD_SUBSUP_RE.search(text, i)
        if not m:
            result.append(text[i:])
            break
        # Emit everything up to the match
        result.append(text[i:m.start()])
        op = m.group(1)    # '_' or '^'
        cmd = m.group(2)   # e.g. 'mathcal'
        brace_start = m.end() - 1   # position of '{'
        brace_end = _find_matching_brace(text, brace_start)
        if brace_end == -1:
            # Unmatched brace — emit unchanged and advance past the match
            result.append(text[m.start():m.end()])
            i = m.end()
            continue
        arg = text[brace_start:brace_end + 1]   # includes surrounding braces
        original = text[m.start():brace_end + 1]
        fixed = f"{op}{{\\{cmd}{arg}}}"
        result.append(fixed)
        if record.count < 5:
            record.examples.append(f"{original!r} → {fixed!r}")
        record.count += 1
        i = brace_end + 1
    return "".join(result), record


def normalize_unicode(text: str) -> tuple[str, TransformRecord]:
    """NFC-normalize Unicode (combines combining characters, etc.)."""
    normalized = unicodedata.normalize("NFC", text)
    count = int(normalized != text)
    return normalized, TransformRecord(name="normalize_unicode", count=count)


def ascii_safe_box_drawing(text: str) -> tuple[str, TransformRecord]:
    """Replace box-drawing characters with their ASCII equivalents."""
    record = TransformRecord(name="ascii_safe_box_drawing", count=0)
    result: list[str] = []
    for ch in text:
        if ch in BOX_TO_ASCII:
            result.append(BOX_TO_ASCII[ch])
            record.count += 1
        else:
            result.append(ch)
    return "".join(result), record


def transform(text: str, ascii_safe: bool = False) -> tuple[str, list[TransformRecord]]:
    """
    Run all transformations in a fixed, deterministic order.
    Each stage is idempotent: running twice produces the same result.
    """
    records: list[TransformRecord] = []

    text, r = normalize_unicode(text)
    records.append(r)

    text, r = fix_subscript_superscript(text)
    records.append(r)

    if ascii_safe:
        text, r = ascii_safe_box_drawing(text)
        records.append(r)

    return text, records


# ─── Stage 4: Compilation ─────────────────────────────────────────────────────

MONOFONT = "JetBrainsMono Nerd Font Mono"


def _build_pandoc_cmd(
    input_path: Path,
    output_path: Path,
    engine: str,
    margin: str,
    fontsize: str,
    monofont: Optional[str],
    extra_args: Optional[list[str]],
) -> list[str]:
    cmd = [
        "pandoc", str(input_path),
        "-o", str(output_path),
        f"--pdf-engine={engine}",
        "-V", f"geometry:margin={margin}",
        "-V", f"fontsize={fontsize}",
        "--standalone",
    ]
    if monofont and engine in ("lualatex", "xelatex"):
        cmd += ["-V", f"monofont={monofont}"]
    if extra_args:
        cmd.extend(extra_args)
    return cmd


def _run_pandoc(cmd: list[str]) -> CompileResult:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return CompileResult(
            success=proc.returncode == 0,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired:
        return CompileResult(
            success=False, returncode=-1,
            stdout="", stderr="pandoc timed out after 180 seconds"
        )
    except FileNotFoundError:
        return CompileResult(
            success=False, returncode=-1,
            stdout="", stderr="pandoc not found — install pandoc first"
        )


def compile_pdf(
    source: str,
    output: Path,
    engine: str = "lualatex",
    margin: str = "1in",
    fontsize: str = "11pt",
    keep_tex: bool = False,
    monofont: Optional[str] = MONOFONT,
    extra_args: Optional[list[str]] = None,
) -> CompileResult:
    with tempfile.NamedTemporaryFile(
        suffix=".md", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(source)
        tmp_md = Path(f.name)

    try:
        # Optionally emit intermediate .tex
        if keep_tex:
            tex_path = output.with_suffix(".tex")
            tex_cmd = ["pandoc", str(tmp_md), "-o", str(tex_path), "--standalone"]
            subprocess.run(tex_cmd, capture_output=True, timeout=30)

        cmd = _build_pandoc_cmd(
            tmp_md, output, engine, margin, fontsize, monofont, extra_args
        )
        return _run_pandoc(cmd)
    finally:
        tmp_md.unlink(missing_ok=True)


# ─── Stage 5: Error Recovery ──────────────────────────────────────────────────

def parse_latex_errors(stderr: str) -> list[str]:
    """Extract meaningful error lines from pandoc/LaTeX stderr output."""
    errors: list[str] = []
    for line in stderr.splitlines():
        s = line.strip()
        if (s.startswith("!")
                or "LaTeX Error:" in s
                or "Package error:" in s
                or s.startswith("Error:")):
            errors.append(s)
        elif s.startswith("l.") and errors:
            errors.append(s)   # line reference following an error
    return errors


# Recovery strategy: (pattern, hint, strategy_dict)
_RECOVERY_STRATEGIES = [
    (
        re.compile(r"font.*not found|fontspec error|cannot find font", re.I),
        "Monofont not available — retry without monofont",
        {"drop_monofont": True},
    ),
    (
        re.compile(r"Unicode character.*not set up|missing character.*U\+", re.I),
        "Unicode character missing from font — retry with --ascii-safe",
        {"ascii_safe": True},
    ),
    (
        re.compile(r"Missing \$ inserted|Runaway argument|Paragraph ended before", re.I),
        "Likely unclosed math or environment — check $/$$ delimiters",
        {},
    ),
]


def attempt_recovery(
    source: str,
    result: CompileResult,
    output: Path,
    engine: str,
    margin: str,
    fontsize: str,
    current_ascii_safe: bool,
) -> tuple[str, CompileResult]:
    """
    Try recovery strategies in order.
    Returns (possibly_modified_source, final_result).
    """
    stderr = result.stderr + result.stdout

    for pattern, hint, strategy in _RECOVERY_STRATEGIES:
        if not pattern.search(stderr):
            continue

        print(f"      → Recovery hint: {hint}")

        if strategy.get("drop_monofont"):
            retry = compile_pdf(source, output, engine, margin, fontsize,
                                monofont=None)
            retry.retries = result.retries + 1
            if retry.success:
                return source, retry

        if strategy.get("ascii_safe") and not current_ascii_safe:
            safe_source, _ = ascii_safe_box_drawing(source)
            retry = compile_pdf(safe_source, output, engine, margin, fontsize)
            retry.retries = result.retries + 1
            if retry.success:
                return safe_source, retry

    return source, result


# ─── Log / report ─────────────────────────────────────────────────────────────

def write_log(
    path: Path,
    source_path: Path,
    issues: list[Issue],
    transforms: list[TransformRecord],
    result: CompileResult,
) -> None:
    data = {
        "source": str(source_path),
        "issues": [asdict(i) for i in issues],
        "transforms": [asdict(t) for t in transforms],
        "compile": {
            "success": result.success,
            "returncode": result.returncode,
            "retries": result.retries,
            "stderr_tail": result.stderr[-3000:] if result.stderr else "",
        },
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic Markdown→PDF compiler via Pandoc+LuaLaTeX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", type=Path, help="Input .md file")
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="Output PDF path (default: <input>.pdf)")
    parser.add_argument("--keep-tex", action="store_true",
                        help="Also emit intermediate .tex file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyse and show transforms; do not compile")
    parser.add_argument("--log", type=Path, default=None,
                        help="Write JSON transformation log to PATH")
    parser.add_argument("--ascii-safe", action="store_true",
                        help="Replace box-drawing chars with ASCII equivalents")
    parser.add_argument("--engine", default="lualatex",
                        choices=["lualatex", "xelatex", "pdflatex"],
                        help="PDF engine (default: lualatex)")
    parser.add_argument("--margin", default="1in",
                        help="Page margin (default: 1in)")
    parser.add_argument("--fontsize", default="11pt",
                        help="Font size (default: 11pt)")
    parser.add_argument("--no-monofont", action="store_true",
                        help="Disable monofont override (use LaTeX default)")
    parser.add_argument("--pandoc-args", default="",
                        help="Extra pandoc arguments as a single quoted string")
    args = parser.parse_args()

    src = args.input.resolve()
    if not src.exists():
        print(f"error: {src} not found", file=sys.stderr)
        return 1

    output = (args.output or src.with_suffix(".pdf")).resolve()
    monofont = None if args.no_monofont else MONOFONT
    extra = args.pandoc_args.split() if args.pandoc_args.strip() else None

    # ── Stage 1: Ingestion ────────────────────────────────────────────────
    print(f"[1/5] Ingesting {src.name} …")
    text = ingest(src)
    n_lines = text.count('\n') + 1
    print(f"      {len(text):,} chars, {n_lines} lines")

    # ── Stage 2: Analysis ─────────────────────────────────────────────────
    print("[2/5] Analysing …")
    issues = analyze(text)
    icons = {"error": "✗", "warning": "⚠", "info": "i"}
    for issue in issues:
        print(f"      {icons.get(issue.severity, '·')} [{issue.severity}] {issue.description}")
    if not issues:
        print("      No issues detected.")

    # ── Stage 3: Transformation ───────────────────────────────────────────
    print("[3/5] Transforming …")
    transformed, records = transform(text, ascii_safe=args.ascii_safe)
    changed = False
    for r in records:
        if r.count > 0:
            changed = True
            print(f"      · {r.name}: {r.count} change(s)")
            for ex in r.examples[:3]:
                print(f"          {ex}")
    if not changed:
        print("      No transformations applied (source is already clean).")

    if args.dry_run:
        print("\n[dry-run] Stopping before compilation.")
        if args.log:
            write_log(args.log, src, issues, records,
                      CompileResult(success=False, returncode=-1, stdout="", stderr="dry-run"))
            print(f"      Log written to {args.log}")
        return 0

    # ── Stage 4: Compilation ──────────────────────────────────────────────
    print(f"[4/5] Compiling → {output.name}  (engine={args.engine}) …")
    result = compile_pdf(
        transformed, output, args.engine, args.margin,
        args.fontsize, args.keep_tex, monofont, extra
    )

    if result.success:
        size_kb = output.stat().st_size // 1024 if output.exists() else 0
        print(f"      ✓ PDF written to {output}  ({size_kb} KB)")
        if args.keep_tex:
            print(f"      ✓ .tex written to {output.with_suffix('.tex')}")
    else:
        # ── Stage 5: Recovery ─────────────────────────────────────────────
        print("[5/5] Compilation failed. Attempting automatic recovery …")
        latex_errors = parse_latex_errors(result.stderr)
        for e in latex_errors[:5]:
            print(f"      ! {e}")

        _, result = attempt_recovery(
            transformed, result, output,
            args.engine, args.margin, args.fontsize, args.ascii_safe
        )

        if result.success:
            size_kb = output.stat().st_size // 1024 if output.exists() else 0
            print(f"      ✓ Recovered. PDF written to {output}  ({size_kb} KB)")
        else:
            print("      ✗ Recovery failed.\n")
            print("Pandoc/LaTeX stderr (last 40 lines):")
            for line in result.stderr.splitlines()[-40:]:
                print(f"  {line}")

    # ── Log ───────────────────────────────────────────────────────────────
    if args.log:
        write_log(args.log, src, issues, records, result)
        print(f"\n      Log written to {args.log}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
