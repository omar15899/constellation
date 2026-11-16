# Isomorph Synth — Worked Example

One end-to-end example: an 8-section `project-isomorph` dossier as input, an assembled 6-section scaffold artefact as output. Both are synthetic — no real project is described here.

---

## Input (excerpt from a `project-isomorph` dossier)

```markdown
# 1. Project Abstract Overview

- Purpose: batch pipeline that ingests observed instrument quotes from a
  market-data vendor, calibrates an instrument-valuation model, produces
  per-instrument valuations and first-order sensitivities, and publishes
  both a structured report and a downstream message stream.
- System type: pricing engine.
- Core architectural paradigm: batch pipeline-and-filter with a
  calibration loop at its core.

# 2. Global Architecture Graph
Module_Ingestion → Module_Calibration → Module_Valuation → Module_Reporting

# 3. Folder / Module Structure
## Module_Ingestion  ## Module_Calibration  ## Module_Valuation  ## Module_Reporting
  (each with Role / Dependencies / Interfaces / Invariants)

# 4. Component Specifications
## ObservationIngestorComponent           (stateful, calls vendor adapter)
## CalibrationOrchestratorComponent       (pure, numerical optimisation)
## ClosedFormValuationComponent           (pure, closed-form over a log-normal model)
## SimulationValuationComponent           (stochastic, seed-controlled Monte Carlo)
## ReportRendererComponent                (pure, formats valuations)
## EventPublisherComponent                (side-effectful, message broker)

# 5. Data Structures & Schemas
## Dataset_RawObservations  (col_timestamp, col_identifier, col_bid, col_ask, col_volume_bucket)
## Dataset_CalibratedParameters  (col_calibration_timestamp, col_model_class, col_parameters, col_residual_norm, col_seed)
## Dataset_DerivedValuations  (col_identifier, col_present_value, col_first_order_sensitivity_k)

# 6. Execution Flow
1. init  2. ingest  3. calibrate  4. value  5. publish

# 7. Integration Points
## ExternalService_MarketDataVendor  (read, HTTP+streaming, vendor auth)
## Database_OperationalStore         (read/write, SQL over TCP, IAM)
## Topic_DownstreamPnL               (write, pub/sub, mTLS)

# 8. Reconstructability Notes
Required: Ingestor, Calibrator (≥1 model class), at least one Valuation
branch (closed-form or sim), Renderer, Publisher.
Known non-preservation: specific calibration tuning, early-exercise
heuristic thresholds.
```

---

## Output (the 6-section synthesized scaffold — condensed)

````markdown
# 1. Assumptions

- **Stack / runtime**: Python 3.11+, `uv` as the package manager, `pytest` for tests. Justification: spec declares `pricing engine` with numerical calibration — the Python numerical stack is the most commonly reintegrable for this system type (see `stack_selection.md`).
- **HTTP client**: `httpx` (sync + async). The spec calls out a vendor SDK; `httpx` stands in generically.
- **Optimisation library**: `scipy.optimize.least_squares` — generic choice for the implied Levenberg–Marquardt-style calibration.
- **Message broker client**: `aio-pika` stub adapter; the firm's actual broker will be bound at reintegration.
- **Database**: SQLite file-based store for the scaffold's self-test; swap for the firm's operational store at reintegration.
- **Observability**: stdout via the Python `logging` module; rebind to the firm's observability sink at reintegration.
- **Calibration regulariser**: `λ = 1e-3`, purely a default; re-tune at reintegration (spec flagged this as non-preserved).

# 2. Generated folder structure

```text
pricing-engine-scaffold/
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   └── pricing_engine/
│       ├── __init__.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── schemas.py
│       │   └── valuation.py
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   └── adapters/
│       │       ├── __init__.py
│       │       ├── market_data_adapter.py
│       │       ├── operational_store_adapter.py
│       │       └── event_publisher_adapter.py
│       ├── interfaces/
│       │   ├── __init__.py
│       │   ├── market_data_interface.py
│       │   ├── operational_store_interface.py
│       │   └── event_publisher_interface.py
│       ├── calibration.py
│       ├── ingestion.py
│       ├── reporting.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py
│       └── pipeline.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/
    │   └── synthetic_observations.parquet
    ├── test_schemas.py
    ├── test_ingestion.py
    ├── test_calibration.py
    ├── test_valuation.py
    ├── test_reporting.py
    └── test_end_to_end.py
```

# 3. File contents

## pyproject.toml

```toml
[project]
name = "pricing-engine-scaffold"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "httpx>=0.27",
  "pandas>=2.2",
  "numpy>=1.26",
  "scipy>=1.13",
  "aio-pika>=9.4",
  "pydantic>=2.7",
]
[dependency-groups]
dev = ["pytest>=8.0", "ruff>=0.5"]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

## src/pricing_engine/domain/schemas.py

```python
"""
Data contracts for the pricing engine. These are the stable types the rest
of the scaffold refers to; downstream binding preserves them.
"""
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


ModelClass = Literal["closed_form_lognormal", "simulation_monte_carlo"]
VolumeBucket = Literal["very_low", "low", "medium", "high"]


class InstrumentHandle(BaseModel):
    identifier: str = Field(..., description="Opaque handle of the instrument.")
    strike: float
    maturity: datetime


class MarketObservation(BaseModel):
    col_timestamp: datetime
    col_identifier: str
    col_bid: float
    col_ask: float
    col_volume_bucket: VolumeBucket


class CalibratedParameterSet(BaseModel):
    col_calibration_timestamp: datetime
    col_model_class: ModelClass
    col_parameters: dict[str, float]
    col_residual_norm: float
    col_seed: int


class ValuationResult(BaseModel):
    col_identifier: str
    col_present_value: float
    col_first_order_sensitivities: dict[str, float]
```

## src/pricing_engine/interfaces/market_data_interface.py

```python
"""
Abstract interface for the external market-data vendor. The scaffold
provides an in-memory adapter; the firm supplies the real one at
reintegration time.
"""
from __future__ import annotations
from typing import Protocol
import pandas as pd
from pricing_engine.domain.schemas import InstrumentHandle


class MarketDataInterface(Protocol):
    def fetch_observations(
        self,
        universe: list[InstrumentHandle],
    ) -> pd.DataFrame:
        """
        Fetch current observations for the given instrument universe.

        Returns a DataFrame with columns matching the `MarketObservation`
        schema. Must tolerate transient upstream failures without
        propagating them; a retry/backoff policy is expected.
        """
        ...
```

## src/pricing_engine/infrastructure/adapters/market_data_adapter.py

```python
"""
USER-INTEGRATION REQUIRED
Market-data adapter for the upstream vendor. Replace the stub body with
the firm's real client. The returned DataFrame must match the
`MarketObservation` schema in `pricing_engine.domain.schemas`; the adapter
must tolerate transient 5xx without propagating them and must not cache
across calibration runs.
"""
from __future__ import annotations
import pandas as pd
from pricing_engine.domain.schemas import InstrumentHandle
from pricing_engine.interfaces.market_data_interface import MarketDataInterface


class MarketDataAdapter(MarketDataInterface):
    def fetch_observations(self, universe: list[InstrumentHandle]) -> pd.DataFrame:
        # USER-INTEGRATION REQUIRED: bind to the firm's real vendor client.
        # The stub below reads a shipped fixture so the scaffold boots
        # without network; swap for real upstream at reintegration.
        from tests.fixtures.synthetic_observations import load_stub
        return load_stub([i.identifier for i in universe])
```

## src/pricing_engine/domain/valuation.py

```python
"""
Instrument valuation components. Each branch is a generic default whose
body is replaced at reintegration by the firm's proprietary routine.
Signatures and output shapes are stable.
"""
from __future__ import annotations
import math
from datetime import datetime
import numpy as np
from pricing_engine.domain.schemas import (
    InstrumentHandle, MarketObservation, CalibratedParameterSet, ValuationResult,
)

_SECONDS_PER_YEAR = 365.25 * 24 * 3600


def compute_closed_form_valuation(
    instrument: InstrumentHandle,
    params: CalibratedParameterSet,
    observation: MarketObservation,
) -> ValuationResult:
    """
    ADAPTATION POINT
    Generic closed-form valuation under a log-normal asset model (vanilla
    Black–Scholes). Replace with the firm's proprietary valuation while
    preserving signature and output shape. Must be deterministic for a
    fixed (instrument, params, observation) triple.
    """
    # ADAPTATION POINT: swap body for the proprietary routine; generic
    # vanilla Black–Scholes below serves as a runnable default for tests.
    S = (observation.col_bid + observation.col_ask) / 2.0
    K = instrument.strike
    T = (instrument.maturity - observation.col_timestamp).total_seconds() / _SECONDS_PER_YEAR
    r = params.col_parameters.get("short_rate", 0.0)
    sigma = params.col_parameters.get("implied_vol", 0.2)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    from math import erf
    N = lambda x: 0.5 * (1 + erf(x / math.sqrt(2)))
    pv = S * N(d1) - K * math.exp(-r * T) * N(d2)
    delta = N(d1)
    vega = S * math.sqrt(T) * (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1**2)
    return ValuationResult(
        col_identifier=instrument.identifier,
        col_present_value=pv,
        col_first_order_sensitivities={"delta": delta, "vega": vega},
    )


def compute_simulation_valuation(
    instrument: InstrumentHandle,
    params: CalibratedParameterSet,
    observation: MarketObservation,
    n_paths: int = 10_000,
) -> ValuationResult:
    """
    ADAPTATION POINT
    Generic Monte-Carlo valuation with a log-normal GBM and a vanilla
    payoff. Replace with the firm's proprietary simulation while
    preserving signature and output shape. Determinism is enforced via
    `params.col_seed`.
    """
    # ADAPTATION POINT: swap body for the proprietary simulation.
    rng = np.random.default_rng(params.col_seed)
    S = (observation.col_bid + observation.col_ask) / 2.0
    K = instrument.strike
    T = (instrument.maturity - observation.col_timestamp).total_seconds() / _SECONDS_PER_YEAR
    r = params.col_parameters.get("short_rate", 0.0)
    sigma = params.col_parameters.get("implied_vol", 0.2)
    Z = rng.standard_normal(n_paths)
    ST = S * np.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * Z)
    payoff = np.maximum(ST - K, 0.0) * math.exp(-r * T)
    pv = float(payoff.mean())
    standard_error = float(payoff.std(ddof=1) / math.sqrt(n_paths))
    return ValuationResult(
        col_identifier=instrument.identifier,
        col_present_value=pv,
        col_first_order_sensitivities={"standard_error": standard_error},
    )
```

(… remaining files follow the same pattern — calibration, reporting, pipeline, tests. Elided here for brevity; see the live skill for the full layout.)

# 4. Adaptation points

- **USER-INTEGRATION REQUIRED** in `src/pricing_engine/infrastructure/adapters/market_data_adapter.py:MarketDataAdapter.fetch_observations` — bind to the firm's real market-data vendor client; returned DataFrame must match `MarketObservation` schema; must tolerate transient 5xx without propagating them.
- **USER-INTEGRATION REQUIRED** in `src/pricing_engine/infrastructure/adapters/operational_store_adapter.py:OperationalStoreAdapter` — bind read/write access to the firm's operational store; preserve IAM-based auth and schema of `Dataset_CalibratedParameters` and `Dataset_DerivedValuations`.
- **USER-INTEGRATION REQUIRED** in `src/pricing_engine/infrastructure/adapters/event_publisher_adapter.py:EventPublisherAdapter.publish` — bind to the firm's message broker with mTLS; preserve payload schema of `Dataset_DerivedValuations` records.
- **ADAPTATION POINT** in `src/pricing_engine/domain/valuation.py:compute_closed_form_valuation` — replace the vanilla Black–Scholes body with the proprietary closed-form routine; preserve signature, output shape, and determinism.
- **ADAPTATION POINT** in `src/pricing_engine/domain/valuation.py:compute_simulation_valuation` — replace the GBM + vanilla-payoff body with the proprietary simulation; preserve signature, output shape, and `col_seed`-based determinism.
- **ADAPTATION POINT** in `src/pricing_engine/calibration.py:calibrate_parameters` — replace the generic least-squares body with the proprietary calibration routine; preserve signature and the invariant that `col_residual_norm` is a monotone-decreasing function of iterations.

# 5. Integration notes

- **Install**: `uv sync` (from the project root).
- **Run**: `uv run python -m pricing_engine.pipeline` (runs the end-to-end with the stub adapters and synthetic fixtures).
- **Test**: `uv run pytest` (covers schemas, each component in isolation, and an end-to-end smoke test over the stub adapters).
- The scaffold boots with self-contained stubs so it can run without network; every adapter has a clearly labelled replacement point.
- The calibration uses a textbook Levenberg–Marquardt; if the firm's calibration is convex only on a subdomain, the caller must restrict the initial guess — this is a known caveat, mirroring the spec's Section 8.
- Extend with new valuation branches by adding a function to `src/pricing_engine/domain/valuation.py` with the same signature shape, updating `pipeline.py` to dispatch to it, and adding a test in `tests/test_valuation.py`.

# 6. Reintegration map

| # | Marker | Location | What must be replaced | What private system / contract it binds to | What must remain true after binding |
|---|--------|----------|-----------------------|----------------------------------------------|-------------------------------------|
| 1 | USER-INTEGRATION REQUIRED | `market_data_adapter.py:MarketDataAdapter.fetch_observations` | stub fixture loader | firm's market-data vendor client | returned DataFrame matches `MarketObservation` schema; transient failures do not propagate |
| 2 | USER-INTEGRATION REQUIRED | `operational_store_adapter.py:OperationalStoreAdapter` | SQLite-based stub | firm's operational store | IAM-based auth; schemas of `Dataset_CalibratedParameters` and `Dataset_DerivedValuations` unchanged |
| 3 | USER-INTEGRATION REQUIRED | `event_publisher_adapter.py:EventPublisherAdapter.publish` | aio-pika stub | firm's message broker (mTLS) | payload schema of `Dataset_DerivedValuations` preserved |
| 4 | ADAPTATION POINT | `valuation.py:compute_closed_form_valuation` | vanilla Black–Scholes body | firm's proprietary closed-form routine | signature, output shape, determinism |
| 5 | ADAPTATION POINT | `valuation.py:compute_simulation_valuation` | GBM + vanilla payoff | firm's proprietary simulation | signature, output shape, `col_seed`-based determinism |
| 6 | ADAPTATION POINT | `calibration.py:calibrate_parameters` | generic least-squares | firm's proprietary calibration | signature, `col_residual_norm` monotonicity |
````

---

## Commentary on the example

Notice:

- Every module in the input dossier has a corresponding package / file in the output.
- Every component has a concrete generic implementation that actually runs (not a bare `NotImplementedError`).
- Every integration point has an adapter + interface + labelled seam.
- Every `ADAPTATION POINT` / `USER-INTEGRATION REQUIRED` appears in both Section 4 (enumeration) and Section 6 (Reintegration map).
- Assumptions in Section 1 surface every non-obvious choice (package manager, libraries, DB backend, broker).
- Numerical tuning (the `1e-3` regulariser) is mentioned in Assumptions and will be flagged by the validator if left without an adaptation point in the calibration code.
- No real names. Everything generic. A reader unfamiliar with the original project can still understand the pipeline end-to-end.

This is the shape every synthesized scaffold should take.
