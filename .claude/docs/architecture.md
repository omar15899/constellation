# Constellation architecture

`~/GitHub/` is the private constellation control-plane repository. Neighboring
repositories have separate histories and local contracts. QuantOS members share
tier and perimeter constraints; adjacent projects retain independent governance.
Current membership lives in [the registry](../registry/repos.yaml), not a fixed
count in this document. The hub has no QuantOS tier.

For Claude Code, the [kernel](../CLAUDE.md) establishes authority, routing and
evidence discipline. The current agent chooses scope directly using
[routing](../contracts/routing.md). Single-repo work continues through local
contracts. Multi-repo implementation uses the orchestrator; metadata and
dependency audits have separate specialist agents. Search and state inspection
use small reusable skills.

Claude Code uses `.claude/`; the hub's native Codex contract lives in
[AGENTS.md](../../AGENTS.md) and [`.codex/`](../../.codex/README.md). Native child
repositories retain their own technical rules and share the
[workspace workflow](../../.codex/WORKSPACE.md). A `.codex/profile.json` marker
reserves each native surface.

For repositories that still use projection,
[codex_sync.py](../scripts/codex_sync.py) projects the explicitly selected target,
preserving modified and unknown outputs; `.codex/local/` is reserved for their
local additions. Configuration, tests and native hook approval remain separate
facts: see [Codex projection](codex_parity.md).

Per-repo AGENTS.md/CLAUDE.md remain authoritative for their implementations.
The hub reads these when descending into a target and does not install its own
infrastructure there without task authority. OmarOS owns vault writing and is
read-only from this plane.

Registry, policies, scripts, hooks and tests are versioned in this hub. Private
run evidence under `.claude/run/` is ignored and must not become a conversation
archive. Reports are created only when needed; idempotent tools do not rewrite
unchanged state. The hub is invoked on demand, with no background polling.
