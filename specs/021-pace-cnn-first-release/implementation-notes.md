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

## US2 code (T030–T046, 2026-10-20)

- **No CI rule needed for `release/sbom.py`** (T042): `select_tests.py --files src/mobility_model_zoo/release/sbom.py` falls under the area `core`, which selects all tests including `tests/security`.
- **Mean latency** (deviation from contracts/records.md): `edge measure` reports `latency_us` as the median of the samples (unchanged, as picket-forest and gate rule 15 use it). It now also writes `latency_mean_us`, and the verdict's budget criteria S4 and K3 use the mean, as FR-014 budgets the average time per window. `edge measure` also writes `device_bit_exact_vectors` (device SELFTEST).
- **Footprint on the host simulator**: the native build on macOS is a Mach-O binary without symbol sizes, so `--footprint model` falls back to the parameter estimate there and says so in the description. ESP32 and ESP8266 use the toolchain's `nm` on the ELF.
- **Examples = self-test vectors**: the release examples are the first three QModel test vectors (uniform int8, seed 0), so the board's SELFTEST covers them. The exported C sources, compiled on the host with `-Wall -Werror`, reproduce all three bit for bit.

## US3 code (T051–T069, 2026-10-20)

- **Compliance schema contract copy moved to feature 021**: `tests/compliance/test_register_schemas.py` compares the packaged compliance schemas with the copy of the latest owning feature. The copy now lives in `specs/021-pace-cnn-first-release/contracts/compliance/`; the 011 copy stays as that feature's record. A new rule in `scripts/ci/select_tests.py` runs the compliance tests when a contract copy changes, as for the release schemas.
- **`model_family` is required on every route** (R21); the test helper route got `local-test`.
- **Card wording for datasets**: the training-data section, the teacher section ("None" instead of an empty table) and the privacy sentence now distinguish datasets from texts. scout-large 0.1.3 renders byte-identically; picket-forest's re-rendered card loses the empty teacher table and the text wording (published cards are unaffected, `audit` compares hashes only).
- **Regression (T065)**: rules 7 and 9 pass offline for scout-large 0.1.3, picket-forest 0.2.0 and 0.2.1 (scout-large: "Claude only claude-consumer-cli as frozen benchmark reference (D-claude-risk-0.1.x)"). Rule 16 fails for picket-forest 0.2.0 (card changed since the scan) and 0.2.1 (scan report missing), both already before this feature's card change.
- **"Hung" test runs were the Mac sleeping**: several runs stalled for 10–30 minutes and then passed in about 2 minutes. The power log (`pmset -g log`) shows repeated Maintenance Sleep and DarkWake cycles on 2026-10-20, during which every process stops. Long runs now use `caffeinate -i`, which only holds off idle sleep while the command runs.
- **Formatting slip, reverted**: `ruff format` was once run on the whole package and on whole test folders, which reformatted 31 files of other areas (productdev, catalog, five compliance tests, `scripts/ci/select_tests.py`). All were restored with `git checkout`, and only the intended two-line rule in `select_tests.py` was applied again. Formatting is now run on this feature's files only.
- **Card content (T066–T071)**: `uci-har` `used_by: [pace-cnn@0.1.0]`. Card block written from `quality.json` (prose values formatted with `cards.num`, as in the tables). `unmet_criteria` lists S5 (not tested) and S4 ("not measured yet"); S4 must be updated from the verdict after the board measurement (T050). The compliance record is `state: draft` until the owner's signoff.
- **Card needs performance.json**: the card does not render without device results. `test_card_contents.py` skips until T049. A dry run with a temporary performance file from the host simulator (removed afterwards) gave: 8 of 9 card tests pass (the ninth expects real-board or emulator rows); card lint C-C1/C-C2 clean after two fixes (copyright policy link in the dataset block; out-of-scope wording without "safety function"); offline gate rules 2–4, 6–11, 13–15, 17, 18 pass, rule 7 "no Claude inputs", rule 9 "5 runs on frozen uci-har-v1, criteria committed before the first run"; open as expected: rule 1 (not staged) and rule 16 (scan and signoff).
