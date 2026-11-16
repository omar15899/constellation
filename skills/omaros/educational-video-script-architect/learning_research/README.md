# learning_research/

Drop folder for papers, summaries, and notes about pedagogy, cognitive science, mathematical cognition, and expertise development. The skill consults this folder, when non-empty, to inform pacing, example selection, sequencing, abstraction timing, cognitive-load control, and misconception repair.

## Layout

```
learning_research/
  README.md                  ← you are here
  papers/                    ← original PDFs or links
  summaries/                 ← short markdown notes per paper
  extracted_principles.md    ← the synthesised, video-design-relevant takeaways
```

## How the skill uses this folder

When invoked, the skill checks whether `extracted_principles.md` exists and is non-empty. If so:

- It reads the file as a list of design principles tagged by audience level and pedagogical move.
- It applies the most relevant principles to the current script (pacing, examples, signaling, segmenting, retrieval moments).
- It cites, in **§3 Pedagogical design notes** of the script, which principles influenced the design — briefly, never as a literature review.

If `extracted_principles.md` is missing or empty, the skill falls back to the defaults in `style/` and the canonical structure.

## What to put in `extracted_principles.md`

Short, actionable principles with a one-line rationale. Tag by audience level when the effect is level-specific (e.g., the **expertise reversal effect** says techniques that help novices may hurt experts).

Recommended format:

```markdown
# Extracted Principles

## Cognitive load
- **Worked-example effect** (novice / undergraduate). Show fully worked examples before asking the viewer to predict the next step. Cite: Sweller 1988, Renkl 2014.
- **Expertise reversal** (research / expert). Drop redundant scaffolding for advanced viewers; it costs attention and adds nothing.
- **Segmenting** (all levels). Give the viewer pause moments after each conceptually dense definition.

## Sequencing
- **Concrete-first for novices**, **abstract-first for experts** (mixed audience: bridge with a single concrete instance, then lift).
- **Interleaving** improves long-term transfer for series of videos covering related but distinct concepts.

## Misconception repair
- **Refutation text** (Tippett 2010). Naming the misconception explicitly and contrasting it with the correct concept is more effective than just stating the correct concept.
- **Bridging analogies**. When a metaphor is partial, follow it with the metaphor that fixes its failure mode.

## Visual learning
- **Dual coding** (Paivio). Visual and verbal channels processed independently; redundant signaling helps when not overloaded.
- **Signaling**. Highlights, arrows, and colour cues direct attention; effective only when sparse.
```

Adjust the principles list as the folder grows. The skill will read the latest version on every invocation.

## Suggested papers

If you are starting from scratch, papers worth ingesting:

- Sweller, "Cognitive Load Theory" (1988, with later refinements)
- Renkl, "Toward a theory of worked examples" (2014)
- Mayer, "Multimedia Learning" (textbook; pick chapters on signaling, segmenting, redundancy)
- Kalyuga et al., "Expertise Reversal Effect" (2003)
- Bjork & Bjork, "Desirable Difficulties" (2011)
- Karpicke, "Retrieval-based learning" (2012)
- Roediger & Pyc, "Inexpensive techniques to improve education" (2012)
- diSessa, "Conceptual change" (1993; pieces of phenomenology in physics)
- Tall, "How humans learn to think mathematically" (2013)
- Tippett, "Refutation text in science education" (2010)
- Hidi & Renninger, "The four-phase model of interest development" (2006)

The summaries/ folder should contain a one-page note per paper: title, citation, three-line summary, three takeaways relevant to video design.

## Hard constraint

Pedagogical optimization may simplify the *route* into a concept, but never the *concept itself*. No principle from this folder is licence to soften a definition, blur a quantifier, or pretend an example is a definition.
