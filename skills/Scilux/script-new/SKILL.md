---
name: script-new
description: Scaffold a new Scilux lesson. Creates lesson folder, workspace, logs, and an empty brief from the template. Argument is the lesson_id (kebab-case).
tools: Read, Write, Edit, Bash, Glob
---

# /script-new

## Contract

Usage: `/script-new <lesson_id>`

Steps:

1. Validate `<lesson_id>` against `config/context-registry.yaml#naming.lesson_id_regex`.
2. Refuse if `lessons/<lesson_id>/` already exists.
3. Copy `lessons/_template/` to `lessons/<lesson_id>/`.
4. Copy `inputs/briefs/_template.yaml` to `inputs/briefs/<lesson_id>.yaml`.
5. Create `workspace/<lesson_id>/` and `logs/<lesson_id>/`.
6. Print the path to the new brief and the next-step instruction: "Fill in `inputs/briefs/<lesson_id>.yaml`, drop sources in `inputs/`, then run `/script-generate <lesson_id>`."

Delegation: none. This is a pure scaffolding skill; do not invoke agents.
