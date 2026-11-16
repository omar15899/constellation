---
name: sync-architect
description: Document and maintain the cloud-sync topology (Pole A) — which provider holds which content class, what the sync invariants are, and where drift has occurred. Use this skill when the user says "update sync topology", "document sync rules", "which provider holds X", "sync policy", "check for drift", "what's the provider matrix", "iCloud vs OneDrive roles", "actualiza la topología de sync", "política de sincronización", or invokes /sync-check. Maintains Provider_Matrix.md (which provider holds what, with a single primary and any mirrors) and Sync_Rules.md (invariants like "vault is mirrored on GitHub and QNAP"). Detects drift by cross-referencing device-cartographer inventories. Documentation and policy only — never touches actual sync daemons. Do NOT trigger for NAS-specific layout (nas-architect), for device inventory (device-cartographer), or for vault governance (governance-auditor).
license: Proprietary. OmarOS internal.
---

# Sync Architect

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

The cloud-sync topology is the mapping between content classes (vault, Office files, Apple-native captures, photos, code) and providers (iCloud, OneDrive, Google Drive, GitHub, QNAP NAS). Without this mapping being explicit and maintained, it's impossible to answer "where is the authoritative copy of X?" — which is the question that matters most during a restore or a conflict.

This skill maintains the policy documents that make the topology legible. It never manipulates sync daemons; its job is to document what should be true and surface drift when reality diverges.

## Managed files

| File | Purpose |
|------|---------|
| `08_Systems_and_Infrastructure/Sync/Provider_Matrix.md` | Content class → provider mapping |
| `08_Systems_and_Infrastructure/Sync/Sync_Rules.md` | Invariants, conflict resolution, drift alerts |

## Provider roles (canonical)

| Provider | Primary role |
|----------|-------------|
| iCloud | Apple-native continuity: Notes, Reminders, Photos, Files, iOS app data |
| OneDrive | Office files, Notability `.note` archives, Microsoft 365 continuity |
| Google Drive | Collaborative documents, shared files |
| GitHub | Code, versioned markdown, OmarOS vault mirror |
| QNAP NAS | Cold-storage backbone, always-on bridge between providers |
| Mac (local) | Active execution surface — where OmarOS runs |

## Provider_Matrix.md structure

```markdown
# Provider Matrix

Last updated: <ISO datetime>

## Content class assignments

| Content class | Primary | Mirrors | Notes |
|--------------|---------|---------|-------|
| OmarOS vault | GitHub | QNAP NAS | `.obsidian/workspace*` excluded |
| Office files | OneDrive | QNAP NAS (cold) | |
| Apple Notes | iCloud | — | no vault mirror |
| Photos | iCloud Photos | QNAP NAS (cold archive) | |
| Code repos | GitHub | Mac (local) | |
| Notability notes | OneDrive | — | `.note` bundles |
```

**Invariant:** every content class has exactly one primary provider. Dual-primary is a drift condition, not a design.

## Sync_Rules.md structure

```markdown
# Sync Rules and Invariants

Last updated: <ISO datetime>

## Hard invariants

1. The OmarOS vault is mirrored on GitHub (authoritative) and QNAP NAS (cold backup).
2. iCloud holds Apple-native captures only — no manual file management.
3. The `.obsidian/workspace*` state files are excluded from GitHub sync (runtime UI state only).
4. QNAP NAS is the cold-storage backbone — never a primary for active content.

## Conflict resolution policy

<what to do when two providers have diverging versions of the same file>

## Drift alerts

| Condition | Detected by | Response |
|-----------|-------------|---------|
| Vault not on GitHub | /sync-check | force push from Mac |
| NAS vault mirror stale | /sync-check | trigger rsync job |
```

## Drift detection

Cross-reference the `device-cartographer` inventory against the Provider Matrix. A drift condition exists when:
- A content class's observed primary differs from the documented primary.
- A mirror is absent or stale.
- Two providers both hold an "authoritative" copy of the same content class.

Surface drift as a list of deviations in `Sync_Rules.md` under `## Drift alerts`. Never silently update the matrix to match reality — surface the drift and let the user decide whether to update the policy or fix the reality.

## Constraints

- **Documentation and policy only** — never touches sync daemons, rsync jobs, or provider settings.
- **Every content class must have exactly one primary provider** — dual-primary is a drift condition.
- **QNAP NAS is always cold-storage backbone** — never a primary for actively-edited content.
- **GitHub is the authoritative vault mirror** — `.obsidian/workspace*` state is explicitly excluded.

## Dependencies

- Sibling skills: `nas-architect` (NAS layout; the NAS is one node in this topology), `device-cartographer` (device inventory cross-referenced for drift detection).
- `/sync-check` command: triggers a drift detection pass.
- Write surface: `08_Systems_and_Infrastructure/Sync/` only.
