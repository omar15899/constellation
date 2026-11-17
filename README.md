# Constellation

One source for Omar's eight agents, skills and change contracts. Codex, Claude
and GitHub Copilot select tools and run native subagents; Constellation records
ownership, evidence, review and publication. Consultations need no task record.

```text
Constellation/
├── constellation.py       # common command entry
├── constellation/         # ledger, Git, hooks and reversible installation
├── agents/                # eight canonical English definitions
├── skills/                # methods and resources grouped by owner
├── profiles/              # project constraints and native client guides
├── instructions/          # shared working contract
├── resources/automations/ # integration code, separate from skill discovery
├── git-hooks/             # Git entries into the same publication gate
├── tests/                 # existing suites; explicit user request required
├── resource-inventory.json
└── migration.py           # inventory, preservation and explicit retirement
```

## Methods and project workflows

The library has 18 maintained skills. Only the five general methods are installed
globally; each project receives its own workflows. Repository constraints belong
in `profiles/`, and the eight agents supply working roles rather than additional
skills for planning, logging, routing or review.
Existing native enable/disable preferences still apply to installed entries.

| Scope | Skills |
| --- | --- |
| General | `coding`, `mathematics`, `quant-research`, `writter`, `teach-from-first-principles` |
| OmarOS | `fast-finder`, `engie-learning`, `brainteasers-quant`, `brainteasers-quant-notes`, `doc-forge`, `educational-video-script-architect`, `git-history-reviewer` |
| KarimSpecificCase | `gs-interface-editor` |
| tradinginterface | `component-builder` |
| Sweeplab | `pde-intake`, `pde-results-review` |
| Scilux | `scilux-lessons`, `scilux-documents` |

Use the owner's profile for lab rules and cross-repository work. Document-format,
design and skill-authoring tools remain with their native providers; their
availability depends on the client. Constellation does not maintain copied
provider catalogues or old slash-command aliases.

The [automation map](profiles/automations.md) identifies integration code and
its consumers. Automations do not appear as skills or start because this source
is installed. Private client databases, task records and receipts are runtime
data, not another source of instructions.

## Install

Use Python 3.11+, Git and a native client. Keep this checkout outside client
homes. Project roots live in `profiles/projects.json`. From this checkout:

```sh
python3 constellation.py install
python3 constellation.py install --apply
```

The first command previews the full installation; the second applies it with
private rollback receipts. It can touch all registered projects. For Copilot
personal entries only, use the scoped commands:

```sh
python3 constellation.py install --client copilot
python3 constellation.py install --client copilot --apply
```

Personal preferences, authentication, sessions and privacy belong to the native
client. Inspect hook admission in a new native session. Third-party skills remain
with their providers. Each repository retains its own Git and data.

The [Claude guide](profiles/claude.md) and [Copilot guide](profiles/copilot.md)
explain native locations, preserved data and limits. The eight roles live only in
`agents/*.toml`; installation generates Markdown adapters in private state.
Clients share skills and scope controls while retaining native formats,
permissions and trust. Reinstall after changing generated role or instruction
sources. This local installation does not deploy cloud jobs.

`python3 constellation.py docs --provider copilot verify` checks local reference
integrity; `search TEXT` searches and `refresh` explicitly downloads current
official pages. Providers are `codex`, `claude`, `copilot` and `all`.

## Engineering and parallel review

Write readable code with domain names, visible control flow, explicit contracts
and useful failure handling. Abstractions solve current needs. The coding skill
and canonical roles define this standard in English.

Do not create, change or run tests unless Omar explicitly requests them. Preserve
existing tests. Static inspection, syntax/configuration validation and independent
review are permitted; state their limits and leave test-dependent gates unmet.

Use native parallel agents for independent tasks with exclusive file ownership.
After integration and permitted checks, reviewers inspect the same fingerprint.
A finding's verifier differs from its author and discoverer. Hooks enforce
supported scope controls and remind about pending work; they do not launch agents
or guarantee correctness. Copilot reviewers have no edit, shell or delegation
tool, and a worker's completion is a handoff rather than final approval.

## Work

Read the owner's profile. Before editing, open a contract with **exact file
paths** and real native author IDs. One contract per Git owner permits work in
several repositories without sharing indexes.

```sh
python3 constellation.py begin example < contract.json
python3 constellation.py check example whitespace -- git diff --check
python3 constellation.py status example
python3 constellation.py review example < review.json
python3 constellation.py commit example 'Describe the change'
python3 constellation.py push example
```

`contract.json` contains `root`, `requirement`, `coordinator`, `session_id`,
`assignments` (path to native author ID) and `required_checks` (for example,
`["whitespace"]`). Select checks appropriate to the change; whitespace alone
establishes no behavioral correctness. Use `mode: "local"` for a local deliverable
and close it with `finish` after checks and independent review. The default
publication mode freezes the Git destination; publication also requires the
user's authorization for that scope and destination.

When hooks supply a UUID and the catalog supplies a canonical name,
`actor_sessions` associates them within the task. This is routing, not
authentication. `session_id` identifies the parent and `agent_id` the child;
Copilot uses the corresponding camelCase fields. Register both before editing.
Reviews contain `reviewer`, `evidence`, `verdict` and `expected_fingerprint`, read
before review. Reviewers differ from authors and the coordinator. Later changes
to content or evidence invalidate approval.

Record curated milestones with `checkpoint` and `{"summary":"..."}`. To correct
or transfer ownership, `assign` accepts `path`, `author` and `reason`; it retains
previous authors and invalidates stale evidence. Use the ID returned by the
native tool, not an inherited environment ID. Private records live under
`~/.local/state/constellation`; they contain neither conversations nor tool output.

Shared hooks inspect structured edits and recognized destructive commands.
They cannot isolate arbitrary shell writes. Stop hooks report pending work
without inventing completion. Git controls the candidate tree, outgoing commits
and exact destination. Publication preserves foreign staged work and confirms
the remote SHA. Recorded identities enforce declared independence; they neither
authenticate processes nor certify the intellectual quality of a review.

The Notes/Reminders monitor preserves its three local snapshots using exact
receipts, hashes and indexes; this automation does not authorize a push.

## Recover or roll back

After an interruption, run `python3 constellation.py recover example` and inspect
the result. If the remote already contains the intended commit, no duplicate is
created. A changed destination or divergence blocks publication. Checks and
reviews remain frozen during publication. If the remote confirms the commit but
local scoped edits remain, the task stays open: repeat permitted checks, review
and commit in that task. Recovery preserves the prior publication and local edits.

Use `python3 constellation.py install --rollback RECEIPT` to reverse installation.
Receipts stay outside Git; rollback rejects later edits. Historical retirement
has an exact manifest and private backup. Recover versioned content from Git and
local state from that backup. Retain receipts and history while recovery may be
needed.
