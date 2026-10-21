# Record formats: pace-cnn first release

## Benchmark manifest

`topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json`

```json
{
  "benchmark": "uci-har-v1",
  "datasets": [{"id": "uci-har", "licence": "CC-BY-4.0", "retrieved_at": "<ISO date>", "archive_sha256": "<hex>"}],
  "protocol": {
    "test": "official UCI HAR test split",
    "validation": "3 of the 21 training subjects, drawn with validation_seed",
    "validation_seed": 2026,
    "normalisation": "per channel, mean and std of the training subjects (validation excluded)",
    "window": {"samples": 128, "channels": 9, "rate_hz": 50, "overlap": 0.5},
    "headline_metrics": ["int8_macro_f1", "int8_accuracy"]
  },
  "splits": {
    "train":      {"subjects": 18, "windows": "<n>", "subjects_sha256": "<hex>", "data_sha256": "<hex>"},
    "validation": {"subjects": 3,  "windows": "<n>", "subjects_sha256": "<hex>", "data_sha256": "<hex>"},
    "test":       {"subjects": 9,  "windows": 2947,  "subjects_sha256": "<hex>", "data_sha256": "<hex>"}
  },
  "normalisation": {"mean": ["<9 floats>"], "std": ["<9 floats>"]},
  "frozen_at": "<ISO datetime>"
}
```

`subjects_sha256` hashes the sorted subject numbers, joined by commas. `data_sha256` hashes the float32 windows (C order) followed by the int64 labels.

## Criteria record

`configs/condition-monitoring/activity/pace-cnn-criteria.yaml`

```yaml
version: 1
date: <YYYY-MM-DD, before the first run>
rationale: Owner decisions of 2026-10-18 (spec 021, Clarifications).
benchmark: uci-har-v1
recipe: configs/condition-monitoring/activity/pace-cnn.yaml
seeds: {candidate: 0, spread: [1, 2, 3, 4]}
selection: none (model after the last epoch of the candidate seed)
success:
  - {id: S1, metric: int8_macro_f1, op: ">=", value: 0.90}
  - {id: S2, metric: int8_accuracy, op: ">=", value: 0.90}
  - {id: S3, metric: int8_f1_min_class, op: ">=", value: 0.80}
  - {id: S4, budgets_on_reference_board: true}
  - {id: S5, fact: transfer_tested, value: true}   # false for 0.1.0, so 0.1.0 is experimental
kill:
  - {id: K1, metric: int8_macro_f1, op: "<", value: 0.80}
  - {id: K2, difference: float_macro_f1 - int8_macro_f1, op: ">", value: 0.03}
  - {id: K3, budgets_exceeded_on_reference_board: true}
budgets: {flash_kb: 128, ram_kb: 32, latency_us: 100000, reference_hardware: "ESP32 (esp32-1, LilyGO LoRa32)"}
```

## Verdict

`topics/condition-monitoring/reports/pace-cnn/0.1.0/verdict.json`

```json
{
  "criteria_version": 1,
  "criteria": [{"id": "S1", "measured": 0.0, "threshold": ">= 0.90", "met": false}],
  "kill": {"fired": ["K1"], "outcome": "kill | none"},
  "status": "experimental",
  "reasons": ["S5 transfer to mobility data not tested"]
}
```

`status` is computed, never written by hand. A criterion whose evidence does not exist yet (for example S4 before the bench run) has `"measured": null, "met": false, "note": "not measured"`.

## Quality metric names

`zoo/models/pace-cnn/results/0.1.0/quality.json` follows `results.schema.json` (`kind: quality`). Names in order are in [data-model.md](../data-model.md#quality-results-results010qualityjson).

Class names in metric rows are the dataset's labels: `walking`, `walking_upstairs`, `walking_downstairs`, `sitting`, `standing`, `laying`.

Subject rows are never named after dataset subject numbers.

## Model footprint

Measured from the ELF of the bench firmware built for the board's target (`nm --size-sort -S` or the toolchain's equivalent).

| Part | Symbols | Counted in |
|---|---|---|
| Model constant data | `mi_model_pace_cnn` and the arrays it references (weights, bias, multipliers, shifts, layer table) | flash |
| Engine code | the int8 engine's functions reachable from `mi_invoke` | flash |
| Arena | pace-cnn's arena size from the QModel (`arena_bytes`) | RAM |
| Input and output | 1,152 B input window, 6 B scores | RAM |
| Engine static data | the engine's `.data` and `.bss` symbols | RAM |

`flash_kb` and `ram_kb` are the sums divided by 1,024 and rounded up to 0.1 KB. The shared bench arena (`MI_ZOO_ARENA_SIZE`) is not used, because it is the maximum over all compiled-in models. `flash_kb_image_*` and `ram_kb_image_*` report the whole firmware image as information.

## Performance metric names

`edge performance` writes rows with `origin` and `hardware`:

- **reference**: `flash_kb`, `ram_kb`, `latency_us` (esp32-1, `real_board`);
- **suffixed**: `latency_us_esp32_qemu` (`emulator`), `latency_us_esp8266` (`real_board`), `latency_us_host` (`simulator`), `flash_kb_image_esp32`, `ram_kb_image_esp32`;
- **bit-exactness on the board**: `device_bit_exact_vectors`.

`latency_us` is the mean over at least 100 inferences. `n_items` gives the count.

## Example format `pace-cnn-v1`

```json
{
  "format": "pace-cnn-v1",
  "source": "synthetic",
  "generator": {"name": "uniform-int8", "version": 1, "seed": 0},
  "input": ["<1152 int8 values, row-major 128 x 9, channel order of config.json>"],
  "expected": ["<6 int8 scores in label order>"]
}
```

JSON schema: `src/mobility_model_zoo/condition_monitoring/activity/pace-cnn-v1.schema.json`. Field meanings for the site: `zoo/formats/pace-cnn-v1.yaml` (check B5 requires both).
