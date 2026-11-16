---
name: execution-lifecycle-doctrine
description: ExecutionLab's load-bearing doctrine. Enforces the IAR triple (Intent / Action / Realization) separation, idempotency keys, never-auto-promote-to-live, append-only ledger, and the RiskLab-certificate gate before any broker call. Use whenever ExecutionLab code, agents, or commands touch the proposal-order-fill chain, the trading mode, or the broker boundary.
license: proprietary
contract_invariants:
  - I1_iar_triple_separation
  - I2_append_only_ledger
  - I3_idempotency_key_required
  - I4_risklab_certificate_gate
  - I5_never_auto_promote_to_live
  - I6_single_execution_surface
  - I7_capability_split_read_default
  - I8_human_override_for_live
---

# Execution Lifecycle Doctrine

Five non-negotiables. Every ExecutionLab agent, command, and code path
must satisfy all five. Violations are bugs, not exceptions.

---

## I1 — IAR triple separation

The lifecycle is partitioned into three layers. They are never collapsed.

| Layer       | Object          | Owner                   |
| ----------- | --------------- | ----------------------- |
| Intent      | `OrderProposal` | strategy / governance   |
| Action      | `Order`         | `lifecycle-engineer`    |
| Realization | `Fill`          | `ibkr-adapter-engineer` |

A function that builds an `Order` from raw inputs without going through
`OrderProposal` is a violation. A function that produces a `Fill` not
tied to a parent `Order` row is a violation.

---

## I2 — Append-only ledger (ADR-0002)

The Postgres tables `order_proposals`, `orders`, `fills`, `positions`,
`cashflows`, `mode_transition_events`, `reconciliation_breaks`,
`reconciliation_runs` are append-only. `UPDATE` and `DELETE` are revoked
at the role level. Corrections are new rows with a `correction_of`
foreign key. Status transitions are new rows with an `event_type`
discriminator.

Any code that issues `UPDATE` or `DELETE` against these tables is a
data-integrity violation. The DB enforces this; the engine never tries.

---

## I3 — Idempotency key required

Every `OrderProposal` carries a deterministic `idempotency_key` derived
from `(strategy_id, decision_record_id, instrument_id, side, quantity,
bar_timestamp)`. The lifecycle engine:

- rejects duplicate proposals in the open set,
- derives the broker `clientOrderId` from the key (so the broker also
  rejects duplicates),
- groups fills by key for PostTradeReview.

A submission without an idempotency_key is rejected at the gateway,
before the broker is contacted.

---

## I4 — RiskLab-certificate gate

`IBKRExecutionGateway.submit_approved_order` refuses any proposal
whose `risk_certificate` is not in the `passed` state. The certificate
is the materialised result of pre-trade check 4. A missing or `failed`
certificate is rejected with `RISK_LIMIT_BREACH`.

The `execution_preflight` hook verifies the same property *before* the
shell command starts.

---

## I5 — Never auto-promote to live

`live` mode is reachable only from `dry-run`, only with a typed
passphrase, only with an explicit human-override id, and only when
reconciliation is clean, data is fresh, and all kill switches are green.
The system **auto-reverts** to `dry-run` on restart, exception, or
health-check failure (ADR-0025).

Any code that sets `mode = "live"` programmatically without traversing
the `mode-switcher` gate is a doctrinal violation. Any agent that
suggests "skip the passphrase" is refused.

---

## I6 — Single execution surface (E1)

`IBKRExecutionGateway.submit_approved_order` is the **only** code path
in QuantOS that calls the broker order-placement API. A second call
site is a CI failure, not a style issue. Enforced by
`tests/contract/test_no_orphan_broker_calls.py`.

---

## I7 — Capability split, read by default

The broker adapter exposes two Capability protocols:
`IBKRReadCapability` and `IBKRWriteCapability`. Functions receive the
narrowest capability they need. Read is the default; write is granted
only on a complete, certified, idempotent, override-bearing proposal
in a write-permitting mode.

A function with only `IBKRReadCapability` cannot place orders — and
mypy enforces that statically.

---

## I8 — Human override for live

Every live-mode broker-touching action carries an explicit
`human_override_id` resolvable in the audit log. The
`execution_preflight` hook (P4) blocks the action if the override is
absent. Reading `EXECUTIONLAB_HUMAN_OVERRIDE` from the environment is
acceptable; assuming the override is not.

---

## References

- `docs/vault/decisions/ADR-0002-orders-fills-postgres.md`
- `docs/vault/decisions/ADR-0003-ib-insync-adapter.md`
- `docs/vault/decisions/ADR-0025-four-trading-modes.md`
- `docs/vault/labs/executionlab/Vision/00_Doctrine.md`
- `docs/vault/labs/quantos/Vision/Policies/EXECUTION_POLICY.md`
