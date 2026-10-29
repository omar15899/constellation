# Engineering workflow

For substantial or extended work, preserve decisions, findings, evidence and
next steps through the [chosen cycle's progress](../../../ecosystem/docs/progress.md).
Synchronize personal milestones only when local policy authorizes it; do not open
another contract or turn a small task into a tracking procedure.

## Contract and diagnosis

Locate the actual owner of the files and the instructions governing the work.
In Constellation, use `workspace.py` routing and read `AGENTS.md`,
`.codex/PROJECT.md` and the instructions for affected directories. In another
project, preserve its own workflow. Working from a common root does not authorize
editing neighboring projects, external dependencies or global configuration.

Turn the task into criteria a third party can verify: inputs, outputs, expected
errors and relevant compatibility, resource or data constraints. For a bug,
reproduce the failure and distinguish symptom, cause and unresolved hypotheses.
For a refactor, identify the behavior to preserve and its consumers. For a
feature, include the path that makes it usable, not just an isolated function.

Read the code and consumers needed to verify the contracts. Identify relevant
invariants, such as types, units, temporal order, resource ownership,
transactions or permissions. Do not extrapolate architecture from a filename.
If a material decision remains open, compare alternatives through a small
experiment, a primary source or a concrete cost. Resolve routine decisions
with the available context.

## Record and distribute work

Choose the cycle according to the [common protocol](../../../ecosystem/references/protocol.md).
The receiving project's Git workflow governs changes and publication; the
portable CLI retains its schema for deliveries needing semantic evidence
without depending on Git. Resolve its resources relative to the installed
package, not the cwd. The working root is the receiving project; operational
state is private and remains outside the delivery. Do not copy prompts,
transcripts, secrets or sensitive outputs into reports.

Before modifying delivery files, declare the contract and its checks in the
chosen cycle. Connect requirements, exact artifacts and checks that allow them
to be judged; identify inputs and dependencies whose variation could invalidate
the result. In the portable protocol, code requirements use behavioral
acceptance. Do not attribute that schema to the Git contract. A purely
diagnostic task can deliver a report with evidence and limits without modifying
the product. Keep the contract brief for small changes. Answer a read-only query
without deliverables without creating state or a new report; do not present it
as certified by a persisted gate.

Register the IDs returned by the native surface, including all authors of edited
paths, before review. A role name, task alias or planned slot proves neither
identity nor execution. Engine registration and loading an agent profile are
different facts. Profiles in this package inherit model, reasoning effort and
permissions; if they are not loaded, read their instructions and pass them to
the available native agent.

Delegate research, implementation or review only when they provide useful
independent work. Each writer receives exclusive paths, requirements,
dependencies, invariants, expected outcome and a way to verify it. Identify
relevant skills and their accessible locations; the worker must check its own
catalogue and read the instructions it needs. Do not assume it inherits a
connection, tool or profile because the coordinator has it. Warn that it shares
the tree and must preserve others' changes. Subtract busy agents from the shared
effective limit; do not multiply capacity per project. Wait for provider evidence
before integrating a dependent consumer. The coordinator integrates and
publishes; workers deliver files and evidence.

For an ordinary Constellation Git change, use the current session, `workspace.py`
and its dispatch when appropriate; record authors, checks and review there
without opening a second portable contract. If the objective also requires a
mathematical proof or a report with portable-engine guarantees, declare that
obligation, its artifacts and the Git integration's dependency on its current
evidence. Do not duplicate every requirement or assume synchronization between
engines. The protocol details which controls are not interchangeable. Do not
replace an active contract or treat portable closure as publication permission.
The absence of Git does not prevent planning, checking and reviewing files;
do not initialize a repository to satisfy this procedure.

## Implement and check

Choose the design according to the request and observed contracts. Compare the
minimum compatible solution with an abstraction that addresses concrete
variations or reuse: brevity alone does not prove simplicity, and a layer does
not prove generality. If abstractions are requested, make their responsibilities,
contracts and composition explicit; if a direct solution is requested, do not
add architecture by default. Reuse existing structures and update affected
consumers within scope. Keep the delta minimal unless a need is demonstrated;
justify compatibility changes or costs and avoid shims, dependencies and
preventive refactors.

Readability requires being able to follow input → transformation → output.
Choose names that express the domain, structures that expose relationships and
steps readable without reconstructing hidden state. Generalize over required
variations, not hypothetical futures; verify those variations with representative
cases. When assessing efficiency, identify what grows—records, bytes, calls or
dimensions—and the relevant time, memory or I/O cost. Distinguish reasoned
complexity from measurement: a performance improvement requires reproducible
load, units, environment and comparison; without those data, retain the
conclusion as a hypothesis.

### Document decisions and data

In Python use [Google Style for comments and docstrings](https://google.github.io/styleguide/pyguide.html#s3.8-comments-and-docstrings).
Document public APIs and code of non-trivial size or logic. A docstring opens
with a summary and develops the context needed to use the interface without
reading its implementation. Develop the context and data supporting the
contract as fully as necessary; an obvious getter may need only one line.
Preserve the project's applicable conventions and avoid duplicating text in
every wrapper.

Explain the purpose and data flow in the responsible module or class; document
each function's part of the contract. Use `Args:`, `Returns:` or `Yields:` and
`Raises:` when they add information, and `Attributes:` for public attributes
that need it. Describe meanings and constraints that annotations do not express;
add types if absent and you can establish them. For generators, describe values
yielded, input consumption and resources held during iteration. Do not fill
empty sections or repeat the signature verbatim.

Where they affect use, state preconditions, invariants, effects, limits, resource
ownership and lifetime, mutation and aliasing. For collections, records, tables
or tensors, specify fields, keys, relationships, schema, shape, dtype, units,
nulls, empties, duplicates and ordering relevant to the contract. Accompany
difficult structures with a small input/output example compatible with the
implementation, identifying and verifying synthetic values; show what is
preserved, transformed or discarded. Use the program's actual structures and
verify examples: do not invent types, columns, guarantees or results to complete
documentation. If a contract cannot be established, state the gap.

`Raises:` covers errors belonging to the offered interface and their conditions;
it does not turn accidental failures outside preconditions into guarantees.
Place a decision's rationale with its owner: contract and consequences for the
caller in the docstring, non-obvious internal details in comments beside the
code. Explain why a structure or algorithm is chosen when that affects its
understanding, invariants or costs; avoid comments that translate every Python
line into prose.

### Check behavior and documentation

Check observable behavior with representative inputs and boundaries that could
refute the solution. For an automatable regression, retain a test that fails
before the fix and passes afterward. A control change needs both rejection
and a permitted case to detect false blocking. Include consumers or integration
where an isolated test does not reach the contract. An unexecuted command or
skipped test does not count as success.

In numerical code, state the contract's range and precision. Check valid
extremes, intermediate overflow and cancellation that could violate it, with
an independent reference or relevant bounds where needed. A warning in the
documentation does not excuse a violation or permit silently restricting the
requested domain; fix the calculation or state the outstanding obligation.
Justify the chosen solution's cost without imposing an algorithm.

Record final checks through the appropriate cycle against current artifacts.
A worker's preliminary tests help the coordinator but do not replace that
record. For a small edit, an existing focused check may suffice; do not invent
tests that merely search for the text just added. After relevant checks pass,
repeat or broaden them only for changes, failures or a specific concern. Explain
any actual verification limit, including unavailable dependencies or environments.

## Review and resolve

Determine risk through the receiving project's policy and the change's semantic
effect; never lower its minimum. Use the common gate's thresholds:

| Mode | Independent coverage per file |
| --- | --- |
| Quick | One correctness reviewer for low-risk changes allowed by policy |
| Standard | Three correctness reviewers for ordinary code changes |
| Deep | Three correctness reviewers and two security reviewers for sensitive changes |

A small adjustment to hooks, permissions, authentication, publication,
installation or controls can require Deep. Meet the quota and total number of
distinct identities per file; if slots are limited, run reviews sequentially.
Do not use an author to review their own files or invent identities to meet a
quota. If the coverage cannot be obtained, retain the partial state.

Open review after current checks. Give reviewers the current token, diff,
requirements, invariants, relevant consumers and evidence. Request a substantive
assessment of each requirement as well as correctness, regressions and security
according to focus. A list of passed tests or a generic verdict does not replace
the requirement–result connection. Reviewers must inspect artifacts; they do
not edit the object they are reviewing.

Each finding states a reproducible scenario, location, consequence and evidence;
distinguish introduced defects from preexisting ones. Fix the entire error
class and assign verification to an agent independent of authors and discoverers.
Dismissing a false positive also requires independent justification. Record the
result through the protocol; do not erase or close a finding by informal consensus.

A change in artifacts, inputs, contract or checks can invalidate evidence:
consult the current state and renew what is needed. Automatic freshness
controls differ between Git and portable contracts; expressly check semantic
dependencies that the receiving project does not pin. Later rounds cover the
delta and its consequences without losing pending findings. Admission of new
rounds depends on explicit budget and repetition signals, without a universal
three-round maximum. An undeclared budget is unknown. When the engine requires
continuation, state the reason and a concrete action. Replanning preserves
history, findings, authorship and minima; it does not bypass an exhausted
deadline. With obligations pending, keep state open and explain the specific
impediment.

## Integrate and deliver

Before closure, check this chain for each significant requirement:

`requirement → current artifacts → relevant checks → actual authors → current independent review`

Include negative results and limitations without turning them into acceptance.
Hashes bind evidence to a version; agents judge whether that evidence demonstrates
the requirement. If a necessary obligation is discovered, record it in the
contract and resolve it within scope, or retain partial closure.

Integrate dependencies in the order allowed by the receiving project. Before
publication, check scope, diff, other people's staged work, current authorizations
and all gates. Use only the receiving project's authorized commit, push, PR or
deployment workflow; the portable engine neither publishes nor grants permission.
In Constellation, the coordinator uses `workspace.py`, preserves hooks and
checks, and verifies the remote SHA before declaring publication complete. Do
not add a second committer or bypass a rejection. Other projects need their own
scope and authorization; do not transfer the hub's authorization. Do not request
authorization again when it has already been granted for the same action within
the same scope.

Full closure requires all applicable requirements and gates satisfied, including
publication when part of the task. With obligations pending, record partial
closure and explain what works, what evidence exists, what remains and why.
Without Git, the verified delivery consists of the authorized files and their
evidence. Summarize the change and verification in the user's language; do not
claim that review, installation, activation or publication occurred without
evidence of the actual operation.
