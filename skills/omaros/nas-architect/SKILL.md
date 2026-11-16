---
name: nas-architect
description: 'Document and maintain the QNAP NAS layout, snapshot policy, and cold-storage rules in 08_Systems_and_Infrastructure/NAS/. Use this skill when the user says "update the NAS layout", "document the NAS shares", "snapshot policy", "cold storage rules", "what''s on the NAS", "how do I restore from NAS", "NAS backup policy", "add a new NAS share", "documenta el NAS", "política de snapshots del NAS", or when the NAS topology changes and the documentation needs to stay in sync. Maintains three files: Layout.md (shares, purposes, owners), Snapshots.md (schedule, retention, restore playbook), and Cold_Storage.md (what moves to cold and when). Documentation only — never touches actual sync daemons or NAS configuration. Do NOT trigger for cloud sync topology (sync-architect), for device inventory (device-cartographer), or for vault governance audits (governance-auditor).'
license: Proprietary. OmarOS internal.
---

# NAS Architect

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

The QNAP NAS is the cold-storage backbone of OmarOS — the always-on physical layer that backs up cloud providers and holds archives that are too large or too infrequently accessed for warm cloud storage. Without accurate documentation, a restore scenario (the moment when this documentation matters most) becomes guesswork.

This skill maintains three documents that together constitute the NAS runbook: what's there, how it's protected, and what lives in cold storage. The guiding principle is that a restore must be runnable from these documents alone, without reference to any external system.

## Managed files

| File | Purpose |
|------|---------|
| `08_Systems_and_Infrastructure/NAS/Layout.md` | Shares, purposes, owners, mount points |
| `08_Systems_and_Infrastructure/NAS/Snapshots.md` | Snapshot schedule, retention counts, restore playbook |
| `08_Systems_and_Infrastructure/NAS/Cold_Storage.md` | Cold-storage policy, movement rules, retrieval procedure |

## Layout.md structure

```markdown
# NAS Layout

Last updated: <ISO datetime>

## Share inventory

| Share name | Mount point | Purpose | Owner | Size (approx) | Mirror? |
|------------|-------------|---------|-------|--------------|---------|
| vault | /volume1/vault | OmarOS git mirror | vault | ~2 GB | iCloud + GitHub |
| media | /volume1/media | Photos, videos archive | personal | ~500 GB | iCloud Photos |
| ...

## Access policy

<who can access what, and how (SMB, SFTP, rsync)>

## Single points of failure

<shares that hold unique state not mirrored elsewhere — these are risks>
```

**Rule:** every share has exactly one purpose and one owner. Shared ownership creates ambiguity about who is responsible for a share's integrity.

## Snapshots.md structure

```markdown
# Snapshot Policy

Last updated: <ISO datetime>

## Schedule

| Share | Daily | Weekly | Monthly | Yearly | Retention |
|-------|-------|--------|---------|--------|-----------|
| vault | ✓ | ✓ | ✓ | ✓ | 7 / 4 / 12 / 3 |
| media | ✓ | ✓ | — | — | 7 / 4 |

## Restore playbook

Step-by-step procedure for restoring from each share type.
This section must be runnable without reference to external systems.

### Restore a single file

1. ...

### Restore a full share

1. ...
```

**Rule:** retention policy is always explicit with counts (daily/weekly/monthly/yearly). "Long enough" is not a retention policy.

## Cold_Storage.md structure

```markdown
# Cold Storage Policy

Last updated: <ISO datetime>

## What moves to cold storage

| Content class | Trigger | Cold path | Retrieval SLA |
|--------------|---------|-----------|--------------|
| Photos >3 years old | age threshold | /volume2/cold/photos | within 24h |
| ...

## Movement procedure

<how files are moved to cold storage — never delete from warm until cold write is confirmed>

## Retrieval procedure

<how to retrieve from cold storage — must be runnable alone>
```

## Constraints

- **Documentation only** — never touches actual NAS configuration, sync daemons, or QNAP admin interface.
- **No secrets in these docs** — point to the password manager by name ("see 1Password vault 'NAS'"), never include passwords, SSH keys, or credentials.
- **Retention policy must be explicit** — daily/weekly/monthly/yearly counts; no vague language.
- **Restore must be self-contained** — the playbook must be runnable from these documents alone.

## Dependencies

- Sibling skills: `sync-architect` (cloud sync topology; the NAS is the cold-storage backbone of that topology), `device-cartographer` (inventories devices including NAS).
- Write surface: `08_Systems_and_Infrastructure/NAS/` only.
