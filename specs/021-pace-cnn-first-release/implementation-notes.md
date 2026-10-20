# Implementation notes: feature 021

Running notes for the PR description. Findings that change a plan or contract are also recorded in research.md.

## Baseline before this feature (T001, 2026-10-20)

Environment: `uv sync --extra edge --extra edge-train --extra edge-hw` (TensorFlow 2.21.0, Keras 3.15.1, numpy 2.5.3). The sync removes the packages of other extras.

`uv run pytest tests/condition_monitoring tests/edge tests/release tests/compliance tests/unit/test_task_configs.py -n 8` on `main` 60f338b:

- **Result**: 508 passed, 1 failed, 9 skipped.
- **`tests/compliance/test_recall.py::test_combined_recall_meets_d9`** fails with `ModuleNotFoundError: dotenv`. The module belongs to the productdev extra, which this environment does not install; it is unrelated to this feature.
- **Flaky under parallel load, pass when run serially**:
  - `tests/edge/int8/test_keras_export.py::test_export_writes_bit_exact_model_outside_the_repo[False]` (accuracy 0.75 against a 0.8 floor on toy data);
  - `tests/edge/bench/test_device_session.py::test_hang_is_recovered_by_reset` (timing).

## Dataset (T002)

- `uv run zoo data download uci-har`: licence check passed (CC BY 4.0), retrieved 2026-10-20T06:26:17Z, archive SHA-256 `c00b8030…1031`, 61,005,872 bytes.
- **Deviation from contracts/records.md**: `SOURCE.json` has no `archive_sha256` field. The archive hash is `files[0].sha256`, and the manifest takes it from there.
- **Layout**: `extracted/UCI HAR Dataset/UCI HAR Dataset/{train,test}/`, with 7,352 training windows and 2,947 test windows.

## US1 code (T004–T028, 2026-10-20)

- **Reproduction compares parameters, not file hashes** (deviation from research R4): `QModel.save` stores the `meta` block, including `trained_at`, inside the `.npz`. The file hash therefore differs between two runs even when every weight is identical. `reproduce` compares `weights_sha256`, which hashes the model's parameters and quantisation header without `meta`. The run report records both hashes.
- **Refusal order**: `train` checks for the frozen manifest before it reads the recipe config, so a missing benchmark always exits 3.
- **Flaky existing test**: `test_export_writes_bit_exact_model_outside_the_repo[False]` failed once in three runs even serially (accuracy 0.71 against a 0.8 floor on toy data). It calls `fit` directly without op determinism. It was already flaky in the baseline, and CI skips it because TensorFlow is not installed there.
- **Freeze on the real data (T019)**: 18/3/9 subjects with 6,288/1,064/2,947 windows; the second run changed nothing, and the manifest contains no integer lists.
- **Parallel build race (existing)**: `tests/edge/bench/test_measure.py::test_measure_custom_model_via_edge_models_env` fails under `pytest -n 8` when several bench tests build the native firmware at once. It passes serially, and all 44 bench tests pass serially; this feature does not change the bench code.
- **Owner decisions (2026-10-20)**: the pre-registration commit of everything so far on the branch (no push). Input preparation: median filter of 3 samples, 3rd-order gravity filter, causal filters (research R11).
