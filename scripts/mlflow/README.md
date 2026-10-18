# MLflow tracking server on the laptop (feature 017)

The zoo's experiment tracking store: a private MLflow server on the owner's laptop, on 127.0.0.1 only. It holds numbers, hashes and metadata of data versions and runs, never dataset content, labels or model weights. The repository stays the source of truth. Owner guide: [docs/tracking.md](../../docs/tracking.md). Design: [specs/017-mlflow-data-transparency/research.md](../../specs/017-mlflow-data-transparency/research.md) (R2, R3, R10, R17).

Nothing runs on the DGX Spark: training runs there write an offline log next to their outputs; `scripts/spark/tracking-pull.sh` fetches the logs over SSH and syncs them into this store.

## Start and stop

```bash
scripts/mlflow/mlflow.sh up        # uvx mlflow==3.17.1, store in ~/.local/share/mobility-model-zoo/mlflow
scripts/mlflow/mlflow.sh status    # pid, health, version, listening on 127.0.0.1:5000 only
open http://127.0.0.1:5000
scripts/mlflow/mlflow.sh down      # takes a backup, then stops the server
```

`.env` (only these keys are read by the script):

```text
MLFLOW_TRACKING_URI=http://127.0.0.1:5000                   # for the zoo commands
MMZ_TRACKING_HOME=~/.local/share/mobility-model-zoo/mlflow  # optional, the default
MMZ_TRACKING_BACKUP=/Volumes/<drive>/mlflow-backups         # optional, default ~/mlflow-backups
```

Open `http://127.0.0.1:5000`, not `localhost:5000`: on macOS the AirPlay receiver also listens on port 5000 (on all interfaces), and `localhost` may resolve to IPv6, where AirPlay answers instead of MLflow. MLflow itself listens on 127.0.0.1 only. To move it, set `MMZ_TRACKING_PORT` and the port in `MLFLOW_TRACKING_URI`, or switch off System Settings → General → AirDrop & Handoff → AirPlay Receiver.

Stop the server when you do not need it: while it runs, a web page in your browser could talk to it. Its host check refuses requests that do not name localhost or 127.0.0.1.

## Backup, restore, upgrade

- **Backup**: `mlflow.sh down` (and `upgrade`) first runs `mlflow.sh backup`: an online copy of the SQLite store through SQLite's backup API, a tar of the artifacts and the MLflow version, in `$MMZ_TRACKING_BACKUP/<date-time>/`. The newest 14 are kept.
- **Restore**: `mlflow.sh restore <backup dir>` backs up and stops a running server, replaces store and artifacts, and starts the MLflow version recorded in the backup.
- **Upgrade**: `mlflow.sh upgrade 3.x.y` takes a backup, stops the server, runs `mlflow db upgrade` with the new version and starts it; later `up` calls use that version. Before upgrading, check the advisories at <https://osv.dev/list?ecosystem=PyPI&q=mlflow>.

Restore drill (spec SC-009, under 30 minutes): stop the server (backup), restore that backup, check in the browser that the same runs are there, and write the date and duration below.

| Date | Duration | Result |
|---|---|---|
| 2026-10-16 | 8 s (store 1.2 MB: 16 data versions, 9 imported runs) | same runs and experiments after restore; host check `evil.example` → 403; listening on 127.0.0.1:5000 only |

Losing the store loses no truth: the data overview can be published again from the repository (`zoo data publish`), past results imported again (`zoo tracking import`), and Spark runs synced again from their offline logs (`zoo tracking sync`).
