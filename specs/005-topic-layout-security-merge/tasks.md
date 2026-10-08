---
description: "Tasks for feature 005: topic layout and merge of mobility-security-ml"
---

# Tasks: Topic layout and security merge

**Input**: Design documents from `specs/005-topic-layout-security-merge/`: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. The repository is test-driven (363 tests before this feature), and the guards this feature adds (training refusal, license compatibility, device evidence, no data in history) are only trustworthy with tests.

**Organization**: Tasks are grouped by user story (US1–US5 from spec.md). **(ops)** marks a step that touches GitHub or Hugging Face settings or an external repository. **GATE** marks a point where work stops until a condition holds. Source branches: **goldberg** = `origin/claude/clever-goldberg-ygio83`, **volta** = `origin/claude/cool-volta-rqsgdx` of `mhabedank/mobility-security-ml` (clone at `/tmp/msml`; re-clone with `gh repo clone mhabedank/mobility-security-ml /tmp/msml` if missing).

**Order note**: The stories build on each other: the layout (US1) is where imports land (US2), and datasets (US3) and the edge release path (US4) work on imported code. Within each story, tasks marked [P] can run in parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US5 from spec.md

---

## Phase 1: Setup

**Purpose**: Baseline and tooling before anything moves.

- [ ] T001 Record the baseline: run `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --offline pytest -q` and `uv run zoo validate --all` on branch `005-topic-layout-security-merge` and write the counts (expected 363 passed, 1 skipped, 1 deselected) into `specs/005-topic-layout-security-merge/validation.md` under "Baseline".
- [ ] T002 [P] Check tools and write versions into `specs/005-topic-layout-security-merge/validation.md`: `git filter-repo --version`, `gitleaks version`, `gh auth status`, `cc --version`, `make --version`; install `gitleaks` with `brew install gitleaks` if missing.
- [ ] T003 [P] Anchor the data ignore in `.gitignore`: replace `data/` with `/data/`, and add `/results/`, `firmware/bench/lib/modelzoo/`, `firmware/bench/.pio/`, `firmware/picket-forest/c/generated/*_model.h`, `firmware/picket-forest/c/generated/test_vectors.h`, `build/` (research R5, contracts/cli.md `edge build`). Verify with `git check-ignore -v data/x src/mobility_model_zoo/datasets/x` that only the first is ignored.

---

## Phase 2: Foundational

**Purpose**: Constitution and import tooling. **No story work starts before this phase is complete.**

- [ ] T004 Amend `.specify/memory/constitution.md` to **1.5.0** (MINOR) per research R12. Edit, keeping all other text:
  - **Sync report**: a new sync-impact report at the top, with the rationale.
  - **Scope note** (lines 35–41): Principles I, II, VII, X and the agreement pilot apply to model-labeled tasks; ground-truth tasks name dataset labels as their reference.
  - **Principle III**: ground-truth tasks report against dataset labels and may say accuracy.
  - **Principle V**: per-runtime budgets. Python: GB RAM, CPU/GPU. Microcontroller: KB flash and RAM on a named board. Every measurement records its origin: real board, emulator or simulator.
  - **Principle VI**: per-topic dataset declarations; share-alike carries over to the model license; NC data is `benchmark_only`.
  - **Principle VIII**: Ludwig is the default for text models; other tasks choose their framework with a justification in their first spec.
  - **Principle IX**: raw-label retention applies to model-labeled tasks.
  - **Resources**: add CI runners and the bench boards.
  - **Project Scope**: one topic = one collection = one `topics/<topic>/` folder; top level only for shared material.
  - **Gate before reporting a result**: split by reference kind.
  - **Footer**: `**Version**: 1.5.0 | **Ratified**: 2026-09-25 | **Last Amended**: 2026-10-08`.
- [ ] T005 [P] Update `README.md` link text if it quotes the constitution version, and add a test `tests/unit/test_constitution_version.py` that the footer version of `.specify/memory/constitution.md` equals `1.5.0` and the sync report mentions "1.4.0 → 1.5.0".
- [ ] T006 Write the path maps as data: `scripts/import/path-map-goldberg.yaml` and `scripts/import/path-map-volta.yaml`, each with `renames:` (list of `{from, to}`, directories end in `/`), `strip:` (list of globs) and `drop:` (files neither renamed nor stripped, with a `reason`), copied exactly from contracts/path-map.md sections B and C.
- [ ] T007 Implement `scripts/import/import_branch.py` (stdlib plus `pyyaml`). Arguments: `--source /tmp/msml`, `--branch <ref>`, `--map <yaml>`, `--out <dir>`. Steps:
  1. Fresh `git clone --no-local --single-branch --branch <ref>` into `<out>`.
  2. List every path that ever existed: `git log --all --format= --name-only | sort -u`.
  3. Fail with exit 2 if any path matches no rename, strip or drop entry, listing the paths.
  4. Run `git filter-repo --force` with `--invert-paths --paths-from-file` for strip and drop, then a second pass with `--path-rename from:to` for every rename.
  5. Write `<out>.merge-log.csv` with columns `branch,old_path,new_path,status,reason`.
- [ ] T008 [P] Write `tests/unit/test_import_branch.py`: build a small git repository in `tmp_path` with three commits (a renamed file, a stripped file, an unmapped file), run `import_branch.py`, and assert:
  - an unmapped path makes it exit 2;
  - after adding a drop entry, the stripped path is absent from `git log --all --name-only`;
  - the renamed file has its original author and date;
  - the merge log lists all three paths.
- [ ] T009 [P] Implement `scripts/import/check_merge_log.py`: reads `topics/security/research/merge-log.md` (Markdown table generated from the two CSVs) and the source branches; exits 0 only if every path of both branches appears with a new path or a reason (SC-001). Test in `tests/unit/test_check_merge_log.py` on a fixture table.

**Checkpoint**: The constitution allows ground-truth edge tasks; the import tool is tested.

---

## Phase 3: User Story 1 - One repository, laid out by topic (Priority: P1) 🎯 MVP

**Goal**: Every topic has `topics/<topic>/`; productdev material has moved there; tests and `zoo audit` are unchanged.

**Independent Test**: quickstart scenario 1. `ls topics/` shows `productdev security condition-monitoring`. No JTBD folder remains at the top level. `pytest` and `zoo validate --all` give the T001 counts plus the new tests. The published `scout-large` links still resolve.

### Tests for User Story 1

- [ ] T010 [P] [US1] Write `tests/release/test_layout.py`: for every topic in `zoo/topics.yaml` except `sandbox`, `topics/<id>/README.md` and `topics/<id>/datasets.yaml` exist; none of `guideline/`, `reports/`, `benchmarks/`, `spike/`, `deploy/`, `docs/recipes/` exists at the top level; `zoo validate --all` fails on a fixture registry with a missing topic folder.
- [ ] T011 [P] [US1] Write `tests/release/test_deprecate_from_tag.py` with the FakeHub and a fixture git repository: tag `m-x/v0.1.0` with `model.yaml` figure path `docs/f.png`, then move the figure and change `model.yaml` on `main`; `zoo deprecate` for 0.1.0 renders figure URLs with `docs/f.png` at the tag (research R14).

### Implementation for User Story 1

- [ ] T012 [US1] `git mv` per contracts/path-map.md section A:
  - `guideline/` → `topics/productdev/guideline/`
  - `reports/{pilot-v2,spike-v2,scout-large}/` → `topics/productdev/reports/…`
  - `benchmarks/` → `topics/productdev/benchmarks/`
  - `spike/` → `topics/productdev/spike/`
  - `deploy/railway-perf/` → `topics/productdev/deploy/railway-perf/`
  - `docs/recipes/` → `topics/productdev/recipes/`
  - `scripts/{pilot,span,railway,spark}/` → `topics/productdev/scripts/…`

  Commit only the renames ("Move productdev material to topics/productdev"), so rename detection stays exact.
- [ ] T013 [US1] Update path references:
  - **Configs** (`configs/productdev/jtbd/`):
    - `pilot-v1.yaml`: `guideline`, `examples`, `benchmarks`, `reports` → `topics/productdev/…` (lines 7–8, 15–16).
    - `span-train-v1.yaml` (lines 10–11, 21) and `spike-v1.yaml` (lines 8–9, 19): same change.
    - `domain/mobility.yaml:2`: the comment.
  - **Code**:
    - `src/mobility_model_zoo/productdev/jtbd/span/results.py`: `FIGURE` (line 314) → `topics/productdev/recipes/figures/scout-large-pareto`; draft `doc` (line 405) → `topics/productdev/recipes/scout-large.md`.
    - Docstrings in `src/mobility_model_zoo/productdev/jtbd/config.py:82` and `freeze.py:3`.
  - **Scripts** (all under `topics/productdev/scripts/`):
    - `pilot/categorize_contested.py:78`
    - `railway/collect.py:31`
    - `railway/stage.sh:2,10,16`
    - `span/comparisons.py:39`
  - **Deploy**: `topics/productdev/deploy/railway-perf/run.sh:20`.
  - **Tests**:
    - `tests/unit/test_pareto_student.py:48-49`
    - `tests/unit/span/test_record.py:58`
    - `tests/unit/test_no_spike_imports.py:25` (path `topics/productdev/spike`)
    - `tests/fixtures/mini-corpus/domain.yaml:2`

  Do not edit `zoo/models/scout-large/releases/0.1.0.yaml` or `0.1.1.yaml`.
- [ ] T014 [US1] In `zoo/models/scout-large/model.yaml` lines 24 and 26, change figure paths to `topics/productdev/recipes/figures/scout-large-quality-speed.png` and `…/scout-large-10k-texts.png`. Widen `card.figures[].path` in `src/mobility_model_zoo/release/schemas/model.schema.json` to `^(docs|topics)/[a-z0-9/_.-]+\.png$`. Create `specs/005-topic-layout-security-merge/contracts/` copies of all four schemas, and point `tests/release/test_schemas.py:17-21` at the new folder (research R13).
- [ ] T015 [US1] Make `zoo deprecate` and every re-render of a published version read `zoo/models/<name>/model.yaml` at git tag `<name>/v<version>`, using `git show <tag>:<path>`, in `src/mobility_model_zoo/release/publish.py` and `card.py:78-83`. Fall back to the working tree only for unpublished versions. T011 passes.
- [ ] T016 [US1] Topic registry: widen the topic `id` pattern in `src/mobility_model_zoo/release/schemas/topics.schema.json:17` and `model.schema.json:33` to `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` with `maxLength: 24`, in both the packaged schemas and the contract copies. Add to `zoo/topics.yaml`:
  - `{id: security, title: Automotive security, description: "Small models that detect attacks on vehicle buses and radio interfaces, built to run on microcontrollers.", hf_collection: null}`
  - `{id: condition-monitoring, title: Condition monitoring, description: "Small models that watch machines and movement through sensors, built to run on microcontrollers.", hf_collection: null}`

  Check that `zoo index` and the card do not assume a non-null `hf_collection` for non-sandbox topics; render "collection not yet published" where they do.
- [ ] T017 [US1] Extend `zoo validate --all` in `src/mobility_model_zoo/release/cli.py:66-102`: for every non-sandbox topic, require `topics/<id>/README.md` and `topics/<id>/datasets.yaml`. Until US3 lands, the datasets file is checked for existence only. T010 passes.
- [ ] T018 [P] [US1] Write `topics/productdev/README.md`: scope, the task `jtbd`, the model `scout-large` with its collection link, and the sections (guideline, benchmarks, reports, recipes, spike, deploy, scripts). Add `topics/productdev/datasets.yaml` with `datasets: []` and a comment that JTBD sources live in the snapshot registry under `data/` (Principle VI, crawl once). Create empty `topics/productdev/research/README.md` that links the pilot reports.
- [ ] T019 [P] [US1] Create skeletons:
  - `topics/security/README.md` and `topics/condition-monitoring/README.md`: scope, tasks, models, "collection not yet published".
  - `topics/security/datasets.yaml` and `topics/condition-monitoring/datasets.yaml`, each `datasets: []`.
  - Empty folders with a `.gitkeep`: `research/`, `reports/`, `recipes/`, `tasks/`.
- [ ] T020 [P] [US1] Write `docs/layout.md`: the top-level rule (shared vs. per topic, research R3), the tree from contracts/path-map.md section D, and where a new topic or task puts code, configs, research, datasets, reports, recipes and firmware. Link it from `README.md` and `docs/adding-a-model.md` (FR-005).
- [ ] T021 [US1] Run the full suite, `zoo validate --all` and `uv run zoo audit` (uses `HF_RELEASE_TOKEN` from `.env`). Record the results under "US1" in `specs/005-topic-layout-security-merge/validation.md`. **GATE**: same pass count as T001 plus the new tests, and audit ok for `scout-large` 0.1.0 and 0.1.1.

**Checkpoint**: The layout exists and nothing published broke.

---

## Phase 4: User Story 2 - Security and condition-monitoring content arrives (Priority: P1)

**Goal**: Both branches are in the zoo with history, in the topic layout, reconciled, with four registered models.

**Independent Test**: quickstart scenarios 2, 3 and 5 (`zoo check` part). `git log --follow` shows the original commits. No stripped path is in history. `zoo check <model> 0.1.0 --offline` gives a definite list for each of the four models.

### Import

- [ ] T022 [US2] Run `uv run python scripts/import/import_branch.py --source /tmp/msml --branch claude/clever-goldberg-ygio83 --map scripts/import/path-map-goldberg.yaml --out /tmp/import-goldberg`.
  - Fix the map until it exits 0, then re-run T006/T007 tests.
  - Inspect the result: `git -C /tmp/import-goldberg log --stat | head -100`.
  - Confirm `git -C /tmp/import-goldberg log --all --name-only --format= | grep -E 'test_vectors|\.bin$|joblib|_model\.h'` is empty.
- [ ] T023 [US2] Merge goldberg: `git remote add import-goldberg /tmp/import-goldberg && git fetch import-goldberg && git merge --allow-unrelated-histories --no-ff import-goldberg/claude/clever-goldberg-ygio83 -m "Import mobility-security-ml goldberg branch (can-ids-tiny, research) with history"`, then `git remote remove import-goldberg`. Resolve no content conflicts by hand: if any path collides, fix the map and redo T022.
- [ ] T024 [US2] Same as T022 for volta: `--branch claude/cool-volta-rqsgdx --map scripts/import/path-map-volta.yaml --out /tmp/import-volta`. Confirm that `firmware/lib/modelzoo`, `models/` and `hub.py` are absent from the whole rewritten history.
- [ ] T025 [US2] Same as T023 for volta, with the merge message "Import mobility-security-ml volta branch (hil bench, datasets, edge models) with history".
- [ ] T026 [US2] Generate `topics/security/research/merge-log.md` from `/tmp/import-goldberg.merge-log.csv` and `/tmp/import-volta.merge-log.csv`: one table, columns branch, old path, new path or "dropped", reason. Add the reasons from research R4 and R9. Run `scripts/import/check_merge_log.py` → exit 0.
- [ ] T027 [US2] Run `uv run zoo history-check` (gitleaks over all commits plus forbidden paths). **GATE**: clean. If gitleaks or the forbidden-path check reports any finding, fix the map and redo the import before any further commit.

### Package integration

- [ ] T028 [US2] Fix imports in the moved modules to the new package paths:
  - `hilbench.data` → `mobility_model_zoo.datasets`
  - `hilbench.ml.{model,quant,reference,floatnet,codegen,tflite_import,train}` → `mobility_model_zoo.edge.int8.…`
  - `hilbench.ml.datasets` → `mobility_model_zoo.edge.bench.synthetic`
  - `hilbench.ml.zoo` → `mobility_model_zoo.edge.bench.reference_models`
  - `hilbench.ml.features` → `mobility_model_zoo.condition_monitoring.sound_anomaly.features`
  - `hilbench.*` → `mobility_model_zoo.edge.bench.*`
  - `msml.*` → `mobility_model_zoo.security.can_ids.*`

  Add the `__init__.py` files for `security`, `security/can_ids`, `condition_monitoring`, `condition_monitoring/sound_anomaly`, `condition_monitoring/activity`, `edge` and `datasets`. Remove `hub` from `edge/bench/cli.py`.
- [ ] T029 [US2] Replace hard-coded repository paths:
  - `edge/bench/config.py` `REPO_ROOT` and `reference_models.py` `parents[2]` → the repository root found by walking up to `pyproject.toml`.
  - `models/zoo` → a build directory `build/edge/models/` (gitignored); `models/custom` → `--model` options.
  - `firmware/lib/modelzoo/src` → `firmware/bench/lib/modelzoo/src`.
  - `firmware/platformio.ini` → `firmware/bench/platformio.ini`.
  - `hil/*.yaml` unchanged.
  - Env vars: `HILBENCH_DATA` → `MMZ_DATA` (default `~/.cache/mobility-model-zoo/datasets`); `HILBENCH_BOARDS` → `MMZ_BOARDS`.
  - Lock directory `/var/lock/hilbench` → `/var/lock/mmz-edge` in `edge/bench/lock.py` and `hil/setup-host.sh`.
- [ ] T030 [US2] Make the generated firmware model sources a build step:
  - Add a PlatformIO pre-script `firmware/bench/scripts/gen_modelzoo.py` that calls `mobility_model_zoo.edge.int8.codegen.write_zoo_sources` with the synthetic reference models from `edge.bench.reference_models.build()` (deterministic, fixed seeds) plus `--model` npz files passed in `MMZ_EDGE_MODELS`.
  - Have `firmware/bench/native/Makefile` call the same generator.
  - Sanitise model names to C identifiers (`picket-mlp` → `picket_mlp`) in `codegen.py`, with a test in `tests/edge/int8/test_codegen_names.py`.
- [ ] T031 [US2] Replace the committed synthetic eval sets (`can_ids_mlp.eval.npz`, `sensor_ae.eval.npz`) with generation in `reference_models.build()`. Change `tests/edge/bench/test_models_zoo.py` to build the reference models into `tmp_path`, and verify that two builds give byte-identical npz files.
- [ ] T032 [US2] Split `src/mobility_model_zoo/edge/train_real.py`:
  - `security/can_ids/mlp.py`: ROAD candump parsing, 32 features, Keras MLP, TFLite int8, bit-exact check.
  - `condition_monitoring/sound_anomaly/train.py`: MIMII.
  - `condition_monitoring/activity/train.py`: UCI HAR.
  - `edge/int8/keras_export.py`: shared int8 conversion and `verify_with_interpreter` wrapper.

  Split `tests/edge/test_train_real.py` the same way into `tests/security/can_ids/test_mlp.py`, `tests/condition_monitoring/test_sound_anomaly_train.py` and `tests/condition_monitoring/test_activity_train.py`. Delete `edge/train_real.py`. Outputs go to `--out` (default `$MMZ_DATA/derived/<model>/`), never into the repository.
- [ ] T033 [US2] Port goldberg `security/can_ids/forest.py` (former `pipeline.py`) to the zoo:
  - **Paths:** `artifacts/` → `--out` (default `$MMZ_DATA/derived/picket-forest/`); generated headers → `firmware/picket-forest/c/generated/` (gitignored, T003); `testvectors` writes into `--out`.
  - **Code:** the dataset loader is `security/can_ids/can_train_and_test.py`; `forest_features.py` compiles `firmware/components/can_features/*.c` (new path) into the ctypes cache under `build/`.
  - **Renames:** `firmware/picket-forest/c/can_ids_tiny.{c,h}` → `picket_forest.{c,h}`, with symbol prefix `picket_forest_`.
- [ ] T034 [US2] Create the common frame format in `src/mobility_model_zoo/security/can_ids/frames.py`:
  - **Columns:** `ts_us:int64, can_id:int32, dlc:int8, b0..b7:uint8, label:int8, capture:str, vehicle:str`.
  - **Readers:** `from_can_train_and_test(dir)` (the existing CSV parser) and `from_road(dir)` (the candump parser moved out of `mlp.py`).
  - **Writer:** `write_parquet(df, path)`.
  - **Tests:** `tests/security/can_ids/test_frames.py` on tiny synthetic CSV and candump files.
- [ ] T035 [US2] Make `security/can_ids/metrics.py` (goldberg) the metric code for both CAN models. `mlp.py` reports frame metrics through it and drops its inline metric code. Keep goldberg `tests/test_metrics.py` (now `tests/security/can_ids/test_metrics.py`) green.
- [ ] T036 [US2] Create the task CLIs per contracts/cli.md: `src/mobility_model_zoo/security/cli.py` (`security can-ids frames|evaluate|freeze|forest …|mlp train`) and `src/mobility_model_zoo/condition_monitoring/cli.py` (`condmon sound-anomaly train|evaluate|freeze`, `condmon activity train|evaluate|freeze`). Register `edge = mobility_model_zoo.edge.bench.cli:main`, `security = mobility_model_zoo.security.cli:app` and `condmon = mobility_model_zoo.condition_monitoring.cli:app` in `pyproject.toml` `[project.scripts]`. `evaluate` and `freeze` may exit 5 ("benchmark not frozen yet") in this feature.
- [ ] T037 [US2] Update `pyproject.toml` per research R16:
  - Extras: `edge = [numpy, pyserial>=3.5, pyyaml>=6, jsonschema]`, `edge-hw = [esptool>=4.7, platformio>=6.1, pytest-xdist>=3.3]`, `edge-train = [tensorflow-cpu>=2.16, tflite>=2.10, ai-edge-litert, scikit-learn>=1.5, emlearn>=0.23, setuptools>=70, pandas>=2.2, pyarrow>=17]`.
  - pytest: marker `hil`, and `addopts = "-m 'not slow and not hil' -p mobility_model_zoo.edge.bench.pytest_plugin"`.
  - ruff: exclude `firmware/**/scripts/*.py`.

  Run `uv lock`. Check that the base dependency list is unchanged (diff `[project].dependencies`).
- [ ] T038 [US2] Make the bench pytest plugin inert unless a test requests `dut` or the session gets `--hil-board`, in `src/mobility_model_zoo/edge/bench/pytest_plugin.py`. Run the full default suite and confirm the jtbd and release tests are unaffected (same counts as T021 plus the imported unit tests).
- [ ] T039 [US2] Run `uv run ruff check --fix` and `uv run ruff format` on the imported code. Fix the remaining findings (I, UP, B) by hand in a commit "Lint imported code to zoo rules". Do not change behaviour; tests stay green.
- [ ] T040 [US2] Run `uv run edge build -t native` and `uv run pytest -m hil --hil-board sim -q`, and record the result under "US2" in `specs/005-topic-layout-security-merge/validation.md`. **GATE**: the simulator HIL suite passes on the generated reference models.

### Tasks and models

- [ ] T041 [P] [US2] Write `topics/security/tasks/can-ids.md` per data-model.md "Task":
  - **Scope in:** per-frame and per-event detection of injection, fuzzing, masquerade and scanning on classic CAN.
  - **Scope out:** CAN FD, automotive Ethernet, response or blocking actions, root-cause attribution.
  - **Reference:** dataset labels.
  - **Benchmark:** `can-ids-v1`, built per research R8 (can-train-and-test four-way splits plus ROAD held-out captures).
  - **Metrics:** frame P/R/F1/FPR/AUC-PR; event episode recall, time to alarm, false alarms per hour (headline). Formulas as in `metrics.py`.
  - **Tool:** `security can-ids`.
  - **Frameworks:** scikit-learn + emlearn for trees, Keras + TFLite int8 for neural nets, each with a justification.
  - **Budget:** at most 16 KB RAM and 128 KB flash on ESP32-S3.
- [ ] T042 [P] [US2] Write `topics/condition-monitoring/tasks/sound-anomaly.md`:
  - **Scope:** unsupervised anomaly score per 10 s clip from one microphone, trained on normal sounds only.
  - **Benchmark:** `mimii-fan-v1`.
  - **Metrics:** clip AUC (headline), pAUC at FPR ≤ 0.1, per machine id.
  - **Mobility relevance and limits:** taken from volta `docs/datasets.md` "Bezug zur Mobilität", in English.
  - **Budget:** at most 64 KB RAM and 256 KB flash.

  Write `topics/condition-monitoring/tasks/activity.md`:
  - **Scope:** six activities from waist-worn 6-axis IMU windows of 2.56 s; no vehicle classes.
  - **Benchmark:** `uci-har-v1`, the official subject-disjoint test split.
  - **Metrics:** accuracy and macro-F1 (headline).
  - **Budget:** at most 32 KB RAM and 128 KB flash.
- [ ] T043 [P] [US2] Create task configs:
  - `configs/security/can-ids/picket-forest.yaml`: the goldberg grid, final choice 30 trees / depth 12 / `min_samples_leaf=20`, alarm rule 3 frames in 200 ms with 1 s hold-off, budget 2 false alarms per hour.
  - `configs/security/can-ids/picket-mlp.yaml`: volta MLP 32-64-32-2, ROAD subsampling 15 %, test captures `_2`.
  - `configs/condition-monitoring/sound-anomaly/hum-fan.yaml`: AE 200-64-64-8-64-64-200, log-mel 5×40, threshold at p95.
  - `configs/condition-monitoring/activity/pace-cnn.yaml`: the CNN layers from research.

  Take the values from the source code. Training commands read them through `--config`.
- [ ] T044 [US2] Register the four models in `zoo/models/<name>/model.yaml` per data-model.md table "Model":
  - **`picket-forest`:** security, can-ids, `runtime: mcu`, Apache-2.0, scikit-learn, tabular-classification, `languages: []`, `base_model: null`.
  - **`picket-mlp`:** security, can-ids, mcu, Apache-2.0, tflite, tabular-classification.
  - **`hum-fan`:** condition-monitoring, sound-anomaly, mcu, CC-BY-SA-4.0, `license_exception: "trained on MIMII (CC BY-SA 4.0); share-alike applies to the weights"`, tflite, audio-classification.
  - **`pace-cnn`:** condition-monitoring, activity, mcu, Apache-2.0, tflite, time-series-classification.
  - **Every model:**
    - `repos{public: mobility-model-zoo/<name>, staging: mobility-model-zoo/<name>-staging}`;
    - card texts: intended use, out of scope (no safety-critical use without a vehicle-specific validation; dual-use note for `picket-*` from goldberg MODEL_CARD.md);
    - input/output description;
    - `install` with `<tag>`;
    - `how_to_run` with the Python host reference;
    - `device_usage` with the C call;
    - limitations taken from the research cards.

  Depends on T062–T064 for schema support. Until then, keep the files on the branch and expect `zoo validate` to fail only on the fields that US4 adds.
- [ ] T045 [US2] Create draft `zoo/models/<name>/releases/0.1.0.yaml` for the four models:
  - `status: experimental`, `change_type: initial`, `files: []`, `staging: null`, `published: null`;
  - `recipe` pointing at the task config and recipe document at the current commit;
  - `provenance.sources` with `dataset:` ids from data-model.md and `permitted_use: training_allowed`; teachers `[]`; `spike_data: false`;
  - `evaluation{benchmark: can-ids-v1|mimii-fan-v1|uci-har-v1, reference_kind: ground_truth}`;
  - `performance.budget{ram_kb, flash_kb, target: ESP32-S3}` from the task budgets.
- [ ] T046 [US2] Move the research results to reports, not zoo results:
  - `topics/security/reports/picket-forest/` keeps goldberg `config.json`, `protocol_results.json` and the QEMU json files.
  - `topics/security/reports/picket-mlp/research-report.json` and `topics/condition-monitoring/reports/{hum-fan,pace-cnn}/research-report.json` hold the volta `*.report.json` contents, recovered with `git -C /tmp/msml show origin/claude/cool-volta-rqsgdx:models/zoo/<old>.report.json`.
  - Each folder gets a `README.md` that says: research run from the old repository, not a frozen benchmark result, weights not in the zoo (research R4).
- [ ] T047 [US2] Run `uv run zoo index` (regenerates `zoo/MODELS.md` with the two new topics) and `for m in picket-forest picket-mlp hum-fan pace-cnn; do uv run zoo check $m 0.1.0 --offline; done`. Record each failure list under "US2" in `validation.md`. **GATE** (after US4): every model exits 2 with only "files not staged", "results missing" and "no real-board latency"; no schema error (SC-004).

### Translation

- [ ] T048 [P] [US2] Translate into English, keeping every citation, URL, `[V]`/`[U]`/`[CONFLICT]` mark, number and license statement (FR-012):
  - `topics/security/README.md`
  - `topics/security/roadmap.md`
  - `topics/security/research/README.md`
  - `topics/security/research/0{1,2,3,4,5}-*.md`
  - `topics/security/reports/picket-forest/research-card.md` (if German)

  Replace `can-ids-tiny` with `picket-forest` where the text refers to the zoo model; keep the old name where it refers to the old repository.
- [ ] T049 [P] [US2] Translate into English:
  - `docs/edge/{hil-bench,ci,extending,hardware,protocol}.md`
  - `topics/condition-monitoring/research/datasets-volta.md`

  Update commands to `edge …`, `zoo data …`, `security …` and `condmon …`, and paths to the new layout. Split `datasets-volta.md`: CAN parts go to `topics/security/research/datasets.md`, sound and IMU parts stay; the dataset table content goes into the `datasets.yaml` files in T051.
- [ ] T050 [US2] Write `scripts/import/check_language.py`, a stopword heuristic: a Markdown file fails if more than 3 % of its words are common German function words (`und, der, die, das, nicht, mit, für, ist, auf, wir`). Run it over `topics/ docs/ README.md`. **GATE**: zero files flagged (SC-007). Add it as a test in `tests/unit/test_docs_english.py`.

**Checkpoint**: Content merged, history intact, four models registered.

---

## Phase 5: User Story 3 - Datasets declared, downloadable, license-checked (Priority: P2)

**Goal**: Per-topic declarations; `zoo data` commands; license check in CI; training refuses `benchmark_only`.

**Independent Test**: quickstart scenario 4.

### Tests for User Story 3

- [ ] T051 [P] [US3] Write `tests/datasets/test_declarations.py`, rejecting each of the following:
  - an id that is not `^[a-z0-9][a-z0-9-]*$`;
  - an id that appears in two topic files;
  - `permitted_use: training_allowed` with `commercial_use: false`;
  - `training_allowed` with an `NC` or `ND` license;
  - `rejected` or `broken_at_source` without `reason`;
  - `license_check: manual` without `license_checked`.

  Both real topic files validate.
- [ ] T052 [P] [US3] Write `tests/datasets/test_guard_and_download.py` with mocked HTTP:
  - `require_training_allowed("syncan")` raises `UsageRefused`;
  - `zoo data download syncan` exits 3;
  - `download can-mirgu` without `--force` exits 3;
  - a download target inside the repository exits 3;
  - `SOURCE.json` has `id, title, license, license_url, attribution, citation, homepage, retrieved_at, files[]{name,url,sha256,bytes}`;
  - `verify` exits 2 on a mocked Zenodo license change and reports `manual` entries with their date.

### Implementation for User Story 3

- [ ] T053 [US3] Create `src/mobility_model_zoo/release/schemas/datasets.schema.json` (and the copy in `specs/005-…/contracts/`) per data-model.md "Dataset declaration":
  - **Fields:** `id, title, use_case, provider (zenodo|uci|bitbucket|url), locator, homepage, license (SPDX), license_url, license_check (api|manual), license_checked (date), permitted_use (training_allowed|benchmark_only), commercial_use, attribution, citation, approx_size_mb, retention, status (active|broken_at_source|rejected), reason, used_by`.
  - **Conditional rules:** as listed in T051.

  Rewrite `src/mobility_model_zoo/datasets/registry.py` to load and validate every `topics/*/datasets.yaml` instead of the Python `SOURCES`/`REJECTED` lists. Keep the `Source` dataclass as the in-memory form.
- [ ] T054 [US3] Fill the declaration files per data-model.md "Initial declarations". Take provider data from volta `registry.py` (recover with `git show origin/claude/cool-volta-rqsgdx:hilbench/data/registry.py`) and goldberg `can_train_and_test.py`.
  - **`topics/security/datasets.yaml`:**
    - `can-train-and-test`: bitbucket `brooke-lampe/can-train-and-test`, CC-BY-4.0, `license_check: manual`, checked 2026-10-08 against DOI 10.11583/DTU.24805533.
    - `road`: zenodo 10462796, CC-BY-4.0, api.
    - `can-mirgu`: uci 1035, `broken_at_source`, reason "UCI archive zero-filled in place of header and data start; not recoverable".
    - `syncan`, `hcrl-car-hacking`, `tue-can-v2`, `gem-can`: `benchmark_only`, status `rejected`, reason "non-commercial license".
    - `veremi-extension`, `gps-spoofing-aissou`: CC-BY-4.0, active, `used_by: []`.
  - **`topics/condition-monitoring/datasets.yaml`:**
    - `mimii`: zenodo 3384388, CC-BY-SA-4.0, `locator.zenodo_files: ["6_dB_fan"]`, `zip_members` as in volta.
    - `uci-har`: uci 240, CC-BY-4.0.
    - `dcase2020-task2-dev`, `dcase2021-toyadmos2`, `gnss-interference-mendeley`, `driver-behavior`: `rejected` with reasons.
  - **Every entry:** `retention: "local cache only; delete 12 months after the last training run that used it"`.
- [ ] T055 [US3] Add a `bitbucket` provider to `src/mobility_model_zoo/datasets/download.py`, using goldberg's Bitbucket API listing from `can_train_and_test.py`. `can_train_and_test.py` then only parses. Default root is `$MMZ_DATA`, and the downloader refuses any target under the repository root.
- [ ] T056 [US3] Implement `require_training_allowed(id)` in `src/mobility_model_zoo/datasets/__init__.py`, and call it in every training entry point: `security/can_ids/forest.py` (evaluate, export), `security/can_ids/mlp.py`, `condition_monitoring/sound_anomaly/train.py`, `condition_monitoring/activity/train.py` (FR-017).
- [ ] T057 [US3] Add the `zoo data` command group to `src/mobility_model_zoo/release/cli.py` (`list, info, verify, download, path, tree, validate`) per contracts/cli.md, delegating to `mobility_model_zoo.datasets`. Remove the `data` group from `edge/bench/cli.py`. `zoo validate --all` also runs `zoo data validate`.
- [ ] T058 [US3] Create `.github/workflows/datasets.yml`:
  - **Triggers:** `schedule: cron "23 5 * * 1"`, `workflow_dispatch`, and push on `topics/*/datasets.yaml` or `src/mobility_model_zoo/datasets/**`.
  - **Job:** `uv sync --extra edge --extra release`, then `uv run zoo data verify`.
  - **Restrictions:** no downloads; no secrets.

**Checkpoint**: Datasets are declared and guarded.

---

## Phase 6: User Story 4 - Edge models can be built, verified and released (Priority: P2)

**Goal**: The release format, gate and card support `runtime: mcu`; the bench produces device measurements; CI runs simulator, QEMU and firmware builds.

**Independent Test**: quickstart scenario 5.

### Tests for User Story 4

- [ ] T059 [P] [US4] Extend `tests/release/fixtures/registry/` with an mcu fixture model `edge-fixture-tiny` (topic `sandbox`, `runtime: mcu`), plus an int8 npz from `edge.bench.reference_models`, three `examples/*.json` and performance results with `origin`. Update `tests/release/fixtures/golden/` with its expected card.
- [ ] T060 [P] [US4] Write `tests/release/test_edge_rules.py`:
  - **Rule 1:** fails for an mcu model without `device_usage`; fails for a python model with empty `languages`.
  - **Rule 6:**
    - fails when a source `dataset` is undeclared;
    - fails when the declared license differs from the source license;
    - fails for a `CC-BY-SA-4.0` source with an Apache-2.0 model;
    - fails for an NC training source;
    - passes for `hum-fan`-like settings.
  - **Rule 10:** `ground_truth` requires the sentence "Quality is measured against the labels of the datasets named below, on test data not used for training." and allows "accuracy"; `model_consensus` keeps the agreement sentence and the ban.
  - **Rules 12/13:** mcu examples must match bit-exactly on the host reference; one changed expected byte fails.
  - **Rule 15:** missing `flash_kb` fails; `status: stable` with only an emulator latency fails; `experimental` with an emulator latency passes.
  - **Regression:** `scout-large` and `sandbox-pipeline-tiny` fixtures still pass every rule.
- [ ] T061 [P] [US4] Write `tests/release/test_card_mcu.py`. The mcu card renders:
  - tags `tinyml`, `microcontroller` and the target name;
  - "How to run it" with the Python host snippet and a `c` block from `device_usage`;
  - "Budget: {ram_kb} KB RAM, {flash_kb} KB flash on {target}.";
  - a "Measured on" column showing hardware and origin;
  - a provenance table with dataset, provider, license and attribution, plus the sentence that the dataset is not redistributed.

  The python card output for `scout-large` is byte-identical to the current golden file.

### Implementation for User Story 4

- [ ] T062 [US4] Change `src/mobility_model_zoo/release/schemas/model.schema.json` per contracts/release-format.md:
  - `runtime` enum `python|mcu`, default `python`;
  - `languages` `minItems: 0`;
  - `base_model` and `base_model_license` nullable for all topics;
  - `card.device_usage` optional string;
  - figure path pattern (done in T014).

  Update the contract copy.
- [ ] T063 [US4] Change `release-record.schema.json`: `performance.budget` becomes `oneOf` `{ram_gb>0, gpu: false}` | `{ram_kb>0, flash_kb>0, target}`; add `provenance.sources[].dataset` (optional, pattern `^[a-z0-9][a-z0-9-]*$`) and `evaluation.reference_kind` enum `model_consensus|ground_truth`. Change `results.schema.json`: add `metrics[].origin` enum `real_board|emulator|simulator|host`, and remove the "accuracy" name ban from the schema (it moves to rule 10). Update the contract copies. Published records must validate unchanged; check with a test over `zoo/models/*/releases/*.yaml`.
- [ ] T064 [US4] Update `src/mobility_model_zoo/release/gate.py`:
  - **Rule 1:** the conditional checks.
  - **Rule 6:** dataset declarations and share-alike/NC checks via `mobility_model_zoo.datasets`.
  - **Rule 10:** the quality sentence depends on `reference_kind`; constant `GROUND_TRUTH` next to `AGREEMENT`.
  - **Rules 12/13:** mcu branch through `edge.int8.reference.run_model` on the staged npz.
  - **Rule 15 `device_evidence`:** add it to the rule table (`gate.py:40-55`), the run order (`:390`) and `OFFLINE_RULES` in `cli.py:19`.
  - **Rule 2:** keep, with the topic pattern from T016.

  T060 passes.
- [ ] T065 [US4] Update `src/mobility_model_zoo/release/templates/model_card.md.j2` and `card.py` per contracts/release-format.md "Model card template". Keep the python path byte-identical (T061). `publish.py` `_record_template` (`:73-96`) writes the mcu budget shape when `runtime: mcu`. `forbidden_upload` keeps rejecting `data/`, and also rejects `*.eval.npz`.
- [ ] T066 [US4] Implement `edge measure MODEL.npz -b BOARD --out FILE.json` in `src/mobility_model_zoo/edge/bench/cli.py`. It runs the performance suite for one model and writes performance metrics `latency_us`, `latency_p99_us`, `flash_kb`, `ram_kb`, `arena_bytes` in `results.schema.json` format, with `hardware` from the board inventory and `origin` from the board kind: `native` → `simulator`, qemu flasher → `emulator`, otherwise `real_board`. Test in `tests/edge/bench/test_measure.py` against the simulator.
- [ ] T067 [US4] Update CI in `.github/workflows/ci.yml`:
  - Job `test`: `uv sync --extra jtbd --extra release --extra edge` (no `--all-extras`, so no TensorFlow), then ruff, pytest, `zoo validate --all`.
  - New job `edge-sim`: `uv run edge build -t native && uv run pytest -m hil --hil-board sim -q`.
  - New job `edge-qemu`: Espressif QEMU `esp-develop-9.2.2-20250817` from GitHub releases (cached), ESP32 firmware build via PlatformIO, `uv run edge --boards hil/qemu-boards.yaml run -b esp32-qemu --quick`. Port from volta `.github/workflows/ci.yml`, recovered with `git show origin/claude/cool-volta-rqsgdx:.github/workflows/ci.yml`.
- [ ] T068 [US4] Create `.github/workflows/firmware.yml`:
  - **Triggers:** push and pull_request with paths `firmware/**`, `hil/**`, `src/mobility_model_zoo/edge/**`; plus `workflow_dispatch`.
  - **Bench matrix:** the 11 bench targets (`esp8266, esp8266_160mhz, esp32, esp32s3, esp32s3_usb, esp32c3, esp32c3_usb, rp2040, rp2350, stm32f446, nrf52840`), each running `uv run edge build -t <target>`, plus a summary job with RAM and flash per target. Port from volta.
  - **`picket-forest` host check:** a gcc `-Werror` build of `firmware/components/can_features` and `firmware/picket-forest/c` against host scores computed in the job. Port from goldberg `.github/workflows/ci.yml` (recover with `git show`).
- [ ] T069 [US4] Create `.github/workflows/hil.yml`, ported from volta:
  - **Triggers:** `workflow_dispatch` (inputs `boards`, `quick`) and cron `17 2 * * *`.
  - **Runner:** `runs-on: [self-hosted, hil]`, with `if: vars.HIL_RUNNER_ENABLED == 'true'`, so without the variable the job is skipped (US4 scenario 4).
  - **Settings:** timeout 120 min; concurrency group `hil-bench`.
- [ ] T070 [US4] Run `uv run zoo build pace-cnn 0.1.0 --out /tmp/pace-cnn-card` (or the fixture model if `build` requires staged files) and attach the rendered card to `validation.md` under "US4". Then rerun T047. **GATE**: SC-004 holds.

**Checkpoint**: Edge models are releasable through the zoo pipeline.

---

## Phase 7: User Story 5 - Credentials and pipelines in the zoo; old repository retired (Priority: P3)

**Goal**: One documented set of credentials; the old repository points to the zoo, has no secrets and is archived.

**Independent Test**: quickstart scenario 6.

- [ ] T071 [P] [US5] Write `docs/credentials.md` from data-model.md "Credential". The table covers `HF_RELEASE_TOKEN` (GitHub secret; release-verify, release-publish, zoo-audit), `HF_STAGING_TOKEN` (local `.env`, `zoo stage`) and `HIL_RUNNER_ENABLED` (GitHub variable, `hil.yml`). For each: scope, rotation steps (new fine-grained HF token → update secret or `.env` → revoke old token on huggingface.co/settings/tokens), and the rule that secrets are never committed. Add `HIL_RUNNER_ENABLED` and `MMZ_DATA` to `.env.example` as comments.
- [ ] T072 [P] [US5] Write `tests/unit/test_workflow_secrets.py`: parse all `.github/workflows/*.yml`, collect every `secrets.X` and `vars.X`, and assert each name appears in the table of `docs/credentials.md` (FR-022).
- [ ] T073 [US5] (ops) Set the repository variable with `gh variable set HIL_RUNNER_ENABLED --body false -R mhabedank/mobility-model-zoo`. Confirm with `gh secret list -R mhabedank/mobility-model-zoo` that `HF_RELEASE_TOKEN` exists.
- [ ] T074 [US5] (ops) List the private Hugging Face repositories created by the old `hub` workflow. With the release and staging tokens from `.env`, run `HfApi().list_models(author=<org>, search="hilbench")` for `mobility-model-zoo` and the token owners (`whoami`). Write the list (repo id, private, created, last modified) into `specs/005-topic-layout-security-merge/validation.md` under "Old staging repos" for the owner's decision (FR-025). Delete nothing.

**The following run only after the pull request (T079) is merged into `main`.**

- [ ] T075 [US5] (ops) **GATE**: `git -C . log origin/main --oneline | grep "Import mobility-security-ml"` shows both import merges. Ask the owner to confirm the retirement before T076 (outward-facing, hard to reverse).
- [ ] T076 [US5] (ops) Commit a README to the old repository's `main`. Clone `mhabedank/mobility-security-ml`, write `README.md` saying: "This repository is archived. Its content moved to https://github.com/mhabedank/mobility-model-zoo on <merge date>", plus a table of where each part went (from contracts/path-map.md sections B and C: research → `topics/security/research/`, `can-ids-tiny` → `picket-forest`, hilbench → `src/mobility_model_zoo/edge/` and `firmware/bench/`, datasets → `topics/*/datasets.yaml`, models → `picket-mlp`, `hum-fan`, `pace-cnn`), and that the `claude/*` branches stay readable. Push to `main`.
- [ ] T077 [US5] (ops) Delete the old secrets and variables: `gh secret delete HF_RELEASE_TOKEN -R mhabedank/mobility-security-ml`, `gh secret delete HF_STAGING_TOKEN -R mhabedank/mobility-security-ml`, and `gh variable list -R mhabedank/mobility-security-ml` → delete each. Then archive with `gh repo archive mhabedank/mobility-security-ml --yes`. Verify `gh repo view mhabedank/mobility-security-ml --json isArchived` is `true` and the secret list is empty. Tell the owner to revoke the old HF tokens on Hugging Face if they differ from the zoo's (deleting a GitHub secret does not revoke a token).

**Checkpoint**: One repository, one set of credentials.

---

## Phase 8: Polish & Cross-Cutting

- [ ] T078 [P] Rewrite `README.md`. It needs:
  - a topics table: id, title, collection (link or "not yet published"), models;
  - a short "Repository layout" section linking `docs/layout.md`;
  - setup with extras (`edge`, `edge-hw`, `edge-train`);
  - per-topic quick commands (`jtbd …`, `security can-ids …`, `condmon …`, `edge run -b sim`, `zoo data list`).

  Remove the "Later topics, for example cyber security or IoT" sentence. Update `docs/adding-a-model.md` for `runtime: mcu`, device measurements, dataset declarations and task documents.
- [ ] T079 Run the full quickstart (scenarios 1–5) and write the results into `specs/005-topic-layout-security-merge/validation.md`. Run `uv run zoo history-check` again. Push the branch and open a PR "005: topic layout and merge of mobility-security-ml" with `gh pr create`; the body has the summary, the GATE results and the list of old staging repos. **GATE**: CI green on the PR (`test`, `edge-sim`, `edge-qemu`, `firmware`).
- [ ] T080 [P] Update the memory note `project-zoo-scope-broad-mobility` if the topic list changed (security and condition-monitoring now exist). Mark tasks done in this file.

---

## Dependencies & Execution Order

- **Setup (T001–T003)** → **Foundational (T004–T009)** → **US1 (T010–T021)** → **US2 (T022–T050)** → **US3 (T051–T058)** and **US4 (T059–T070)** → **US5 (T071–T077)** → **Polish (T078–T080)**.
- **US2 depends on US1:** the import maps target `topics/…`.
- **US3 and US4 depend on US2** (imported code). They are independent of each other except for two points:
  - T064 rule 6 reads dataset declarations, so it needs T053–T054.
  - T044, T045 and T047 finish only after T062–T064.
- **Order within US2:** T022 → T023 → T024 → T025 → T026 → T027 (GATE) → T028 … T040 (GATE) → T041–T047 → T048–T050.
- **Inside US5:** T075–T077 only after T079's PR is merged.

### Parallel opportunities

- **Phase 2:** T005, T008 and T009 in parallel after T006 and T007 are written.
- **US1:** T010 and T011 in parallel; then T018, T019 and T020 in parallel once T012–T017 are done.
- **US2:**
  - T041, T042 and T043 in parallel;
  - T048 and T049 in parallel;
  - T033 and T034 in parallel after T028;
  - T030, T031 and T032 touch different modules and can run in parallel after T029.
- **US3:** T051 and T052 in parallel; T055 and T056 in parallel after T053.
- **US4:** T059, T060 and T061 in parallel; T067, T068 and T069 in parallel.
- **US5:** T071 and T072 in parallel.

## Implementation Strategy

1. **MVP = US1**: the layout, with productdev moved and nothing broken. It is mergeable on its own as a first PR if the import takes longer.
2. **US2** next. After the T027 GATE (history clean), the import is irreversible on the branch; redo from T022 if a GATE fails.
3. **US3 and US4** make the merged models governable and releasable.
4. **US5** retires the old repository only after the owner confirms (T075).
