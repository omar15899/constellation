# Video Design Rules

The operational translation of `extracted_principles.md` into concrete production rules. The skill enforces these during script design and at the QC pass. Each rule cites the principles it derives from. When a rule and the user's explicit request conflict, ask before defaulting.

## Rules of engagement

### R1. The viewer is a participant, not an audience.

Every video must include explicit prompts that ask the viewer to predict, recall, classify, compare, or explain. Continuous narration over visuals with no break for viewer cognition is a quality failure, not a stylistic choice. The intervention need not be elaborate; even a 3-second silent beat with a question on screen suffices.

*Principles:* active learning, retrieval practice, self-explanation. *Papers:* Freeman et al. (2014); Roediger & Karpicke (2006a, 2006b); Chi et al. (1989, 1994); Carpenter, Pan & Butler (2022).

### R2. Insert at least one retrieval prompt per major scene.

A retrieval prompt is a moment where the viewer is asked to recall, predict, or classify before the answer is shown. Vary the format across the video (free recall, recognition, prediction, comparison). Reveal the answer 2–4 s after the prompt.

*Principles:* retrieval practice, active learning. *Papers:* Roediger & Karpicke (2006a, 2006b); Dunlosky et al. (2013).

### R3. Re-encounter the central concept after intermediate material.

Within a single video, the central object should reappear at least once after secondary material is introduced. Across a series, schedule conceptual revisits in later episodes. Spacing is the principle behind series-level design; massed exposure inside a single block underestimates what the viewer will forget.

*Principles:* spacing, desirable difficulties. *Papers:* Cepeda et al. (2006); Carpenter, Pan & Butler (2022).

### R4. Interleave when the goal is discrimination.

When the viewer must learn to choose between similar concepts (Itô vs Stratonovich; type-I vs type-II error; pull-back vs push-forward), present interleaved examples (A, B, A, B, A) rather than blocked (A, A, A, B, B, B). Begin with a brief blocked introduction of each individually, then interleave for the discrimination work. Include at least one *unmarked* problem with no hint about which technique applies.

*Principles:* interleaving, discrimination. *Papers:* Kornell & Bjork (2008); Birnbaum et al. (2013); Rohrer (2012).

### R5. Use worked examples for novices; fade them for experts.

For beginner / undergraduate audiences, the first example of any new technique is fully worked — every step shown, every choice justified. Worked examples should be paired with self-explanation prompts at non-obvious moves and with isomorphic follow-ups. For research-level audiences, worked examples become extraneous load — replace them with structural sketches and motivating instances.

*Principles:* worked examples, expertise reversal. *Papers:* Atkinson et al. (2000); Kalyuga et al. (2003); Sweller, van Merriënboer & Paas (1998).

### R6. Use worked-example fading for procedural content.

For procedural content (algorithms, derivations, problem-solving) at the undergraduate level: example 1 fully worked → example 2 with the last step blank → example 3 with more blanks → example 4 unaided. Each blank is a 2–4 s prompt with answer revealed visually.

*Principles:* worked examples, worked-example fading, scaffolding. *Papers:* Renkl, Atkinson, Maier & Staley (2002).

## Rules of representation

### R7. Concrete first, abstract last — by morphing, not cutting.

When a topic admits a natural concrete instance, the script defaults to: concrete → semi-abstract bridge → fully formal object. Each transition is animated as a morph; the visual continuity is what carries the learning. End at the formal object, never at the bridge.

*Principles:* concreteness fading, multimedia learning (visual continuity), schema construction. *Papers:* McNeil & Fyfe (2012); Fyfe et al. (2014); Kokkonen et al. (2022).

### R8. Distinguish object, representation, notation, and example — visibly.

Coordinate expressions are not the manifold; sample paths are not the process; histograms are not the distribution; matrices are not the linear map. Make the distinction visible: when the representation fades, the invariant object remains. When the representation transforms (rotation, re-coordinatisation), the underlying object holds still and is re-highlighted.

*Principles:* mathematical rigor; visual continuity (CTML). *Papers:* Mayer (2005); Sweller, van Merriënboer & Paas (1998).

### R9. Synchronise narration and visual change.

The voice-over and the visual event must occupy the same instant (within 0.3 s). Do not narrate something seconds before or after it appears. When a visual takes longer than the narration that introduces it, the narration stops; the visual continues silently. State the silent continuation in production notes.

*Principles:* multimedia learning (temporal contiguity), cognitive load (split-attention). *Papers:* Mayer (2005); Sweller (1994).

### R10. No verbatim duplication of voice-over on screen.

If the voice-over says "the gradient points in the direction of steepest ascent", the screen does not display the same sentence as text. Pick one channel per piece of information. On-screen text is reserved for formal definitions, formulas, names of objects, and labels — content that the viewer needs to *re-read*, not *re-hear*.

*Principles:* multimedia learning (redundancy effect), cognitive load. *Papers:* Mayer (2005); Sweller, van Merriënboer & Paas (1998).

### R11. Place labels adjacent to their target.

A label far from the object it labels forces the viewer to split attention between the two. Annotations belong adjacent to their anchor; legends are last-resort.

*Principles:* multimedia learning (spatial contiguity), cognitive load (split-attention). *Papers:* Mayer (2005); Sweller, van Merriënboer & Paas (1998).

### R12. Strip every visual element that does not encode conceptual structure.

Decorative ornament — particles, gradients, swirling lines, flourish animations — adds extraneous load and competes for attention with the structure that matters. Every element on screen earns its place by encoding conceptual content. Background is not empty — it is the visual equivalent of a pause.

*Principles:* multimedia learning (coherence), cognitive load. *Papers:* Mayer (2005, 2024); Sweller (1994).

### R13. Use motion to encode meaning, not for variety.

Morphs encode transformation. Arrows growing in real time encode dependence. Refinement encodes limits. Zooms encode local-to-global structure. Fades encode abstraction. Reversible morphisms encode equivalence. Avoid bullet-point reveals — they are the static-list anti-pattern.

*Principles:* multimedia learning (signalling), cognitive load (germane). *Papers:* Mayer (2005); Sweller (1994).

## Rules of engagement with rigor

### R14. Build definitions from necessity.

A definition arrives as the answer to a problem. Build the conceptual pressure that makes the definition feel inevitable, then formalise. Definitions presented by fiat ("an atlas is a collection of charts") fail to land; definitions presented as solutions ("we need a way to describe a curved space without tearing — here is the data we need") land as recognition.

*Principles:* schema construction; coherence; concreteness fading. *Papers:* Mayer (2005); Atkinson et al. (2000).

### R15. Use refutation framing for misconceptions.

When a likely misconception exists, name it explicitly and refute it visually before stating the correct concept. "Many learners initially think X — let us see why X breaks, and what to put in its place." More effective than stating the correct concept alone.

*Principles:* metacognition, conceptual change. *Papers:* Metcalfe (2009); Panadero (2017).

### R16. Pair retrieval prompts with calibration commentary.

When the viewer's prediction is likely to be wrong, narrate the calibration move: "if you are surprised, that is the point — the next scene shows why." Avoid scripts that always confirm the viewer's intuition.

*Principles:* metacognition, desirable difficulties. *Papers:* Metcalfe (2009); Carpenter, Pan & Butler (2022).

### R17. Use non-examples when they sharpen the boundary.

When a definition has a subtle condition that beginners often miss, a non-example clarifies the boundary: "here is something that almost satisfies the definition but fails because…". Use sparingly — non-examples add cognitive load. Pick the one or two that genuinely sharpen the definition.

*Principles:* discrimination; mathematical rigor. *Papers:* Kornell & Bjork (2008); Rohrer (2012).

### R18. Do not simplify by falsifying.

Pedagogical simplification may simplify the *route* into a concept; it may not simplify the *concept itself*. Do not soften definitions, do not blur quantifiers, do not pretend examples are definitions, do not present partial metaphors as if they were the formal object. Where a metaphor is partial, name its limit.

*Principles:* mathematical rigor; conceptual correctness. *Foundational rule across all sources.*

## Rules of pacing and structure

### R19. Hold for 1–2 seconds after each definition.

A definition needs absorption time. The narration stops; the screen is held; the viewer reads. The pause is in the production notes, not in the voice-over text.

*Principles:* multimedia learning (segmenting), cognitive load. *Papers:* Mayer (2005); Sweller (1994).

### R20. Chunk into discrete scenes with conceptual function.

Divide the video by *conceptual function* — motivate / show / define / exemplify / abstract / return / synthesise — not by topic. Each scene has a single function. Scene breaks are pauses in the cognitive flow; they let the viewer consolidate.

*Principles:* multimedia learning (segmenting), schema construction. *Papers:* Mayer (2005, 2024).

### R21. End on a re-encounter with the original question.

The video closes by returning to the opening question or phenomenon, with the new construction available. The viewer should feel a shift — the original question is now answerable. Do not end on a definition or a formula; end on understanding.

*Principles:* schema construction, metacognition (reflection). *Papers:* Panadero (2017); Atkinson et al. (2000).

### R22. Hand off to deliberate practice when skill is the goal.

When the script's objective is skill (algorithm execution, derivation fluency, problem-solving), the closing scene hands off to a deliberate-practice activity. The video introduces; the practice builds. Be honest about scope.

*Principles:* deliberate practice; self-regulated learning. *Papers:* Ericsson, Krampe & Tesch-Römer (1993); Panadero (2017).

## Rules of audience adaptation (cross-cutting)

### R23. Pick an audience tier at the design phase, not after.

Beginner / undergraduate / advanced UG / research / mixed. The tier choice controls: notation density, pacing, visual density, example strategy, prompt style, scaffolding amount. Designing one script and then "adapting" it after the fact produces a video that under-serves both tiers.

*Principle:* expertise reversal. *Paper:* Kalyuga et al. (2003).

### R24. For mixed audiences, bridge with one concrete instance, then lift.

When the audience genuinely spans tiers (a public-facing video on a specialist topic), open with a concrete instance accessible to the lower tier, then lift cleanly to the formal object for the higher tier. Do not try to satisfy both throughout — the seam is unavoidable; place it deliberately.

*Principles:* concreteness fading, expertise reversal. *Papers:* McNeil & Fyfe (2012); Kalyuga et al. (2003).

## Rules of QC enforcement

The four checklists in `../checklists/` enforce these rules at the audit phase. The pedagogical-quality checklist enforces R1–R6, R14–R17, R23–R24. The visual-quality checklist enforces R7–R13, R19–R20. The mathematical-accuracy checklist enforces R8 and R18. The production-readiness checklist enforces synchronisation (R9), labelling (R11), and asset coverage.

If a rule is broken, the QC pass either repairs or flags. A FAIL on any rule blocks delivery. A NOTE is recorded with the script.
