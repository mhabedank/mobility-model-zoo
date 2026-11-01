# Research: Transparency over training data, benchmarks and training runs (MLflow)

**Feature**: 017 | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Facts about MLflow were checked on 2026-10-15 against PyPI, the ghcr.io registry, the v3.17.1 source tag and OSV, and by running mlflow 3.17.1 (SQLite server on 127.0.0.1, mlflow-skinny client) on Python 3.12. Facts about the repository come from the current `main` (`8aebe7e`). Items marked **verify** were not tested on the target machine and become explicit checks in the tasks. **Revision 2026-10-16**: R2, R3, R4, R7, R10 and R16 changed and R17 is new (spec decision 2).

## R1. MLflow version and client package

- **Decision**: Server `mlflow==3.17.1` through `uvx` on the laptop (R2; the pinned container image `ghcr.io/mlflow/mlflow:v3.17.1` was the choice while the server was planned for the Spark). Client: a new optional extra `tracking` with `mlflow-skinny>=3.17.1,<4`, `numpy`, `python-dotenv`, `psutil`, `nvidia-ml-py`.
- **Rationale**: 3.17.1 (PyPI 2026-10-13) is the latest stable release and closes about a dozen advisories fixed in 3.17.0 (see R10). `mlflow-skinny` is about 69 MB installed against about 610 MB for full `mlflow`. It has no server, no UI and no SQL store, but it logs params, metrics, tags, artifacts (proxied upload) and dataset inputs to a remote server; all of these were tested. `mlflow.data.meta_dataset` needs numpy, so numpy is listed explicitly. `psutil` (manylinux aarch64 wheels exist since 7.x) and `nvidia-ml-py` enable system metrics (R7).
- **Alternatives considered**: full `mlflow` as the client (rejected: ten times larger, pulls pandas, scipy, scikit-learn, pyarrow and Flask into every training environment); `mlflow-tracing` (GenAI tracing only); W&B or other hosted trackers (rejected by the owner: cloud, cost, data leaves the house; constitution cost order).

## R2. Where the server runs and how it is reached (revised 2026-10-16)

- **Decision**:
  - The server runs on the owner's laptop, started on demand by `scripts/mlflow/mlflow.sh up` as a background process: `uvx --from mlflow==3.17.1 mlflow server --host 127.0.0.1 --port 5000 --backend-store-uri sqlite:///$MMZ_TRACKING_HOME/mlflow.db --artifacts-destination $MMZ_TRACKING_HOME/artifacts`. `MMZ_TRACKING_HOME` defaults to `~/.local/share/mobility-model-zoo/mlflow`.
  - It listens on the laptop's loopback interface only. The laptop's `.env` holds `MLFLOW_TRACKING_URI=http://127.0.0.1:5000`. There is no tunnel and no Docker.
  - **Training on the Spark** does not talk to the server at all. Its containers run in offline mode (`MMZ_TRACKING_OFFLINE=1`) and write an offline run log next to the run's sidecar (R17). `scripts/spark/tracking-pull.sh` fetches only these logs over SSH, and `zoo tracking sync` puts them into the store.
  - **Host check**: the server's default allowed hosts (localhost and loopback) suffice; no extra host name is configured.
- **Rationale**:
  - Offline logs need nothing on the Spark beyond the training run itself, which already runs there: no service, no Docker network, no port.
  - `uvx` with a pinned version is already how the slow integration test starts a real server; it needs no Docker on the laptop and keeps full `mlflow` out of the project environment (R15).
  - Long trainings still never depend on the laptop being awake: the offline log is written on the Spark and fetched whenever the laptop is on.
- **Alternatives considered**:
  - **Server on the Spark behind an SSH tunnel**: the original design, replaced on 2026-10-16 (spec decision 2).
  - **Reverse tunnel from the laptop into Spark containers** (`ssh -R`): runs would stall or degrade whenever the laptop sleeps.
  - **MLflow's file store as the offline format**: deprecated since 3.6, the server refuses it since 3.13, and the client needs `MLFLOW_ALLOW_FILE_STORE`; it would also need MLflow inside every training container. Rejected for an own, versioned log format (R17).
  - **Basic auth**: not needed for a loopback-only, single-user server.

## R3. Backend store, artifacts and backup (revised 2026-10-16)

- **Decision**:
  - **Store**: SQLite at `$MMZ_TRACKING_HOME/mlflow.db` on the laptop, with artifacts in `$MMZ_TRACKING_HOME/artifacts` served through the server (`--artifacts-destination`).
  - **Automatic backup**: `mlflow.sh down` and `mlflow.sh upgrade` first run `mlflow.sh backup`. It makes an online SQLite backup with Python's `sqlite3` backup API and a tar of the artifact directory, written to `$MMZ_TRACKING_BACKUP/<date-time>/` (default `~/mlflow-backups`, which the owner may point at an external drive). It keeps the newest 14.
  - **Second copy of Spark runs**: the offline logs stay in the run folders on the Spark and in the fetched copy on the laptop; a lost store can be rebuilt from them with `zoo tracking sync`.
  - **Restore**: `mlflow.sh restore <dir>` stops the server, replaces the store and starts again. It is tested once (SC-009).
  - **Upgrades**: `mlflow.sh upgrade <version>` takes a backup, stops the server, runs `mlflow db upgrade` with the new version and starts it.
- **Rationale**:
  - SQLite has been the default backend since 3.7. The file store is deprecated (3.6) and refuses to start since 3.13.
  - A laptop is not always on, so a nightly schedule would miss days; backing up whenever the server stops covers every session in which the store changed. The MLflow docs say to back up before `mlflow db upgrade`.
- **Alternatives considered**:
  - **PostgreSQL**: a second service to run, for no gain at single-user scale.
  - **A launchd schedule**: possible later; it adds nothing while the store changes only while the server runs.
  - **mlflow-export-import**: kept as a fallback for a move to another machine, not used for backup.

## R4. Configuration: environment only (revised 2026-10-16)

- **Decision**:
  - **Live mode**: the tracking layer reads `MLFLOW_TRACKING_URI` from the process environment. If it is unset, it reads only the `MLFLOW_*` and `MMZ_TRACKING_*` keys from a `.env` file in the working directory or at the repository root, using `dotenv_values` with no side effects.
  - **Offline mode**: `MMZ_TRACKING_OFFLINE=1` without a tracking URI. The Spark scripts set it with `-e` on their training containers (the container installs the package non-editably, so `.env` is not found there). A URI wins over offline mode.
  - When neither is set, the layer is a no-op that returns immediately. The `mlflow` import happens only in live mode; offline mode imports no tracking software.
  - `.env.example` gets `MLFLOW_TRACKING_URI`, `MMZ_TRACKING_HOME`, `MMZ_TRACKING_BACKUP` and the missing `SPARK_HOST`; `docs/credentials.md` lists them under "Other local settings". `MLFLOW_TRACKING_URI_CONTAINER` is removed.
- **Rationale**:
  - `jtbd` already loads `.env`, but `zoo`, `zoo-security` and `condmon` do not (python-dotenv is only in the `jtbd` and `catalog` extras). Reading only the tracking keys keeps the other commands' behaviour unchanged (FR-010, FR-011).
  - One switch for the Spark scripts keeps any address out of the repository and out of the containers.
- **Alternatives considered**:
  - **Calling `load_dotenv()` globally in every CLI**: it changes behaviour for every other variable. Rejected.
  - **A config file in `configs/`**: forbidden by FR-010.

## R5. Run logging without breaking runs

- **Decision**:
  - One thin wrapper, `mobility_model_zoo.tracking`, is the only place that imports MLflow.
  - Calls are synchronous with short limits, set by the wrapper only if the user has not set them: `MLFLOW_HTTP_REQUEST_MAX_RETRIES=2`, `MLFLOW_HTTP_REQUEST_TIMEOUT=10`.
  - **Circuit breaker**: on the first failure the wrapper marks the run "degraded", stops calling the server and prints one warning. At the end it writes a sidecar `tracking.json` next to the run's own outputs, holding run id, experiment and `complete: false`.
  - Metrics are sent once per epoch, evaluation step or measurement batch, in a single `log_batch` call.
- **Rationale**:
  - The defaults retry 7 times with backoff (about 4 minutes) and then raise. That would stall or break a training run.
  - Async logging (`MLFLOW_ENABLE_ASYNC_LOGGING`) loses failed batches silently; `flush` did not raise in testing. That violates FR-020's "warn that tracking was incomplete".
  - Epochs take minutes, so one synchronous batch per epoch adds negligible time (SC-006 is measured, not assumed).
- **Alternatives considered**:
  - **Async logging**: silent loss.
  - **A local spool with later replay**: originally deferred. Since 2026-10-16 it exists as offline mode for machines without the server (R17); a live run that loses the laptop's server still degrades as described here rather than switching to offline mid-run, because one run would then live in two places.

## R6. No autologging; explicit, allow-listed logging

- **Decision**:
  - No `autolog()` anywhere. Each task logs explicitly through the wrapper.
  - **jtbd span**: the per-epoch `history` entry in `span/train.py`.
  - **Keras tasks**: a small callback passed through `fit_kwargs` in `edge/int8/keras_export.py`.
  - **can-ids**: the result dicts of `evaluate.run` and `evaluate_v2`.
  - **HIL bench**: `summarize()` output at the end of `write_summary`.
- **Rationale**:
  - The span model has a custom PyTorch loop, which has no autologger (`mlflow.pytorch.autolog` covers Lightning only).
  - sklearn and Keras autolog do not log input examples by default, but they do log models and checkpoints by default. Models must never go to the store (FR-023).
  - Explicit logging keeps the privacy guard (R8) in one place.
- **Alternatives considered**: autolog with `log_models=False, log_datasets=False, checkpoint=False`. Rejected: implicit behaviour that can change between MLflow versions, and it does not cover the main task.

## R7. System metrics (revised 2026-10-16)

- **Decision**:
  - **Live mode** (laptop): training runs enable MLflow system metrics when `psutil` is importable.
  - **Offline mode** (Spark): a small sampler thread in the tracking layer records, every 10 s, CPU and memory through `psutil` when importable, and GPU utilisation and power through `nvidia-smi --query-gpu=utilization.gpu,power.draw --format=csv,noheader,nounits` when that command exists. It writes them as metrics under MLflow's own names (`system/cpu_utilization_percentage`, `system/system_memory_usage_megabytes`, `system/gpu_0_utilization_percentage`, `system/gpu_0_power_watts`), so synced and live runs chart alike.
  - `MMZ_TRACKING_SYSTEM_METRICS=0` switches both off.
  - **verify** on the Spark: `nvidia-smi` in the NGC container reports utilisation and power on GB10 (memory queries are "Not Supported" there, a known NVIDIA issue, and are not sampled).
- **Rationale**: answers "is the GPU busy, is the run stuck" without a shell on the Spark (US4). MLflow's own monitor needs MLflow in the container, which offline mode avoids.
- **Alternatives considered**: installing the `tracking` extra in the container only for system metrics (rejected: 70 MB more per container for four numbers).

## R8. Privacy guard (FR-024, SC-007)

- **Decision**: `tracking/guard.py` checks every value before it leaves the process.
  - **Keys** match `^[a-z0-9_./-]{1,120}$`.
  - **Tags** come only from the `mmz.*` allow-list in [contracts/tracking.md](contracts/tracking.md).
  - **Param values** are numbers, booleans or strings of at most 120 characters, with no line break and at most three spaces, so no prose.
  - **Artifacts** come only from an allow-list of file kinds the zoo writes itself: the inventory profile JSON, a copy of the committed config file, `span_config.json` without paths into `data/`, the HIL `summary.json` and `summary.md`. Each is at most 1 MB.
  - A refused value raises in tests and is dropped with a warning at run time.
  - **Audit**: `zoo tracking audit` downloads every param, tag and text artifact from the store and runs the same detectors as the release publication scan over them:
    - `compliance.scan.pii(text, allow)` for personal identifiers, with the controller's contact allow-list from `compliance.release_checks.contact_allowlist`;
    - `compliance.scan.overlap_spans` against a `CorpusIndex` of the snapshot corpus, when the corpus is on the machine, to catch verbatim source text.
- **Rationale**: the spec forbids text, labels, payloads and personal data in the store. An allow-list is testable; a deny-list for "looks like text" is not.
- **Alternatives considered**: trusting call sites. Rejected, because the store lives longer than any code review.

## R9. Datasets in MLflow, idempotent publishing

- **Decision**:
  - **Experiment**: `datasets`. One run per data version, with run name `<id>@<version>`.
  - **What a run carries**: tags `mmz.kind`, `mmz.id`, `mmz.version`, `mmz.topic`, `mmz.sha256`, `mmz.frozen_at`, `mmz.permitted_use`, `mmz.licence`; metrics for sizes, counts and distributions (`count.<dimension>.<value>`); and one dataset input built with `mlflow.entities.Dataset(name, digest, source_type="zoo", source=<repo path>, profile=<JSON of aggregates>)`.
  - **Digest**: the first 16 hex characters of the version's sha256; the full hash goes in the tag. **verify**: the digest column length of the SQL store (believed 36 characters).
  - **Idempotent publishing**: search `tags.mmz.id = X and tags.mmz.version = Y`.
    - Same `mmz.sha256` → update the metrics of the existing run.
    - Different hash → new run, and the old run gets `mmz.superseded_by`.
  - **Links from runs**: training and evaluation runs log the same `Dataset` entity with context `training` or `evaluation`, so the run table's dataset filter (`datasets.digest IN (...)`) links runs and data in both directions (US5).
- **Rationale**:
  - A metadata-only `Dataset` with a profile round-trips through the server; this was tested. `MetaDataset` cannot carry a profile.
  - Search by tag and by dataset fields works; this was tested.
- **Alternatives considered**: MLflow's GenAI "evaluation datasets", which store records. Rejected: they are for content, which must not be stored.

## R10. Server security (revised 2026-10-16)

- **Decision**:
  - Pin `3.17.1` or newer.
  - Loopback only (`--host 127.0.0.1`), with the default Host-header check.
  - No AI assistant, gateway or LLM keys are configured on the server.
  - `mlflow.sh upgrade` is the documented path for new versions, and `docs/tracking.md` says to check OSV before upgrading.
  - Stop the server (`mlflow.sh down`) when it is not in use; that also backs it up.
- **Rationale**: 2025–2026 advisories include DNS rebinding (CVE-2025-14279, fixed in 3.5.0), unauthenticated file read (CVE-2026-2614, fixed in 3.10.0), assistant origin validation (CVE-2026-2611, fixed in 3.10.0), unauthenticated SSRF via the webhook test endpoint (GHSA-7gwp-5pfp-969j, fixed in 3.15.0) and about 12 more fixed in 3.17.0. A loopback-only server limits these to the owner's own browser; a malicious web page open while the server runs is the residual risk, which the Host and CORS checks address. Nothing listens on the Spark. Not configuring an assistant keeps Principle XI trivially true.
- **Alternatives considered**: a reverse proxy with TLS. Not needed on loopback.

## R11. Overview sources and how counts are found

- **Decision**: the overview reads only what exists. It adds no register fields.
  - **Third-party datasets**:
    - From the registry (`datasets.registry.declarations`), 17 entries today across security and condition-monitoring. The productdev `datasets.yaml` is empty.
    - Measured values come from `$MMZ_DATA/<id>/SOURCE.json` (`files[].bytes`, `sha256`, `retrieved_at`) and a walk of `$MMZ_DATA/<id>/` for size and file count.
    - The dataset hash is the sha256 of the sorted `name:sha256` lines from `SOURCE.json`, or the publisher checksum for zip-member downloads.
    - Without a download, the row shows `approx_size_mb` from the register and "not downloaded here".
  - **Source collection (productdev)**: `topics/productdev/compliance/sources.yaml` gives counts by source class, licence and permitted use. Snapshot size and count come from the configured `data/snapshots` directory when present.
  - **Benchmarks**: one reader per manifest shape.
    - **jtbd pilot** (`pilot-v1`, `pilot-v2`): counts are `len(chunks)`, `len(holdout_chunks)` and `len(train_chunks)`; lineage from `supersedes` and the history from `history[]`. These manifests hold no label distribution, so none is shown.
    - **jtbd cluster** (`cluster-v1`): `counts.items/snapshots/pairs/sets` by split, `excluded`, `revisions`.
    - **can-ids** (`can-ids-v1` to `v3`): from `captures[]`, counts by role, split, set, vehicle, dataset and attack family, plus frames, attack frames, episodes and duration; lineage from `based_on`.
    - **condition-monitoring**: has no benchmark folders yet (its `freeze` commands are stubs). The overview says so instead of inventing rows.
    - **Benchmark hash**: the existing whole-manifest formula `sha256(json.dumps(manifest, sort_keys=True))`, the same as `based_on.manifest_sha256` and the run records.
  - **Training sets**:
    - `span-train-v1` comes from `frozen.json` (`chunk_count`, `sha256`, `frozen_at`) and `rows/rows.stats.json` (`rows`, `rows_per_split`, `composition` by language, source type and sub-area). The path comes from `configs/productdev/jtbd/span-train-v1.yaml`, and `data/` is local.
    - picket-forest's training data is the `train` and `calibration` roles of `can-ids-v3`, shown on the benchmark row and in the run links.
    - The Keras tasks train straight from `$MMZ_DATA/<id>/extracted`. Their "training set" is the dataset version (its `SOURCE.json` hash), until a task freezes one.
  - **"Used by"**: register `used_by` for datasets, `evaluation.benchmark` of every release record for benchmarks, and the span config `dataset` plus the release `recipe` for training sets.
- **Rationale**: FR-003 and FR-008 (count and hash, never read content beyond that); the assumption that no register fields are added.
- **Alternatives considered**: adding counts to every register entry by hand. Rejected: they would drift, and measured values are better.

## R12. History and integrity from git

- **Decision**:
  - **Register history**: for each register file, `git log --format='%H %cs' --reverse -- <file>` plus `git show <sha>:<file>`, parsed per record id. Consecutive versions are diffed field by field. This is the same pattern as `site/roadmap.py:_history` and `catalog/pilot.py:_criteria_at_commits`, cached per process.
  - **Benchmark families**: the commit that added each manifest (`--diff-filter=A`), `frozen_at`, `supersedes` or `based_on`, and the manifest's own `history`, `events` or `revisions`.
  - **Integrity on every run, no data needed**:
    1. each `based_on.manifest_sha256` must equal the parent manifest's hash. No code checks this today.
    2. A frozen manifest must have no commits after its freezing commit, except revisions it records itself (cluster `revisions[]`).
  - **`--verify`**: when the data is present, it also calls the existing content verifiers: `freeze.verify_frozen` / `verify_benchmark_frozen`, cluster `bench.verify`, can-ids `verify_captures`.
  - In a shallow clone or outside git, history says "history unavailable (shallow clone)" and the integrity check is skipped with a note. It never fails.
- **Rationale**: FR-005 to FR-007. It reuses helpers and hash formulas that already exist.
- **Alternatives considered**: storing history in MLflow only. Rejected: the repository is the source of truth.

## R13. Importing past results (FR-028)

- **Decision**: `zoo tracking import` creates one run per existing result, tagged `mmz.imported=true` and `mmz.import_key=<model>@<version>` (or `<benchmark>/decision`).
  - **Sources**:
    - `zoo/models/*/results/<version>/{quality,performance}.json`: scout-large 0.1.0 to 0.1.3, picket-forest 0.2.0 and 0.2.1; sandbox-pipeline-tiny is skipped as a test model.
    - The matching release records: `date`, `evaluation.benchmark`, `recipe.git_commit`, `usage`.
    - `topics/productdev/benchmarks/cluster-v1/decision.json`.
    - `topics/condition-monitoring/reports/{hum-fan,pace-cnn}/research-report.json`.
  - **Timing**: `start_time` and `end_time` come from the record date (`create_run(start_time=…)`, `set_terminated(end_time=…)`), and metrics carry that timestamp.
  - **No reconstruction**: no curves are invented. Missing values stay missing.
  - **Idempotent**: a search on `mmz.import_key` before creating a run.
- **Rationale**: the owner's decision (Q1: A). Backdating is supported by the client.

## R14. Release record link

- **Decision**:
  - The release record gets an optional root object `tracking: {run_id, experiment}`, where `run_id` matches `^[0-9a-f]{32}$`.
  - The schema contract moves to `specs/017-mlflow-data-transparency/contracts/release/release-record.schema.json`, and `tests/release/test_schemas.py` points at it.
  - Gate rule 1 checks the form through the schema. Nothing requires the field.
  - The model card and website do not show it, because the store is private. `zoo release-verify` prints it with the evidence.
- **Rationale**: FR-022. The schema has `additionalProperties: false`, so the field must be declared, and the "latest owner" contract convention is the project's way to change it.

## R15. CI, extras and test strategy

- **Decision**:
  - `tracking` joins `TRAINING_EXTRAS` in `tests/unit/test_dependency_layout.py`, so it never appears on a model card's install line.
  - The base install and the `edge` size limit are unchanged.
  - The CI `test` job adds `--extra tracking`, so the wrapper and guard tests run with the real client against an in-process fake transport. No server runs in CI.
  - One `slow` integration test starts `mlflow server` (full `mlflow` via `uvx`) on a temporary SQLite store and runs: publish data, a tiny training run, import, audit.
  - New paths get rules in `scripts/ci/select_tests.py`.
- **Rationale**:
  - FR-011 and SC-008.
  - skinny cannot host a SQL store, so a real server needs full `mlflow`. That is fine for a slow, local test and too heavy for every CI run.
- **Alternatives considered**: a mocked `mlflow` module everywhere. Rejected: it would not catch API drift between versions.

## R16. Compliance register (revised 2026-10-16)

- **Decision**:
  - A new owner decision `D-tracking-store` in `compliance/decisions.yaml` records the store: its location (the owner's laptop, DE), its content (metrics, hashes, metadata; no personal data, no dataset content), access (owner only), retention (kept with the project, backups the newest 14), the offline logs (the same allow-listed content, written next to run outputs on the training machine, including the DGX Spark, where training outputs already live) and the Principle XI note (no assistant or LLM on the server).
  - The "Technical and organisational measures" text of `compliance/templates/record-of-processing.md.j2` gets one paragraph for the store. `zoo compliance render` then updates `docs/compliance/record-of-processing.md`, and the C-N3 drift check covers it.
  - `PRIVACY.md` and recipients are unchanged: there is no new recipient and no personal data.
- **Rationale**: FR-027. The register has no structured list of processing systems, and adding one for a single store would be more structure than content.

## R17. Offline run log and sync (FR-030, new 2026-10-16)

- **Decision**:
  - **Where**: next to the run's sidecar, never inside a staged or published folder. For a sidecar `<dir>/tracking.json` the log is `<dir>/tracking/<id>.mmz-run.jsonl`; for an explicit sidecar such as `data/models/span-xlmr-c1.tracking.json` it is `data/models/span-xlmr-c1.tracking/<id>.mmz-run.jsonl`. Allow-listed artifacts are copied to `<same folder>/<id>.mmz-run/<published name>`. `<id>` is a random 32-hex id, recorded in the sidecar (`mode: offline`, `offline_id`, `log`). A run without an output folder of its own (a finished evaluation or measurement logged through `tracking.record`) gets its sidecar under `data/tracking/`.
  - **Format** (`mmz-run/1`): one JSON object per line, appended and flushed per event: `{"seq": n, "t": <epoch ms>, "type": …}` with types `start` (format, experiment, name, task), `params`, `tags`, `metrics` (step and values), `input` (name, digest, source, profile, context), `artifact` (published name), `end` (status). Values pass the same guard (R8) before they are written; refused values are dropped and counted as in live mode.
  - **Continuing a run**: a later command that continues the run (e.g. `jtbd span tune`) finds the `offline_id` in the sidecar and appends to the same log.
  - **Sync**: `zoo tracking sync PATH... [--dry-run]` finds `*.mmz-run.jsonl` under the paths. Per log it searches `tags.mmz.offline_id`; it creates the run with the log's start time if missing, then replays only events with `seq` above the run's `mmz.offline_synced` tag, setting that tag after each batch. Metrics keep their step and timestamp. An `end` event sets the final status and end time. An incomplete last line is ignored until the next sync. Every value passes the guard again; artifacts are checked by name, size and the never-list (origin was checked when written). Output: one line per log, `created`, `updated` (with the number of new events) or `unchanged`; exit 0, or 8 when the server cannot be reached.
  - **Fetch**: `scripts/spark/tracking-pull.sh` runs `rsync -am` over SSH from the Spark's `mobility-model-zoo/data/` with includes for `*/`, `*.mmz-run.jsonl`, `*.mmz-run/***` and `*.tracking.json` and excludes everything else, into the laptop's `data/`, then runs `zoo tracking sync data/`.
- **Rationale**:
  - Append-only events with a sequence number make sync idempotent and incremental, which gives a near-live view by syncing again during training (SC-004) without anything running on the Spark.
  - An own small format is stable against MLflow's store changes, needs no MLflow in the training container, and the guard runs before anything is written on the Spark.
- **Alternatives considered**: MLflow file store (R2); mlflow-export-import (meant for whole servers, legacy on PyPI); copying the sidecar only (no curves).

## Open items carried into tasks (verify on the Spark)

1. **Host check**: *Verified locally on 2026-10-15 against mlflow 3.17.1 (SQLite server): a request with `Host: evil.example` gets 403 on the API and UI; `/health` is exempt from the check.* Since 2026-10-16 the server runs on the laptop with the default allowed hosts; the container path is gone.
2. **Digest length**: the maximum length of the dataset digest in the SQLite store (R9). *Verified locally on 2026-10-15: a 16-character digest round-trips through a SQLite-backed server and the `datasets.name` filter finds the run (`tests/integration/test_tracking_server.py`).*
3. **GPU metrics on GB10**: the offline sampler's `nvidia-smi` query reports utilisation and power in the NGC container (R7).
4. **Logging overhead**: below 2 % on one span training epoch in offline mode on the Spark, and in live mode on the laptop (SC-006).
