# Language and target editions

Constellation has one current layout and one packaging contract. The default
language retains Spanish sources; `en/` supplies the complete allowlisted English
overlays. Their paths match the canonical `.codex/` sources. They are build
inputs, not another active skill checkout.

Both editions retain the `constellation` plugin identity, current
`1.4.0-rc.1` version, four module IDs (including `writter`), protocol keys and
review obligations. Install one edition per client.

## Build from canonical sources

Use Python 3.11+ and new output paths:

```sh
python3 .codex/ecosystem/build.py --language en \
  --output /tmp/constellation-1.4.0-rc.1-en \
  --archive /tmp/constellation-1.4.0-rc.1-en.zip
```

Add `--target windows-claude` for the native Windows Claude candidate. The
default `posix` target covers macOS/Linux. Actual Windows acceptance remains
pending; native Windows Codex is outside that target. Follow the bundled
`ecosystem/docs/windows.md`.

The English tree must contain the complete fixed translation inventory, even
for a module subset. Missing, empty, linked or extra resources fail before output.
The constructor generates Claude Markdown roles from translated TOML, rather
than maintaining separate instruction bodies.

For the same target, executable resources are shared across languages except
for fixed progress-renderer display strings. An AST comparison permits only
their declared constants without executing translated Python. It does not
certify translation accuracy. Platform primitives in the standalone Claude
bootstrap are a mechanical projection of their canonical source.

## Rebuild and install

A verified extracted package can rebuild itself or a module subset without the
checkout. Omit `--language` and `--target` for portable inputs: defaults preserve
its existing bytes, language and target. Explicit conversions are rejected
because portable packages do not contain the source overlays needed for them.

The schema-1 bundle inventory records file hashes and logical modes. Codex
ownership uses receipt 3; Claude uses receipt 1; current review policy and ledger
use schema 2. Retired formats are rejected while their files remain preserved.
Updates between versions with the current compatible layout retain the
protected installation and recovery contract.

Use `ecosystem/docs/migrations.md` for installation. Building does not change a
personal installation; installing neither copies accounts, credentials,
conversations or profiles nor grants hook trust. Local permissions and private
data remain with their owner.

Source history and earlier evidence remain in Git revisions. They are not
alternate runtime inputs or a new evaluation of the English candidate.
