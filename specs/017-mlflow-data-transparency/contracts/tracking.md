# Tracking contract: what may enter the store

The wrapper `mobility_model_zoo.tracking` is the only module that imports MLflow. It enforces this contract with the guard (research R8). `zoo tracking audit` checks it again on the stored data.

## Python interface (used by task code)

```python
from mobility_model_zoo import tracking

with tracking.run(
    experiment="productdev/jtbd-span",      # one of EXPERIMENTS
    name="span-xlmr-c1",
    task="jtbd-span",
    config_path="configs/productdev/jtbd/span-xlmr.yaml",   # committed file; flattened into params
    inputs=[tracking.data_ref("span-train", "span-train-v1", context="training")],
    out_dir=out,                              # sidecar tracking.json goes here
    system_metrics=True,
) as r:
    r.log_step(epoch, {"loss": 0.41, "item_f1": 0.63})
    r.log_final({"best_epoch": 4, "score": 0.71})
    r.log_artifact(out / "span_config.json")  # allow-listed kinds only
```

- **No tracking URI and no offline mode**: `tracking.run(...)` returns a no-op object. Nothing is imported, nothing is written, and no sidecar is created.
- **Offline mode** (`MMZ_TRACKING_OFFLINE=1`, no URI; revised 2026-10-16): the same calls write the guarded values to the offline run log next to the sidecar (research R17, [data-model.md](../data-model.md#offlinerunlog-idmmz-runjsonl-research-r17)). MLflow is not imported. `out_dir` or `sidecar` is required; without either the run is a no-op with one warning. `zoo tracking sync` replays the log into the store.
- **Errors**: never raised to the caller at run time. See the circuit breaker in research R5. Tests set `tracking.STRICT = True` so guard refusals raise.
- **`data_ref(id, version, context)`**: resolves the [InventoryRow](../data-model.md#inventoryrow) and logs it as a dataset input. When the row cannot be resolved, it logs a tag `mmz.input_unresolved=<id>@<version>` and warns.

## Experiments

`datasets`, `productdev/jtbd-span`, `productdev/jtbd-cluster`, `security/can-ids`, `condition-monitoring/sound-anomaly`, `condition-monitoring/activity`, `edge/hil-bench`, `spikes`. A new task adds its experiment here.

## Tags (allow-list)

| Key | Value | On |
|---|---|---|
| `mmz.kind` | `dataset`, `source-collection`, `training-set`, `benchmark`, `train`, `tune`, `evaluate`, `measure`, `import` | all |
| `mmz.topic` | topic id | all |
| `mmz.task` | task id (`jtbd-span`, `can-ids`, …) | runs |
| `mmz.id`, `mmz.version` | inventory id and version | data runs |
| `mmz.sha256` | 64-hex | data runs |
| `mmz.frozen_at` | ISO date | data runs |
| `mmz.permitted_use` | `training_allowed`, `benchmark_only` | data runs |
| `mmz.licence` | SPDX-like id from the register | data runs |
| `mmz.superseded_by` | run id | data runs |
| `mmz.git_commit` | 40-hex | runs |
| `mmz.git_clean` | `true`, `false` | runs |
| `mmz.hardware` | short host or board label, e.g. `dgx-spark`, `macbook-m3-pro`, `esp32s3` | runs |
| `mmz.benchmark` | benchmark version, e.g. `can-ids-v3` | evaluation runs |
| `mmz.training_set` | training set or dataset version | training runs |
| `mmz.model`, `mmz.model_version` | zoo model name and version, when known | runs, imports |
| `mmz.candidate` | candidate id (`c1`) | runs |
| `mmz.imported` | `true` | imported runs |
| `mmz.import_key` | `<model>@<version>` or `<benchmark>/decision` | imported runs |
| `mmz.spike` | `true` | spike runs (never benchmark results) |
| `mmz.input_unresolved` | `<id>@<version>` | runs |
| `mmz.offline_id` | 32-hex id of the offline log | synced offline runs |
| `mmz.offline_synced` | highest replayed `seq` | synced offline runs |

MLflow's own system tags (`mlflow.*`) are left as the client sets them. The guard removes `mlflow.source.name` when it points to a path outside the repository, and keeps only the repo-relative script.

## Params

- Keys match `^[a-z0-9_./-]{1,120}$`, flattened with `.` from the committed config file and command options.
- Values are numbers, booleans or strings of at most 120 characters with no line break and at most three spaces.
- Paths are stored repo-relative or as `$MMZ_DATA/...`, never as home-directory paths.

## Metrics

- Finite numbers only. Name pattern as for params.
- Data runs use `size_mb`, `files`, `count.<dimension>` and `dist.<dimension>.<value>`. Values are sanitised to the key pattern, for example `dist.attack_family.fuzzing`.

## Dataset inputs

`mlflow.entities.Dataset` with:

| Field | Value |
|---|---|
| `name` | `<id>@<version>` |
| `digest` | `sha256[:16]` |
| `source_type` | `zoo` |
| `source` | repository path of the manifest, freeze file or register |
| `profile` | JSON of the row's `counts` and `distribution` |

The context tag is `inventory`, `training` or `evaluation`. A dataset input carries no schema of the data.

## Artifacts (allow-list)

| File | From | Max |
|---|---|---|
| `profile.json` | `zoo data publish --profile` | 1 MB |
| `config/<name>.yaml` | copy of a committed file under `configs/` | 1 MB |
| `span_config.json` | span training output, with any `data/` paths reduced to the file name | 1 MB |
| `report.json` | Keras export report (`<model>.report.json`) | 1 MB |
| `export-config.json` | `config.json` of a picket-forest export (`benchmark`, `manifest_sha256`, `code_commit`, forest settings) | 1 MB |
| `summary.json`, `summary.md` | HIL bench | 1 MB |
| `quality.json`, `performance.json` | import of `zoo/models/*/results/*` | 1 MB |

Never allowed: model weights (`*.safetensors`, `*.bin`, `*.joblib`, `*.tflite`, `*.npz`, `*.keras`, `*.h5`), JSONL, chunk, snapshot, label or capture files, and anything under `data/` or `$MMZ_DATA` other than the files above.

## Principle XI

- The store never receives labels, teacher outputs or judgements from Claude, because no logged task uses Claude.
- No MLflow assistant, gateway or LLM judge is configured on the server or called by the wrapper, the offline writer or sync.
- `zoo tracking audit` flags any param or tag value containing `claude` in a labeler, teacher or judge position, for review.
