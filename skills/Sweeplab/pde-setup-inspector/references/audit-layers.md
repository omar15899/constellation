# Setup Inspector — Audit Layer Protocol

Six layers, worked in order. Each item: PASS / WARN / FAIL.

---

## Layer 1 — settings.json Hook Wiring

Read `.claude/settings.json`. For every hook in `.claude/registry/hooks.yaml`:
1. Does the hook file exist on disk?
2. Is it wired under the correct event (SessionStart / PreToolUse / PostToolUse / UserPromptSubmit / PostToolUseFailure)?
3. Does the matcher (if any) correctly target the intended tool call pattern?
4. Is the timeout appropriate?

Report: table of hook → event → wired (yes/no) → timeout → status.

---

## Layer 2 — Agent Roster Coherence

Read `.claude/registry/agents.yaml` and every `.claude/agents/<id>.md`.

For each registered agent:
1. Does the .md file exist?
2. Does the role in YAML match the agent's self-description?
3. Are `writes_to` directories correct?
4. Are `triggers` specific and actionable?
5. Is the `mandatory` flag correctly set?

Additionally:
6. Capability gaps — any user request type no agent handles?
7. Overlapping roles — any two agents with significantly overlapping scope?

Report: table of agent → file_exists → role_match → writes_to_correct → triggers_clear.

---

## Layer 3 — Command Completeness

Read `.claude/registry/commands.yaml` and every `.claude/commands/<id>.md`.

For each registered command:
1. Does the .md file exist?
2. Is `routing_class` correct (PIPELINE / SPECIALIST / REASONING / MIXED / OPERATIONAL)?
3. Is `entry_point` the correct agent or "direct"?
4. Are `mandatory_agents` accurate?
5. Is the workflow clearly described?

Additionally:
6. Is there a command for every major user need in CLAUDE.md? List missing.
7. Any redundant or overly similar commands?

Report: table of command → file_exists → routing_class → entry_point → workflow_clear → status.

---

## Layer 4 — Registry Internal Consistency

Read all five registry YAMLs:
- `.claude/registry/agents.yaml`
- `.claude/registry/commands.yaml`
- `.claude/registry/hooks.yaml`
- `.claude/registry/intent_taxonomy.yaml`
- `.claude/registry/capabilities.yaml`

Check:
1. Every agent in `commands.yaml` mandatory_agents exists in `agents.yaml`.
2. Every routing_class in `commands.yaml` exists in `intent_taxonomy.yaml`.
3. Every hook in `hooks.yaml` has a matching settings.json entry.
4. `capabilities.yaml` accurately reflects what the system can actually do.
5. Examples in `intent_taxonomy.yaml` route to the correct class.

Report: cross-reference issues found, or "cross-references clean".

---

## Layer 5 — Invariant Coverage

Read all `.claude/tests/invariants/I*.py` files.

For each invariant: what does it check? Is the check complete? What's not covered?

Confirm the following are validated by some invariant:
- All hook files exist
- All agent files exist
- All command files exist
- settings.json is valid JSON
- venv is reachable
- SOLVER_ROOT is correct
- docs/ directories exist
- Git hooks are installed
- sdc_gate module is present

Report: table of invariant → what_it_checks → complete (yes/partial/no) → gaps.

---

## Layer 6 — CLAUDE.md Consistency

Read CLAUDE.md (both root `~/CLAUDE.md` and project-level). Check:
1. §3 Agent Pipeline — roster table matches `agents.yaml`?
2. §3 Key Commands — command table matches `commands.yaml`?
3. §5 Numerical Invariants — same 7 invariants as in `tests/test_bs_american.py`?
4. §6 American Option Methods — matches `cases/bs_greeks_american.py`?
5. §15 Meta-Routing — taxonomy matches `intent_taxonomy.yaml`?
6. §16 SDC-First — `src/sdc_gate.py` exists?
7. Any CLAUDE.md sections describing things that no longer exist, or missing sections for things that do?

Report: per-section status, specific mismatches.
