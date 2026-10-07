# Contract: release format for edge models

Changes to the zoo release format (feature 003) so that microcontroller models can be released. All changes are additive or widen a constraint; every existing model and release record stays valid. The changed schema files are copied to this folder during implementation, and `tests/release/test_schemas.py` compares the packaged schemas with the copies here (previously `specs/003-model-zoo-hf-release/contracts/`).

## `topics.schema.json`

- `id`: pattern `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, `maxLength: 24` (was `^[a-z][a-z0-9]{1,15}$`).

## `model.schema.json`

| Field | Change |
|---|---|
| `topic` | same pattern as topic `id` |
| `runtime` | new, optional, enum `python` (default), `mcu` |
| `languages` | `minItems: 0`; the gate requires at least one language when `runtime` is `python` |
| `base_model`, `base_model_license` | both null allowed for any topic; then the card says "trained from scratch" |
| `card.how_to_run` | `{text}` required only when `runtime` is `python` (gate rule 1, conditional) |
| `card.device_usage` | new, optional, required for `mcu`: a C snippet showing how to call the model on a device; may use `{repo_id}` and `{revision}` |
| `card.figures[].path` | pattern `^(docs|topics)/[a-z0-9/_.-]+\.png$` |

## `release-record.schema.json`

| Field | Change |
|---|---|
| `performance.budget` | `oneOf`: `{ram_gb > 0, gpu: false}` (python) or `{ram_kb > 0, flash_kb > 0, target: string}` (mcu) |
| `provenance.sources[].dataset` | new, optional: id of a dataset declaration in `topics/<topic>/datasets.yaml` |
| `evaluation.reference_kind` | new, optional, enum `model_consensus` (default), `ground_truth` |

## `results.schema.json`

| Field | Change |
|---|---|
| `metrics[].origin` | new, optional, enum `real_board`, `emulator`, `simulator`, `host` |
| `metrics[].name` | the ban on "accuracy" moves from the schema to gate rule 10, which applies it only to `model_consensus` |

## `datasets.schema.json` (new)

See [data-model.md](../data-model.md), "Dataset declaration".

## Gate rules

| # | Change |
|---|---|
| 1 | conditional checks: `languages` non-empty for python; `{text}` in `how_to_run` for python; `device_usage` present for mcu; budget variant matches `runtime` |
| 6 | for every source with `dataset`: the declaration exists, its license equals the source license, `permitted_use` is `training_allowed`, `status` is `active`; if any source license is share-alike (`CC-BY-SA-*`), the model license equals it; a non-commercial license (`*-NC-*`) as a training source fails |
| 7 | unchanged (`training_allowed` only) |
| 10 | quality sentence: `model_consensus` keeps the fixed agreement sentence and the "accuracy" ban; `ground_truth` requires the sentence "Quality is measured against the labels of the datasets named below, on test data not used for training." and allows "accuracy" |
| 12 | `mcu`: instead of running the Python snippet, load the staged int8 model with the host reference and run the first example |
| 13 | `mcu`: examples are `examples/*.json` with `input` (int8 vector) and `expected` (output); each must match bit-exactly on the host reference; at least 3 |
| 15 (new) | device evidence for `mcu`: performance metrics include `flash_kb`, `ram_kb` and `latency_us` with `origin` and `hardware`; unless `status` is `experimental`, at least one `latency_us` has `origin: real_board` |

## Model card template

- Front matter: `runtime: mcu` adds the tags `tinyml`, `microcontroller` and the target names.
- "How to run it": python unchanged; mcu shows the Python host reference (install line plus snippet) and the C usage from `card.device_usage`.
- "Speed and memory": python unchanged; mcu: "Budget: {ram_kb} KB RAM, {flash_kb} KB flash on {target}." and a table with an "Measured on" column showing hardware and origin (real board, emulator, simulator).
- "Quality": sentence per `reference_kind` (rule 10).
- "Provenance": for sources with `dataset`, the table lists dataset, provider, license and attribution; the fixed text says the dataset is not redistributed with the model and links the provider.
