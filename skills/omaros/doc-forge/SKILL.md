---
name: doc-forge
description: "Convert OmarOS documents between LaTeX, Markdown, PDF and Word using the bundled converters, individually or in batches. Use for format conversion and mathematical-note export; document editing and layout design belong to their format tools."
---

# Document conversion

Preserve the source and choose the intended output path before conversion.
Use the [OmarOS profile](../../../profiles/omaros.md) for placement and privacy;
a converter's routing suggestion is advisory.

## Supported routes

| Input | Output | Implementation |
| --- | --- | --- |
| `.tex` | `.md`, default | [tex_to_md.py](scripts/tex_to_md.py): input resolution, simple macros, Pandoc, metadata |
| `.tex` | `.pdf` | Direct LaTeX compilation |
| `.md` | `.pdf`, default | [md_to_pdf.py](scripts/md_to_pdf.py): Pandoc and TeX |
| `.md` | `.docx` | Pandoc |
| `.pdf` | `.md`, default | [pdf_to_md.py](scripts/pdf_to_md.py) and [pdf_extract.py](scripts/pdf_extract.py): extraction or OCR |

The [dispatcher](scripts/forge.py) selects the route from the input and output
extensions. It does not convert arbitrary formats or accept Word as an input.

## Invocation

```sh
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py skill-run omaros doc-forge scripts/forge.py chapter.tex -o chapter.md
```

Set `-o notes.pdf` or `-o notes.docx` to choose the output explicitly. Without
`-o`, the default target is beside the input. For a directory use
`--batch --from tex --to md`, optionally `--out-dir DESTINATION`.

Select only options relevant to the route:

- LaTeX → Markdown: `--base-dir` for includes, `--no-resolve-inputs`,
  `--no-frontmatter`, `--keep-intermediate`. `--route-only` is supported here.
- Markdown → PDF: `--theme academic|minimal|tech`, `--engine`, `--margin`,
  `--fontsize`, `--no-monofont` and quoted `--pandoc-args`.
- PDF → Markdown: `--pdf-mode auto|text|ocr` and `--pages`.
- Batch: `--fail-fast` requests early termination; otherwise inspect the
  per-file failures. There is no `--continue-on-error` option.
- `--dry-run` skips conversion; batch setup can still create the output
  directory. Use static inspection if no filesystem mutation is allowed.

## Existing outputs and batches

Batch discovery is recursive. Without `--out-dir`, outputs stay beside their
sources; with it, filenames are flattened into one destination. Check duplicate
basenames and existing outputs before running so unrelated files are not
overwritten. Review every requested file's outcome, not just the process exit.

By default the dispatcher records `.doc_forge_manifest.json` beside the input
file, or inside the input directory for a batch. `--manifest PATH` changes its
location; `--no-manifest` disables reading and writing it.

The cache compares the source hash, output path, converter version and output
existence. It does not prove that options, included files or output bytes are
unchanged. Use `--force` or `--no-manifest` when those changed, after checking
the destinations. Keep optional `--log` output private when it contains private
paths or content; conversion does not authorize publication.

## Fidelity and delivery

LaTeX preprocessing resolves `\input` / `\include`, expands simple macros and
marks theorem-like environments; it is not a complete TeX semantic parser.
Check complex macros, bibliography, cross-references, figures and proof
structure against the source. The Markdown route uses
`gfm+tex_math_dollars-tex_math_gfm` for Obsidian-style `$...$` / `$$...$$` math.

Generated frontmatter and inferred routes need checking against the current
owner rules. Preserve confidentiality; a newly converted work document is
still a work document.

The PDF path can retry fonts, engines and Unicode substitutions. A successful
build can still have altered symbols or layout. Inspect actual PDF/Word pages
for equations, Unicode, tables, clipping, figures and page flow; for extracted
Markdown, check reading order, OCR errors and mathematical fidelity. Report
unrecoverable loss or missing dependencies rather than claiming equivalence.

Dependencies are route-specific: Pandoc, an available TeX engine for PDF, and
the extractor/OCR dependencies selected by `pdf_extract.py`. Inspect the
existing environment before proposing installation. Conversion and artifact
inspection do not require creating or running software tests.
