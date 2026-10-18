# Handoff: feature 017, state on 2026-10-16

Branch `claude/mlflow-data-transparency`, pull request #39. Tasks: [tasks.md](tasks.md).

## Revision 2026-10-16: the store moves to the laptop

Nothing of the tracking feature runs as a service on the DGX Spark:

- the MLflow server runs on the owner's laptop, on 127.0.0.1 only, started with `scripts/mlflow/mlflow.sh up` (T062);
- training on the Spark writes an offline run log next to its sidecar (`MMZ_TRACKING_OFFLINE=1`, T065);
- `scripts/spark/tracking-pull.sh` fetches only these logs over SSH and `zoo tracking sync` replays them into the store, incrementally (T066, T067).

Spec decision 2, FR-009, FR-010, FR-012, FR-020, the new FR-030 and SC-004 changed; research R2, R3, R4, R7, R10 and R16 are revised and R17 is new. The compliance decision `D-tracking-store` (T056) now names the laptop.

## Done

- **US1 and US2 (data overview)**: `zoo data stats`, `zoo data history` and `zoo data diff`, with integrity checks of frozen benchmarks.
- **US3 (tracking core)**: the tracking package `src/mobility_model_zoo/tracking/`, `zoo data publish`, `zoo tracking status` and `zoo tracking audit`. The Spark server script `scripts/spark/mlflow/` is superseded and removed by T062.
- **T040 and T042**: span training and tuning log through `tracking.run()`; T065 makes the same calls work offline.
- **T050 and T051**: `zoo tracking import` of past results, and the optional `tracking` link in release records, printed by the gate and never on the card.
- **T057 and T058**: owner guide and command lists; the server parts of `docs/tracking.md` are rewritten by T069.

- **T062 to T068** (2026-10-16): `scripts/mlflow/mlflow.sh` on the laptop (tested end to end: up, loopback only, backup on down, restore), offline mode in `tracking.run()` (`tracking/offline.py`), `zoo tracking sync` (`tracking/sync.py`), `scripts/spark/tracking-pull.sh`, `train_span.sh` in offline mode, tests including a sync into a real server.

- **T069 and T056** (2026-10-16): `docs/tracking.md` describes the laptop server and Spark pull and sync; `D-tracking-store` in `compliance/decisions.yaml` names the laptop, and the record of processing is re-rendered.

## Next: two owner steps

- **T039 (laptop)**: `mlflow.sh up`, check loopback and host check, `down` and `restore` once with timing, `zoo data publish --profile`.
- **T041 (Spark + laptop, go/no-go)**: one span candidate offline, pulled mid-run and after; overhead under 2 %; GPU metrics; one laptop run with the server stopped mid-run.

## After T041 passes

T043 to T049 and T061 (Keras callback, evaluation runs, picket-forest training), T052's integration tests, T053, US6 (T054, T055), then T059 and T060. If T041 fails, stop and keep the data overview, the import and the laptop server.
