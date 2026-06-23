# Perimeter Doctrine

Every directory under `~/GitHub/` carries exactly one **perimeter**.
The perimeter determines tier discipline, governance, vault home, and
allowed cross-imports.

## The perimeters

| Perimeter      | Tier scope | Vault-bound | Tier-enforced | Members                                            |
| -------------- | ---------- | ----------- | ------------- | -------------------------------------------------- |
| `quantos-core` | 0–1.5      | yes         | yes           | Shared, BacktestLab, MonteCarloLab, Sweeplab, PricingLab |
| `quantos-info` | 2          | yes         | yes           | NewsLab, ResearchLab, IntelligenceLab              |
| `quantos-alloc`| 2.5        | yes         | yes           | PortfolioLab                                       |
| `quantos-prod` | 3          | yes         | yes           | RiskLab, ExecutionLab                              |
| `quantos-ui`   | UI         | yes         | no            | tradinginterface                                   |
| `adjacent`     | n/a        | optional    | no            | Scilux, MMARV1, KarimSpecificCase                  |
| `future`       | n/a        | n/a         | n/a           | (reserved)                                         |

## Cross-perimeter imports

| From → To              | `quantos-core` | `quantos-info` | `quantos-alloc` | `quantos-prod` | `quantos-ui` | `adjacent` |
| ---------------------- | -------------- | -------------- | --------------- | -------------- | ------------ | ---------- |
| **quantos-core**       | tier-internal  | ✗              | ✗               | ✗              | ✗            | ✗          |
| **quantos-info**       | ✓              | tier-internal  | ✗               | ✗              | ✗            | ✗          |
| **quantos-alloc**      | ✓              | ✓              | tier-internal   | ✗              | ✗            | ✗          |
| **quantos-prod**       | ✓              | ✓              | ✓               | tier-internal  | ✗            | ✗          |
| **quantos-ui** (HTTP)  | ✓ HTTP/WS only | ✓ HTTP/WS only | ✓ HTTP/WS only  | ✓ HTTP/WS only | tier-internal| ✗          |
| **adjacent**           | ✗              | ✗              | ✗               | ✗              | ✗            | self-only  |

- ✓ → allowed.
- ✗ → forbidden. `import-graph-auditor` flags as `tier_inversion` or
  `perimeter-leak`.
- "tier-internal" → cross-imports inside the perimeter are bounded by
  the QuantOS tier ladder.

## Decision rules

1. **Adjacent repos are self-contained.** They must never import from
   QuantOS labs. If a need emerges, the adjacent repo first applies to
   be promoted into a QuantOS perimeter (open a vault-side decision).
2. **No back-imports up the tier ladder.** A Tier *k* component may not
   import from a Tier *j* component with *j ≥ k*. This is hard.
3. **UI talks over HTTP/WS only.** `tradinginterface` is a separate
   process — Python imports across the UI boundary are forbidden by
   construction.
4. **`future` perimeter cannot host code.** It is a naming reservation
   only; promote into a real perimeter before adding code.

## Drift detection

The `perimeter-keeper` agent watches for:

- An `adjacent` repo's deps gaining `quant_core` or similar.
- A `quantos-*` repo whose `.importlinter` contract no longer matches
  its declared tier.
- A repo whose `claude_dir`, `vault_link`, or `stack` field in
  `registry/repos.yaml` no longer matches reality.

When drift is detected, the keeper writes `docs/drift_report.md` and
the constellation orchestrator surfaces the report before any
cross-repo work proceeds.

## Promotion / demotion

Promoting an `adjacent` repo into a QuantOS perimeter requires:

1. A vault-side decision under `~/OmarOS/05_Projects/QuantOS/Decisions/`.
2. A new `.importlinter` contract for the repo.
3. A vault-side vision note under `05_Projects/QuantOS/Labs/<repo>/Vision/`.
4. An update to `registry/repos.yaml` and to the relevant `peers.yaml`
   files (via `peer_sync.py`).

Demotion follows the reverse path. Neither is a low-risk operation.
