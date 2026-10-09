# Tasks: picket-forest 0.1.0, honest CAN IDS benchmark and first release

**Input**: Design documents from `specs/007-picket-forest-release/`: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/cli.md](contracts/cli.md), [quickstart.md](quickstart.md).

**Tests**: included. The spec requires tests for the benchmark freeze (SC-001), the time-to-alarm fix (FR-008), the gate (SC-006) and the release.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task).
- **[Story]**: US1 benchmark, US2 evaluation, US3 gate for tree models, US4 device evidence and release.

## Path Conventions

- Package code: `src/mobility_model_zoo/security/can_ids/`, `src/mobility_model_zoo/release/`.
- Tests: `tests/security/can_ids/`, `tests/release/`.
- Benchmark files: `topics/security/benchmarks/can-ids-v1/`.
- Report: `topics/security/reports/picket-forest/can-ids-v1/`.
- Model: `zoo/models/picket-forest/`.
- Data: `$MMZ_DATA` (never in git).

---

## Phase 1: Setup

- [X] T001 Download the declared datasets and record what was fetched:
  - run `uv run zoo data download can-train-and-test` and `uv run zoo data download road`;
  - note the sizes, the `SOURCE.json` retrieval dates and the can-train-and-test repository revision in `specs/007-picket-forest-release/validation.md` (new file, section "Setup").
  - If the Bitbucket HEAD is the v1.5 layout instead of v1, record which split folders exist and stop for an owner decision before T008.
- [X] T002 [P] Create `topics/security/benchmarks/README.md`. It says that the folder holds frozen benchmark manifests with hashes only (no frames), and that a frozen manifest never changes: a change makes a new version (constitution IX).

---

## Phase 2: Foundational (blocks all stories)

- [X] T003 Write `tests/security/can_ids/test_metrics_alarm.py` before the fix (FR-008, research R4). It covers:
  - a one-frame episode whose alarm falls in the grace window, which gives a defined latency;
  - an alarm on the first attack frame, which gives 0 ms;
  - several episodes, where the median and the p95 of time to alarm are non-empty whenever at least one episode is detected;
  - false alarms counted outside `[start, end + grace]`.
- [X] T004 Fix `alarm_metrics` in `src/mobility_model_zoo/security/can_ids/metrics.py`:
  - latency is the time of the first alarm in `[start, end + grace]` minus `start`;
  - add `p95_latency_ms`;
  - add `mcc` to `frame_metrics`;
  - add `recall_at_fpr(y, score, fpr=0.001)`, with the threshold chosen on benign validation frames passed in by the caller, never on the test data.

  T003 must pass. The existing tests in `tests/security/can_ids/test_can_metrics.py` must stay green.
- [X] T005 Add a `budget_operating_point(val_caps, val_scores, thr, budget_per_hour)` function to `src/mobility_model_zoo/security/can_ids/metrics.py`. Per research R3, it:
  - scans the alarm grid `k ∈ {1,2,3,5,8} × window_ms ∈ {50,200,1000}` with a 1 s hold-off on validation captures;
  - returns the rule with the highest episode recall whose false alarms per hour are ≤ budget;
  - returns `None` when no rule fits.

  Add its test to `tests/security/can_ids/test_metrics_alarm.py`.
- [X] T006 [P] Add an `engine` field to `src/mobility_model_zoo/release/schemas/model.schema.json` and the compliance fields `runtime` and `sbom`:
  - `engine`: `{"enum": ["int8", "emlearn"], "default": "int8"}`, only meaningful with `runtime: mcu`;
  - in `src/mobility_model_zoo/compliance/schemas/release-compliance.schema.json`, add `runtime` (`python|mcu`) and `sbom` (string path), with `sbom` required when `runtime` is `mcu`. Check C-G4 expects them, but the schema rejected them;
  - copy all release schemas to `specs/007-picket-forest-release/contracts/`, the release-compliance schema to `specs/006-compliance-harness/contracts/schemas/`, and switch `tests/release/test_schemas.py` `CONTRACTS` to the 007 folder;
  - add a test that a release-compliance record with `runtime: mcu` and no `sbom` fails C-G4, and passes with it;
  - set `engine: emlearn` in `zoo/models/picket-forest/model.yaml`.

**Checkpoint**: The metrics are correct and tested, and the schemas know tree models and the mcu compliance fields.

---

## Phase 3: User Story 1 - Frozen, honest benchmark (P1) 🎯 MVP

**Goal**: `can-ids-v1` is frozen, reproducible and protected against changed or duplicated captures.

**Independent Test**: Freezing twice gives byte-identical manifests. A changed capture makes evaluation refuse to run.

### Tests for User Story 1

- [X] T007 [P] [US1] Write `tests/security/can_ids/test_benchmark.py` on tiny synthetic can-train-and-test and ROAD trees in `tmp_path`, built with the `frames` writers. It covers:
  - (a) the manifest fields of data-model.md "Benchmark manifest". `captures[].id` is unique; no frame data appears in the file.
  - (b) A second freeze gives a byte-identical manifest. A changed manifest is refused with exit 3, and identical content is a no-op with exit 0.
  - (c) Two captures with equal content and different vehicle or split labels stop the freeze with exit 1, naming both. With a `resolutions.yaml` entry (`action: keep|drop|relabel`, `reason` required), the freeze passes and records `resolutions_sha256`.
  - (d) `verify_captures` raises on a changed capture and names it.
  - (e) Role assignment:
    - `train_01` captures are train, except the highest-numbered capture per attack type, which is validation;
    - can-train-and-test `test_0x` captures are test;
    - ROAD attack runs ending `_2` (also `_2_masquerade`) and every fourth ambient capture by CRC32 of the name are test;
    - ROAD masquerade and accelerator captures are out of scope.

### Implementation for User Story 1

- [X] T008 [US1] Create `src/mobility_model_zoo/security/can_ids/benchmark.py` per research R1, R2 and R6. It provides:
  - `load_captures(data_dir)`, which yields common-format frames with dataset, set, split, vehicle, attack family and role;
  - `capture_hash(df)`, the SHA-256 of the frame columns `ts_us, can_id, dlc, b0..b7, label` in row order;
  - `episode_count(df)`, using the 1.0 s gap;
  - `freeze(data_dir, out_dir, resolutions)`;
  - `verify_captures(manifest, data_dir)`.

  The manifest format follows data-model.md, with the protocol constants episode gap 1.0 s, grace 1.0 s, budgets [1, 10], benign keep 0.1, seed 0 and recall FPR 0.001. Attack families come from the capture names (`DoS`, `fuzzing`, `interval`, `rpm`, `speed`, `standstill`, `systematic`, `force-neutral`, `double`, `triple`, …; ROAD: `fabrication`, `fuzzing`, `masquerade`, `accelerator`).
- [X] T009 [US1] Wire `security can-ids freeze [--benchmark can-ids-v1] [--data DIR]` in `src/mobility_model_zoo/security/cli.py` to `benchmark.freeze`, with the exit codes of contracts/cli.md. Missing dataset gives 5; an unresolved duplicate gives 1; a change to a frozen manifest gives 3.
- [X] T010 [US1] Run the freeze on the real data. First check the suspect pairs (set_01/test_04 vs set_02/test_01, set_03/test_04 vs set_04/test_01).
  - Write every duplicate group with its resolution and reason to `topics/security/benchmarks/can-ids-v1/resolutions.yaml`.
  - Commit `manifest.json` and `resolutions.yaml`.
  - Record the counts (captures, frames, episodes per split) and every resolution in `validation.md` under "US1".

**Checkpoint**: The benchmark is frozen. From here on, no test capture is used for training, thresholds or selection.

---

## Phase 4: User Story 2 - picket-forest next to baselines and shortcut controls (P1)

**Goal**: One harness scores picket-forest, the four controls and the baselines on the same protocol and writes the report and the quality results.

**Independent Test**: `evaluate picket-forest --sets set_01` produces a partial report; the full run produces `quality.json` that validates against the results schema.

### Tests for User Story 2

- [X] T011 [P] [US2] Write `tests/security/can_ids/test_detectors.py` on synthetic frames from `synth.py` (T019 can come first; if not, use a local helper):
  - every detector in the registry implements `fit(train_caps, val_caps)` and `score(caps) -> list[np.ndarray]`;
  - `ctrl-shuffled` on a separable toy problem scores near chance;
  - `ctrl-id-lookup` scores 1.0 when attacks use an ID that never appears benign;
  - `bl-mean-interval` and `bl-binning` flag a doubled message rate;
  - `bl-can-logic` flags an unknown ID, three repeats of the same ID and a too-short interval.
- [X] T012 [P] [US2] Write `tests/security/can_ids/test_evaluate.py` on a two-set synthetic benchmark frozen in `tmp_path`. Assert:
  - each set trains only on its own train captures, which is checked by recording the captures the detector saw;
  - thresholds and the alarm operating point come from validation captures;
  - the report contains no support-weighted metric (a search for "weighted" finds nothing);
  - `quality.json` validates against `results.schema.json`, with `reference_kind` set in the release record, a `reference` text and `benchmark: can-ids-v1`;
  - a partial run (`--sets`) is marked `partial: true` and refuses to write `quality.json`;
  - a set that cannot be loaded is listed as missing and makes the report partial (spec edge case "Missing set");
  - a hash mismatch makes the run exit 1;
  - the report contains the Pareto table and the C-versus-Python check section.

### Implementation for User Story 2

- [X] T013 [US2] Create `src/mobility_model_zoo/security/can_ids/detectors.py` with a registry and one interface, per research R5.
  - **picket-forest:** reuses `forest.py` (`select`, `fit`, `vote_score`, feature set `no_can_id`, 10 % benign subsampling with seed 0).
  - **Controls:**
    - `ctrl-id-lookup`: per-ID attack rate on training data; an unseen ID scores the global rate.
    - `ctrl-timing-only`: the forest on the timing features of `FEATURE_NAMES`. List them explicitly in the code.
    - `ctrl-forest-with-id`: the feature set `full`.
    - `ctrl-shuffled`: training labels permuted within each capture, seed 0.
  - **Baselines:**
    - `bl-mean-interval` and `bl-binning`: Blevins et al. 2021, benign-only per-ID interval statistics; the threshold comes from validation.
    - `bl-can-logic`: interval too short, ID repeated three times in a row, ID not in the training whitelist.
    - `bl-isolation-forest`: on the 13 features.
    - `bl-orig-{dt,rf,et,gnb,logreg,mlp}`: scikit-learn defaults on the original frame features (timestamp, ID, data bytes); the report notes the absolute timestamp as a shortcut feature.
- [X] T014 [US2] Create `src/mobility_model_zoo/security/can_ids/evaluate.py`. For each detector × set it:
  - verifies hashes (`benchmark.verify_captures`) and loads cached features from `$MMZ_DATA/derived/picket-forest/features/`;
  - fits on the set's train captures;
  - chooses the score threshold on validation (best F1, as in `forest.best_threshold`) and the operating points for budgets 1 and 10 with `budget_operating_point` (T005);
  - scores the four test splits, storing the scores per data-model.md "Detector run" with `run.json`.

  It then computes the headline and secondary metrics per split and aggregates them as the median over sets and the worst set. A set that cannot be loaded is recorded as missing.

  For ROAD, it trains the release model on demand with the recipe of T026 (`train_01` of all four sets, selection on validation captures) and caches it in `$MMZ_DATA/derived/picket-forest/export/`. It reports fabrication and fuzzing in the main tables and masquerade and accelerator in an out-of-scope table (FR-013). T026 reuses this cached model.

  It also records, for every detector, its cost: model size (tree nodes or parameters, and estimated flash) and per-frame latency on the host. For picket-forest it runs the C host scorer on every test capture and counts score mismatches against Python.
- [X] T015 [US2] Write the report and the results in `evaluate.py`.
  - **`topics/security/reports/picket-forest/can-ids-v1/report.md`** starts with the outcome per research R10 (success, partial or kill), computed from the numbers. Then come:
    - headline tables, controls, baselines, per attack family, ROAD, out of scope;
    - the quality-vs-cost Pareto table (headline at ≤ 10 false alarms per hour on unknown vehicles against flash and host latency), marking the Pareto-optimal detectors (constitution III);
    - the deterministic check: C-versus-Python score mismatches on all test captures (must be 0);
    - limitations, `code_commit` and `manifest_sha256`.
  - **`metrics.json`** holds the full numbers.
  - **`zoo/models/picket-forest/results/0.1.0/quality.json`** holds metric names `<metric>_<split>_<agg>` (data-model.md), each with `reference`, `benchmark: can-ids-v1` and `n_items`.
- [X] T016 [US2] Wire `security can-ids evaluate DETECTOR|all --benchmark can-ids-v1 [--sets …] [--report]` in `src/mobility_model_zoo/security/cli.py` per contracts/cli.md, replacing the exit-5 stub. Keep `security can-ids forest evaluate` as an alias that calls the harness for picket-forest only.
- [ ] T017 [US2] Fast check: run `uv run security can-ids evaluate all --benchmark can-ids-v1 --sets set_01` and record the runtime and partial results in `validation.md` under "US2 (partial)". Fix anything that fails before the full run.
- [ ] T018 [US2] Full run: run `uv run security can-ids evaluate all --benchmark can-ids-v1 --report`.
  - Record the runtime, the R10 outcome, the headline per split (median and worst set) for picket-forest and for the best control and baseline, and the ROAD results in `validation.md` under "US2".
  - Commit the report, `metrics.json` and `quality.json`.
  - **GATE**: `ctrl-shuffled` collapses (attack-class AUROC at most 0.6 on every split, research R10); otherwise stop and investigate leakage (research R10, kill).

**Checkpoint**: The honest numbers exist. The card text may only claim what this report supports (SC-004).

---

## Phase 5: User Story 3 - Release gate for tree models (P2)

**Goal**: Gate rules 12 and 13 verify an emlearn model bit-exactly through its C code.

**Independent Test**: A fixture tree model passes. One flipped expected score bit fails rules 12 and 13 (SC-006).

### Tests for User Story 3

- [X] T019 [P] [US3] Create `src/mobility_model_zoo/security/can_ids/synth.py` and `tests/security/can_ids/test_synth.py` (research R8). The generator `generate(attack, n_frames=2000, seed)` produces:
  - periodic benign IDs (10–100 ms periods, ±2 % jitter, counter and checksum bytes);
  - one injected attack per sequence: `fabrication` (extra frames on an existing ID with a changed payload), `dos` (ID 0x000 at 0.2 ms), `fuzzing` (random IDs and payloads) or `scan` (sequential IDs).

  The output is in the common frame format plus labels. The test checks determinism per seed and that every sequence contains at least one attack episode.
- [X] T020 [P] [US3] Create a tree-model fixture `edge-fixture-forest` in `tests/release/fixtures/registry/zoo/models/edge-fixture-forest/`:
  - topic `sandbox`, `runtime: mcu`, `engine: emlearn`;
  - a release record, synthetic results with `origin`, and a `device_usage` that uses `picket_forest_process`.

  Add `tests/release/edge_fixture_forest.py`, which at test time:
  - trains a 3-tree forest (emlearn) on synthetic frames;
  - writes `picket_forest_model.h`, `picket_forest_config.h`, `model.joblib` and `config.json` as the staged files;
  - writes three `examples/*.json` per data-model.md "Tree-model example": `source: synthetic`, `frames`, `expected_scores` as 8-digit hex float32 bit patterns, `expected_alarms` as frame indices.

  Add an `mcu_forest_env` fixture to `tests/release/conftest.py`. Skip when emlearn or a C compiler is missing.
- [X] T021 [P] [US3] Write `tests/release/test_gate_emlearn.py`. It asserts:
  - the fixture passes offline and online (rules 12, 13 and 15 PASS);
  - one flipped bit in `expected_scores` fails rules 12 and 13, and restoring it passes (SC-006);
  - a changed `expected_alarms` fails;
  - an example with `source: road` fails rule 13 (redistribution unclear);
  - the int8 fixture `edge-fixture-tiny` still passes unchanged.

### Implementation for User Story 3

- [X] T022 [US3] Extract the host scorer build from `security/can_ids/forest.py` (`build_host_scorer`, `host_scores`) into a reusable function `build_scorer(headers_dir, out_dir) -> Path`. It compiles with `-ffp-contract=off` from the C sources at the current checkout (`firmware/picket-forest/c`, `firmware/components/can_features`). Keep `forest.py` using it.
- [X] T023 [US3] Extend `src/mobility_model_zoo/release/gate.py` for `engine: emlearn` (research R7).
  - Rule 12 and rule 13 online: download the staged files to a temporary folder, check that the staged `c/` sources equal the repository sources at the recipe commit, build the scorer from the staged files only, replay each example (frames written to the binary frame format of `frames_to_bin`), and compare the scores bit by bit and the alarm indices (alarms recomputed with `forest_features.alarms` and the staged alarm rule).
  - Offline, rule 13 checks the example count (≥ 3), the fields and `source`.
  - Rule 11 additionally rejects staged files over 5 MB except `model.joblib`.

  Extend `tests/release/test_gate_emlearn.py`: a staged source that differs from the repository fails rule 12.

  The `engine: int8` path stays unchanged.
- [X] T024 [US3] Extend the mcu card in `src/mobility_model_zoo/release/card.py` and `templates/model_card.md.j2` for `engine: emlearn`:
  - Each example is shown as a summary: frames, attack frames, expected alarms, and the first 5 frames as a table.
  - The "On the device" C block comes from `device_usage`.
  - The python card stays byte-identical, and the int8 mcu golden card is unchanged.

  Add a golden file `tests/release/fixtures/golden/edge-fixture-forest-0.1.0.README.md`, rendered via `ZOO_UPDATE_GOLDEN=1`.
- [X] T025 [US3] Run the release tests (`uv run pytest tests/release -q`) and record the result in `validation.md` under "US3".

**Checkpoint**: The gate can verify picket-forest.

---

## Phase 6: User Story 4 - Device evidence and the published release 0.1.0 (P2)

**Goal**: picket-forest 0.1.0 is measured, documented, compliance-checked and published as experimental.

**Independent Test**: `zoo check picket-forest 0.1.0 --offline` passes. `release-verify` passes. After approval the model is public in the security collection.

### Implementation for User Story 4

- [ ] T026 [US4] Change `security can-ids forest export` in `src/mobility_model_zoo/security/can_ids/forest.py` so that it:
  - trains the release model on `train_01` of all four sets with the config of `configs/security/can-ids/picket-forest.yaml`. Selection uses validation captures only; if it picks other hyperparameters than 30 trees, depth 12, alarm 3 in 200 ms, the config is updated with the reason;
  - reuses the release model cached by T014 if its recipe hash matches, otherwise trains it;
  - writes to `$MMZ_DATA/derived/picket-forest/export/` the files `picket_forest_model.h`, `picket_forest_config.h`, `model.joblib`, `config.json` (with `manifest_sha256` and `code_commit`) and the `c/` sources (`picket_forest.{c,h}`, `msml_can_features.{c,h}`, `msml_alarm.{c,h}`);
  - writes `sbom.cdx.json` (CycloneDX 1.5: component per source file with SHA-256, plus emlearn and scikit-learn with versions) and a test in `tests/security/can_ids/test_forest_port.py` that the SBOM lists every staged source with its hash.

  Run it and record the parity result and the chosen hyperparameters in `validation.md` under "US4".
- [ ] T027 [US4] Add `security can-ids forest examples --out DIR` to `forest.py`. It writes three synthetic examples (`fabrication`, `dos`, `fuzzing`) with T019 and computes the expected scores and alarms with the scorer of T022 from the exported headers. Run it into `zoo/models/picket-forest/examples/` and commit the files.
- [X] T028 [P] [US4] (CI build deferred, see validation.md) Create a PlatformIO project in `firmware/picket-forest/platformio/` (`platformio.ini` with envs `esp32` and `esp8266` = `d1_mini` at 160 MHz, framework arduino):
  - `src/` reuses the existing replay sketch `firmware/picket-forest/esp8266/picket_forest_bench/bench.cpp` and the C sources through `lib_extra_dirs`/`build_src_filter`; no copies;
  - a pre-script copies the exported headers and a synthetic test-vector header (from the T027 examples, not dataset frames) into a gitignored `generated/` folder;
  - the sketch prints `PICKET_FOREST_RESULT` with frames, cycles or µs per frame (median, p99), score mismatches against the expected scores, alarms, state bytes and free heap.

  Add the envs to `.github/workflows/firmware.yml` (build only).
- [X] T029 [US4] Create `src/mobility_model_zoo/security/can_ids/measure.py` and wire `security can-ids measure --target host|esp32-qemu|esp8266 -b BOARD [--out FILE]` in `security/cli.py` per contracts/cli.md:
  - **`host`:** times the scorer of T022 over the examples (median and p99 µs per frame), origin `host`.
  - **`esp32-qemu`:** builds the `esp32` env and runs it in QEMU through `mobility_model_zoo.edge.bench.qemu`. Reads the result line and takes `flash_kb` (detector code plus rodata from the linker map) and `ram_kb` (state bytes plus static data). Origin `emulator`; the latency description says "not representative".
  - **`esp8266 -b BOARD`:** builds the `esp8266` env, flashes it through the bench flasher of the board in `hil/boards.yaml`, reads the result line over serial, and records `latency_us`, `latency_p99_us` and `ram_kb` with origin `real_board` and hardware "ESP8266 (Wemos D1 mini), 160 MHz, substitute for the reference board ESP32-S3".

  Every run merges its metrics into `--out` in `results.schema.json` format. Add `tests/security/can_ids/test_measure_forest.py` for the host target and for the parsing of the result lines.
- [ ] T030 [US4] Measure.
  - Run `measure --target host`, `--target esp32-qemu` and, with the D1 mini on USB (`uv run edge discover`, entry in `hil/boards.yaml`), `--target esp8266 -b <id>`.
  - **GATE**: 0 score mismatches on the ESP8266 and in QEMU.
  - Record the numbers in `validation.md` under "US4", including the ESP8266 latency against the 100 µs target and the ESP32 image against 16 KB RAM and 128 KB flash.
  - Commit `zoo/models/picket-forest/results/0.1.0/performance.json`.
- [ ] T031 [US4] Complete `zoo/models/picket-forest/releases/0.1.0.yaml`: `files[]` (via `zoo stage`), `recipe` (commit of the export, `configs/security/can-ids/picket-forest.yaml`, `topics/security/tasks/can-ids.md`), `provenance.sources` (`can-train-and-test` with `dataset`, `count` = training frames), `evaluation` (`benchmark: can-ids-v1`, `reference_kind: ground_truth`, `reference`: the can-train-and-test labels and the ROAD injection labels), and `performance` (hardware, budget `{ram_kb: 16, flash_kb: 128, target: ESP32-S3}`). Set `used_by` in `topics/security/compliance/datasets.yaml` for `can-train-and-test` (training and evaluation) and `road` (evaluation).
- [ ] T032 [US4] Write `zoo/models/picket-forest/releases/0.1.0.compliance.yaml` with the compliance harness. Set `runtime: mcu` and `sbom: sbom.cdx.json` (check C-G4). It also records:
  - AI Act classification: not high-risk, not a safety component, open-source exclusion; intended purpose is research and monitoring;
  - the dual-use note;
  - datasets with attribution;
  - no personal data in published files.

  Then run `uv run zoo compliance render` and `uv run zoo compliance scan-publish --model picket-forest --version 0.1.0`.
- [ ] T033 [US4] Update `zoo/models/picket-forest/model.yaml` card texts from the report:
  - the limitations name the numbers for false alarms per hour on unknown vehicles, recall on unseen scans and fuzzing, masquerade not detected, and classic CAN only (SC-007);
  - the text states that the published model is trained on all four vehicles and has no untouched test set, and that quality comes from the per-set protocol;
  - `how_to_run` uses the joblib host reference and `device_usage` the C API.

  Only claims supported by the R10 outcome (SC-004).
- [ ] T034 [US4] Stage and check.
  - Run `uv run zoo stage picket-forest 0.1.0 --from "$MMZ_DATA/derived/picket-forest/export"`, `uv run zoo compliance signoff --model picket-forest --version 0.1.0` (owner), and `uv run zoo check picket-forest 0.1.0 --offline`.
  - **GATE**: all offline rules pass (SC-005).
  - Record the gate output in `validation.md`.
- [ ] T035 [US4] Publish. Open the PR for `007-picket-forest-release` and get CI green. After the merge, tag `picket-forest/v0.1.0`:
  - `release-verify` passes every rule and produces the card preview;
  - the owner reviews and approves with `release-publish` (`confirm=picket-forest/v0.1.0`).

  Verify that the model is public, in the security collection, and that `zoo audit` reports OK. Record everything in `validation.md`.

**Checkpoint**: picket-forest 0.1.0 is public (SC-008).

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T036 [P] Update `topics/security/tasks/can-ids.md`: the frozen benchmark, the headline definitions, the R10 outcome, and the ESP8266 as named substitute hardware.
- [ ] T037 [P] Update `README.md` (security row: picket-forest released, link to the report) and `topics/security/README.md`.
- [ ] T038 Run `uv run ruff check`, the full default test suite, `uv run zoo validate --all`, `uv run zoo compliance check --ci`, `uv run reuse lint` and `scripts/import/check_language.py`. Record the results in `validation.md`.
- [ ] T039 [P] Update the memory note for the security topic with the published status and the 0.2.0 plan (rule layer, calibration).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: no dependencies; T001 needs network access and disk space.
- **Foundational (T003–T006)**: after Setup; blocks US1 and US2. T006 blocks US3.
- **US1 (T007–T010)**: after Foundational.
- **US2 (T011–T018)**: after US1, because evaluation needs the frozen manifest. T014 trains the release model on demand for ROAD, and T026 reuses it.
- **US3 (T019–T025)**: after T006; independent of US1 and US2 (synthetic data only).
- **US4 (T026–T035)**: T026 after US1 (hyperparameter selection on validation captures). T027–T030 after T022 (scorer) and T026. T033 after T018 (report). T034 after US3 and all of T026–T033. T035 last.
- **Polish (T036–T039)**: after T035, except T038, which runs before the PR in T035 as well.

### User Story Dependencies

- US1 → US2 (frozen manifest).
- US3 is independent of US1 and US2.
- US4 needs US1 (selection), US2 (card claims) and US3 (gate).

### Within Each User Story

Tests first (T003, T007, T011–T012, T019–T021), then implementation, then the real runs (T010, T017–T018, T030), which are recorded in `validation.md`.

### Parallel Opportunities

- T002 alongside T001; T006 alongside T003–T005.
- **US3 can be built entirely in parallel with US1 and US2.**
- T011 and T012 together; T019, T020 and T021 together.
- T028 (firmware project) in parallel with T026–T027.
- T036, T037 and T039 together.

## Parallel Example: User Story 3 while US1/US2 run

```text
Developer A: T007 → T008 → T009 → T010 (freeze), then T011–T018 (evaluation; the full run takes hours)
Developer B: T019, T020, T021 (tests) → T022 → T023 → T024 → T025 (gate for tree models)
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Setup and Foundational (the metrics fix).
2. Freeze `can-ids-v1` (US1).
3. **Stop and validate**: the manifest is reproducible and duplicates are resolved. This alone settles whether the benchmark is clean.

### Incremental Delivery

1. US1: benchmark frozen.
2. US2: honest numbers, plus the R10 outcome and the decision on what the card may claim.
3. US3: the gate can verify tree models (independent; can land early).
4. US4: measurements on the host, QEMU and the D1 mini, then release 0.1.0.

## Notes

- **Test data and leakage**:
  - Test captures never choose thresholds, alarm points or hyperparameters (constitution III).
  - If the GATE in T018 fails, stop: a leak is a benchmark problem and leads to a new benchmark version, not a quick fix.
- **Data never published**: no dataset frame is committed or staged. The examples and the firmware test vectors are synthetic.
- **Origins**: emulator latency is never presented as hardware latency. The ESP8266 is always named as a substitute for the ESP32-S3.
