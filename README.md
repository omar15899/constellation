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
├── tests/                 # existing suites and focused regressions
├── resource-inventory.json
└── migration.py           # inventory, preservation and explicit retirement
```

## Methods and project workflows

The library has 19 maintained skills. Only the five general methods are installed
globally; each project receives its own workflows. Repository constraints belong
in `profiles/`, and the eight agents supply working roles rather than additional
skills for planning, logging, routing or review.
Existing native enable/disable preferences still apply to installed entries.

| Scope | Skills |
| --- | --- |
| General | `coding`, `mathematics`, `quant-research`, `writter`, `teach-from-first-principles` |
| OmarOS | `fast-finder`, `engie-learning`, `ng-diario`, `brainteasers-quant`, `brainteasers-quant-notes`, `doc-forge`, `educational-video-script-architect`, `git-history-reviewer` |
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

Use Python 3.11+, Git and the client you want to configure. Keep the Constellation
checkout or extracted source package in a stable location outside client homes.
Run the installer with `python3 constellation.py` on macOS or Linux and
`py -3 .\constellation.py` in Windows PowerShell.
On Windows, put Git for Windows on your `PATH` or set `CONSTELLATION_GIT` to
the absolute path of its `git.exe`.

| Client | Installer selection | Platform |
| --- | --- | --- |
| Codex | `--client codex` | Windows, macOS, Linux |
| Claude Code | `--client claude` | Windows, macOS, Linux |
| GitHub Copilot CLI | `--client copilot` | Windows, macOS, Linux |
| GitHub Copilot in Microsoft Visual Studio | `--client visual-studio` | Windows |

Use a native client version that supports the capabilities you need. From this
checkout, preview the CLI client configuration and apply it after inspecting
the proposed writes and conflicts.

```sh
python3 constellation.py install
python3 constellation.py install --apply
```

The default `all` selection includes Codex, Claude Code and Copilot CLI and can
touch registered projects. To set up Copilot inside Visual Studio, select the
repository or the personal agents directory configured in the IDE. For example,
from this checkout in PowerShell, with the exact root of a local Git repository:

```powershell
py -3 .\constellation.py install --client visual-studio --project-root 'C:\Projects\Example'
py -3 .\constellation.py install --client visual-studio --project-root 'C:\Projects\Example' --apply
```

See the [Visual Studio guide](profiles/visual-studio.md) for personal discovery,
available versions and verification inside Copilot Chat. Client trust,
authentication, model choice and personal preferences are managed in the client.

On macOS and Linux, the CLI installers use links for shared resources. The
Windows CLI installers and Visual Studio target produce regular files and skill
directories. Reinstall after editing canonical resources. The installer records
private rollback receipts and reports existing entries that need attention.
Windows installation leaves repository Git hook configuration as it was.
On Windows, an installation and its receipt need to be on the same local
volume. Select `install --state-dir` on the target volume if necessary.

The [Claude guide](profiles/claude.md) and [Copilot CLI guide](profiles/copilot.md)
describe native discovery and hook admission. The [automation map](profiles/automations.md)
describes separately installed integrations.

### Projects on another machine

The shared registry in `profiles/projects.json` defines project IDs, policies and
profiles. Bind IDs to an exact local checkout with a private `projects.json`.
On Windows the default location is `%LOCALAPPDATA%\Constellation\projects.json`.
On macOS and Linux it is `~/.local/state/constellation/projects.json`.
Let the installer create a new private state directory on the first installation,
then add the registry if needed. To register projects before the first
installation, store the file in a private location and set
`CONSTELLATION_PROJECTS_FILE` to its absolute path. The installer and tooling in
native client sessions need the same mapping.

```json
{
  "projects": {
    "sweeplab": "D:/Projects/Sweeplab",
    "scilux": "D:/Projects/Scilux"
  }
}
```

Use the actual paths on your machine. Existing matching legacy registrations are
retained. Constellation binds its own project automatically when its source is a
Git checkout. Resolve legacy path examples in project profiles against the
actual local project root.
General skills work across unrelated repositories. Project skills are installed
only for their registered owners. Their resources may require project data,
additional libraries or operating-system tools.

Set `CONSTELLATION_SKILL_PYTHON` to the absolute path of a Python interpreter with
a skill's dependencies. Otherwise `skill-run` uses a configured group interpreter
when available, or the Python running Constellation. OmarOS Fast Finder, ENGIE
learning capture, and the Brainteasers production and course scripts rely on
POSIX filesystem primitives. Use those scripts from macOS or Linux. Their skill
documents and other resources are part of the shared catalogue on Windows.

`python3 constellation.py docs --provider copilot verify` checks local reference
integrity; `search TEXT` searches and `refresh` explicitly downloads current
official pages. Providers are `codex`, `claude`, `copilot` and `all`.
The documentation snapshot tool currently requires macOS or Linux.

## Engineering and parallel review

Make the smallest complete change that meets the requirement. Preserve existing
contracts, reuse domain logic, and favor clear control flow and efficient
algorithms. Add abstractions when they solve a present need. Use Google Style
docstrings for Python. The coding skill and canonical roles explain the standard.

Start with static inspection and independent review. Preserve existing tests and
skip new ones by default. Keep test work focused when requested, required by the
project, or necessary to cover a concrete regression risk. Honor tighter limits
and report the scope and limits of the evidence.

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
python3 constellation.py publish example 'Describe the change'
```

`contract.json` contains `root`, `requirement`, `coordinator`, `session_id`,
`assignments` (path to native author ID) and `required_checks` (for example,
`["whitespace"]`). Select checks appropriate to the change; whitespace alone
establishes no behavioral correctness. Use `mode: "local"` for a local deliverable
and close it with `finish` after checks and independent review. The default
publication mode freezes the Git destination. Obtain authorization for the
scope and destination before opening a task for publication.

For automatic publication, include `mode: "publish"` and a
`publication_message` in the authorized task contract. Once all required checks
are current, recording independent approval with `review` creates the commit,
pushes to the declared destination, and verifies its remote SHA. Reviewers can
record a rejection or approve while checks are still pending. The automatic
publication runs on an approval of the current candidate when the gate is ready.

Use `publish TASK MESSAGE` for one-step publication after review when a contract
has no publication message. Use `publish TASK` to resume with the stored message
or retry an already created commit. `commit` and `push` remain available as
individual commands. A remote failure leaves the review and any local commit
available for retry. Complete a pending publication before another task moves
its local branch or the exact same remote ref.

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
`~/.local/state/constellation` on macOS and Linux and
`%LOCALAPPDATA%\Constellation` on Windows. They contain neither conversations nor
tool output.

Shared hooks inspect structured edits and recognized destructive commands.
They cannot isolate arbitrary shell writes. Stop hooks report pending work
without inventing completion. Git controls the candidate tree, outgoing commits
and exact destination. Publication preserves foreign staged work and confirms
the remote SHA. Recorded identities enforce declared independence; they neither
authenticate processes nor certify the intellectual quality of a review.

The Notes/Reminders monitor preserves its three local snapshots using exact
receipts, hashes and indexes; this automation does not authorize a push.

### Publish existing work and remove private tracking

Existing staging remains outside a task by default. When the user authorizes
publishing that work, the contract's `policy` can declare three exact path lists:

- `adopt_staged_paths` includes owned staged paths. Publication uses the current
  worktree version; the reviewed fingerprint also binds the staged object IDs
  and modes. A private index backup and local recovery ref retain the previous
  staging before the owned entries change. Foreign staging remains untouched.
- `remove_paths` removes owned tracked paths from the candidate and index without
  reading or deleting their local files. This supports private-data cleanup and
  removal of old tracked descendants beneath a replacement skill link. Paths
  may be tracked in HEAD or only in the index.
- `symlink_paths` permits owned leaf links. Review binds the link target text,
  without following it. Other paths cannot traverse a link; every removed
  descendant of a replacement directory must have explicit ownership.

These options require declared ownership and independent review; they do not
permit private content in an outgoing tree. Source templates named
`.env.example` are distinguished from environment secrets; private parent
directories and project restrictions still apply. Browser captures and daemon
output remain private runtime data. Keep removed local data ignored in its
owning repository so a later task cannot accidentally propose it again.

## Recover or roll back

After an interrupted publication, retry `python3 constellation.py publish example`.
Use `recover example` to inspect and reconcile a staged publication separately.
When the remote already contains the intended commit, the workflow verifies that
same SHA. A changed destination or divergence blocks publication. Checks and
reviews remain frozen during publication. If the remote confirms the commit but
local scoped edits remain, run fresh checks and obtain review to publish them
in the same task. If you restore those paths to the verified version, retry
`publish` to close the task with its original receipt. Recovery preserves the
prior publication and local edits.

Use `python3 constellation.py install --rollback RECEIPT` to reverse installation.
Receipts stay outside Git; rollback rejects later edits. Historical retirement
has an exact manifest and private backup. Recover versioned content from Git and
local state from that backup. Retain receipts and history while recovery may be
needed.
