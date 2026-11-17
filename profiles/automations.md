# Automation resources

Integration code lives in `resources/automations/`; it is not a second skill
catalogue. The source tree contains no personal databases, conversation archives,
credentials or operational receipts. Those remain with their existing local
owners. Installation creates native discovery entries, not scheduled jobs.

| Resource | Purpose and current consumer |
| --- | --- |
| `knowledge_sync.py`, `knowledge_import.py`, `project_registry.py` | Existing knowledge-sync LaunchAgent and its import/registry helpers. Exact source permissions still govern each export. |
| `official_docs.py` | The common `constellation.py docs` command for public provider documentation. |
| `secret_scan.sh`, `changed_python_syntax.sh` | Existing GitHub workspace domain hooks. |
| `reminders-sync/` | Apple Reminders bridge; its fetcher is also used by OmarOS's Notes/Reminders monitor. |
| `task-marshal/` | Task-ledger parsing, classification and aggregation shared by Reminders and Calendar. |
| `calendar-sync/` | Optional calendar bridge using the same task-ledger format. |
| `outlook-sync/` | Optional mailbox integration with its existing configuration and setup guide. |
| `notability-sync/` | Optional Notability import resources. |
| `claude-conversations-sync/`, `codex-conversations-sync/` | Optional local conversation import/rendering code. Archives, manifests and sync state stay private; this code's presence grants no permission to inspect or export them. |

The seven integration packages retain their scripts and supporting assets.
Their old skill wrappers and automatic-routing instructions have been retired.
Launch templates are optional installation assets, not evidence of a running
service. No matching jobs for these seven packages were present in the inspected
LaunchAgent/LaunchDaemon directories during the 2026-11-16 cleanup; the Reminders
fetcher's monitor consumer is separate. Inspect current configuration before
asserting that an integration is enabled or live.

Use an integration only for an authorized task and inspect its documented
arguments and effects first. Do not install launch templates, access accounts,
publish imported material or enable background capture as part of a routine
Constellation reinstall. Existing task, privacy and publication contracts apply.

SQLite databases in native client homes are client-managed operational storage.
They are not skill definitions. This cleanup does not treat an unexplained
database as disposable: identify its owning process and purpose before a
separately scoped database retirement.
