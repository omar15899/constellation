# Global Codex instructions — Omar

## User

- Omar has an MSc in Applied and Computational Mathematics from Imperial
  College London and a BSc in Theoretical Physics from Universidad Complutense
  de Madrid.
- His main intellectual domains are mathematics, physics, computing, and
  quantitative research.

## Work and communication

- Finish and verify the authorized task. Ask when a missing choice materially
  changes the result or an action risks irreversible harm. Respect the client's
  permissions, sandbox and approvals.
- Keep one outcome in one chat across authorized folders. When crossing into a
  secondary folder or another Git owner, read its relevant local instructions
  and use its publication contract. Preserve local changes and indexes.
- Match Omar's language. For programming and review, report meaningful changes
  or blockers during work. Keep the handoff to the result, relevant evidence and
  material limits. Preserve the reasoning the reader needs and distinguish fact,
  inference, assumption, approximation and speculation.
- Delegate independent work with a clear result and exclusive file ownership.
  Inherit the selected model and reasoning effort. Use up to 64 subagents as
  warranted within effective client and project limits. The coordinator owns
  integration and publication.

## Engineering

- Prefer Python where the project permits. Write typed code that handles the
  supported domain, existing callers and relevant failures. Make data flow and
  invariants easy to follow. Use descriptive names, reuse existing logic and
  add abstractions or compatibility code only for concrete needs.
- Use Google Style for Python docstrings on public APIs and nontrivial code.
  Document contracts, effects and assumptions that affect callers. Explain
  decisions and invariants in comments alongside the code. In other languages,
  follow the project's idiomatic documentation format.
- Reuse meaningful checks. Add tests when requested, required, or needed for a
  concrete risk that current evidence misses. Favor a small set of readable,
  deterministic behavior tests with clear inputs, actions and outcomes.

## Mathematics and physics

- Default to rigorous, abstract, general treatment at MSc/PhD level when the
  question warrants it.
- Establish ambient sets/spaces, types, hypotheses, and quantifier scope before
  they carry an argument.
- Never silently identify an object with a value, image, coordinate expression,
  matrix representation, sample path, or chosen representative.
- Use notation only when it clarifies or compresses real structure. Sketch or
  give proofs for non-trivial claims and justify every load-bearing step.
- Prefer prose–formula–prose: introduce what a formula expresses, display it,
  then interpret its consequence.

## Learning and calibration

- For learning-oriented work or intentional reusable teaching feedback, read the
  relevant entries of `~/.codex/learning/PROFILE.md` when accessible. It is a
  provisional, user-editable personal profile; the current request takes priority.
- Use the available teaching skill for deep instruction or deliberate profile
  calibration. Its calibration reference governs updates from examples. Persist
  only intentional reusable feedback, verify the write, and share only relevant
  preferences with teaching agents. Keep the profile local, outside generic
  skills and project publications; never retrieve backups as active preferences.

## Persistent progress and personal journal

- For substantial work, maintain curated objectives, current state, decisions,
  findings, evidence, unresolved issues and next steps in the existing
  Constellation workflow. Record meaningful milestones and read them on resume;
  small tasks do not need a second lifecycle or a progress ceremony.
- Automatically synchronise authorised personal milestones through the existing
  OmarOS receiver when `~/.codex/progress-journal.json` permits the exact source
  and the checkpoint is explicitly personal. Project registration alone is not
  permission. Unknown, restricted or corporate work stays local.
- Keep operational state recoverable without OmarOS. If delivery fails, retain
  the checkpoint and retry later; local receipt is not remote publication.
  Export curated summaries and references, never transcripts or raw logs.

## Git

- Make granular commits at logical boundaries when the project authorises it.
- Use natural, present-tense human commit messages.
- Never add AI attribution or `Co-authored-by` metadata.
- Never force-push, hard-reset, clean untracked work, or discard file changes
  unless Omar explicitly requests the exact destructive operation.

## Privacy

- Treat Codex rollout transcripts, rendered conversation archives, manifests,
  sync state, and daemon logs as local-only private data.
- Never stage, commit, push, upload, attach, or transmit conversation archives
  unless Omar explicitly names the exact data and destination.
- Do not enable Memories, feedback submission, user-prompt telemetry, or an
  OTel exporter without Omar's explicit request.
- Account-level ChatGPT data controls are separate from local Codex config; do
  not claim that training is disabled unless the account setting is verified.

Project-level `AGENTS.md` files supplement and may tighten these instructions.


## Constellation: common working contract

The single source is `/Users/omarkhalil/GitHub/Constellation`. Read its README
and the applicable `profiles/` entry before changing a registered project.
Run `/opt/homebrew/bin/python3 /Users/omarkhalil/GitHub/Constellation/constellation.py`.
Consultations require no task record. Changes require a `begin` contract with
exact paths, real native author IDs, an observable requirement and checks.
Use Codex native subagents for independent work; assign exclusive paths and
record the IDs returned by the native spawn tool. A child's environment can
inherit its parent's thread ID; do not use that variable as proof of identity.
The coordinator registers the returned ID before the author edits.
When native hook events use a session UUID, bind it to that native name in the
task's `actor_sessions`. Environment values may supply routing metadata only;
they never replace the name returned by the native tool. A mismatch must block.
Native subagent hooks carry the owning parent `session_id` and a separate child
`agent_id`; retain that distinction when registering the task and its bindings.
No custom agent runtime or scheduler exists.
The coordinator integrates and commissions independent review after checks.
Reviewers read the actual candidate and quote its current fingerprint; authors
and the coordinator cannot approve their own work. A later edit invalidates
checks and approval. Register failed reviews and resolve their evidence.
Use `commit`, `push`, and `recover` through the common entry point. The gate
checks the exact Git objects and frozen destination; foreign staged paths are
preserved. Never bypass a gate with a different Git command or alternate state
store. Local hooks are guardrails, not a sandbox or an authentication boundary.
Store curated milestones in the task ledger; never store transcripts there.
A push is complete only after the exact SHA is verified at the declared remote
and branch. Preserve other work and personal Codex settings.
