---
name: doc-forge
description: 'Universal document conversion engine for OmarOS. Use this skill whenever the user wants to convert between document formats: .tex → .md, .md → .pdf, .md → .docx, .pdf → .md, or batch-convert an entire directory. Also trigger when the user mentions "convert my LaTeX", "export reflexiones to markdown", "compile notes to PDF", "batch convert", "make a nice PDF from this", "tex to md", "md to pdf", or any format-to-format document transformation. Prefer this over ad-hoc pandoc commands whenever quality or OmarOS frontmatter matters. For Omar''s Reflexiones_a_Latex repo at /Users/omarkhalil/OmarOS/05_Projects/Reflexiones_a_Latex/latex, this is the skill to use.'
---

# doc-forge — Universal Document Converter

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Pandoc-powered conversion engine with OmarOS vault integration. One script, all
directions, with automatic frontmatter generation and vault routing hints.

```
Input detection → Pre-processing → Pandoc → Post-processing → OmarOS frontmatter
```

---

## Quick start

```bash
SKILL_DIR="/Users/omarkhalil/OmarOS//Users/omarkhalil/GitHub/Constellation/skills/omaros/doc-forge"
SCRIPT="$SKILL_DIR/scripts/forge.py"

# .tex → .md (with OmarOS frontmatter)
python "$SCRIPT" chapter.tex

# .md → .pdf (with theme)
python "$SCRIPT" notes.md --theme academic

# batch: entire directory of .tex → .md
python "$SCRIPT" /path/to/chapters/ --batch --to md

# .md → .docx
python "$SCRIPT" notes.md -o report.docx
```

---

## Supported conversions

| From | To | Engine | Notes |
|------|-----|--------|-------|
| `.tex` | `.md` | pandoc + pre/post | Math preserved, `\input{}` resolved |
| `.md` | `.pdf` | pandoc + lualatex | Themes: academic, minimal, tech |
| `.md` | `.docx` | pandoc | Clean Word output |
| `.tex` | `.pdf` | lualatex direct | Full LaTeX compilation |
| `.pdf` | `.md` | pymupdf4llm / OCR | Fallback chain |

Conversion direction is **auto-detected** from the input extension. Override with `-o output.ext`.

---

## Invocation reference

```bash
# Auto-detect (tex→md, md→pdf based on input extension)
python "$SCRIPT" input.tex
python "$SCRIPT" input.md

# Explicit output path (also sets conversion target)
python "$SCRIPT" input.tex -o ~/vault/note.md
python "$SCRIPT" input.md -o ~/vault/report.pdf

# Batch mode — convert all files of one type in a directory
python "$SCRIPT" /path/to/dir/ --batch --from tex --to md
python "$SCRIPT" /path/to/dir/ --batch --from md --to pdf --theme minimal

# PDF themes (md→pdf only)
python "$SCRIPT" notes.md --theme academic    # serif, numbered sections, TOC
python "$SCRIPT" notes.md --theme minimal     # clean, no headers
python "$SCRIPT" notes.md --theme tech        # monospace-friendly, code blocks

# Dry-run: show what would happen, write nothing
python "$SCRIPT" input.tex --dry-run

# Keep intermediate files (.tex for pdf builds, raw pandoc .md for tex→md)
python "$SCRIPT" input.tex --keep-intermediate

# Skip OmarOS frontmatter generation
python "$SCRIPT" input.tex --no-frontmatter

# Resolve \input{} recursively before converting (default: true)
python "$SCRIPT" input.tex --no-resolve-inputs

# Show vault routing suggestion only
python "$SCRIPT" input.tex --route-only

# Write JSON run log
python "$SCRIPT" input.tex --log run.json
```

---

## tex → md pipeline (the main new capability)

### Stage 1 — Input resolution
If the `.tex` file uses `\input{...}` or `\include{...}`, the referenced files are
inlined into a single source before conversion. This is essential for multi-file
LaTeX projects like Reflexiones_a_Latex where chapters are split across files.

### Stage 2 — Pre-processing
- Strip LaTeX comments (`% ...`)
- Handle custom macro definitions: expand simple `\newcommand` macros
- Normalize math environments: `\[ ... \]` → `$$ ... $$`
- Mark theorem-like environments (`theorem`, `lemma`, `proof`, `definition`,
  `proposition`, `corollary`, `remark`) with bold headings in the output

### Stage 3 — Pandoc conversion
```bash
pandoc -f latex -t 'gfm+tex_math_dollars-tex_math_gfm' \
  --wrap=none \
  --standalone \
  input.tex -o output.md
```
`-tex_math_gfm` is essential: pandoc 3.x enables `tex_math_gfm` by default in
GFM mode, which emits `` $`...`$ `` and ` ```math ` blocks that Obsidian cannot
render. Disabling it forces `$...$` / `$$...$$` output, which Obsidian's
MathJax renderer understands natively.

### Stage 4 — Post-processing
- Remove pandoc artefacts (spurious `:::` divs, leftover `\hypertarget`)
- Collapse excessive blank lines (max 2)
- Fix escaped underscores in math: `\_` → `_` inside `$...$` blocks

### Stage 5 — OmarOS frontmatter
Extracts from the LaTeX source:
- `\title{...}` → `title:`
- `\author{...}` → `author:`
- `\chapter{...}` / `\section{...}` headings → outline summary

Infers vault domain from file path + content:
| Path contains | Domain | Subdomain |
|---|---|---|
| `reflexiones_filosof` | `01_Daily_Life` | `Reflections/Philosophy` |
| `algebra` | `06_Knowledge_Base` | `Mathematics/Algebra` |
| `analisis_funcional` | `06_Knowledge_Base` | `Mathematics/Functional_Analysis` |
| `topologia` | `06_Knowledge_Base` | `Mathematics/Topology` |
| `teoria_medida` | `06_Knowledge_Base` | `Mathematics/Measure_Theory` |
| `stochastic` / `probability` | `06_Knowledge_Base` | `Mathematics/Stochastic_Processes` |
| `calculo` | `06_Knowledge_Base` | `Mathematics/Calculus` |
| `mathematical_finance` | `06_Knowledge_Base` | `Mathematics/Finance` |
| `engie` | `03_Work` | `ENGIE` |
| `ai_claude` | `07_AI_and_Agents` | `Reference` |
| `informatica` / `csharp` / `ml` / `git` | `06_Knowledge_Base` | `Computing/...` |
| `fisica` / `physics` | `06_Knowledge_Base` | `Physics` |

Fallback: if the content contains `\begin{theorem}` or similar, routes to
`06_Knowledge_Base/Mathematics`.

---

## md → pdf pipeline (improved over md-to-pdf)

Inherits all fixes from `md-to-pdf` (subscript bracing, unicode box-drawing,
lualatex engine, JetBrainsMono Nerd Font) and adds:

### Themes

**`academic`** (default for math-heavy content):
- Serif body font (Latin Modern)
- Numbered sections
- Auto-generated TOC for docs > 3 sections
- Page numbers in footer
- Theorem-block styling

**`minimal`**:
- Sans-serif (Inter/Helvetica)
- No section numbers
- No TOC
- Generous whitespace

**`tech`**:
- Monospace-friendly
- Syntax-highlighted code blocks (via `--highlight-style tango`)
- Dark header bar

### Recovery chain
Same as `md-to-pdf`: font errors → retry without monofont; Unicode errors →
retry with ascii-safe. Plus new recovery: if lualatex fails entirely, falls
back to xelatex, then pdflatex (with Unicode warning).

---

## Batch mode

Processes all matching files in a directory. Outputs go next to their sources
by default, or into a `--out-dir` if specified.

```bash
# Convert all .tex in DOCUMENTO_COMPLETO to .md
python "$SCRIPT" \
  /Users/omarkhalil/OmarOS/05_Projects/Reflexiones_a_Latex/latex/DOCUMENTO_COMPLETO/chapters/ \
  --batch --from tex --to md \
  --out-dir ~/vault-import/

# Progress is printed per file; errors don't abort the batch
# Final summary: N succeeded, M failed (with paths)
```

Batch runs are sequential by default. Large batches (>20 files) print a progress
counter every 5 files.

---

## OmarOS routing

After conversion, `doc-forge` prints a **routing suggestion**:

```
→ Vault route: 06_Knowledge_Base/Mathematics/Functional_Analysis/analisisfuncional.md
  (check the current placement rules before writing)
```

This is advisory — check the current vault placement rules before writing.
Use `--route-only` to get the suggestion without converting.

---

## Dependencies

```bash
# Core
brew install pandoc               # Conversion engine
brew install --cask mactex        # or: brew install basictex

# pdf → md (fallback chain)
pip install pymupdf4llm           # Primary PDF extractor
pip install pdfplumber            # Fallback
pip install pdf2image pytesseract # OCR for scanned PDFs
brew install tesseract
```

---

## Troubleshooting

**"pandoc not found"** → `brew install pandoc`  
**Math renders as literal text in md output** → ensure pandoc version ≥ 3.x; check `gfm+tex_math_dollars` flag  
**`\input{}` not resolved** → pass explicit `--base-dir /path/to/tex/root`  
**lualatex font error** → the recovery chain handles this automatically; if it persists, pass `--no-monofont`  
**Batch stops on error** → use `--continue-on-error` (default) or `--fail-fast` to abort at first failure  
**Frontmatter domain is wrong** → edit the generated YAML before routing to vault
