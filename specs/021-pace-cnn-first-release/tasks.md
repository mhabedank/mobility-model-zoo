---

description: "Task list for feature 021: pace-cnn first release"
---

# Tasks: pace-cnn first release (activity recognition on a microcontroller)

**Input**: Design documents from `specs/021-pace-cnn-first-release/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R22), data-model.md, contracts/ (cli.md, records.md, release-files.md), quickstart.md (V1–V13)

**Tests**: Included. The plan names the test files per area (plan.md, Project Structure: `tests/condition_monitoring/`, `tests/edge/`, `tests/release/`, `tests/compliance/`). Within each story, write the tests first and confirm they fail before the implementation.

**Organization**: Tasks are grouped by user story. US1 gives the measured candidate and its verdict, US2 the device evidence, US3 the publication.

**Revision**: 2026-10-20, after `/speckit-analyze`. The new tasks T055–T057 and T062–T065 cover the gate check for no Claude inputs (R21) and the benchmark trace (R22). T003, T007, T008, T012, T014, T016, T025, T026, T061, T068, T072 and T073 are sharpened. The other tasks are renumbered.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2 or US3 (spec.md user stories)
- **Owner** marks a step only the owner can do (research R18). Claude prepares it and waits.

## Rules for every task

- **Principle XI**: Claude writes code and runs the pre-registered commands only. Claude never picks a seed, epoch, setting, threshold, filter parameter or candidate by looking at results, and never writes labels or data.
- **Test subjects**: the test split is used only by `evaluate` and by the interpreter check inside `train`. It never feeds training, early stopping, thresholds or choices (FR-004). Recomputing the same evaluation deterministically is allowed and is not a new evaluation.
- **Fidelity check**: the fidelity result of the input preparation is informative. It never changes a filter parameter (R11).
- **No dataset content in public files**: no subject numbers, no dataset windows and no local paths in git, reports or release files (FR-023, FR-028). `$MMZ_DATA` stays outside the repository.
- **Pre-zoo report**: the numbers in `topics/condition-monitoring/reports/pace-cnn/research-report.json` (for example 93.3 %) never set a threshold, feed a gate or appear on the card (SC-007).
- **Commits**: the pre-registration must be committed before the first run (FR-007). Ask the owner before each commit or push if no standing approval exists.

## Path Conventions

Single Python package. Source code is in `src/mobility_model_zoo/`, tests in `tests/`, configuration in `configs/condition-monitoring/activity/`, topic material in `topics/condition-monitoring/`, records in `zoo/`, firmware in `firmware/bench/` and bench config in `hil/`. Note: the edge CLI lives in `src/mobility_model_zoo/edge/bench/cli.py` (the plan writes `edge/cli.py`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment, dataset and the facts the input preparation needs.

- [X] T001 Run `uv sync --extra edge --extra edge-train --extra edge-hw` and a baseline `uv run pytest tests/condition_monitoring tests/edge tests/release tests/compliance -q`. Write any failures that exist before this feature into the PR description, so they are not mistaken for regressions.
- [X] T002 Download the dataset with `uv run zoo data download uci-har` into `$MMZ_DATA` (FR-005). Confirm the licence check passes and that `$MMZ_DATA/uci-har/SOURCE.json` holds `retrieved_at` and the archive SHA-256. If the declared licence differs, the download fails closed: stop and report it to the owner (spec edge case).
- [X] T003 Read `README.txt` and `features_info.txt` of the downloaded copy and, where they leave a value open, the dataset paper (Anguita et al., ESANN 2013). Append a subsection "Verified after download" to R11 in `specs/021-pace-cnn-first-release/research.md` with:
  - the units of `total_acc`, `body_acc` and `body_gyro`;
  - the noise filters with type, order and cut-off;
  - the type, order and cut-off of the gravity filter.

  Every value is fixed here, before T025. If the documentation and the paper both leave a value open, ask the owner and record the decision with its date in R11. Copy facts only, no dataset content.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Subject-aware data loading, a shared test fixture, and the benchmark definition in the task document. FR-003 requires the task document to be updated before the freeze.

**⚠️ CRITICAL**: No user story work starts before this phase is complete.

- [X] T004 [P] Add a synthetic UCI HAR tree fixture in `tests/condition_monitoring/conftest.py`. It extends the `_split` helper of `tests/condition_monitoring/test_activity_train.py` and writes:
  - 21 training subjects and 9 test subjects, 2 to 3 windows each, all random values;
  - `subject_train.txt`, `subject_test.txt`, `y_*.txt`, the nine `Inertial Signals` files per split;
  - a `SOURCE.json` with `retrieved_at` and `archive_sha256`.

  Switch `test_activity_train.py` to the fixture.
- [X] T005 Extend `load_har()` in `src/mobility_model_zoo/condition_monitoring/activity/train.py` to read `subject_train.txt` and `subject_test.txt`. It returns the subject number per window next to `x` and `y`, and its callers are adapted. Add a test to `tests/condition_monitoring/test_activity_train.py`: the subject arrays have one entry per window, and the test subjects do not overlap the training subjects.
- [X] T006 [P] Update `topics/condition-monitoring/tasks/activity.md`:
  - **Benchmark `uci-har-v1`** (FR-003, R1): official test split (9 of 30 subjects, 2,947 windows); validation is 3 of the 21 training subjects drawn once with `validation_seed` 2026; normalisation from the 18 remaining training subjects only; the manifest records counts and SHA-256 values, never subject numbers.
  - **Metrics**: add per-class F1, worst test subject, subject range and seed spread (R5).
  - **Hardware budget**: reference hardware is ESP32 classic, `esp32-1` (LilyGO LoRa32, 240 MHz), instead of ESP32-S3 (FR-015). Budgets are ≤ 128 KB flash and ≤ 32 KB RAM for the model with its working memory, and ≤ 100 ms average per window on the reference board (FR-014).
  - **Criteria**: point to `configs/condition-monitoring/activity/pace-cnn-criteria.yaml`.
- [X] T007 Put the split values in one place, `src/mobility_model_zoo/condition_monitoring/activity/train.py` (R1):
  - add a constant `BENCHMARK` with `id: uci-har-v1`, `validation_seed: 2026` and the validation rule "a seventh of the training subjects" (3 of 21);
  - no other file holds these values as data.

  Update the wording in the same change in two places, because `load_config` in `src/mobility_model_zoo/edge/int8/keras_export.py` refuses any difference between them:
  - `data.validation` and `data.normalisation` in `configs/condition-monitoring/activity/pace-cnn.yaml`;
  - `FIXED["data"]` in the same `train.py`.

  Use "3 of the 21 training subjects, drawn with validation_seed 2026" and "per channel, mean and std of the training subjects (validation excluded)". Confirm that `uv run pytest tests/unit/test_task_configs.py` passes.

**Checkpoint**: Subjects are loadable, the benchmark is defined in the task document, and the split values have a single source.

---

## Phase 3: User Story 1 - A measured candidate with an honest verdict (Priority: P1) 🎯 MVP

**Goal**: Freeze `uci-har-v1`, commit the criteria, train five pre-registered seeds, evaluate the int8 candidate once on the test subjects and derive the status by rule.

**Independent Test**: `condmon activity freeze`, the five `train` runs and `evaluate --version 0.1.0` on a fresh download produce `quality.json`, `evaluation.json` and `verdict.json`. They name `uci-har-v1` and hold the int8 headline metrics, per-class and per-subject results, the seed spread, the deterministic check and the status (quickstart V1–V5).

### Tests for User Story 1 ⚠️

> Write these tests first and confirm they fail before the implementation.

- [X] T008 [P] [US1] Write `tests/condition_monitoring/test_activity_benchmark.py` on the T004 fixture. It covers:
  - the first freeze writes `manifest.json` with 18/3/9 subjects and the fields of contracts/records.md;
  - a second freeze leaves the file byte-identical, exit 0;
  - with `BENCHMARK["validation_seed"]` patched by `monkeypatch`, a new freeze raises `FrozenChanged`, CLI exit 3, and prints the differing fields (quickstart V1);
  - a missing dataset gives exit 4 and writes nothing;
  - "No subject numbers appear in the manifest (FR-028)": no list of subject ids anywhere, and `subjects` fields are counts;
  - `subjects_sha256` hashes "the sorted subject numbers, joined by commas" and `data_sha256` hashes "the float32 windows (C order) followed by the int64 labels".
- [X] T009 [P] [US1] Write `tests/condition_monitoring/test_subject_split.py`. It covers:
  - validation is drawn by whole subjects with seed 2026, and the number of validation subjects is a seventh of the training subjects (3 of 21);
  - no subject is in two splits;
  - normalisation `mean[9]` and `std[9]` come from the training subjects only, with validation excluded;
  - `make_task` refuses a split whose `data_sha256` differs from the manifest.
- [X] T010 [P] [US1] Write `tests/condition_monitoring/test_criteria.py`. Use a temporary git repository and stub out training. `condmon activity train` exits 3 in each of these cases:
  - no frozen manifest;
  - the criteria file is untracked;
  - the criteria file differs from `HEAD`;
  - `--seed` is not in `seeds.candidate` or `seeds.spread`.

  After a clean commit, the run report records `criteria_version`, `criteria_sha256` and `criteria_commit`. `--epochs` is rejected for `activity`, while `sound-anomaly` keeps it.
- [X] T011 [P] [US1] Extend `tests/edge/int8/test_keras_export.py` and `tests/edge/int8/test_tflite_import.py`; the TensorFlow tests use `importorskip`.
  - `verify_with_interpreter` accepts explicit inputs and counts mismatches over all of them.
  - The run report has the fields of data-model.md "Run report": `seed`, `benchmark`, `manifest_sha256`, `criteria_*`, `git_commit`, `dirty`, `tensorflow`, `keras`, `platform`, `npz_sha256`, `validation` and `tflite_interpreter_mismatches` over all test windows.
  - The default output folder is `derived/pace-cnn/seed-<n>/`.
- [X] T012 [P] [US1] Write `tests/condition_monitoring/test_prepare.py` for the input preparation host reference. It covers:
  - output windows are int8, shape 128 × 9, with 50 % overlap;
  - the channel order equals `SIGNALS`;
  - quantisation uses the model's input scale and zero point;
  - streaming in chunks gives the same windows as the whole stream, so filter state carries over;
  - the module imports with numpy only, and its filters match `scipy.signal.sosfilt` within float tolerance, run only when scipy is installed (`importorskip`);
  - the fidelity function returns RMSE and correlation per axis.
- [X] T013 [P] [US1] Write `tests/condition_monitoring/test_verdict.py` for the verdict rules of contracts/records.md "Verdict":
  - "`verdict.status` is `released` only if every success criterion is met and no kill criterion fires";
  - S5 `transfer_tested: false` always gives `experimental`;
  - S4 without `performance.json` gives `"measured": null, "met": false, "note": "not measured"`;
  - K1 (int8 macro-F1 < 0.80), K2 (float minus int8 macro-F1 > 0.03) and K3 fire correctly;
  - `reasons` lists every missed criterion with its value.
- [X] T014 [P] [US1] Write `tests/condition_monitoring/test_activity_evaluate.py` on fake run folders. Build small QModels without TensorFlow, as in the existing edge int8 tests. It covers:
  - `quality.json` validates against `src/mobility_model_zoo/release/schemas/results.schema.json` (`kind: quality`);
  - the metric rows appear in the order of data-model.md, and every row carries `reference: labels of the uci-har dataset`, `benchmark: uci-har-v1`, `n_items`, `hardware` and `date`;
  - per-subject results are a list sorted ascending, without subject numbers;
  - the confusion matrix is 6 × 6 and its rows are dataset labels;
  - `evaluation.json` holds `model_sha256` of the seed-0 `.npz` and `runs[]` with `seed`, `manifest_sha256`, `criteria_version`, `criteria_commit`, `npz_sha256` and `trained_at` for all five runs (R21, R22);
  - two runs give byte-identical files;
  - exit 3 when a run used another manifest or criteria version;
  - exit 4 when `tflite_interpreter_mismatches` > 0.
- [X] T015 [P] [US1] Update `tests/condition_monitoring/test_condmon_cli.py`. `sound-anomaly evaluate|freeze` still exit 5, while `activity freeze|evaluate|reproduce|export` are real commands. `test_train_reports_missing_dataset` no longer passes `--epochs` for `activity`.

### Implementation for User Story 1

- [X] T016 [US1] Create `src/mobility_model_zoo/condition_monitoring/benchmark.py` following the freeze pattern of `src/mobility_model_zoo/security/can_ids/benchmark.py:313`:
  - `build_manifest()` writes the format of contracts/records.md, with fields from `SOURCE.json` and the dataset declaration; the benchmark id, `validation_seed` and validation rule come from the caller (`BENCHMARK` of T007), never from a default in this module;
  - `split_subjects(subjects, validation_seed)`;
  - `freeze(path)` rebuilds, compares without `frozen_at` and raises `FrozenChanged` on any difference;
  - `verify_split(manifest, name, x, y)` checks `data_sha256`.

  Keep it free of activity-specific code where possible so `hum-fan` can reuse it within the topic (R1).
- [X] T017 [US1] Make `condmon activity freeze` real in `src/mobility_model_zoo/condition_monitoring/cli.py`. It exits 0 when written or unchanged, 3 on `FrozenChanged`, and 4 when the dataset is missing or the licence check fails. `sound-anomaly` keeps its exit-5 stubs; split `_task` so the two tasks can differ. Update the module docstring.
- [X] T018 [US1] Rewrite `make_task` in `src/mobility_model_zoo/condition_monitoring/activity/train.py`:
  - load the frozen manifest and refuse without it;
  - derive the validation subjects with `split_subjects` and the manifest's `validation_seed`;
  - check `data_sha256` of every split with `verify_split`;
  - normalise with the manifest's `normalisation` (training subjects only);
  - pass the test subjects on to the export only for the interpreter check.
- [X] T019 [US1] Run `uv run condmon activity freeze` twice (quickstart V1). Expect 18/3/9 subjects and 2,947 test windows, and the second run must change nothing. Check that `grep` finds no subject list in `topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json`. Commit the manifest together with T006 and T007.
- [X] T020 [US1] Write `configs/condition-monitoring/activity/pace-cnn-criteria.yaml` exactly as in contracts/records.md "Criteria record":
  - `version: 1`, `date` = the commit date (before the first run), `benchmark: uci-har-v1`;
  - `seeds: {candidate: 0, spread: [1, 2, 3, 4]}`;
  - `selection: none (model after the last epoch of the candidate seed)`;
  - success S1–S5, kill K1–K3;
  - `budgets: {flash_kb: 128, ram_kb: 32, latency_us: 100000, reference_hardware: "ESP32 (esp32-1, LilyGO LoRa32)"}`.

  Commit it before any training run (FR-007, Gate before an experiment).
- [X] T021 [US1] Add the pre-registration checks to `train_main` and `train` in `src/mobility_model_zoo/edge/int8/keras_export.py`, with new parameters for the criteria path and manifest path. Exit 3 when:
  - the manifest is missing;
  - the criteria file is untracked or differs from `HEAD` (`git ls-files`, `git diff --quiet HEAD -- <file>`);
  - the seed is not in the criteria seeds.

  Record `criteria_version`, `criteria_sha256` and `criteria_commit`. Add a per-task switch so `activity` drops `--epochs` (epochs come from the recipe config) and `sound-anomaly` keeps it. The default `--out` becomes `derived_dir(name) / f"seed-{seed}"`.
- [X] T022 [US1] Extend the run report in `src/mobility_model_zoo/edge/int8/keras_export.py`:
  - call `tf.config.experimental.enable_op_determinism()` next to `set_random_seed` (R4);
  - add `seed`, `benchmark` and `manifest_sha256`;
  - add `git_commit` and `dirty`;
  - add the `tensorflow` and `keras` versions and `platform`;
  - add `npz_sha256`;
  - add informative `validation` metrics (accuracy, macro-F1).

  Keep `pace-cnn.eval.npz` local; it is never uploaded.
- [X] T023 [P] [US1] Change `verify_with_interpreter` in `src/mobility_model_zoo/edge/int8/tflite_import.py:266` to take explicit int8 inputs. `export` in `keras_export.py` passes all quantised test windows (2,947) instead of `n=32` random inputs (R5, FR-011). Leave the QModel `test_inputs` as 8 synthetic vectors, so the `.npz` holds no dataset content.
- [X] T024 [US1] Validate the pre-registration (quickstart V2): with an uncommitted change to the criteria file, `uv run condmon activity train --seed 0` exits 3; revert the change. Then run exactly `for s in 0 1 2 3 4; do uv run condmon activity train --seed $s; done` (V3). Expect five `seed-<n>` folders under `$MMZ_DATA/derived/pace-cnn/`, each with `tflite_interpreter_mismatches: 0`. Do not look at the metrics to decide anything. If any run reports a mismatch, stop: it is a defect that blocks the release, not a status question.
- [X] T025 [US1] Create `src/mobility_model_zoo/condition_monitoring/activity/prepare.py`, the host reference of the input preparation (R11, FR-021). It turns a continuous raw stream (accelerometer, gyroscope, 50 Hz, units from T003) into int8 windows of 128 × 9 with 50 % overlap. The steps, all streaming:
  - the dataset's noise filters (T003);
  - gravity separation with a Butterworth low-pass at 0.3 Hz, order fixed in T003;
  - per-channel normalisation with the manifest constants;
  - int8 quantisation with the model's input scale and zero point.

  Implement the filters with numpy only, as second-order sections with filter state, because the `edge` extra the card installs has no scipy. Their coefficients are exported for `config.json` (T045). Add `fidelity(total_acc, body_acc)`, which returns RMSE and correlation per axis on the training subjects; it is informative, local only, and never changes a parameter.
- [X] T026 [US1] Create `src/mobility_model_zoo/condition_monitoring/activity/evaluate.py`. It runs the frozen test split through the int8 host reference of the seed-0 `.npz` (R5) and computes:
  - headline `int8_macro_f1` and `int8_accuracy`;
  - `int8_f1_min_class` and `int8_f1_<class>` ×6, with class names as in contracts/records.md;
  - `int8_macro_f1_worst_subject` and `int8_macro_f1_subject_range`;
  - `int8_macro_f1_seed_min|mean|max` over the five runs;
  - informative `float_macro_f1` and `float_accuracy`;
  - `tflite_interpreter_mismatches`.

  It writes:
  - `topics/condition-monitoring/reports/pace-cnn/<version>/evaluation.json`, which holds `model_sha256` of the evaluated seed-0 `.npz`, `runs[]` (seed, `manifest_sha256`, `criteria_version`, `criteria_commit`, `npz_sha256`, `trained_at` per run, from the run reports; R21, R22), the confusion matrix, per-subject macro-F1 sorted ascending (no subject numbers), validation results and the T025 fidelity check;
  - `verdict.json`, computed from the criteria file and never written by hand; S4 and K3 come from `zoo/models/pace-cnn/results/<version>/performance.json` if it exists, else they are "not measured";
  - a generated `README.md`;
  - `zoo/models/pace-cnn/results/<version>/quality.json`, with rows in the order of data-model.md.
- [X] T027 [US1] Make `condmon activity evaluate [--version 0.1.0]` real in `src/mobility_model_zoo/condition_monitoring/cli.py`. It prints the derived status and every missed criterion. Exits: 0 when the report is written, whatever the status; 3 when a run used another manifest or criteria version; 4 when the deterministic check reports a mismatch.
- [X] T028 [US1] Add `condmon activity reproduce` in `src/mobility_model_zoo/condition_monitoring/cli.py`, with its logic in `evaluate.py`. It retrains the candidate seed into a temporary folder and compares the `.npz` SHA-256. If the hashes differ, it compares the int8 metrics. The result (`identical`, or the deviation per metric) goes to `evaluation.json` under `reproduction` (FR-013). Exit 0 in both cases.
- [X] T029 [US1] Run `uv run condmon activity evaluate --version 0.1.0` twice (V4) and confirm identical files. Then run `uv run condmon activity reproduce` (V5) and run `evaluate` again so `evaluation.json` holds `reproduction`. Commit the reports and `quality.json`. If K1 or K2 fired, report the kill outcome to the owner: the quality claims it concerns are blocked, an `experimental` release stays possible, and a new iteration would need criteria `version: 2` with a rationale.

**Checkpoint**: The owner sees the first honest result (int8 headline metrics, per-class, worst subject, seed spread, verdict `experimental`). US1 is complete and testable on its own (SC-001, SC-008).

---

## Phase 4: User Story 2 - The model runs within budget on a real microcontroller (Priority: P2)

**Goal**: Run the trained candidate through the HIL bench on esp32-1 and measure the model's own flash, RAM and latency with their origin. Prove bit-exact board outputs and ship standalone C sources.

**Independent Test**: With `MMZ_EDGE_MODELS` pointing at `seed-0/pace-cnn.npz`, the bench suite passes on sim, ESP32 QEMU and esp32-1. `edge measure --footprint model` and `edge performance` write `performance.json` with `origin` per row. The exported `c/` sources compiled on the host reproduce the examples bit for bit (quickstart V6–V8).

**Dependency**: the code tasks T030–T045 need only Phase 2 and can run alongside US1. The measurements T046–T050 need the seed-0 run of T024.

### Tests for User Story 2 ⚠️

- [X] T030 [P] [US2] Extend `tests/edge/bench/test_models_zoo.py`. `load_eval(name)` finds `<name>.eval.npz` next to a model given in `MMZ_EDGE_MODELS` and in `derived/<name>/<name>.eval.npz`. The HIL catalogue helper returns the same models as `bench_models()`, including `MMZ_EDGE_MODELS`.
- [X] T031 [P] [US2] Write `tests/edge/bench/test_footprint.py` on a captured `nm --size-sort -S` text fixture. It checks the model footprint of contracts/records.md "Model footprint":
  - **flash** = `mi_model_pace_cnn` with its referenced arrays, plus the engine functions reachable from `mi_invoke`;
  - **RAM** = the QModel `arena_bytes` + 1,152 B input + 6 B output + the engine's `.data`/`.bss`;
  - "`flash_kb` and `ram_kb` are the sums divided by 1,024 and rounded up to 0.1 KB";
  - the whole image is reported under `flash_kb_image_*` and `ram_kb_image_*`.
- [X] T032 [P] [US2] Write `tests/edge/bench/test_performance_merge.py` for `edge performance`. It checks:
  - the reference file gives the plain names `flash_kb`, `ram_kb` and `latency_us`;
  - each `--extra` gives suffixed names (`latency_us_esp32_qemu`, `latency_us_esp8266`, `latency_us_host`, `flash_kb_image_esp32`, `ram_kb_image_esp32`);
  - `device_bit_exact_vectors` comes from the reference board;
  - exit 4 when the reference origin is not `real_board` and `--allow-substitute` is not given; with it, the plain rows carry the substitute's origin;
  - the output validates against `results.schema.json` (`kind: performance`).
- [X] T033 [P] [US2] Write `tests/edge/int8/test_int8_release_export.py` for the generic int8 exporter on a small QModel. It checks:
  - the folder matches the allow-list of contracts/release-files.md exactly;
  - no `*.eval.npz` and no dataset window is in it;
  - `config.json` has `labels`, `input`, `normalisation`, `quantisation`, `preparation` and `format: pace-cnn-v1`;
  - there are at least three examples with `source: synthetic`, `input` of "1,152 int8 values, row-major 128 × 9" and `expected` of "6 int8 scores in class order", each validating against `pace-cnn-v1.schema.json`;
  - exit 4 when a file outside the allow-list would be written or an example does not reproduce.
- [X] T034 [P] [US2] Write `tests/edge/int8/test_release_c_sources.py`. Compile the exported `c/*.c` with the host C compiler and a small test driver (skip if no compiler is found), feed every `examples/*.json` input and compare with `expected` bit for bit (V8).
- [X] T035 [P] [US2] Write `tests/release/test_sbom.py`. `mobility_model_zoo.release.sbom.sbom(dir)` returns the same CycloneDX document as the old `security/can_ids/release_export.sbom` for a fixture folder, and it lists every shipped file except `sbom.cdx.json`.

### Implementation for User Story 2

- [X] T036 [P] [US2] Build the model catalogue of `tests/edge/hil/test_inference.py`, `tests/edge/hil/test_models.py` and `tests/edge/hil/test_robustness.py` from `bench_models()`, the same function that `pytest_plugin.py:168` uses for the parameters. Replace the `load_zoo()` catalogue (R8), keyed by model name.
- [X] T037 [P] [US2] Fix `load_eval` in `src/mobility_model_zoo/edge/bench/reference_models.py:149`. It looks next to each `.npz` in `MMZ_EDGE_MODELS`, then in `derived/<name>/<name>.eval.npz`, then in the current places (R8).
- [X] T038 [P] [US2] Raise the serial receive buffer from 2048 to 4096 bytes for ESP32 and ESP8266 in `firmware/bench/src/hal_arduino.cpp:56`, so a pace-cnn INFER line of about 2.3 KB fits (R8). Check that `BENCH_LINE_MAX` in `firmware/bench/lib/benchapp/src/benchapp.c:16` covers `2 × 1152 + 96`.
- [X] T039 [P] [US2] Add `budgets: {pace-cnn: 100000}` to the `esp32` target in `hil/targets.yaml`. `edge/bench/config.py:47` already reads `budgets`, and `tests/edge/hil/test_performance.py:22` enforces it.
- [X] T040 [US2] Add `--footprint model|image` (default `image`) to `edge measure` in `src/mobility_model_zoo/edge/bench/cli.py` and `src/mobility_model_zoo/edge/bench/measure.py`. `model` reads the symbol sizes of the ELF built for the board's target with the toolchain's `nm` and computes `flash_kb` and `ram_kb` as in T031. It also reports the whole-image values under `*_image` names. Latency and origin stay unchanged (`origin_of`, `hardware_of`). Add the share of self-test vectors equal to the host reference to the output, if it is not there yet.
- [X] T041 [US2] Create `src/mobility_model_zoo/edge/bench/performance.py` and the command `edge performance --model M --version V --reference FILE [--extra FILE ...] [--allow-substitute]` in `src/mobility_model_zoo/edge/bench/cli.py`. It writes `zoo/models/<model>/results/<version>/performance.json` following T032 and the picket-forest 0.2.0 layout that gate rule 15 accepts (R9).
- [X] T042 [P] [US2] Move the SBOM generator from `src/mobility_model_zoo/security/can_ids/release_export.py:48` to `src/mobility_model_zoo/release/sbom.py` (R10). Make `release_export.py` and `release_export_v2.py:186` import it from there. In `scripts/ci/select_tests.py`, make a change to `src/mobility_model_zoo/release/sbom.py` also select `tests/security` (plan, Structure Decision). Confirm with `uv run python scripts/ci/select_tests.py` on that path.
- [X] T043 [P] [US2] Create `src/mobility_model_zoo/condition_monitoring/activity/pace-cnn-v1.schema.json` for the example format of contracts/records.md:
  - `format` is `pace-cnn-v1` and `source` is `synthetic`;
  - `generator` has `name`, `version` and `seed`;
  - `input` holds exactly 1,152 integers in −128…127;
  - `expected` holds exactly 6 integers in −128…127;
  - no extra keys.
- [X] T044 [US2] Create `src/mobility_model_zoo/edge/int8/release_export.py`, the generic int8 release exporter that `hum-fan` can reuse (R10). It writes the allow-list of contracts/release-files.md:
  - `<model>.npz` and `<model>.tflite`;
  - `c/<model>_model.c` and `c/<model>_model.h`, the model alone, generated with `edge/int8/codegen.py`;
  - `c/microinfer.c` and `c/microinfer.h`, copied from `firmware/bench/lib/microinfer/src/`;
  - `config.json`;
  - `examples/example-1.json` … `example-3.json`, built from the first three QModel `test_inputs` (generator `uniform-int8`, version 1, the QModel's seed) with `expected` from the host reference, so the board's self-test covers the examples;
  - `sbom.cdx.json` via `release/sbom.py`.

  It refuses (exit 4) on any extra file or on an example that does not reproduce.
- [X] T045 [US2] Add `condmon activity export --version 0.1.0 --out DIR` in `src/mobility_model_zoo/condition_monitoring/cli.py`. It calls `release_export.py` with the seed-0 run and fills `config.json` from the manifest normalisation, the QModel quantisation and the `prepare.py` steps (channel names and units, 50 Hz, window 128, overlap 0.5, the filter coefficients of T025).
- [X] T046 [US2] Run `uv run condmon activity export --version 0.1.0 --out /tmp/pace-cnn-0.1.0` (V8). Copy the three examples into `zoo/models/pace-cnn/examples/` and add `zoo/models/pace-cnn/examples/SOURCES.yaml` stating `synthetic`, as `zoo/models/picket-forest/examples/SOURCES.yaml` does. Confirm T034 passes on the real export.
- [X] T047 [US2] Run the bench on the simulator and the emulator (V6 steps 1–2):
  - `MMZ_EDGE_MODELS=$MMZ_DATA/derived/pace-cnn/seed-0/pace-cnn.npz uv run edge run -b sim`;
  - `… uv run edge --boards hil/qemu-boards.yaml run -b esp32-qemu --require-all`.

  All HIL tests must pass with pace-cnn in the catalogue before the real board is used.
- [X] T048 [US2] **Owner** connects esp32-1 (press PWR if it does not answer, `hil/boards.yaml`) and esp8266-1 to the Mac. Then run `edge run -b esp32-1` and `edge run -b esp8266-1` with the same `MMZ_EDGE_MODELS` (V6 steps 3–4). On esp32-1, every self-test vector and example must equal the host reference (SC-003, FR-016); any mismatch blocks the release. If esp32-1 stays unreachable, continue with the emulator as substitute (T049 `--allow-substitute`) and record "budgets on the real reference board: not measured".
- [X] T049 [US2] Run `uv run edge measure $MMZ_DATA/derived/pace-cnn/seed-0/pace-cnn.npz -b <board> --footprint model --model-version 0.1.0 --out <board>.json` for esp32-1, esp32-qemu, esp8266-1 and sim. Then run `uv run edge performance --model pace-cnn --version 0.1.0 --reference esp32.json --extra qemu.json --extra esp8266.json --extra sim.json` (V7). Keep the per-board JSON files outside git.
- [X] T050 [US2] Set `performance.hardware: ESP32 (LilyGO LoRa32, HIL bench)` and `performance.budget.target: ESP32` in `zoo/models/pace-cnn/releases/0.1.0.yaml` (FR-015, R16). Re-run `uv run condmon activity evaluate --version 0.1.0` so S4 and K3 are decided from `performance.json`; this is a deterministic recomputation, not a new evaluation (FR-004). Commit `performance.json`, the updated reports and the record.

**Checkpoint**: Flash, RAM and latency on esp32-1 with origin, bit-exact board outputs, and standalone C sources exist. US2 is testable on its own (SC-002, SC-003).

---

## Phase 5: User Story 3 - A newcomer finds, understands and uses the published model (Priority: P3)

**Goal**: Close the gate gaps (site and format files, compliance record, attribution on the card, topic collection, the confirmation of no Claude inputs, the benchmark trace), write an honest card from `verdict.json`, and publish through the pipeline with the owner's approval.

**Independent Test**: In a fresh environment, the card's install line and host example print six int8 scores in at most 5 minutes. The card shows status, usage class, licence, limits, missed criteria and the UCI HAR attribution. The gate confirms no Claude inputs. The collection, website, model lists and roadmap show pace-cnn as published (quickstart V9–V13).

**Dependency**: the code tasks T051–T065, T068 and T069 need only Phase 2. The card, records and publication (T066, T067, T070–T079) need US1 and US2.

### Tests for User Story 3 ⚠️

- [X] T051 [P] [US3] Write `tests/release/test_collection.py` and extend `tests/release/fakehub.py` with collection visibility. It checks:
  - `init_model` creates a private collection from the topic's title and description when `hf_collection` is null, and writes the slug into `topics.yaml`;
  - nothing changes when the collection exists;
  - `publish` makes a private topic collection public when it adds the first public model.
- [X] T052 [P] [US3] Write `tests/compliance/test_scan_publish_nontext.py`. A dataset whose source class is not text (for example `imu-activity-datasets`) and that has `used_by` is exempt from the corpus-overlap scan, and the exemption and its reason are recorded in the publication-scan report. A text source without a snapshot still fails with "the scan needs the snapshots under data/snapshots" (plan, Risks).
- [X] T053 [P] [US3] Write `tests/release/test_card_dataset_attribution.py`. For a release whose training source is a declared dataset, the card section "Training data and attribution" shows the dataset's `attribution_text` and its licence, and it does not speak of "published documents" or "training texts". The privacy section shows `card_privacy_note`.
- [X] T054 [P] [US3] Write `tests/condition_monitoring/test_card_verdict.py`. Every missed criterion in `topics/condition-monitoring/reports/pace-cnn/0.1.0/verdict.json` appears in `zoo/models/pace-cnn/model.yaml` `card.unmet_criteria` with its measured value (R6). "Rule 18 allows at most five items for `unmet_criteria` and `limits_short` together."
- [X] T055 [P] [US3] Write `tests/release/test_no_claude_inputs.py` for the new check of gate rule 7 (R21, FR-027), on fixture registries. Rule 7 fails when any of these belongs to the Claude family:
  - a teacher in `provenance.teachers`;
  - a route the compliance register links to the release;
  - a labeling, data-generation or evaluation run recorded for it.

  Membership is decided by `model_family: claude` or, for entries without the field, by `claude` or `anthropic` in the model id or hosting provider. The check passes, and says so in its output, for a release without teachers or routes like pace-cnn. A frozen reference that Principle XI keeps (pilot-v1, pilot-v2, cluster-v1, spike-v2) passes only in the role of benchmark reference, never as a training source or teacher.
- [X] T056 [P] [US3] Write `tests/release/test_rule9_benchmark_trace.py` for the new benchmark trace of gate rule 9 (R22), on a fixture topic with a manifest and an evaluation report. It covers:
  - rule 9 fails when a run in `evaluation.json` names another manifest SHA-256;
  - rule 9 fails when a criteria commit is not in the history, or is newer than the earliest `trained_at`;
  - rule 9 passes when everything matches;
  - a release without a manifest skips the trace with a note.
- [X] T057 [P] [US3] Write `tests/condition_monitoring/test_card_contents.py`. Render the pace-cnn card with `release/card.py` and check that it contains every item FR-020 names:
  - status, usage class `commercial` and licence Apache-2.0;
  - intended use, every out-of-scope use including the AI Act uses, and the limitations;
  - the headline metrics with their reference, the per-class F1 rows, the worst test subject and the seed spread;
  - the budget results with origin and hardware;
  - the UCI HAR attribution (creators, title, DOI, licence, modifications), the input contract and the privacy note.

### Implementation for User Story 3

- [X] T058 [US3] In `src/mobility_model_zoo/release/hub.py:183`, give `create_collection` a `private` flag and add a method that makes a collection public, via `huggingface_hub`'s collection update; check the current signature with context7. Mirror both in `tests/release/fakehub.py`.
- [X] T059 [US3] In `src/mobility_model_zoo/release/publish.py`, make `init_model` (line 49) ensure the topic collection: create it private and write the slug into `zoo/topics.yaml` (R12). In `add_to_collection` (line 349), make a private collection public when it adds the first public model. Update the `init-model` and `publish` help texts in `src/mobility_model_zoo/release/cli.py`.
- [X] T060 [P] [US3] Add the non-text exemption to `scan-publish` in `src/mobility_model_zoo/compliance/cli.py` (lines 258–296 and `_corpus_texts` at line 230), following T052. First look for an existing field that marks a source class as text. If there is none, add a `modality` field to the source-class schema in `src/mobility_model_zoo/compliance/schemas/` and set it in `topics/*/compliance/source-classes.yaml`. Record each exempt dataset and its reason in the report written by `release_checks.report_path`.
- [X] T061 [P] [US3] Fix the card in `src/mobility_model_zoo/release/templates/model_card.md.j2` and its context in `src/mobility_model_zoo/release/card.py` (`compliance_context`):
  - **Training data and attribution** (line 177): for dataset sources, render title, creators, DOI, licence, the declaration's `attribution_text` and `modifications`, with dataset wording instead of "published documents" and "training texts" (R13, FR-020);
  - **FR-020 items**: add whatever the template does not yet render for T057, such as quality rows beyond the headline or budget rows with origin.

  Re-check the golden cards in `tests/release/fixtures/golden/` and update them only where the change is intended.
- [X] T062 [P] [US3] Add the field `model_family` to every route in `compliance/providers.yaml` and to its schema in `src/mobility_model_zoo/compliance/schemas/` (R21). `claude-api` and `claude-consumer-cli` get `claude`, every other route its own family. A route without the field is reported by `zoo validate --all`.
- [X] T063 [US3] Implement the check for no Claude inputs in gate rule 7 (`rule_7` in `src/mobility_model_zoo/release/gate.py:449`) following T055 and R21. It reads the teachers of the release record and the routes and recorded runs that the compliance register links to the release. The exception for the frozen references that Principle XI keeps comes from decision D-claude-risk-0.1.x in `compliance/decisions.yaml`, not from a list in code. The rule's output states "no Claude inputs" when it passes.
- [X] T064 [US3] Implement the benchmark trace in gate rule 9 (`rule_9` in `src/mobility_model_zoo/release/gate.py:733`) following T056 and R22. It reads `topics/<topic>/benchmarks/<benchmark>/manifest.json` and `topics/<topic>/reports/<model>/<version>/evaluation.json`. Use `git merge-base --is-ancestor` and the commit date for the criteria commits. Releases without a manifest skip the trace with a note.
- [X] T065 [US3] Regression check of the new rules 7 and 9: run `uv run zoo check <model> <version> --offline` for every published release (at least scout-large 0.1.3 and picket-forest 0.2.1) and `uv run zoo validate --all`. They must pass as before. If a published release now fails rule 7, stop and report it to the owner instead of widening the exception.
- [X] T066 [US3] Set `used_by: [pace-cnn@0.1.0]` for `uci-har` in `topics/condition-monitoring/compliance/datasets.yaml`, after T060 (FR-005). `redistribution` stays `unclear`, because no dataset content is published.
- [X] T067 [US3] Rewrite the `card` block of `zoo/models/pace-cnn/model.yaml` (data-model.md, R14):
  - `intended_use`;
  - `out_of_scope` and `not_for`, worded so card lint C-C2 passes, in plain words: monitoring or evaluating persons at work; decisions on access to insurance, credit or services from a person's movement; identifying or profiling persons; fall detection as a safety function; transport-mode or vehicle classes;
  - `input_output`, the input contract of R11 with units, 50 Hz, 128 samples, 50 % overlap, gravity separation, normalisation constants and a pointer to `config.json`;
  - `how_to_run`, which loads `pace-cnn.npz` from the Hub, runs the first example and says the input is synthetic and checks the arithmetic, not an activity;
  - `device_usage`, which uses the shipped `c/pace_cnn_model.h` and `c/microinfer.h` with the model's own arena size;
  - `limitations` and `limits_short`, including the measured sitting/standing F1 and the worst test subject;
  - `unmet_criteria` from `verdict.json`: S5 "Transfer to mobility data tested: not tested (UCI HAR only)", plus every other miss with its value, grouped so that `unmet_criteria` and `limits_short` together hold at most five items.

  Take every number from `quality.json` or `performance.json` (FR-022).
- [X] T068 [P] [US3] Create `zoo/models/pace-cnn/site.yaml` following `zoo/models/picket-forest/site.yaml` and `src/mobility_model_zoo/site/schemas/site.schema.json`:
  - tagline, share_line, an audience of at most 25 words, and 3–4 differentiators (titles at most 5 words, texts at most 20);
  - numbers only as `{metric:quality.…}` or `{metric:performance.…}` placeholders, and no release status;
  - `quickstart_example: example-1.json`, a hardware note, and metric cards for `quality.int8_macro_f1`, `quality.int8_accuracy`, `performance.flash_kb` and `performance.latency_us`.

  Every metric card label and differentiator that names a device value states the board and the origin of `performance.json` (for example "Latency per window (ESP32, real board)", or "(ESP32, emulator)" if the substitute was used) (Principle V).
- [X] T069 [P] [US3] Create `zoo/formats/pace-cnn-v1.yaml` with the field meanings of the example format for the website, following `zoo/formats/picket-forest-v2.yaml`. Point it to `src/mobility_model_zoo/condition_monitoring/activity/pace-cnn-v1.schema.json` (check B5 needs both).
- [X] T070 [US3] Update `zoo/models/pace-cnn/releases/0.1.0.yaml`:
  - `date`;
  - `changes`, the first-release text;
  - `recipe.git_commit`, the commit holding the freeze, criteria and recipe;
  - `provenance.sources[0].count`, the number of training windows from the manifest.

  Keep `status: experimental`, `evaluation.benchmark: uci-har-v1`, `evaluation.reference_kind: ground_truth`, `usage.class: commercial` and `licence: Apache-2.0`. `files[]` and `staging.revision` are filled by `zoo stage`.
- [X] T071 [US3] Create `zoo/models/pace-cnn/releases/0.1.0.compliance.yaml` with the compliance harness, following `zoo/models/picket-forest/releases/0.2.0.compliance.yaml`:
  - `runtime: mcu`, `sbom: sbom.cdx.json`;
  - `intended_purpose`, `out_of_scope`, `annex_iii_match`;
  - `card_privacy_note`: trained on motion signals of 30 volunteers, published under numbers by the dataset authors; no data or subject number is in the release.

  The card template reads `card_privacy_note` from the compliance record, not from `model.yaml`. Then run `uv run zoo compliance render`.
- [X] T072 [US3] Run `uv run zoo check pace-cnn 0.1.0 --offline` (V9). Open may stay only:
  - the rules that need staging or the Hub (1, 5, 12);
  - rule 16, because its compliance stages include the owner's signoff (`compliance/checks.py:212`, `RELEASE_STAGES`).

  Rules 7 (with "no Claude inputs"), 9 (with the benchmark trace), 13, 15, 17 and 18 and card lint C-C2 must pass. Fix the cause and do not weaken a check.
- [X] T073 [US3] Run `uv run zoo compliance scan-publish --model pace-cnn --version 0.1.0` (V10). It must pass without a text snapshot for `uci-har` and record the exemption reason. Check the rendered card for the UCI HAR attribution and the privacy note. **Owner** runs `zoo compliance signoff --model pace-cnn --version 0.1.0`. Then run `uv run zoo check pace-cnn 0.1.0 --offline` again: rule 16 must now pass.
- [X] T074 [US3] **Owner** gives the go. Then run `uv run zoo init-model pace-cnn`, which creates the Hub repos and the private `condition-monitoring` collection and writes its slug into `zoo/topics.yaml`. **Owner** adds `mobility-model-zoo/pace-cnn-staging` to the repo list of `HF_STAGING_TOKEN` (R18).
- [X] T075 [US3] Run `uv run zoo stage pace-cnn 0.1.0 --from /tmp/pace-cnn-0.1.0` and the full `uv run zoo check pace-cnn 0.1.0` (V11 steps 2–3). All 18 rules must pass, including the fresh-environment run of the card's host example (rule 12, FR-025). If a check fails after staging, fix the cause and stage again; nothing is published until the gate passes.
- [ ] T076 [US3] Open the PR from `021-pace-cnn-first-release`. **Owner** merges it and pushes the tag `pace-cnn/v0.1.0`. release-verify builds the preview, and the card's topic link must point to the collection. **Owner** reviews the preview and starts release-publish (V11 steps 4–5, FR-024).
- [ ] T077 [US3] After publication, edit the manual rows in `README.md` and `topics/condition-monitoring/README.md`: pace-cnn is published, with a link to the `condition-monitoring` collection. Confirm that `zoo/MODELS.md` was updated by the publish step (R15).
- [ ] T078 [US3] Fresh-environment walkthrough (V12, SC-004): in a new folder, create a Python 3.12 venv with `uv`, run only the card's install line and host example, and time it. Six int8 scores must appear in at most 5 minutes without any step that is not on the card. Write the time into the PR or a follow-up note.
- [ ] T079 [US3] Check the public surfaces (V13, SC-005, SC-007):
  - the website model page shows `experimental`, the missed criteria and device values labelled with board and origin;
  - the roadmap entry `pace-cnn` shows delivered with `published_at` on or before 2026-12-31;
  - the collection is public and lists pace-cnn;
  - every number on the card appears in `quality.json` or `performance.json`, and none comes from the pre-zoo report.

**Checkpoint**: pace-cnn 0.1.0 is published as `experimental` and listed everywhere. The gate has confirmed no Claude inputs. All three stories are complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T080 [P] Run `uv run ruff check` and `uv run ruff format --check` on all changed Python files, and fix the findings.
- [X] T081 Run `uv run python scripts/ci/select_tests.py` on the branch diff and run the selected test areas (condmon, edge, release, compliance, security for `release/sbom.py`). Confirm that:
  - the CI jobs `edge-sim` and `edge-qemu` are selected for the firmware change;
  - the change to `release/gate.py` selects the release tests of all models.
- [X] T082 [P] Run a privacy and provenance sweep over the branch diff and the upload folder:
  - no subject numbers or lists in `topics/condition-monitoring/benchmarks/`, `topics/condition-monitoring/reports/pace-cnn/0.1.0/`, `zoo/models/pace-cnn/` or `/tmp/pace-cnn-0.1.0`;
  - no `*.eval.npz` and no local paths;
  - no pre-zoo report numbers on the card or the site text (FR-023, FR-028, SC-007).
- [X] T083 [P] Align the feature docs with what was built:
  - in `specs/021-pace-cnn-first-release/data-model.md`, `card_privacy_note` lives in the compliance record (T071), not in `model.yaml`;
  - note the example generator decision of T044 in research R10;
  - note the source-class field chosen in T060 in research R13.
- [ ] T084 Walk through `specs/021-pace-cnn-first-release/quickstart.md` V1–V13 and mark each scenario passed, or give its finding in the PR description. List the plan's follow-ups (picket-forest attribution patch, SAMD21 bench support, 6-channel candidate, `edge-qemu` regression test from the public repo, the "14 rules" help text) for the owner. Do not open issues without the owner's go.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T002 needs network access to the UCI provider. T003 must be finished before T025.
- **Foundational (Phase 2)**: needs Setup and blocks all stories. T006 and T007 must be committed before T019 (the freeze).
- **US1 (Phase 3)**: needs Phase 2. Inside it, the order is strict: T016–T018 → T019 freeze → T020 criteria commit → T021–T023 → T024 runs → T025 → T026–T028 → T029.
- **US2 (Phase 4)**: the code tasks (T030–T045) need only Phase 2. The measurements T046–T050 need T024 (the seed-0 run) and T044–T045 (export). T050 re-runs T027's `evaluate`.
- **US3 (Phase 5)**: the code tasks T051–T065, T068 and T069 need only Phase 2. Inside them:
  - T059 needs T058;
  - T063 needs T062, and T064 comes after T063 (same file);
  - T065 needs T062–T064.

  The rest:
  - T066 needs T060;
  - T067 needs T029 and T050 (verdict and performance);
  - T070–T079 run strictly in order and contain owner steps.
- **Polish (Phase 6)**: T080–T083 can run once their files are final. T084 comes last.

### User Story Dependencies

- **US1 (P1)**: independent; it is the MVP and the constitution's gate before reporting.
- **US2 (P2)**: its code is independent of US1. Its evidence needs the US1 candidate (seed 0), because the budgets must be measured on the model that is released.
- **US3 (P3)**: its code is independent, including the new gate checks. Its card and publication need the US1 verdict and the US2 performance file, as the spec says ("only makes sense once stories 1 and 2 hold"). The benchmark trace (T064) reads the `runs[]` that T026 writes.

### Owner Steps (blocking)

- T003: only if the dataset documentation and its paper leave a filter value open.
- T048: connect esp32-1 and esp8266-1.
- T065: only if a published release fails the new rule 7.
- T073: compliance signoff.
- T074: go for `init-model`; staging token repo list.
- T076: merge, tag, preview review, release-publish.

### Within Each User Story

- Tests first, and they must fail before the implementation.
- Records and formats come before the commands that write them, and commands before the runs that use them.
- Commit the reports a story produces before the next story reads them.

---

## Parallel Opportunities

- **Phase 2**: T004 and T006 in parallel.
- **US1 tests**: T008–T015 in parallel (different files).
- **US1 implementation**: T023 alongside T021–T022 (different file).
- **US2 tests**: T030–T035 in parallel.
- **US2 code**: T036, T037, T038, T039, T042 and T043 in parallel; T040 → T041 and T044 → T045 in sequence.
- **US3 tests**: T051–T057 in parallel.
- **US3 code**: T060, T061, T062, T068 and T069 in parallel; T058 → T059 and T062 → T063 → T064 → T065 in sequence.
- **Across stories**: once Phase 2 is done, the US2 and US3 code tasks can run alongside US1, while the US1 runs (T024) and evaluation (T029) proceed.

## Parallel Example: User Story 1

```bash
# Tests of US1 together:
Task: "Benchmark freeze tests in tests/condition_monitoring/test_activity_benchmark.py"
Task: "Subject split tests in tests/condition_monitoring/test_subject_split.py"
Task: "Pre-registration refusal tests in tests/condition_monitoring/test_criteria.py"
Task: "Verdict rule tests in tests/condition_monitoring/test_verdict.py"
Task: "Evaluate tests in tests/condition_monitoring/test_activity_evaluate.py"
Task: "Input preparation tests in tests/condition_monitoring/test_prepare.py"
```

## Parallel Example: User Story 2

```bash
# Bench fixes together (different files):
Task: "HIL catalogue from bench_models() in tests/edge/hil/test_inference.py, test_models.py, test_robustness.py"
Task: "load_eval next to the .npz in src/mobility_model_zoo/edge/bench/reference_models.py"
Task: "Serial RX buffer 4096 in firmware/bench/src/hal_arduino.cpp"
Task: "esp32 budget pace-cnn: 100000 in hil/targets.yaml"
Task: "SBOM move to src/mobility_model_zoo/release/sbom.py"
```

## Parallel Example: User Story 3

```bash
# Tests together:
Task: "No Claude inputs, gate rule 7, in tests/release/test_no_claude_inputs.py"
Task: "Benchmark trace, gate rule 9, in tests/release/test_rule9_benchmark_trace.py"
Task: "FR-020 card contents in tests/condition_monitoring/test_card_contents.py"
Task: "Non-text exemption in tests/compliance/test_scan_publish_nontext.py"

# Code in different files together:
Task: "scan-publish non-text exemption in src/mobility_model_zoo/compliance/cli.py"
Task: "Card attribution and FR-020 rows in src/mobility_model_zoo/release/templates/model_card.md.j2"
Task: "model_family per route in compliance/providers.yaml"
Task: "Website text in zoo/models/pace-cnn/site.yaml"
Task: "Format file zoo/formats/pace-cnn-v1.yaml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) and Phase 2 (Foundational).
2. Phase 3 (US1): freeze, criteria commit, five runs, evaluate, reproduce.
3. **Stop and validate**: the owner sees the int8 result, the seed spread and the verdict `experimental` (quickstart V1–V5). This is the first honest result of pace-cnn and the constitution's gate before reporting.

### Incremental Delivery

1. Setup + Foundational → subjects loadable, benchmark defined.
2. US1 → measured candidate with verdict (MVP; nothing is published yet).
3. US2 → device evidence on esp32-1 and standalone C sources.
4. US3 → gate checks, card, compliance, collection, publication as `experimental` (roadmap delivery, SC-005 by 2026-12-31).

### Parallel Strategy

After Phase 2, one line works on the US1 runs and evaluation while another builds the US2 bench and export code and the US3 gate, release and compliance code. The two lines meet at T046–T050 (measure the candidate) and T067 (card from the verdict).

---

## Notes

- [P] tasks touch different files and depend on no unfinished task.
- If a kill criterion fires or the board disagrees with the host reference, report it and do not route around it: a mismatch blocks the release, and a kill blocks only the claims it concerns.
- Amending the criteria after any result has been seen needs `version: 2` with a rationale. Version 1 stays in git, and the reports name the version they used.
