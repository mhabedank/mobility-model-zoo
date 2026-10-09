# Data model: picket-forest 0.1.0

## Benchmark manifest (`topics/security/benchmarks/can-ids-v1/manifest.json`)

| Field | Content |
|---|---|
| `benchmark` | `can-ids-v1` |
| `frozen_at` | ISO date of the freeze |
| `datasets` | `[{id, version_or_revision, licence, retrieved_at}]` from each dataset's `SOURCE.json` |
| `protocol` | episode gap 1.0 s, grace 1.0 s, budgets `[1, 10]` false alarms per hour, benign keep share 0.1, seed 0, validation rule (highest-numbered capture per attack type in `train_01`), fixed frame FPR for recall (0.001) |
| `captures[]` | `{id, dataset, set, split, vehicle, attack_family, role (train/validation/test/out_of_scope), frames, attack_frames, episodes, duration_s, sha256}` |
| `resolutions_sha256` | hash of `resolutions.yaml` |

Rules:

- `sha256` is the hash of the capture in the common frame format, without the `capture` and `vehicle` columns.
- `captures[].id` is unique.
- No frame, payload or timestamp list is ever stored.
- Freezing twice on the same files gives a byte-identical manifest (SC-001).
- A frozen manifest never changes. A change makes `can-ids-v2`.

## Duplicate resolution (`topics/security/benchmarks/can-ids-v1/resolutions.yaml`)

`resolutions: [{sha256, captures: [id…], labels_seen: {vehicle: […], split: […]}, action: keep|drop|relabel, keep: id|null, reason}]`

Freezing fails while any duplicate group spanning different labels has no entry.

## Detector run (data cache only)

`$MMZ_DATA/derived/can-ids-v1/runs/<detector>/<set>/`, holding:

- `scores/<split>.npz`, with per-capture float32 scores, or uint8 tree votes for forests;
- `run.json`:
  - `detector`, `version`, `code_commit`, `manifest_sha256`;
  - `threshold` and `threshold_source` (`validation`);
  - `alarm_rule`, `alarm_rule_source`;
  - training-data summary.

## Evaluation report (`topics/security/reports/picket-forest/can-ids-v1/`)

- **`report.md`**: human-readable; headline tables, controls, baselines, per attack family, ROAD, out-of-scope section, limitations.
- **`metrics.json`**:
  - per detector × set × split: headline (detection share at budgets 1 and 10, median and p95 time to alarm), secondary (attack-class P, R, F1, AUC-PR, MCC per attack family; recall at the fixed frame FPR; false alarms per hour of the default rule);
  - aggregates: median over sets and worst set.
- Both carry `manifest_sha256` and `code_commit`.

## Quality and performance results (`zoo/models/picket-forest/results/0.1.0/`)

- **`quality.json`** (results schema):
  - every metric has `reference: "can-train-and-test labels (official splits)"` or `"ROAD injection labels"`, `benchmark: can-ids-v1` and `n_items` (captures or episodes);
  - names follow `<metric>_<split>`, for example `episode_detection_fa1_unknown_vehicle_median`, `f1_attack_unknown_vehicle_worst`.
- **`performance.json`**: `latency_us`, `flash_kb`, `ram_kb` (gate rule 15), each with `hardware` and `origin`, plus `latency_p99_us` and `state_bytes`.

## Tree-model example (`zoo/models/picket-forest/examples/*.json`)

```json
{
  "source": "synthetic",
  "generator": {"name": "picket-synth", "version": 1, "seed": 3, "attack": "fabrication"},
  "frames": [[ts_us, can_id, dlc, [b0, b1, b2, b3, b4, b5, b6, b7]], …],
  "expected_scores": [float32 as hex bit pattern, …],
  "expected_alarms": [frame_index, …]
}
```

Rules:

- `len(expected_scores) == len(frames)`.
- Scores are stored as 8-digit hex IEEE-754 bit patterns, for exact comparison.
- `source` is `synthetic` or a declared dataset id with `redistribution: allowed`.
- There are at least three examples, covering different attack families.

## Model (`zoo/models/picket-forest/model.yaml`), change

- New optional field `engine`: `int8` (default) or `emlearn`; only with `runtime: mcu`.
- `picket-forest` sets `engine: emlearn`.

## Release record, change

- Staged `files[]`:
  - `picket_forest_model.h`;
  - `picket_forest_config.h`;
  - `model.joblib`;
  - `config.json`;
  - `c/picket_forest.{c,h}`, `c/msml_can_features.{c,h}`, `c/msml_alarm.{c,h}`;
  - `sbom.cdx.json` (CycloneDX: the source files with SHA-256, the emlearn and scikit-learn versions).

## Release compliance record, change

The release-compliance schema gets two optional fields, which compliance check C-G4 already expects but the schema did not allow:

- `runtime`: `python` or `mcu`;
- `sbom`: the path of the staged SBOM, for example `sbom.cdx.json`. It is required when `runtime` is `mcu`.
- `evaluation`: `benchmark: can-ids-v1`, `reference_kind: ground_truth`.
- `performance.budget`: `{ram_kb: 16, flash_kb: 128, target: ESP32-S3}`.
