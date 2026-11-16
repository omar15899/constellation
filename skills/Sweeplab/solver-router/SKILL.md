---
name: solver-router
description: Classify any SweepLab request into a routing class and return a structured routing decision with entry point, agent sequence, and suggested command — without executing anything. Use this skill whenever /route is invoked, whenever you need to inspect routing before acting, or whenever the orchestrator needs to classify an ambiguous free-form request. Also trigger when the user asks "what would happen if I asked X" or "how would this be routed".
---

# Solver Router — Intent Classification

Classify the request and return a routing decision. Do not execute anything. Do not write files. Return the structured block below and stop.

## Routing taxonomy

Apply criteria top-to-bottom; first match wins.

### PIPELINE
- Entry point: `orchestrator`
- Math-first: yes
- When: request involves a new PDE, physical model, or constraint formulation; requires both mathematical analysis AND implementation; spans pde-intake → formulation → case → tests
- Examples: "implement a heat equation solver", "add a new American option method", "build a Burgers equation case"
- Mandatory sequence: `pde-intake → formulation-architect → solver-strategist → case-builder`

### SPECIALIST
- Entry point: the matching specialist skill or agent
- Math-first: no
- When: maps clearly to exactly one domain; no cross-domain coordination; output is narrow (a document, a test, an analysis)
- Examples: "analyze the output of this run", "write a convergence test", "derive the weak form", "update the investigation log"

### REASONING
- Entry point: `direct` (in-session, no agent spawned)
- Math-first: no
- When: no file modifications expected; answerable from code reading + reasoning; user asks why/how/explain/what
- Examples: "why does VI outperform penalty?", "explain the Snell envelope", "what does the epsilon convergence order mean?"

### MIXED
- Entry point: `orchestrator`
- Math-first: yes
- When: requires diagnosis + implementation; spans multiple components; user asks for both explanation AND fix
- Examples: "investigate why the put price is wrong and fix it", "explain the SDC sweep paths and then refactor them"

### OPERATIONAL
- Entry point: `direct`
- Math-first: no
- When: single concrete action completable in one tool call; no analysis, no architecture decisions
- Examples: "run the quick profile", "git status", "show last 5 commits"

## Decision rules

1. Any request touching a PDE → at minimum MIXED
2. If ambiguous between PIPELINE and MIXED: choose PIPELINE if any new file will be created
3. Never downgrade PIPELINE to OPERATIONAL to save steps
4. If genuinely uncertain: escalate to orchestrator (safe default)

## Output — always this exact format

```
ROUTING DECISION
================
Request:        <one-line summary of the request>
Class:          <PIPELINE | SPECIALIST | REASONING | MIXED | OPERATIONAL>
Entry point:    <agent-id | skill-name | direct>
Agent sequence: <[pde-intake, formulation-architect, ...] or N/A>
Math-first:     <yes | no>
Rationale:      <one sentence>
Suggested cmd:  </command-name or N/A>
Will proceed:   <yes — system acts immediately | no — user confirmation needed>
```

No prose before or after the block.
