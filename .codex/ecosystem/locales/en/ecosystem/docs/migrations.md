# Installation and maintenance

This guide describes Constellation's active `1.4.0` format. The package has
one allowlisted layout. Retired formats are rejected without executing or
replacing their files; they are not silently converted.

## Install and update

Python 3.11+ and the chosen client are required. `python3` must resolve that
interpreter in the environment launching the POSIX client. Git is used for
publication, not for a portable delivery without Git.

| Target | Use |
| --- | --- |
| `posix` | Codex and Claude Code on macOS/Linux. |
| `windows-claude` | Candidate for native Windows Claude; actual acceptance remains pending. |

For Windows follow the [specific guide](windows.md). Do not use the Codex
installer there or interpret packaging tests as native Windows execution.

From canonical sources, choose new paths:

```sh
python3 .codex/ecosystem/build.py --language en \
  --output /tmp/constellation-1.4.0-en \
  --archive /tmp/constellation-1.4.0-en.zip
shasum -a 256 /tmp/constellation-1.4.0-en.zip
```

`--language en --target windows-claude` selects the English native Windows
Claude package. An existing portable package preserves its language and target
when rebuilt without those options; it does not perform conversion. The ZIP is
self-contained. Check its hash through the delivery channel and extract into a
new destination. A hash detects differences but does not itself authenticate
the sender.

### Claude installation

With an extracted POSIX package:

```sh
python3 /path/to/package/ecosystem/claude.py install \
  --bundle /path/to/package --claude-home ~/.claude --check
python3 /path/to/package/ecosystem/claude.py install \
  --bundle /path/to/package --claude-home ~/.claude
python3 /path/to/package/ecosystem/claude.py verify --claude-home ~/.claude
claude plugin validate --strict --json ~/.claude/skills/constellation
```

The installer manages `skills/constellation` with a schema-1 Claude receipt.
It preserves unrelated skills and settings and respects explicit disablement.
It neither copies accounts nor grants trust. Open a new session and inspect
the real client's catalogue, roles and events: structural validation does not
prove dispatch.

### Codex installation

```sh
python3 /path/to/package/ecosystem/install.py \
  --bundle /path/to/package --codex-home ~/.codex --check
python3 /path/to/package/ecosystem/install.py \
  --bundle /path/to/package --codex-home ~/.codex
```

Codex uses a schema-4 receipt. The stable launcher
`$CODEX_HOME/constellation/run` has mode 0700 and a digest recorded in that
receipt. It invokes `hook.py` with the absolute Python used for installation,
including the original virtual environment spelling. The installer verifies
the prior version's receipt before migrating it. The installer preserves unrelated
configuration and registers the roles needed by the selected modules. If source
and plugin copies are active together, native source exclusion requires exact
identity between them. Spanish sources are not identical to the English package:
use the extracted package outside the checkout in that case.

### Install one published revision across devices

Constellation publishes its code on `main` in `omar15899/constellation`. From
a trusted checkout or verified package, explicitly select and promote the
latest published commit once per device:

```sh
python3 -I -B .codex/ecosystem/sync.py --latest --vault-root "$ABSOLUTE_OMAROS_ROOT" \
  --workspace-root "$ABSOLUTE_CONSTELLATION_ROOT"
```

An existing install provides the same command at
`~/.codex/constellation/catalog/plugins/constellation/ecosystem/sync.py`.
`--vault-root` selects the four general methods and the optional `omaros`
module. This profile requires Python 3.11+ with PyYAML and the absolute path
to this device's OmarOS Git root. Vault search tools require `rg`; Brainteasers
compilation uses the project's TeX distribution. `--general` explicitly selects the four
general methods. The default language is Spanish. `--language en` selects
available English overlays. `--codex-home` and `--codex` select the native
installation and executable for the device.

`--latest` trusts the main branch of the fixed canonical repository, freezes its
SHA in a private temporary copy and builds that exact revision. To require an
independently approved SHA, use `--revision "$APPROVED_REVISION"` in place of
`--latest`. If `main` has advanced, the pinned check exits before installing. `--check` verifies the package and installation
preflight without changing the installation or registering the vault. Git probes the canonical HTTPS URL outside every project, rejects URL
rewrites, then uses independent HTTPS-only configuration with TLS verification
and redirects disabled. Recognized standard credential helpers or the GitHub
CLI integration explicitly configured for GitHub are supported. At promotion,
the installer checks under its lock that the receipt still matches the one
observed before downloading. If another process already installed a different
state, retry the synchronization against the newly observed state. Output
includes the Git SHA, inventory digest and modules. Installation uses the
installer's lock, integrity checks and recovery. Repeating an installed
revision and selection returns `current` after checking its inventory and
native registration.

On a verified installation, `"$HOME/.codex/constellation/run" install-vault --project-root "$ABSOLUTE_OMAROS_ROOT"` prepares the personal profile
with the same Codex executable. It installs the owned Git guards, configures
applicable native exclusions and registers the exact root on success. A vault
setup failure reports the completed package installation separately. Correct
the reported condition and retry the same SHA. Folders on the device share its installed
package. Open a fresh session if the client needs to reload its catalogue and
review hook trust in `/hooks`. To promote a revision across devices, run the
command with the same approved SHA on each. Verify receipt and native
activation separately on each device. [Periodic updates](updates.md) are opt-in
per device. `updates plan` previews the definition to be installed.

The optional `--workspace-root` excludes duplicates in the actual source
checkout at the end of installation. Its sources must correspond to the
selected package. If this folder is missing, has local edits to the relevant
resources, or belongs to another revision, the command distinguishes the
completed installation from the pending exclusion. Preserve local work,
compare that revision and retry. `--check` skips exclusion writes.

You can also finish this step separately with the installed native diagnostic.
`CONSTELLATION_ROOT` identifies the permanent checkout on this device:

```sh
python3 -I -B "$HOME/.codex/constellation/catalog/plugins/constellation/ecosystem/native.py" \
  --codex-home "$HOME/.codex" --cwd "$CONSTELLATION_ROOT" \
  --exclude-source-root "$CONSTELLATION_ROOT/.codex"
```

The operation compares source and installed resources, including contents and
permissions, scopes changes to the selected paths, and checks discovery with
a fresh native client. These exclusions refer to the checkout that the device's
client discovers.

### Codex diagnostic

```sh
python3 /path/to/package/ecosystem/native.py \
  --codex-home ~/.codex --cwd /path/to/project --capabilities
```

The query describes a new CLI process; it does not install components, load
skills or automatically represent an open session. Recorded CLI evidence belongs
to 0.165.0. Revalidate capabilities when the client or version changes.

Inspect `/hooks` for effective enablement and trust. Never edit hashes or use
options to bypass approval. Installed, discovered, enabled, trusted and an event
actually executed are distinct states.

## Integrity, updates and recovery

Current formats are bundle inventory 1, Codex receipt 4, Claude receipt 1 and
review policy/ledger 2. A version number does not replace validation of schema,
inventory, hashes, permissions and identity. An incompatible format, unknown
file or modified copy blocks the operation while preserving files for explicit
inspection.

An update between versions with the compatible format uses the same command and
a new verified package. Repeating the installed package is idempotent. Preflight
does not modify the selected home. Hooks hold a shared lock through verification
and execution; replacement requires the exclusive lock.

Directory promotion is exclusive. If a filesystem lacks the required primitive,
the operation fails without replacing foreign data. After a handled failure,
the previous copy is restored when its identity and rollback destination remain
verifiable. Partial, changed or foreign data and collisions are preserved,
rather than deleted to manufacture recovery. Inspect an interruption before
retrying.

The Claude installer result reports `directory_sync`: `supported`, `unsupported` or `not_measured`. A file
flush does not establish directory-metadata durability against every power loss.
Windows uses verified DACLs for private access; a logical Unix mode is not a
substitute.

Do not copy complete Codex or Claude homes, credentials, conversations, personal
profiles or project state. Operational state stays outside the replaceable plugin
directory. Imports from an immutable package use `python3 -B` to avoid adding
bytecode outside its inventory.

## Receivers and evidence

The optional OmarOS profile executes the vault lifecycle from the verified
Constellation package. Exact-root registration is local to each device. Project
context, data and publication permissions belong to their Git owner.

[Compatibility](compatibility.md) separates evidence by snapshot and platform;
[evaluation](evaluation.md) distinguishes mechanism checks from substantive
quality. Retired results are available in Git, not loaded as installation
dependencies. Native references are the hook contracts for
[Codex](https://learn.chatgpt.com/docs/hooks) and
[Claude](https://code.claude.com/docs/en/hooks).
