---
name: latex-tikz-specialist
description: 'Produce complete, compilable TikZ and LaTeX figure code for mathematical diagrams. Use this skill when the user says "create a TikZ diagram", "draw a commutative diagram", "tikz figure", "LaTeX figure", "category theory diagram", "commutative square", "adjunction diagram", "filtration timeline", "geometric construction", "draw the fiber bundle", "poset diagram", "DAG with labels", "stochastic process timeline", "PDE domain diagram", "tikzcd", "dibuja un diagrama conmutativo", "figura TikZ". Produces figures inside figure environments (LuaLaTeX, tikz-cd for commutative diagrams), following all Reflexiones_a_Latex conventions: label scheme fig:<chapter>_<description>, personal macros \mb{} \mbb{} \mc{} \on{} \lp \rp \fa, minimal styling, em/cm dimensions. Output is either a fenced latex code block for embedding in a vault note, or a complete figure environment for insertion into a .tex file. Do NOT trigger for Mermaid/Markdown visualisations (md-grapher), for prose writing (writer skills), or for generating full LaTeX documents (reflexiones-writer).'
license: Proprietary. OmarOS internal.
---

# LaTeX / TikZ Specialist

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Responsible for mathematical diagram production at the highest quality level. Every figure produced must be:
- **Complete and compilable** — not a sketch, not a placeholder.
- **Semantically meaningful** — the diagram clarifies structure, not merely decorates.
- **Reflexiones_a_Latex-compatible** — LuaLaTeX, personal macro set, label scheme, figure environment conventions.

## Quick reference

| Diagram type | TikZ approach |
|--------------|---------------|
| Commutative diagram (category theory, homological algebra) | `tikz-cd` |
| Geometric construction | `tikzpicture` + `calc`, `intersections` |
| Graph / poset / lattice / DAG | `tikzpicture` + `positioning`, `arrows.meta` |
| Algorithm / proof strategy flow | `tikzpicture` + `shapes.geometric`, `positioning` |
| Stochastic process timeline | `tikzpicture` + horizontal axis with marks |
| PDE domain with boundary conditions | `tikzpicture` + `decorations.pathmorphing` |
| Fiber bundle diagram | `tikzpicture` + layered structure |

## When this skill runs

- Any commutative diagram (natural transformations, adjunctions, pullbacks, fiber bundles).
- Any geometric construction whose verbal description is harder than the picture.
- Any graph, poset, lattice, or DAG with more than three elements.
- Any flow diagram for an algorithm, proof strategy, or pipeline destined for LaTeX.
- Any stochastic process timeline (filtration, stopping time, Brownian path).
- Any figure appearing in a source paper being annotated in the vault.

Do **not** run for:

- Mermaid/markdown visualisations in vault notes → `md-grapher`.
- Full LaTeX document drafting → `reflexiones-writer`.

## LaTeX / Reflexiones_a_Latex conventions (mandatory)

**Compiler**: LuaLaTeX only. Use only LuaLaTeX-compatible packages.

**Figure wrapper**:
```latex
\begin{figure}[ht]
  \centering
  \begin{tikzpicture}[...]
    % figure content
  \end{tikzpicture}
  \caption{<semantically complete caption>}
  \label{fig:<chapter>_<description>}
\end{figure}
```

**Commutative diagrams** — use `tikz-cd`:
```latex
\begin{tikzcd}
  A \ar[r, "f"] \ar[dr, "g \circ f"'] & B \ar[d, "g"] \\
                                        & C
\end{tikzcd}
```

**TikZ libraries** — declare only what is actually used:
`arrows.meta`, `positioning`, `calc`, `decorations.pathmorphing`, `matrix`, `shapes.geometric`.

**Dimensions**: always `em` or `cm`, never `pt`.

**Styling**: minimal. Semantic use of colour is acceptable (highlighting a path, distinguishing arrow classes) but must be motivated.

**Label scheme**: `fig:<chapter>_<description>` — e.g. `fig:cat_adjunction_unit`, `fig:fa_banach_inclusion`, `fig:mf_filtration_timeline`.

**Personal macros** (available in Reflexiones_a_Latex preamble — use freely):
```latex
\mb{}       % \mathbf
\mbb{}      % \mathbb
\mc{}       % \mathcal
\on{}       % \operatorname
\lp \rp     % \left( \right)
\fa         % \forall
```

**Font**: Libertinus Serif / XITS Math via `unicode-math`. Do not use `amssymb` symbols that conflict with XITS.

## Output modes

**Embedded in a markdown vault note**: wrap TikZ code in a fenced `latex` block, preceded by a prose description.

**Embedded in a `.tex` file**: produce a complete `figure` environment ready for insertion. State the target file and approximate insertion point.

**Standalone figure file**: for large or multi-referenced figures, produce as `DOCUMENTO_COMPLETO/figures/<chapter>/<label>.tex` with a corresponding `\input{}` call.

## Quality standards

**Correct:**
- All arrows labelled with morphism names or natural transformation components.
- Commutativity visually evident from layout.
- Shape of diagram signals its type (triangle = composition/factorisation, square = naturality/pullback, hexagon = hexagon identity).
- Objects with structure (filtered probability spaces, manifold bundles) have that structure indicated in node notation.

**Excellent:**
- Looking at it, the reader immediately understands why it appears here.
- Does not require a paragraph to decode.
- Layout respects mathematical direction conventions.

## Escalation

If the diagram requires deep domain knowledge to determine the correct semantic layout (complex spectral sequence, derived category, subtle naturality condition): state the mathematical question explicitly, produce the diagram, and flag the semantic assumption made.

If the diagram requires >80 lines of TikZ: produce in stages — node structure first, then arrows, then decorations.

## Dependencies

- Sibling skills: `md-grapher` (markdown visualisations; delegate non-LaTeX needs there), `research-scribe`, `reflection-writer` (call this when a diagram would materially aid exposition).
- Reflexiones_a_Latex standards: `09_Data_Sources/LaTeX_Repos/reflexiones_latex/source/CLAUDE.md`.
