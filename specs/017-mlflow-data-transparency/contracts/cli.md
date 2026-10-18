# CLI contract: feature 017

New commands live under the existing `zoo` app: four under `zoo data` and a new group `zoo tracking`. The training and evaluation commands of each task keep their interface. They only gain logging when `MLFLOW_TRACKING_URI` (live, laptop) or `MMZ_TRACKING_OFFLINE=1` (offline log, Spark) is set.

## Shared behaviour

**Exit codes**: codes 1 to 6 keep their existing meanings (`release/errors.py`: 1 general or gate, 2 usage, 3 immutability, 4 approval, 5 credentials, 6 hub; `zoo data` uses 6 for data errors). Two codes are new and unused today:

| Code | Meaning |
|---|---|
| 7 | integrity failure (`zoo data stats`) or audit findings (`zoo tracking audit`) |
| 8 | tracking server not configured or unreachable (only commands whose job is to talk to the server: `zoo data publish`, `zoo tracking …`); on the laptop, start it with `scripts/mlflow/mlflow.sh up` |

**Output**: tables by default. `--json` prints the same rows as JSON, as a list of [InventoryRow](../data-model.md#inventoryrow) or the entity named per command.

**Content**: no command prints dataset content (FR-008).

## `zoo data stats`

Lists every dataset, source collection, training set and benchmark version (US1).

```text
zoo data stats [--topic TOPIC]... [--kind dataset|source-collection|training-set|benchmark]...
               [--use training_allowed|benchmark_only] [--include-rejected]
               [--verify] [--json] [--wide]
```

- **Default table columns**: `topic kind id version status use size files main-count frozen last-change integrity`.
- **`--wide`**: adds licence, redistribution, sha256 (12 characters), lineage and used-by.
- **`--include-rejected`**: also shows datasets with status `rejected` or `broken_at_source`. They are hidden by default but counted in the footer.
- **Footer**: totals per kind and topic, and the total measured size.
- **`--verify`**: runs the content verifiers where data is present (research R12). It is slow on large data.
- **Exit codes**: 0, or 7 when any row has integrity `mismatch` or `changed-after-freeze`. Rows with `availability: error` print the error and do not change the exit code.
- **Works with**: the `release` extra. MLflow is not needed.

## `zoo data history ID`

Shows the history of one dataset id, benchmark family (`can-ids`, `pilot`, `cluster`), training set (`span-train`) or one version (`can-ids-v2`) (US2).

```text
zoo data history ID [--json]
```

- **Output**: [HistoryEvent](../data-model.md#historyevent) rows, oldest first, then the lineage chain.
- **Outside git or in a shallow clone**: prints the history it can see, followed by "history incomplete (shallow clone or no git)", and exits 0. The freeze check of `zoo data stats` is skipped there with a note on each benchmark.

## `zoo data diff A B`

Compares two versions of the same family, for example `zoo data diff can-ids-v2 can-ids-v3` (US2).

```text
zoo data diff A B [--members] [--json]
```

- **Output**: a [VersionDiff](../data-model.md#versiondiff).
- **`--members`**: also lists added, removed and changed member ids.
- **Kinds or families differ**: exit 2.

## `zoo data publish`

Publishes the overview to the `datasets` experiment (US3). Publishing is idempotent (FR-015).

```text
zoo data publish [--topic TOPIC]... [--kind ...]... [--dry-run] [--profile]
```

- **`--dry-run`**: writes nothing.
  - **With a tracking URI**: it looks up existing runs read-only and prints `create`, `update` or `supersede` per row.
  - **Without one**: it prints every row as `create` and says that no server was asked. It exits 0.
- **Register-only rows** (dataset not downloaded on this machine): published with version `register`, register metrics only (`approx_size_mb`) and no `mmz.sha256`. Once the dataset is downloaded and published from that machine, a run with the retrieval-date version is created, and the `register` run is tagged `mmz.superseded_by`.
- **`--profile`**: attaches `profile.json` per version (aggregates only).
- **Exit codes**: 0, or 8 without a tracking URI or with the server unreachable (FR-011: other commands are unaffected).

## `zoo tracking status`

Reports the configured URI host, server version, the experiments with run counts, and whether the client extra is installed. It is the first thing to run after `scripts/mlflow/mlflow.sh up`.

```text
zoo tracking status [--json]
```

Exit codes: 0, 8.

## `zoo tracking import`

Imports past results once as runs marked `imported` (FR-028, research R13).

```text
zoo tracking import [--model NAME]... [--dry-run]
```

- **Output**: one line per source record, `created` or `exists`, with the import key.
- **Values**: no value is reconstructed.
- **Exit codes**: 0, 8.

## `zoo tracking sync`

Replays offline run logs into the store (FR-030, research R17).

```text
zoo tracking sync PATH... [--dry-run]
```

- **Finds**: every `*.mmz-run.jsonl` under the given paths.
- **Per log**: `created` (new run), `updated N` (N new events replayed) or `unchanged`, with the experiment, the run name and `running` when the log has no `end` yet.
- **Rules**: idempotent and incremental through `mmz.offline_id` and `mmz.offline_synced`; an incomplete last line waits for the next sync; every value passes the guard again; a refused value is reported and skipped.
- **Exit codes**: 0, 7 (a log fails the guard and nothing of it was written), 8.

## `zoo tracking audit`

Scans the whole store for anything that is not an allowed number, hash or metadata value (SC-007, research R8).

```text
zoo tracking audit [--experiment NAME]... [--json]
```

- **What it scans**: every param, tag and text artifact, with the publication scan's personal-identifier detectors, plus the guard rules applied after the fact.
- **Exit codes**: 0 when clean, 7 with findings (one line per finding: experiment, run, key; a value at most as its first 12 characters, and never for personal data or source text), 8.

## Changes to existing commands

Each command below logs only when a tracking URI is set. Without one, its behaviour and output are byte-identical to today (SC-008).

| Command | Experiment | Logged |
|---|---|---|
| `jtbd span train` | `productdev/jtbd-span` | config params, per-epoch `history` metrics, best epoch, training set input (`span-train-v1`), system metrics, sidecar |
| `jtbd span tune` | same run when the candidate's run id is in `span_config.json`, else a new run | thresholds as params, tuning metrics |
| `jtbd score`, `jtbd perf --backend span`, `jtbd span results` | `productdev/jtbd-span` | evaluation metrics, benchmark input (`pilot-v2` or the named version) |
| `jtbd cluster tune`, `jtbd cluster score` | `productdev/jtbd-cluster` | grid and scores, benchmark input (`cluster-v1`) |
| `zoo-security can-ids evaluate`, `zoo-security can-ids forest evaluate` (`forest.py:cmd_evaluate`) and `evaluate_v2` | `security/can-ids` | per-detector metrics, benchmark input with `manifest_sha256` |
| `zoo-security can-ids forest export` (`forest.py:cmd_export`) and `zoo-security can-ids v2 export` (`release_export_v2.export`) | `security/can-ids` | training run: forest settings, training input (the benchmark's `train` and `calibration` roles), export metrics, `config.json` of the export as artifact; never the model files |
| `zoo-security can-ids measure` | `security/can-ids` | performance metrics per board |
| `zoo-security can-ids mlp train`, `condmon sound-anomaly train`, `condmon activity train` | `security/can-ids`, `condition-monitoring/sound-anomaly`, `condition-monitoring/activity` | Keras per-epoch metrics through a callback, export report metrics, dataset input (`SOURCE.json` hash) |
| `edge run` and the HIL pytest plugin | `edge/hil-bench` | measurement run (`mmz.kind=measure`): `summarize()` perf and accuracy per board and model, `summary.json` and `summary.md` artifacts, the hash of any evaluation file used |
| `zoo release-verify` | none | prints `tracking.run_id` when the record has one |

## Scripts (revised 2026-10-16)

`scripts/mlflow/mlflow.sh` runs on the laptop. It replaces `scripts/spark/mlflow/`; nothing runs as a service on the Spark.

```text
mlflow.sh up                    # uvx mlflow==${MLFLOW_VERSION:-3.17.1} server on 127.0.0.1:5000, in the background
mlflow.sh down                  # backup, then stop
mlflow.sh status | logs
mlflow.sh backup                # online SQLite backup + artifacts tar → $MMZ_TRACKING_BACKUP/<date-time>/, keep 14
mlflow.sh restore DIR           # stop, replace store, start
mlflow.sh upgrade VERSION       # backup, stop, mlflow db upgrade, start VERSION
```

Paths come from `MMZ_TRACKING_HOME` and `MMZ_TRACKING_BACKUP` (`.env` or environment, with the defaults in research R3). The script never configures an assistant, gateway or LLM key.

`scripts/spark/tracking-pull.sh [REMOTE_DATA_DIR]` (laptop): rsync over `$SPARK_HOST` of only `*.mmz-run.jsonl`, `*.mmz-run/` and `*.tracking.json` from `mobility-model-zoo/data/` (or the given directory) into `data/`, then `uv run zoo tracking sync data/`. It needs SSH only.

`topics/productdev/scripts/spark/train_span.sh` changes:
- When `.env` sets `MMZ_TRACKING_OFFLINE=1`, it starts the training container with `-e MMZ_TRACKING_OFFLINE=1 -e MMZ_HARDWARE=dgx-spark`. No network option, no address, no `tracking` extra (`/work[jtbd]` as before).
- Its header says how to fetch and sync the log (`scripts/spark/tracking-pull.sh`).
- Without the variable it behaves as today.
