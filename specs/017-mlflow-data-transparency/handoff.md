# Handoff: feature 017, state on 2026-10-18

Branch `claude/mlflow-data-transparency`, pull request #39. Tasks: [tasks.md](tasks.md).

## Done

All code tasks are done:

- **Data overview**: `zoo data stats`, `zoo data history` and `zoo data diff`.
- **Tracking server script**: `scripts/spark/mlflow/mlflow.sh`.
- **Publishing and checks**: `zoo data publish`, `zoo tracking status`, `zoo tracking import` and `zoo tracking audit`.
- **Run logging**: span training and tuning, Keras trainings, jtbd and cluster evaluations, can-ids evaluation, measurement and picket-forest training, and the HIL bench all log to the tracking server when `MLFLOW_TRACKING_URI` is set. Without it nothing changes.
- **Release records**: they may carry `tracking.run_id`.
- **Compliance**: decision `D-tracking-store` and the updated record of processing.

The integrations were built before the robustness check T041. That check still decides whether they stay on: if it fails, leave the tracking address out of `.env` (everything then runs as before) and report it.

## Open: owner steps on the DGX Spark

These need the Spark and cannot run from a cloud session. Commands: [scripts/spark/mlflow/README.md](../../scripts/spark/mlflow/README.md).

### T039: start the server, check it, back it up and restore it

1. On the Spark:

   ```bash
   scripts/spark/mlflow/mlflow.sh up
   scripts/spark/mlflow/mlflow.sh status
   ```

2. From another machine on the network, `curl http://<spark-ip>:5000` must fail.
3. Add the nightly backup line from the README to the crontab. Run `mlflow.sh backup`, then `mlflow.sh restore ~/mlflow-backups/<date>`, and write the duration into the table in the README.
4. On the laptop:
   - put `MLFLOW_TRACKING_URI=http://127.0.0.1:5000` and `MLFLOW_TRACKING_URI_CONTAINER=http://mlflow:5000` into `.env`;
   - run `scripts/spark/mlflow/mlflow.sh tunnel`, then `uv run zoo tracking status` and `uv run zoo data publish --profile`.

### T041: robustness check of training with tracking

1. Run `topics/productdev/scripts/spark/train_span.sh c1` and watch the run in the browser: one point per epoch.
2. During a second run, run `mlflow.sh down` once and then `mlflow.sh up`. The training must finish normally, and `data/models/span-xlmr-c1.tracking.json` must show `"complete": false`.
3. Compare the epoch time with and without `MLFLOW_TRACKING_URI_CONTAINER`. The difference must be below 2 %.
4. Check whether GPU utilisation appears under system metrics.

Write the results into [research.md](research.md) under "Open items".

### T053 and T060: import and final check against the real server

```bash
uv run zoo tracking import                     # twice: the second run reports "exists"
uv run zoo tracking audit                      # exit 0
```

Then walk through [quickstart.md](quickstart.md) and tick off SC-001 to SC-010.
