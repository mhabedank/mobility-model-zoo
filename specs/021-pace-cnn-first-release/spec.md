# Feature Specification: pace-cnn first release (activity recognition on a microcontroller)

**Feature Branch**: `021-pace-cnn-first-release`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "ich möchte pace-cnn nun entwickeln." / "implement pace-cnn"

## Context

`pace-cnn` is registered in the zoo (topic `condition-monitoring`, task `activity`, feature 005) but has never been built or measured through the zoo pipeline. What exists today: the task document (`topics/condition-monitoring/tasks/activity.md`), a training recipe, a model record with a draft card, an unpublished draft release record `0.1.0` with no files and the unmet criterion "Trained and measured on the frozen benchmark", and a pre-zoo research report whose numbers must not set a threshold, pass a gate or appear on a card. The roadmap lists `pace-cnn` as a first release planned for 2026-Q4, stage `in-progress`.

This feature takes `pace-cnn` from registered to published: freeze the benchmark, fix the success and kill criteria before the first run, train and measure the model in the numeric format that runs on the device, measure its budgets on the reference hardware, write an honest card, and publish it through the release pipeline as `experimental`. `pace-cnn` is the first published model of the `condition-monitoring` topic.

## Clarifications

### Session 2026-10-18

- Q: How far does this feature go beyond UCI HAR? → A: UCI HAR only, as planned on the roadmap. Transport-mode recognition is the separate roadmap model `mode-cnn` (working name, 2027-Q1..Q2) and comes later. (The owner first chose "mobility data straight away", then withdrew it on seeing that this is `mode-cnn`.)
- Q: Which int8 thresholds make `pace-cnn` production ready? → A: macro-F1 ≥ 0.90, accuracy ≥ 0.90 and every class F1 ≥ 0.80 on `uci-har-v1`, recorded and reported. Version 0.1.0 is published as `experimental` whatever the results, because its riskiest assumption (transfer to mobility) is untested; `released` needs a later round that tests it.
- Q: Which board is the reference hardware? → A: the ESP32 board on the bench (LilyGO LoRa32, ESP32 classic, 240 MHz), not the ESP32-S3 named in the draft record, which is neither on the bench nor emulated in CI. ESP8266 and SAMD21 are measured as informative results. (Planning, research R16: the SAMD21 measurement is deferred, because the bench firmware has no SAMD branch; the card does not mention SAMD21.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A measured candidate with an honest verdict (Priority: P1)

The owner wants to know how well `pace-cnn` really performs when it is built by the zoo's own pipeline, on the zoo's own frozen benchmark, in the int8 format the microcontroller runs. The pipeline trains the pre-registered recipe, converts it to int8, checks that the int8 host reference is bit-exact, evaluates once on the frozen test subjects and derives the release status by rule from criteria that were written down before the first run.

**Why this priority**: Nothing else can be claimed without this result. It is also the constitution's gate before reporting any result, and it decides whether the release is `released` or `experimental`.

**Independent Test**: Run the recorded recipe against a fresh download of the dataset. The output is a quality report that names benchmark `uci-har-v1` and contains the int8 headline metrics, per-class and per-subject results, the seed spread, the deterministic check and a status verdict, without any later step of this feature.

**Acceptance Scenarios**:

1. **Given** the dataset is downloaded and its licence check passes, and `uci-har-v1` has not been used yet, **When** the benchmark is frozen, **Then** its record lists the subjects of the training, validation and test splits, and every later attempt to change it is refused.
2. **Given** the frozen benchmark and the pre-registration record, **When** the recipe runs, **Then** the report states int8 accuracy and macro-F1 on the bit-exact host reference as headline results, each named as measured against the UCI HAR dataset labels, with float results marked as informative.
3. **Given** a finished report, **When** the status is derived, **Then** it is `released` only if every pre-registered criterion is met, and otherwise `experimental` with every missed criterion and its measured value listed.
4. **Given** any run in which the test subjects were used for training, early stopping, threshold or seed choice, **When** the release gate checks the run, **Then** the gate fails.

---

### User Story 2 - The model runs within budget on a real microcontroller (Priority: P2)

An embedded developer wants to know that `pace-cnn` fits on a common, low-cost board, keeps up with the sensor in real time, and gives on the board exactly the answers it gives on the PC.

**Why this priority**: The zoo's promise for this topic is "runs on a microcontroller". A model that is only measured on the PC does not deliver it, and the constitution forbids presenting emulator or simulator results as hardware results.

**Independent Test**: Build the bench firmware with `pace-cnn` for the reference board and run the bench suite. The output records flash, RAM and latency per window, each with its origin, and the agreement of the board's outputs with the host reference on the published test vectors.

**Acceptance Scenarios**:

1. **Given** the int8 release candidate, **When** the firmware is built for the reference board, **Then** the flash and RAM the model needs (weights, code and working memory) are recorded and compared with the budget.
2. **Given** the board runs the published test vectors, **When** its outputs are compared with the host reference, **Then** every output is equal bit for bit.
3. **Given** a measurement was made only on an emulator or simulator, **When** the status is derived, **Then** the measurement is labelled with its origin and cannot satisfy a criterion that requires the reference hardware.

---

### User Story 3 - A newcomer finds, understands and uses the published model (Priority: P3)

A researcher or developer interested in mobility sensing finds `pace-cnn` on the zoo website or on Hugging Face. Within a minute they understand what it does, what it must not be used for, what its licence allows and how good it really is. They then run it from a fresh environment by following the card.

**Why this priority**: Publication is what counts as delivery on the roadmap and what builds the zoo's reputation, but it only makes sense once stories 1 and 2 hold.

**Independent Test**: In a fresh environment, follow only the model card: install line, download, host example. Six int8 class scores come out. The card shows status, usage class, licence, limits, missed criteria (if any) and the dataset attribution.

**Acceptance Scenarios**:

1. **Given** the published model, **When** a newcomer follows the card's host example in a fresh environment, **Then** six class scores are printed without errors and without any step that is not on the card.
2. **Given** the published card, **When** a reader looks at it, **Then** it states status, usage class and licence, intended use, out-of-scope uses, limitations, every missed criterion with its measured value, the dataset attribution that CC BY 4.0 requires, and how to prepare the model input from raw sensor readings.
3. **Given** the release is published, **When** the zoo's public surfaces are checked, **Then** the `condition-monitoring` collection lists `pace-cnn`, the website has its model page, the topic and model lists show it as published, and the roadmap entry shows it as delivered with its publication date.

---

### Edge Cases

- The licence the provider declares at download differs from the declaration: the download stops and no training starts (fails closed).
- Windows in the dataset overlap by half. A validation set drawn by window would contain near-copies of training windows and overstate validation results; the validation split is therefore drawn by subject.
- int8 conversion loses more quality than the kill criterion allows: the kill outcome is reported, the quality claims it concerns are blocked, and an `experimental` release with an honest card is still possible.
- The int8 host reference, the conversion's reference interpreter or the board disagree on any output: the release is blocked until the mismatch is fixed; this is a defect, not a status question.
- Results vary strongly between seeds: the release candidate remains the pre-registered seed whatever its rank, and the spread is reported on the card.
- Sitting and standing are confused (known for this dataset): per-class F1 and the confusion matrix are reported, and the per-class floor in the success criteria decides.
- One test subject scores much lower than the others: per-subject results are reported and the worst subject's result appears on the card.
- A user feeds windows from another sensor placement, sample rate or unit: the model cannot detect this; the input contract and the limitation are on the card.
- The ESP32 board is not connected or not answering when the budgets are measured: the emulated ESP32 or another bench board is measured instead and labelled with its origin, and the card lists "budgets on the real reference board" as not measured.
- A later check (for example the fresh-environment quickstart) fails after staging: the release is fixed and staged again; nothing is published until the gate passes.
- The pre-zoo report's numbers (93.3 % accuracy, sizes): they are never used as a threshold, a gate input or a card value.

## Requirements *(mandatory)*

### Functional Requirements

**Scope**

- **FR-001**: This feature MUST deliver the first published version of `pace-cnn`, version `0.1.0`, trained and measured on UCI HAR only, through the zoo's release pipeline. Mobility data (transport modes, other sensor placements) is out of scope; it belongs to the later model `mode-cnn`. The riskiest assumption stays untested and is stated on the card.
- **FR-002**: The task's scope stays as defined in the task document: in, six activities from a 2.56 s window of a waist-worn 6-axis IMU at 50 Hz; out, vehicle or transport-mode classes, fall detection as a safety function, identification of persons.

**Benchmark and data**

- **FR-003**: Benchmark `uci-har-v1` MUST be frozen before its first result. Test split: the official UCI HAR test subjects (30 % of the subjects). Validation split: a fixed set of training subjects drawn once with a recorded seed, so that no subject is in both training and validation. The frozen record MUST identify the subjects of each split reproducibly (split source, validation rule and seed, subject counts and a checksum of each subject list) without listing subject numbers (FR-028). The task document MUST be updated to this definition before the freeze.
- **FR-004**: The test subjects MUST NOT be used for training, early stopping, threshold choice, or model, setting or seed selection. Each model file of a pre-registered training run is evaluated on them by one fixed procedure. Recomputing the same result deterministically (for example after the budget results arrive) is not a new evaluation, and no result on the test subjects feeds any choice.
- **FR-005**: The dataset MUST be fetched from the original provider into storage outside the repository with a passing licence check. Its declaration MUST name `pace-cnn` as a user.
- **FR-006**: The model MUST be trained only on the training subjects of UCI HAR and the dataset's own labels. No teacher outputs, model-generated or synthetic training data and no other dataset enter training.

**Pre-registration**

- **FR-007**: Before the first training run, a pre-registration record MUST be committed. It holds the candidate recipe (architecture, training settings, seed), the selection rule (applied on validation only), the success criteria for `released`, the kill criteria and the budgets. A change after results are seen MUST be a new, documented iteration with its rationale; the original record stays.
- **FR-008**: Model selection MUST be mechanical. The pipeline applies the pre-registered rule; no person and no assistant picks a candidate, seed or setting by looking at results. This keeps Claude output out of every selection signal (Principle XI).
- **FR-009**: Kill criteria (defaults, fixed in the pre-registration record): int8 macro-F1 below 0.80 on `uci-har-v1`; or int8 macro-F1 more than 0.03 below the float macro-F1 of the same run; or the candidate exceeds a budget on the reference hardware. A kill outcome blocks the claims it concerns, not an `experimental` release.

**Training and evaluation**

- **FR-010**: Headline results MUST be the int8 results on the bit-exact host reference: accuracy and macro-F1, each stated as measured against the UCI HAR dataset labels. The report MUST also give per-class F1, the confusion matrix and per-test-subject macro-F1 (worst subject and spread). Float results MAY be reported, marked as informative.
- **FR-011**: The deterministic check MUST be run and reported on its own: the int8 host reference equals the conversion's reference interpreter on every test window. Any mismatch blocks the release.
- **FR-012**: The pre-registered recipe MUST additionally be trained with four further pre-registered seeds. The spread (minimum, mean, maximum of macro-F1) is reported. The release candidate stays the pre-registered seed.
- **FR-013**: Re-running the recorded recipe on the same machine MUST reproduce the candidate's benchmark results. Where training is not bit-deterministic, the measured deviation MUST be stated in the report.

**Device and budgets**

- **FR-014**: Budgets of the release (Principle V): flash at most 128 KB and RAM at most 32 KB for the model including its working memory, and average inference time per window at most 100 ms on the reference hardware. Every measurement MUST record its origin: real board, emulator or simulator.
- **FR-015**: The reference hardware MUST be the ESP32 board on the bench (ESP32 classic, dual core, 240 MHz). The task document and the draft release record MUST name it instead of ESP32-S3. The emulated ESP32 in CI MAY be measured as well; its results are labelled as emulator results.
- **FR-016**: On the reference board, the outputs for the published test vectors MUST equal the host reference bit for bit.
- **FR-017**: Other boards on the bench MAY be measured as well. Their results are informative, labelled with their origin and never replace the reference hardware.

**Status and card**

- **FR-018**: The release status MUST be derived by rule from the pre-registered criteria: `released` only if every success criterion and every budget is met on the reference hardware; otherwise `experimental`. The card and the release record MUST list every criterion with its measured value and whether it is met.
- **FR-019**: Success criteria for `released` (owner decision 2026-10-18): on `uci-har-v1`, int8 macro-F1 ≥ 0.90, int8 accuracy ≥ 0.90 and int8 F1 ≥ 0.80 for every class; every budget of FR-014 met on the real reference board; and the riskiest assumption (transfer to mobility data) tested. The last criterion cannot be met in this feature, so version `0.1.0` is `experimental` whatever its quality results, and the card says so.
- **FR-020**: The model card MUST state: status, usage class (`commercial`) and licence (Apache-2.0); intended use; out-of-scope uses, including uses that would make a deployment high-risk under the EU AI Act (monitoring or evaluating persons at work, decisions on access to insurance, credit or services from a person's movement, identifying or profiling persons) and fall detection as a safety function; limitations; the headline metrics with their reference; per-class and worst-subject results; the seed spread; budget results with their origin; the UCI HAR attribution (creators, title, DOI, licence, modifications); and the input contract.
- **FR-021**: The input contract MUST let a user prepare the nine input channels from raw 6-axis IMU readings: units, sample rate, window length and overlap, the separation of gravity from body acceleration, and the normalisation constants. The release MUST provide this preparation as a documented procedure with a host reference.
- **FR-022**: Every number on the card MUST come from the frozen-benchmark quality report or the performance report of this release.

**Release and publication**

- **FR-023**: Published files MUST NOT contain training data or dataset windows, unless the `uci-har` declaration says `redistribution: allowed` after a check of the licence and the provider's terms. In that case the release MAY include a minimal number of example windows, without subject identifiers and with attribution. Test vectors for the bit-exact check MUST otherwise be synthetic.
- **FR-024**: `pace-cnn` MUST be published only through the release pipeline: staging, a passing release gate including its compliance checks, the owner's approval of card and status, then publication. The published version is immutable.
- **FR-025**: The release gate MUST run the card's host example in a fresh environment built from the card's install line, and pass.
- **FR-026**: On publication, the zoo MUST show `pace-cnn` as published everywhere it is listed: the `condition-monitoring` Hugging Face collection (created with this first model), the zoo index and model list, the repository and topic READMEs, the website model page and the roadmap, where delivery is read from the release record's publication date.

**Compliance**

- **FR-027**: The usage class MUST be derived from all inputs: UCI HAR (CC BY 4.0, commercial use allowed) and no base model, teacher or third-party model at run time, which gives `commercial`. The gate MUST confirm that no input behind the model was produced by Claude: no teacher, route, labeling, data-generation or evaluation run of the release belongs to the Claude family. The only exception is the frozen benchmark references that Principle XI keeps, used in their role as benchmark references.
- **FR-028**: Personal data: UCI HAR holds motion signals of 30 volunteers, identified by number only. Published files and reports MUST NOT contain subject identifiers. Per-subject results are reported under neutral positions (for example "worst test subject"), never under the dataset's subject numbers. The card MUST state that the model was trained on motion data of volunteers.

### Key Entities

- **Benchmark `uci-har-v1`**: the frozen evaluation definition: dataset, subjects per split, validation seed, metrics, freeze date. Immutable after first use.
- **Pre-registration record**: recipe, seeds, selection rule, success criteria, kill criteria and budgets, committed before the first run; amendments append, never overwrite.
- **Training run**: one execution of the recipe with one seed, with its int8 model, float and int8 results and deterministic check.
- **Quality report**: the results of the release candidate and the seed spread on `uci-har-v1`, with the status verdict.
- **Performance report**: flash, RAM and latency per board, each with its origin, and the bit-exact agreement on the board.
- **Release record `0.1.0`**: status, files with checksums, recipe commit, provenance, usage class and licence, evaluation and performance results, publication date. Draft today; immutable once published.
- **Model card**: the public description generated from the model record and release record.
- **Test vectors**: inputs and expected int8 outputs for the bit-exact check on host and board.
- **Dataset declaration `uci-har`**: licence, permitted use, redistribution, personal data, retention, users.
- **Roadmap entry `pace-cnn`**: first planned 2026-Q4; delivered when the release is published.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A quality report on the frozen benchmark `uci-har-v1` exists with every result FR-010 names, and the int8 host reference agrees with the reference interpreter on 100 % of the test windows.
- **SC-002**: On the reference hardware, `pace-cnn` needs at most 128 KB flash and 32 KB RAM and classifies a 2.56 s window in at most 100 ms on average, measured on the real board, or the card states which of these is missed and by how much.
- **SC-003**: On the reference board, 100 % of the published test vectors give outputs equal to the host reference.
- **SC-004**: A newcomer gets six class scores from a fresh environment in at most 5 minutes, following only the model card.
- **SC-005**: The release is published by 2026-12-31, so the roadmap entry planned for 2026-Q4 is delivered on time.
- **SC-006**: The release gate and its compliance checks report 0 findings at publication: attribution, usage class, provenance, no Claude inputs, no subject identifiers, no dataset content without allowed redistribution.
- **SC-007**: 100 % of the numbers on the card trace to this release's quality or performance report; 0 numbers come from the pre-zoo report.
- **SC-008**: Applying the pre-registered criteria to the published reports gives the published status, for any reader who repeats it.

## Assumptions

- The first published version is `0.1.0`. The draft release record is unpublished and is updated in place; it becomes immutable at publication.
- The existing recipe (three convolution blocks over the time axis, nine channels, six outputs) is the single pre-registered candidate. Other sizes or architectures are a later iteration.
- Training and evaluation run locally on the owner's laptop: the dataset is about 60 MB and the model is small. No cash cost; cash budget 0 €.
- Claude writes code, specs and the card and runs the pre-registered pipeline as a development assistant. The labels are the dataset's own ground truth; Claude produces no label, training data, judgment or selection signal.
- The owner's steps: connecting the reference board if the measurement needs physical access, approving card and status, merging, tagging, publication tokens and creating the Hugging Face collection if the token requires it.
- Energy use is not measured (the bench has no power measurement). The card says so.
- The on-device preparation of the input (gravity separation, normalisation) is not part of this release unless planning finds input channels that need no filter. The card documents the preparation, and a host reference is provided.
- If the MLflow tracking of feature 017 is merged when the runs start, they are logged there. This feature does not depend on it.
- `hum-fan`, the other condition-monitoring model planned for 2026-Q4, is a separate feature.
- The riskiest assumption of the task (waist-worn activity windows are a useful base for micromobility and manoeuvre detection) stays a stated limit on the card and is the reason 0.1.0 is `experimental`.
- Follow-up outside this feature: `mode-cnn` (roadmap 2027-Q1..Q2, precondition "data licence to be confirmed"). Found on 2026-10-18: the MobilitApp sensor dataset (CORA.RDR, DOI 10.34810/data1948) is listed under CC0 1.0, with eleven modes including e-scooter, e-bike, bus, tram, train and car, and accelerometer, gyroscope and magnetometer data from 50 smartphones. Its terms and personal-data situation still need a declaration check. The SHL licence remains unconfirmed.

## Constitution Compliance

Principles I, II, VII and X apply to the JTBD extraction task only; this feature does not touch them.

| Principle or section | How this feature complies |
|---|---|
| III Measure Before Optimizing | Ground-truth task with a benchmark frozen before first use (FR-003); test subjects never used for selection (FR-004); deterministic check reported on its own (FR-011); int8 on the bit-exact host reference as headline (FR-010); metrics named after their reference. |
| IV Riskiest Assumption First | Success and kill criteria committed before the first run (FR-007, FR-009); the riskiest assumption is named and stays a card limit (Assumptions, FR-001). |
| V Small and Local, Budgets per Task | Concrete budget values and a named reference hardware (FR-014, FR-015); every measurement records its origin; emulator results are never presented as hardware results. |
| VI Clean Provenance | Dataset declared with licence, permitted use, redistribution, personal data and retention; usage class `commercial` derived from all inputs (FR-027); no dataset in git (FR-005); no published dataset content without allowed redistribution (FR-023); subject identifiers kept out (FR-028). |
| VIII Fair Architecture Comparison | One build-and-measure tool for the task (`condmon activity`) and one benchmark version for every run. |
| IX Reproducible, Dated Releases | Recipe reproducible (FR-013); status by rule, `released` only when production ready (FR-018); publication only through the pipeline after owner approval (FR-024); no training data published. |
| XI No Claude in Model Learning | Dataset labels only; no Claude label, data, judgment or selection signal (FR-006, FR-008); the gate confirms it (FR-027). |
| Roadmap and Delivery Pace | Delivery counted at publication, read from the release record (FR-026, SC-005). |
| Resources & Cost Discipline | Local compute first; no cash cost. |
| Quality Gates | Gate before an experiment (FR-007), before reporting (SC-001), before release (FR-024, FR-025, SC-006). |
