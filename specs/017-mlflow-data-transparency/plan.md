# Implementation Plan: Transparency over training data, benchmarks and training runs (MLflow)

**Branch**: `claude/mlflow-data-transparency` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-mlflow-data-transparency/spec.md`

## Summary

The owner gets one place to see what data the zoo has and one place to watch training.

1. **Overview first (P1, no server needed).** `zoo data stats` lists every dataset, source collection, training set and benchmark version with size, counts, distributions, licence, permitted use, freeze date, hash, last change, lineage and users. `zoo data history` and `zoo data diff` show how versions came about and what changed. All of it is computed from what already exists (registers, `SOURCE.json`, frozen manifests, freeze files, release records, git). Integrity checks catch a frozen benchmark that changed. Nothing new is added to the registers.
2. **MLflow on the DGX Spark (P2).** A pinned `ghcr.io/mlflow/mlflow:v3.17.1` container with SQLite and local artifacts, published on the Spark's loopback only and reached from the laptop by SSH tunnel. It has scripted up, backup, restore and upgrade. `zoo data publish` mirrors the overview into a `datasets` experiment, idempotently.
3. **Run logging (P2).** A thin wrapper, `mobility_model_zoo.tracking`, is the only place that imports MLflow. It is a no-op without `MLFLOW_TRACKING_URI`. It logs synchronously with short timeouts and a circuit breaker, so it never breaks a run. A guard admits only allow-listed numbers, hashes and metadata. Every task's train, tune, evaluate and measure command logs its config, commit, hardware, per-step metrics and the exact data and benchmark versions it used. Past results are imported once as `imported` runs. Release records may name their run.

Decisions with evidence and rejected alternatives: [research.md](research.md). Entities: [data-model.md](data-model.md). Interfaces: [contracts/](contracts/). Validation walk-through: [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.12 (project standard, `uv`); Bash for the Spark scripts.

**Primary Dependencies**:
- **existing packages** `mobility_model_zoo.datasets`, `release`, `compliance`, `productdev.jtbd`, `security.can_ids`, `condition_monitoring`, `edge`, using PyYAML, jsonschema and Typer (all present);
- **new optional extra `tracking`**: `mlflow-skinny>=3.17.1,<4`, `numpy`, `python-dotenv`, `psutil`, `nvidia-ml-py` (research R1, R7);
- **server, container only, never in the package**: `ghcr.io/mlflow/mlflow:v3.17.1`, multi-arch including linux/arm64 (R2).

**Storage**:
- **Tracking store on the Spark**: SQLite `~/mlflow/mlflow.db` plus `~/mlflow/artifacts` (R3).
- **Backups**: `~/mlflow-backups/<date>/` on the Spark, copied to the laptop.
- **Run sidecars**: `tracking.json` next to each run's outputs.
- **Repository**: nothing new beyond code, docs, scripts, one optional release-record field and one compliance decision.

**Testing**:
- **pytest unit tests**: collectors on fixture manifests and registers, history on a temporary git repo, diff, guard, the no-op path, circuit breaker and sidecar with a fake transport, import key idempotency, release schema.
- **CLI tests**: `CliRunner`.
- **One `slow` integration test**: a real `mlflow server` on a temporary SQLite store via `uvx mlflow==3.17.1`.
- **Spark checks**: from [quickstart.md](quickstart.md) §3 and §5.

**Target Platform**:
- **CLI**: Linux and macOS laptops, the DGX Spark (aarch64, NGC PyTorch container), the HIL runner, GitHub CI (logging off).
- **Server**: the DGX Spark, Docker.

**Project Type**: CLI and library (single project), plus deployment scripts for one self-hosted service.

**Performance Goals**:
- **Overview**: `zoo data stats` under 10 s without `--verify` on the current registry (17 datasets, 6 benchmarks), so the one-minute answer of SC-001 has headroom.
- **Logging overhead**: under 2 % of run time (SC-006).
- **Live view**: metrics visible within one minute (SC-004).
- **Restore**: under 30 minutes (SC-009).

**Constraints**:
- no dataset content, labels or personal data in the store (FR-024);
- no tracking dependency in the base install or the `edge` size limit (FR-011, SC-008);
- the repository stays the source of truth: no gate reads the store (FR-025);
- no cloud and no cash cost (SC-010);
- loopback-only server behind SSH (FR-009);
- no Claude, assistant or LLM on the server (FR-026).

**Scale/Scope**:
- **Data**: about 25 inventory rows today.
- **Integrations**: 6 task integrations (span, cluster, can-ids, sound-anomaly, activity, HIL).
- **Imports**: about 10 imported runs.
- **Commands**: 7 new (`zoo data stats|history|diff|publish`, `zoo tracking status|import|audit`).
- **Packaging**: 1 new package (`tracking`), 1 new module group (`datasets/inventory/`), 1 new extra, 1 schema field, 1 Spark script set, 1 docs page.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Principles I, II, VII and X concern JTBD extraction behaviour and are not touched. The feature changes no model, benchmark content, training recipe or published card.

| Principle or section | Touched | How the plan complies |
|---|---|---|
| III Measure before optimizing | yes | Every evaluation run carries `mmz.benchmark`, and its dataset input points at the frozen benchmark version, so a result without a frozen benchmark is visible as such. Gate decisions still read the repository's results files, not the store. Benchmark labelers are not logged as runs, and none is Claude. |
| IV Riskiest assumption first | yes | Riskiest assumption: logging into a remote server never harms a long training run. Tested first on the Spark (quickstart §5: server stopped mid-run, overhead under 2 %) before integrating more tasks. Kill criterion: if the circuit breaker cannot keep a run unharmed, run logging falls back to sidecar-only and the overview ships alone. |
| V Small and local | yes | Server and clients run locally; the server is on the Spark. The client extra is about 69 MB and optional. No hosted service. |
| VI Clean provenance | yes | The overview shows licence, permitted use and redistribution for every row. Benchmarks inherit the strictest permitted use of their datasets. The store holds only aggregates, hashes and metadata, so no restricted data is copied anywhere. The guard and audit enforce this (R8). |
| VIII Fair comparison | yes | Runs carry their benchmark version as tag and dataset input. The comparison view (US6) filters by it, so runs on different versions are not silently mixed. |
| IX Reproducible, dated releases | yes | The release records stay authoritative. The optional `tracking.run_id` only adds a pointer (R14). Integrity checks detect a changed frozen benchmark, and none existed before for `based_on` hashes (R12). Runs record commit and clean-tree state. |
| XI No Claude in model learning or extraction | yes | No logged task uses Claude. No MLflow assistant, gateway or LLM judge is configured or called (R10). The audit flags any value naming Claude as labeler, teacher or judge. No deviation is possible or sought. |
| Resources & Cost Discipline | yes | Local compute only (Spark, laptop). No cash budget needed. Cost order respected. |
| Technical Spikes | yes | Spike runs log to the `spikes` experiment with `mmz.spike=true` and are never imported or presented as benchmark results. |
| Development Workflow & Quality Gates | yes | This plan lists touched principles. New code is covered by unit tests and CI with logging off. The gate before a labeling, data generation or evaluation run is unchanged. The compliance register gains decision `D-tracking-store`, and the record of processing is re-rendered (R16). |

**Gate result before research**: pass. **After design**: pass. No deviation to justify.

## Project Structure

### Documentation (this feature)

```text
specs/017-mlflow-data-transparency/
├── plan.md              # This file
├── spec.md
├── research.md          # R1–R16
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md           # zoo data stats|history|diff|publish, zoo tracking status|import|audit, Spark scripts
│   ├── tracking.md      # wrapper interface, experiments, tag/param/metric/artifact allow-lists
│   └── release/         # schemas; release-record adds optional `tracking` (latest owner of the format)
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/mobility_model_zoo/
├── datasets/
│   ├── cli.py                     # + stats, history, diff, publish
│   └── inventory/                 # NEW: overview, no MLflow import
│       ├── __init__.py            # collect(root, data_root) -> list[InventoryRow]
│       ├── rows.py                # InventoryRow, HistoryEvent, VersionDiff dataclasses
│       ├── hashes.py              # dataset, manifest, source collection and training set hashes
│       ├── third_party.py         # registry + SOURCE.json + measured size
│       ├── sources.py             # productdev sources.yaml collection
│       ├── benchmarks.py          # readers: jtbd pilot, jtbd cluster, can-ids
│       ├── training_sets.py       # span frozen.json + rows.stats.json
│       ├── used_by.py             # register used_by, release records, span config
│       ├── history.py             # git history per record / manifest (cached)
│       ├── integrity.py           # based_on hashes, changed-after-freeze, --verify hooks
│       ├── diff.py
│       └── render.py              # table and JSON output
├── tracking/                      # NEW: the only module importing mlflow
│   ├── __init__.py                # run(), data_ref(), EXPERIMENTS, STRICT
│   ├── config.py                  # MLFLOW_* from env or .env (dotenv_values), no-op detection
│   ├── guard.py                   # allow-lists (contracts/tracking.md)
│   ├── client.py                  # synchronous client, short retries, circuit breaker, sidecar
│   ├── keras.py                   # Keras callback for fit_kwargs
│   ├── publish.py                 # zoo data publish (inventory -> datasets experiment)
│   ├── importer.py                # zoo tracking import
│   ├── audit.py                   # zoo tracking audit (reuses compliance publication scan)
│   └── cli.py                     # zoo tracking status|import|audit
├── release/
│   ├── cli.py                     # mount `tracking` group; release-verify prints tracking.run_id
│   └── schemas/release-record.schema.json   # + optional tracking (from contracts/release)
├── productdev/jtbd/span/train.py  # log per-epoch history; sidecar
├── productdev/jtbd/span/tune.py   # thresholds, tuning metrics
├── productdev/jtbd/{scoring.py, perf.py}, span/results.py   # evaluation runs
├── productdev/jtbd/cluster/{tune.py, score.py}
├── security/can_ids/{evaluate.py, evaluate_v2.py, measure.py, forest.py, release_export_v2.py}
├── edge/int8/keras_export.py      # callback via fit_kwargs, report metrics
└── edge/bench/results.py          # log summarize() at write_summary

scripts/spark/mlflow/
├── mlflow.sh                      # up|down|status|logs|backup|restore|upgrade|pull-backup|tunnel
└── README.md
topics/productdev/scripts/spark/train_span.sh   # mmz-tracking network, -e MLFLOW_TRACKING_URI from MLFLOW_TRACKING_URI_CONTAINER, [jtbd,tracking]

compliance/decisions.yaml          # + D-tracking-store
src/mobility_model_zoo/compliance/templates/record-of-processing.md.j2   # + store paragraph
docs/compliance/record-of-processing.md   # re-rendered
docs/tracking.md                   # owner guide: tunnel, commands, backup, upgrade, security notes
docs/credentials.md, .env.example  # MLFLOW_TRACKING_URI, SPARK_HOST
README.md                          # short "Data and runs overview" section

tests/
├── datasets/test_inventory_*.py   # collectors, used_by, render, CLI
├── datasets/test_history_diff.py  # temp git repo fixture
├── datasets/test_integrity.py
├── tracking/test_config_noop.py, test_guard.py, test_client_breaker.py, test_publish.py,
│   test_importer.py, test_audit.py, test_keras_callback.py
├── release/test_schemas.py        # CONTRACTS -> specs/017-.../contracts/release
├── unit/test_dependency_layout.py # tracking in TRAINING_EXTRAS; base unchanged
└── integration/test_tracking_server.py   # slow: real server round trip
scripts/ci/select_tests.py         # rules for datasets/inventory, tracking, scripts/spark/mlflow
.github/workflows/ci.yml           # test job: --extra tracking
```

**Structure Decision**:
- **Single project**, following the existing layout.
- **Overview in `datasets/inventory/`**: it belongs to `zoo data` and must run with the `release` extra only.
- **Tracking in its own package**: the import boundary keeps MLflow out of every other module, and lets the no-op path be tested without the extra.
- **Spark scripts in `scripts/spark/`**: they serve every topic. `train_span.sh` stays in its topic folder.

## Delivery order

1. **Overview** (US1, US2): inventory, history, diff, integrity, CLI. This ships on its own and needs no server.
2. **Server and publish** (US3): Spark scripts, docs, `tracking` config, guard, client, `zoo tracking status`, `zoo data publish`.
3. **Riskiest assumption check** (Principle IV): span training with logging, server stopped mid-run, overhead measured. Go or no-go for step 4.
4. **Run logging** (US4, US5): span, cluster, can-ids, Keras tasks, HIL. Release-record field. Then import and audit.
5. **Compare** (US6): no code beyond consistent tags and inputs. Validated in the browser.

## Complexity Tracking

No constitution violation. Two choices that add moving parts, recorded for review:

| Choice | Why needed | Simpler alternative rejected because |
|---|---|---|
| Synchronous logging with circuit breaker instead of MLflow async logging | FR-020 requires a visible warning when tracking is incomplete | Async logging drops failed batches silently (R5). |
| Allow-list guard plus a store audit | FR-024 and SC-007 must be testable | Relying on call-site discipline cannot be checked once data is in the store (R8). |
