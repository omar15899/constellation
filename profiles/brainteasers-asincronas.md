# brainteasers-asincronas

Raíz: `/Users/omarkhalil/GitHub/brainteasers-asincronas`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

brainteasers-asincronas is the production system for the asynchronous video lectures of the Brainteasers Quant course in the Universidad de las Hespérides Máster en Finanzas Cuantitativas y Métodos Computacionales. It is perimeter `adjacent` in the constellation, tier null, status active, stack mixed — explicitly NOT bound by QuantOS tier discipline and must not touch QuantOS infrastructure. The repo contains ONLY the system (`_sistema/`: the vendored Hespérides Beamer template, styles, four validation modules plus a shared parser in hooks/, six scripts, a stdlib contract test, and a video template). The produced videos live outside it, in the OmarOS vault at ~/OmarOS/05_Projects/Brainteasers_Quant/asincronas/. Each video is exactly three deliverables: presentacion/main.tex compiled to build/presentacion.pdf, guion-teleprompter.md, and justificacion-pedagogica.md; source tracing and the adversarial review are embedded in the justification rather than added as extra artifacts.

## Fuentes del dominio

- [CLAUDE.md](../CLAUDE.md): separación entre sistema, fuentes y salida; jerarquía de fuentes; reglas duras.
- [Convenciones](../_sistema/convenciones.md): notación, formato del guion, tiempo, revisión adversaria y finalización.
- [Manual del sistema](../_sistema/README.md): secuencia de producción, scripts y fases de validación.
- [Evidencia educativa](../_sistema/referencias/evidencia-educativa.md): fuentes iniciales y límites de transferencia.
- [Validador](../_sistema/scripts/validar.py) y [controles](../_sistema/hooks/): comportamiento ejecutable de cada fase.

## Stack and commands
**Stack:** mixed — LaTeX (Beamer + LuaLaTeX, vendored Hespérides template, latexmk) + Python 3 stdlib only (no third-party deps, no venv, no uv, no packaging config) + bash scripts.

```bash
_sistema/scripts/nuevo_video.sh <sesion> <num-video> <slug> <duracion_objetivo_s> ["Título"] # scaffolds from _sistema/plantilla-video/ into $ASINCRONAS_OUT (default ~/OmarOS/05_Projects/Brainteasers_Quant/asincronas)
_sistema/scripts/build.sh <ruta-video> # internally: latexmk -lualatex -interaction=nonstopmode -halt-on-error -outdir="$VIDEO_DIR/build" main.tex, run from presentacion/, then cp build/main.pdf build/presentacion.pdf
_sistema/scripts/render.sh <ruta-video> [dpi] # internally: rm -rf build/paginas, then pdftoppm -png -r ${dpi:-150} build/presentacion.pdf build/paginas/pag. NOT optional: the compile phase blocks without these PNGs
_sistema/scripts/validar.py <ruta-video> [--fase pre|tex|compile|entrega] # the ONLY gate. Runs ALL four phases in order (it does NOT stop at the first failure, despite what _sistema/README.md says), prints per-phase '[✓|✗] fase <n>: N errores, M avisos', ends with 'RESULTADO: OK|FALLO'; exit 1 if any phase has …
_sistema/scripts/resolver_problema.py <V8-ID|ref_origen> # read-only stdlib resolver; requires exactly one manifest id/ref_origen match and exactly one V8 enunciado and solucion file, then prints their paths; exits 2 on missing or ambiguous state
_sistema/scripts/update_hesperides.sh # idempotently re-vendors the canonical $BRAINTEASERS_ROOT/hesperides-beamer-template (override HESPERIDES_SOURCE), including exact images/ synchronization, and records source provenance in _sistema/hesperides/UPSTREAM.md
Normal order for one video: nuevo_video.sh -> build.sh -> render.sh -> validar.py (repeat build/render/validar until OK)
All six scripts are tracked mode 100755 and are invoked directly by path (bash shebang / '#!/usr/bin/env python3'). Python helpers use the stdlib; verify the interpreter available in the current environment.
python3 -m unittest discover -s _sistema/tests -p 'test_*.py' # stdlib contract tests for Hespérides drift and the adversarial delivery gate. There is still no pytest/ruff/mypy/package/CI configuration; validar.py remains the per-video quality gate
```

## Invariantes
- The hyphen, en dash, and em dash are not used as prose separators in delivered text. Mechanically enforced by comun.separadores_tex on main.tex/frames/figures and comun.separadores_markdown on the guion, justification, and session README when present. Commit-message style remains doctrine rather than hook enforcement.
- Videos are never created inside this repo. System changes live here and delivered videos live in the OmarOS output folder, but neither surface is committed or pushed unless Omar explicitly requests it.
- The vault is read-only except for the explicitly authorized video output folder. Course sources, V8, structural Markdown, and the canonical Hespérides template are never modified from this workflow.
- Hespérides is the mandatory presentation base. `_sistema/hesperides/` is not hand-edited; it is synchronized only through update_hesperides.sh from the course's canonical template. Extensions live in `_sistema/estilos/`.
- "`estado: aprobado` en un guion → intocable; cambios a `versions/vNN`." check_pre.py hard-errors on an approved guion.
- "MODO B sin huecos: jamás se reserva ni se marca zona de escritura en la slide." Permanent rule fixed by Omar 2026-07-18. check_entrega enforces the weaker mechanical half only: MODO B must carry CONGELADA and an ESCRIBIR label.
- "Si sobra contenido, se recorta o se divide el vídeo; nunca se acelera la locución. Duración final dentro de ±5 % del objetivo." (MARGEN_DURACION = 0.05, PPM_ERROR_MAX = 175, PPM_AVISO_MAX = 160.)
- Priority: mathematical correctness, fidelity to the course's actual purpose, comprehension, spoken naturalness, audiovisual coordination, time, legibility, and beauty.
- Hespérides governs typography, composition, aspect ratio, and recording configuration. V8 may contribute TikZ craft and semantic figures, but these are adapted to the Hespérides grammar. convenciones §4 forbids muros de texto, generic bullets, slides copying the teleprompter, decorative figures, and putting a whole …
- The semantic colour layer of asincronas.sty has fixed meanings (cDestacado / cDato / cResultado / cError / cSecundario) and "El significado no se intercambia entre vídeos" (convenciones §4).
- Notation comes from estilos/notacion.tex, ported from V8_Apuntes_Definitivos_corregida/latex/styles/macros.tex, and is never redefined inside a frame (convenciones §2).
- Structure is fixed (convenciones §3): one frame per file in presentacion/frames/NN_slug.tex, self-contained TikZ in presentacion/figures/figNN_slug.tex included with \input, and presentacion/main.tex as the single entry point. check_tex hard-errors on any frame or figure written but not included.
- Las reglas completas están en [CLAUDE.md](../CLAUDE.md), especialmente «Jerarquía de fuentes», «Secuencia por vídeo» y «Reglas duras», y en [convenciones](../_sistema/convenciones.md), §§6–11. Se aplican directamente desde esas fuentes; no dependen de un brief generado del hub.

### Route through these

- Para producir o revisar un vídeo, parte de `AGENTS.md` y de las fuentes de dominio enlazadas arriba. Codex ejecuta la secuencia y los controles pertinentes directamente; no requiere una cadena de comandos o agentes de Claude.
- _sistema/scripts/validar.py --fase pre — blocks: malformed session/video path, incomplete guion identity or objective duration, `estado: aprobado`, missing structural Markdown, missing V8 purpose/theory/notation/problem sources, missing canonical Hespérides source, and any byte-level drift between the canonical …
- _sistema/scripts/validar.py --fase tex — blocks: main.tex missing, main.tex not referencing HesperidesQFBeamer, any broken \input/\include/\includegraphics/\usepackage reference (resolved recursively from main.tex with \def macros expanded), any frames/*.tex or figures/*.tex written but never referenced, and …
- _sistema/scripts/validar.py --fase compile — blocks: build/main.log absent, any '! ' LaTeX error, undefined references or citations, 'File ... not found', overfull hbox > 12.0pt, missing build/presentacion.pdf, a 0-page PDF, AND missing build/paginas/*.png or a PNG count different from the PDF page count. Warns (does …
- _sistema/scripts/validar.py --fase entrega — preserves the timing, synchronization, mode, words-per-minute, Spanish, separator, table, and budget checks, scans the guion, justification, and session README, and additionally blocks unless problema_v8 is a real manifest/enunciado/solucion ID or a justified NO_APLICA and …
