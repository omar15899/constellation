# Constellation

Constellation coordinates requirements, evidence, review and publication on
Codex and Claude Code. The clients run models, tools and agents; each project
retains its files, permissions and Git ownership. Current distribution
`1.4.0` combines four general methods and eight roles. The personal edition
adds seven skills and the OmarOS profile to the same installed runtime.

The coordinator consults its session's catalogue and loads relevant instructions.
Discovery, enablement, authorization, execution and result quality are distinct
facts. The [architecture](docs/architecture.md) defines those responsibilities;
[compatibility](docs/compatibility.md) retains the evidence and its limits.

## Choose the workflow

| Outcome | Execution |
| --- | --- |
| Brief question or small local edit | Response and proportionate checking, respecting any active receiver contract. |
| Git change | One owner contract, checks, review and publication through `ecosystem/cli.py git`. |
| Repository coordination | `ecosystem/cli.py workspace`; separate contracts for each Git owner. |
| Research or document requiring persistent evidence | Portable protocol, including without Git; its closure does not publish. |

The `coding`, `mathematics`, `quant-research` and `writter` skills cover substantive
engineering, mathematical arguments, systematic research and writing. Select them
for the task and the receiver's instructions. A brief explanation does not itself
create a team or contract. Static method guidance does not read or store prompts
and does not prove correct skill selection.

## Structure

| Source | Responsibility |
| --- | --- |
| `.codex/skills/` | Canonical sources for the four general methods and the seven OmarOS module skills. |
| `.codex/ecosystem/runtime/` | Git, workspace, dispatch, review and progress. |
| `core.py`, `storage.py`, `cli.py` | Portable contracts, private persistence and public entry point. |
| `platform_support.py` | Platform-specific filesystem and access primitives. |
| `manifests/` and `agents/` | Native manifests and eight canonical roles. |
| `references/` and `docs/` | Current method, protocol and guides. |
| `tests/` and `evals/` | Current tests and evaluation fixtures. |
| `locales/en/` | Source translations selected during the build, not another active installation. |

The builder accepts only an explicit inventory. It generates Claude agents from
TOML and the standalone bootstrap from canonical sources, rather than maintaining
another manual body. History is available in Git, without retired reports as
delivery dependencies.

## Install and update

Python 3.11+ and the chosen client are required. The `posix` target covers
macOS/Linux; `windows-claude` is the candidate for native Windows Claude without
WSL. Actual acceptance there remains pending. Follow the
[Windows guide](docs/windows.md) for that target.

From canonical sources, choose a new destination:

```sh
python3 .codex/ecosystem/build.py --language en \
  --output /tmp/constellation-1.4.0-en \
  --archive /tmp/constellation-1.4.0-en.zip
shasum -a 256 /tmp/constellation-1.4.0-en.zip
```

The default edition retains the Spanish sources. Both editions use the same
identity: install one per client. The package does not copy accounts, credentials,
conversations, personal profiles or project data.

The [installation guide](docs/migrations.md#install-and-update) describes
preflight, verification and updates of the current format. Retired formats are
rejected while their files are preserved; there is no implicit conversion.
Installing or retaining a path does not grant hook trust.

## Work and check

On a configured device the stable entry verifies the installed release and holds
its lock while using the workspace, the project Git contract or a skill:

```sh
entry="${CODEX_HOME:-$HOME/.codex}/constellation/run"
"$entry" cli workspace route Shared/README.md
"$entry" cli git --root /path/to/project --session ID begin
"$entry" cli skill-read writter
```

The source CLI accepts `--source` for development within the owning checkout.
The portable API remains available from a verified extracted distribution.

The [protocol](references/protocol.md) separates Git and portable delivery. In
Claude, the lifecycle identity is `claude-<session_id>`; authors and reviewers
retain their native IDs. Substantial work keeps
[recoverable progress](docs/progress.md) in the existing store.

Inventory and review checks bind version and evidence; they do not themselves
prove mathematical truth, editorial quality or performance.
[Evaluation](docs/evaluation.md) distinguishes those obligations and retains
negative results.
