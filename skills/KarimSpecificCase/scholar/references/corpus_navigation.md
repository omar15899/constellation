# Corpus navigation — Reflexiones_a_Latex

Used in Route L to identify where in the LaTeX corpus a new section belongs.

## Corpus root

`/Users/omarkhalil/Desktop/Universidad/Reflexiones_a_Latex/`

## Top-level structure

```
Reflexiones_a_Latex/
├── DOCUMENTO_COMPLETO/
│   ├── main.tex               ← master document (includes all chapters)
│   ├── Libreria.bib           ← bibliography (all \cite{} keys must be here)
│   ├── preamble.tex           ← all \usepackage, theorem environments, macros
│   └── chapters/
│       ├── Analisis_Funcional/
│       ├── Calculo_Univariable/
│       ├── Calculo_Multivariable/
│       ├── ComplexAnalisis/
│       ├── Teoria_de_la_Medida/
│       ├── Probability Theory/
│       ├── Markov_Processes/
│       ├── Stochastic_Calculus/
│       ├── Mathematical_Finance/
│       ├── Finance/
│       ├── Geometria_Diferencial/
│       ├── Teoria_Conjuntos/
│       ├── TeoriaCategorias/
│       ├── Fisica_Apuntes/
│       ├── Construccion_Fisica/
│       ├── Reflexiones_Filosoficas/
│       ├── ML/
│       ├── Informatica/
│       ├── computational_mathematics/
│       ├── Optimisation/
│       └── Finite_Elements/
```

## Folder map by topic

| Topic area | Corpus folders |
|---|---|
| Set theory, categories | `Teoria_Conjuntos/`, `TeoriaCategorias/` |
| Analysis | `Analisis_Funcional/`, `Calculo_Univariable/`, `Calculo_Multivariable/`, `ComplexAnalisis/` |
| Measure, probability | `Probability Theory/`, `Markov_Processes/`, `Teoria_de_la_Medida/` |
| Stochastic / finance | `Stochastic_Calculus/`, `Mathematical_Finance/`, `Finance/` |
| Geometry / physics | `Geometria_Diferencial/`, `Fisica_Apuntes/`, `Construccion_Fisica/` |
| Philosophy | `Reflexiones_Filosoficas/` |
| Computation / ML | `ML/`, `Informatica/`, `computational_mathematics/` |
| Optimisation | `Optimisation/`, `Finite_Elements/` |

## Navigation procedure

1. **Identify the primary chapter** from the table above. When a topic spans multiple chapters (e.g., stochastic integration touches Measure Theory, Probability Theory, and Stochastic Calculus), identify the *primary* locus and list the others for cross-references.
2. **Read the chapter's main `.tex` file** to understand existing label conventions, notation, and section structure.
3. **Grep for existing labels** matching the topic: `\label{def:slug}`, `\label{thm:slug}`, `\label{sec:slug}`. If a label already exists for the same concept, extend consistently rather than creating a duplicate.
4. **Check `Libreria.bib`** for existing citation keys before writing any `\cite{}`.

## Placement decision

| User intent | Placement |
|---|---|
| Genuinely new topic for this chapter | New file: `chapters/<Area>/<slug>.tex`, included via `\input{}` in chapter main |
| Extension of an existing section | Append `\subsection{}` inside the existing file |
| Cross-chapter synthesis | New file in the more general chapter + `\ref{}` pointers to the other |

## Label convention

`type:area_slug` where type ∈ {`def`, `thm`, `prop`, `lem`, `cor`, `rmk`, `ex`, `sec`, `fig`}.

Examples: `def:weak_derivative`, `thm:lln_kolmogorov`, `sec:functional_calculus`.

All labels must be unique across the entire corpus. Grep before assigning.
