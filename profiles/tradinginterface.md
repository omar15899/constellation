# tradinginterface

Raíz: `/Users/omarkhalil/GitHub/tradinginterface`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

tradinginterface (product name: Helix) is the UI tier of QuantOS — a desktop-first, dark-themed, information-dense quantitative trading terminal that puts one surface over the whole constellation: live market data, backtests, Monte Carlo, portfolio/risk, a Trading 212 read/monitor plane, and the research registry, across 19 workspaces driven by a modular grid engine. Perimeter quantos-ui, tier "UI", status substantive in ~/GitHub/.claude/registry/repos.yaml; it sits OUTSIDE the Python Tier 0-3 import graph and reaches the labs over HTTP/WS (frontend) or through a FastAPI backend that editable-imports 18 sibling lab packages (local) / hash-pinned wheels (cloud). Two halves in one repo: a React 18 + TypeScript 5.7 + Vite 6 SPA under src/, and a three-layer FastAPI service under backend/app/ (routers -> services -> bridges) whose HELIX_PROFILE gates which of 21 routers mount (verified: backend/app/routers/ holds 21 .py files).

## Fuentes del dominio

- README.md

- CLAUDE.md

- docs/ARCHITECTURE.md

- docs/STATUS.md

- docs/architecture/BACKEND_LAYERS.md

- docs/architecture/AGENTS.md

- backend/README.md

- docs/architecture/DEPLOYMENT.md

- docs/adr/ADR-LOCAL-0002-shared-store-over-tanstack.md

- docs/adr/ADR-LOCAL-0003-sibling-editable-packaging.md

- docs/adr/ADR-LOCAL-0005-profile-capabilities-plane.md

- docs/refactor/SUBBRANCH_PLANS.md

## Invariantes

- T212 execution freeze. CLAUDE.md:111 — 'backend/app/t212_exec.py and backend/app/routers/t212_exec.py are **frozen**. Never edit them, never weaken T212_DRY_RUN, T212_DISABLE_LIVE_TRADING, or HELIX_T212_EXECUTION_ENABLED, never call the live broker path.' CLAUDE.md:104 — under any non-`full` profile Settings.execution_hard_disabled is True, 'a fifth additive T212 lock that can only disable execution'. The frontend order pane is quarantined in src/workspaces/pies/execution/ behind a freeze notice. Enforced in CI by infra/tests/test_taskdef_guards.py (hard gate in ci.yml and in deploy.yml both pre-plan and pre-apply) and locally by bin/t212-preflight.sh inside bin/verify-backend.sh.

- Sync-by-design market path / EODHD cap. README.md:147 — 'The market-data path is synchronous by design; single-flight caching protects the EODHD vendor cap. Never async-ify it, never run more than one backend replica against the shared usage ledger.'

- `uv run --no-sync` on the backend launch path. CLAUDE.md:90 — '**`--no-sync` is mandatory** — a bare `uv run`/`uv sync` against the shared constellation venv wipes the lab extras and silently degrades the labs.'

- Design tokens only. CLAUDE.md:134 — 'All visual constants are CSS custom properties on `:root` in `src/styles/`. **Never introduce ad-hoc hex/rgba values or pixel sizes in TSX.**' Canvas consumers read them via src/charts/readColors.ts. CLAUDE.md also: source badges (live/internal/sim/rec) always via the CSS variable, never a hardcoded colour; all icons in src/ui/icons.tsx, never inline SVG elsewhere.

- No chart library, ever. CLAUDE.md:24 — 'Hand-coded SVG/canvas kit (`src/charts/`) — no chart library, intentional'; CLAUDE.md:167 — 'No chart library, ever.'

- Barrel-free imports. CLAUDE.md:75-80 — 'Imports are **direct and layer-addressed**. The migration-era compatibility barrels (`src/shell.tsx`, `src/workspaceEngine.tsx`, `src/app.tsx`) are **gone** … Do not reintroduce a barrel; `scripts/ts_nocheck_ratchet.mjs` (run in `npm run typecheck`) fails the build if any file reintroduces `@ts-nocheck`.' Verified: 0 files in src/ contain @ts-nocheck.

- Backend layer direction. CLAUDE.md:96 — 'Three layers: `routers/` → `services/` → `bridges/`; a router never imports another router.' Frontend layer direction is stated in docs/ARCHITECTURE.md:39 (NOT CLAUDE.md) — '`shell → ui · lib`; nothing imports `app`. Layers below never reach up.'

- No window globals. CLAUDE.md:85 — 'The former `window.HX` / `window.HXL` / `window.SlotCtx` globals no longer exist.' Registration goes through the typed module singletons in src/engine/registry.ts via the HX / HXL shims.

- No Redux, no TanStack Query (CLAUDE.md:168, ADR-LOCAL-0002); server state goes through src/lib/store.ts polled stores; Context is confined to the shell/engine.

- Never skip hooks. CLAUDE.md:179 — 'Never skip hooks (`--no-verify`). `playwright_gate.py` runs the `@smoke` Playwright tier on any commit touching `src/`, `index.html`, or `vite.config*`.' NOTE: this gate is currently inert because of the stale TRADING_ROOT (see gotchas) — the rule stands as doctrine, the enforcement does not.

- Granular commits, one logical change each (CLAUDE.md:175 'Adding a pane ≠ adding a tooltip ≠ fixing a CSS variable'); semantic natural messages; CLAUDE.md:181 — 'No AI attribution. No `Co-authored-by`.'

- Never stage secrets. .claude/hooks/pre_commit_gate.py blocks any staged path containing .env, .env.local, .env.production, credentials.json, secrets/, .ssh/, id_rsa, id_ed25519, .pem, .key, or .DS_Store (exit 2 + JSON block decision). Doctrine holds; enforcement is currently broken by the stale TRADING_ROOT.

- CSS is desktop-only. CLAUDE.md:198 — 'CSS: desktop-only. No media queries, no mobile breakpoints.' CLAUDE.md:199 — 'Numbers: always right-aligned in tables, always IBM Plex Mono.' IBM Plex woff2 is self-hosted (src/styles/fonts.css, src/assets/fonts/) — no Google Fonts CDN.

- Endpoints and tests are the contract. README.md:163 — wire envelopes, widget ids and `helix.*` localStorage keys are stable; the pytest OpenAPI snapshot and the Playwright suite pin behaviour. README.md:102 names backend/tests' OpenAPI snapshot + T212 gate proofs as 'the behaviour oracle'.

- backend/pyproject.toml keeps the 18 editable [tool.uv.sources] entries verbatim for local dev; containers consume CI-built hash-pinned wheels from infra/labs.lock (ADR-LOCAL-0003).

- Do not contradict docs/architecture/AGENTS.md, the QuantOS governance binding already in the repo: no client-side authority over execution; staleness visible (`as_of` + freshness on every mirrored panel); failure modes are first-class UI indicators; density floor 9-13px text / 1px hairlines / 4px grid; deterministic rendering (same backend snapshot -> byte-identical UI); no business logic in the client.

## Comandos de referencia

- npm ci

- npm run dev  # vite, :5173

- npm run backend  # cd backend && uv run --no-sync uvicorn app.main:app --reload --port 8000

- npm run dev:all  # npm run dev & npm run backend & wait

- npm run typecheck  # tsc -b --noEmit && node scripts/ts_nocheck_ratchet.mjs

- npm run lint  # eslint src tests/unit

- npm run lint:fix  # eslint src tests/unit --fix

- npm run test:unit  # vitest run

- npm run test:unit:watch  # vitest

- npm test  # playwright test

- npm run test:ui  # playwright test --ui

- npx playwright test --grep @smoke  # commit gate + CI e2e job; backend-free with PW_FORCE_MOCK=1

- npx playwright test --grep @live  # needs the backend up; runs only on the self-hosted runner

- npm run test:all  # npm run typecheck && npm run test:unit && npm run test

- npm run build  # tsc -b && vite build

- npm run build:budget  # node scripts/bundle_budget.mjs dist

- npm run preview  # vite preview

- cd backend && uv run --no-sync pytest -q

- bin/verify-backend.sh  # bin/t212-preflight.sh + ruff check + ruff format --check + pytest -q. The t212 preflight AND pytest both gate the exit code; ruff/format are advisory unless RUFF_STRICT=1

- cd backend && uv run --no-sync ruff check app tests

- cd backend && uv run --no-sync ruff format --check app tests

- make verify  # npm run typecheck ; npx vitest run ; cd backend && uv run --no-sync pytest -q

- make wheels  # infra/scripts/build_lab_wheels.sh

- make requirements-cloud  # cd backend && uv pip compile pyproject.toml --no-sources --find-links ../wheelhouse -c constraints.cloud.txt --python-platform x86_64-unknown-linux-gnu --python-version 3.12 --generate-hashes -o requirements.cloud.txt

- make wheelhouse-push  # aws s3 sync wheelhouse/ $(WHEELHOUSE_BUCKET)/$(LOCK_SHA)/ ; guards on `command -v aws`

- make image  # docker build -f backend/Dockerfile --build-context wheelhouse=wheelhouse -t helix-backend:local .

- make image-frontend  # docker build -f docker/frontend.Dockerfile -t helix-frontend:local .

- make core-up  # docker compose -f infra/compose.yaml --profile core up --build

- make parity-up  # docker compose -f infra/compose.yaml --profile parity up --build

- make publish-artefacts  # runs infra/scripts/publish_artefacts.sh if executable; wave-3 / WP-6, script not present yet

- python3 infra/tests/test_taskdef_guards.py  # fail-closed T212 task-def guard; hard gate in both ci.yml terraform and deploy.yml validate/apply

- uvx ruff@0.15.20 check app tests  # CI backend job, advisory (continue-on-error)

- uvx ruff@0.15.20 format --check app tests  # CI backend job, advisory (continue-on-error)

- uvx mypy app  # CI backend job, advisory (continue-on-error)
