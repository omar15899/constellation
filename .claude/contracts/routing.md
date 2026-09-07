# Routing

The current agent establishes scope before non-trivial work. Routing is a
reasoning step, not a separate agent call or an additional approval.

1. Identify the intended result and relevant git roots from the registry and
   repository contracts. The constellation hub is a separate repo with no tier.
2. Answer conceptual questions directly. Use `find-in-repos` for search and
   `repo-status` for state, inventory or a constellation brief.
3. Use `repo-discovery` and `constellation-cartographer` for classification,
   discovery or metadata drift; `tier-check` and `import-graph-auditor` for
   dependency and perimeter boundaries.
4. Use `multi-repo-orchestrator` for implementation spanning multiple git roots,
   and for work involving ExecutionLab, real money or Tier 3. For one other
   repository, load its local contracts and continue directly.
5. Requests to write in OmarOS belong to its workflow. Do not write vault
   material from the hub. Technical discussion does not itself require vault work.

Keep obvious routing brief. Inspect evidence before asking about ambiguity;
ask only when it changes the target, authority or intended outcome. When asked
to explain routing, report the operation, targets, workflow and justification.
No fixed envelope is required for ordinary tasks.
