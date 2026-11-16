---
name: md-to-pdf
description: DEPRECATED — absorbed into doc-forge. Do NOT invoke directly. Any Markdown → PDF conversion now routes through doc-forge, which handles .md↔.pdf alongside .tex↔.md, .md↔.docx, .pdf↔.md, and batch directory conversion. The canonical descriptor lives at /Users/omarkhalil/GitHub/Constellation/skills/omaros/doc-forge/SKILL.md. This stub is retained for governance traceability and the historical notes below; the routing/NL front door will never pick this skill over doc-forge.
deprecated: true
replaced_by: doc-forge
---

> **DEPRECATED — use `doc-forge`**. The implementation details below are kept
> as historical reference (Pandoc+LaTeX failure-mode catalogue) but all
> invocations should go through `doc-forge`, which owns every format-to-format
> conversion in OmarOS. See `/Users/omarkhalil/GitHub/Constellation/skills/omaros/doc-forge/SKILL.md`.


# md-to-pdf — Markdown → PDF Compiler

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

This skill drives a deterministic 5-stage pipeline:

```
Ingestion → Analysis → Transformation → Compilation → Recovery
```

The pipeline behaves like a compiler: same input always produces the same output,
every change is logged, and known LaTeX failure modes are fixed automatically
before Pandoc ever sees the source.

---

## Quick start

```bash
python /path/to/skills/md-to-pdf/scripts/md_to_pdf.py input.md
```

**Always resolve the script path first** — use `SKILL_DIR` as defined below.

```bash
SKILL_DIR="/Users/omarkhalil/OmarOS//Users/omarkhalil/GitHub/Constellation/skills/omaros/md-to-pdf"
SCRIPT="$SKILL_DIR/scripts/md_to_pdf.py"
```

---

## Invocation reference

```bash
# Basic — output sits next to the input
python "$SCRIPT" input.md

# Custom output path
python "$SCRIPT" input.md -o /path/to/output.pdf

# Dry-run: analyse and show what would be changed, don't compile
python "$SCRIPT" input.md --dry-run

# Keep intermediate .tex file (useful for debugging LaTeX errors)
python "$SCRIPT" input.md --keep-tex

# Write a JSON transformation log
python "$SCRIPT" input.md --log transforms.json

# Replace box-drawing chars (┌ │ ─ etc.) with ASCII equivalents
python "$SCRIPT" input.md --ascii-safe

# Larger margins, bigger font
python "$SCRIPT" input.md --margin 1.5in --fontsize 12pt

# Pass extra pandoc flags
python "$SCRIPT" input.md --pandoc-args "--toc --number-sections"

# Disable monofont override (use LaTeX's default verbatim font)
python "$SCRIPT" input.md --no-monofont

# Alternative engine (pdflatex breaks on Unicode; avoid unless specifically needed)
python "$SCRIPT" input.md --engine xelatex
```

---

## Pipeline stages

### 1. Ingestion
Reads the file and enforces UTF-8. Falls back to latin-1 if the file has legacy
encoding, then re-processes as UTF-8. Reports character and line count.

### 2. Analysis
Detects issues *before* any transformation:
- **error** — unbraced `_\mathcal{}` / `^\mathbf{}` subscripts/superscripts
- **warning** — unclosed `$...$` or `$$...$$` math delimiters
- **warning** — unclosed code fences
- **info** — box-drawing Unicode characters (handled by lualatex + Nerd Font)

All issues are printed with severity icons. Errors are auto-fixed in stage 3;
warnings require the user to fix the source manually.

### 3. Transformation
Applies fixes in a fixed, deterministic order:

1. **`normalize_unicode`** — NFC normalisation
2. **`fix_subscript_superscript`** — wraps `_\cmd{arg}` → `_{\cmd{arg}}` using
   balanced-brace matching (handles nested braces correctly; idempotent)
3. **`ascii_safe_box_drawing`** — only runs if `--ascii-safe` is passed

Every change is logged with a before/after example. Running the pipeline twice
on already-clean input applies zero changes.

Fixed LaTeX commands: `mathcal`, `mathbf`, `mathrm`, `mathbb`, `mathfrak`,
`mathsf`, `mathtt`, `text`, `operatorname`, `boldsymbol`, `vec`, `hat`,
`tilde`, `bar`, `dot`, `ddot`.

### 4. Compilation
```
pandoc input.md \
  --pdf-engine=lualatex \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V monofont="JetBrainsMono Nerd Font Mono" \
  --standalone
```

**lualatex is the default engine** — it handles Unicode natively. The
`JetBrainsMono Nerd Font Mono` monofont is set because it includes box-drawing
glyphs, so ASCII-art diagrams in code blocks render correctly.

### 5. Recovery
If compilation fails, the pipeline parses LaTeX error lines from stderr and
applies automatic fallbacks:

| Error pattern | Fallback |
|---|---|
| `font not found` / `fontspec error` | Retry without monofont override |
| `Unicode character not set up` | Retry with ascii-safe box-drawing conversion |
| `Missing $ inserted` / unclosed env | Reported with line hint; no auto-fix |

After recovery, the success/failure verdict and retry count are reported.

---

## Outputs

| File | When produced |
|---|---|
| `output.pdf` | Always (on success) |
| `output.tex` | Only with `--keep-tex` |
| `transforms.json` | Only with `--log PATH` |

The JSON log contains:
```json
{
  "source": "...",
  "issues": [{"severity": "...", "kind": "...", "description": "...", "line": null}],
  "transforms": [{"name": "...", "count": 0, "examples": []}],
  "compile": {"success": true, "returncode": 0, "retries": 0, "stderr_tail": ""}
}
```

---

## Failure modes that require manual intervention

The pipeline cannot auto-fix these — flag them clearly to the user:

1. **Truly unclosed math** — `$x = $ y` (mismatch). The user must close the delimiter.
2. **Malformed environments** — `\begin{align}` without `\end{align}`.
3. **Missing packages** — e.g. `! LaTeX Error: File 'algorithm.sty' not found.`
   → ask the user to install the package (`tlmgr install algorithms`) or remove the block.
4. **pdflatex with Unicode** — if the user insists on `--engine pdflatex` and the
   file has Unicode, switch them to lualatex instead.

---

## Workflow for Omar's math notes

Omar's vault notes in `06_Knowledge_Base/` are math-heavy and frequently use
`\mathcal`, `\mathbf`, `\mathrm` in subscripts/superscripts. Run the dry-run
first to preview what the transformer will fix, then compile:

```bash
python "$SCRIPT" note.md --dry-run
python "$SCRIPT" note.md --keep-tex --log note_transforms.json
```

If the PDF looks wrong, open `note.tex` to inspect the intermediate LaTeX.

---

## Troubleshooting

**"pandoc not found"** — `brew install pandoc`  
**"lualatex not found"** — `brew install --cask mactex` or `brew install basictex`  
**Font warning about JetBrainsMono** — JetBrains Mono Nerd Font is installed at
`~/Library/Fonts/`. If lualatex can't find it, use `--no-monofont`.  
**PDF is empty / 0 KB** — pandoc succeeded but lualatex failed silently. Run
`--keep-tex` and compile the .tex manually: `lualatex output.tex`  
**Math renders as literal text** — check that math is inside `$...$` or `$$...$$`
delimiters (not escaped as `\$`).
