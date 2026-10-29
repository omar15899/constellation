# Quantitative campaigns with reproducible evidence

Use this workflow to compose existing capabilities. Adapt stages to the economic
question and the receiving project's contract: a daily ETF strategy, a futures
portfolio and a storage problem require different data, accounting and execution.
Generality comes from extensible contracts and explicit rejection of unsupported
cases.

## Discover before executing

Read the project's instructions, dependency map and current interfaces.
Distinguish declared, discovered, available, executed and verified. An installed
SDK, MCP or adapter does not establish account access, a license, integration
or a successful call. Consult current primary documentation when a decision
depends on changing external capabilities.

In a workspace with separate laboratories, assign responsibilities as follows
and confirm local names and interfaces:

| Outcome | Responsibility |
| --- | --- |
| Data snapshot and admissibility controls | Data laboratory |
| Hypotheses, candidates, family and validation | Research laboratory |
| Simulated orders, fills and causal accounting | Backtesting engine |
| Allocation, exposures and limits certificate | Portfolio and risk |
| Paper trading, connectors and reconciliation | Execution laboratory |
| Campaign, dependencies and persistent state | Receiving project's integration |
| Presentation and navigation through evidence | Interface, without financial recalculation |

Do not introduce imports that reverse their tiers. Agent coordination uses
native capabilities and one contract per Git owner; a local delivery preserves
the receiving project's protocol. Combining disciplines does not require
duplicating the lifecycle.

## Contract the question and the search

Before examining selected results, record the economic hypothesis, falsifiable
prediction, comparable baseline, universe, period, frequency, reference capital
and minimum net improvement. Fix rejection criteria, temporal partitions,
selection objective, budget and stopping conditions. Distinguish the historical
universe from the currently tradable universe.

Identify the family of hypotheses and configurations tested. Register each
attempt before running it, including failures, interruptions and negative
results; state how identical retries and parameter changes are counted.
Preserve both the multiple-testing denominator and complete returns and
selection evidence. Increasing a counter does not recover omitted trials.
Do not reuse a final OOS set to choose the next winner without recording that
it has become selection information.

## Fix admissible data

Preserve provider, revision, instrument identities, calendar, time zone, units,
currencies, corporate actions, adjustments, gaps and usage rights. Distinguish
economic observation, publication and receipt. Where vintages or historical
availability are unknown, report the limitation and restrict conclusions that
depend on it. A market timestamp does not demonstrate that this version was
known at that instant.

Share immutable snapshots and the receiving project's cache among candidates;
do not duplicate downloads per agent or incidentally rebuild storage. Validate
delistings and historical constituents if the hypothesis needs them. Check
raw/adjusted consistency and dividends to avoid double counting. A current
universe does not by itself provide a historical estimate free of survivorship
bias.

Separate interactive queries from bulk acquisition. For offline tests use an
explicit replay transport and fixed clock: omitting a token does not guarantee
that the adapter stops looking up environment credentials or using the network.
Manifests and errors must not contain tokens or private account responses.

## Evaluate causality, economics and selection

Specify when the signal is known, when the order is sent and at which prices
it can execute. Fit normalization, feature selection and parameters only on
the relevant training segment. Use temporal separation and walk-forward;
purge or embargo when overlap between labels/horizons requires it.

Replay decisions, orders, fills, positions and cash with the receiving project's
canonical engine. Check relevant commissions, spread, slippage, FX, financing,
short borrowing, trading restrictions and settlement. Record which costs were
charged and which could not be measured. Distinguish vectorized diagnostic
results from audited causal replay; configuration or data hashes do not equal
an audit root issued by that engine.

Consume the laboratory's complete current promotion report, with the appropriate
family, engine restrictions and execution class. Verify that its cost, turnover,
exposure and penalty inputs were actually supplied. Do not reimplement or lower
a gate to obtain approval. If no applicable policy exists, declare one appropriate
to the experiment before selection, justify statistical assumptions and preserve
its limits.

Evaluate sensitivity to parameters and costs, temporal stability, regimes,
drawdown, liquidity, participation and capacity at the planned capital. Neither
a high Sharpe ratio nor a passed gate guarantees future profitability. A data,
family-evidence, cost or audit blocker keeps the result limited. An imprecise
estimate or insufficient evidence does not by itself refute an economic
hypothesis; distinguish inconclusive results from refutation according to the
fixed criterion and preserve the meaning of the receiving project's verdicts.

## Automate a verifiable chain

Use the receiving project's runner and persistence. Before launching a campaign,
map each stage to an available implementation, its input/output contract and
dependencies; an absent required stage blocks the campaign. If an adapter needs
to be developed, declare it as implementation and verify it before attributing
economic results to it.

Evidence must allow this semantic chain to be reconstructed, using the names
of local contracts rather than adding another parallel schema:

```text
hypothesis and family → snapshot → candidate → audited backtest
  → allocation and risk → validation → paper trading → reconciliation → interface
```

For each result preserve campaign/candidate/family identity, state, inputs and
hashes, code revision, configuration, seeds, output references and a verifiable
reason for failure or limitation. A run without an engine audit leaves that
field absent; it does not fill it with a self-generated hash. Scientific
promotion and operational authorization are different decisions.

Repetition must be idempotent or create a linked new attempt. Preserve state
after interruptions and do not turn a partial output or timeout into success.
Retry policy distinguishes repeatable reads from orders with external effects:
an ambiguous broker response requires reconciliation before resending,
especially without a verified idempotency guarantee.

The automated test pipeline must execute actual behavior with explicit profiles
and produce a machine-readable report of checks, states and failures. A profile
that did not run its required tests cannot return approval. Verify the relevant
invariants:

- Identical replay reproduces decisions, ledger and metrics within declared
  tolerances; changing future information does not alter earlier decisions.
- Cash, positions and corporate actions reconcile; cost changes are reflected
  in P&L and approval where appropriate.
- Stale data, transport failures, missing stages and an incomplete family retain
  their cause and block the result depending on them.
- Interrupting and resuming preserves attempts and provenance without duplicating
  effects.
- An offline profile works without credentials and blocks network access; an
  integration with replay verifies contracts between engines and is not presented
  as a test of a remote provider or broker.
- The interface reflects server state, limits and provenance; it distinguishes
  demonstration data from results and does not compute another profitability
  measure.

## From simulation to broker

Treat EODHD or other providers and T212 or other brokers as distinct roles.
Check actual capabilities for accounts, instruments, history, orders, fills
and modes; do not assume the broker supplies research history. Keep local
replay, simulated paper trading, a remote demo environment and live execution
separate.

Risk and liquidity controls need verifiable artifacts, not booleans without
provenance. Reconciliation compares orders, fills, cash and positions with
evidence from both sides; the mere existence of a ledger does not demonstrate
that comparison. Approved paper trading does not activate live trading. Any
step to real orders requires specific authorization and the receiving project's
own controls.

Deliver the hypothesis, baseline, complete family, result, reproducible evidence
and unresolved limits. Distinguish executed work from designed work and software
checks from economic validity. Curated checkpoints use existing progress;
they do not include prompts, conversations or restricted data.
