# Research: picket-forest 0.1.0

Decisions for [plan.md](plan.md). The evidence for the benchmark and metric choices is in [06 – Competitive landscape](../../topics/security/research/06-competitive-landscape.md) and its notes, especially [state of the art on hard protocols](../../topics/security/research/notes/competition-sota-protocols.md).

## R1 Dataset versions

- **Decision**: Use can-train-and-test v1 as declared: Bitbucket `brooke-lampe/can-train-and-test`, four sets, `train_01` and `test_01`–`test_04`. Add ROAD as declared (Zenodo 10462796).
  - The v1.5 additions (`train_01_attack_free`, `test_05_suppress`, `test_06_masquerade`) are not part of `can-ids-v1`.
- **Rationale**:
  - v1 holds the splits that the original 18-model benchmark, can-logic and the BusRecall replication report on, so our numbers can sit next to theirs.
  - Suppression has no frame labels.
  - Masquerade is out of scope for this model.
- **Alternatives**: v1.5. Rejected for `can-ids-v1`; a later benchmark version can add its masquerade split when a masquerade-capable model exists.

## R2 Duplicate and label consistency check

- **Decision**:
  - At freeze, hash every capture (SHA-256 of the parsed frame table in the common frame format, so CSV formatting does not matter) and group equal hashes.
  - A group spanning different labels (vehicle, split or attack family) stops the freeze.
  - The resolution is written to `topics/security/benchmarks/can-ids-v1/resolutions.yaml`, one entry per group with its action (keep in one place / drop / relabel) and reason.
  - The research report's suspect pairs (set_01/test_04 vs set_02/test_01, set_03/test_04 vs set_04/test_01) are checked first.
- **Rationale**: Identical captures under two vehicle labels would let the "unknown vehicle" test see a known vehicle (FR-002).
- **Alternatives**: Hashing raw CSV files. Rejected: it misses re-serialised duplicates.

## R3 Episodes, budgets and headline

- **Decision**:
  - An episode is a run of attack frames with gaps of at most 1 s.
  - Detection counts an alarm inside the episode or up to 1 s after it (grace); every other alarm is false.
  - The headline per split is the detection share at the best alarm operating point whose false alarms per hour on validation captures are ≤ 1 (and separately ≤ 10). That point is chosen on validation captures and then reported on test.
  - Reported per split: the median over the four sets and the worst set, with median and p95 time to alarm.
- **Rationale**:
  - Same definitions as `metrics.py` and the research card, so pre-zoo and zoo numbers differ only by benchmark hygiene.
  - Choosing the operating point on validation respects constitution III: test data never selects a model or threshold.
- **Alternatives**: An operating point at a fixed budget on test data. Rejected, because it is test tuning.

## R4 Time-to-alarm defect

- **Decision**:
  - Reproduce on stored scores: the suspicion is that the median is empty when every detected episode has its alarm at a later frame than the episode's last frame (in the grace window), or when latencies are filtered.
  - Fix in `alarm_metrics`: latency = first alarm time in `[start, end + grace]` minus `start`, never empty when `detected > 0`.
  - Add a test with a one-frame episode and an alarm in the grace window.
- **Rationale**: FR-008.

## R5 Controls and baselines

- **Decision**: All controls and baselines run in the same harness, per set, trained on `train_01` with the same benign subsampling (all attack frames, 10 % of benign) and thresholds chosen on held-out training captures.

  | Name | Kind | What it shows |
  |---|---|---|
  | `ctrl-id-lookup` | control | attack rate per CAN ID learned on train, used as a score; shows how much is identifier memorisation |
  | `ctrl-timing-only` | control | forest on the timing features only |
  | `ctrl-forest-with-id` | control | picket-forest's recipe with the raw ID feature (`full` feature set) |
  | `ctrl-shuffled` | control | picket-forest's recipe with training labels shuffled within each capture; must collapse |
  | `bl-mean-interval`, `bl-binning` | baseline | Blevins et al. 2021 timing detectors, benign-only |
  | `bl-can-logic` | baseline | interval, three-repeat and ID-whitelist rules (Lampe & Meng) |
  | `bl-isolation-forest` | baseline | unsupervised, frame features |
  | `bl-orig-{dt,rf,et,gnb,logreg,mlp}` | baseline | original benchmark models on its frame features (timestamp, ID, data bytes), attack-class metrics; KNN and SVMs dropped (they ran for days in the original) |

- **Rationale**:
  - FR-009 and FR-010; constitution VIII (same harness).
  - The original-feature models keep the absolute timestamp because the original did. The report says it is a shortcut feature.
- **Alternatives**: Also running KD-GAT and CANShield. Rejected for 0.1.0: KD-GAT needs GPU training and graph windows; CANShield needs decoded signals, which can-train-and-test lacks. Both are named in the report with their published numbers and protocols.

## R6 ROAD protocol

- **Decision**:
  - Evaluate the release model (trained on `train_01` of all four sets) on the ROAD held-out captures. These are attack runs ending in `_2` (fabrication, fuzzing) plus every fourth ambient capture by name hash.
  - Labels come from the injection metadata, as in `frames.road_labels`.
  - Masquerade and accelerator captures are reported separately as out of scope.
- **Rationale**:
  - ROAD is a fifth vehicle from another dataset, with remapped IDs: the strictest unknown-vehicle test, and a direct check that the model does not depend on identifiers.
  - Training on ROAD would only add a within-dataset number that the literature already has.
- **Alternatives**: A per-capture ROAD protocol with ROAD training. Kept as an optional section if time allows.

## R7 Tree models in the release gate

- **Decision**:
  - `model.yaml` gets `engine: int8 | emlearn` for `runtime: mcu` (default `int8`).
  - For `emlearn`, the staged files are:
    - `picket_forest_model.h` (generated forest);
    - `picket_forest_config.h` (inputs, threshold, alarm rule);
    - `model.joblib` (host reference);
    - `config.json` (selection, parity).
  - Rules 12 and 13 build the host scorer from the staged headers plus the C sources at the recipe commit (`firmware/picket-forest/c`, `firmware/components/can_features`) with `-ffp-contract=off`.
  - Each example is replayed, and per-frame scores (float32 bits) and alarm frame indices are compared exactly.
- **Rationale**:
  - The existing int8 path loads an npz.
  - The tree path needs the C build, because the published artefact is C code.
  - The comparison covers the whole chain the card promises.
- **Alternatives**: Comparing joblib Python scores only. Rejected: it would not test the published C.

## R8 Examples

- **Decision**:
  - A deterministic generator writes synthetic frame sequences: periodic benign IDs with jitter, plus one injected attack family per example (fabrication/spoofing on an existing ID, DoS on ID 0x000, fuzzing).
  - Expected scores and alarms come from the host scorer of the release model.
  - Each example is 2,000 frames, `source: synthetic`.
- **Rationale**: The redistribution of ROAD and can-train-and-test is `unclear`, so no recorded frame may be published (FR-015). Synthetic frames still exercise every feature and the alarm stage.

## R9 Device evidence

- **Decision**:
  - **Host**: `latency_us` of the host scorer per frame (whole chain), origin `host`, hardware = host CPU.
  - **Real board (required in 0.1.0)**: the owner's Wemos D1 mini (ESP8266, run at 160 MHz). Steps:
    - add an `esp8266` env (d1_mini, 160 MHz) to the PlatformIO replay benchmark;
    - flash it over USB through the bench's flasher;
    - read the `PICKET_FOREST_RESULT` line;
    - record `latency_us` (median and p99 per frame, whole chain), `ram_kb` (detector state plus static data) and a score check against the host on every replayed frame.

    Origin `real_board`, hardware "ESP8266 (Wemos D1 mini), 160 MHz, substitute for the reference board ESP32-S3". The ESP8266 has no FPU (software floating point) and a weaker core, so its latency is a conservative bound for the ESP32-S3. Bit-exactness on it is a strong portability check. No CAN transceiver is needed: frames are replayed from flash.
  - **Emulator**: PlatformIO env `esp32` of the same project, run in Espressif QEMU through the bench's QEMU tooling. Records `ram_kb` and `flash_kb` for the ESP32 image (detector objects from the linker map), the score check, and `latency_us` marked as not representative. Origin `emulator`.
  - **Not measured in this feature**: reception through a CAN controller and transceiver at full bus load; ESP32-S3 on real hardware.
- **Budgets** (task document): ≤ 16 KB RAM and ≤ 128 KB flash on ESP32-S3. Latency target: the whole chain under 100 µs per frame on the reference board (full load at 500 kbit/s is at most about 4,400 frames/s, that is ≥ 225 µs per frame). The ESP8266 result is reported against the same target as a conservative check.
- **Rationale**: Constitution V allows a named substitute when the reference hardware is not available, and requires the origin of every measurement. Gate rule 15 gets a real-board latency. The version stays `experimental` anyway (below 1.0.0).
- **Alternatives**:
  - QEMU only: rejected, because emulator timing is not representative.
  - Buying an ESP32-S3: deferred to the owner; a later patch release can add its numbers.

## R10 Riskiest assumption, success and kill criteria (constitution IV)

Written before the first zoo evaluation.

- **Riskiest assumption**: detection transfers to unknown vehicles without identifier memorisation.
- **Success** (USP claim allowed): on `test_02` and `test_04` (unknown vehicle), picket-forest's median attack-class F1 and its headline detection share at ≤ 10 false alarms per hour both exceed every control and baseline. `ctrl-shuffled` collapses (F1 below 0.1).
- **Partial**: picket-forest beats the baselines, but a control (`ctrl-timing-only` or `ctrl-forest-with-id`) is at least as good. The card reports this split by split and the USP rests on event-level honesty and the device footprint, not on superior transfer.
- **Kill for the transfer claim**: `ctrl-id-lookup` reaches picket-forest's F1 on an unknown-vehicle split, or `ctrl-shuffled` does not collapse (leakage). No transfer claim is made. The release proceeds with the honest numbers only after the leak is understood and the benchmark is fixed as a new version.
- **Release blockers independent of the claim**: any C-versus-Python score mismatch; a missing set; a manifest hash mismatch.

## R11 Compute

- **Decision**:
  - Featurisation goes through the C feature library (ctypes) with a per-split feature cache in `$MMZ_DATA/derived/picket-forest/features/`.
  - Baselines train on the subsampled training data.
  - The full run is expected to take several hours on the owner's machine (the pre-zoo run evaluated all 16 cells).
  - No hosted compute, no cost.
- **Rationale**: Constitution resources rule; the spec assumes local runs.
