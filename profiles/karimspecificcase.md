# KarimSpecificCase

Raíz: `/Users/omarkhalil/GitHub/KarimSpecificCase`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

KarimSpecificCase is the ENGIE / Storengy gas-storage operations dashboard — an adjacent-perimeter, untiered client UI that sits outside the QuantOS tier graph entirely. It is a desktop-first, dark-themed, information-dense dashboard authored as two standalone vanilla HTML/CSS/JS files: index.html (Trader + Monitor workspaces, pane engine, hand-coded SVG charts) and monitor.html (the 10-pane Commercial Operations Monitor). registry/repos.yaml classifies it perimeter=adjacent, tier=null, stack=vanilla-web, status=external, role "gas-storage operations monitor (adjacent client UI; sister UI to tradinginterface)", notes "HTML/CSS/JS + Playwright. Not part of QuantOS tier graph." There is no framework, no bundler and no build step — the files served are the files authored — and the only dev-time dependency is @playwright/test, which is intended to gate every UI commit (see gotchas: that gate is currently misconfigured and inert).

## Fuentes del dominio

- CLAUDE.md

- .claude/skills/code-artisan/SKILL.md

- .claude/skills/code-backend-foundation/SKILL.md

- .claude/settings.json

- playwright.config.cjs

- .github/workflows/ci.yml

- .codex/README.md

## Invariantes

- Tier discipline does not apply — registry/repos.yaml records tier: null, perimeter: adjacent, notes 'Not part of QuantOS tier graph.' Do not import or wire QuantOS infrastructure into this repo.

- No framework, no bundler, no build step in the served artefact. CLAUDE.md: 'The served artefact remains vanilla HTML/CSS/JS — no bundler, no build step. The files served are the files authored.'

- Flow semantics are the semantic anchor of the whole UI and must never be inverted. CLAUDE.md: 'Flow semantics (--inj / --wth): always use the CSS variable. Never hardcode the colour. Never invert the mapping (injection is never red).' Enforced by test_flow_semantics_not_inverted_in_css in .claude/tests/test_design_system_invariants.py (verified passing).

- Never introduce ad-hoc hex values or pixel sizes. CLAUDE.md: 'All visual constants are CSS custom properties on :root in each HTML file. Never introduce ad-hoc hex values or pixel sizes. Use the existing variables.' The pre-commit aesthetic checklist adds: sizes/gaps are multiples of 4px (4/8/12/16/24 — 'No 5, 7, 10, 15'); text 9-13px; borders 1px hairlines via var(--hair)/var(--hair-2), no drop shadows; shell heights topbar 56 / ctxbar 32 / statusbar 22 / pane-head 28.

- Feature and spec ship together. CLAUDE.md: 'When adding a feature: add the Playwright spec in the same commit (or an earlier one). A feature without a spec silently rots.' and 'Adding a pane without extending tests/monitor.spec.cjs or tests/index.spec.cjs is incomplete.'

- Never skip hooks. CLAUDE.md: 'Never skip hooks (--no-verify). ... If either blocks, fix the code, don't bypass.'

- Stage explicit paths only. CLAUDE.md: 'Stage explicit paths: git add index.html, git add tests/monitor.spec.cjs. Never git add -A.'

- One logical change per commit, semantic natural messages, no AI attribution and no Co-authored-by trailers. CLAUDE.md: 'Granular: one logical change per commit. Adding a pane != tightening a gap != renaming a token.'

- CSS is desktop-only. CLAUDE.md: 'No media queries, no mobile breakpoints. Portrait vs landscape is handled by the layout engine, not by CSS media queries.'

- Brand colours (--engie-*, --storengy-amber) are reserved for brand surfaces and must not be repurposed for data encoding. CLAUDE.md: 'Do not repurpose them for data encoding.'

- Both test layers are hard gates and neither substitutes for the other. CLAUDE.md: 'Both are hard gates. python3 .claude/tests/run_tests.py covers wiring; Playwright covers runtime behaviour. Neither is a substitute for the other.'

- Codex uses the native profile declared in `.codex/profile.json`. Edit `AGENTS.md` and `.codex/` directly; Claude retains its separate `.claude/` configuration. Do not regenerate a Claude projection over this profile.

## Comandos de referencia

- npm install

- npx playwright install chromium

- npx playwright test

- npx playwright test tests/monitor.spec.cjs

- npx playwright test --ui

- npx playwright test --headed

- npm test  # package.json scripts.test = "playwright test"

- npm run test:ui  # "playwright test --ui"

- npm run test:headed  # "playwright test --headed"

- npm run serve  # "python3 -m http.server 5199 --bind 127.0.0.1" — the TEST port, not the dev port

- python3 .claude/tests/run_tests.py  # .claude meta-test suite; verified 14 tests, all pass; also the CI step

- python3 -m http.server 5173 --bind 127.0.0.1  # dev server, CLAUDE.md line 62

- python3 .claude/hooks/dev_server.py < /dev/null  # what /serve start runs

## GS Trading Interface: contrato obligatorio de edición


Antes de modificar `GS_trading_interface.html`, lee el [README](README.md#contrato-permanente-plug-and-play) y [GS_INTERFACE.md](GS_INTERFACE.md#sustituir-en-el-backend). El resultado debe seguir siendo un único HTML que sustituya al anterior sin modificar el backend. Conserva conexiones, endpoints, métodos, payloads, unidades, autenticación/CSRF, inyección `__RAW__`, nonce, API pública y persistencia del modo conectado. No añadas dependencias de ejecución ni archivos que deban desplegarse junto al HTML. El modo demo permanece explícito, aislado y sin llamadas API.

Mejora activamente estructura, rendimiento y fiabilidad; refactoriza los mecanismos internos cuando aporte valor, conservando ese contrato y el significado de los datos. Una mejora de interfaz no autoriza una migración de backend: cualquier cambio del contrato requiere un encargo explícito de Omar. Preserva el aspecto salvo petición contraria. Acompaña los cambios funcionales con pruebas relevantes en `tests/gs-interface.spec.cjs`, comprueba regresiones, conservación del estado y liberación de recursos, y verifica la interfaz en navegador antes de publicar. Documenta cualquier límite real de compatibilidad; las pruebas con mocks no equivalen a una validación contra el servidor productivo.

