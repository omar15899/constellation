---
name: newslab-daily-reports
description: Automated once-per-day OSINT market-intelligence study generated from the NewsLab (QuantOS Tier-2) GDELT pipeline and elevated by headless Claude Code (the automation’s configured model) into a scholar-style report inside OmarOS. Use when the user says "genera el informe diario de NewsLab", "run the daily news report", "actualiza los informes de mercado", "newslab daily", "informe OSINT diario", or wants to install / trigger / inspect the daily NewsLab report pipeline. Produces one master report per day at 11_Documents_and_Reports/Generated_Reports/NewsLab/. Observation/monitoring only — never a trade signal. CLI/launchd driven; the LLM never touches the network, only the deterministic context bundle.
---

# newslab-daily-reports

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

A launchd-scheduled, run-once pipeline that turns NewsLab's deterministic GDELT
observation into a daily scholar-style market-intelligence study in the vault.

## Architecture: decoupled drip (why two daemons)

GDELT DOC 2.1 enforces a **rolling-volume throttle**; a full daily run (~100
calls) trips it, and concurrency makes it worse. So retrieval is **decoupled**
from reporting by two launchd agents:

- **`com.omaros.newslab-importer`** (KeepAlive) — `scripts/importer.py` drips ONE
  (topic, query) per ~90s with exponential backoff on throttle, caching each raw
  response under `NewsLab/outputs/cache/<UTC-day>/`. Stays under the cap by low
  sustained rate. The cache files are the state (crash-resilient, resumable).
- **`com.omaros.newslab-daily-reports`** (07:00 daily) — `scripts/sync.py` builds
  the report from that cache with **zero network I/O**, then elevates + commits.

## Two surfaces

- **Deterministic substrate (NewsLab).** `scripts/cache_pipeline.py` replays the
  cached corpus through the exact live code path (`ReplayTransport` → `run_topic`),
  building content-addressed `FeatureSet`s + `DailySignal`s, z-score alerts, and a
  governed markdown report under `NewsLab/outputs/`.
- **Elevated study (OmarOS).** Headless Claude (the automation’s configured model) rewrites the
  deterministic context bundle into a thorough scholar-style report at
  `11_Documents_and_Reports/Generated_Reports/NewsLab/<YYYY-MM-DD>_global_news_intelligence.md`.

## Pipeline (one report run = `scripts/sync.py`)

1. **Retrieve + features** — default `NLDR_SOURCE=cache` builds from the importer's
   drip cache (no burst). `NLDR_SOURCE=live` bursts GDELT directly (throttle-prone);
   `NLDR_REPLAY=<fixture>` forces an offline fixture build (tests). Writes the
   report + per-topic history.
2. **Context assembly** — `assemble_context.py` wires the `RuleBasedRegimeDetector`
   (the daily pipeline does not), reproduces the mandatory caveats, and emits the
   deterministic hand-off bundle that is the LLM's *sole* input. **Empty-data
   guard:** zero articles ⇒ abort, no report, no commit.
3. **Safety gates** — `check_execution_safety.py` (research mode, execution off).
   Non-contamination (I-8) is N/A while the tagger is the training-free
   deterministic ontology matcher and the LLM tagger is off.
4. **LLM elevation** — `claude -p --model claude-sonnet-4-6 --permission-mode
   acceptEdits` with `OMAROS_AUTO_COMMIT=0`/`OMAROS_AUTO_PUSH=0` and no git tools
   (so the vault Stop-hook never bundles/races), writing the study into the vault.
5. **Post-write gate** — `safety_lint.py` (caveats reproduced verbatim, no
   buy/sell/price-target/forecast language) + strict frontmatter validation. Any
   violation ⇒ discard the LLM output, keep the deterministic report, abort.
6. **Commit** — one scoped commit of exactly the report, push to `origin` (when
   `NLDR_PUSH=1`), plus an explicit `docs/investigation_logs/` entry (the launchd
   commit fires no Claude hooks, so traceability is honoured here).

## Idempotency

Per `as_of` date via `02_Tasks_and_Execution/Ledger/.sync_state/newslab_daily_reports.json`.
A second fire the same day is a no-op (override with `NLDR_FORCE=1`).

## Configuration (env)

| Var | Default | Meaning |
|---|---|---|
| `NLDR_SOURCE` | `cache` | `cache` (drip corpus) \| `live` (burst) — report build source |
| `NLDR_TOPICS` | all 7 | comma-separated topic names (importer + report) |
| `NLDR_LLM` | `1` | `1` = scholar elevation; `0` = publish deterministic report only |
| `NLDR_PUSH` | `1` | push the commit to origin |
| `NLDR_COMMIT` | `1` | `0` = dry run (write report, no commit, don't claim the day) |
| `NLDR_REPLAY` | _(unset)_ | path to a GDELT artlist fixture → offline/test build |
| `NLDR_TIMESPAN` / `NLDR_MAX` | `1d` / `75` | GDELT window / max articles per query |
| `NLDR_BASE_INTERVAL` | `90` | importer: seconds between successful drips |
| `NLDR_MAX_BACKOFF` | `1800` | importer: cap on throttle backoff |
| `NLDR_FORCE` | `0` | re-run the report even if already ran today |

## Install / trigger / uninstall

```bash
bash /Users/omarkhalil/GitHub/Constellation/skills/omaros/newslab-daily-reports/scripts/install_launchd.sh   # both agents
launchctl list | grep newslab                                          # status must be 0, not 2
launchctl kickstart -k gui/$(id -u)/com.omaros.newslab-daily-reports   # run a report now
```

Manual report run (offline, no push, deterministic-only):

```bash
NLDR_REPLAY=/Users/omarkhalil/GitHub/NewsLab/packages/quant_news/tests/fixtures/gdelt_artlist_sample.json \
NLDR_PUSH=0 NLDR_LLM=0 NLDR_COMMIT=0 \
/Users/omarkhalil/.venvs/omaros/bin/python /Users/omarkhalil/GitHub/Constellation/skills/omaros/newslab-daily-reports/scripts/sync.py
```

## Tests

```bash
/Users/omarkhalil/GitHub/NewsLab/.venv/bin/python -m pytest \
  /Users/omarkhalil/GitHub/Constellation/skills/omaros/newslab-daily-reports/tests/ -q
```

## Out of scope

- Live trading, signals, pricing, VaR, backtesting — all are sibling QuantOS
  labs, import-linter-blocked in NewsLab and never consulted here.
- Multi-source ingestion (SEC, Reuters, Bloomberg, Twitter) — stubbed in NewsLab;
  this skill uses GDELT only until those adapters exist.
- The cloud `/schedule` path — it cannot reach the local NewsLab repo or vault.
