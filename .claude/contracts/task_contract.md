# Task Contract

For serious code/research tasks, Claude completes this contract. Skip it for
trivial one-liners. It is the per-task instantiation of the
[Expert-Agent Contract](expert_agent_contract.md).

## 1. User Intent Reconstruction
- [ ] Restate the user's request concretely.
- [ ] Separate explicit requirements from inferred intent.
- [ ] Identify non-goals.
- [ ] Identify user-owned planning decisions.
- [ ] Identify Claude-owned execution decisions.
- [ ] Identify ambiguities resolvable from repo inspection.
- [ ] Identify ambiguities that would change success criteria.

## 2. Definition of Verified Success
- [ ] Define what counts as done.
- [ ] Define required artifacts.
- [ ] Define required checks / tests.
- [ ] Define required report / log updates.
- [ ] Define what would make this only partially complete.
- [ ] Define what would falsify the claim.

## 3. Execution Evidence
- [ ] List files inspected.
- [ ] List files changed.
- [ ] List commands run.
- [ ] List artifacts generated.
- [ ] List tests / checks passed.
- [ ] List failures encountered and repairs made.

## 4. Refutation Pass
- [ ] List at least five ways the current solution could be wrong.
- [ ] Test the cheapest plausible failure mode.
- [ ] Check for stale artifacts.
- [ ] Check for silent fallbacks.
- [ ] Check for NaN / null / empty metrics where relevant.
- [ ] Check whether the qualitative conclusion still follows.

## 5. Research Validity *(when applicable)*
- [ ] Check lookahead leakage.
- [ ] Check feature / label alignment.
- [ ] Check chronological train / test separation.
- [ ] Check survivorship bias.
- [ ] Check current-universe vs historical-universe distinction.
- [ ] Check whether the metric improvement is alpha or beta exposure.
- [ ] Check costs / slippage / turnover assumptions.
- [ ] Check metric sample sizes.

## 6. Safety
- [ ] No secrets printed.
- [ ] No `.env` staged.
- [ ] No token-like values in the staged diff.
- [ ] Broker / API behaviour remains read-only unless explicitly requested.
- [ ] No destructive command without clear user intent.

## 7. Final Claim Discipline
Every serious final answer includes:

| claim | artifact / source | check performed | result | residual caveat |
|---|---|---|---|---|

Rules:
- No artifact / source → unsupported claim.
- NaN / null / empty metric → investigate or state it explicitly.
- "done", "fixed", "wired", "complete", "end-to-end" require hard evidence.
