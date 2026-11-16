# Isomorph Synth — Stack Selection (heuristics)

The agnostic spec often under-specifies the runtime. This file is the decision tree for picking a stack when the spec is silent, and the justification menu for each choice. Whatever is chosen goes into Section 1 (Assumptions) of the output with a one-line reason.

The guiding principle: pick the stack that maximises **reintegration ease**. If the user's private system is in language X, the closer the scaffold is to language X the better. When the spec doesn't hint at the private language, default to the **most commonly reintegrable** option for the inferred system kind.

---

## Primary inference table

Look up the **system type** declared in the spec (Section 1 of a project-isomorph dossier, field "System type"). If present, use the first matching row below. If not present, use the secondary heuristics further down.

| Spec signal (system type) | Default stack | Justification |
|---------------------------|---------------|---------------|
| `data pipeline` / `batch ETL` / `ingestion pipeline` | Python 3.11+, `uv`, `pytest`, `pandas` or `polars` | Ubiquitous in data engineering; easy to rebind to `pyspark` / `dask` / Airflow at reintegration if needed. |
| `pricing engine` / `numerical solver` / `risk engine` | Python 3.11+, `uv`, `numpy`, `scipy`, `pytest` | Quant and numerical finance overwhelmingly use Python. A Julia / C++ / Rust alternative is possible but less universally bindable; state that tradeoff in Assumptions. |
| `ML training pipeline` | Python 3.11+, `uv`, `numpy`, `torch`, `pytest` | Torch is the default ML framework; a generic scaffold reintegrates to either framework easily. |
| `ML inference service` | Python + FastAPI + `torch`, `pytest` | Pairs naturally with a data-pipeline upstream; FastAPI's type-first style is close to typed internal RPC frameworks. |
| `UI system` / `web dashboard` / `internal tool UI` | TypeScript + React + Vite, `vitest` | React is the most reintegrable front-end stack for internal tooling. |
| `async API client` / `streaming consumer` | Python + `httpx` + `asyncio`, or Python + `aio-pika` / `confluent-kafka` for brokers | Spec's "async" signal is the tell; Python async is idiomatic. |
| `event-driven service` / `message broker consumer` | Python + a broker client (`aio-pika`, `confluent-kafka`) + structured logging | Same as async above; Python's ecosystem covers most brokers. |
| `batch reporting system` | Python 3.11+, `uv`, `pandas`, `jinja2`, `pytest` | Reports are often rendered from templates; jinja is a safe default generator. |
| `static-site generator` | Python (`mkdocs`) or TypeScript (`astro`) — choose by what the spec's execution flow looks like | If the spec talks about markdown → HTML, prefer the Python path; if it talks about components + hydration, prefer the TS path. |
| `workflow orchestrator` | Python + `prefect` / `dagster` / plain function composition | Spec usually implies one of these; use `prefect` as the safer default if not stated. |
| `research notebook cluster` | Python 3.11+, `uv`, `jupytext`, `pytest`; build pipeline for LaTeX when present (`latexmk`) | Research code is the most variable; keep the scaffold minimal so the user can restructure. |
| `monitoring / observability layer` | Python + `prometheus_client` + structured JSON logs | Broker-agnostic; most observability stacks ingest either. |
| `CQRS / actor model service` | Python + explicit actor harness, or TypeScript if the spec implies a Node backend | Flag as a non-trivial stack choice; state it explicitly. |

---

## Secondary heuristics (when system type is not explicit)

When Section 1 doesn't name a system type, infer from these signals:

- **Spec mentions DataFrames, schemas, tabular data, SQL** → Python data stack.
- **Spec mentions JSX / React components / routes / hooks / state management** → TypeScript + React.
- **Spec mentions WebSocket / server-sent events / pub-sub / Kafka / AMQP** → async Python or async TypeScript (Fastify); pick by the rest of the spec's shape.
- **Spec mentions LaTeX or figures or chapters** → Python (figures + LaTeX build). The scaffold is *not* the LaTeX content itself.
- **Spec mentions microservices / gRPC / protobuf** → the language the spec emphasises most, defaulting to Python + `grpcio` when ambiguous.
- **Spec mentions mobile / iOS / Android / Swift / Kotlin** → the native language; flag as a significant stack decision. Most OmarOS-relevant scaffolds won't be here.
- **Spec mentions CUDA / GPU / Triton / CUDA kernels** → Python + `torch` (or `cupy` if purely array compute). Don't scaffold CUDA directly; let the private version decide.
- **Spec mentions PDE / finite-elements / spectral methods on meshes** → Python + `numpy` + `scipy` is the universal default; mention that FEniCS / FreeFEM / Julia are faster at production scale.

---

## When the spec pins the runtime

If the spec's component specs carry an explicit `Runtime_*` tag:

| Spec tag | Stack choice |
|----------|--------------|
| `Runtime_InterpretedDynamic` | Python (default) unless the rest of the spec suggests Node. |
| `Runtime_CompiledStatic` | Go, Rust, or C++; pick the most reintegrable given the spec's shape. Go is the safest default for services, Rust for systems-heavy code. |
| `Runtime_Managed` | C# (.NET), Java, or Kotlin; pick based on remaining signals. |
| `Runtime_Browser` | TypeScript + React + Vite. |
| `Runtime_Container` | Docker + whatever language the container hosts, inferred from the rest of the spec. |

Always state the chosen concrete language in Section 1 of the output.

---

## Build / package manager choices

For each primary language, the default toolchain:

| Language | Package manager | Test runner | Linter | Formatter |
|----------|-----------------|-------------|--------|-----------|
| Python 3.11+ | `uv` (preferred), `poetry` (fallback) | `pytest` | `ruff` | `ruff format` |
| TypeScript | `pnpm` (preferred), `npm` (fallback) | `vitest` | `eslint` | `prettier` |
| Go | `go mod` | `go test` | `golangci-lint` | `gofmt` |
| Rust | `cargo` | `cargo test` | `cargo clippy` | `cargo fmt` |
| C#/.NET | `dotnet` | `dotnet test` | `roslyn analyzers` | `dotnet format` |
| Java | `gradle` or `maven` (preferred gradle) | `junit5` | `spotbugs` | `spotless` |

State the chosen build tool in Section 1.

---

## When to mix stacks

Only when the spec explicitly describes a multi-runtime system:

- **Backend + UI**: Python (or Node) backend + TypeScript/React UI. Output is two subdirectories, each with its own package manifest and tests, and an `.env.example` at the root.
- **Compute kernel + orchestrator**: a low-level kernel in Rust/C++/Julia + a Python orchestrator. Keep the interface between them explicit (Python calls via `ctypes` / `pyo3` bindings / subprocess with a typed CLI).
- **Notebook cluster + LaTeX build**: a Python scripts directory + a LaTeX build pipeline. Flag both in Section 1.

If the spec does not describe a split, do not introduce one. A monolingual scaffold is easier to rebind.

---

## When the scaffold is trivially small

A scaffold of one or two files does not need the full layered architecture (`domain/`, `infrastructure/`, `adapters/`, …). A sensible minimum for tiny scaffolds:

```
<slug>/
├── pyproject.toml      (or package.json / etc.)
├── src/
│   └── main.py         (single module; name it after the role)
└── tests/
    └── test_main.py
```

Do not inflate a tiny project to fit an enterprise layout — the user will have to un-inflate it at bind time. Scale the architecture to the spec's declared size.

---

## Stating the assumption

Every stack decision lands in Section 1 (Assumptions) as a single bullet:

```markdown
- **Stack / runtime**: Python 3.11+, using `uv` as the package manager and `pytest` for tests. Justification: spec describes a batch data pipeline with numerical calibration — the Python data / numerical stack is the most commonly reintegrable choice for this system type.
```

The user can override ("actually, build this in Go") by replying with a directive; the scaffold is regenerated from the new assumption.
