# Extracted Principles

This is the **operational digest** of the learning-research collection. The skill reads this file (and `video_design_rules.md`) on every invocation; it does not re-read the underlying papers unless a deep dive is explicitly requested.

The frame: pedagogy improves the *route* into a concept; it never softens the concept itself. Mathematical and conceptual correctness are non-negotiable. Every principle below is a tool for making the route shorter, more honest, and more durable — not a permission to falsify.

Each principle is structured as: **definition → why it matters → how to apply it in a video script → what to avoid → audience adaptation → relevant papers**.

---

## 1. Retrieval practice (the testing effect)

- **Definition.** A learner who attempts to *retrieve* studied material from memory retains it better and longer than a learner who restudies for the same time.
- **Why it matters.** The strongest single intervention in cognitive science of learning. The effect grows with retention interval — short-term gains underestimate it.
- **How to apply in a video script.**
  - Insert at least one retrieval prompt per major scene: "pause and try to predict X", "which of these is *not* a chart?", "what does this notation mean?"
  - Reveal the answer 2–4 s later, visually.
  - Vary prompt format (recall, recognition, prediction, classification, compare-and-contrast).
- **What to avoid.** Retrieval prompts at trivia points; prompts without feedback; prompts that the viewer cannot possibly answer at that moment in the video.
- **Audience adaptation.**
  - **Beginner / undergraduate**: cued recall (with a visual hint). Frequent.
  - **Advanced / research**: prediction of the *next move* is more valuable than recall. Sparser.
- **Papers.** Roediger & Karpicke (2006a, 2006b); Carpenter, Pan & Butler (2022); Dunlosky et al. (2013).

## 2. Spacing (distributed practice)

- **Definition.** Distributing study over time outperforms massing it — the longer the desired retention, the larger the optimal gap between encounters.
- **Why it matters.** Like retrieval, spacing is robust across domains, ages, and material types. Unlike retrieval, it operates *across* sessions, so it is the principle behind series-of-videos design.
- **How to apply in a video script.**
  - **Within a video**: re-encounter the central object at least once after intermediate examples. The re-encounter is itself a small-scale spacing event.
  - **Across a series**: schedule conceptual revisits in later episodes; do not silo each episode topic-purely.
  - The optimal gap scales with retention horizon: ~10–30% of the desired retention interval.
- **What to avoid.** Massing all material on a topic in one block; assuming a one-shot exposure produces durable learning.
- **Audience adaptation.** Spacing helps all audiences; the gap and re-encounter density should be larger for advanced viewers (who can tolerate more time before needing a refresher).
- **Papers.** Cepeda et al. (2006); Carpenter, Pan & Butler (2022); Dunlosky et al. (2013).

## 3. Interleaving and discrimination

- **Definition.** Mixing examples of different categories or problem types during practice improves the ability to *discriminate* between them — to know which technique applies. Pure-blocked practice produces fluency *within* a category but not selection *between* them.
- **Why it matters.** A viewer who can apply technique A when told to apply A may still fail to recognise *when* to apply A on a free problem. Discrimination is a separate skill.
- **How to apply in a video script.**
  - When the topic involves choice between similar concepts (Itô vs Stratonovich; type-I vs type-II error; pull-back vs push-forward), interleave examples.
  - Begin with a brief blocked introduction of each concept *individually*, then interleave for discrimination.
  - Include at least one *unmarked* example (no hint about which technique applies) to force the discrimination move.
- **What to avoid.** Interleaving from the very first encounter (cognitive overload); pure blocking when discrimination is the goal; treating "variety of examples" as equivalent to "interleaving" (the order matters).
- **Audience adaptation.** Beginners need more blocked anchor before interleaving begins; experts can tolerate immediate interleaving.
- **Papers.** Kornell & Bjork (2008); Birnbaum et al. (2013); Rohrer (2012).

## 4. Desirable difficulties

- **Definition.** Some learning conditions feel harder in the moment but produce stronger long-term retention and transfer. Retrieval, spacing, interleaving, and varied conditions are all instances.
- **Why it matters.** Reframes the design problem: subjective ease is not the goal. The viewer's sense that "this video flowed easily" is a poor proxy for what they actually retained a week later.
- **How to apply in a video script.**
  - Be willing to design moments of productive friction: a retrieval prompt the viewer probably gets wrong, a non-obvious notation switch, a comparison that requires effort.
  - Briefly narrate that the friction is intentional ("this feels like jumping around — that is the point").
- **What to avoid.** Friction without resolution; long stretches of confusion; engineered difficulty that has no follow-up.
- **Audience adaptation.** Calibrate the *amount* of difficulty to audience tier; the *pattern* (difficulty → resolution → calibration commentary) is the same.
- **Papers.** Carpenter, Pan & Butler (2022); Bjork & Bjork (2011, missing PDF — referenced via secondary sources); Kornell & Bjork (2008).

## 5. Cognitive load

- **Definition.** Working memory is narrow; learning requires building schemas in long-term memory. Instruction succeeds when *intrinsic* load (the inherent difficulty of the material) is respected, *extraneous* load (the design's accidental cost) is minimised, and *germane* load (the effort spent on schema-building) is maximised.
- **Why it matters.** Tells you which design elements help and which silently destroy comprehension. The cost of a poorly designed split-attention frame is invisible from the outside but real for the viewer.
- **How to apply in a video script.**
  - Reduce extraneous load: do not narrate text identical to on-screen text (redundancy effect); do not place labels far from their referents (split-attention); do not decorate.
  - Respect intrinsic load: a definition with three quantifiers and two function spaces cannot be sped up. Pacing is constrained by the material, not by stylistic preference.
  - Cultivate germane load: signal what to attend to; structure the visual hierarchy; use colour semantics consistently.
- **What to avoid.** Visual ornament; on-screen-text duplication of the voice-over; high-density frames with more than ~7 distinct elements.
- **Audience adaptation.** Beginners benefit from heavier load reduction (more signalling, more redundancy across modes); experts find the same scaffolding *adds* extraneous load — the **expertise reversal effect**.
- **Papers.** Sweller (1994); Sweller, van Merriënboer & Paas (1998); Mayer (2005); Kalyuga et al. (2003).

## 6. Worked examples

- **Definition.** Fully solved demonstrations of a problem, presented to the learner *before* they attempt to solve their own. Outperforms problem-solving for novices in well-structured domains.
- **Why it matters.** Solving from scratch costs working-memory resources that should be spent building schemas. A worked example offloads search and lets the learner focus on structure.
- **How to apply in a video script.**
  - For procedural / problem-solving content, the first example in any new technique is fully worked — every step shown, every choice justified.
  - Pair each worked example with a self-explanation prompt at non-obvious moves.
  - Follow worked examples with isomorphic problems on which the viewer attempts the structure.
- **What to avoid.** Showing only the final answer; skipping the "obvious" steps that are obvious to the author but not to the viewer; passive worked examples (no self-explanation prompts).
- **Audience adaptation.** Critical for novices; *harmful* for experts (expertise reversal). For research-level audiences, replace worked examples with structural sketches and motivating instances.
- **Papers.** Atkinson, Derry, Renkl & Wortham (2000); Sweller, van Merriënboer & Paas (1998).

## 7. Worked-example fading

- **Definition.** A graduated transition from worked example → completion problem (with a blank to fill) → fully unaided problem-solving. The fading transfers agency to the learner without the cliff of "now you do one".
- **Why it matters.** Bridges the gap between the worked-example mode and independent practice. Outperforms either pure worked examples or pure problem-solving on transfer measures.
- **How to apply in a video script.**
  - Sequence: example 1 (full); example 2 (last step blank, reveal after pause); example 3 (more blanks); example 4 (viewer attempts unaided, video shows the solution after).
  - Each blank is a 2–4 s pause with the answer revealed visually.
  - Narration scaffolds early, fades to silence by the unaided example.
- **What to avoid.** One worked example followed by abrupt "now try this" with no scaffolding in between.
- **Audience adaptation.** Compress the fading sequence for shorter videos and for more advanced audiences.
- **Papers.** Renkl, Atkinson, Maier & Staley (2002); Atkinson et al. (2000).

## 8. Multimedia learning (CTML)

- **Definition.** A theoretical framework with twelve+ design principles governing how to combine words and pictures effectively. Roughly: the verbal and visual channels are processed independently, each is narrow, and active processing is required.
- **Why it matters.** The design rules in `style/visual_language_guide.md` are downstream of CTML. Without it, design decisions about voice-over, on-screen text, and visual layout are arbitrary.
- **How to apply in a video script.**
  - **Modality**: prefer voice-over + visual over on-screen text + visual.
  - **Redundancy**: do not duplicate voice-over verbatim on screen.
  - **Spatial contiguity**: place labels adjacent to their target.
  - **Temporal contiguity**: synchronise narration with the visual event it describes (within 0.3 s).
  - **Signalling**: highlight what to look at; use colour semantics consistently.
  - **Segmenting**: chunk into discrete scenes with pauses.
  - **Coherence**: strip every visual element that does not serve the explanation.
- **What to avoid.** Decorative ornament; bullet-point reveals; dense on-screen text the viewer cannot read at narration pace; unsignalled visual changes.
- **Audience adaptation.** All CTML principles apply across tiers, but their weight changes: signalling and segmenting matter most for beginners; coherence and modality matter for everyone; redundancy violations hurt experts most.
- **Papers.** Mayer (2005, 2024); Sweller, van Merriënboer & Paas (1998).

## 9. Self-explanation

- **Definition.** A learner who generates explanations of *why* a step works learns substantially more than one who passively reviews the same content. The act of generation matters; even silent self-explanation works; even partly wrong explanations help, when followed by feedback.
- **Why it matters.** What happens *inside the viewer's head* matters more than what is on screen. A "why?" prompt is more powerful than a "what?" prompt.
- **How to apply in a video script.**
  - At each non-obvious move (a substitution, a choice of technique, a lemma), pause for 3–5 s with a self-explanation prompt: "why does this work?" or "why this choice and not the other?"
  - Reveal the explanation a beat later in the narration.
  - Spontaneous self-explanation is rare; *prompt explicitly*.
- **What to avoid.** Trivial "why?" prompts at obvious points (devalues the device); too many prompts in quick succession (cognitive overload).
- **Audience adaptation.** All audiences benefit; the prompts should target audience-appropriate non-obviousness (a research-level "why this lemma?" vs an undergraduate "why this substitution?").
- **Papers.** Chi et al. (1989); Chi, de Leeuw, Chiu & LaVancher (1994).

## 10. Active learning (in STEM)

- **Definition.** Learning environments that demand viewer engagement (predict, classify, compare, explain) outperform passive lectures by large margins. Effects are large enough that the absence of active engagement is itself a design failure.
- **Why it matters.** A video that asks nothing of the viewer is the analog of a failing lecture format. The intervention does not need to be elaborate — even brief, well-placed prompts shift the cognitive mode.
- **How to apply in a video script.**
  - Treat the absence of viewer-engagement prompts as a quality-control failure, not a stylistic choice.
  - Combine retrieval, self-explanation, and prediction prompts; vary their format.
  - The viewer is a *participant*, not an audience.
- **What to avoid.** Continuous narration over visuals with no break for viewer cognition. The "documentary" style works for entertainment, not for retention.
- **Audience adaptation.** Sustained — research-level viewers need fewer but more demanding prompts; beginners need more frequent, lighter ones.
- **Papers.** Freeman et al. (2014); Carpenter, Pan & Butler (2022).

## 11. Concreteness fading

- **Definition.** Start with a concrete instance the viewer can see, then *gradually* fade the surface features into the abstract symbolic form. The concrete-only and abstract-only conditions both lose to fading on transfer measures.
- **Why it matters.** Concrete-only anchors learning to surface features and inhibits transfer. Abstract-only loses many learners. Fading bridges them and is what enables transfer to novel concrete instances.
- **How to apply in a video script.**
  - Three-stage default: concrete instance → semi-abstract bridge (schematic, diagrammatic) → fully formal object.
  - Use *morph* animations between stages, not cuts. The visual continuity is the pedagogy.
  - End at the formal object, not at the bridge stage. Stopping at intermediate concreteness gives wrong intuitions.
- **What to avoid.** Stopping at the concrete metaphor and never reaching the formal object; presenting the formal object first and treating the concrete instance as an afterthought; using a misleading concrete metaphor where none naturally exists (e.g., "addition is like combining piles of apples" — true for ℕ, false for ordinals).
- **Audience adaptation.** Beginners need a longer concrete stage; experts can compress it to a sentence and a single visual instance before lifting.
- **Papers.** McNeil & Fyfe (2012); Fyfe, McNeil, Son & Goldstone (2014); Kokkonen, Lichtenberger & Schalk (2022).

## 12. Expertise reversal

- **Definition.** Designs that benefit novices often *hurt* experts, because the redundant scaffolding becomes extraneous load. As expertise grows, scaffolding should be faded.
- **Why it matters.** Justifies the audience-tier table in `SKILL.md` §4. A beginner video should not look like a research-level video, and vice versa.
- **How to apply in a video script.**
  - **Beginner/UG**: full worked examples, generous signalling, slow pacing, redundant verbal+visual cues, frequent retrieval prompts.
  - **Advanced/research**: drop the scaffolding. Definitions can lead. Examples can be motivating instances rather than solved templates. Pacing brisk. Prompts target deep predictions, not basic recall.
- **What to avoid.** Designing one script and then adapting it to audience after the fact. Adaptation must happen at the design phase.
- **Audience adaptation.** This *is* the audience-adaptation principle.
- **Papers.** Kalyuga, Ayres, Chandler & Sweller (2003); Sweller, van Merriënboer & Paas (1998).

## 13. Deliberate practice

- **Definition.** Skill is built by focused, effortful, feedback-rich activity at the edge of current capability. A video is not deliberate practice; at best, it primes deliberate practice.
- **Why it matters.** A reality check on what a video can deliver. Conceptual videos can transmit understanding; skill is built by what the viewer does *between* videos.
- **How to apply in a video script.**
  - When the script's objective is skill acquisition (algorithm execution, derivation fluency, problem-solving), the closing scene should hand off to a deliberate-practice activity, not conclude self-sufficiently.
  - Recommend feedback-rich exercises ("try this on the following five problems before moving on; each comes with worked solutions").
  - Be honest about scope: "this video introduces; it does not build skill on its own."
- **What to avoid.** Implying that watching the video *is* the learning. It is the priming; deliberate practice is the building.
- **Audience adaptation.** All audiences benefit from clear hand-off; the recommended deliberate-practice activities differ by tier.
- **Papers.** Ericsson, Krampe & Tesch-Römer (1993).

## 14. Metacognition and self-regulated learning

- **Definition.** Knowing what you do and do not know. Skilled learners monitor their own understanding, set goals, and reflect on outcomes. Unskilled learners are systematically overconfident — feeling-of-knowing diverges from actual knowing.
- **Why it matters.** A viewer's subjective sense of "I understood that" is a poor guide to what they actually retained. The script can engineer calibration moments that correct overconfidence.
- **How to apply in a video script.**
  - Pair retrieval prompts with calibration commentary: "if you are surprised, that is the point — the next scene shows why."
  - Optional opening prompt: "what do you want to be able to do after this?" (goal-setting).
  - Closing reflection prompt rather than a self-contained summary.
  - Refutation framing: name the misconception explicitly, then refute. More effective than stating the correct concept alone.
- **What to avoid.** Always confirming the viewer's intuition (no calibration); engineered confusion that does not resolve quickly.
- **Audience adaptation.** All audiences. Goal-setting prompts can feel didactic in short-form videos; use sparingly.
- **Papers.** Panadero (2017); Metcalfe (2009).

---

## Cross-principle synthesis

Some pairs of principles compound: retrieval × spacing → successive relearning; concreteness fading × worked examples → graduated abstraction; interleaving × self-explanation → comparative discrimination. These compounds are usually stronger than either component alone. When a script uses one of these compounds, name it explicitly in pedagogical-design notes.

Some pairs are in tension: scaffolding (worked examples, signalling, redundancy) helps novices but creates extraneous load for experts (expertise reversal). The script must pick a tier and design for it; trying to satisfy both is a quality failure.

The deepest cross-principle commitment: **mathematical and conceptual correctness is non-negotiable**. Learning science is the route into the concept, not a permission to soften the concept.
