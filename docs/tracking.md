# Data overview and experiment tracking

Feature 017 makes visible what the zoo holds and how its models are trained: which datasets, training sets and benchmarks exist, how large they are, what they may be used for, when they changed, and which runs and models used them. Spec and design: [specs/017-mlflow-data-transparency/](../specs/017-mlflow-data-transparency/).

## What lives where

- **The repository is the source of truth.** Dataset registers (`topics/*/compliance/datasets.yaml`, `sources.yaml`), frozen benchmark manifests (`topics/*/benchmarks/`), freeze files of training sets, release records and gate rules decide everything, as before.
- **The tracking store is the lab notebook.** A private MLflow server on the DGX Spark shows data versions and runs in the browser, live, sortable and comparable. No gate or report reads from it. Losing it loses no truth.
- **Only numbers, hashes and metadata enter the store.** No dataset text, chunk, label, frame, payload, personal data or model weight. An allow-list guard checks every value before it leaves the machine, and `zoo tracking audit` checks the store afterwards.

## The data overview (no server needed)

```bash
uv run zoo data stats                          # every dataset, training set and benchmark version
uv run zoo data stats --kind benchmark --wide  # with licence, hash, lineage and the models using it
uv run zoo data stats --use benchmark_only --json
uv run zoo data history can-ids                # freezes, lineage, exclusions, register changes
uv run zoo data history can-train-and-test     # registration and every change of licence or use
uv run zoo data diff can-ids-v2 can-ids-v3 --members
```

- **Sizes and hashes** of third-party datasets are measured where they are downloaded (`$MMZ_DATA`). Elsewhere a row shows the register's approximate size and says "not downloaded here".
- **Integrity**: `zoo data stats` exits 7 when a frozen benchmark changed. Either its `based_on` hash no longer matches the parent, or its content changed after the freeze. Lifecycle updates, recorded revisions and a re-freeze before any labeling are allowed. Never edit a frozen manifest to make the check pass (constitution IX); a change makes a new benchmark version.
- **History** needs the full git history. In a shallow clone, run `git fetch --unshallow` first.

## The tracking server

Setup, backup, restore and upgrade on the Spark: [scripts/spark/mlflow/README.md](../scripts/spark/mlflow/README.md). On the laptop:

```bash
uv sync --extra tracking                       # the client (mlflow-skinny), about 70 MB
scripts/spark/mlflow/mlflow.sh tunnel &        # SSH tunnel to the Spark; close it when done
# .env: MLFLOW_TRACKING_URI=http://127.0.0.1:5000
uv run zoo tracking status                     # server version and experiments
uv run zoo data publish --profile              # the overview as the `datasets` experiment
uv run zoo tracking audit                      # anything in the store that should not be there?
```

- **Without `MLFLOW_TRACKING_URI`**, every command behaves exactly as before. Nothing is imported or written.
- **`zoo data publish` is idempotent.** An unchanged version updates its run. A changed one (new hash) gets a new run, and the old run is tagged `mmz.superseded_by`. Publish from the machine that has the data, so that sizes and hashes are measured.
- **Training containers on the Spark** reach the server as `MLFLOW_TRACKING_URI_CONTAINER` (usually `http://mlflow:5000`). The Spark scripts pass it in.
- **If the server is unreachable**, a run continues without tracking. Its output folder gets `tracking.json` with `complete: false`, and the log shows one warning.

## Experiments

`datasets`, `productdev/jtbd-span`, `productdev/jtbd-cluster`, `security/can-ids`, `condition-monitoring/sound-anomaly`, `condition-monitoring/activity`, `edge/hil-bench`, `spikes`. Spike runs carry `mmz.spike=true` and are never benchmark results.

Useful filters in the run table:

- `tags.mmz.benchmark = 'pilot-v2'`: every result on one frozen benchmark version. Compare runs only within one benchmark version (constitution VIII).
- `datasets.name = 'can-ids@can-ids-v3'`: every run that trained or was evaluated on that version.
- `tags.mmz.imported = 'true'`: results imported from the repository's results files.

## Privacy and security

- **The server listens only on the Spark's 127.0.0.1.** SSH is the only way in.
- **Close the tunnel when you do not need it.** The server's host check refuses requests that do not name localhost, 127.0.0.1 or mlflow.
- **No assistant, gateway or language model is configured on the server** (constitution XI).
- **Before upgrading**, check the advisories at <https://osv.dev/list?ecosystem=PyPI&q=mlflow>.
- **What may be logged** is listed in [contracts/tracking.md](../specs/017-mlflow-data-transparency/contracts/tracking.md). A refused value is dropped with a warning and counted in `tracking.json`.
