# Control-plane audit — 2026-09-07

The previous surface was functional in parts, but not coherent enough to call
optimal. It advertised duplicate procedures, delegated simple routing/search,
misstated helper behavior and could leave retired generated entries discoverable. This audit
consolidates the root hub only; neighboring repositories and global configuration
are outside the update. Existing user work, including video-asincrono, is preserved.

## Selection and capability coverage

The discoverable hub surface moves from 30 skills and 7 agents to 14 skills and
3 agents. Counts include command projections and symlinked skills. Reduction is
a consequence of distinct responsibilities, not a target that overrides utility.

| Previous entries | Current owner | Reason |
| --- | --- | --- |
| multi-repo-status, repo-status, constellation, constellation-brief, repos | repo-status | Git state and brief/index views share one read-only workflow |
| cross-repo-grep, find-in-repos, cross-repo-search agent | find-in-repos | Scoped native search needs no wrapper script or dedicated agent |
| repo-discovery, perimeter-classify, repo-classifier, metadata part of perimeter-keeper | repo-discovery + constellation-cartographer | Discovery, classification and metadata maintenance share evidence |
| tier-discipline, tier-check, dependency part of perimeter-keeper | tier-check + import-graph-auditor | One boundary audit with explicit coverage and exceptions |
| cross-repo-router, repo-route | Current agent + routing contract | Scope selection is a reasoning step, not a separate dispatch |
| repo-bootstrap command and skill | repo-bootstrap skill | One procedure; bootstrap now implements the plan it prints |
| verify-loop, intent-check, evidence, refute, ship-loop | verify-loop | Intent, evidence, counterexamples and final verification are one workflow |
| gate-check, record-verdict | gate-check | Separate assessment/recording modes without repeating research |
| repo-doctor, review-claude-system | repo-doctor | Structural health plus behavioral workflow audit when requested |
| commit-research, commit-constellation | commit-research | Explicit task selection and one governed commit entry |

cross-repo-refactor, quant-loop, debug-metric, codex-sync and video-asincrono
retain distinct procedures. multi-repo-orchestrator remains responsible for
integration across git roots and production-sensitive decomposition. Agent specs
are the roster; the unused duplicate registry/agents.yaml is removed. All three
roles inherit the session model and reasoning effort.

## Concrete repairs

- Correct the edge direction: importer → dependency requires a strictly lower
  dependency tier across distinct numeric-tier QuantOS repos. Fractional tiers,
  Tier 4 code, same-repo imports, UI and test exceptions are distinguished.
- Remove automatic session-start registry rewrites, mandatory evidence tables,
  fixed risk quotas, repeated approval requests and arbitrary loop limits.
- Align instructions with actual options and artifacts: discovery is read-only,
  stack categories differ from tooling profiles, and gate-check uses the actual
  promotion driver and supported writer flags.
- Remove grep_all.sh/status_all.sh wrappers. Their loose argument handling,
  incomplete exclusions and error masking added risk beyond native tools.
  Discovery now reports a failed status read as unknown, not clean.
- Make bootstrap plan/apply coherent, preserve existing files and linked
  worktrees, preflight missing sources and destination conflicts, and stop hiding
  CI failures. Copied import/CI files remain drafts needing actual repo parameters.
- Track projection ownership by fingerprints. Plan before writing; retire only
  unchanged owned files or links. Preserve local/unknown files, reject ancestor
  symlinks and collisions, and never recursively delete a skill directory.
- Rebase copied Markdown links to their real canonical resources. Verify skill
  discovery against exact local origins so a global homonym cannot satisfy it.
- Add exact literal file selection to the governed committer. Require explicit
  selection for pre-staged work, refuse selected partial files, keep temporary
  indexes from falling back to the real index, and synchronize only committed
  paths. Unrelated prepared changes survive; no blanket index reset remains.

## Evidence and limits

The supporting suites live under [tests](../tests/): projection safety,
Codex workflow, hooks, promotion enforcement, bootstrap, discovery status and
exact commit selection. They exercise
refusals, preservation of user work, partial failures, idempotence and relevant
behavior. Native verification distinguishes skills discovered from agent TOML
parsed; a configuration parse cannot establish agent discovery or hook approval.

A separate adversarial review exercised seven prescribed scenarios: constellation
status, a single-repo typo with dirty state, a change across fractional tiers,
ambiguous classification, recording an existing verdict, mixed commit ownership
and hooks without observed runtime trust. These are reviews of behavior prescribed
by the sources, not end-to-end executions of financial research or production work.

Executed verification: 127 tests across eight standalone suites passed. Native
Codex discovered 14/14 local skills and parsed three agent configurations.
The doctor passed validators, structure and Codex checks, with WARN for the
dirty worktree. A second projection wrote nothing and preserved generated mtimes.
Edited Markdown references resolve; the inspected neighboring contracts/workflows
contain no direct references to retired hub paths. These are scoped checks,
not a claim that every possible downstream caller or client behavior was tested.

The global skill-creator was reviewed as fallible guidance and not modified.
Its quick validator depends on PyYAML and does not establish useful scope,
reference integrity, correct tools or effective client discovery. In-memory
probes of its post-parse checks accepted empty content and broken references;
that is not a full runtime compatibility test. No extra scaffold, agent UI file
or validator dependency was added merely to satisfy it.

Remaining boundaries are explicit: static import scans cannot prove all runtime
edges; repository metadata validation is partial; verdict recording does not
establish the statistics and the legacy writer does not atomically update both
ledger files. A fresh native session must establish effective role loading and
hook approval. The hub does not modify client trust to claim success.

Design references: [latest-model guide](https://developers.openai.com/api/docs/guides/latest-model),
[skills](https://learn.chatgpt.com/docs/build-skills),
[subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
Use those as product guidance, then test behavior against this repository's
implementation and contracts. See [Codex parity](codex_parity.md) for operation.
