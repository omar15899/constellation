# Constellation: shared authority and native execution

Constellation coordinates contracts, evidence, review and publication. Codex and
Claude Code run models, tools, agents, sessions and permissions. Real files and
their Git owner retain authority; an index or receipt describes their state,
rather than creating another source of truth.

## Responsibilities and sources

| Responsibility | Implementation and boundary |
| --- | --- |
| Capability discovery and execution | Native client, session catalogue and effective permissions. |
| Selection and composition | Model and relevant instructions; no additional skill selector. |
| Public entry point | `ecosystem/cli.py` with `git`, `workspace`, `agent-policy` and portable operations. |
| Git publication | `runtime/workflow.py` and `workspace.py`; owner-specific contract, review and upstream. |
| Portable evidence | `core.py` and `storage.py`; private SQLite and delivery without requiring Git. |
| Independent review | `runtime/review_gate.py` and current schema-2 policy. |
| Progress | `runtime/progress.py` and existing stores; OmarOS receiver only with exact authorization. |
| Filesystem | `platform_support.py`; real locks, identity, access and exclusive promotion per OS. |
| Native adaptation | `hooks.py`, `hook_entry.py`, `claude_hooks.py` and installers. |
| Method | Four skills, references and eight roles inheriting model, effort and permissions. |

Current formats are bundle inventory 1, Codex receipt 3, Claude receipt 1 and
review policy/ledger 2. Those numbers belong to different contracts. Retired
formats are rejected without executing or overwriting their copies; no alternate
engine or inventory is loaded for compatibility.

## Source and distribution organisation

`.codex/ecosystem/` contains the runtime, adapters, manifests, roles, method,
guides and tests; `.codex/skills/` contains skill instructions.
`ecosystem/cli.py` is the single entry point. The builder distributes only its
allowlisted paths and generates the projections each client requires.

Claude Markdown roles come from canonical TOML. The Claude bootstrap
mechanically embeds platform primitives so it can verify the inventory before
importing package code. The remaining runtime uses the same helper from the
verified distribution. There are no two manually maintained implementations,
and an event does not select executable code from a project.

English translations are sources selected during the build. For the same target,
the engine is shared; the progress renderer permits only declared display
constants. An extracted package preserves language and target when rebuilt
without conversion options. History is available through Git revisions, without
retired reports in the active structure.

## One distribution for several computers

Current delivery `1.4.0-rc.1` retains four skills, eight roles and a full inventory
of 82 resources. Module variants retain only the roles they need. `posix` covers
macOS/Linux; `windows-claude` adapts Claude Code for native Windows. Actual
execution there remains pending, as stated in [compatibility](compatibility.md)
and the [Windows guide](windows.md).

Computers share methodological sources and contracts, not accounts, data,
connectors, personal registries or authorizations. Installers preserve foreign
data under installation locks; hooks retain a shared lock through verification
and dispatch. Trust belongs to the client.

## Work criteria by responsibility

An explanation establishes objects, structures and hypotheses before using them,
distinguishes a function from its value and a representation from its object.
Notation should clarify a relationship, and essential steps must be reconstructible.

Engineering starts from requested behavior, real code and its consumers. Compare
a sufficient intervention with a justified abstraction, make data flow visible,
and check relevant valid cases and rejections. Reasoned cost and measured
performance are different claims.

Research states sources, refutable hypotheses, contrary evidence and limits.
Handoffs contain what an autonomous task needs; a failed agent or missing evidence
does not become a completed dependency. Independent review seeks defects and
requires evidence, rather than votes.

## One sufficient workflow per objective

A Git task uses the receiver's contract. A portable delivery retains semantic
evidence without publishing. Mixed work declares the dependency between those
results without duplicating the whole assignment or treating portable closure
as publication permission. Brief queries remain brief, subject to obligations
already imposed by an active contract.

The coordinator records real authors before review. Quick requires one correctness
reviewer; Standard, three; Deep, three correctness and two security reviewers,
with coverage and distinct people per file. Open findings block completion;
resolution requires a verifier distinct from author and discoverer.
The [protocol](../references/protocol.md) defines data and freshness.

## Continuity and personal knowledge

Progress lives in private Git JSON or portable SQLite. Source history stays in
Git. OmarOS receives only personal syntheses authorized for the exact root and
alias; local receipt does not establish publication or closure. Pedagogical
profiles and corporate data are not exported by association.

The active OmarOS adapter retains its 1.2.0 pin of four verified resources.
It is a current receiver specialization, not a retired structure. Updating the
plugin neither replaces nor overwrites that adapter.

## Verifiable boundaries

Controls bind scope, bytes, identity, access and evidence to a version. Windows
checks DACLs and reparse points; a logical Unix mode does not replace an ACL.
Directory promotion is exclusive; a filesystem without the required primitive
is rejected. Directory-flush status is explicit and does not establish durability
against every power loss.

The guard observes declared editing paths, not every shell or MCP write. It does
not replace client permissions. Hashes and quorums likewise do not prove editorial
quality, mathematical truth, empirical validity or universal skill selection.
Those obligations require substantive evidence.

## Correspondence with designs published by Anthropic

Composition, self-contained handoffs and outcome checks are comparable with
published mechanisms for
[composable agents](https://www.anthropic.com/research/building-effective-agents)
and [multi-agent research](https://www.anthropic.com/research/multi-agent-research-system).
This correspondence neither reveals a provider's internal architecture nor
establishes its experimental results in Constellation.

Operational references are the hook contracts for
[Codex](https://learn.chatgpt.com/docs/hooks) and
[Claude](https://code.claude.com/docs/en/hooks).
