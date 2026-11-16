---
name: device-cartographer
description: Maintain the inventory of every device in Omar's ecosystem (Macs, iPhone, iPad, QNAP NAS, external drives) — documenting each device's role, installed sync clients, attached storage, and which assets it holds. Use this skill when the user says "update the device inventory", "document this Mac", "add the new iPad", "which devices sync what", "device roles", "what sync clients are on the iPhone", "inventario de dispositivos", "documenta el Mac", "qué tiene el NAS montado", "single points of failure in devices", or when a new device is added to the ecosystem. Maintains one file per device under 08_Systems_and_Infrastructure/Devices/ and a cross-device index at _Inventory.md. Flags devices that hold unique state not mirrored elsewhere — those are single points of failure. Documentation only — never interacts with devices. Do NOT trigger for cloud sync topology (sync-architect), for NAS-specific layout (nas-architect), or for governance audits.
license: Proprietary. OmarOS internal.
---

# Device Cartographer

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Every device in Omar's ecosystem plays a specific role in the OmarOS architecture — one is the execution surface, one is the mobile capture surface, one is the backup backbone. When devices are undocumented, two things happen: the same question gets asked repeatedly ("which machine has the Notability archive?"), and single points of failure go unnoticed until they fail.

This skill makes the device topology explicit and auditable. One document per device; a master index that shows the whole fleet at a glance; and a dedicated flag for devices that hold unique state no other device mirrors — because those are the ones that matter most in a failure scenario.

## Managed files

| File | Purpose |
|------|---------|
| `08_Systems_and_Infrastructure/Devices/<device_slug>.md` | Per-device documentation |
| `08_Systems_and_Infrastructure/Devices/_Inventory.md` | Cross-device fleet index |

## Per-device document structure

```markdown
---
title: Device — <name>
note_type: architecture
domain: 08_Systems_and_Infrastructure
updated: <ISO datetime>
---

# <Device name>

## Identity

| Field | Value |
|-------|-------|
| Name | <human name, e.g. "Omar's MacBook Pro 16"> |
| Type | Mac / iPhone / iPad / NAS / external_drive |
| OS | macOS 15.2 / iOS 18 / iPadOS 18 / QTS 5.x |
| Primary role | <one sentence: what this device does in the system> |

## Sync clients

| Client | Scope | Direction |
|--------|-------|-----------|
| iCloud Drive | ~/Library, Desktop, Documents | bidirectional |
| GitHub Desktop | ~/OmarOS | bidirectional |
| Obsidian Sync | n/a — synced via iCloud | — |

## Storage

| Mount / path | Size (approx) | Contents | Mirrored? |
|--------------|--------------|---------|-----------|
| /volume1/vault | 2 GB | OmarOS git repo | GitHub + NAS |
| ~/Downloads | varies | transient | no |

## Single point of failure?

<Yes/No — if yes, describe what unique state this device holds and what the risk is>

## Notes

<anything unusual about this device's role or configuration>
```

**Rules:**
- Every device has exactly one primary role in the system.
- Storage paths are absolute, with owner and purpose.
- Never list serial numbers, IMEIs, or passwords.

## _Inventory.md structure

```markdown
# Device Fleet Inventory

Last updated: <ISO datetime>

| Device | Type | OS | Primary role | SPF? |
|--------|------|----|-------------|------|
| Omar's MacBook Pro 16 | Mac | macOS 15.x | Execution surface | No |
| Omar's iPhone | iPhone | iOS 18 | Mobile capture + retrieval | Yes — local iCloud origination |
| Omar's iPad | iPad | iPadOS 18 | Notability capture + PDF annotation | Yes — Notability originals |
| QNAP NAS | NAS | QTS 5.x | Cold-storage backbone | No — NAS is the mirror |

SPF = Single Point of Failure
```

## Procedure

### Adding or updating a device

1. Check if a per-device file already exists in `08_Systems_and_Infrastructure/Devices/`.
2. If yes: update the relevant fields and bump `updated:`.
3. If no: create a new file from the structure above.
4. Update `_Inventory.md` to reflect the new or changed device.
5. Evaluate whether the device holds unique state → flag as SPF if so.

### SPF evaluation

A device is a Single Point of Failure if:
- It holds content not mirrored on any other device or cloud provider.
- It is the only device with a particular sync client installed (e.g., only the Mac has GitHub Desktop).
- Losing it would mean losing data permanently.

Surface SPFs prominently. The goal is not to eliminate them (sometimes they're acceptable) but to make them visible so they can be addressed deliberately.

## Constraints

- **Never list serial numbers, IMEIs, or passwords** — use a pointer to the password manager by name.
- **Every device has exactly one primary role** — multi-role devices hide architectural confusion.
- **Documentation only** — never interacts with actual devices or installs/configures software.

## Dependencies

- Sibling skills: `sync-architect` (uses device inventory to detect drift in cloud sync topology), `nas-architect` (NAS is one node in this inventory).
- Write surface: `08_Systems_and_Infrastructure/Devices/` only.
