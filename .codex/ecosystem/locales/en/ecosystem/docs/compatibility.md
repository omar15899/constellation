# Compatibility and evidence

The `1.4.0` distribution includes four general methods and eight roles.
On POSIX Codex, the optional `omaros` module adds the vault engine and seven
skills. The built package inventory identifies the selected resources. Targets are `posix` and `windows-claude`.
A valid inventory does not establish execution, native trust or response quality.

## Platforms and limits

| Scope | Status and limit |
| --- | --- |
| Codex CLI and desktop app with local execution | The client supports locally installed plugins. A new session can inspect the refreshed catalogue and hook trust. [Codex plugins](https://learn.chatgpt.com/docs/plugins) |
| IDE extension and cloud-orchestrated ChatGPT Work | The IDE extension does not load plugins. Cloud-orchestrated Work does not execute the local plugin's hooks. [Plugin support](https://learn.chatgpt.com/docs/plugins) · [Hooks](https://learn.chatgpt.com/docs/hooks) |
| macOS/Linux | POSIX target, Python 3.11+, compatible client and filesystem supporting exclusive promotion. |
| Git publication on POSIX | Requires Git 2.48 or later. Before transfer, the engine verifies it can replace the remote URL list with the sole authorized endpoint. A push was verified with Git 2.50.1. |
| Native Windows Claude | Candidate adaptation without WSL; actual execution remains pending and the user has deferred it. |
| Native Windows Codex | Outside this delivery's Windows target. |
| Hook trust | Native client review; neither installation nor retained paths grant it. |
| OmarOS | The central `omaros` profile uses the local contract, vault restrictions and per-owner publication. |

The [Windows guide](windows.md) distinguishes installation, isolated backend
checks, direct replays, events in a real client, Git and PowerShell. The latter
scopes do not follow from a replay result. The probe neither imposes network
confinement on the native executable nor verifies account controls.

## Published baseline

The coordinator's record for [fd824929](https://github.com/omar15899/constellation/commit/fd824929a50ad8e2473988107ae0b129213c1be7) predates the final removal
of retired formats and documents. These are its observed results, not projected
counts for the current cleanup:

| Check | Baseline result | Limit |
| --- | --- | --- |
| Composed source suite | 508 cases: 476 executed and 32 host skips. | Skips do not establish their platforms. |
| Hub | 429 of 429. | Applies to that snapshot. |
| Five English POSIX exports | 491 cases per variant; executed: full 459, coding 447, mathematics 448, quant-research 441, writter 449; skips: 32/44/43/50/42. | Variants reuse tests; these are not independent counts to add together. |
| Five Windows Claude target exports | 35 cases per variant: 30 executed and 5 skipped. | Format and packaging were tested from macOS, not Windows APIs. |
| Ten bundles | Immutable inventories and modes; relocation, reconstruction and reproducible ZIP. | Integrity and reconstruction, not semantic quality. |
| English Codex on macOS | CLI 0.165.0 catalogue: four skills and five hooks without granted trust. | New-process query; not execution in every chat. |
| English Claude | Strict native schema, fresh/repeated installation and language switches preserved foreign data and settings. | Isolated checks, not Windows acceptance. |

That adaptation work issued no new model requests. Subsequent cleanup checks are
recorded in the owner's workflow and execution trace. This table neither replaces
them nor invents their results.

## Scope of the evidence

Earlier selection and quality trials belong to their snapshots. Three expected
skill invocations occurred in four positive cases, alongside two proportionate
negative controls; the editorial case did not invoke its method. A later
editorial correction needed authorized feedback and independent verification.
It remains a guided correction, not autonomous success or evaluation of the
Windows candidate. [Evaluation](evaluation.md) explains how to interpret those
results.

Capabilities depend on version, surface and permissions. The client retains
model, effort and effective limits. Unobserved telemetry and account controls
remain unknown. Changing sources or installing a package does not establish that
an open session reloaded it.

Detailed history remains in Git revisions. Retired reports are not installed,
and earlier formats are not loaded to reconstruct missing evidence.
