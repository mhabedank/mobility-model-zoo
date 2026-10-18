# Data overview and experiment tracking

Feature 017 makes visible what the zoo holds and how its models are trained: which datasets, training sets and benchmarks exist, how large they are, what they may be used for, when they changed, and which runs and models used them. Spec and design: [specs/017-mlflow-data-transparency/](../specs/017-mlflow-data-transparency/).

## What lives where

- **The repository is the source of truth.** Dataset registers (`topics/*/compliance/datasets.yaml`, `sources.yaml`), frozen benchmark manifests (`topics/*/benchmarks/`), freeze files of training sets, release records and gate rules decide everything, as before.
- **The tracking store is the lab notebook.** A private MLflow server on your laptop shows data versions and runs in the browser, sortable and comparable. No gate or report reads from it. Losing it loses no truth.
- **Nothing runs on the DGX Spark.** Training there writes an offline log next to its outputs, and you fetch and sync it from the laptop over SSH.
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

## The tracking server (laptop)

Start, stop, backup, restore and upgrade: [scripts/mlflow/README.md](../scripts/mlflow/README.md).

```bash
uv sync --extra tracking                       # the client (mlflow-skinny), about 70 MB
scripts/mlflow/mlflow.sh up                    # uvx mlflow==3.17.1 on 127.0.0.1:5000, in the background
# .env: MLFLOW_TRACKING_URI=http://127.0.0.1:5000
uv run zoo tracking status                     # server version and experiments
uv run zoo data publish --profile              # the overview as the `datasets` experiment
uv run zoo tracking audit                      # anything in the store that should not be there?
open http://127.0.0.1:5000
scripts/mlflow/mlflow.sh down                  # takes a backup, then stops the server
```

- **Without `MLFLOW_TRACKING_URI` and `MMZ_TRACKING_OFFLINE`**, every command behaves exactly as before. Nothing is imported or written.
- **`zoo data publish` is idempotent.** An unchanged version updates its run. A changed one (new hash) gets a new run, and the old run is tagged `mmz.superseded_by`. Publish from the machine that has the data, so that sizes and hashes are measured.
- **Training on the laptop** logs live while the server runs. **If the server is unreachable**, a run continues without tracking. Its output folder gets `tracking.json` with `complete: false`, and the log shows one warning.
- **Backups**: every `mlflow.sh down` (and `upgrade`) writes one to `$MMZ_TRACKING_BACKUP` (default `~/mlflow-backups`) and keeps the newest 14. Point it at an external drive in `.env` if you like.

## Training on the Spark (offline logs, pull and sync)

Set `MMZ_TRACKING_OFFLINE=1` in the laptop's `.env`. `train_span.sh` passes it into the training container, which then writes an offline log instead of talking to a server: no port, no tunnel, no tracking software on the Spark.

```bash
topics/productdev/scripts/spark/train_span.sh c1
scripts/spark/tracking-pull.sh                 # during the run: the epochs so far
scripts/spark/tracking-pull.sh                 # after the run: the rest and the final status
```

- **Where the log is**: next to the run's sidecar, never inside the model folder, because that folder is staged as it is. For `data/models/span-xlmr-c1` it is `data/models/span-xlmr-c1.tracking/<id>.mmz-run.jsonl`, with `span-xlmr-c1.tracking.json` beside it (`mode: offline`).
- **`tracking-pull.sh`** copies only offline logs, their artifact folders and sidecars over SSH (never models or training data) into the same paths under `data/`, then runs `zoo tracking sync data/`. The server must be running.
- **`zoo tracking sync PATH...`** prints one line per log: `created`, `updated N` (N new events) or `unchanged`, plus `running` while the log has no end yet. It adds only what is new, keeps the run's own times and epochs, and checks every value with the guard again. A log with a refused value is skipped whole (exit 7) and nothing of it is written.
- **The logs are a second copy.** If the store is lost, `zoo tracking sync data/` (or a fresh pull) brings the Spark runs back.
- **Continuing a run**: `jtbd span tune` after `span train` appends to the same offline log, as it continues the same run live.

## Past results and release records

```bash
uv run zoo tracking import --dry-run           # what would be created
uv run zoo tracking import                     # once; a second run prints only `exists`
uv run zoo tracking import --model scout-large
```

- **One run per published result**: every `zoo/models/*/results/<version>/` (with the release record's date, benchmark, recipe commit and usage), the `cluster-v1` decision and the condition-monitoring research reports. The test model `sandbox-pipeline-tiny` is skipped.
- **Nothing is reconstructed.** A run carries the date of its record, the numbers of its results files and nothing else: no curves, and a missing value stays missing. Imported runs are tagged `mmz.imported=true` and `mmz.import_key=<model>@<version>`.
- **A release record may name its run** with `tracking: {run_id, experiment}`. `zoo check` (and so `release-verify`) prints it with the gate results; the model card and the website never show it, because the store is private.

## Experiments

`datasets`, `productdev/jtbd-span`, `productdev/jtbd-cluster`, `security/can-ids`, `condition-monitoring/sound-anomaly`, `condition-monitoring/activity`, `edge/hil-bench`, `spikes`. Spike runs carry `mmz.spike=true` and are never benchmark results.

Useful filters in the run table:

- `tags.mmz.benchmark = 'pilot-v2'`: every result on one frozen benchmark version. Compare runs only within one benchmark version (constitution VIII).
- `datasets.name = 'can-ids@can-ids-v3'`: every run that trained or was evaluated on that version.
- `tags.mmz.imported = 'true'`: results imported from the repository's results files.

## Privacy and security

- **The server listens only on the laptop's 127.0.0.1.** Nothing on the network reaches it, and nothing listens on the Spark.
- **Stop the server when you do not need it** (`mlflow.sh down`, which also backs it up): while it runs, a web page in your browser could talk to it. Its host check refuses requests that do not name localhost or 127.0.0.1.
- **Offline logs on the Spark** hold the same allow-listed numbers, hashes and metadata as the store, checked by the guard before they are written; they sit next to the training outputs that are already there.
- **No assistant, gateway or language model is configured on the server** (constitution XI).
- **Before upgrading**, check the advisories at <https://osv.dev/list?ecosystem=PyPI&q=mlflow>.
- **What may be logged** is listed in [contracts/tracking.md](../specs/017-mlflow-data-transparency/contracts/tracking.md). A refused value is dropped with a warning and counted in `tracking.json`.
