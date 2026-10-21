# Research: pace-cnn first release

Feature 021, 2026-10-18. Every decision below follows from the spec ([spec.md](spec.md)), the constitution (3.0.0) and a read of the code on `main` at 60f338b. Code references are given as paths; they describe the state before this feature.

## State before this feature

- `condmon activity train` works: it trains the recipe, exports int8 (`.tflite`, `.npz` QModel), writes `pace-cnn.eval.npz` (1024 real test windows) and `pace-cnn.report.json` to `$MMZ_DATA/derived/pace-cnn/` (`edge/int8/keras_export.py`).
- `condmon activity evaluate` and `freeze` are stubs that exit with code 5 (`condition_monitoring/cli.py`).
- Nothing reads `subject_train.txt` or `subject_test.txt`. Validation is a seeded seventh of the windows, and the normalisation uses all training windows, validation included (`activity/train.py`).
- Metrics: int8 and float accuracy and macro-F1 only. There is no per-class or per-subject result and no confusion matrix. Nothing writes `zoo/models/pace-cnn/results/`.
- Interpreter check: 32 random int8 inputs. The real test windows run only through the host reference.
- The QModel `test_inputs` are 8 random int8 vectors (`edge/int8/tflite_import.py`), so the `.npz` contains no dataset content.
- Determinism: only `tf.keras.utils.set_random_seed`. There is no op determinism and no multi-seed support.
- HIL bench: pace-cnn has never been in a firmware. The tests load their catalogue with `load_zoo()`, which ignores `MMZ_EDGE_MODELS`, while the test parameters come from `bench_models()`. `load_eval` looks in the wrong folder. `edge measure` reports flash and RAM of the whole firmware image. There is no converter from bench results to `performance.json`, and no `budgets:` entry in `hil/targets.yaml`.
- Release gate (18 rules): pace-cnn lacks `results/0.1.0/*.json`, `examples/*.json` (rule 13), `site.yaml` and `zoo/formats/pace-cnn-v1.yaml` (rule 17), `releases/0.1.0.compliance.yaml` (rule 16) and a firmware SBOM (C-G, generator exists only for security models).
- Card: the topic link is rendered before the `condition-monitoring` collection exists. Datasets with `used_by` force a text snapshot in `scan-publish`, so non-text datasets keep `used_by: []` and the card's attribution table stays empty. Card lint C-C2 is expected to flag "Fall detection as a safety function".

## R1. Benchmark `uci-har-v1`

- **Decision**: Test split is the official UCI HAR test set (9 of 30 subjects, 2,947 windows). Validation is 3 of the 21 training subjects (one seventh), drawn once with a dedicated validation seed (`2026`, separate from the training seed). Normalisation constants come from the remaining 18 training subjects only. `condmon activity freeze` writes `topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json` and refuses any later change, following the can-ids manifest pattern (`security/can_ids/benchmark.py`: rebuild, compare without `frozen_at`, refuse on difference). The logic lives in `condition_monitoring/benchmark.py`, so `hum-fan` can reuse it within the topic.
- **Subject identifiers (spec FR-003 vs FR-028)**: The manifest does not list subject numbers. It records the derivation (official split files, validation rule, seed, subject counts) and the SHA-256 of each sorted subject list and of each split's window data. This is reproducible from the dataset and keeps subject numbers out of public files. FR-003 is reworded accordingly.
- **Single source of the split values**: `validation_seed` (2026) and the rule "a seventh of the training subjects" live in one benchmark constant in the activity code. The recipe config states them only as text, which `load_config` keeps equal to the code. A changed seed is tested by patching that constant (quickstart V1).
- **Rationale**: Windows overlap by 50 %, so a validation set drawn by window holds near-copies of training windows and overstates validation results. Subject-wise validation matches the subject-wise test split. The benchmark has never been used, so its definition can still change (constitution IX).
- **Alternatives considered**: Random windows (today) were rejected because of the leakage. Leave-one-subject-out cross-validation was rejected because the recipe trains for a fixed number of epochs, validation selects nothing, and cross-validation would add cost without informing a decision. A shared freeze module across topics was rejected for now: security and productdev have different manifests, and the constitution extracts shared code only when it is needed.

## R2. Pre-registration record

- **Decision**: `configs/condition-monitoring/activity/pace-cnn-criteria.yaml`, modelled on `configs/productdev/jtbd/decision-criteria.yaml`. It holds version, date, rationale, benchmark, recipe config path, seeds (`candidate: 0`, `spread: [1, 2, 3, 4]`), the selection rule, success criteria (FR-019), kill criteria (FR-009) and budgets (FR-014). `condmon activity train` refuses to run if the file is untracked or modified in the working tree, and it records the file's commit and SHA-256 in the run report. An amendment adds a new `version` with a rationale. The old version stays in git, and the report names the version used.
- **Rationale**: Git history proves that the criteria predate the results. The constitution's gate before an experiment is enforced by the tool, not by discipline.
- **Alternatives considered**: Prose pre-registration in research.md (the picket-forest precedent) cannot be checked by a tool. Hard-coding the criteria in Python mixes policy with code.

## R3. Mechanical selection (Principle XI)

- **Decision**: There is no selection step. The recipe trains a fixed 20 epochs without early stopping. The model after the last epoch of seed 0 is the release candidate. Seeds 1–4 are trained the same way and reported only as spread. Validation results are reported as information. Success, kill and status are computed by `condmon activity evaluate` from the criteria file. Claude writes the code and runs the commands but chooses nothing by looking at results.
- **Rationale**: FR-008 and Principle XI forbid any Claude output as a selection signal. Without a selection step there is no signal to give.
- **Alternatives considered**: Best-validation-epoch checkpointing is a mechanical rule too, but it adds a selection that has to be explained. The existing recipe has none.

## R4. Determinism and reproducibility

- **Decision**: Add `tf.config.experimental.enable_op_determinism()` next to `set_random_seed` in `train_main`. The run report records the TensorFlow and Keras versions resolved by `uv.lock` (2.21.0 / 3.15.1 today), the platform and the SHA-256 of the `.npz`. The reproducibility check (FR-013) retrains seed 0 on the same machine and compares the `.npz` SHA-256. If they differ, it compares the int8 metrics and reports the deviation.
- **Rationale**: On CPU with op determinism, identical results are expected. The check measures this instead of assuming it.
- **Alternatives considered**: Pinning TensorFlow in `pyproject.toml` was rejected; `uv.lock` already pins it for reproduction, and the run report records the version.

## R5. Metrics and deterministic checks

- **Decision**: `condmon activity evaluate` runs the frozen test split (2,947 windows) through the int8 host reference.
  - **Headline metrics**: `int8_macro_f1` and `int8_accuracy`, both against the UCI HAR dataset labels.
  - **Further metrics**: per-class `int8_f1_<class>` (six rows); `int8_macro_f1_worst_subject` and `int8_macro_f1_subject_range` (subjects ranked, never named); the seed spread `int8_macro_f1_seed_min|mean|max`; `float_accuracy` and `float_macro_f1` marked informative; the deterministic check `tflite_interpreter_mismatches`, which runs over all 2,947 quantised test windows instead of 32 random inputs.
  - **Report only, not in `quality.json`**: the confusion matrix and validation results go to the evaluation report.
- **Rationale**: These are the constitution's metric naming rule (reference stated), the int8 result as headline, the deterministic check on its own, and the spec's FR-010–FR-012. The results schema allows no extra keys, so per-class and per-subject results are separate metric rows.
- **Alternatives considered**: Showing the confusion matrix as a card figure is possible (`card.figures`), but it would be a new figure type for the site. It stays in the report, linked from the card.

## R6. Status verdict

- **Decision**: `evaluate` writes `verdict.json` into the evaluation report: each criterion with its measured value, its threshold and met or missed, the kill outcome, and the derived status. For 0.1.0, the criterion "transfer to mobility data tested" is always missed, so the status is `experimental`. `card.unmet_criteria` in `model.yaml` lists the missed criteria with their values. A unit test checks that every missed criterion in `verdict.json` appears in the card, and rule 9 traces every number on the card to the results.
- **Constraint**: Rule 18 allows at most five items for `unmet_criteria` plus `limits_short`. If several quality criteria are missed, they are grouped into one item ("quality thresholds: …").

## R7. Device footprint and latency

- **Decision**: The footprint of the model on the device is defined in [contracts/records.md](contracts/records.md#model-footprint):
  - **flash**: the model's constant data plus the int8 engine code it uses;
  - **RAM**: the arena, the input and output buffers, and the engine's static data.

  It is read from the symbol sizes of the ELF built for the board's target (`edge measure --footprint model`). The whole-image size is reported as information. Latency is the average over at least 100 inferences on the board, from the bench's benchmark test. The budget is added to `hil/targets.yaml` (`esp32: budgets: {pace-cnn: 100000}`). Origin follows `edge measure`: `real_board` for esp32-1 and esp8266-1, `emulator` for the ESP32 QEMU, `simulator` for the host.
- **Rationale**: The budget (128 KB flash, 32 KB RAM) concerns the model, not an Arduino firmware image. Arduino images on ESP32 exceed 128 KB on their own. Symbol sizes are exact and per model.
- **Alternatives considered**: The size difference between builds with and without pace-cnn was rejected: the shared arena is the maximum over all models, so the difference does not equal pace-cnn's RAM. The QModel summary alone was rejected because it does not include engine code.

## R8. HIL harness fixes

- **Decision**:
  - The HIL tests take their model catalogue from the same function as their parameters (`bench_models()`, which includes `MMZ_EDGE_MODELS` and `build/edge/custom/`).
  - `load_eval` looks in `derived/<model>/<model>.eval.npz`.
  - The serial receive buffer on ESP32 and ESP8266 grows to 4096 bytes, because a pace-cnn INFER line is about 2.3 KB and the buffer holds 2048 bytes.
  - All three are checked on the simulator and on the ESP32 QEMU before the real board.
- **Rationale**: Without these fixes the documented route (`MMZ_EDGE_MODELS=… edge run`) fails for any trained model.

## R9. Performance results

- **Decision**: A new command `edge performance` merges the `edge measure` outputs of several boards into `zoo/models/pace-cnn/results/0.1.0/performance.json`.
  - **Plain names**: `flash_kb`, `ram_kb` and `latency_us` carry the reference board's values (`real_board`, ESP32).
  - **Other origins**: suffixed names (`latency_us_esp32_qemu`, `latency_us_esp8266`, `latency_us_host`, `flash_kb_image_esp32`) carry the other boards and the whole-image size.
  - The command lives in `edge/` because `hum-fan` and `picket-mlp` will need it.
- **Rationale**: This follows the picket-forest 0.2.0 file layout that rule 15 already accepts, and it keeps the origin of every value.

## R10. Release files and device sources

- **Decision**: A generic int8 exporter, `edge/int8/release_export.py`, is called by `condmon activity export`. It writes the upload folder:
  - `pace-cnn.npz` and `pace-cnn.tflite`;
  - `c/`: the generated model source for pace-cnn alone and the int8 engine sources;
  - `config.json`: labels, input contract and normalisation constants;
  - `examples/*.json`: at least three synthetic inputs with expected int8 outputs, `source: synthetic`;
  - `sbom.cdx.json`: the SBOM generator moves from `security/can_ids/release_export.py` to `release/sbom.py`, because the int8 exporter is its second user.

  `pace-cnn.eval.npz` is never in the folder (rule 11 forbids it anyway).

  **As built (T044)**: the examples are the first three QModel test vectors (generator `uniform-int8`, version 1, the training seed), so the board's SELFTEST checks exactly the published examples. The C sources are standalone (`codegen.model_sources`): `c/pace_cnn_model.h` defines `PACE_CNN_IN_SIZE`, `PACE_CNN_OUT_SIZE` and `PACE_CNN_ARENA_SIZE`. `card.device_usage` is updated to the shipped headers. A test compiles the shipped `c/` files with the host compiler and checks the examples bit-exactly.
- **Rationale**: A developer can use the model on a device without the zoo's bench firmware, which is the point of US2. Publishing no dataset windows satisfies FR-023 without a redistribution check.
- **Alternatives considered**: Documenting `uv run edge build` as the way to get sources (today's snippet) was rejected: it builds the bench firmware, not standalone sources. Real UCI HAR windows as examples were rejected because they would need `redistribution: allowed` for data of volunteers, which contradicts data minimisation.

## R11. Input preparation (FR-021)

- **Decision**: The 9-channel recipe stays the single candidate. `condition_monitoring/activity/prepare.py` is a host reference that turns a continuous raw stream (accelerometer in g, gyroscope in rad/s, 50 Hz) into int8 windows of 128 × 9 with 50 % overlap. It runs streaming filters: the noise filters the dataset documents, then gravity separation with a Butterworth low-pass at 0.3 Hz, per-channel normalisation with the training-subject constants, and int8 quantisation with the model's input scale and zero point. The card's input contract states the same steps.
- **To verify after download**: The UCI page states 50 Hz, windows of 2.56 s with 50 % overlap and gravity separation by Butterworth low-pass at 0.3 Hz. It does not state units, noise filters or filter orders. These are read from the dataset's own `README.txt` and `features_info.txt` in the downloaded copy before `prepare.py` is fixed. Where the dataset leaves a value open (for example the order of the gravity filter), the value chosen is stated as such on the card.
- **Fidelity check (informative)**: Applying the gravity separation to the dataset's `total_acc` of the training subjects is compared with the dataset's `body_acc` (RMSE and correlation per axis). The result goes to the evaluation report, and the comparison runs locally only. It never changes a filter parameter.
- **Fixing open values**: Every filter value is fixed before `prepare.py` is written, from the dataset's documentation or its paper (Anguita et al., ESANN 2013). A value that both leave open is decided by the owner and recorded here with its date. Nothing is tuned against the fidelity result.
- **Verified after download** (T003, 2026-10-20; sources: the dataset's `README.txt` and `features_info.txt`, and Anguita et al., ESANN 2013, section 2.1):
  - **Units**: `total_acc` and `body_acc` in standard gravity units g (9.80665 m/s²); `body_gyro` in rad/s.
  - **Sampling and windows**: 50 Hz; windows of 2.56 s (128 samples) with 50 % overlap.
  - **Noise filters**: a median filter, then a 3rd-order low-pass Butterworth filter with a corner frequency of 20 Hz, on accelerometer and gyroscope.
  - **Gravity separation**: a low-pass Butterworth filter with a corner frequency of 0.3 Hz on the acceleration; `body_acc` = total minus gravity.
  - **Left open by both sources**: the median filter length, the order of the 0.3 Hz gravity filter, and whether the filters run causally or zero-phase.
- **Owner decision** (2026-10-20, before `prepare.py` was written): a median filter of **3 samples**, a **3rd-order** Butterworth low-pass at 0.3 Hz for the gravity separation (the same order as the dataset's documented 20 Hz noise filter), and **causal** filtering, so the preparation runs as a stream on the device. The card states these three values as chosen by the zoo, not taken from the dataset.
- **Dependencies**: The filters are implemented with numpy only (second-order sections, coefficients written to `config.json`). Correction of the analysis finding U1 (2026-10-20): the `edge` extra does install scipy, transitively through scikit-learn. numpy-only stays the choice, because the host reference then runs the same biquad arithmetic as a device implementation and does not rest on an undeclared transitive dependency. A test compares the filters with `scipy.signal.sosfilt` (equal within 1e-9).
- **Alternatives considered**: A 6-channel variant (total acceleration and gyroscope, no gravity filter) would be easier to deploy. It is the first candidate for the next iteration, not this one: the spec keeps the existing recipe as the single pre-registered candidate, and changing channels without a measured comparison would be an unmeasured change.

## R12. Topic collection before the card is rendered

- **Decision**: `zoo init-model` makes sure the model's topic has a Hugging Face collection. If `hf_collection` is null, it creates the collection as private and writes the slug into `zoo/topics.yaml`. `zoo publish` makes the collection public when it adds the first public model.
- **Rationale**: The card is rendered in release-verify and uploaded unchanged at publish, which the owner approves. Without the collection at render time, the 0.1.0 card links to the organisation page permanently.
- **Alternatives considered**: Re-rendering the card at publish was rejected because the published card would differ from the approved preview. A public empty collection was rejected because it would show an empty topic for days.

## R13. Compliance

- **Decision**:
  - **Non-text datasets**: `scan-publish` exempts datasets that are not text (no text snapshot exists) from the corpus-overlap scan and records why. The `uci-har` declaration then gets `used_by: [pace-cnn@0.1.0]`.
  - **Attribution**: the card section "Training data and attribution" shows each source's `attribution_text`, as CC BY 4.0 requires.
  - **Privacy**: `card_privacy_note` states that the model was trained on motion signals of 30 volunteers, published under numbers by the dataset authors, and that no data or subject number is in the release.
  - **Card wording**: `not_for` and `out_of_scope` are reworded for card lint C-C2 and name the EU AI Act high-risk uses of FR-020.
  - **Compliance record**: `releases/0.1.0.compliance.yaml` is written and rendered; `scan-publish` runs; the owner signs off.
- **As built (T060)**: the source-class schema had no field for the kind of data, so an optional `modality` (`text`, `audio`, `motion_sensor`, `can_frames`) was added; a missing value counts as text. `imu-activity-datasets`, `machine-sound-datasets` and `can-bus-datasets` declare their modality. `scan-publish` records each exempt dataset and its reason under `exempt_sources`.
- **Follow-up outside this feature**: picket-forest's published cards show an empty attribution table for the same reason. A patch release is listed in the plan's follow-ups.
- **AI Act wording**: The card names the uses (monitoring or evaluating persons at work, decisions on insurance, credit or services from a person's movement, identifying or profiling persons) in plain words without quoting the regulation. The exact Annex III wording is checked by the compliance review before signoff, not by this plan.

## R14. Card and status

- **Decision**: Status `experimental`.
  - **`unmet_criteria`**: "Transfer to mobility data tested: not tested (UCI HAR only)", plus every other missed criterion from `verdict.json` with its value.
  - **`limits_short`**: belt-worn sensor without vehicle classes; one dataset of 30 volunteers; sitting and standing confusion, with the measured per-class F1.
  - **`input_output`**: the input contract of R11.
  - **`how_to_run`**: loads `pace-cnn.npz` from the Hub, runs the first example, and says that the input is synthetic and checks the arithmetic, not an activity.

## R15. Site and listings

- **Decision**:
  - **Site and format files**: `zoo/models/pace-cnn/site.yaml` and `zoo/formats/pace-cnn-v1.yaml` are added, the latter with a JSON schema for the examples (`src/mobility_model_zoo/condition_monitoring/activity/pace-cnn-v1.schema.json`). The motif `pace-cnn.svg` exists.
  - **Manual rows**: `README.md` and `topics/condition-monitoring/README.md` are edited by hand at release time.
  - **Automatic**: `zoo/MODELS.md` and the roadmap's delivery update themselves at publish (the roadmap reads `published_at` of the first version).

## R16. Reference hardware and boards

- **Decision**: The reference is esp32-1 (LilyGO LoRa32, ESP32-D0WDQ6-V3, 240 MHz). The release record changes `performance.hardware` to "ESP32 (LilyGO LoRa32, HIL bench)" and `budget.target` to `ESP32`, and the task document follows. Informative measurements are made on the ESP32 QEMU, on esp8266-1 and on the host simulator.
- **Deviation from the clarification**: SAMD21 (mkrzero-1) was to be measured as an informative result. The bench firmware has no SAMD branch (`hal_arduino.cpp` reports chip "unknown" and fails `chip_match`), and the picket-forest SAMD21 run used its own firmware. Adding SAMD support to the bench is outside this feature, so the SAMD21 measurement is deferred and the card does not mention SAMD21.

## R17. Literature context (not for the card)

- Deep models on UCI HAR report about 93 % (CNN-LSTM with self-attention, [PMC9252338](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9252338/)) up to about 97.5 % (frequency-domain CNN, [QUB](https://pure.qub.ac.uk/en/publications/smartphone-based-human-activity-recognition-using-cnn-in-frequenc/)) float accuracy. Medium confidence: secondary listings, setups differ. The often quoted 94.79 % of Ronao & Cho 2016 could not be verified and is not used.
- These values only place the owner's thresholds (int8 macro-F1 and accuracy ≥ 0.90). They set no threshold and appear on no card (constitution III; the pre-zoo report rule).

## R18. Owner steps and outward-facing actions

| Step | Who | Why |
|---|---|---|
| `zoo init-model pace-cnn` (creates the Hub repos and the private collection) | Claude after the owner's go, or the owner | Creates public-facing resources with `HF_RELEASE_TOKEN` |
| Add `pace-cnn-staging` to the repo list of `HF_STAGING_TOKEN` | Owner | Token settings on Hugging Face |
| Connect esp32-1 (and esp8266-1) to the Mac for the bench run | Owner | Physical access |
| Compliance signoff | Owner | `zoo compliance signoff` is an owner action |
| Merge the PR, push tag `pace-cnn/v0.1.0` | Owner (or Claude on request) | Release gate in release-verify |
| Review the preview, start release-publish | Owner | Principle IX: owner approves the card |

## R19. Tracking

MLflow tracking (feature 017) is not on `main`. Runs write their report files as today. If 017 is merged before the runs start, they are logged there as well, and nothing in this feature depends on it.

## R20. Cash and compute

Training and evaluation run on the owner's laptop (CPU): dataset 60 MB, a model of about 7 k parameters (three convolution blocks of 16, 32 and 32 filters and a dense layer of six outputs). Six runs (five seeds and one reproduction). Cash budget 0 €.

## R21. Gate check: no Claude inputs (FR-027)

- **Finding** (`/speckit-analyze`, 2026-10-20): Neither the release gate nor a compliance stage confirms that no input behind a release came from Claude. `presend.py` only blocks routes for new runs. The constitution's gate before a release and FR-027 require that confirmation.
- **Decision** (owner, 2026-10-20): A new check in gate rule 7 ("provenance"). It fails if any of these belongs to the Claude family:
  - a teacher in `provenance.teachers`;
  - a route that the compliance register links to the release;
  - a labeling, data-generation or evaluation run recorded for the release.

  Membership comes from a new field `model_family` on every route in `compliance/providers.yaml` (the two Claude routes get `claude`). A name pattern (`claude`, `anthropic` in model ids and hosting providers) catches entries without the field. The gate output states the confirmation explicitly.
- **Exception**: the frozen benchmark references that Principle XI keeps (pilot-v1, pilot-v2, cluster-v1, spike-v2; decision D-claude-risk-0.1.x), only in their role as benchmark references. They are never accepted as training data or teacher output.
- **Evaluation record**: `evaluation.json` names the evaluated model file (SHA-256 of the `.npz`), as Principle XI requires every evaluation run to record the model behind its output.
- **Regression**: published releases (scout-large 0.1.3, picket-forest 0.2.1) must still pass the offline gate with the new check.
- **Alternatives considered**: Rewording FR-027 so the confirmation stays indirect (no teacher, no route) was rejected by the owner: Principle XI admits no deviation, and an explicit check also covers later releases.

## R22. Benchmark trace in the gate (US1, scenario 4)

- **Finding** (`/speckit-analyze`, 2026-10-20): `train` and `evaluate` refuse a wrong manifest or criteria file, but the release gate itself does not check the runs.
- **Decision**: `evaluation.json` lists each run with seed, `manifest_sha256`, `criteria_version`, `criteria_commit`, `npz_sha256` and `trained_at`. Gate rule 9 then checks, for a release whose benchmark has a frozen manifest under `topics/<topic>/benchmarks/<benchmark>/manifest.json` and an evaluation report under `topics/<topic>/reports/<model>/<version>/`:
  - every run names the SHA-256 of the frozen manifest;
  - every criteria commit is in the history and older than the earliest `trained_at`.

  Releases without a manifest skip this check with a note.
- **Rationale**: The gate can then show that the split was frozen and the criteria were committed before the runs, which is the evidence scenario 4 asks for.
