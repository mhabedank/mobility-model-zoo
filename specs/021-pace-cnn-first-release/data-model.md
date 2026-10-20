# Data model: pace-cnn first release

Entities of feature 021. Exact field formats are in [contracts/records.md](contracts/records.md); this file names each entity, its fields, rules and transitions. "New" marks entities this feature introduces.

## Benchmark manifest `uci-har-v1` (new)

Path: `topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json`. Written by `condmon activity freeze`.

| Field | Meaning |
|---|---|
| `benchmark` | `uci-har-v1` |
| `datasets[]` | `id` (`uci-har`), `licence`, `retrieved_at`, `archive_sha256` from `SOURCE.json` |
| `protocol` | split source (official train/test), validation rule (`3 of 21 training subjects`), `validation_seed` (2026), normalisation rule (training subjects only), window (128 × 9, 50 Hz), metrics (headline `int8_macro_f1`, `int8_accuracy`) |
| `splits.{train,validation,test}` | `subjects` (count), `windows` (count), `subjects_sha256` (SHA-256 of the sorted subject list), `data_sha256` (SHA-256 of the split's windows and labels) |
| `normalisation` | `mean[9]`, `std[9]` of the training subjects |
| `frozen_at` | date and time of the freeze |

Rules:

- No subject numbers appear in the manifest (FR-028).
- Re-running `freeze` rebuilds the manifest. Identical content (ignoring `frozen_at`) changes nothing; any difference is refused with exit code 3 (`FrozenChanged`).
- `train` and `evaluate` refuse to run without the manifest and check `data_sha256` before they use a split.

Transitions: absent → frozen. A frozen manifest never changes, and a new definition is `uci-har-v2`.

## Criteria record (new)

Path: `configs/condition-monitoring/activity/pace-cnn-criteria.yaml`.

| Field | Meaning |
|---|---|
| `version`, `date`, `rationale` | Record version and why it was written or amended |
| `benchmark` | `uci-har-v1` |
| `recipe` | path of the recipe config (`configs/condition-monitoring/activity/pace-cnn.yaml`) |
| `seeds` | `candidate: 0`, `spread: [1, 2, 3, 4]` |
| `selection` | `none: model after the last epoch of the candidate seed` |
| `success` | thresholds of FR-019, each with id, metric, operator and value; plus `budgets_on_reference_board: true` and `transfer_tested` (a boolean fact, false for 0.1.0) |
| `kill` | kill criteria of FR-009, each with id, metric or difference, operator and value |
| `budgets` | `flash_kb: 128`, `ram_kb: 32`, `latency_us: 100000`, `reference_hardware: ESP32 (esp32-1)` |
| `amends` | previous version and reason, only for an amendment |

Rules:

- `train` refuses to run if the file is untracked or differs from `HEAD`. The run report records its commit and SHA-256.
- An amendment after any result has been seen needs a new `version` with `rationale`, and the evaluation report names the version it used.

## Run report (extends `pace-cnn.report.json`)

One per training run, in `$MMZ_DATA/derived/pace-cnn/seed-<n>/` (outside git).

Fields added to today's report:

- `seed`, `benchmark`, `manifest_sha256`, `criteria_version`, `criteria_sha256`, `criteria_commit`;
- `git_commit` and `dirty` (bool);
- `tensorflow`, `keras`, `platform`;
- `npz_sha256`;
- `validation` metrics (informative);
- `tflite_interpreter_mismatches` over all test windows.

## Evaluation report (new)

Path: `topics/condition-monitoring/reports/pace-cnn/0.1.0/` (in git, public).

| File | Content |
|---|---|
| `evaluation.json` | evaluated model file (`model_sha256` of the seed-0 `.npz`); `runs[]` with `seed`, `manifest_sha256`, `criteria_version`, `criteria_commit`, `npz_sha256`, `trained_at` per run (R21, R22); metrics of the candidate on the test split; per-class F1; confusion matrix (6 × 6, rows = dataset label); per-subject macro-F1 as a list sorted ascending, without subject numbers; seed spread; validation results; preparation fidelity check (R11) |
| `verdict.json` | each success and kill criterion with measured value, threshold and `met` (bool); kill outcome; derived `status` |
| `README.md` | short human summary, generated from both files |

The rules for this report:

- Values are int8 results on the bit-exact host reference unless the name starts with `float_`.
- `verdict.status` is `released` only if every success criterion is met and no kill criterion fires. Otherwise it is `experimental`, which is always the case for 0.1.0.

## Quality results `results/0.1.0/quality.json`

Path: `zoo/models/pace-cnn/results/0.1.0/quality.json`. Schema: `src/mobility_model_zoo/release/schemas/results.schema.json` (`kind: quality`).

Metric rows, in this order (the card's version history shows the first three):

`int8_macro_f1`, `int8_accuracy`, `int8_f1_min_class`, `int8_f1_<class>` ×6, `int8_macro_f1_worst_subject`, `int8_macro_f1_subject_range`, `int8_macro_f1_seed_min`, `int8_macro_f1_seed_mean`, `int8_macro_f1_seed_max`, `float_macro_f1`, `float_accuracy`, `tflite_interpreter_mismatches`.

Every row carries:

- `reference: labels of the uci-har dataset`;
- `benchmark: uci-har-v1`;
- `n_items` (2,947 test windows; 9 subjects for subject rows; 5 runs for seed rows);
- `hardware: host (bit-exact int8 reference)`, and `date`.

## Performance results `results/0.1.0/performance.json`

Schema as above (`kind: performance`). Written by `edge performance`.

| Rows | Origin | Board |
|---|---|---|
| `flash_kb`, `ram_kb`, `latency_us` | `real_board` | esp32-1 (reference) |
| `flash_kb_image_esp32`, `ram_kb_image_esp32` | `real_board` | esp32-1, whole firmware image, informative |
| `latency_us_esp32_qemu` | `emulator` | ESP32 QEMU |
| `latency_us_esp8266` | `real_board` | esp8266-1, informative |
| `latency_us_host` | `simulator` | host build of the bench firmware |
| `device_bit_exact_vectors` | `real_board` | esp32-1: share of examples and test vectors equal to the host reference |

If esp32-1 cannot be measured, the plain rows carry the emulator values with `origin: emulator`, and the card lists "budgets on the real reference board" as not measured (spec edge case).

## Model footprint (definition)

- **Flash**: the size of pace-cnn's constant model data plus the int8 engine functions it calls.
- **RAM**: pace-cnn's arena plus the input buffer (1,152 B) and output buffer (6 B) plus the engine's static data.

Both are read from the symbol sizes of the ELF built for the board's target. Details: [contracts/records.md](contracts/records.md#model-footprint).

## Release record `zoo/models/pace-cnn/releases/0.1.0.yaml` (changed)

- **Fields that change**:
  - `date` and `changes`, which give the first release text;
  - `files[]` and `staging.revision`, filled by `zoo stage`;
  - `recipe.git_commit`, the commit of the freeze, criteria and recipe;
  - `provenance.sources[0].count`, the number of training windows;
  - `performance.hardware: ESP32 (LilyGO LoRa32, HIL bench)` and `performance.budget.target: ESP32`.
- **Fields that stay**: `status: experimental`, `evaluation.benchmark: uci-har-v1`, `evaluation.reference_kind: ground_truth`, `usage.class: commercial`, `licence: Apache-2.0`.
- **Transitions**: draft (`files: []`) → staged → verified (release-verify) → published (`published` block written by release-publish). After publication it is immutable.

## Model record `zoo/models/pace-cnn/model.yaml` (changed)

The `card` block changes:

- `intended_use`;
- `out_of_scope` and `not_for` (reworded for lint C-C2, with the AI Act uses);
- `input_output`, the input contract of R11;
- `how_to_run`, with a synthetic example and a stated purpose;
- `device_usage`, matching the shipped `c/` headers;
- `limitations` and `limits_short`;
- `unmet_criteria`, taken from `verdict.json`;
- `card_privacy_note`.

Rule 18 allows at most five items for `unmet_criteria` and `limits_short` together.

## Examples `examples/*.json` (new, uploaded)

At least three files in format `pace-cnn-v1`:

| Field | Content |
|---|---|
| `source` | `synthetic` |
| `generator` | `name`, `version`, `seed` |
| `input` | 1,152 int8 values, row-major 128 × 9 |
| `expected` | 6 int8 scores in class order |

Their schema is `src/mobility_model_zoo/condition_monitoring/activity/pace-cnn-v1.schema.json`, and the field meanings for the website are in `zoo/formats/pace-cnn-v1.yaml`.

## Release config `config.json` (new, uploaded)

It holds `labels` (class order), `input` (window 128, channels 9 with names and units, sample rate 50 Hz, overlap 0.5), `normalisation` (mean and std per channel), `quantisation` (input scale and zero point), `preparation` (filter steps and parameters as in R11) and `format: pace-cnn-v1`.

## Compliance record `zoo/models/pace-cnn/releases/0.1.0.compliance.yaml` (new)

Created and rendered by the compliance harness. Signoff `state` is set by the owner.

## Dataset declaration `uci-har` (changed)

`used_by: [pace-cnn@0.1.0]`. `redistribution` stays `unclear`, because no dataset content is published.

## Topic `condition-monitoring` in `zoo/topics.yaml` (changed)

`hf_collection`: null → slug, set by `zoo init-model`. The collection is created private and becomes public at the first publish.

## Roadmap entry `pace-cnn`

Unchanged in `zoo/roadmap/roadmap.yaml`. It counts as delivered once version 0.1.0 has a `published` block (`site/roadmap.py`).
