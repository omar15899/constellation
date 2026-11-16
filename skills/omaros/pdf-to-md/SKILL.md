---
name: pdf-to-md
description: DEPRECATED — absorbed into doc-forge. Do NOT invoke directly. Any PDF → Markdown conversion now routes through doc-forge, the single canonical converter for every format pair in OmarOS (.tex↔.md, .md↔.pdf, .md↔.docx, .pdf↔.md, batch dirs). The historical implementation notes (detection → extraction → cleanup → output pipeline, Pandoc+LaTeX failure modes, etc.) are kept below for traceability. The NL router will never pick this skill over doc-forge.
deprecated: true
replaced_by: doc-forge
---

> **DEPRECATED — use `doc-forge`**. The body below is preserved as historical
> reference. All PDF → Markdown work now belongs in `doc-forge`; see
> `/Users/omarkhalil/GitHub/Constellation/skills/omaros/doc-forge/SKILL.md`.


# pdf-to-md — PDF → Markdown Converter

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Mirror image of `md-to-pdf`. Same 4-stage pipeline approach:

```
Detection → Extraction → Cleanup → Output
```

---

## Quick start

```bash
SKILL_DIR="/Users/omarkhalil/OmarOS//Users/omarkhalil/GitHub/Constellation/skills/omaros/pdf-to-md"
SCRIPT="$SKILL_DIR/scripts/pdf_to_md.py"

python "$SCRIPT" paper.pdf
```

Output is written to `paper.md` next to the source by default.

---

## Invocation reference

```bash
# Basic — .md lands next to the PDF
python "$SCRIPT" paper.pdf

# Custom output path
python "$SCRIPT" paper.pdf -o ~/vault/15_Reading/paper.md

# Convert specific pages only (0-based indices)
python "$SCRIPT" paper.pdf --pages 0-9
python "$SCRIPT" paper.pdf --pages 0,2,5

# Force OCR mode (for scanned / image-based PDFs)
python "$SCRIPT" paper.pdf --mode ocr

# OCR with a different Tesseract language
python "$SCRIPT" paper.pdf --mode ocr --lang spa

# Skip YAML frontmatter (raw Markdown only)
python "$SCRIPT" paper.pdf --no-frontmatter

# Dry-run: detect type and show what would happen, don't convert
python "$SCRIPT" paper.pdf --dry-run

# Write a JSON run log
python "$SCRIPT" paper.pdf --log run.json
```

---

## Pipeline stages

### 1. Detection
Classifies the PDF as `text`, `scanned`, or `mixed` by counting average extracted
characters per page using PyMuPDF. Drives the automatic mode selection:
- `text` / `mixed` → text-extraction path
- `scanned` → OCR path

### 2. Extraction

**Primary — `pymupdf4llm`** (install: `pip install pymupdf4llm`)

Best quality for text-based PDFs. Preserves headings, lists, tables, bold/italic,
code blocks, and inline math. Output is already structured Markdown.

**Fallback — `pdfplumber`** (install: `pip install pdfplumber`)

If `pymupdf4llm` is not installed or fails, falls back to `pdfplumber`. Text is
extracted with layout tolerance; tables are converted to Markdown format.
Structure (headings, emphasis) is not recovered — output is paragraphs + tables.

**OCR — `pdf2image` + `pytesseract`** (install: `pip install pdf2image pytesseract`)

For scanned documents. Each page is rasterised and fed to Tesseract. Output is
raw recognised text with page separators (`---`). Math is not preserved — it
comes out as best-effort character strings. Requires `tesseract` on PATH:
`brew install tesseract`.

### 3. Cleanup
- Collapses runs of 3+ blank lines to 2
- Strips trailing whitespace per line
- No semantic changes to the content

### 4. Output
Writes UTF-8 Markdown to the target path. Prepends YAML frontmatter by default:

```yaml
---
title: Paper Title From Filename
note_type: reference
source: paper.pdf
converter: pymupdf4llm
pages_converted: 0
created: 2026-04-20
updated: 2026-04-20
ai_generated: true
---
```

Use `--no-frontmatter` for raw output, or edit the frontmatter fields after
conversion (especially `note_type`, `domain`, `tags`) before ingesting into the vault.

---

## Math handling

PDF → Markdown math extraction is imperfect by nature. The situation by tool:

| Converter | Math rendering | Result |
|---|---|---|
| `pymupdf4llm` | Embedded text (e.g. LaTeX PDFs) | Reasonable — inline `$...$` preserved |
| `pymupdf4llm` | Rendered glyphs (e.g. Word/typeset) | Partial — Greek letters OK, operators may break |
| `pdfplumber` | Any | Raw text, no math markup |
| OCR | Any | Best-effort character recognition; expect errors |

**For math-heavy academic papers**, the safest workflow is:
1. Run the converter to get the text skeleton.
2. Open the PDF alongside the .md and manually correct math blocks.
3. Use `md-to-pdf` to verify the result compiles cleanly.

If the paper has a LaTeX source on arXiv, prefer downloading the `.tex` source
directly — it will yield perfect Markdown via `md-to-pdf` in reverse.

---

## OmarOS vault routing

After conversion, check the output against the current vault placement rules before finalising its
vault path. Typical destinations:

| PDF type | Vault destination |
|---|---|
| Academic paper | `15_Reading_and_Learning/Papers/<slug>.md` |
| Textbook chapter / reference | `06_Knowledge_Base/<subdomain>/<area>/<slug>.md` |
| Work document | `03_Work/` or `11_Documents_and_Reports/` |
| Research notes / preprints | `04_Research/<area>/<slug>.md` |

Update frontmatter fields (`domain`, `subdomain`, `tags`, `note_type`) after routing.

---

## Dependencies

```bash
# Core (text-based PDFs)
pip install pymupdf4llm          # Primary converter
pip install pdfplumber           # Fallback

# OCR (scanned PDFs)
pip install pdf2image pytesseract
brew install tesseract           # Tesseract binary

# Auto-detection (included with pymupdf4llm; standalone install if needed)
pip install pymupdf
```

---

## Troubleshooting

**"pymupdf4llm not found"** — `pip install pymupdf4llm`. If that fails, the
fallback to pdfplumber is automatic.

**Output is mostly empty** — the PDF is likely scanned. Rerun with `--mode ocr`.

**OCR quality is poor** — check that the correct Tesseract language pack is
installed (`brew install tesseract-lang`), then pass `--lang <code>`.

**Math looks garbled** — expected for typeset PDFs. See *Math handling* above.

**`pdf2image` fails** — requires `poppler`: `brew install poppler`.

**Frontmatter fields are wrong** — pass `--no-frontmatter` and write your own,
or edit the generated block before committing to the vault.
