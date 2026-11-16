---
name: repo-bootstrap
description: Install the central Constellation entry points for an authorized repository while preserving its existing files, Git owner and domain rules.
---

# Bootstrap a repository

Read the target's instructions and Git identity. Consult the
[central project registry](../../../profiles/projects.json) and
[installation contract](../../../README.md). Registration records a root and its
profile; it does not authorize unrelated repositories or private data access.

For an unregistered project, prepare a central profile with its domain rules,
checks, private publication exclusions and existing automation dependencies.
Preserve the owner's Git and all local/index changes. Use the common installer
from the README; inspect its concrete plan before applying an authorized change.
Keep only native entry points in the target. Do not generate another engine,
agent roster, copied skills or unrelated CI templates.

Verify a fresh native session loads the intended profile and skills. Verify
existing hooks and automations still function. Configuration is not evidence of
native trust or execution; report missing trust accurately. Publication follows
the assignment's declared paths and independent review.
