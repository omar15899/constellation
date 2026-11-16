---
name: external-setups-mirror
description: "Create or refresh explicitly scoped reference snapshots of external project AI configuration, preserving privacy, source ownership and prior snapshots."
license: Proprietary. OmarOS internal.
---

# External setup snapshots

Use the [common Constellation entry](../../../README.md) for assignment scope,
evidence, independent review and publication. Constellation is the only active
AI source. A reference snapshot does not become an installation or a second
configuration owner.

Use this method when the user requests a snapshot or refresh of named external
setups. An ordinary audit uses `ai-setup-inspector`; a question about an existing
snapshot is read-only. Do not start recurring mirroring from either request.

1. Resolve the exact authorized project roots and inspect their instructions.
   Inventory candidate configuration and method files without traversing external
   symlinks. Avoid dependencies, caches, build outputs and user runtime homes.
2. Preview the source-to-destination file list. Exclude secrets, credentials,
   conversations, conversation manifests, sync state and daemon logs before any
   copy. Do not treat a post-copy secret scan as authorization to retain secrets.
3. Use `07_AI_and_Agents/External_Setups/<slug>/` in OmarOS only for the requested
   reference material. Record source path, source revision when available,
   capture time, copied file hashes and exclusions. Do not copy Constellation's
   central code or profiles back into the vault; link their canonical source.
4. Preserve source bytes and relevant metadata for approved files. Never follow
   a symlink to broaden the scope. Preserve prior snapshots or make the update
   recoverable; an exact deletion request is required to prune old material.
5. Update the snapshot index only for the inspected scope. Missing projects keep
   a visible stale or archived status. Validate hashes and report skipped files,
   failures and limitations. Publication needs exact data and destination
   authorization, especially when any reference material is private.

The bundled `scripts/mirror.py` is a retained resource. Inspect its current
options and selection behavior before use. Run it only if its preview and
exclusions satisfy this contract for the selected roots; otherwise perform the
scoped copy with native tools or adapt the script under an authorized coding
assignment. Never invoke a broad recursive mirror merely because it is bundled.

`--dry-run` denotes inspection without writes. `--only SLUG` restricts the selected
project where the script supports it. `--prune` is destructive and requires the
exact removal scope. No snapshot refresh activates agents, trusts hooks, enables
telemetry or commits automatically.
