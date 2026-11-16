---
title: "<Title> — Shotlist"
note_type: video_shotlist
domain: 15_Reading_and_Learning
subdomain: Video_Scripts
slug: <topic-slug>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
status: draft
production_track: true
---

# Shotlist — `<topic>`

This is the human-readable inventory of every shot in the video. Each shot is one visual unit: one composition, one cognitive purpose, one place in the arc. Shots are smaller than scenes (a scene has many shots) and larger than frames (a frame is a single still inside a shot).

This document is **upstream of `09_animation_spec.yaml`**. Each row here becomes a YAML document there.

## How to fill this

- Read `03_scene_architecture.md` first. Each scene divides into 2–10 shots.
- For each shot, write **one sentence** under "Visual description" — no more. Detail belongs in the animation spec, not here.
- Pick **one** cognitive purpose and **one** pedagogical function per shot. If you cannot, the shot is doing too much; split it.
- Pick **one** dominant visual metaphor. It must be in the registered catalogue (see `production_track/doctrine/07_registered_metaphors.md`) or have a pending approval.
- Mark `human_review_required: yes` for any high-leverage shot (cold open, first definition, mechanism diagram, valuation formula, misconception refutation, climax, essence — see `production_track/doctrine/15_human_review_gates.md`).

## Cognitive purposes (closed vocabulary)

`anchor` · `introduce_object` · `define_term` · `build_intuition` · `compare` · `reveal` · `derive` · `apply` · `refute_misconception` · `retrieve` · `synthesise` · `transition`

## Pedagogical functions (closed vocabulary)

`hook` · `worked_example_step` · `worked_example_full` · `interleaved_contrast` · `concrete_to_abstract` · `abstract_to_concrete` · `self_explanation_prompt` · `retrieval_prompt` · `boundary` · `climax` · `essence`

## Object memory ledger (filled as shots are written)

For each persistent semantic object, record an entry. See `production_track/doctrine/06_object_memory.md` for the full schema.

```yaml
object_memory:
  - object_id: ghost_time_series_basis
    first_appearance:
      shot_id: <shot_id>
      visual_form: <one sentence>
    semantic_role: <one sentence>
    later_reappearances: []        # list of {shot_id, morph}
    morph_rule: <invariant constraint>
    continuity_constraints: []
    human_review_required: yes
```

## The shotlist

For each shot, fill one of these blocks. One block per shot; keep them in arc order.

```markdown
### Shot `<shot_id>`

| Field                | Value |
|----------------------|-------|
| scene_id             | `<scene_id>` |
| time_range           | `00:MM:SS.s – 00:MM:SS.s` |
| duration             | `<seconds>` |
| narration_reference  | `05_narration_script.md` rows `R<nnn>` – `R<mmm>` |
| visual_description   | _<one sentence>_ |
| cognitive_purpose    | `<one of the closed vocabulary>` |
| pedagogical_function | `<one of the closed vocabulary>` |
| doctrine_tags        | `[FORMAL|INFORMAL|PREAMBLE|INSTANCE|BOUNDARY|CROSS_DOMAIN|RETRIEVAL|SELF_EXPLAIN|ESSENCE|TRANSITION]` |
| dominant_metaphor    | `<registered metaphor id>` or `none` |
| key_objects          | `<comma-separated component / object ids>` |
| composition_summary  | _<one sentence>_ |
| transition_in        | `<primitive>` from previous shot's exit state |
| transition_out       | `<primitive>` into next shot's entry state |
| human_review_required| `yes` / `no` |
| notes                | _<freeform; questions, risks, alternates>_ |
```

## Example row (delete when filling)

```markdown
### Shot `IP-S0-F02`

| Field                | Value |
|----------------------|-------|
| scene_id             | `S0_anomaly` |
| time_range           | `00:00:08.4 – 00:00:18.1` |
| duration             | `9.7 s` |
| narration_reference  | `05_narration_script.md` rows `R004 – R009` |
| visual_description   | Two airport-style departure boards (NYC, Frankfurt) diverge as the basis crosses below zero into BASIS_RED territory. |
| cognitive_purpose    | `anchor` |
| pedagogical_function | `hook` |
| doctrine_tags        | `[HOOK][INSTANCE][BOUNDARY]` |
| dominant_metaphor    | `EKG` (basis as stress signal) — pre-figured; full metaphor lands in S5 |
| key_objects          | `SplitFlapBoard.left`, `SplitFlapBoard.right`, `BasisTicker`, `GhostTimeSeries.basis_history`, `ZeroReferenceLine` |
| composition_summary  | Two boards left/right, separated by central zero-reference line; basis ticker above the right board; ghost time series behind, full-width. |
| transition_in        | `Create` boards from `DEEP_BACKGROUND`, ghost curve `FadeIn` to 35% opacity |
| transition_out       | Hold final state; next shot continues with the same boards |
| human_review_required| `yes` (cold open, high-leverage) |
| notes                | Confirm exact basis value at climax (-30 bps illustrative? or use 2018-Q4 real value?). |
```

## When the shotlist is complete

A shotlist is complete when:

- Every second of every scene is covered by exactly one shot.
- Every shot has all fields filled (no placeholders).
- Every high-leverage shot is marked `human_review_required: yes`.
- The object memory ledger contains every persistent semantic object that appears.
- The total duration of all shots matches the total declared duration in `00_declaration.md`.
- No two shots share a `shot_id`.

The shotlist is the input to `09_animation_spec.yaml`. The animation_spec agent will fail if any of the above is missing.
