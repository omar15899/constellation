# 05 — Visual Economy

## The rule

**On-screen text and visual elements are scarce resources. Keep the frame as empty as possible while still doing the pedagogical work.**

The animation must not become a slide deck. Every shot declares a maximum visible word count; the default is **35 words** unless the shot is explicitly a summary frame.

## When on-screen text is appropriate

Screen text earns its place when it carries information the viewer needs to *retain in working memory* across the shot, or *return to* during a pause. The canonical legitimate uses:

- **Object labels.** A short label attached to a visual object, so the viewer can name it as the narration refers to it.
- **Key numbers.** The current value of a tracked quantity (a ticker, a present value, an FX rate).
- **Formulas.** When the formula *is* the object of attention — see `12_formula_doctrine.md`.
- **Definitions.** A short `<term> — <8–15 word definition>` block that appears when the term is first voiced.
- **Retrieval questions.** A single short question that hangs during a retrieval pause.
- **Essence statements.** The single-sentence essence of the concept, voiced once and held briefly on screen at the climactic frame.

## What screen text is NOT for

- **Re-stating what the narration is saying.** The voice does the prose. The screen does the structure.
- **Paragraphs.** If more than two lines of text are simultaneously on screen, the shot has failed visual economy.
- **Decorative quotes.** Inspirational tags do not belong here.
- **Section headers that the viewer does not need to navigate.** If the narration has already established what scene we are in, repeating the scene name on screen is noise.

## The 35-word limit

Every shot declares `max_visible_words` in its animation spec. The default is 35. If the spec sets it higher, the spec must give a reason in the `notes` field (e.g., "summary frame at end of scene, expected to be held for 6 s while the viewer rereads"). The render_review agent counts visible words at any frame and rejects shots that exceed their declared limit.

Counting rules:

- Every visible word counts once. Multi-line formulas count as their TeX-rendered word equivalents (`V_CCS`, `PV_EUR`, etc. each count as one).
- Labels that appear and disappear within a single shot count if they are visible at *any* moment in the shot.
- Numbers in tickers count as one word per visible token (so a ticker showing `EUR 75.4` counts as two).
- Single-character labels (`A`, `t`, `x`) count as words.

The limit is on words *simultaneously visible at a single frame*, not on the cumulative word count across the shot. A shot can introduce label `A`, replace it with label `B`, and so on, as long as the frame at any instant respects the limit.

## What this earns you

When the frame is uncluttered, the eye knows where to land. The viewer is not parsing text — they are watching the diagram. The voice carries the prose; the visual carries the structure. This is the medium working as intended.

The most common failure of AI-generated educational animation is the *PowerPoint reflex*: every shot becomes a slide with three bullet points, a title, a logo, and a chart. Each element on its own is defensible; the cumulative effect is a presentation, not an explanation.

## Visual economy beyond text

The same discipline applies to non-text elements:

- **One dominant focal point per shot.** If the viewer's eye has to choose where to land, the composition has failed.
- **No decorative icons.** Every icon must have a semantic role (see `10_negative_constraints.md`). A finance-themed clip-art dollar sign is not a semantic icon; it is decoration.
- **No "atmospheric" particle fields or glows** unless the field is doing semantic work (e.g., the `DollarGravityField` metaphor literally drawn as a field of arrows).
- **No background animation during a retrieval pause.** Silence on the audio track must be matched by stillness on the visual track (see `09_synchronization.md`).

A shot can have high implementation detail and low visual density. The spec resolves the small set of decisions about what is on screen; the result on screen is sparse, deliberate, and legible.

## The economy test

Before approving a shot, ask: *if I removed one element from this frame, would the pedagogical work still get done?* If yes, remove it. Repeat until the answer is no.

The shot that emerges is the spec's actual intention.
