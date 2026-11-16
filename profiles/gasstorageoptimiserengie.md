# GasStorageOptimiserEngie

Raíz: `/Users/omarkhalil/GitHub/GasStorageOptimiserEngie`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

GasStorageOptimiserEngie is a standalone private repo (github.com/omar15899/GasStorageOptimiserEngie) holding the ENGIE `rollint` engine — daily rolling-intrinsic valuation and hedging of a UK NBP gas storage contract — reconstructed from 93 photographs of the ENGIE source, plus the line of work built on top of it. It carries two side-by-side trees under src/: `rollint_original/` (10 files: 9 transcribed modules plus a marked constants.py; FROZEN, digest-protected, never edited) and `rollint/` (the working line, which starts as a faithful copy and improves from there); both import, so improvements are measured against a live baseline rather than argued. The economics live in a 209-line Pyomo AbstractModel (src/rollint/models/ReferenceModel.py) solved daily via HiGHS/appsi. It is independent of QuantOS tier discipline. AGENTS.md and the native .codex/ profile define its Codex integration; CLAUDE.md preserves the technical rules for Claude without a local .claude/ harness. Its long-form mathematics and improvement doctrine are canonical in the OmarOS vault at ~/OmarOS/06_Knowledge_Base/Mathematics/Finance/ENGIE/ (Gas_Storage_Rolling_Intrinsic/ for the manual, Evolucion_Rolling_Intrinsic/ for the fourteen-stage route), read-only from here.

## Fuentes del dominio

- CLAUDE.md

- README.md

- provenance/README.md

- provenance/PHOTO_MANIFEST.md

- docs/GUIA_DEL_CODIGO.md

- docs/evolucion/README.md

- src/rollint/models/ReferenceModel.py

## Invariantes

- "**`src/rollint_original/` is never edited.** Not to fix a bug, not to satisfy ruff or mypy, not to add a docstring, not to reformat." (CLAUDE.md §The one rule, verified verbatim). It is the only baseline that exists — the original codebase is on an ENGIE machine we do not have. Enforced by .githooks/pre-commit and tools/verify_original.py.

- "Change `src/rollint/`, never `src/rollint_original/`." (CLAUDE.md §How work happens here, 1 — verbatim)

- "`diff -r src/rollint_original src/rollint` must, at any moment, be a list you can defend line by line. If a diff hunk has no reason, it is a regression." (CLAUDE.md §How work happens here, 2 — verbatim)

- "A fix to a defect in the original is a separate commit from a refactor. Say which defect, and how you know it was one — a failing case beats an argument." (CLAUDE.md §How work happens here, 3 — verbatim)

- "`PYTHONPATH=src:tools/stubs python tools/smoke_check.py` must stay green." (CLAUDE.md §How work happens here, 4 — verbatim). NOTE FOR THE AGENT: the intent is binding, but that literal command fails from a cold shell; run it as `PYTHONPATH=src:tools/stubs .venv/bin/python tools/smoke_check.py`.

- "There are no tests beyond `tools/smoke_check.py`. Do not report a change as verified on the strength of the tree importing." (CLAUDE.md §What you cannot verify here — verbatim)

- "Nothing that touches Mercure or the market discount curve can be executed outside ENGIE, so claims about those paths are static reasoning and must be labelled as such." (CLAUDE.md §What you cannot verify here — verbatim)

- "Anything in `src/rollint/` that is *not* in the photographs carries a marker in the file saying so ... Keep those markers. When a gap is closed by a new photograph, update `provenance/PHOTO_MANIFEST.md` in the same commit." (CLAUDE.md §Provenance discipline — verified)

- "Use `tools/original_engine.original_rollint()` for any behavioural comparison" — importing rollint_original.* directly silently borrows the working calendar. (CLAUDE.md §Comparing the two engines — verified, and the three absolute-name imports were confirmed in the frozen tree)

- Deliberate re-transcription is the ONLY authorised path through the guard: commit with `--no-verify`, then regenerate digests with `tools/verify_original.py --write`, "saying in the message which photographs changed." (CLAUDE.md §The one rule — verbatim; the same escape hatch is documented in .githooks/pre-commit)

- The vault is canonical and never written from here: "El vault es canónico y **no se toca desde aquí**: es la matemática y la doctrina." (docs/evolucion/README.md preamble — verified verbatim)

- Honesty rules inherited from the vault (docs/evolucion/README.md §7, verified verbatim): every quantitative claim is exactly one of (a) a number with cited provenance, (b) a result derivable by hand, or (c) a reasoned estimate labelled as such. "**Nunca se inventan benchmarks ni tiempos.**" When something is not measured, write that it is not measured and describe the experiment that would measure it. Plus L-1 no maxima over configurations, L-2 every delta with its standard error (|Δ|/SE < 2 means indistinguishable from zero), L-3 no interpolating between fixtures.

- `src/rollint/calendar/` is ours, not ENGIE's, and has no counterpart in the frozen tree — a diff there is expected, not a regression. (CLAUDE.md §Provenance discipline)

## Comandos de referencia

- PYTHONPATH=src:tools/stubs .venv/bin/python tools/smoke_check.py    # THE only test surface; verified green ('all checks passed'). MUST use .venv/bin/python — see gotchas

- PYTHONPATH=src:tools/stubs uv run --no-sync python tools/smoke_check.py    # equivalent verified form; --no-sync is MANDATORY (bare `uv run` mutates the venv)

- python tools/verify_original.py    # verified exit 0, 'src/rollint_original/ intact — 10 files match SHA256SUMS'. Stdlib-only, so bare `python` genuinely works for THIS script

- python tools/verify_original.py --write    # regenerate provenance/SHA256SUMS, ONLY when deliberately re-transcribing

- PYTHONPATH=src:tools/stubs:. .venv/bin/python tools/compare_engines.py    # verified: 'compared 30 quantities ... the two engines agree exactly'. Needs repo root (`.`) on the path

- PYTHONPATH=src:tools/stubs .venv/bin/python tools/original_engine.py    # verified; demonstrates the scoped `rollint` name swap. The README's form (`python tools/original_engine.py`) is WRONG and crashes — see gotchas

- diff -r src/rollint_original src/rollint    # the full list of what the working line has changed

- git config core.hooksPath .githooks    # enable the frozen-tree pre-commit guard, once per clone (ALREADY set in this clone)

- NO test command: no pytest suite, no tests/ dir, no test_*.py, no conftest.py anywhere. tools/smoke_check.py is the entire test surface

- NO lint command runnable: pyproject has only [tool.ruff] line-length = 100 — no invocation in any config, no Makefile, no CI, and ruff is NOT installed

- NO typecheck command runnable: pyproject has only [tool.mypy] python_version = "3.11", ignore_missing_imports = true — no invocation anywhere, and mypy is NOT installed

- Build backend: hatchling; [tool.hatch.build.targets.wheel] packages = ["src/rollint"] (no build script, no Makefile, no CI workflow exists)
