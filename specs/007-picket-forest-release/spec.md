# Feature Specification: picket-forest 0.1.0, honest CAN IDS benchmark and first release

**Feature Branch**: `007-picket-forest-release`

**Created**: 2026-10-09

**Status**: Draft

**Input**: User description: "First release of picket-forest 0.1.0 (topic security, task can-ids): a frozen, honest benchmark can-ids-v1, evaluation of picket-forest on it, the release-gate support for tree models, device measurements, compliance record, model card and publication through the existing zoo release pipeline. Feature 007."

## Context

`picket-forest` detects injected messages on a vehicle's classic CAN bus. It scores every frame with a random forest over 13 streaming timing and payload features (no raw CAN identifier), and an alarm stage turns flagged frames into alarms. It runs as plain C on ESP32-class microcontrollers in about 10 KB of RAM, with the same scores as the Python model. It came into the zoo with feature 005; its earlier results are pre-zoo research results, not benchmark results ([research card](../../topics/security/reports/picket-forest/research-card.md)).

The competitive research of 2026-10-09 ([06 – Competitive landscape](../../topics/security/research/06-competitive-landscape.md), notes in `topics/security/research/notes/competition-*.md`) found:

- **Most published CAN IDS numbers are not comparable.** They come from random frame splits, from Car-Hacking, or from support-weighted F1. Under realistic protocols, the same model classes drop sharply.
- **Unknown vehicles are unsolved.** On the official unknown-vehicle splits of can-train-and-test, the attack-class F1 of published methods, recomputed from their own confusion counts, is at most about 0.38. A 2026 replication measures a cross-vehicle F1 of 0.04.
- **Nobody reports event-level numbers.** False alarms per hour, share of attack episodes detected and time to alarm are missing from every CAN paper found for 2025–2026.
- **The open embedded space is empty.** No open, documented microcontroller CAN IDS exists on Hugging Face, and vendors publish no reproducible benchmark.

So the USP of 0.1.0 is not a new detector. It is honest, reproducible, event-level and attack-class results on unknown vehicles and unknown attacks, from a model that runs on a low-cost microcontroller and is open to audit. The known weaknesses are stated in 0.1.0, not fixed:

- false alarms on unknown vehicles;
- missed unseen identifier scans and fuzzing;
- no masquerade detection.

A rule layer and an on-device calibration phase follow in a separate feature for 0.2.0.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A frozen, honest benchmark for CAN intrusion detection (Priority: P1)

The owner freezes the benchmark `can-ids-v1` from the declared datasets. Anyone can reproduce the split from the manifest and score any detector on it with the same code.

**Why this priority**: Every claim of the release depends on it. Without a frozen, checked benchmark the model cannot be released (gate rule 9) and no USP can be shown.

**Independent Test**: With the datasets downloaded to the data cache, `security can-ids freeze` writes a manifest. A second run on the same files gives the same manifest. Scoring a trivial detector (all frames benign) gives the expected metrics.

**Acceptance Scenarios**:

1. **Given** can-train-and-test and ROAD are downloaded, **When** the owner runs the freeze command, **Then** a manifest lists every capture with its split, vehicle, attack family, frame count and content hash, and records the dataset versions.
2. **Given** two captures with identical content but different labels (vehicle or split), **When** the benchmark is frozen, **Then** freezing stops and names both captures. They are resolved explicitly (kept, dropped or relabelled, with the reason) before the benchmark can be frozen.
3. **Given** a frozen benchmark, **When** a file in the data cache changes, **Then** evaluation refuses to run and names the changed capture.
4. **Given** the benchmark, **When** anyone inspects the repository, **Then** it holds only the manifest (hashes, counts, labels of captures), never frames or payloads.

---

### User Story 2 - picket-forest measured on the benchmark, next to baselines and shortcut controls (Priority: P1)

The owner runs `security can-ids evaluate picket-forest --benchmark can-ids-v1` and gets a report in which picket-forest's headline numbers stand next to:

- published-style baselines rerun on the same protocol;
- shortcut controls, which would expose leakage if picket-forest's advantage came from it.

**Why this priority**: The research found a gap to published results large enough to be suspicious. The release may only claim what survives the controls.

**Independent Test**: The evaluation writes a quality results file in the zoo format and a report. Every number in the report is traceable to the frozen benchmark and the code version.

**Acceptance Scenarios**:

1. **Given** the frozen benchmark, **When** picket-forest is evaluated, **Then** it is trained per set on that set's training split only and tested on that set's four test splits, and the report gives the headline metrics per split as median over the four sets and for the worst set:
   - share of attack episodes detected at a false-alarm budget of at most 1 and at most 10 false alarms per hour;
   - median and 95th-percentile time to alarm.
2. **Given** the same run, **When** the report is read, **Then** it also gives:
   - attack-class precision, recall, F1, AUC-PR and MCC per attack family;
   - recall at a fixed frame false-positive rate;
   - the false alarms per hour of the default alarm rule.

   It never gives a support-weighted metric.
3. **Given** the shortcut controls, **When** they run in the same harness, **Then** their results appear next to picket-forest. The controls are an identifier lookup, a timing-only forest, picket-forest with the raw identifier, and a shuffled-label model. If a control matches or beats picket-forest on a split, the report says so on that split.
4. **Given** the baselines, **When** they run, **Then** their results appear on the same protocol:
   - simple timing detectors (mean interval, binning);
   - can-logic-style rules (interval, repetition, identifier whitelist);
   - an unsupervised Isolation Forest;
   - a stated subset of the original can-train-and-test benchmark models, rescored with attack-class metrics.
5. **Given** ROAD held-out captures, **When** evaluated, **Then** results for fabrication and fuzzing are reported. Masquerade and accelerator captures are reported separately and marked out of scope.

---

### User Story 3 - The release gate verifies a tree model end to end (Priority: P2)

The release gate checks picket-forest the way it checks int8 models: the staged artefacts run the published examples, and the outputs match exactly.

**Why this priority**: Feature 005 left this gap. Without it the gate cannot pass rules 12 and 13 for picket-forest.

**Independent Test**: A fixture tree model passes the gate. Changing one expected score in an example makes rules 12 and 13 fail.

**Acceptance Scenarios**:

1. **Given** a tree model with `examples/*.json`, **When** the gate runs:
   - each example holds a sequence of CAN frames (timestamp, identifier, length, payload), the expected per-frame scores and the expected alarms;
   - the gate builds the staged C code into a host scorer and replays each example;
   - scores and alarms must match bit-exactly.
2. **Given** an int8 model, **When** the gate runs, **Then** the existing int8 path is used unchanged.
3. **Given** an example whose frames come from a dataset whose declaration does not allow redistribution, **When** the gate runs, **Then** rule 13 fails. Examples are synthetic, or taken from a dataset that allows it.

---

### User Story 4 - Device evidence and the published release 0.1.0 (Priority: P2)

The owner stages the trained artefacts and completes the release record, results, compliance record and card. The release goes through tag, verification, owner approval and publication.

**Why this priority**: This is the outcome of the feature. It depends on stories 1 to 3.

**Independent Test**: `zoo check picket-forest 0.1.0` passes all offline rules. The release-verify workflow produces a card preview. After approval, the model is public in the security collection.

**Acceptance Scenarios**:

1. **Given** the whole detection chain (features, forest, alarm stage) built for the host, for an emulated ESP32 and for the ESP8266 board, **When** it is measured, **Then** performance results give flash, RAM and per-frame latency, each with hardware and origin. The real board is the owner's ESP8266 (Wemos D1 mini), a named substitute for the reference board ESP32-S3. The release is experimental (below 1.0.0).
2. **Given** the published model, **When** the card is read, **Then** it says:
   - the model was trained on the training splits of all four vehicles;
   - the quality numbers come from the per-set protocol, which tests on unseen vehicles and attacks;
   - the published model itself has no untouched test set.
3. **Given** the card, **When** it is read, **Then** it states the limitations with numbers:
   - false alarms on unknown vehicles;
   - unseen scans and fuzzing;
   - masquerade not detected;
   - classic CAN only.

   It also carries a dual-use note, states that the model is not a safety mechanism and makes no ISO/SAE 21434 or UN R155 claim, and gives the C usage on a device.
4. **Given** the compliance harness, **When** the release is checked, **Then** a compliance record covers the training and evaluation datasets with attribution, the AI Act classification, the dual-use note and the absence of personal data in published files. Gate rule 16 passes.

### Edge Cases

- **Captures without attack episodes** (benign only): they count towards false alarms per hour and not towards detection.
- **Episodes shorter than the alarm window**: they are counted and reported as such. They are not dropped.
- **Single-frame alarm rules**: time to alarm is defined (0 ms when the first flagged frame is the first attack frame). The suspected bug that yields an empty median is fixed and covered by a test.
- **Missing set**: a set that cannot be loaded or featurised is reported as missing in the report and in `metrics.json`. A report with a missing set is partial and cannot feed the quality results; nothing is silently skipped.
- **Unclear redistribution**: ROAD and can-train-and-test both have `redistribution: unclear`. No frame of either dataset appears in published examples.
- **Timestamp resolution**: ROAD has a 100 µs resolution and can-train-and-test has finer timestamps. Time to alarm is reported with the resolution of its source.

## Requirements *(mandatory)*

### Functional Requirements

**Benchmark**

- **FR-001**: The system MUST freeze benchmark `can-ids-v1` from the declared datasets `can-train-and-test` and `road`:
  - can-train-and-test: the four sets with their training split and the four test splits (known/unknown vehicle × known/unknown attack);
  - ROAD: held-out captures (attack runs ending in `_2`, every fourth ambient capture by name hash).
- **FR-002**: Freezing MUST hash every capture and detect identical content under different labels. It MUST stop until each duplicate is resolved and the resolution is recorded with a reason.
- **FR-003**: The frozen manifest MUST be in git. It holds capture names, splits, vehicles, attack families, frame and episode counts, hashes and dataset versions. Frames and payloads MUST stay in the data cache.
- **FR-004**: Evaluation MUST refuse to run when a capture's hash differs from the manifest.

**Metrics**

- **FR-005**: The headline metric MUST be the share of attack episodes detected at a false-alarm budget of ≤ 1 and ≤ 10 false alarms per hour. It is reported per test split as median over the four sets and for the worst set, with median and 95th-percentile time to alarm.
- **FR-006**: Episode definitions MUST be fixed in the benchmark and documented:
  - an attack episode is a run of attack frames separated by more than 1 s;
  - an episode is detected if an alarm falls inside it or up to 1 s after it;
  - every other alarm is a false alarm.
- **FR-007**: Secondary metrics MUST be attack-class only: precision, recall, F1, AUC-PR, MCC per attack family, recall at a fixed frame false-positive rate (stated in the report), and false alarms per hour of the default alarm rule. Support-weighted averages MUST NOT be reported.
- **FR-008**: Time to alarm MUST be defined for every alarm rule, including single-frame rules. The defect that yields an empty median MUST be fixed and covered by a test.

**Controls and baselines**

- **FR-009**: The harness MUST run these shortcut controls on the same protocol and report them next to picket-forest:
  - identifier lookup;
  - timing-only forest;
  - picket-forest including the raw identifier;
  - shuffled-label model.
- **FR-010**: The harness MUST run these baselines on the same protocol:
  - mean-interval and binning timing detectors;
  - can-logic-style rules;
  - Isolation Forest;
  - a stated subset of the original can-train-and-test benchmark models with attack-class metrics.
- **FR-011**: Thresholds of every detector MUST be chosen on training or validation data, never on test data. The report MUST state how.

**Evaluation output**

- **FR-012**: `security can-ids evaluate MODEL --benchmark can-ids-v1` MUST write:
  - a quality results file in the zoo results format, with reference kind `ground_truth` and the benchmark name;
  - a report under `topics/security/reports/picket-forest/` with all numbers, the code version and the manifest hash.

  The report MUST also contain:
  - a quality-vs-cost Pareto table over all detectors: headline against model size (flash or tree nodes) and per-frame latency on the host (constitution III);
  - the deterministic checks of the deployed format: the C-versus-Python score agreement of picket-forest on the benchmark test captures.
- **FR-013**: ROAD masquerade and accelerator captures MUST be reported separately and marked out of scope; they MUST NOT enter the headline.

**Release gate**

- **FR-014**: Gate rules 12 and 13 MUST support tree models. Examples are frame sequences with expected per-frame scores and alarms, replayed through a host build of the staged C code, and they must match bit-exactly. The int8 path stays unchanged.
- **FR-015**: Example frames MUST be synthetic or come from a dataset whose declaration allows redistribution (existing rule 13).

**Device evidence**

- **FR-016**: The whole detection chain (features, forest, alarm stage) MUST be measured. The measurement gives flash, RAM and per-frame latency, each with hardware and origin. Required: a host build, an emulated ESP32 (memory and correctness), and the ESP8266 (Wemos D1 mini) as a named substitute for the reference board (real-board latency and bit-exact scores).

**Release**

- **FR-017**: The published model MUST be trained on the training splits of all four sets with the frozen recipe (config and code version). The card MUST say:
  - the quality numbers come from the per-set protocol;
  - the published model has no untouched test set.
- **FR-018**: The release MUST include:
  - the C headers (model, configuration), the host reference model file and the C sources of the detector, features and alarm stage, all staged, so the model builds without the repository;
  - a compliance record (datasets, attribution, AI Act classification, dual-use note) with a CycloneDX software bill of materials of the device code (compliance check C-G4);
  - a model card with limitations, a dual-use note, a statement that it is not a safety mechanism and the C usage.

  It is published through tag, `release-verify`, owner approval and `release-publish`.
- **FR-019**: The release MUST be `experimental` (version below 1.0.0). Every measurement MUST name its hardware, and the ESP8266 MUST be named as a substitute for the reference board.

### Key Entities

- **Benchmark manifest (`can-ids-v1`)**: dataset versions; per capture its name, source dataset, set, split, vehicle, attack family, frame count, episode count and content hash; resolved duplicates with reasons; protocol constants (episode gap, grace period, budgets).
- **Detector run**: detector name and version, set, training split used, thresholds and how they were chosen, per-capture scores and alarms (kept in the data cache), aggregated metrics.
- **Evaluation report**: headline and secondary metrics per split for picket-forest, controls and baselines; code version; manifest hash.
- **Tree-model example**: a frame sequence with expected per-frame scores and alarms, and its source (synthetic or a redistributable dataset).
- **Device measurement**: metric (flash, RAM, latency), value, unit, hardware, origin, date.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Freezing the benchmark twice on the same files gives byte-identical manifests. Every duplicate capture found is resolved with a recorded reason.
- **SC-002**: The evaluation report gives, for picket-forest, the headline metrics on all four test splits of all four sets and on ROAD fabrication and fuzzing captures. No support-weighted metric appears.
- **SC-003**: Every shortcut control and baseline listed in FR-009 and FR-010 has results on the same splits, or a stated reason why it could not run.
- **SC-004**: Whatever the controls show, the release claims only what survives them. If any control reaches picket-forest's headline on a split, the card says so for that split.
- **SC-005**: `zoo check picket-forest 0.1.0` passes every offline rule, and the release-verify run passes every rule, before the owner's approval.
- **SC-006**: Changing one expected score in one example makes rules 12 and 13 fail; restoring it makes them pass.
- **SC-007**: The card states the model's false alarms per hour on unknown vehicles, its recall on unseen scans and fuzzing, and that masquerade is not detected, each with the number from the report.
- **SC-008**: picket-forest 0.1.0 is public on Hugging Face in the security collection, and its card reports event-level results on unseen vehicles and attacks.

## Budgets

From the task document `topics/security/tasks/can-ids.md` (constitution V):

- **Reference board**: ESP32-S3.
- **Memory**: at most 16 KB RAM (features, model state and alarm stage) and 128 KB flash.
- **Latency**: the whole chain under 100 µs per frame on the reference board. At 500 kbit/s and full load a frame takes at least about 225 µs.
- **Measured here**: on the host, on an emulated ESP32 (memory and correctness) and on an ESP8266 (Wemos D1 mini) as a named substitute for the reference board.
- **Cash**: none. Everything runs locally.

## Constitution Compliance

| Principle | How this feature complies |
|---|---|
| I, II, VII, X | Not applicable (JTBD task only). |
| III Measure before optimising | Ground-truth task with the labels of can-train-and-test and ROAD as reference, frozen as `can-ids-v1` before the first zoo result. Test data is never used for thresholds or selection (FR-011). Metric names state the reference; there are no support-weighted metrics (FR-007). The report gives the deterministic C-versus-Python check and a quality-vs-cost Pareto table (FR-012). |
| IV Riskiest assumption first | Transfer to unknown vehicles without identifier memorisation, tested by the shortcut controls (FR-009). Success, partial and kill criteria are recorded before the evaluation ([research R10](research.md)). |
| V Small and local, budgets | Budgets above. Every measurement names its hardware and origin; the emulator is never presented as hardware, and the ESP8266 is named as a substitute. |
| VI Clean provenance | Declared datasets (CC BY 4.0, training allowed, redistribution unclear). No dataset frame is published; the examples are synthetic (FR-015). |
| VIII Fair comparison | One benchmark version and one harness for picket-forest, controls and baselines (FR-009, FR-010). |
| IX Reproducible releases | Frozen, versioned benchmark; model reproducible from configuration and code version; published only through the release pipeline. |

## Assumptions

- The datasets can-train-and-test (Bitbucket, CC BY 4.0) and ROAD (Zenodo, CC BY 4.0) are declared, training-allowed and downloadable. Their redistribution stays `unclear`; nothing of them is published.
- The benchmark uses can-train-and-test as provided by the download (v1.5 layout if the repository HEAD is v1.5). Masquerade and suppression splits of v1.5 (`test_05`, `test_06`) are reported separately and are out of scope for the headline.
- The model configuration of the pre-zoo research is kept for 0.1.0: 30 trees, depth 12, min_samples_leaf 20, features without the raw identifier, alarm rule 3 frames in 200 ms with 1 s hold-off. It is reselected only through the documented validation procedure, never on test data.
- Hosted compute is not needed. Training and evaluation run on the owner's machine; the full evaluation may take hours.
- The owner has ESP8266 boards (Wemos D1 mini) but no ESP32 and no CAN transceiver. Frames are replayed from flash, so no transceiver is needed. Reception at full bus load and ESP32-S3 hardware numbers come later.
- The Hugging Face collection for the security topic is created at the first publication (existing pipeline behaviour).
- Out of scope:
  - the rule layer and calibration phase (0.2.0);
  - picket-mlp;
  - ingestion of commaCarSegments;
  - mapping to the Auto-ISAC Automotive Threat Matrix and UN R155 Annex 5;
  - masquerade detection;
  - real-vehicle tests.
