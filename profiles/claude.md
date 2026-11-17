# Claude with Constellation

Claude runs the tools and native subagents. Constellation supplies the shared
instructions, eight agent definitions, skills, edit guards and reviewed Git
workflow. There is one source checkout:
`/Users/omarkhalil/GitHub/Constellation`.

## What belongs where

| Location | Responsibility |
| --- | --- |
| `Constellation/agents/*.toml` | The eight canonical roles, also used by Codex. |
| `Constellation/skills/` | Shared skill instructions and their resources, grouped by owner. |
| `Constellation/constellation/` | Installation, task records, hook decisions and Git publication. |
| `Constellation/profiles/` | Client guidance and each repository's domain boundaries. |
| `~/.claude/CLAUDE.md` | Small global import of shared instructions and this guide. |
| `~/.claude/agents/` | Native discovery links to generated Claude Markdown adapters. |
| `~/.claude/skills/` | Links to shared core skills; provider-managed skills remain provider-owned. |
| `<project>/.claude/skills/` | Links to that project's central skills. |
| `<project>/CLAUDE.md` | Project imports and any specific domain guidance. |
| `~/.claude/settings.json` | Claude preferences, permissions, plugins and the two common hooks. |
| `~/.local/state/constellation/` | Private task evidence, generated adapters, installation receipts and recovery. |

The generated Markdown files are adapters, not another set of agent definitions.
Edit the TOML source, then run the installer. Claude inherits the selected model
and effort; Constellation does not change those settings or approve native trust.

## Work through the common entry

Read the project's profile and applicable local `AGENTS.md` before changes.
Use Claude's native Agent tool for independent work, and record the returned
agent ID. A role name (`agent_type`) is not the unique running agent ID
(`agent_id`). The parent `session_id` is separate. Bind observed routing IDs to
the recorded native identity before editing; never substitute an inherited
environment variable as proof of identity.

The [common workflow](../README.md#work) defines `begin`, `check`, `review`,
`commit`, `push`, `recover` and `finish`. Keep one task per Git owner and assign
exact files. Independent reviewers quote the current candidate fingerprint.
Use Constellation for commits and pushes; native hooks do not authorize an
automatic pull, commit or push. Domain preflight checks remain project-owned.
Declare the applicable domain checks in the task's `required_checks` before
publication. A native hook listening for `git commit` does not observe the
outer `constellation.py commit` command; preserved Git validators and explicit
candidate checks carry that obligation. A retained script alone is not proof
that it ran against the candidate.

Two user-level hooks call the same engine as Codex: `PreToolUse` checks declared
structured edits and known destructive commands; `Stop` reports unfinished work
with one bounded continuation. Claude's `NotebookEdit` is a structured edit too.
These guards cannot isolate arbitrary shell programs. Native permissions and
the exact Git publication checks remain separate controls.
For project command filters, native `matcher` selects the tool name; a handler's
`if` selects its arguments, for example `matcher: "Bash"` with
`if: "Bash(git commit*)"`. Historical skill stage names describe responsibilities;
delegate them through the eight loaded roles instead of recreating retired agents.

## Install and inspect

```sh
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py install
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py install --apply
```

The preview identifies conflicts instead of silently replacing unknown agents,
skills or personal configuration. Installation retains private recovery receipts.
After installation, open a fresh Claude session and inspect `/agents`, `/skills`,
`/hooks`, `/memory` and `/status`. Review workspace/import trust in Claude when
it asks. A configuration file, unit test or isolated headless probe does not
establish trust in an existing interactive session.

To roll back one installation, use `constellation.py install --rollback RECEIPT`.
It rejects later changes instead of overwriting them. Old cleanup receipts and
recovered resources are historical evidence; they are not active configuration.

## Claude's local data

Keep credentials, `settings.local.json`, `projects/`, `sessions/`, `history.jsonl`,
`file-history/`, plans, jobs, daemon state, shell snapshots and provider plugin
data in the native home. They support authentication, continuity, recovery or
Claude features. They are not Constellation source and are not published.
The provider-owned `skills/synced/` directory is also separate from our skills.
When a synced skill shares a local name, the local skill keeps the short name;
the account version remains available as `/anthropic-skills:<name>`.
This installation covers local Claude Code. Cowork and cloud sessions use
account skills and do not read this machine's local skill directories.

SQLite files, when a client creates them, are structured local storage. A name
or version suffix alone does not make a database obsolete; its `-wal` and `-shm`
companions may be part of an active write. The Claude home inspected for this
migration contained no SQLite database files. Do not delete client state to
make the directory look smaller. Regenerable caches may return during use.

## Official documentation

The shared documentation utility lives at
`resources/automations/official_docs.py`. The local public snapshots stay in
`~/.claude/docs/official/` and `~/.codex/docs/official/`; their manifests record
the source URL, download date and hash.

```sh
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py docs --provider claude verify
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py docs --provider claude search 'subagent'
python3 /Users/omarkhalil/GitHub/Constellation/constellation.py docs --provider claude refresh
```

Only `refresh` downloads public documents. Hash verification checks local
integrity, not freshness. Consult the relevant current official page when a
native interface changes: [instructions](https://code.claude.com/docs/en/memory),
[skills](https://code.claude.com/docs/en/skills),
[subagents](https://code.claude.com/docs/en/sub-agents),
[hooks](https://code.claude.com/docs/en/hooks) and
[settings](https://code.claude.com/docs/en/settings).
