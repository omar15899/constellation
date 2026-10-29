# Language editions

Constellation has one runtime and one packaging contract. The default source
edition is Spanish. The English edition selects reviewed text overlays in
`en/`, using the same source-relative paths as `.codex/`. These overlays are
source resources; the output contains the ordinary package layout, not a second
translation system. Both editions keep the plugin ID `constellation`, version,
module IDs (including `writter`), protocol keys, policies and installer behavior.
Install one edition per client. Installing the other edition replaces that
client's owned package through its normal protected update procedure.

## Build from canonical sources

Use Python 3.11 or later, and choose new destinations:

```sh
python3 .codex/ecosystem/build.py --language en \
  --output /tmp/constellation-1.4.0-rc.1-en \
  --archive /tmp/constellation-1.4.0-rc.1-en.zip
shasum -a 256 /tmp/constellation-1.4.0-rc.1-en.zip
```

The English tree must contain the complete allowlisted translation inventory,
even for a module subset. Missing, empty, linked or extra resources fail before
output is created. Claude agents are generated from the translated canonical
TOML bodies; do not maintain independent Markdown translations for those roles.
The builder keeps canonical file modes and the schema-1 bundle inventory.

All executable resources are shared verbatim between language editions, except
for the progress renderer's fixed display strings. The builder compares its
Python AST without executing the translated file, allowing changes only to an
explicit set of presentation constants. Paths, validation, metadata fields,
control flow and publication statements remain part of the shared contract.
Changing a display string still requires review for accurate meaning; an AST
comparison does not certify the quality of a translation.

## Rebuild and install a portable package

The English ZIP is self-contained. A verified extracted bundle can rebuild
itself or a module subset with its bundled `ecosystem/build.py`, without the
source checkout. Omit `--language` for portable inputs: the default means
preserve existing bytes in this case, including English. An explicit
`--language en` is rejected for portable inputs rather than claiming to convert
a package without its source overlays.

Use the normal commands in the bundled `ecosystem/docs/migrations.md` for Codex
or Claude. Installing does not grant hook trust or copy accounts, credentials,
connectors, conversation history, personal profiles or local authorizations.
No existing personal installation changes when a package is built.

The platform contract remains Python 3.11+ and a compatible client. The default
target retains POSIX behavior on macOS/Linux. Candidate 1.4.0-rc.1 adds the
explicit source target `--target windows-claude` for native Windows Claude Code.
Use both `--language en --target windows-claude` when building that edition.
Portable inputs preserve their existing target by default; they do not perform
a target conversion. Actual Windows acceptance remains pending until its
isolated checks and native session checks run there. Native Windows Codex is
outside this target. See the bundled `ecosystem/docs/windows.md`. Spanish
behavioral evidence remains tied to the snapshots that produced it. It is not a new native model
quality evaluation of the English instructions.
