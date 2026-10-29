# Installation and maintenance

This guide describes Constellation's active `1.4.0-rc.1` format. The package has
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
  --output /tmp/constellation-1.4.0-rc.1-en \
  --archive /tmp/constellation-1.4.0-rc.1-en.zip
shasum -a 256 /tmp/constellation-1.4.0-rc.1-en.zip
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

Codex uses native registration, a schema-3 receipt and the stable entry point
`CODEX_HOME/constellation/hook.py`. The installer preserves unrelated
configuration and registers the roles needed by the selected modules. If source
and plugin copies are active together, native source exclusion requires exact
identity between them. Spanish sources are not identical to the English package:
use the extracted package outside the checkout in that case.

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

Current formats are bundle inventory 1, Codex receipt 3, Claude receipt 1 and
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

The active OmarOS adapter retains four verified resources pinned to 1.2.0 and
its own workflow. It is not a retired format. Installing the plugin does not
authorize overwriting that receiver or changing its pin.

[Compatibility](compatibility.md) separates evidence by snapshot and platform;
[evaluation](evaluation.md) distinguishes mechanism checks from substantive
quality. Retired results are available in Git, not loaded as installation
dependencies. Native references are the hook contracts for
[Codex](https://learn.chatgpt.com/docs/hooks) and
[Claude](https://code.claude.com/docs/en/hooks).
