# Visual Creativity Protocol

The single most important file in the skill. Every other artefact resolves against the **richness of visual imagination** declared here. A specification of motion verbs (`04_visual_language.md §4.5`) tells the model *what motion is available*. This file tells the model *which motion to choose* — and forces the act of imagination that decides.

This file is read **before writing `03_scene_architecture.md`** and **referenced again before every scene** in `05_narration_script.md`.

---

## §0 — The thesis

Most educational videos fail because their authors imagine the explanation as *text with pictures attached*. The result is a slide deck with voice-over: a formula appears, a label points at it, an arrow grows, the next slide. The animations are decorations on the prose.

A great educational video inverts this. The **animation is the argument**. The narration explains what the eye is already seeing. Remove the text, and a competent viewer still understands the concept — perhaps imperfectly, but the *shape* of the idea lands. Add the text back and you have rigour. Add motion and rigour together and you have a video that teaches at a level prose cannot reach.

This file exists to force that inversion.

---

## §1 — The Visual Imagination Brainstorm (mandatory pre-scene step)

Before writing the rows of any scene in `05_narration_script.md`, generate this brainstorm in working memory or in a scratchpad. The brainstorm itself does not appear in the delivered files — but its output is what makes the scene worth watching.

### Step 1 — Name the conceptual content of the scene

In one sentence, what does the viewer need to *recognise* after this scene? Not what they need to *know* — what they need to *recognise*. Recognition implies the structure has become visible.

> Example: "After this scene, the viewer recognises that a derivative is the slope of a tangent, and that the tangent is the limit of secants."

### Step 2 — Generate 3–5 candidate visual approaches

Each candidate is a complete answer to "what would the viewer literally see for 10–30 seconds that conveys this content". Be specific about objects, colour, motion. No fragments.

Force yourself to generate genuinely different approaches. If candidates 1 and 2 are both "show the formula and animate parts of it", you have not brainstormed. You have repeated the same idea.

> **Candidate A — Secants collapsing into tangent.** A smooth curve in teal; a second point Q on the curve, connected to P by a secant line in amber. Q slides toward P over 6 s; the secant slope is shown as a number tracker. As Q → P, the secant rotates and snaps onto the tangent (white). The number tracker stops at f'(x).
>
> **Candidate B — Local linearisation zoom.** A curve at full scale; the camera zooms in on a single point over 8 s by factor 1000×. As we zoom, the curve visibly straightens — at the limit, the curve and its tangent are indistinguishable. The derivative *is* this asymptotic straightness.
>
> **Candidate C — Velocity from position.** A particle moves along a 1D line, position x(t) traced above as a curve. A vertical bar shows the particle's current velocity, lengthening and shortening as the slope of x(t) changes. The bar's length **is** the derivative.
>
> **Candidate D — Slope field.** The (x, y) plane; at every grid point, a small line segment with slope f'(x). As we trace a curve through this field, the segments are always tangent. The derivative is the local "weather" of the function.
>
> **Candidate E — Difference quotient as parameter.** A horizontal slider `h` from 1 down to 0; for each value of h, the secant from x to x+h is drawn live; as h → 0, the secants pivot smoothly onto a single line.

### Step 3 — Rank the candidates by three criteria

| Criterion | Question |
|---|---|
| **Inevitability** | Does the animation make the concept feel *forced* by the visual, or merely *illustrated*? The best animations make the viewer think "of course it has to be this." |
| **Audience fit** | Does the candidate match the audience tier (see §3 below)? An undergraduate candidate may bore an expert; a research candidate may lose a beginner. |
| **Conceptual purity** | Does the animation focus on the *concept* or on the *machinery*? A candidate that needs three setup objects to convey one idea is impure. |

For the derivative example: candidate A is excellent for beginners; candidate B is striking and works for all tiers; candidate C connects to physics intuition; candidate E reveals the algebraic structure (the parameter h is visible). Candidate D is a *consequence* of the derivative, not the derivative itself — weaker.

### Step 4 — Elite-creator stress test

Before locking in the winner, ask:

> **Which elite creator's signature does my chosen candidate most resemble — and if I were that creator, what would I do differently here?**

Cross-reference `style/elite_explainer_doctrine.md §2` (creator signatures). If the topic is fundamentally a physical phenomenon and the chosen candidate is a 3B1B-style continuous morph, a Veritasium-style counter-experiment with real footage might land harder. If the topic is mathematical and the chosen candidate uses a Kurzgesagt-style mascot, you have probably picked a less rigorous register than the topic deserves. Pick deliberately.

Then ask the second question:

> **What would the iconic frame of this scene look like as a still?**

If you cannot picture it, the candidate is still too abstract. Sketch the frame in your scratchpad — composition, colour, dominant object — before writing the row.

### Step 5 — Pick the winner and write its row(s)

Write the chosen candidate as a row (or sequence of rows) in `05_narration_script.md`. The "On-screen" column should specify the candidate completely.

When in doubt between two strong candidates, **use one as the main scene and the other as the cross-domain echo or boundary scene**. Strong candidates rarely waste themselves — they teach somewhere.

---

## §2 — The two tests of visual quality

### §2.1 — The Inevitability Test

> *If the narration were silent, would a viewer in the target audience derive the right gestalt of the concept from the animation alone?*

If yes, the animation is doing the work. If no, the animation is decoration and the prose is doing the work — which means you have a podcast with pictures, not a video.

This does **not** mean every scene must be silent-comprehensible — formal statements need words. It means that the *conceptual core* of every scene must be encoded in the motion. The voice-over rigorises what the motion has already shown.

### §2.2 — The Frozen Frame Test

> *If I freeze the video at any moment and hand the still frame to a colleague, can they explain what the video is talking about?*

A still from a slide-paradigm video is mostly text and a static decoration. A still from a rich animation is a *figure* — something that could appear in a textbook, with axis labels, a coordinate system, an object in motion, a relationship visible. Stills from your video should look like the best figures from the best papers.

This is a discipline: it forces every frame to carry information.

---

## §3 — Audience-tier visual calibration

The audience tier (§5 in `SKILL.md`) determines the *register* of the visual imagination. Use this matrix when picking among candidates and when designing each scene.

| Tier | Primary visual register | Concrete material | Abstraction level | Example for "derivative" |
|---|---|---|---|---|
| **Absolute beginner** | physical metaphor; objects with mass / friction / shadow | ball rolling, water level, fabric stretching, light beam, marble on track | symbol-poor; numbers only when they tell a story | a marble moving along a curved track; an arrow attached to it shows its instantaneous direction |
| **Undergraduate** | geometric construction with explicit coordinates | drawn curves, axes, labelled points, secant lines | symbol-aware; standard notation introduced explicitly | the canonical secant-collapses-to-tangent animation (candidate A above) |
| **Advanced UG / master's** | structural diagrams; parameter spaces; high-dimensional projections | manifold patches, transition maps, vector bundles, deformation families | symbol-fluent; rich notation; quantifiers visible | tangent space at a point: $T_p M$ shown as the limit of secant directions on $M$ |
| **Research / expert** | morphisms; commutative diagrams; categorical structure animated | functors, natural transformations, parameter spaces, moduli | symbol-dense; structural compression preferred | derivative as functor: tangent bundle $TM \to M$ as a continuous assignment, with naturality animated |
| **Mixed** | progressive lift across the scene sequence | start beginner; lift to UG by scene 3; touch expert in synthesis | scale the symbolic density across scenes | scene 1 (marble) → scene 2 (secants) → scene 3 ($T_p M$) |

Mixed audience is the **default for most YouTube-style videos**. Plan the lift explicitly in `03_scene_architecture.md`.

---

## §4 — Canonical visual patterns library

These are tested, reusable visual recipes for common concept types. They are **starting points**, not constraints. Use them as a thinking tool when brainstorming: ask "which of these resonates with my concept, and how do I adapt it?"

### §4.1 — Calculus and analysis

**Limit / convergence.** A sequence of objects $x_1, x_2, \ldots$ each drawn slightly closer to the target; previous iterates fade to 30% opacity (trail). At a chosen $n^*$, a $\varepsilon$-ball appears around the limit; all $x_k$ for $k > n^*$ visibly inside the ball.

**Derivative.** Secants collapsing to tangent (candidate A above). Alternative: local zoom revealing asymptotic straightness (candidate B). Sequel: the derivative *as a function* — second curve below the first, with the slope of the upper curve becoming the height of the lower curve, animated live as a vertical scanner moves left-to-right.

**Integral (Riemann).** Rectangles built from coarse partition to fine partition; on each refinement, the rectangles tighten against the curve; total area number tracker converges to the true integral. The shaded region between curve and axis is the *invariant*; the rectangles are the *approximation*.

**Fundamental theorem of calculus.** Two coupled animations side by side. Left: a curve $f(t)$; a scanner moves left to right. Right: the accumulated area under $f$ up to the scanner's $t$, plotted as $F(t)$. As the scanner moves, the slope of $F$ at $t$ equals the height of $f$ at $t$ — make this visually undeniable by showing both as synchronised vertical bars.

**Taylor series.** Polynomial approximations of increasing degree, each drawn over the target function in successively brighter amber. At each degree, a residual curve below shows $f - P_n$ — visibly smaller with $n$. Optional: a "Taylor expansion is local" beat — at the point of expansion, all polynomials agree; far away, only high-degree ones track the curve.

**Continuity (ε–δ).** A point $x$ on the domain; image $f(x)$ on the codomain. An $\varepsilon$-ball appears around $f(x)$. The viewer is asked: "what neighbourhood of $x$ maps inside this ball?" A $\delta$-ball appears around $x$, shrinking until its image fits inside the $\varepsilon$-ball. The video animates this for arbitrary $\varepsilon$.

### §4.2 — Linear algebra

**Linear map.** The plane deforms under the matrix $A$: grid lines bow, parallelograms shear, the unit square morphs into the column-vector parallelogram. Determinant = signed area of the morphed square, shown as a number tracker.

**Eigenvectors.** A unit circle of vectors; each vector $v$ animated to its image $Av$. Most vectors rotate; a few (the eigenvectors) only scale — they stay on their own line. Highlight the eigenvectors when their image is collinear with them, holding them in colour while the others rotate.

**Determinant.** Animate the unit cube deforming under the matrix; show the signed volume scaling factor as a number tracker. A negative determinant: the cube *inverts* through itself — the orientation reverses, indicated by a colour flip on one face.

**Change of basis.** Two coordinate systems overlaid on the same plane; the same vector shown twice with two coordinate representations. As basis vectors morph from old to new, the labels on the vector's coordinates change but the vector itself does not move — make the vector's identity the invariant.

### §4.3 — Geometry and topology

**Manifold / chart / atlas.** A 2D surface in 3D ambient space (sphere, torus). A small patch of the surface morphs (flattens) into a 2D coordinate chart in a side panel; the chart map $\varphi$ is shown as a coupling between corresponding points. Multiple charts cover the surface; transition maps animated where charts overlap.

**Homotopy.** Two paths between the same endpoints; a continuous family $H(s, t)$ animated by parameter $s$ from 0 to 1; the first path morphs into the second through intermediate paths, all drawn faintly as trail.

**Group action.** A geometric object (square, triangle, sphere) with the group elements as arrows in a separate panel. Click an element: the object rotates / reflects / translates accordingly. Orbit highlighted by union of all images.

**Topology vs metric.** A torus deforming continuously into a coffee mug (the classic), but with the *invariants* highlighted: the hole count stays equal to 1 throughout; a closed loop around the handle stays non-contractible.

### §4.4 — Probability and statistics

**Probability density.** A scatter cloud of $N=1000$ points drawn from the distribution; opacity per point proportional to local density; cloud breathes (jitters slightly) to show samples are realisations, not the distribution.

**Convergence in distribution (CLT).** A histogram of sample means built from samples of sizes $n = 1, 2, 5, 30, 100$; with each $n$, the histogram morphs visibly closer to a Gaussian; the Gaussian curve is overlaid in invariant teal.

**Bayes' theorem.** A 2D probability cloud in amber (the prior). Evidence arrives as a likelihood surface in mint (a stripe across the cloud where the data is consistent). The cloud morphs: density outside the stripe drops to 0; remaining density rescales to integrate to 1. The result is the posterior, shown still in amber but now concentrated.

**Markov chain.** Nodes for states; tokens for probability mass. At each step, each token splits according to transition probabilities and the pieces flow along edges to neighbour states. After many steps, mass settles into the stationary distribution; node sizes proportional to stationary mass.

**Stochastic process / sample path.** Multiple sample paths drawn simultaneously in faint teal; one bold sample path in amber; the marginal distribution at a given $t$ shown as a vertical density slice — establishes the object-vs-representation distinction (Doctrine Pillar I.5).

### §4.5 — Differential equations and dynamics

**Vector field / phase portrait.** Grid of small arrows showing $\dot{x} = f(x)$ at each point. Trajectories drawn live by integrating from a few initial conditions; particles flow along the field.

**Fixed point and stability.** Phase portrait near an equilibrium; trajectories spiralling in (stable focus), out (unstable focus), or saddle. The fixed point pulses once when a nearby trajectory reaches it.

**Gradient descent.** A loss surface in 3D; a marble released from an initial point follows the negative gradient flow. Multiple initial conditions; some end in different local minima — convergence is not unique.

**Bifurcation.** A parameter $\mu$ slider; the phase portrait redraws as $\mu$ changes; at a critical $\mu^*$, the qualitative structure changes (a fixed point splits, a limit cycle appears). The bifurcation diagram drawn in a side panel: parameter on horizontal axis, fixed-point locations on vertical, branches forking at $\mu^*$.

### §4.6 — Fourier and signal processing

**Fourier decomposition.** A wave $f(t)$ on the left; on the right, a stack of rotating circles (epicycles), each at a Fourier frequency, with the tip of the chain tracing $f(t)$. Increasing the number of circles refines the approximation. This is the 3Blue1Brown canonical animation; reuse and adapt.

**Convolution.** Two functions $f, g$; flip $g$ to get $g(-\tau)$; slide it across; at each position $t$, integrate $f(\tau) g(t - \tau) d\tau$; the result $(f * g)(t)$ traced live as $t$ advances. All three operations (flip, slide, integrate) visible.

**Phase vs amplitude.** A complex-valued signal as a rotating arrow; its real part traced below; its modulus traced as height of envelope; argument shown as colour cycling.

### §4.7 — Optimisation and learning

**Stochastic gradient descent.** Loss surface; a marble bouncing around (the noise) but with a *drift* toward the minimum. Toggle batch size: as it grows, the noise shrinks and the drift dominates.

**Backpropagation.** Computation graph drawn as a DAG; forward pass animates left-to-right, lighting up nodes as activations propagate; backward pass animates right-to-left in a contrasting colour, lighting up gradients.

**Overfitting.** Training data fixed; a model curve animated as training proceeds; the curve initially smooth, then wiggling more and more to thread every training point; meanwhile, a held-out validation curve grows error.

### §4.8 — Algebra and abstract structures

**Quotient / equivalence classes.** Plane partitioned into equivalence classes (cosets); each class drawn as a coloured region. Animate the quotient: classes collapse into single points on a new coordinate system.

**Universal property.** A diagram with three objects and a candidate morphism; the universal one drawn in teal; alternative morphisms drawn in amber; the alternatives "snap" into the universal one to show uniqueness up to isomorphism.

**Category / functor.** Two categories side by side; objects as nodes, morphisms as arrows; functor as a structure-preserving mapping between them. Animate a composition: $F(g \circ f) = F(g) \circ F(f)$ shown by simultaneously composing in both categories.

### §4.9 — Physics

**Wave / oscillation.** Standing wave: time evolution with the wave pattern oscillating; amplitude vs time at a chosen point traced below; spatial wavelength visible.

**Conservation law.** Two quantities (e.g., kinetic and potential energy) plotted as bars; one rises as the other falls; their sum drawn as a constant horizontal line — the invariant.

**Field lines.** A point charge or mass; field lines drawn radially; insert a second charge of opposite sign and animate the field lines bending and reconnecting (electric dipole).

**Phase space (Hamiltonian).** Position $q$ vs momentum $p$; trajectories drawn as level curves of the Hamiltonian; for a pendulum, the libration / rotation transition visible at the separatrix.

### §4.10 — Algorithms and computation

**Sort.** An array of bars of varying heights; the algorithm's swaps animated; the sorted region (in teal) grows from one end; comparisons highlighted by colour flashes.

**Recursion.** Call tree drawn live as the algorithm executes; each recursive call adds a child node; return values flow back up the tree.

**Hash function / hash table.** A bucket array; inputs animated falling into buckets according to the hash; collisions resolved visibly (chaining or probing).

**Graph algorithm (BFS / DFS).** Graph drawn; the frontier expanded one layer at a time (BFS) or one branch at a time (DFS); explored nodes filled in teal; current frontier in amber.

---

## §5 — Banned slide-paradigm phrasings

The following phrasings, when they appear in `05_narration_script.md`'s "On-screen" column, indicate a slide-paradigm failure. Reject them on review.

| Banned phrasing | Why it fails | Replacement strategy |
|---|---|---|
| "the formula appears" | a frame containing a formula is not a scene | specify what is animating *around* the formula (object the formula describes, parameter being varied, subexpression being highlighted) |
| "show the definition" | passive; no motion specified | describe the object the definition is *about* and animate it; the definition is the corner companion |
| "introduce concept X" | hides the visual choice in a generic verb | answer "what does the viewer *literally see*?" |
| "diagram fades in" with no further motion | states the entry but not the content | specify what changes after the diagram is on screen |
| "the slide shows…" / "next we display…" / "the screen presents…" | these are slide-deck verbs; the medium is animation | reframe in terms of motion |
| "text slides in from the left" / "text fades in word by word" | text choreography is decoration | use `write` for entrance and put the conceptual motion elsewhere on screen |
| "we see that…" / "as you can see…" | shifts authority to the viewer's observation rather than the visual; also banned narration | replace with the actual visual event |
| "explain how X works" | not a visual at all; a stage direction | brainstorm 3–5 candidates per §1 |
| "an animation showing the relationship" | non-specific; non-binding | name the objects, the parameter, the invariant |

---

## §6 — Forcing functions when imagination stalls

When stuck, run through these prompts in order. Stop when one breaks the block.

1. **What is the parameter?** Every concept has at least one parameter to vary. Make that parameter a visible slider or progress bar. What happens as the parameter varies?
2. **What is invariant?** Every concept has something held fixed. What is it? Hold it visibly fixed while everything else changes.
3. **What is the physical intuition?** If the concept could be illustrated by a physical system (mass on spring, water, light, fabric, marbles, sand), how would it look? Beginners and undergraduates respond strongly to physical intuition even for abstract concepts.
4. **What is the worst representation?** Sometimes generating a *bad* visual reveals what the *good* one must avoid. If "show a formula" is bad, what is its opposite?
5. **What is the universal example?** Every concept has one or two canonical instances every textbook uses. Animate that instance well; then generalise.
6. **What does the concept *enable*?** Concepts justify their existence by what they let you do. Show the use case dynamically: a problem unsolvable before the concept, dissolved by it.
7. **What is the cross-domain echo?** The Doctrine Pillar IV scene is required anyway. Brainstorm the echo early — sometimes the echo is the cleaner visual and should drive the main scene.

---

## §7 — Aesthetic principles (the 3Blue1Brown / Ben Eater / Veritasium register)

What separates a great educational animation from a merely correct one:

- **Restraint.** One conceptual move per scene. The viewer's eye should be *led*, not assaulted.
- **Permanence.** Objects survive between scenes when their meaning survives. The teal manifold from scene 2 is recognisable in scene 5.
- **Synchronicity.** When the voice says "and this becomes…", the visual *becomes* in that instant. The verb in narration aligns with the visual verb.
- **Reveal, don't display.** The viewer should feel the concept *emerging* rather than being *shown*. Build up: object first, then label, then formula. Never the reverse.
- **Use silence.** A 1.5–3 s silence with a held visual lands deeper than a continuous voice-over. The pause is when the concept settles.
- **Use cuts sparingly.** Manim's defaults encourage continuous motion. Hard cuts are reserved for register changes (e.g. transition from animation to live-action footage; from one domain to its echo).
- **The camera is a narrator.** A zoom-in says "this matters". A pull-out says "remember the context". An orbit says "see this from another side". Use camera moves intentionally, never reflexively.

---

## §8 — Output: where the brainstorm leaves a trace

The brainstorm itself is internal. But traces of it must be visible in the delivered files:

- `03_scene_architecture.md` §3.X for each scene: a one-paragraph "visual strategy" describing the chosen candidate's conceptual function (not its execution details — those go in §4 and §5).
- `04_visual_language.md` §4.5/§4.6: the chosen primary motion verbs and the structural concept's visual signature.
- `05_narration_script.md` §5.3: each row's "On-screen" column specifies the chosen animation completely.
- `10_manim_blueprint.md`: parameter-level implementation of the chosen animation.
- `11_rigor_audit.md` §11.X: include a "visual creativity audit" — for each major scene, confirm that the §2 Inevitability Test and Frozen Frame Test pass.

If any scene's "On-screen" column reads like a slide description (an object simply appearing), the script has skipped the brainstorm. Reject and revise.

---

## §9 — Quick reference card

When in doubt, the protocol in one paragraph:

> Before writing each scene, name what the viewer must *recognise* by the end. Generate 3–5 distinct candidate visuals — not variations, but genuinely different approaches (physical metaphor, parametric sweep, structural diagram, cross-domain echo, computational trace). Rank by inevitability, audience fit, conceptual purity. Pick the winner. Write its rows in `05_narration_script.md` with the parameter being varied, what changes, and what is held invariant fully specified. Apply the Inevitability Test (silent comprehension) and the Frozen Frame Test (each still readable as a figure). If both fail, re-brainstorm.
