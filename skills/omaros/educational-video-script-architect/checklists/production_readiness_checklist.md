# Production Readiness Checklist

Run during §11. **PASS / NOTE / FAIL** with a short reason. The question this checklist answers: could the production team build this video without coming back with questions?

## Completeness of the script

- [ ] Every scene in the explanatory architecture has a corresponding block of rows in the second-by-second script.
- [ ] The script covers the entire intended duration with no gaps.
- [ ] Every important visual change in any scene appears as its own row.
- [ ] No row has placeholder content like `<TBD>`, `<add later>`, or `[insert visual]`.

## Voice-over completeness

- [ ] Every row in the second-by-second script either has voice-over text in quotes or is explicitly marked "no narration".
- [ ] The voice-over-only version (§9) reads end-to-end and matches the intended duration ± 5%.
- [ ] No stage directions ("then we cut to…", "Manim shows…") leaked into the voice-over column or §9.

## Modality coverage

- [ ] Every scene declares its production modality.
- [ ] When multiple modalities appear in one scene, the composite plan in §7 specifies the layer stack.
- [ ] Manim sections have a Manim blueprint entry (§7) listing scene class, objects, animations, and camera.
- [ ] Generative-video sections have a clip prompt (§8) with style lock and negative prompt.
- [ ] Motion-graphics / 3D sections have a production blueprint entry (§7) with layers / scene file / asset paths.

## Asset inventory

- [ ] Every imported asset (image, clip, audio, font) is listed.
- [ ] Every asset has a defined first-appearance and last-appearance time.
- [ ] Every asset is marked as "to produce", "to capture", "to license", or "available".
- [ ] No asset that the script depends on is missing from the inventory.

## Notation and equations

- [ ] Every formula on screen has its source LaTeX in the script.
- [ ] Substring/index maps for partial highlights are included where the production needs them.
- [ ] Substitution sequences (generic → specific values) are explicit, not implied.

## Timing

- [ ] The sum of scene durations equals the intended duration ± 5%.
- [ ] Voice-over reading time is consistent with the intended duration (≈ 150 wpm for clear technical narration; adjust for chosen tone).
- [ ] Pauses (1–2 s after definitions, breath beats between scenes) are accounted for.

## Synchronization contract

- [ ] For every row, the visual event and the voice-over text refer to the same instant.
- [ ] Where an animation runs longer than its narration, the script states that the animation continues silently (and for how long).

## Audio plan

- [ ] Voice-over track parameters declared (recording vs TTS, target loudness).
- [ ] Music bed (if any) declared with intensity envelope and licence source.
- [ ] Sound design cues (definition appears, abstraction lifts, transition) declared in §7.

## Caption plan

- [ ] Captions can be derived directly from §9 (the voice-over-only version).
- [ ] No on-screen text in the script depends on captions to disambiguate it.

## Asset prompts (when used)

- [ ] Every storyboard / image prompt has a style lock and negative prompt.
- [ ] Every generative-video prompt has a style lock, negative prompt, action timeline, and continuity note.
- [ ] No generated asset is required to contain mathematically precise symbolic content.

## Open questions

- [ ] Any choice the production team must make is enumerated in a single "Open questions" block (in §7), not buried in prose.
- [ ] No silent assumptions about budget, software, or licensing.

## Final smell test

- [ ] If the script were handed to a competent Manim implementer they could begin coding without asking further questions about *what* to render.
- [ ] If the script were handed to a competent motion-graphics editor they could begin laying out compositions without asking *what* belongs in each frame.
- [ ] If the script were handed to a generative-video pipeline operator they could begin generating clips without inventing details.
- [ ] The production team would not need to consult the user to make any pedagogical or mathematical decision — those are all decided by the script.
