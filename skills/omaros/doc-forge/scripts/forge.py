#!/usr/bin/env python3
"""
doc-forge — universal document converter
Entry point: auto-detects conversion, dispatches to the right pipeline.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_VERSION = 1
MANIFEST_FILENAME = ".doc_forge_manifest.json"
TOOL_VERSION = "doc-forge-1"


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_manifest_path(args, src_or_dir: Path) -> Path:
    if args.manifest:
        return Path(args.manifest).expanduser().resolve()
    base = src_or_dir if src_or_dir.is_dir() else src_or_dir.parent
    return (base / MANIFEST_FILENAME).resolve()


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"version": MANIFEST_VERSION, "entries": {}}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {"version": MANIFEST_VERSION, "entries": {}}
    if data.get("version") != MANIFEST_VERSION or "entries" not in data:
        return {"version": MANIFEST_VERSION, "entries": {}}
    return data


def save_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def manifest_skip(manifest: dict, src: Path, out: Path, src_sha: str) -> bool:
    e = manifest["entries"].get(str(src))
    if not e:
        return False
    if e.get("src_sha256") != src_sha:
        return False
    if e.get("dst") != str(out):
        return False
    if e.get("tool_version") != TOOL_VERSION:
        return False
    if not out.exists():
        return False
    return True


def manifest_record(manifest: dict, src: Path, out: Path, src_sha: str,
                    pipeline: str) -> None:
    manifest["entries"][str(src)] = {
        "src_sha256": src_sha,
        "src_size": src.stat().st_size,
        "dst": str(out),
        "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline": pipeline,
        "tool_version": TOOL_VERSION,
    }

CONVERSIONS = {
    ('.tex', '.md'),
    ('.md', '.pdf'),
    ('.md', '.docx'),
    ('.tex', '.pdf'),
    ('.pdf', '.md'),
}

DEFAULT_TARGET = {
    '.tex': '.md',
    '.md':  '.pdf',
    '.pdf': '.md',
}


def detect(src: Path, out: Path | None) -> tuple[str, str]:
    src_ext = src.suffix.lower()
    dst_ext = out.suffix.lower() if out else DEFAULT_TARGET.get(src_ext)
    if dst_ext is None:
        die(f"Cannot infer output format from {src_ext}. Pass -o output.ext")
    if (src_ext, dst_ext) not in CONVERSIONS:
        die(f"Unsupported conversion: {src_ext} → {dst_ext}")
    return src_ext, dst_ext


def die(msg: str, code: int = 1) -> None:
    print(f"[doc-forge] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def run_tex_to_md(args, src: Path, out: Path) -> None:
    from tex_to_md import TexToMdPipeline
    p = TexToMdPipeline(
        src=src,
        out=out,
        resolve_inputs=not args.no_resolve_inputs,
        frontmatter=not args.no_frontmatter,
        keep_intermediate=args.keep_intermediate,
        dry_run=args.dry_run,
        log_path=Path(args.log) if args.log else None,
        base_dir=Path(args.base_dir) if args.base_dir else None,
        route_only=args.route_only,
    )
    p.run()


def run_md_to_pdf(args, src: Path, out: Path) -> None:
    from md_to_pdf import MdToPdfPipeline
    p = MdToPdfPipeline(
        src=src,
        out=out,
        theme=args.theme,
        keep_intermediate=args.keep_intermediate,
        dry_run=args.dry_run,
        log_path=Path(args.log) if args.log else None,
        engine=args.engine,
        margin=args.margin,
        fontsize=args.fontsize,
        extra_pandoc=args.pandoc_args,
        no_monofont=args.no_monofont,
    )
    p.run()


def run_md_to_docx(args, src: Path, out: Path) -> None:
    import subprocess
    cmd = ["pandoc", str(src), "-o", str(out), "--standalone"]
    if args.dry_run:
        print(f"[dry-run] would run: {' '.join(cmd)}")
        return
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        die(f"pandoc failed:\n{r.stderr}")
    print(f"[doc-forge] ✓ {out}")


def run_tex_to_pdf(args, src: Path, out: Path) -> None:
    import subprocess
    engine = args.engine or "lualatex"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "pandoc", str(src),
        "-o", str(out),
        f"--pdf-engine={engine}",
        "--standalone",
    ]
    if args.dry_run:
        print(f"[dry-run] would run: {' '.join(cmd)}")
        return
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        die(f"pandoc+{engine} failed:\n{r.stderr}")
    print(f"[doc-forge] ✓ {out}")


def run_pdf_to_md(args, src: Path, out: Path) -> None:
    from pdf_to_md import PdfToMdPipeline
    p = PdfToMdPipeline(
        src=src,
        out=out,
        mode=args.pdf_mode,
        pages=args.pages,
        frontmatter=not args.no_frontmatter,
        dry_run=args.dry_run,
        log_path=Path(args.log) if args.log else None,
    )
    p.run()


PIPELINE_NAME = {
    ('.tex', '.md'):   "tex_to_md",
    ('.md',  '.pdf'):  "md_to_pdf",
    ('.md',  '.docx'): "md_to_docx",
    ('.tex', '.pdf'):  "tex_to_pdf",
    ('.pdf', '.md'):   "pdf_to_md",
}


def run_single(args, src: Path, out: Path | None,
               manifest: dict | None = None,
               manifest_path: Path | None = None) -> str:
    src_ext, dst_ext = detect(src, out)
    if out is None:
        out = src.with_suffix(dst_ext)
    output_lookup = out.absolute()
    out = out.resolve()
    src = src.resolve()

    pipeline = PIPELINE_NAME[(src_ext, dst_ext)]
    src_sha = _sha256_file(src) if src.is_file() else None

    use_manifest = manifest is not None
    if not use_manifest and not args.no_manifest:
        manifest_path = _resolve_manifest_path(args, src)
        manifest = load_manifest(manifest_path)
        use_manifest = True

    if (use_manifest and src_sha and not args.force
            and not args.dry_run and not args.route_only
            and manifest_skip(manifest, src, out, src_sha)):
        print(f"[doc-forge] = unchanged, skip: {src}")
        return "skip"

    dispatch = {
        ('.tex', '.md'):   run_tex_to_md,
        ('.md',  '.pdf'):  run_md_to_pdf,
        ('.md',  '.docx'): run_md_to_docx,
        ('.tex', '.pdf'):  run_tex_to_pdf,
        ('.pdf', '.md'):   run_pdf_to_md,
    }
    # TikZ attachment selection needs to inspect the original output ancestry.
    dispatch[(src_ext, dst_ext)](args, src, output_lookup if pipeline == "tex_to_md" else out)

    if (use_manifest and src_sha and out.exists()
            and not args.dry_run and not args.route_only):
        manifest_record(manifest, src, out, src_sha, pipeline)
        if manifest_path is not None:
            save_manifest(manifest_path, manifest)
    return "ok"


def run_batch(args) -> None:
    src_dir = Path(args.input)
    from_ext = f".{args.from_ext.lstrip('.')}"
    to_ext   = f".{args.to_ext.lstrip('.')}"
    out_dir  = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(src_dir.rglob(f"*{from_ext}"))
    if not files:
        die(f"No {from_ext} files found in {src_dir}")

    print(f"[doc-forge] batch: {len(files)} files, {from_ext} → {to_ext}", flush=True)

    manifest = None
    manifest_path = None
    if not args.no_manifest:
        manifest_path = _resolve_manifest_path(args, src_dir.resolve())
        manifest = load_manifest(manifest_path)
        print(f"[doc-forge] manifest: {manifest_path}", flush=True)

    succeeded, skipped, failed = 0, 0, []

    for i, f in enumerate(files, 1):
        out = (out_dir / f.with_suffix(to_ext).name) if out_dir else f.with_suffix(to_ext)
        try:
            result = run_single(args, f, out, manifest=manifest, manifest_path=None)
            if result == "skip":
                skipped += 1
            else:
                succeeded += 1
                if manifest is not None and manifest_path is not None:
                    save_manifest(manifest_path, manifest)
        except SystemExit:
            if args.fail_fast:
                if manifest is not None and manifest_path is not None:
                    save_manifest(manifest_path, manifest)
                raise
            failed.append(f.name)
        if i % 5 == 0 or i == len(files):
            print(f"  [{i}/{len(files)}] processed (ok={succeeded} skip={skipped} fail={len(failed)})",
                  flush=True)

    if manifest is not None and manifest_path is not None:
        save_manifest(manifest_path, manifest)

    print(f"\n[doc-forge] batch done: {succeeded} converted, {skipped} skipped, {len(failed)} failed")
    if failed:
        print("  failed:")
        for name in failed:
            print(f"    • {name}")


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="forge",
        description="doc-forge: universal document converter for OmarOS",
    )
    ap.add_argument("input", help="Input file or directory (for --batch)")
    ap.add_argument("-o", "--output", help="Output file path")
    ap.add_argument("--batch", action="store_true", help="Batch mode: convert all files in directory")
    ap.add_argument("--from", dest="from_ext", default="tex", help="Source extension for batch (default: tex)")
    ap.add_argument("--to",   dest="to_ext",   default="md",  help="Target extension for batch (default: md)")
    ap.add_argument("--out-dir", help="Output directory for batch mode")
    ap.add_argument("--fail-fast", action="store_true", help="Abort batch on first error (default: continue)")
    ap.add_argument("--theme", choices=["academic", "minimal", "tech"], default="academic",
                    help="PDF theme (md→pdf only)")
    ap.add_argument("--engine", help="PDF engine: lualatex (default), xelatex, pdflatex")
    ap.add_argument("--margin", default="1in", help="PDF margin (default: 1in)")
    ap.add_argument("--fontsize", default="11pt", help="PDF font size (default: 11pt)")
    ap.add_argument("--pandoc-args", default="", help="Extra pandoc flags (quoted string)")
    ap.add_argument("--no-monofont", action="store_true", help="Disable monofont override in PDF")
    ap.add_argument("--no-resolve-inputs", action="store_true", help="Don't resolve \\input{} in .tex")
    ap.add_argument("--no-frontmatter", action="store_true", help="Skip OmarOS YAML frontmatter")
    ap.add_argument("--base-dir", help="Base directory for resolving \\input{} (default: tex file's dir)")
    ap.add_argument("--keep-intermediate", action="store_true", help="Keep .tex/.pandoc-md intermediate files")
    ap.add_argument("--dry-run", action="store_true", help="Analyse and show plan without converting")
    ap.add_argument("--route-only", action="store_true", help="Show vault routing suggestion only")
    ap.add_argument("--pdf-mode", choices=["auto", "text", "ocr"], default="auto", help="pdf→md extraction mode")
    ap.add_argument("--pages", help="Pages to extract from PDF (e.g. 0-9 or 0,2,5)")
    ap.add_argument("--log", help="Write JSON run log to this path")
    ap.add_argument("--manifest", help=f"Path to idempotency manifest (default: <input dir>/{MANIFEST_FILENAME})")
    ap.add_argument("--no-manifest", action="store_true", help="Disable manifest read/write")
    ap.add_argument("--force", action="store_true", help="Reconvert even if manifest says unchanged")

    args = ap.parse_args()

    # Add script dir to path so sub-modules resolve
    sys.path.insert(0, str(Path(__file__).parent))

    if args.batch:
        run_batch(args)
    else:
        out = Path(args.output) if args.output else None
        run_single(args, Path(args.input), out)


if __name__ == "__main__":
    main()
