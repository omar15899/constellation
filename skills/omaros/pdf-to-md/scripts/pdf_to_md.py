#!/usr/bin/env python3
"""pdf_to_md.py — Convert PDF to Markdown.

Pipeline: Detection → Extraction → Cleanup → Output
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect_pdf_type(pdf_path: Path) -> str:
    """Classify PDF as 'text', 'scanned', or 'mixed' by average char density."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        if not doc:
            return "unknown"
        avg_chars = sum(len(p.get_text()) for p in doc) / len(doc)
        doc.close()
        if avg_chars > 150:
            return "text"
        if avg_chars > 30:
            return "mixed"
        return "scanned"
    except ImportError:
        return "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Extraction backends
# ---------------------------------------------------------------------------

def convert_pymupdf4llm(pdf_path: Path, pages: Optional[list[int]] = None) -> str:
    """Primary: pymupdf4llm — best structure-aware Markdown extraction."""
    import pymupdf4llm
    return pymupdf4llm.to_markdown(str(pdf_path), pages=pages)


def convert_pdfplumber(pdf_path: Path, pages: Optional[list[int]] = None) -> str:
    """Fallback: pdfplumber — reliable text + table extraction."""
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        indices = pages if pages is not None else list(range(len(pdf.pages)))
        for idx in indices:
            page = pdf.pages[idx]
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            if text.strip():
                parts.append(text.strip())
            for table in (page.extract_tables() or []):
                if not table or len(table) < 2:
                    continue
                header = [str(c or "").strip() for c in table[0]]
                rows = [[str(c or "").strip() for c in row] for row in table[1:]]
                md_rows = ["| " + " | ".join(header) + " |",
                           "| " + " | ".join("---" for _ in header) + " |"]
                md_rows += ["| " + " | ".join(row) + " |" for row in rows]
                parts.append("\n".join(md_rows))
    return "\n\n".join(parts)


def convert_ocr(pdf_path: Path, pages: Optional[list[int]] = None, lang: str = "eng") -> str:
    """OCR path for scanned PDFs: pdf2image + pytesseract."""
    from pdf2image import convert_from_path
    import pytesseract

    # pdf2image uses 1-based page numbers
    first_page = (min(pages) + 1) if pages else None
    last_page = (max(pages) + 1) if pages else None

    images = convert_from_path(str(pdf_path), first_page=first_page, last_page=last_page)
    parts: list[str] = []
    for img in images:
        text = pytesseract.image_to_string(img, lang=lang).strip()
        if text:
            parts.append(text)
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def clean_markdown(text: str) -> str:
    """Light cleanup: collapse 3+ blank lines, strip trailing whitespace."""
    import re
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    lines = [l.rstrip() for l in text.splitlines()]
    return "\n".join(lines)


def build_frontmatter(pdf_path: Path, converter: str, page_count: int) -> str:
    today = date.today().isoformat()
    title = pdf_path.stem.replace("_", " ").replace("-", " ").title()
    return (
        f"---\n"
        f"title: {title}\n"
        f"note_type: reference\n"
        f"source: {pdf_path.name}\n"
        f"converter: {converter}\n"
        f"pages_converted: {page_count}\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        f"ai_generated: true\n"
        f"---\n\n"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_pages(spec: str) -> list[int]:
    """Parse '0-4' or '0,2,5' into a list of 0-based page indices."""
    if "-" in spec and "," not in spec:
        start, end = spec.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(p) for p in spec.split(",")]


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert PDF → Markdown")
    ap.add_argument("input", type=Path, help="Input PDF")
    ap.add_argument("-o", "--output", type=Path, help="Output .md path (default: input stem + .md)")
    ap.add_argument("--pages", help="0-based page range or list: '0-4' or '0,2,5'")
    ap.add_argument("--mode", choices=["auto", "text", "ocr"], default="auto",
                    help="Extraction mode (default: auto-detect)")
    ap.add_argument("--lang", default="eng", help="Tesseract language for OCR (default: eng)")
    ap.add_argument("--no-frontmatter", action="store_true", help="Skip YAML frontmatter")
    ap.add_argument("--log", type=Path, help="Write JSON run log to this path")
    ap.add_argument("--dry-run", action="store_true", help="Detect and report; do not convert")
    args = ap.parse_args()

    pdf = args.input.resolve()
    if not pdf.exists():
        print(f"ERROR: {pdf} not found", file=sys.stderr)
        sys.exit(1)

    out = args.output or pdf.with_suffix(".md")
    pages = parse_pages(args.pages) if args.pages else None

    # --- Dry run ---
    if args.dry_run:
        pdf_type = detect_pdf_type(pdf)
        print(f"PDF     : {pdf}")
        print(f"Type    : {pdf_type}")
        print(f"Mode    : {args.mode} → would use {'ocr' if pdf_type == 'scanned' and args.mode == 'auto' else 'text'}")
        print(f"Pages   : {pages or 'all'}")
        print(f"Output  : {out}")
        return

    # --- Determine mode ---
    mode = args.mode
    if mode == "auto":
        pdf_type = detect_pdf_type(pdf)
        print(f"Detected: {pdf_type}")
        mode = "ocr" if pdf_type == "scanned" else "text"

    log: dict = {
        "source": str(pdf),
        "mode": mode,
        "pages": pages,
        "converter": None,
        "success": False,
        "chars": 0,
        "error": None,
    }

    # --- Extract ---
    md_text: Optional[str] = None
    converter_used = "unknown"

    if mode == "text":
        try:
            md_text = convert_pymupdf4llm(pdf, pages)
            converter_used = "pymupdf4llm"
            print(f"Converted with pymupdf4llm ({len(md_text):,} chars)")
        except ImportError:
            print("pymupdf4llm not installed — falling back to pdfplumber")
        except Exception as exc:
            print(f"pymupdf4llm failed ({exc}) — falling back to pdfplumber")

        if md_text is None:
            try:
                md_text = convert_pdfplumber(pdf, pages)
                converter_used = "pdfplumber"
                print(f"Converted with pdfplumber ({len(md_text):,} chars)")
            except Exception as exc:
                log["error"] = str(exc)
                print(f"ERROR: pdfplumber also failed: {exc}", file=sys.stderr)
                if args.log:
                    args.log.write_text(json.dumps(log, indent=2))
                sys.exit(1)

    elif mode == "ocr":
        try:
            md_text = convert_ocr(pdf, pages, args.lang)
            converter_used = f"tesseract-ocr ({args.lang})"
            print(f"OCR complete ({len(md_text):,} chars)")
        except Exception as exc:
            log["error"] = str(exc)
            print(f"ERROR: OCR failed: {exc}", file=sys.stderr)
            if args.log:
                args.log.write_text(json.dumps(log, indent=2))
            sys.exit(1)

    assert md_text is not None

    # --- Cleanup ---
    md_text = clean_markdown(md_text)

    # --- Frontmatter ---
    page_count = len(pages) if pages else 0
    if not args.no_frontmatter:
        md_text = build_frontmatter(pdf, converter_used, page_count) + md_text

    # --- Write ---
    out.write_text(md_text, encoding="utf-8")
    print(f"Written : {out}")

    log.update({"converter": converter_used, "success": True, "chars": len(md_text), "output": str(out)})
    if args.log:
        args.log.write_text(json.dumps(log, indent=2))
        print(f"Log     : {args.log}")


if __name__ == "__main__":
    main()
