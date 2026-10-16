# MLflow tracking server on the DGX Spark (feature 017)

The zoo's experiment tracking store: a private MLflow server on the Spark that the laptop reaches through an SSH tunnel. It holds numbers, hashes and metadata of data versions and runs, never dataset content, labels or model weights. The repository stays the source of truth. Owner guide: [docs/tracking.md](../../../docs/tracking.md). Design: [specs/017-mlflow-data-transparency/research.md](../../../specs/017-mlflow-data-transparency/research.md) (R2, R3, R10).

## One-time setup on the Spark

```bash
git clone … mobility-model-zoo && cd mobility-model-zoo
scripts/spark/mlflow/mlflow.sh up          # pulls ghcr.io/mlflow/mlflow:v3.17.1 (arm64), store in ~/mlflow
scripts/spark/mlflow/mlflow.sh status      # container up, /health OK, version 3.17.1
```

Nightly backup (keeps the newest 14 in `~/mlflow-backups/`), added with `crontab -e`:

```text
17 3 * * * cd $HOME/mobility-model-zoo && scripts/spark/mlflow/mlflow.sh backup >> $HOME/mlflow-backups/cron.log 2>&1
```

Check once, from another machine on the network, that the server is not reachable there: `curl http://<spark-ip>:5000` must fail. It listens on the Spark's 127.0.0.1 only.

## On the laptop

```bash
# .env
SPARK_HOST=user@spark
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MLFLOW_TRACKING_URI_CONTAINER=http://mlflow:5000

scripts/spark/mlflow/mlflow.sh tunnel &    # keep it open while you work, close it afterwards
uv run zoo tracking status
open http://127.0.0.1:5000
```

Close the tunnel when you do not need it: while it is open, a web page in your browser could talk to the server. The server's host check (`--allowed-hosts`) refuses requests that do not name localhost, 127.0.0.1 or mlflow.

## Backup, restore, upgrade

- `mlflow.sh backup`: online copy of the SQLite store through SQLite's backup API, plus a tar of the artifacts and the image tag, in `~/mlflow-backups/<date>/`.
- `mlflow.sh pull-backup` (laptop): copies the newest backup from the Spark to `~/mlflow-backups/`.
- `mlflow.sh restore ~/mlflow-backups/<date>`: stops the server, replaces store and artifacts, starts the image tag recorded in the backup.
- `mlflow.sh upgrade v3.x.y`: takes a backup, stops the server, runs `mlflow db upgrade` with the new image and starts it. Before upgrading, check the advisories at <https://osv.dev/list?ecosystem=PyPI&q=mlflow> and `mlflow server --help` of the new tag (the `--allowed-hosts` syntax).

Restore drill (spec SC-009, under 30 minutes): take a backup, restore it, check in the browser that the same runs are there, and write the date and duration below.

| Date | Duration | Result |
|---|---|---|
| (not yet run) | | |

Losing the store loses no truth: the data overview can be published again from the repository (`zoo data publish`) and past results imported again (`zoo tracking import`); only live training curves would be missing.
