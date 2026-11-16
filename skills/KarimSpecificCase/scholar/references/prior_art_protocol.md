# Prior-art protocol — blocking pre-write step

Before writing any research artefact, run a prior-art pass against the Reflexiones_a_Latex corpus. This is non-negotiable: writing before consultation produces notation drift and duplicate treatments that compound across years.

## 1. Corpus location

`/Users/omarkhalil/Desktop/Universidad/Reflexiones_a_Latex/DOCUMENTO_COMPLETO/chapters/`

## 2. Folder map by topic

| Topic area | Corpus folders |
|------------|----------------|
| Set theory, categories | `Teoria_Conjuntos/`, `TeoriaCategorias/` |
| Analysis | `Analisis_Funcional/`, `Calculo_Univariable/`, `Calculo_Multivariable/`, `ComplexAnalisis/` |
| Measure, probability | `Probability Theory/`, `Markov_Processes/`, `Teoria_de_la_Medida/` |
| Stochastic / finance | `Stochastic_Calculus/`, `Mathematical_Finance/`, `Finance/` |
| Geometry / physics | `Geometria_Diferencial/`, `Fisica_Apuntes/`, `Construccion_Fisica/` |
| Philosophy | `Reflexiones_Filosoficas/` |
| Computation / ML | `ML/`, `Informatica/`, `computational_mathematics/` |
| Optimisation | `Optimisation/`, `Finite_Elements/` |

## 3. Grep procedure

For each topic, grep for Spanish AND English aliases of the main terms across the relevant folders. Search both the `.tex` text and label patterns (`\label{def:…}`, `\label{thm:…}`).

## 4. Coverage classification

| Level | Criterion | Action |
|-------|-----------|--------|
| **Substantial** | Multiple sections, formal environments, thorough treatment | **Ask the user first:** "Extensive prior treatment at [path]. Extend consistently, complementary fresh treatment, or import and expand?" Wait for answer. |
| **Tangential** | Passing mentions, adjacent topics, established notation | Read the passages. Extract: notation choices, canonical definitions, prior claims. Write fresh, notation-consistent. |
| **None** | Nothing found | Write fresh. `prior_art: []`. State so in opening. |

## 5. Provenance recording

In the artefact's frontmatter:

```yaml
prior_art:
  - path: DOCUMENTO_COMPLETO/chapters/<Area>/<file>.tex
    finding: "Treated in section on X; uses notation Y."
  - path: …
    finding: …
```

If empty: `prior_art: []` AND an explicit sentence in the opening remark.

## 6. Cross-reference

When adjacent prior art exists, include a plain markdown pointer (not wikilink, since it crosses the project boundary):

> *Cross-reference: `DOCUMENTO_COMPLETO/chapters/Analisis_Funcional/analisisfuncional.tex` § Derivada débil.*

## 7. What the prior-art pass does NOT do

- It does not replace the corpus. If the user wants the content **inside** the corpus, route to `reflexiones-writer` instead.
- It does not vet correctness of the prior treatment; only its presence.
- It does not establish authority over notation; the corpus is authoritative unless the user explicitly updates it.
