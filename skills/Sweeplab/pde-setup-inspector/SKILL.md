---
name: pde-setup-inspector
description: Systematic audit of the SweepLab .claude/ infrastructure — evaluates hook wiring, agent roster, command completeness, registry coherence, invariant coverage, and CLAUDE.md consistency. Outputs a structured report with PASS/WARN/FAIL per component and prioritised improvement proposals. Use when /review-setup is invoked, when something in the infrastructure feels broken, or for periodic health checks. Read-only — never modifies files.
---

# PDE Setup Inspector

Audit the SweepLab `.claude/` infrastructure systematically. Work through six layers in order. For each item assign **PASS**, **WARN**, or **FAIL**. Produce a self-contained report that is actionable without additional context.

You are read-only. Do not edit, write, or create any file.

The layer-by-layer audit protocol is in `references/audit-layers.md` — read it before starting.

## Output format

```
# SweepLab Setup Review — YYYY-MM-DD

## Summary
<3–5 sentences: overall health, top issues>

## Layer 1 — Hook Wiring
<table + findings>

## Layer 2 — Agent Roster
<table + findings>

## Layer 3 — Command Completeness
<table + findings>

## Layer 4 — Registry Consistency
<findings or "cross-references clean">

## Layer 5 — Invariant Coverage
<table + gap list>

## Layer 6 — CLAUDE.md Consistency
<per-section status>

## Prioritised Improvement Proposals

### P1 — Critical (blocks operation)
1. [specific file, what change, why critical]

### P2 — Important (reduces ambiguity or coverage)
1. [specific file, what change, why]

### P3 — Nice to have
1. [specific file, what change]
```

Keep tables concise. Use abbreviations in column headers if needed. When in doubt about intent, use `CLAUDE.md §1` (Project Identity) as ground truth.
