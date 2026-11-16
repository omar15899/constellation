---
name: study-report-pipeline
description: Enforces the canonical Study -> Report -> Manifest pipeline for ResearchLab. Use this skill whenever an agent is about to scaffold a study, render a report from a manifest, write or update a manifest.json, verify a study's provenance chain, or judge whether a regeneration is deterministic. The skill loads the doctrine from research_pipelines/{studies,reports,provenance,reproducibility,figures_and_tables}.md and binds it to the on-disk layout under outputs/<study>/<ts>/. Do NOT invoke for free-form research prose (use scholar), for ADRs (use decision-logger), or for evaluator engine code (BacktestLab / MonteCarloLab own that).
license: Proprietary. OmarOS internal.
contract_invariants:
  - "Read first, write second. Never write a manifest, report, or scaffold without first reading config.yaml, the relevant research_pipelines/* chapter, and any existing manifest.json on disk."
  - "Deterministic regeneration is the central invariant. Same (code_commit, dataset_version_hash, config_hash, seed_pack) -> bit-identical audit_dag_root and bit-identical report.md (modulo a documented timestamp non-determinism floor)."
  - "Five-link lineage chain mandatory. code_commit -> dataset_version_hash -> config_hash -> audit_dag_root -> artefact_hashes. Every link content-addressed via BLAKE3 over a canonical encoding (Cap'n Proto for binary, sorted-key UTF-8 JSON for text)."
  - "as_of_decision_time is part of the config. A config that does not pin it is invalid; refuse to scaffold or run."
  - "Two-numbers rule for backtest studies. Reports of kind single_strategy_backtest or cost_robustness must quote a Sharpe under 3x the calibrated cost in addition to the headline Sharpe."
  - "Definition of Done gate. Reports that fail any of the six DoD checks (data sources stated, model and code versions stated, assumptions stated, conclusions explicit, limitations explicit, output committed or archived) are not Done."
  - "outputs/ is gitignored. Study artefacts are runtime state, not source. Never commit outputs/<study>/<ts>/."
  - "Idempotence at the registry. A second registry write with the same run_id (= audit_dag_root) is a no-op. Records are append-only; never deleted."
  - "AI-authored reports are not evidence on their own. A pure-AI-authored report without a human reviewer carries ai_reviewed: false; a study published without ai_reviewed: true is opinion, not evidence."
  - "Falsifiability is a precondition. A study cannot run against a hypothesis whose falsifiability statement does not name a metric, threshold, and horizon."
  - "Cross-references are explicit. Every artefact (manifest, report, registry entry) cross-references the research_pipelines/* chapter that governs it."
---

# Study -> Report -> Manifest Pipeline

The canonical pipeline that ResearchLab owns. Loaded by the orchestrator and the seven specialist agents (research-intake, research-router, experiment-orchestrator, study-architect, report-generator, provenance-engineer, hypothesis-curator, registry-keeper).

The substantive doctrine lives in the QuantOS corpus at
`~/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/`.
This skill loads that doctrine; the doctrine enforces the contract.

---

## When to invoke this skill

- Scaffolding a new study under `outputs/<study>/<ts>/`.
- Rendering or regenerating a `report.md` from a manifest.
- Writing or updating a `manifest.json`.
- Verifying a study's provenance chain.
- Judging whether two runs are deterministic-equivalent.
- Filing a hypothesis or a registry record that touches a study.

Do **not** invoke this skill for:

- Free-form research prose (scholar).
- ADRs (decision-logger).
- Evaluator engine code (lives in BacktestLab / MonteCarloLab).
- Vault content outside the QuantOS Research Pipelines subcorpus.

---

## The canonical layout

```
outputs/
  <study_name>/
    <ISO-8601 timestamp>/
      config.yaml              # the single source of truth for the run
      manifest.json            # provenance + result hashes
      provenance.json          # lineage links, as_of_decision_time
      data/                    # intermediate artefacts
      figures/                 # PNG (or SVG) outputs
      tables/                  # MD / CSV outputs
      report.md                # rendered from manifest + figures + tables
  registry/
    experiments.jsonl          # append-only registry log
    hypotheses/<H-XXXX>.yaml   # one file per hypothesis
    index/                     # derived caches
```

Source on disk: `research_pipelines/studies.md` section 1.

---

## The protocol

### Stage 1 -- Read

Before any action:

1. `~/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/index.md` -- the corpus map.
2. `studies.md` -- study layout, regeneration pipeline, lineage, two-number rule.
3. `provenance.md` -- manifest schema, lineage walk.
4. `reproducibility.md` -- R1-R4 conditions, replay procedure.
5. `reports.md` -- report template, DoD gate, naming.
6. `figures_and_tables.md` -- artefact rules, non-determinism floor.
7. The existing study directory if it exists.

If a request implies a divergence from doctrine, surface the contradiction; do not silently override.

### Stage 2 -- Decide

Identify the operation: `scaffold`, `dispatch`, `manifest-write`, `report-render`, `verify`, `register`. Each operation has one canonical agent (see `.claude/agents/`).

### Stage 3 -- Act

Each agent operates within its narrow contract:

- **study-architect** -- writes the directory and templates only; no hashes.
- **experiment-orchestrator** -- composes (H, D, F, model_class) and dispatches; never imports evaluator engine code.
- **provenance-engineer** -- computes BLAKE3 hashes, writes manifest.json; never modifies artefacts.
- **report-generator** -- renders report.md from manifest + figures + tables; never invents metrics; deterministic.
- **registry-keeper** -- appends to experiments.jsonl; idempotent on run_id.
- **hypothesis-curator** -- validates falsifiability; allocates ids monotonically.
- **research-intake** / **research-router** -- read-only classification.

### Stage 4 -- Verify

Before declaring an operation complete:

- Lineage chain: every link present and well-formed.
- Determinism: hash-by-hash check that re-running the same operation produces the same bytes (where applicable).
- DoD gate: for reports, all six DoD checks pass.
- Two-numbers rule: for BT-kind studies, the second Sharpe is in the manifest.
- Idempotence: re-running the operation produces zero side effects (no extra registry rows, no new bytes in artefacts).

### Stage 5 -- Cross-link

Every artefact cross-references its governing chapter:

- Manifest: footer cross-link to `research_pipelines/provenance.md` section 2.
- Report: lineage walk section cross-links to `research_pipelines/reports.md` section 2.
- Registry record: cross-link to the manifest path.
- Vault mirror (when published): `[[Documentation/research_pipelines/index]]`.

---

## The five-link lineage chain (research_pipelines/provenance.md section 1)

```
code_commit
  v
dataset_version_hash
  v
config_hash
  v
audit_dag_root
  v
artefact_hashes
```

Verification is one BLAKE3 comparison per link. A mismatch on (1)-(3) is a manifest defect; on (4) a determinism defect (P0).

---

## The DoD gate (research_pipelines/reports.md section 4)

Refuse to ship a report unless every box is checked:

1. Data sources stated.
2. Model and code versions stated.
3. Assumptions stated.
4. Conclusions explicit (no `<TODO -- author>` markers).
5. Limitations explicit (>= 3 bullets).
6. Output committed or archived.

---

## The two-numbers rule (research_pipelines/reports.md section 5)

For BT studies, every report quotes:

- The headline Sharpe under the calibrated cost assumption.
- A robustness Sharpe under 3x the calibrated cost.

A report with one Sharpe is rejected at review.

---

## Failure modes

**Guarded.**

- Missing `as_of_decision_time` -> refuse at scaffold time.
- Mismatched artefact hash -> refuse at verify time.
- Audit root non-reproduction -> P0.
- Missing falsifiability -> hypothesis-curator refuses.

**Surface, do not paper over.**

- Vendor archive deletion (dataset hash unresolvable) -> mark study `UNVERIFIABLE`; do not silently fix.
- Cross-backend determinism gap -> document the backend; do not pretend bitwise equivalence.
- AI-only authorship without human review -> `ai_reviewed: false`; not evidence.

---

## Cross-references

- `~/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/index.md`
- `~/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/studies.md`
- `~/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/reports.md`
- `~/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/provenance.md`
- `~/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/reproducibility.md`
- `~/OmarOS/05_Projects/QuantOS/Documentation/research_pipelines/figures_and_tables.md`
- ADRs: ADR-0014 (tritemporal), ADR-0023 (BLAKE3 audit), ADR-0032 section C (reporting-engine-as-package).
- Sibling skill: `scholar-quant-docs` (corpus voice for documentation).
