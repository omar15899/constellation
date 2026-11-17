# Ultra-Formal / Ultra-Intuitive Doctrine

This reference develops the [shared teaching method](../../../core/teach-from-first-principles/SKILL.md) for time-bound audiovisual explanations. The [skill entrypoint](../SKILL.md) determines the requested deliverables and which resources to read.

The four pillars govern conceptual accuracy and explanatory structure. The numbered files, durations and presentation patterns below describe a full production format; adapt them to the requested artifact rather than requiring a fixed file stack.

---

## Pillar I — Layered exposition (the §X.0 / §X.1+ pattern)

**Claim.** Every technically dense moment in a video is presented in two passes. *First* the conceptual preamble (the analogy, the metaphor, the problem statement, the "what is about to happen and why"); *then* the formal treatment (the definition, the equation, the construction, the proof step). Never reverse the order. Never skip the preamble.

This is not pedagogical decoration for beginners; it is the **correct epistemic order**. Mental models precede symbol manipulation. A viewer who has not been told "we are about to model X as a Y because Z" will not absorb the formal X = Y when it appears, regardless of expertise. The expert benefits from the preamble too — it anchors the precise role of the formalism in *this* video, which may differ from how they have seen it before.

### Mechanics in a video

In the second-by-second narration script (`05_narration_script.md`), every formal block is preceded by a **conceptual beat** of 8–25 seconds tagged `[PREAMBLE]`. Concretely:

| Position | What happens | Tag in script |
|---|---|---|
| Just before a definition | Analogy, metaphor, problem statement that creates the *necessity* of the definition | `[PREAMBLE]` |
| The definition itself | Formal statement, on screen and narrated | `[FORMAL]` |
| Just after | One concrete instance the viewer can hold | `[INSTANCE]` |
| Optional | Boundary case: what fails if you weaken the definition | `[BOUNDARY]` |

The preamble carries no notation. No equation appears on screen during it. The visual is the metaphor. When the preamble ends and the formal block begins, the metaphor either *morphs into* the formal object or *fades* while the formal object enters — never a hard cut from "metaphor world" to "formal world".

### Canonical models from OmarOS

`06_Knowledge_Base/Computing/Concurrency/python_asyncio.md` is the master reference for this pattern. Sections §§II.0, III.0, VI.0, VIII.0, XI.0, XII.0, XVI.0 each demonstrate the preamble→formalism move. When designing a video preamble, mentally translate one of these section preambles into a 15-second visual beat: which analogy carries the concept, what does the camera see, when does the formalism arrive?

---

## Pillar II — Jargon transparency (the inline-definition discipline)

**Claim.** Every English technical term, design-pattern name, or acronym used in narration or on screen is defined on its first occurrence — inline, briefly, even if the audience "knows" it. A term known in isolation may carry a *specific role* in this video that the inline definition pins down.

### Mechanics in a video

- **In narration** (`05_narration_script.md`, `06_voiceover.md`): the first occurrence reads as `<term> — that is, <8–15 word working definition for this video>`. The em-dash construction is the standard form. Once defined, the term may be used unmodified for the rest of the video.
- **On screen** (`04_visual_language.md`, `08_storyboard.md`): the first appearance of a term as text is accompanied by a 1.0–1.5 s pop-in of a small grey definition tag below or beside it. The tag fades after 3 s; the term remains.
- **In assets** (`09_image_prompts.md`, `10_manim_blueprint.md`): the asset prompt explicitly includes the working definition so the rendered frame carries it.

### Examples of terms that always require an inline definition

`scheduler`, `placeholder`, `handle`, `driver`, `backpressure`, `garbage collector`, `monkey-patch`, `fast path`, `fire-and-forget`, `RAII`, `RTT`, `throughput`, `DAG`, `scope`, `lifecycle`, `entry point`, `ownership`, `fairness`, `syntactic sugar`, `overhead`, `eager`, `lazy`, `GIL`, `callback`, `hook`, `wrapper`, `polymorphic dispatch`, `trait`, `mixin`, `kernel`, `tensor`, `embedding`, `gradient`, `loss`, `regulariser`, `manifold`, `chart`, `pushforward`, `pullback`, `martingale`, `filtration`, `numéraire`, `hedge`, `discount factor`. The list is illustrative, not exhaustive.

The discipline applies even when the audience tier is *research/expert*. Compression of the definition is allowed (3–5 words instead of 8–15) but elision is not.

---

## Pillar III — Three-layer definitions (fundamental → rigorous intuition → personal vision)

**Claim.** Every load-bearing definition or theorem in the video is presented at three layers. The video does not have to dwell at every layer for the same duration, but all three must be visible somewhere in the artefact set.

### The three layers

1. **Fundamental.** The most abstract, categorical, minimal-structure form. The version that survives in any setting where the concept makes sense. This is the *canonical* statement. It lives in `01_conceptual_blueprint.md` (§ Three-Layer Definitions) and appears on screen at the formal block in `05_narration_script.md`.

2. **Rigorous intuition.** Why this is the *right* definition. What fails if you weaken each condition. Compressed proofs of why the definition is forced. This is the *justification* layer. It lives in `01_conceptual_blueprint.md` (§ Why this definition) and is voiced — in compressed form — during the post-definition beat in `05_narration_script.md`.

3. **Personal vision.** What the concept reveals about the structure of mathematics, physics, computation, or whatever ambient terrain the video lives in. The cross-domain echo. The "this is the same shape as X in domain Y" observation. This is the *unification* layer. It lives in `01_conceptual_blueprint.md` (§ Cross-domain echoes) and is voiced — once, near the synthesis movement — in `05_narration_script.md`.

A concrete example is mandatory after every abstract definition. The example lives in `05_narration_script.md` directly after the formal block, tagged `[INSTANCE]`.

---

## Pillar IV — Cross-domain unification (the "same structure, different domain" rule)

**Claim.** Every video that touches a load-bearing concept must surface, at least once, the observation that *this same structure appears in a different domain*. Not as decoration — as the deepest pedagogical move available. The viewer leaves the video knowing not only what the concept is, but where else it lives.

### Canonical bridges (use whichever fits the topic)

| Bridge | When to deploy |
|---|---|
| Finance ↔ stochastic calculus ↔ measure theory ↔ functional analysis | Any pricing, hedging, risk-neutral, martingale story |
| Numerical methods ↔ functional analysis ↔ variational principles ↔ physics (PDEs, Lagrangians) | Any approximation, projection, energy-minimisation story |
| Category theory ↔ type theory ↔ logic ↔ geometry | Any structural / morphism / universal-property story |
| Physics ↔ differential geometry ↔ variational calculus ↔ mechanics | Any field theory, gauge, action-principle story |
| Probability ↔ measure theory ↔ ergodic theory ↔ statistical mechanics | Any large-numbers, equilibrium, ensemble story |
| Spacetime ↔ smooth manifolds ↔ fibre bundles ↔ gauge theory | Any geometric-physics story |
| Algorithm ↔ recursion ↔ induction ↔ structural recursion in proof theory | Any computation-as-proof story |
| Concurrency ↔ process algebra ↔ category theory ↔ linear logic | Any composition / interaction story |

### Mechanics

The cross-domain echo is articulated in:

- `01_conceptual_blueprint.md` (§ Cross-domain echoes) — written in detail, with the structural correspondence laid out.
- `05_narration_script.md` — voiced once, in the synthesis movement (§ Movement IV equivalent), as a 10–20 second beat.
- `08_storyboard.md` — visualised once, typically as a split-screen or side-by-side morph showing the same diagram appearing in two domains with relabelled axes.

---

## Master simplification — "essence at maximum compression"

The doctrine's binding clause. Every concept the video carries must be reduced to its **essence at maximum compression** — the shortest possible statement of what the object *is* and what it *does*, free of incidental machinery. This is the moment the video earns its keep.

The essence statement lives in `00_declaration.md` (§ The single-sentence essence) and is voiced — verbatim — at the apex of the synthesis movement in `05_narration_script.md`.

This is *not* a slogan. It is the ultra-compressed formal kernel: the categorical definition, the universal property, the variational principle, the conservation law, the fixed-point equation, whichever one-line object the rest of the video has been preparing the viewer to recognise.

The discipline: if the essence cannot be stated in one sentence, the video has not yet understood the concept it is teaching. Iterate the essence statement until it does.

---

## Hard constraint — rigour over engagement

Pedagogical optimisation may simplify the **route into** a concept. It may not simplify the **concept itself**. Do not soften definitions, do not blur quantifiers, do not present examples as if they were definitions, do not replace formalism with vague intuition under the banner of accessibility. When research and rigour appear to conflict, rigour wins.

Every scene is tagged `[FORMAL]` or `[INFORMAL]` in `11_rigor_audit.md`. An `[INFORMAL]` segment never carries the rhetorical weight of a `[FORMAL]` one. If a metaphor is partial, name its limit explicitly in the narration *and* in the audit.

This constraint is the reason the skill can claim to be *both* ultra-intuitive *and* ultra-formal. The intuition is the route; the formalism is the destination. Neither is sacrificed.
