# MMARV1

Raíz: `/Users/omarkhalil/GitHub/MMARV1`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

MMARV1 is a standalone scientific Python library — package name `mmar`, version 2.0.0 — implementing the multifractal formalism: Hölder/singularity spectra, multiplicative cascade models, and the Mandelbrot–Fisher–Calvet Multifractal Model of Asset Returns. It ships nine estimator families behind one interface (wavelet leaders, MF-DFA, MF-DMA, WTMM, structure functions, Chhabra–Jensen, box counting, generalised Hurst, and pointwise h(t)), a closed-form theory oracle every estimator is tested against, a surrogate-based inference layer whose job is to say "no evidence of multifractality" when that is the truth, and content-addressed SHA-256 provenance on every number it produces. In the constellation it sits in the `adjacent` perimeter with `tier: null` and `status: external` — explicitly NOT bound by QuantOS tier discipline, with no .importlinter and no dependency on any QuantOS lab. It is a ground-up v2 rebuild of Omar's thesis code, which is preserved verbatim and importable under `legacy/` so the thesis results stay auditable.

## Fuentes del dominio

- README.md

- docs/ESTIMATOR_GUIDE.md

- docs/KNOWN_LIMITATIONS.md

- docs/LEGACY_AUDIT.md

- docs/MIGRATION.md

- docs/BRANCHES.md

## Invariantes

- One convention carrier, enforced by the types. README: "`ScalingExponents` stores `ζ(q)` and derives `τ = ζ − d` and `h(q) = ζ(q)/q`. A dropped `±1` between the measure and signal conventions is the most common error in this field, and it cannot happen here because there is only one carrier." Do not introduce a second representation of the scaling exponents.

- Provenance roots must be reproducible and must never depend on wall-clock time. README: the `root` is "a SHA-256 over the input digests, every parameter, the RNG seed and the environment — never the wall clock, so reproducibility is *testable*." CI enforces it: two identical `mmar analyze` invocations must yield byte-identical `root`, and `mmar verify` must re-hash a stored run against its manifest.

- Theory anchors must hold exactly, not approximately. CI runs a dedicated job step "theory anchors must hold exactly" (`uv run pytest -m theory -q`); README pins them as "exact to machine precision on `τ(0) = −1`, `τ(1) = 0`, `f(α₀) = 1` and `τ_X(1/H) = 0`."

- mypy runs in strict mode (`[tool.mypy] strict = true`, `warn_unreachable = true`, `disallow_any_generics = true`) and CI runs `uv run mypy` as a blocking gate. Do not add `# type: ignore` to pass; `ignore_missing_imports` is granted only to pywt/matplotlib/pandas/scipy.

- Every measured claim must be produced by running the code, not inferred from reading it. docs/ESTIMATOR_GUIDE.md: "Every number below was **measured**, not quoted from a paper." docs/LEGACY_AUDIT.md: "Every claim below that carries a number was **observed by running the code**, not inferred from reading it." The probes that produced them are preserved at docs/probes/.

- Known defects are recorded, not silently patched or silently tolerated. docs/KNOWN_LIMITATIONS.md exists for "findings reported and deliberately **not** fixed, with the reason" — "written down so they are decisions, not oversights." Its eight entries each name the reproducing test. Fixing one requires updating both the doc and the corresponding strict xfail.

- `legacy/` is frozen v1, preserved verbatim so thesis results remain reproducible. Do not refactor, lint or modernise it.

- Constellation git policy applies (inherited from ~/GitHub/.claude/CLAUDE.md): atomic commits per repo, never bundled across repos; no `--no-verify`; no force-push to main.

## Comandos de referencia

- uv sync --all-extras

- uv run ruff check src tests examples

- uv run ruff format --check src tests examples

- uv run mypy

- uv run pytest -m "not slow" --cov=mmar --cov-report=term-missing --cov-report=xml

- uv run pytest -m theory -q

- uv run pytest -m slow -q

- uv run mmar analyze --estimator mfdfa --q=-3:3:9 --json-out a.json

- uv run mmar analyze --estimator mfdfa --q=-3:3:9 --store artifacts --label ci

- uv run mmar verify artifacts/run-ci.json

- pip install -e ".[full]"
