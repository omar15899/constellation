# Ecosystem evaluation

Evaluation separates three questions: whether the package preserves its
contracts, whether the client executes the intended mechanisms, and whether
the substantive response is correct. A hash, installation test or review quorum
does not by itself answer the other questions.

## What is evaluated

| Obligation | Relevant evidence |
| --- | --- |
| Distribution | Inventory, hashes, modes/access, projections, reconstruction and deterministic ZIP. |
| Installation | Fresh case, repetition, compatible-format update, preservation of data, tampering rejection and recovery. |
| Native execution | Real catalogue, effective trust, observed events and allowed/rejected operations. |
| Engineering | Behavior and regressions that can refute the implementation, including control failures. |
| Mathematics | Explicit objects and hypotheses, proof or counterexample, and independent assessment of essential steps. |
| Quantitative research | Causal data and timestamps, complete search, out-of-sample validation and relevant accounting. |
| Writing | Accuracy, argument, scope and human reading; formal completeness does not prove editorial quality. |

Selecting a skill, loading it and applying it correctly are distinct observations.
A directed trial tests application under known instructions; it does not establish
automatic selection. Each result identifies sources, snapshot, client, inputs
and limits. A relevant change requires revalidating the claims that depend on it.

## Reproducible checks

From the checkout, with `python3` version 3.11+ also on child processes' PATH:

```sh
python3 -B -m unittest discover -s .codex/ecosystem/tests -v
python3 -B -m unittest discover -s .codex/tests -v
python3 .codex/ecosystem/validate.py
```

Run relevant checks through the owner's workflow to record their snapshot.
Export matrices repeat tests for module and target variants; do not add those
results as independent observations. A skipped or unexecuted case is not a pass.

`native_claude_probe.py` retains its macOS isolation and locally simulated HTTP
responses. Removing isolation does not make it compatible elsewhere.
`windows_acceptance.py` covers the Windows backend and requires that OS; it
does not by itself establish client event dispatch, Git workflow or PowerShell
argument round trips. Follow the [Windows guide](windows.md) for its scope.

## Recorded evidence

[Compatibility](compatibility.md#published-baseline) contains the bounded matrix
for the published baseline, before final cleanup. New cleanup checks are
established in the workflow and execution trace, not by retaining an earlier
table. Removing formats or documents has not produced a new model evaluation.

Earlier trials retain both positive and negative results. On one snapshot,
three of four substantive cases invoked the expected method; the editorial case
did not, and two simple controls avoided tools. Structural checks on those
responses did not establish exhaustive truth.

Later editorial generation contained errors, and an autonomous repetition did
not resolve them all. A pass with explicitly authorized feedback produced a
corrected artifact verified by two independent reviewers. That establishes a
guided correction of that artifact, not general autonomous reliability.
Attempts blocked before transmission made no call and produced no result;
they are not counted as executed evaluations.

Provider evidence and complete hashes remain available in the
[baseline Git revision](https://github.com/omar15899/constellation/commit/fd824929a50ad8e2473988107ae0b129213c1be7). Retaining that history does not require
retired reports in the active tree or runtime support for reading their formats.

## Review and acceptance

The coordinator compares every requirement with current artifacts and checks,
records real native authors, and obtains independent review per file. Every open
finding blocks completion. A person distinct from author and discoverer verifies
its repair or dismissal with concrete evidence.

Operational success does not certify a scientific conclusion. Tests, intellectual
review and any human approval required by the receiver are separate obligations.
Pending Windows acceptance remains pending until actual execution; an English
edition or structural cleanup does not substitute for it.
