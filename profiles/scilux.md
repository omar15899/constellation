# Scilux

Raíz: `/Users/omarkhalil/GitHub/Scilux`. Las rutas de este perfil se interpretan desde esa raíz.
Las reglas de dominio se conservan; versiones y comandos se contrastan con los archivos actuales.
La coordinación y publicación usan el único `constellation.py`.

## Identidad

Scilux (scientia + lux) is a multi-agent educational-content engine: one natural-language command in, a production-quality didactic script plus a frame-by-frame TikZ storyboard out, targeted at Manim Community Edition backends and bilingual (EN/ES) high-school-to-undergraduate audiences. It is pure agent infrastructure — 65 Markdown agent specs, 15 skill folders, 20 Python hook scripts (17 of them wired) and a YAML config backbone under config/ — with no application source tree, no package and no build. It runs two pipelines: the 10-phase lesson pipeline (P0 Setup through P9 Assembly & delivery) and an intellectual writing pipeline (notes, essays, formalizations, diagrams), both entered through the semantic-kernel agent. In the constellation it sits in the `adjacent` perimeter with tier=null: it is not bound by QuantOS tier discipline, imports nothing from Shared, and is governed only by its own CLAUDE.md and the user-level contract.

## Fuentes del dominio

- CLAUDE.md

- config/context-registry.yaml

- docs/architecture.md

- docs/audit/2026-04-15-orchestration-playbook-refactor.md

- docs/governance/playbook.schema.json

- docs/governance/agent-response.schema.json

- config/agent-registry.yaml

- config/skill-registry.yaml

- config/hook-registry.yaml

- config/routing-policy.yaml

- config/style-canon.yaml

- docs/operational-manual.md

## Invariantes

- I15 (constitutional). CLAUDE.md states it in two parts of different strength, and the difference matters: the binding clause is "Every user-originated Agent dispatch to a top-level orchestrator must carry a `semantic_kernel_run_id`", followed by the broader doctrine "No skill, orchestrator, or agent may receive raw user language without first passing through `semantic-kernel`." Hook enforcement is the NARROW version only: .claude/hooks/semantic_bypass_guard.py (PreToolUse: Agent) checks the run_id marker, its format, and its freshness ONLY when subagent_type is in GATED = {script-orchestrator, intellectual-orchestrator, input-classifier, review-orchestrator}. Dispatches to any of the other 61 agents are not I15-checked. Do not write "every request is hook-forced through semantic-kernel" — the doctrine says it, the hook does not enforce it.

- I16: every root-level Agent dispatch to a non-infrastructure subagent must be authorised by an active playbook — the prompt must carry `playbook_id`, `playbook_step` and `lesson_id`, the step must exist in workspace/<lesson_id>/playbook.yaml, and its `subagent_type` must match. The exempt set is 8 names, defined as EXEMPT_FROM_I16 in .claude/hooks/lib/playbook.py: semantic-kernel, script-orchestrator, review-orchestrator, intellectual-orchestrator, input-classifier, _probe, git-steward, log-writer. Enforced by .claude/hooks/playbook_guard.py (PreToolUse: Agent) — which is wired in settings.json but MISSING from config/hook-registry.yaml.

- I3 (verbatim): "Every blocking gate fires. No `--skip` argument exists." Operating principle 12: "Never skip a gate. Every invariant has a verifier. No `--skip` flags exist."

- I9 (verbatim): "Every git commit stages specific named files. No wildcards." git-steward does all staging and committing; pre_commit_gate.py verifies (it also blocks any staged path under workspace/ or reference/).

- I11: "review_report.md must be PASS before Phase 9 runs" — release_gate.py (SubagentStop: review-orchestrator) blocks otherwise, and the /export skill independently refuses.

- I10: "Every commit is recorded in logs/${lesson_id}/git_log.md" — post_commit_tracer.py at PostToolUse: Bash(git commit*).

- I12 (verbatim): "Agents write only to their declared paths. reference/ is read-only." CLAUDE.md assigns this to path_guard.py at PreToolUse: Write|Edit, but path_guard.py is NOT wired in settings.json — so I12 has no live hook verifier. The sandbox denyWrite on reference/ and pre_commit_gate.py's FORBIDDEN_PATH_PREFIXES are the only live enforcement.

- I1/I2: no phase is entered without a verified entry contract and no phase advances without a verified exit contract. CLAUDE.md assigns the verifier to script-orchestrator — an AGENT, not a hook, so this is convention-enforced, not gate-enforced. config/context-registry.yaml holds the contracts and is marked "READ FIRST" in the file-layout section.

- I14: the intellectual pipeline entry gate must fire before intellectual-orchestrator dispatches — intellectual_start_gate.py, wired at `SubagentStart: intellectual-orchestrator` (as is start_gate.py for script-orchestrator). No evidence in logs/ that either has fired; treat this enforcement as unverified.

- I6: every definition beat carries all three layers — formal, rigorous intuition, personal intellectual vision. CLAUDE.md: "A lesson that delivers only layer 1 is a catalogue, not a lesson." Enforced by scene-writer + pedagogical-validator (agents, not hooks).

- I7: "Every TikZ frame compiles before it is committed" — tikz_compile_gate.py at SubagentStop: tikz-frame-renderer, which compiles every frame in the sandbox.

- I13: "Every governed document has complete frontmatter before delivery" — knowledge_schema_gate.py at SubagentStop: markdown-knowledge-agent checks for complete VALID frontmatter.

- Commit discipline: one of exactly 15 typed prefixes (brief:/ingest:/pedagogy:/knowledge:/blueprint:/scene:/script:/storyboard:/tikz:/validate:/fix:/config:/agent:/hook:/infra:), subject <= 50 chars, target 30-40 granular commits per lesson, includeCoAuthoredBy=false.

- Style canon (verbatim): the words "clearly," "obviously," "trivially," "it is easy to see" are forbidden in narration — "These words tell a struggling student that they are alone." Enforced NON-BLOCKINGLY by style_monitor.py and intellectual_style_monitor.py (they log to style_warnings.md / style_violations.md; they do not halt).

- config/context-registry.yaml is the single source of paths. Its header states: "Every agent resolves all paths from this file. No hardcoded paths in agent specs."

- workspace/ is ephemeral and never committed (gitignored, and blocked by pre_commit_gate.py); lessons/ holds the committed artefacts.

## Comandos de referencia

- python3 tests/run_all.py

- python3 tests/run_all.py -v
