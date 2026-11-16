---
name: md-grapher
description: Produce high-quality Markdown visualisations — Mermaid diagrams, structured tables, conceptual maps, and ASCII art — embedded in Obsidian vault notes. Use this skill when the user says "create a diagram", "draw a flowchart", "Mermaid chart", "concept map", "make a table comparing X and Y", "process diagram", "state machine diagram", "sequence diagram", "mind map", "ASCII diagram", "visualise this pipeline", "show the relationship between X and Y", "crea un diagrama", "dibuja un flujo". Produces Mermaid fenced code blocks (flowchart, graph, sequence, mindmap, classDiagram, stateDiagram), structured markdown tables, and inline ASCII art. Uses Obsidian callout syntax for definition/theorem/example/warning boxes. For anything requiring mathematical precision destined for LaTeX output, use latex-tikz-specialist instead. Do NOT trigger for TikZ/LaTeX figures (latex-tikz-specialist), for writing note prose (writer skills), or for Dataview dashboard queries (dashboard-builder).
license: Proprietary. OmarOS internal.
---

# Markdown Grapher

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Responsible for visualisations inside vault markdown files. Uses Mermaid (which Obsidian renders natively), structured tables, ASCII art, and Obsidian callout blocks to create semantically rich visual content embedded in notes.

**Not for TikZ** — for mathematical diagrams destined for LaTeX output, delegate to `latex-tikz-specialist`.

## Quick reference

| Visualisation need | Mermaid type | Direction |
|-------------------|--------------|-----------|
| Pipeline / algorithm flow | flowchart | LR |
| Hierarchy / taxonomy | flowchart | TD |
| Concept relationships | graph | LR |
| Agent interactions, temporal ordering | sequenceDiagram | — |
| Topic overview | mindmap | — |
| Type / structural relationships | classDiagram | — |
| State lifecycle | stateDiagram-v2 | — |
| Cross-domain comparison | markdown table | — |
| Inline ≤4 node diagram | ASCII art | — |

## When this skill runs

- User asks for any visual that will live inside a markdown vault note.
- A writer skill (research-scribe, knowledge-indexer) needs a concept map, process diagram, or comparison table.
- `dashboard-builder` needs a pipeline or status diagram.

Do **not** run for:

- Mathematical diagrams requiring precision or destined for LaTeX → `latex-tikz-specialist`.
- Dataview dashboard queries → `dashboard-builder`.
- Note prose → writer skills.

## Mermaid types

### Flowchart — processes, pipelines, algorithms

```mermaid
flowchart LR
    A[Input] --> B{Route?}
    B --> |math| C[research-scribe]
    B --> |reflection| D[reflection-writer]
    C --> E[04_Research/]
    D --> F[01_Daily_Life/Reflections/]
```

Use `LR` for information flow; `TD` for hierarchies.

### Graph — undirected or weakly directed concept relations

```mermaid
graph LR
    MeasureTheory --- ProbabilityTheory
    ProbabilityTheory --- StochasticCalculus
    StochasticCalculus --- MathematicalFinance
    MeasureTheory --- FunctionalAnalysis
```

### Sequence — interactions and temporal ordering

```mermaid
sequenceDiagram
    User->>Router: free-form request
    Router->>ContentRouter: classified intent
    ContentRouter->>ResearchScribe: WRITE/technical
    ResearchScribe->>Vault: 04_Research/...
```

### Mind map — radial topic explosion

```mermaid
mindmap
  root((Mathematical Finance))
    Pricing Theory
      No-Arbitrage
      Risk-Neutral Measure
    Stochastic Processes
      Brownian Motion
      Itô Calculus
```

### Class diagram — type / structural relationships

```mermaid
classDiagram
    class FilteredProbabilitySpace {
        Omega: sample space
        F: sigma-algebra
        Ft: filtration
        Q: measure
    }
    FilteredProbabilitySpace --> BrownianMotion : adapted to
```

### State diagram — state machines, lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Active: commit + review
    Active --> Archived: deprecated
```

## Structured tables

For comparison, feature matrix, or cross-domain analogy:

| Concept | Mathematics | Physics | Finance |
|---------|-------------|---------|---------|
| Space of states | Vector space | Phase space / Hilbert space | Sample space Ω |
| Observable | Linear functional | Hermitian operator | Random variable |
| Evolution | ODE / semigroup | Schrödinger eq. | SDE / filtration |
| Symmetry | Group action | Gauge group | No-arbitrage |

Rules: column headers are concepts, not categories. Every cell has a specific item. Use `—` for missing analogues. Max ~6 columns.

## ASCII diagrams

For very simple inline diagrams where a Mermaid block would be disproportionate (≤4 nodes, ≤6 arrows, embedded mid-paragraph):

```
Set X ──f──▶ Set Y
 │                │
 │g               │h
 ▼                ▼
Set Z ──k──▶ Set W
```

## Obsidian callouts

Use for structured knowledge boxes inside notes:

```markdown
> [!definition] Filtration
> A filtration $(\mathcal{F}_t)_{t \geq 0}$ is an increasing family of sub-$\sigma$-algebras...

> [!example] Brownian Filtration
> The natural filtration of Brownian motion...

> [!warning] Coordinate dependence
> The metric tensor $g_{\mu\nu}$ depends on the coordinate chart...
```

Types: `definition`, `theorem`, `example`, `warning`, `info`, `note`, `abstract`, `question`.

## Quality standards

**Correct:** no phantom arrows, no missing edges; type appropriate for the relationship; labels semantically precise.

**Excellent:** layout direction natural for the domain; reveals structure that would require a paragraph in prose; self-explanatory with a one-sentence caption.

## Dependencies

- Sibling skills: `latex-tikz-specialist` (delegate math diagrams destined for LaTeX), `dashboard-builder` (uses this for pipeline diagrams), `research-scribe`, `knowledge-indexer` (call this for concept maps).
