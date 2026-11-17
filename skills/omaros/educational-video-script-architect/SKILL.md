---
name: educational-video-script-architect
description: "Design educational video scripts, storyboards and explicit animation specifications for mathematical, scientific and technical explainers. Use for narrated video or Manim production planning; static course presentations use their course workflow."
license: Proprietary. OmarOS internal.
---

# Educational video architecture

Establish the topic, audience prerequisites, learning objective, duration and
production medium from the request and available project context. Build the
requested script, storyboard, shot specification or production package. A short
scene does not require thirteen files, and planning does not authorize rendering,
external uploads or publication.

Use the [teaching method](../../core/teach-from-first-principles/SKILL.md) for
conceptual exposition and the current local learning profile for relevant
preferences. Bundled `user_style/` material is historical, not the active
personal profile. Brainteasers Quant's static Beamer presentations follow
[their own workflow](../brainteasers-quant/SKILL.md).

## Intellectual and audiovisual contract

- Establish objects, hypotheses and notation before they carry an argument.
  Distinguish the object from its coordinates, representation or sample path.
  Examples and metaphors cannot replace definitions or justify a theorem.
- Build the question that motivates a formal beat, then show the mechanism,
  statement and a concrete instance. For load-bearing concepts, preserve the
  fundamental definition, its rigorous intuition and the structural synthesis.
  A full explanation includes a precise cross-domain correspondence and names
  what is lost in that translation.
- Define technical terms at first use in their role here, in narration and on
  screen. Match the depth and pace to the declared audience; do not replace
  precision with jargon or lower the mathematical claim to fit the medium.
- Separate formal claims, intuition and transitions. Name a metaphor's limits
  in both narration and the conceptual review. The concise “essence” statement
  must express the actual structure, not a slogan.
- Each scene adds a distinct capability or insight. Develop its visual idea
  before implementation: compare plausible representations, select one that
  exposes the mechanism and explain why it fits the audience.
- Motion has semantic meaning. Specify the driving parameter, what changes and
  what stays invariant. Reuse persistent objects across shots; an arbitrary
  fade or decorative movement does not explain a transformation. Deliberate
  stillness remains appropriate for reading, retrieval and pauses.
- Write narration against the visible event with pronounceable mathematics,
  precise referents and real pauses. Give timings and a declared synchronization
  tolerance; the production synchronization reference supplies its default.
- Render equations, labels, axes and exact values deterministically with
  appropriate vector/animation tools. Generative imagery can supply context
  or metaphor, not authoritative mathematical symbols or data.

## Develop only the needed artifacts

For an explanation, connect conceptual blueprint, scene sequence, visual
language and timed narration. Derive clean voice-over and voice direction when
needed for production. Use stable scene/frame IDs so narration, storyboard,
assets and revisions remain traceable.

The existing [templates](templates/) provide useful fields for these outputs.
Choose relevant sections; their historical numbering, file counts and approval
ceremonies do not expand the current request. Preserve the useful narrative
tags when using the timed-script format: `[PREAMBLE]` before `[FORMAL]`,
`[INSTANCE]`, `[BOUNDARY]` when relevant, `[CROSS_DOMAIN]` and `[ESSENCE]`.
Keep repeated essence statements consistent wherever they occur.

For saved OmarOS video projects, reuse the existing project location or the
owner's `15_Reading_and_Learning/Video_Scripts/YYYY-MM-DD_slug/` convention.
Record current source/status metadata and curated decisions, not transcripts
or pasted tool output. Templates do not select a model or authorize a commit.

## Before animation implementation

**Implement from an explicit shot-level specification, not vague narration.**
For the affected shots, settle these decisions before writing their code:

| Decision | Required content |
| --- | --- |
| Identity and timing | Stable IDs, scene purpose, duration, narration cues and pauses |
| Geometry and state | Layout, objects, initial/final states, persistent identities |
| Motion | Driving parameters, transitions, easing, invariants and timing |
| Meaning | Semantic colours, formula referents, notation and metaphor limits |
| Inputs | Asset origins/rights, data sources, units, dates and synthetic labels |
| Acceptance | Observable render criteria and any required human-review frames |

Use the [shotlist](production_track/templates/08_shotlist_template.md),
[animation specification](production_track/templates/09_animation_spec_template.yaml),
[asset](production_track/templates/10_asset_manifest_template.yaml) and
[data](production_track/templates/10b_data_manifest_template.yaml) manifests
as applicable. The [component plan](production_track/templates/11_manim_component_library_template.md)
and [render rubric](production_track/templates/12_render_validation_rubric_template.md)
support an implementation handoff. These decisions can live in the appropriate
existing artifact; a small change does not require unrelated empty documents.

Conceptual truth governs learning objectives, scene function, narration timing,
visual language, shot specification, animation specification and finally code.
Name contradictions and repair the affected specification; never silently
prefer the easier implementation. Keep shared visual constants and reusable
components in their existing owners.

Low-risk presentation defaults may be explicit assumptions. Missing sign
conventions, data, mathematical meaning or other high-risk choices require a
`MISSING_SPEC` entry with the field, reason, proposed resolution and consequence.
Continue independent work while resolving the affected decision. Never invent
numeric evidence or silently redesign a metaphor during code implementation.

The responsibility prompts in [production_track/prompts/](production_track/prompts/)
support visual direction, specification, component design, implementation and
render review. They are task briefs, not five additional installed agent roles.

## Review and delivery

Inspect rendered shots against their specification. Review major scenes muted
for conceptual meaning and frozen for legibility of objects, relationships,
labels and notation; a boundary or transition frame need not teach the whole
concept by itself. Match voice and visual timing, and inspect mathematical and
financial conventions, units, source provenance and synthetic-data labels.

Use the [human-review criteria](production_track/doctrine/15_human_review_gates.md)
to identify high-leverage production frames. Preserve declared
`human_review_required` flags and real decisions. Prepare concrete previews
before requesting needed approval; do not mark a pending human review as passed
or request approval already provided for the same candidate.

Deliver the requested materials with their actual state: draft, specified,
rendered or reviewed. Unrendered plans cannot claim visual verification.
The [pipeline validator](scripts/validate_pipeline.py) checks the original
complete thirteen-file format; use it only when maintaining that explicit
format, never as a gate for a smaller adapted deliverable. Its structural
results do not establish pedagogical or mathematical correctness.
Do not create or run software tests without Omar's explicit request.

## Resources by stage

Read only the resources needed for the decision at hand:

- **Concept and narration:** [formal/intuitive doctrine](style/ultra_formal_intuitive_doctrine.md),
  [rigorous explanation](style/rigorous_explanation_guide.md) and
  [narration style](style/narration_style_guide.md). This entrypoint governs
  scope; older fixed file counts and personal-skill aliases are not requirements.
- **Visual design:** [explainer references](style/elite_explainer_doctrine.md),
  [visual creativity](style/visual_creativity_protocol.md) and
  [visual language](style/visual_language_guide.md).
- **Learning evidence:** [principles](learning_research/extracted_principles.md),
  [video rules](learning_research/video_design_rules.md), then the relevant
  summary located through the [research index](learning_research/00_master_index.md).
  Open the source paper when grounding an empirical claim, resolving a conflict
  or when the summary is insufficient; do not turn each script into a literature review.
- **Production detail:** [prime directive](production_track/doctrine/00_prime_directive.md),
  [authority](production_track/doctrine/01_hierarchy_of_authority.md) and the
  relevant files in [doctrine](production_track/doctrine/) for semantic colour,
  motion, visual density, object continuity, registered metaphors, formulas,
  synchronization, financial correctness and missing specifications.
  The [worked shot](production_track/examples/basis_gap_opens_vague_vs_spec.md)
  shows the difference between an evocative brief and implementable instructions.
- **Final editorial review:** the relevant [checklists](checklists/) for
  pedagogy, visual quality, mathematical accuracy and production readiness.
