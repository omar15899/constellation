# Isomorph Synth — Generation Protocol (authoritative)

This file specifies the exact shape of the output artefact. The 6-section ordering and heading spelling are load-bearing: the materializer and validator scripts parse them, and a downstream AI picking up the artefact to continue work uses them as stable landmarks.

---

## Top-level skeleton

```markdown
# 1. Assumptions
# 2. Generated folder structure
# 3. File contents
# 4. Adaptation points
# 5. Integration notes
# 6. Reintegration map
```

No other top-level headings. Ever. Subsections use `##` and below.

---

## Section 1 — Assumptions

Everything the spec did not fully pin down, enumerated explicitly. The reader must be able to scan this section and immediately know what decisions the scaffold has baked in that they may want to contest.

Use a bulleted list; each bullet has the following micro-shape:

```
- **<category>**: <chosen value or default>. <One sentence of why — which spec signal supported this, or which default rule applied.>
```

Typical categories:

- **Stack / runtime** (`Python 3.11`, `Node 20`, `Go 1.22`, etc.).
- **Package manager / build tool** (`uv`, `poetry`, `pnpm`, `cargo`).
- **Test framework** (`pytest`, `vitest`, `go test`).
- **Concrete library for a generic role** — e.g. "HTTP client: `httpx`" when the spec said "dependency on an HTTP client".
- **Storage backend for a generic integration point** — e.g. "`Database_OperationalStore` implemented locally as SQLite; swap for the real DB at reintegration time."
- **Observability backend** — e.g. "`stdout` / `logging` module; swap for the firm's observability stack at reintegration time."
- **Any free parameter the spec marked as non-preserved** — e.g. "calibration regulariser left at 1e-3; re-tune at reintegration time."

If the spec is already explicit about a category, do **not** re-state it in this section; only the genuine assumptions go here.

---

## Section 2 — Generated folder structure

A fenced tree block showing the final layout, top-down. Use the conventional Unicode tree glyphs or ASCII — consistency matters more than the choice. Example shape:

````markdown
```text
<project-slug>/
├── pyproject.toml
├── README.md
├── src/
│   └── <package_root>/
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── entities.py
│       │   └── value_objects.py
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   └── adapters/
│       │       ├── __init__.py
│       │       ├── <integration_role>_adapter.py
│       │       └── ...
│       ├── interfaces/
│       │   ├── __init__.py
│       │   └── <component_role>_interface.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py
│       └── pipeline.py
├── tests/
│   ├── __init__.py
│   ├── test_<module>.py
│   └── ...
└── .env.example
```
````

Every entry that appears in the tree **must** have matching contents in Section 3 (or be a directory / `__init__.py` stub, which may be elided in Section 3 if empty). The validator enforces this.

If the scaffold is intentionally small (fewer than ~10 files), still draw the tree; don't skip it.

---

## Section 3 — File contents

For every file in Section 2 that has meaningful content, emit a subsection with exactly this shape:

````markdown
## <relative/path/to/file.ext>

```<language-tag>
<file content>
```
````

Rules:

- `<relative/path/to/file.ext>` is the path as it appears in the tree — copy-pastable.
- `<language-tag>` uses the canonical Markdown fence tag (`python`, `typescript`, `toml`, `yaml`, `json`, `bash`, `tsx`, `sql`, `rust`, `go`, `javascript`, `dockerfile`, `makefile`, `text`). The materializer script uses the path extension, not the tag, but humans and syntax highlighters use the tag.
- Order files by reading-order. Start with the top-level manifest (`pyproject.toml`, `package.json`, `Cargo.toml`, …), then `README.md` if one is produced, then the domain layer, then infrastructure, then interfaces, then pipeline / entry point, then configuration, then `.env.example` and fixtures, then tests.
- Empty `__init__.py` files can be elided. Non-empty ones must be included.
- Keep files **coherent**: imports in one file refer to symbols defined in another file in the same artefact, not to invented modules.

### File-content conventions

Inside each file:

- **Typed signatures wherever the language supports them** (Python with type hints, TypeScript with `type`/`interface`, Go with interfaces). Signatures are the contract; contracts are the reintegration surface.
- **Docstrings / doc-comments on every public interface**, explaining the role (one sentence) and any invariants the caller must honour (short bullet list if non-trivial).
- **Adaptation markers** inline at the exact point where a private binding will happen — see `adaptation_markers.md` for the vocabulary.
- **No TODO / FIXME** without a matching labelled adaptation marker. The validator flags bare TODOs.
- **Reasonable default implementations** that make the scaffold runnable on synthetic inputs. `raise NotImplementedError` is a last-resort marker for cases where no generic default is possible; every such raise must be adjacent to a labelled `ADAPTATION POINT` comment explaining what the private implementation must do.

---

## Section 4 — Adaptation points

An enumeration of every marker emitted in Section 3, in order of appearance. Do not paraphrase — quote the surrounding name (function / class / file) so the reader can locate it.

Shape:

```markdown
- **<marker-kind>** in `<file>:<symbol>` — <one-sentence description of what the user must supply, what the contract is>.
```

Example:

```markdown
- **USER-INTEGRATION REQUIRED** in `src/pkg/infrastructure/adapters/market_data_adapter.py:MarketDataAdapter.fetch_observations` — connect to the firm's real market-data vendor client; the adapter must return a `DataFrame` matching the `RawObservations` schema and tolerate transient 5xx without propagating them.
- **ADAPTATION POINT** in `src/pkg/domain/valuation.py:compute_closed_form_valuation` — replace the generic Black–Scholes implementation with the proprietary pricing formula; input/output types must remain unchanged.
- **PROJECT-SPECIFIC IMPLEMENTATION GOES HERE** in `src/pkg/config/settings.py:Settings.observability_backend` — bind the observability export to the firm's sink; the current implementation writes to the Python `logging` module.
```

The count of adaptation points must match the count of markers in Section 3. The validator checks this. Every marker in this section must also appear in the Reintegration Map (Section 6).

---

## Section 5 — Integration notes

Prose notes — short, no more than half a page — covering:

- How the scaffold is built / run / tested (the canonical three commands for the chosen stack: install, run, test).
- Any environment setup needed before the scaffold can run (Python version, Node version, an SDK to install, a local DB to start).
- Any known-fragile edges in the generic implementation the user should be aware of (e.g. "the Kalman filter implementation uses SciPy's dense matrix path; at production scale the firm should swap to a sparse formulation").
- How to extend the scaffold with new components without breaking the existing contracts.

Do not repeat content from the Reintegration Map here. Section 5 is about using the scaffold; Section 6 is about binding it to a private system.

---

## Section 6 — Reintegration map

A table. One row per adaptation point, in the same order as Section 4.

```markdown
| # | Marker | Location | What must be replaced | What private system / contract it binds to | What must remain true after binding |
|---|--------|----------|-----------------------|----------------------------------------------|-------------------------------------|
| 1 | USER-INTEGRATION REQUIRED | `src/pkg/infrastructure/adapters/market_data_adapter.py:MarketDataAdapter.fetch_observations` | the stub HTTP fetcher | the firm's real market-data vendor SDK | the returned `DataFrame` must match the `RawObservations` schema defined in `src/pkg/domain/schemas.py` |
| 2 | ADAPTATION POINT | `src/pkg/domain/valuation.py:compute_closed_form_valuation` | the generic Black–Scholes body | the firm's proprietary valuation routine | the function signature and output shape must remain unchanged so the existing tests still pass |
| 3 | ... | ... | ... | ... | ... |
```

Every row must have all six columns filled. The rightmost column ("what must remain true after binding") is the most load-bearing and most frequently skimped — it is the contract that lets the downstream binder preserve test-suite coverage, so write it carefully.

---

## Summary checklist before returning

- [ ] All six top-level headings present, spelled exactly, in order.
- [ ] Section 1 has at least one assumption (or an explicit `_none — the spec pinned every decision_` when genuinely nothing is under-specified).
- [ ] Section 2's tree matches Section 3's file list exactly.
- [ ] Every non-trivial file has typed signatures on public interfaces.
- [ ] Every TODO-like comment is a labelled adaptation marker.
- [ ] Section 4's marker list matches the inline markers in Section 3, in order.
- [ ] Section 5 names the three canonical commands (install, run, test).
- [ ] Section 6 has the same number of rows as Section 4 has entries, with all six columns populated.
- [ ] No verbatim content borrowed from a real codebase; every specific is either generic by construction or marked as an adaptation point.
