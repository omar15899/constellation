# Claude Code on native Windows

The `1.4.0` English package has a native Windows target for Claude Code.
It uses Windows file locks, private access controls and an exec-form Python
hook command. It does not require WSL or a Bash shell for those hooks.
**Native Windows acceptance is pending until the supplied checks have actually
run on Windows.** A build or a successful macOS regression run does not establish
that result. This target does not claim native Windows support for Codex.

## What the package carries

The four skills, eight canonical roles, evidence protocol and review obligations
come from the same source as the POSIX edition. English changes the instructions,
guides, metadata and fixed progress-display strings; the Windows target changes
the platform adapter and the native Claude hook executable. Its hooks use
`command: "python"` with an argument vector, including `-I`, so the client does
not interpret a shell command. Claude's
[exec-form contract](https://code.claude.com/docs/en/hooks#exec-form-and-shell-form)
requires a real executable on Windows; a `.cmd` or `.bat` shim is insufficient.

A distribution contains code and instructions, not accounts, credentials,
conversation history, personal profiles, project data or local permissions.
Keep the work computer's account and managed settings in place. Both language
editions retain the plugin identity `constellation`: install one edition per
client, rather than loading both copies.

## Prepare the package

Use native Windows Python 3.11 or later and a compatible native Claude executable.
The `python` resolved by the environment that launches Claude must select that
supported interpreter. In PowerShell, inspect the commands before installation:

```powershell
python --version
(Get-Command python).Source
(Get-Command claude).Source
claude --version
```

Use a normal local NTFS folder in your user profile. The installer rejects
linked or reparse-point destinations, unexpected files and unsafe ownership;
it does not turn those failures into approval. Git is needed for Git publication,
but the isolated portable acceptance below does not need a corporate repository.

If building from the canonical source checkout, choose new output paths:

```powershell
python .codex/ecosystem/build.py --language en --target windows-claude --output C:\Temp\constellation-1.4.0-en-windows --archive C:\Temp\constellation-1.4.0-en-windows.zip
Get-FileHash C:\Temp\constellation-1.4.0-en-windows.zip -Algorithm SHA256
```

For a delivered ZIP, compare its SHA-256 with the supplied delivery checksum
before extraction. Use a new destination; the example assumes the ZIP is in
the current directory:

```powershell
Get-FileHash .\constellation-1.4.0-en-windows.zip -Algorithm SHA256
$package = Join-Path $env:USERPROFILE 'Downloads\constellation-1.4.0-en-windows'
Expand-Archive -LiteralPath .\constellation-1.4.0-en-windows.zip -DestinationPath $package
```

A checksum detects differences from the delivered artifact; it does not by itself
authenticate whoever supplied both the ZIP and checksum. No personal Codex or
Claude directory needs to be copied from another computer.

## Run isolated backend acceptance first

The following command uses this extracted package and temporary homes with
spaces and Unicode in their paths. It leaves the real Claude home unchanged:

```powershell
python -I -B "$package\ecosystem\tests\windows_acceptance.py" --bundle "$package"
```

If `claude` does not resolve directly to the native executable, pass its real
`.exe` path with `--claude`. The probe rejects shell shims and reparse-point
executable lookups. On another operating system, with missing prerequisites,
or after a failed required check, it returns a nonzero exit status instead of
reporting Windows acceptance.
Named non-Windows tests may be skipped on Windows; their exact IDs are
reported. A skipped Windows case, or an unavailable required hard-link or
symbolic-link fixture, leaves backend acceptance unsatisfied.

Acceptance creates symbolic-link fixtures. If Windows refuses their creation,
for example with WinError 1314 because the test account lacks that capability,
the strict probe remains incomplete; separate junction coverage does not replace
those cases. This is a validation-fixture prerequisite, not a request to give the
installer administrator rights. The script neither requests elevation nor
changes Developer Mode or work policy. Validation may need an authorized test
environment that permits the required fixtures.

The probe verifies the package, invokes local Claude version and plugin-schema
commands, installs into a temporary home, repeats the installation, applies a
synthetic same-version update and checks that unrelated settings and data survive.
It creates an isolated portable contract, replays declared and undeclared
`PreToolUse` events directly, and runs the Windows filesystem and installation
tests. The replay returns a scope decision; it does not execute Claude's native
`Write` tool. The script writes its declared synthetic fixture separately for
the content check.

The final JSON reports `isolated_backend_acceptance` and the number of tests
executed. It also reports `native_claude_event_dispatch:
"pending_manual_check"` and `native_model_quality: "not_evaluated"`. A passing
backend result is evidence for those local checks, not a claim that a real Claude
session dispatched every event or that the model selected the right skill.

This probe does not run the native Windows Git-workflow cases in
`test_core.py` or the PowerShell argument round-trip cases. Its JSON reports
`git_workflow_acceptance: "not_exercised"` and
`powershell_roundtrip: "not_exercised"`. Their acceptance is separate from the
isolated portable-backend result and the manual native Claude event check.

Child processes receive temporary configuration/profile paths and an allowlist
of launch variables; provider credentials are not inherited. The probe issues no
provider or model requests. It applies the documented
[nonessential-traffic controls](https://code.claude.com/docs/en/env-vars)
only to those temporary processes. It does not impose an operating-system
network sandbox on an arbitrary native executable, verify account-level data
settings or change the user's normal update/telemetry configuration.

## Install into the intended Claude home

After reviewing the isolated result, run the protected preflight and installation.
The example uses the default Claude home; select the actual home explicitly if
your work setup uses a different one:

```powershell
$claudeHome = Join-Path $env:USERPROFILE '.claude'
python -I "$package\ecosystem\claude.py" install --bundle "$package" --claude-home "$claudeHome" --check
python -I "$package\ecosystem\claude.py" install --bundle "$package" --claude-home "$claudeHome"
python -I "$package\ecosystem\claude.py" verify --claude-home "$claudeHome"
claude plugin validate --strict --json "$claudeHome\skills\constellation"
```

The preflight validates the interpreter and owned destination before writing.
The installer preserves unrelated files and settings, respects an explicitly
disabled plugin, and refuses an interrupted or modified installation until it
has been inspected. Repeating the same package is idempotent; updating uses a
new verified package with the same command.

After a handled failure, the previous owned payload is restored when its identity
and rollback destination remain verifiable. Changed, partial or independently
owned staging data and rollback collisions are retained for inspection rather
than deleted or replaced to complete cleanup.

The result's `directory_sync` field distinguishes `supported`, `unsupported` and
`not_measured`. Windows file flushing and exclusive directory promotion are
tested separately. A filesystem that does not support directory flushing is
reported as such; the result does not claim POSIX-equivalent directory durability
or recovery after an arbitrary power loss.

Open a new Claude session. The package does not change trust records or override
managed policy. Check the actual catalogue for the four skills and eight roles,
and review native hook status in the client. Keeping the same file paths does
not prove that an already open session reloaded the package.

## Complete the native session check

Use a disposable project containing only synthetic files. Establish a portable
contract whose exact write scope contains `allowed.txt`. In an actual Claude
session, check that a native `Write` to that file is permitted and that a native
`Write` to `undeclared.txt` is rejected without extending the contract. Confirm
that the denied file is absent and that the native event, rather than only a
direct replay, was observed. Check subagent start/stop events separately if that
workflow is required.

This manual session check can use the work computer's approved model connection;
the isolated acceptance script does not start it. Record only curated results,
client version and package hash, without exporting prompts, transcripts,
credentials or corporate material. Model quality, exact skill selection and
scientific validity require their own evidence.

The earlier POSIX tests and model trials remain tied to their recorded snapshots.
They are useful regression evidence, but they do not close this Windows
acceptance. See [observed compatibility](compatibility.md) for that distinction
and [installation and migrations](migrations.md) for the existing POSIX clients.
