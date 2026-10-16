# Handoff: feature 017, state on 2026-10-16

Branch `claude/mlflow-data-transparency`, pull request #39. Tasks: [tasks.md](tasks.md) (40 done, 21 open).

## Done

- **US1 and US2 (data overview)**: `zoo data stats`, `zoo data history` and `zoo data diff`, with integrity checks of frozen benchmarks.
- **US3 (tracking)**:
  - The tracking server script `scripts/spark/mlflow/mlflow.sh`.
  - The tracking package `src/mobility_model_zoo/tracking/`.
  - The commands `zoo data publish`, `zoo tracking status` and `zoo tracking audit`.
- **T040 and T042**: span training and tuning log to the tracking server. `topics/productdev/scripts/spark/train_span.sh` passes the server address into the training container.

## Next: two owner steps on the DGX Spark

### T039: start the tracking server

Follow [scripts/spark/mlflow/README.md](../../scripts/spark/mlflow/README.md).

1. On the Spark:

   ```bash
   scripts/spark/mlflow/mlflow.sh up
   scripts/spark/mlflow/mlflow.sh status
   ```

2. From another machine on the network, `curl http://<spark-ip>:5000` must fail.
3. Add the nightly backup line to the crontab. Run `mlflow.sh backup`, then `mlflow.sh restore ~/mlflow-backups/<date>`, and write the duration into the table in the README.
4. On the laptop:
   - put `MLFLOW_TRACKING_URI=http://127.0.0.1:5000` and `MLFLOW_TRACKING_URI_CONTAINER=http://mlflow:5000` into `.env`;
   - run `scripts/spark/mlflow/mlflow.sh tunnel`, then `uv run zoo tracking status`, then `uv run zoo data publish --profile`.

### T041: robustness check of training with tracking

This decides whether the remaining integrations go ahead (plan: Principle IV).

1. Run `topics/productdev/scripts/spark/train_span.sh c1` and watch the run in the browser: one point per epoch.
2. During a second run, run `mlflow.sh down` once and then `mlflow.sh up` again. The training must finish normally, and `data/models/span-xlmr-c1.tracking.json` must show `"complete": false`.
3. Compare the epoch time with and without `MLFLOW_TRACKING_URI_CONTAINER`. The difference must be below 2 %.
4. Check whether GPU utilisation appears under system metrics.

Write the results into [research.md](research.md) under "Open items".

## After T041 passes

Continue with:

- **T043 and T044**: Keras callback for the condition-monitoring and MLP training.
- **US5**: T046 to T053 and T061 (evaluation runs, picket-forest training, import of past results, release-record link).
- **US6**: T054 and T055.
- **Polish**: T056 to T060.

If T041 fails, stop and keep only the data overview and the tracking server.
