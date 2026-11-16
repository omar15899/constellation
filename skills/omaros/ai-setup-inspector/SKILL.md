---
name: ai-setup-inspector
description: "Inspect a target project’s AI configuration with bounded file inventory, dependency analysis, state comparison and evidence-based findings."
---

# ai-setup-inspector

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

Resolve the authorized target and target_id. The target may be a repository,
a project folder or a named configuration subsystem. Read target instructions and
use native filesystem and client tools for the audit; no retired hook adapter is
required. Do not change the target as a side effect of inspection.

Inventory the relevant files and consumers: native configuration, agent and
skill definitions, hooks, project profiles, prompts, active automation and
required resources. Skip `.git`, dependency caches, build outputs and external
symlink traversal. Count secret-shaped files using metadata only; never open or
hash `.env*`, `*.pem`, `*.key` or credential files. Conversation archives, manifests,
sync state and daemon logs are private; an ordinary setup audit does not
authorize their inspection or transmission.

For regular non-private files in the authorized scope, record path, SHA-256,
size and modification time. Compare with an existing manifest when supplied or
present in the authorized audit destination. Report added, changed, missing and
uninspected paths. A capped or failed scan must disclose its incomplete coverage.
Do not count inaccessible content as absent.

Assess:

1. Target, owner, root and observed date.
2. Scope, exclusions and limitations.
3. Structural map and canonical source for each responsibility.
4. Inventory and active consumers.
5. Native configuration validity and broken references.
6. Installed, discovered, trusted and executed states, separately.
7. Scope, privacy, independent review and publication controls.
8. Observed behavior and reproducible checks.
9. Differences from the previous audit.
10. Concrete findings with severity and evidence.
11. Recommended repairs ordered by consequence.
12. Remaining uncertainty and next verification.

A system with fewer hooks or registries may be sufficient. Evaluate effectiveness
and clarity from evidence rather than assigning maturity from component counts.
The available method templates are
[audit report](../../../resources/methods/setup-audit/audit_report.md) and
[manifest](../../../resources/methods/setup-audit/manifest_schema.md); adapt their
presentation to the request without reviving a separate execution architecture.

For a requested saved audit, use
`07_AI_and_Agents/Setup_Audits/Targets/<target_id>/reports/YYYY-MM-DD_audit.md`,
`latest_manifest.json` and dated manifest/diff snapshots in `history/`. Preserve
existing historical reports. Update related audit indexes only when needed for
discovery. A chat-only audit stays in conversation. Neither a saved report nor a
manifest is permission to install, trust or activate anything.
