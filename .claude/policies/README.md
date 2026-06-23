# `~/GitHub/.claude/policies/`

The doctrine layer of the constellation hub. Every cross-repo agent,
skill, and hook reads these before acting on ambiguous cases.

| Policy                          | Topic                                                        |
| ------------------------------- | ------------------------------------------------------------ |
| `perimeter_doctrine.md`         | Which repos belong to which perimeter; cross-perimeter rules |
| `shared_vs_local.md`            | When a primitive belongs in Shared vs in a lab               |
| `tier_discipline.md`            | The QuantOS tier ladder and how it is enforced               |
| `cross_repo_commits.md`         | One commit per repo, tier-ordered, no bundling               |
| `escalation_to_omaros.md`       | When and how to hand semantic work to the vault              |
| `ai_invariants.md`              | The non-negotiable rules for any AI agent here               |

## Precedence

When two policies appear to disagree:

1. `ai_invariants.md` wins. It is, by construction, non-negotiable.
2. `tier_discipline.md` wins over `shared_vs_local.md` (a primitive
   cannot live in Shared if doing so would create a tier inversion).
3. `escalation_to_omaros.md` wins for any request whose primary output
   is semantic — the vault-side decision binds the hub.

## How a Claude session uses these

Every constellation agent (`agents/*.md`) and every skill
(`skills/*/SKILL.md`) references the relevant policy explicitly in
its "Invariants" section. A session that picks up a non-trivial
request:

1. Reads the kernel (`~/GitHub/.claude/CLAUDE.md`).
2. Reads the routing taxonomy in `cross-repo-router`.
3. Reads the relevant policy from this directory if the request
   touches it.
4. Acts.

Policies here are short and pointed by design. If a policy needs to
be longer, the topic probably needs to be split.
