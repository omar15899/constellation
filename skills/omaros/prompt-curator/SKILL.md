---
name: prompt-curator
description: "Save, version and retrieve reusable OmarOS prompts; inspect the central native agent and skill catalogue when requested."
---

# prompt-curator

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Own the reusable prompt library under `07_AI_and_Agents/Prompts/`. Use this
method for saving a supplied reusable prompt, updating its version, finding a
prompt by purpose, or inspecting available agent and skill definitions. A query
about prompts stays read-only. Do not save conversation transcripts as prompts.

Before creating a prompt, search for an existing entry with the same purpose.
Choose an existing category, commonly research, writing, system, pipeline or
meta. Preserve the supplied text when the user asks to save it verbatim; an
editing request may improve wording while retaining intent and explicit limits.
Use current vault metadata and include purpose, intended audience, inputs,
outputs, usage examples, version and provenance. Do not invent demonstration
results. Keep version history and a short reason for substantive changes.

A prompt entry lives at `07_AI_and_Agents/Prompts/<category>/<slug>.md`. Update
an existing index only when required for navigation. Verify links, metadata and
that examples satisfy the prompt's own contract. Saving a prompt does not activate
it as a global instruction or authorize its actions.

For catalogue questions, inspect the canonical `agents/`, `skills/`,
`resource-inventory.json` and `profiles/projects.json` in
`/Users/omarkhalil/GitHub/Constellation`, then verify the native catalogue when
actual availability matters. Report name, purpose, source and observed loading
state. Do not create parallel agent or command registries inside OmarOS. Changes
to agent definitions or installation belong to the central source and need their
own authorized scope and review.
