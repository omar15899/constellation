# Architecture Diagnosis — Production Track Upgrade

Date: 2026-05-15
Trigger: User request to harden the skill into a production-grade Manim animation pipeline. Central problem: AI agents currently jump from prose (narration / storyboard) to Manim code without an intermediate shot-level animation specification, producing vague, generic, slide-paradigm output.

## 1. What the current skill already does well

- **13-file deterministic pipeline** (INDEX, 00_declaration through 11_rigor_audit). Strong scaffolding via `scripts/scaffold_pipeline.py` and structural validation via `scripts/validate_pipeline.py`.
- **Doctrine layer is rich on the conceptual / pedagogical / aesthetic side**: `style/ultra_formal_intuitive_doctrine.md`, `style/elite_explainer_doctrine.md`, `style/visual_creativity_protocol.md`, `style/visual_language_guide.md`, plus 24 cognitive-science papers integrated into `learning_research/`.
- **Phase gates**: the declaration is a contract that must be approved before any other artefact is filled.
- **Validator** checks: file presence, frontmatter, status, INDEX cross-refs, verbatim essence, `[PREAMBLE]` → `[FORMAL]` ordering, `[ESSENCE]` cardinality, `[PAUSE Ns]` markers.
- **Animation richness test** (driving parameter / continuous change / invariant) is already articulated in `SKILL.md` §8.
- **Two visual-quality tests** (Inevitability, Frozen Frame) are already named in `SKILL.md` §8.

## 2. What is missing for production-grade AI animation

- **No machine-readable shot specification.** The current `08_storyboard.md` is a human-readable frame breakdown; `09_image_prompts.md` is for static AI image generation; `10_manim_blueprint.md` is parameter-level Manim notes — none of these is a binding, deterministic, per-shot animation contract a downstream Manim agent can implement against without re-inventing visual design.
- **No reusable-component plan.** No artefact tells the implementer "use the `BasisTicker` component here" rather than draw a ticker from scratch.
- **No asset / data manifest.** Numerical values, ticker series, image assets are not centralized; magic constants leak into scene files.
- **No formal render-validation rubric.** The rigor audit covers narration/visual discipline at the doctrine level but does not score a finished render against the spec.
- **No formal hierarchy of authority** preventing a "convenient" implementation choice from overriding the pedagogical or conceptual layer.
- **No formal failure protocol.** When the spec is incomplete, there is no doctrine for `MISSING_SPEC` / `CONTRADICTION_REPORT` / `NEEDS_HUMAN_REVIEW` — the agent is free to invent.
- **No specialised downstream agent prompts** binding a Manim implementer to spec-only authority.
- **No "anti-aesthetics" doctrine** explicitly listing what to reject (corporate explainer, crypto promo, slide deck, particle-field nonsense).

## 3. Where the new doctrine should live

The new doctrine is too large and too important to live inside SKILL.md (already 377 lines). It will live in a new top-level subtree:

```
production_track/
  README.md
  doctrine/          ← 16 short doctrine files, one rule each
  templates/         ← shotlist, animation_spec.yaml, manifests, component library, rubric
  prompts/           ← 5 downstream-agent prompts
  examples/          ← worked example (vague vs spec)
```

SKILL.md gains a new §14 "Production Track" that introduces the prime directive, the canonical artefact stack, the hierarchy of authority, the failure protocol, and points to the production_track/ tree for everything else. The existing 13-file pipeline is preserved for purely conceptual / pedagogical / narrative work; the production track is **mandatory** when Manim implementation will follow.

## 4. Does the current skill allow direct prose-to-code generation?

**Yes** — and this is the central problem. The current pipeline ends at `10_manim_blueprint.md`, which is a paragraph-and-parameter-level reference, not a per-shot deterministic contract. Nothing in the current doctrine prevents Claude (or a downstream Manim agent) from reading `05_narration_script.md` + `10_manim_blueprint.md` and inventing visual design while writing code. The animation richness test catches *some* under-specification, but it operates at scene grain, not shot grain, and it asks only three questions — it does not enforce per-object position, colour, easing, keyframes, persistence, semantic role, etc.

## 5. Changes needed to prevent vague animation outputs

The structural fix is the **animation spec layer** (`09_animation_spec.yaml`), which is mandatory before any Manim code is written. The Manim implementation agent is bound, by its own prompt, to refuse to invent visual design from the narration script; if the spec is incomplete it must emit `MISSING_SPEC` rather than improvise.

Around that core artefact, the upgrade installs:

- **Prime directive** (`production_track/doctrine/00_prime_directive.md`): No Manim code from vague prose. Only Manim code from explicit shot-level animation specifications.
- **Hierarchy of authority**: concept > pedagogy > scene function > narration timing > visual language > shot spec > animation spec > implementation. Code may never override a higher layer for convenience.
- **Semantic visual language**: colours, motion, screen text, formulas, metaphors — each a doctrine file.
- **Failure protocol**: 5 explicit failure modes (`COMPLETE_SPEC` / `PARTIAL_SPEC_WITH_ASSUMPTIONS` / `MISSING_SPEC_REPORT` / `CONTRADICTION_REPORT` / `NEEDS_HUMAN_REVIEW`) and the `MISSING_SPEC:` block format.
- **Render validation rubric** (5 axes): pedagogical, cinematic, semantic, technical, Manim — each with explicit pass/fail questions.
- **Downstream agent prompts** (5 of them): one per pipeline role, each bound by its authority and forbidden surfaces.

## 6. Preserved (legacy, still in use for conceptual/narrative work)

- `templates/08_storyboard_template.md` — still scaffolded; the production track's `08_shotlist` supersedes it for implementation work but the narrative storyboard remains useful for non-Manim modalities.
- `templates/09_image_prompts_template.md` — still relevant for generative-image modality.
- `templates/10_manim_blueprint_template.md` — kept as a coarser-grained Manim reference. The production track's `09_animation_spec.yaml` is the binding artefact for code generation; the blueprint can still record per-scene design notes.
- `templates/11_rigor_audit_template.md` — still used for the conceptual / narrative audit. The production track's `12_render_validation_rubric.md` is a complementary, render-targeted audit.

After this upgrade, when the skill is asked to generate Manim code it will (1) read the conceptual / narrative files, (2) generate or refine the shotlist, (3) generate or refine the animation specs, (4) define / reuse Manim components, (5) only then write implementation code, (6) validate the render against the spec, (7) report mismatches and iterate — and refuse to skip any step silently.
