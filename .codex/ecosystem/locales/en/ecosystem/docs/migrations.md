# Installation and migrations

This guide describes commands and update conditions.
[Observed compatibility](compatibility.md) separately records what has been
tested for each version and client. The examples do not by themselves establish
that the package is installed, trusted or running in an existing session.

## Install and update

Python 3.11+, Git for publication and the chosen client with compatible interfaces
are required. This section retains the POSIX target for macOS/Linux and Linux
environments such as WSL. Native Windows Claude has the explicit candidate
1.4.0-rc.1 target `--language en --target windows-claude` and a
[separate guide](windows.md); actual Windows acceptance remains pending.
The POSIX baseline Claude reference is 2.1.301; that does not establish this
version on Windows or compatibility with earlier versions. WSL use requires
validating the clients and relevant tests in that environment.

### Prepare another laptop

1. Build a distribution at a new destination from published sources:

   ```sh
   python3 .codex/ecosystem/build.py --language en --output /tmp/constellation-1.4.0-rc.1 \
     --archive /tmp/constellation-1.4.0-rc.1.zip
   shasum -a 256 /tmp/constellation-1.4.0-rc.1.zip
   ```

2. Copy the ZIP and retain its SHA-256 through an authorized channel. On the other
   laptop, compare the hash before extraction. The internal inventory then checks
   files, hashes and modes. A hash received alongside the ZIP detects differences,
   but does not by itself authenticate the sender.

3. Install the clients you will use from the extracted package. For Claude:

   ```sh
   python3 /path/constellation-1.4.0-rc.1/ecosystem/claude.py install \
     --bundle /path/constellation-1.4.0-rc.1 --claude-home ~/.claude --check
   python3 /path/constellation-1.4.0-rc.1/ecosystem/claude.py install \
     --bundle /path/constellation-1.4.0-rc.1 --claude-home ~/.claude
   ```

   For Codex, retain the existing native installer:

   ```sh
   python3 /path/constellation-1.4.0-rc.1/ecosystem/install.py \
     --bundle /path/constellation-1.4.0-rc.1 --codex-home ~/.codex --check
   python3 /path/constellation-1.4.0-rc.1/ecosystem/install.py \
     --bundle /path/constellation-1.4.0-rc.1 --codex-home ~/.codex
   ```

4. Verify the installation and open a new client session. For Claude:

   ```sh
   python3 /path/constellation-1.4.0-rc.1/ecosystem/claude.py verify --claude-home ~/.claude
   claude plugin validate --strict --json ~/.claude/skills/constellation
   ```

   Then check the effective catalogue and hooks in the client. For Codex, use the
   [complete diagnostic](#codex-diagnostic) and inspect `/hooks`. Validating the
   package or its schema does not certify trust or execution.

### Codex diagnostic

Replace the package and project paths with their actual directories and ensure
that `python3` is Python 3.11 or later:

```sh
python3 /path/to/package/ecosystem/native.py --codex-home ~/.codex --cwd /path/project --capabilities
```

`--codex-home` is mandatory; `--cwd` fixes the observed project. The command
queries metadata in a new CLI process. It does not install or enable components,
change trust, or execute skills or tools to certify their operation. Its results
do not automatically represent an open chat. A hook marked `modified` requires
review and approval through Codex's native interface before execution can be
attributed to it. Preserving its path does not replace that approval; trust
hashes are never edited to complete it.

### Isolated Claude trial

On macOS, you can add an isolated native trial without a remote model:

```sh
python3 -B /path/constellation-1.4.0-rc.1/ecosystem/tests/native_claude_probe.py \
  --bundle /path/constellation-1.4.0-rc.1
```

It accepts `--claude /path/to/binary` to choose the CLI. It uses a local HTTP
server, synthetic authentication and restrictions that block external networking,
the real HOME and Keychain. It checks native loading, permitted and rejected
paths, pending closure, and blocking when a hook fails operationally. It does not
send data to a model or establish research quality. The trial is limited to
macOS; on another system, report its unavailability as such, without approving
it. Subagent execution requires its own native observation. The 1.3.0 test did
not establish it; consult the [current evidence matrix](compatibility.md) before
attributing that capability to a version.

The distribution contains code and instructions expressly allowed by the builder.
Do not copy `~/.codex` or `~/.claude`: they contain authentication, conversations
and personal state. Private profiles, personal policies, local project
registries, data, providers and MCP authorizations are configured separately on
each laptop. The package does not create accounts, download data or grant new
permissions.

### Claude installation

The installer places the package at `skills/constellation` within the directory
specified by `--claude-home`, with both native manifests. Claude discovers that
plugin as `constellation@skills-dir` in a new session unless its policies prevent
it. No marketplace or `settings.json` edit is needed. Skills remain under
`skills/`; Markdown agents are generated from canonical TOML instructions during
the build. Two independent instruction bodies are not maintained for each role.

Installation verifies ownership and integrity before replacing its directory.
It preserves other skills and settings and respects explicit plugin disabling.
`--check` does not modify user directories. Repeating the same package returns
`unchanged`; an update uses the new package and the same command. Independently
owned changes, links or remnants of an interrupted replacement are rejected
while preserving their files. A handled error restores the previous owned
payload when its identity and rollback destination remain verifiable. Partial,
changed or independently owned data and rollback collisions are retained for
explicit inspection. Abrupt termination may require resolving the interruption
before retrying.
Research state remains outside the replaceable directory.

Installed hooks validate the inventory before loading the shared engine and hold
a shared lock during dispatch, incompatible with installation replacement.
An immutable distribution loaded explicitly through `--plugin-dir` also checks
its inventory; that loading does not amount to permanent installation or
establish client trust.

Distribution 1.3.1 does not change the pin of OmarOS's derived 1.2.0 core. That
receiver verifies its four existing resources and retains its own lifecycle.
Its updater accepts only 1.2.0 bundles and rejects the dual-client package;
updating that receiving contract requires a specific migration, rather than
copying the package onto `.codex/vendor/constellation`.

Permanent loading and its limits follow the official references for
[Claude plugins](https://code.claude.com/docs/en/plugins/create#make-a-plugin-load-in-every-session),
[hooks](https://code.claude.com/docs/en/hooks) and
[subagents](https://code.claude.com/docs/en/sub-agents).

### Codex installation

From the checkout, you can also build and install at a temporary destination:

```sh
python3 .codex/ecosystem/build.py --language en --output /tmp/constellation-bundle \
  --archive /tmp/constellation-bundle.zip
python3 /tmp/constellation-bundle/ecosystem/install.py \
  --bundle /tmp/constellation-bundle --codex-home ~/.codex --check
python3 /tmp/constellation-bundle/ecosystem/install.py \
  --bundle /tmp/constellation-bundle --codex-home ~/.codex
```

Repeat with a new bundle to update. The installer verifies inventories, receipts
and profiles; it preserves independently owned configuration, rejects disabled
plugins and compensates for failures through native operations. Do not edit the
cache or catalogue as sources. Unexpected files require explicit treatment that
preserves them; integrity changes are not ignored to complete an update.

The installer registers the eight specialized profiles under `CODEX_HOME/agents`.
Skill sources remain under `.codex/skills`. If you retain that checkout alongside
the plugin, avoid two active entries through the native helper
`--exclude-source-root "$PWD/.codex"` only when every source resource is byte-identical
to the installed distribution. Existing exclusions are preserved. The canonical
Spanish checkout and the English edition do not satisfy that condition; the helper
correctly rejects their combination without changing exclusions. For an English
installation on another computer, use the extracted package outside the source
checkout and work in the receiving project. The source-only English overlay is
not a separate active skill checkout. Keep this integrity check enabled.

Inspect `/hooks` when a definition changes: installation does not grant trust.
A new session loads updated profiles/configuration; do not assume that an open
session has reloaded its catalogue. Scripts avoid incidental bytecode; use
`python3 -B` to import or test an immutable bundle.

Since 1.2, the five events use the same stable entry, installed outside the
versioned cache:

```sh
python3 -I "${CODEX_HOME:-$HOME/.codex}/constellation/hook.py" EVENT
```

Its source is `ecosystem/hook_entry.py`. Before running the adapter from the
installed catalogue, it validates the receipt, inventories, hashes and modes of
the entry, catalogue and cache. It holds a nonblocking shared lock on
`CODEX_HOME/constellation/.install.lock` during validation and execution;
installation takes that lock exclusively. If it encounters an update in progress
or an inconsistent installation, it responds in a controlled manner: `PreToolUse`
denies; `Stop` and `SubagentStop` warn with `INCOMPLETE` without issuing a block
against state that has not yet been validated. Other events report unavailability.
That warning does not approve closure. After validating the package, the adapter
retains its bounded Stop policy. The entry does not automatically repair an
update terminated by `SIGKILL` or execute the package without verification.

The schema 3 receipt includes `hook.sha256` and `hook.mode`; earlier receipts
1 and 2 are verified for updates without importing their code. A session that
captured the old 1.1 cache command needs to be reopened once to load the stable
entry. An already-loaded stable command can continue resolving future verified
installations. This does not reload the rest of the catalogue or grant trust:
if Codex requires native approval for the new definition, use its interface.
Trust hashes are never edited. Real dispatch evidence is recorded separately
from subprocess tests in [observed compatibility](compatibility.md).

The package does not fix the model, effort or context window. Use the client's
observed limits for each model and revalidate its capabilities when updating;
the historical compatibility described in [observed compatibility](compatibility.md)
covers those trials, rather than every future client or model.

## Organization in 1.3.1 and updating from 1.3.0

Manifest sources live under `ecosystem/manifests/`; maintained guides live under
`ecosystem/docs/`. The builder projects the two plugin manifests to the native
locations `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json`.
The distributed destinations `ecosystem/hooks.json` and
`ecosystem/claude-hooks.json` are retained because they participate in the hooks'
native identity. Their sources are not duplicated, and user trust is not changed
to reorganize them.

Past evaluation evidence lives only in the checkout:
`ecosystem/evals/results/2026-10-18.json` and `ecosystem/docs/history/`. It is not
installed as an operational dependency or a substitute for checks of the current
candidate. Historical JSON values and paths are preserved as dated evidence.

An update must verify the inventory of the version it replaces separately from
the new version's inventory. Intentionally removing a document does not authorize
unknown files, mixed versions or independently owned changes. Migration requires
tests in both clients using an earlier 1.3.0 package, data and settings
preservation, tampering rejection and recovery after a handled failure. The
[acceptance](evaluation.md#acceptance-of-131) matrix states the obligations;
only recorded results establish that they were executed.

## Migration history

The following sections describe earlier transitions. Their versions, counts and
observations are not inventories of the current session.

### Adaptive phase 1.2

Review retains the shared algorithm, its risk floors, independence and accumulated
findings. It replaces the universal three-round maximum with justified continuity
and an explicit time budget. Schema 1 policies remain readable and are normalized
without `max_rounds`; schema 2 rejects that field. Replanning or changing policy
preserves risk and coverage minima, including stricter receiving minima.
`review-budget` records each deadline and extension; `review-start` receives a
reason and next action when cycle detection or lack of progress requires them.
Do not invent a token budget from available context. Consult the
[shared contract](../references/protocol.md#review-continuity-and-budget).

The hook moves from a versioned cache command to
`CODEX_HOME/constellation/hook.py`. The installer maintains the entry and schema 3
receipt; the hook verifies the distribution under a shared lock, while the
installer takes the same lock exclusively. The
[installation contract](../README.md#install-and-update) specifies rejections,
updates from earlier receipts and recovery limits.

The first transition requires reopening threads that retain the old command.
Trust hashes are not edited: if the new definition requires client approval,
use its native interface. The stable entry avoids dependence on the path of a
retired cache in subsequent updates, but does not itself demonstrate skill
reloading or successful dispatch.

The native experiment is preregistered with separate single-agent baseline,
native delegation and Constellation conditions, with capacity and recovery
controls. Its design and status are in [evaluation methodology](evaluation.md).
Deterministic engine and installer tests do not replace that comparison.
Do not attribute improvements in quality, latency or cost before obtaining and
analyzing the results.

### Historical inventory 1.1

Initial audit: 2026-10-18, Codex CLI 0.163.0. The infrastructure of the 21
registered repositories, OmarOS, native configuration and the Constellation
distribution was examined. Conversations, secrets and personal content were not
used as context. Historical 1.0 results do not certify this migration.

| Previous component | Initial evidence | Decision |
| --- | --- | --- |
| Five hub modules | Workflow, workspace, dispatch, review and agent policy implementations | Consolidate under `ecosystem/runtime`; retain small compatible entries |
| Portable review | Already imported the same hub algorithm | Retain one algorithm and one shared policy in the package |
| Mandatory Git registration + portable registration | The engineering skill required both lifecycles | Remove the ritual obligation; choose the lifecycle by its guarantees and objective |
| Global and local skills and plugins | Actual native discovery, documented progressive loading | Retain native mechanisms without copying them all into Constellation |
| Plugin diagnostics | Filtered only Constellation and ignored `warnings` | Extend the native adapter with explicit states and surface |
| Hub hooks | Four events; Stop trusted but disabled | Remove duplicate definitions; one plugin adapter for active contracts |
| Plugin hooks | Five trusted and enabled events; only saw portable contracts | Integrate explicit selection of the active contract without automatically starting work |
| OmarOS | Specialized engine and an almost identical copy of the review algorithm | Consume shared review; retain domain semantics and independent publication |
| 19 native children | Four `.codex` files, without engine/agent/hook copies | Preserve domain and projection protection; reduce redundant overrides when inheritance is verified |
| `.claude` | Parallel infrastructure with real consumers, including Git validators | Isolate by client; do not remove domain validators that still run |
| External `ruflo` | Hooks rejected by `_generated_by`; obsolete timeouts and auto-memory | Diagnose incompatibility; preserve external ownership and do not run automations |
| Installed cache and catalogue | Valid 1.0 cache; catalogue with five additional `.DS_Store` files | Treat as derived; validated update from sources, preserving extras |
| Local context and agents | 1,000,000/900,000 context override in the hub and six inherited profiles | Remove override and duplicate profiles; preserve eight specialized profiles and native per-model limits |
| Personalized learning | Explicit user preferences; insufficient examples for a definitive profile | Provisional local profile and calibration in the teaching skill; no personal data in the package |
| Continuity and journal | Existing operational state, Git and OmarOS's own mechanisms | Add checkpoints to the existing store and a curated projection with exact authorization; no other engine or database |
| Small code changes | Ordinary Standard classification even for a bounded change | Allow justified Quick before the first round when both policies permit it; retain Deep and risk floors |

The initial app-server inventory found 21 skills/18 enabled in the hub, 18/18 in
Sweeplab, 120/22 in OmarOS and 191/191 in ruflo. OmarOS retains four enabled local
skills and 98 deliberate exclusions. The plugin listing contained 24 installed
and 23 enabled plugins; it is not equivalent to the skill catalogue of a new
process or of this session.

An empty directory without Git discovered 18 enabled skills, including the three
Constellation skills, and six hooks (one global and five from the plugin),
without creating files in the directory. This demonstrates native integration
without scaffolding for discovery; execution tests are recorded separately.

### Reversible update

This checkout is the source. The builder generates a bundle with an explicit
inventory; the installer verifies the previous distribution and preserves
independently owned configuration. The cache is not edited as a source and trust
is not changed to make a test pass. A new distribution is installed through
native operations.

Existing task states retain their formats and private location. Public adapters
preserve usual invocations. Evidence or policy changes invalidate the relevant
review; an update does not approve earlier work. Recovery from an interrupted
attempt is explicit and never fabricates a successful check.

`task_progress` is created at the first substantive milestone, without mass
migration of earlier tasks. It retains its UUID and chronology when replanning.
The personal journal policy is not generated from the repository registry: it
permits only explicit roots and aliases. The OmarOS receiver updates its pinned
bundle to consume progress and review; the note and dashboard are created through
its own workflow. Its local receipt does not establish publication. Consult
[recoverable progress](progress.md).

The learning profile and local calibration instructions remain outside the
bundle and Git. The initial basis is provisional and derived from explicit
requirements; future examples may refine or correct it. Synthetic trials use
isolated fictional profiles and do not add real preferences. Research, learning
and engineering are composed according to intent without creating independent
engines or persistent selectors.

The installer accepts verified earlier inventories when adding package resources,
preserving private state and independently owned configuration. Tests cover
updates from schema 1 and 2 receipts in temporary homes. That compatibility does
not authorize unknown files or by itself demonstrate that the personal
installation has been updated.

Restoration consists of deploying a verified earlier distribution and restoring
only the configuration files that were changed, with review of task state as
appropriate. It does not require resetting history, deleting work, enabling
disabled plugins or granting hook trust.

### Validation

The current matrix and its limits are described in [evaluation methodology](evaluation.md).
Automated suites test controls and rejection cases in temporary repositories and
remotes. Actual skill selection and agent execution are evaluated as separate
experiments: deterministic fixtures do not replace them.
