# Per-device Constellation updates

Each computer uses one installation across its projects. An optional user
schedule checks the published `main` commit of Constellation's canonical
repository every hour. It first requests only the remote reference. If the
revision, configured profile, or installation receipt changed, it downloads
that exact published revision and runs the same verified synchronization and
binding used for initial setup. The new candidate confirms the workspace against
its own bundle digest before that revision is acknowledged. A network failure keeps the installed version
available. A later interval retries incomplete setup.

On a POSIX device with a verified installation, use the stable device entry,
canonical vault root, Constellation source checkout and actual Codex executable.
The source on this computer is `~/.codex`. Here `--workspace-root` identifies
the source whose skills are excluded from duplicate native discovery. The
operational project workspace remains `~/GitHub`, selected with
`cli workspace --root ~/GitHub`. The `plan` command prints the launchd or systemd
user definitions and activation commands for this device.

```sh
~/.codex/constellation/run updates plan \
  --vault-root ~/OmarOS --workspace-root ~/.codex --codex /path/to/codex
```

Inspect the output of `plan` before choosing `enable`. The `enable` operation
writes persistent user configuration. On macOS, launchd may load the job at
the next login; the returned activation commands can start it immediately.
On Linux, the activation commands enable the timer in the user systemd manager.
For a generic installation, replace `--vault-root ...` with `--general`.
Enrollment accepts future published `main` revisions from the canonical
upstream. Use [SHA-pinned synchronization](migrations.md) on devices where
each revision requires separate approval.

The stable entry verifies the package before running the timer. The private
installation state records the last confirmed promotion. A local checkout
that gains package skill names, or changed discovery settings, triggers
reconciliation against the installed bundle independently of the published
revision. The timer calls the stable launcher across interpreter rotations. The same
marker remembers which source paths native discovery confirmed as disabled.
Re-enabling a source may remove the native `false` row. The timer preserves
that choice and stops before applying other exclusions. To resume, disable the
local source again in the client, or withdraw workspace enrollment to keep
the source enabled. For an older marker without suppression history, inspect
active source paths before resuming automatic updates. Unchanged polls
finish quietly. The user supervisor reports failure and the exit status.
Run `tick` with the enrollment arguments to reproduce a check in the
foreground. A foreign definition remains in place and produces a conflict.
To withdraw, execute the displayed deactivation command and remove only unit
files that still match this device's plan.

New work uses the shared installation after a successful promotion. Each
supervisor requires an active user service or session and normal access to the
private repository. Offline devices adopt the revision upon reconnection.
Running chats retain the catalogue loaded by their client; verify native
events and trust after updating.
