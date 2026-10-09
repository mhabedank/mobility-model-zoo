# Validation: picket-forest 0.1.0

## Setup

- Download started 2026-10-09: ROAD from Zenodo (slow, about 3 h for 600 MB), then can-train-and-test from Bitbucket. Results recorded when finished.

## Foundational

- `alarm_metrics` gained `p95_latency_ms`; `frame_metrics` gained `mcc`; new `recall_at_fpr` (threshold from benign validation scores) and `budget_operating_point` (alarm rule with the best episode recall within a false-alarm budget on validation captures). Tests: `tests/security/can_ids/test_metrics_alarm.py`.
- Suspected defect "median time to alarm null for single-frame rules" (research report): not reproducible. The pre-zoo `protocol_results.json` has no empty or NaN latency where an episode was detected. The behaviour is now pinned by tests (one-frame episode with an alarm in the grace window, alarm on the first attack frame).
- Schemas: `engine: int8|emlearn` in `model.schema.json`; `runtime` and `sbom` in `release-compliance.schema.json` (sbom required for mcu). Check C-G4 expected both fields, but the schema rejected them, so an mcu release could never pass rule 16; fixed with tests.

## US3 (2026-10-09)

- Synthetic CAN generator `synth.py` (fabrication, DoS, fuzzing, scan; deterministic per seed).
- `scorer.py`: host build of the C chain from repository or staged sources; `host_score.c` now also writes the alarm flag of `picket_forest_process`, so examples cover features, forest and alarm stage.
- Gate: `engine: emlearn` path for rules 12/13. It builds from the staged files only, checks that the staged `c/` sources equal the repository sources at the recipe commit, and compares score bit patterns and alarm frames. Rule 11 caps staged files at 5 MB except `model.joblib`.
- Fixture `edge-fixture-forest` (3-tree forest trained at test time) and `tests/release/test_gate_emlearn.py`: passes offline and online; one flipped score bit fails rules 12 and 13 and passes again when restored (SC-006); changed alarms fail; an example from ROAD fails rule 13; a changed staged source fails rule 12; the int8 fixture is unchanged.
- Card: tree examples are shown as frame tables with alarm frames; golden file `edge-fixture-forest-0.1.0.README.md`; python and int8 goldens unchanged.
- Release and compliance tests: 288 passed (before US3 card tests), release suite 182 passed after.

## US1/US2 code (2026-10-09)

- `benchmark.py` and `security can-ids freeze`: hashes in the common frame format, roles (validation = highest-numbered capture per attack type in train_01; ROAD `_2` runs and every fourth ambient capture are test; masquerade and accelerator out of scope), conflicts (same content with different vehicle labels, or train/validation and test in one set) stop the freeze until `resolutions.yaml` records action and reason; frozen manifests are never rewritten. Tests: 6.
- `detectors.py`: picket-forest, 4 controls, 4 rule/statistics baselines and 6 original-benchmark models behind one interface. The shuffled-label control needed three iterations to be a valid leakage check:
  - labels shuffled within a capture keep a capture-level signal (AUROC 0.62);
  - shuffling after the label-dependent subsampling leaks through the frame selection (0.78);
  - hard majority votes of a forest trained on random, imbalanced labels rank dense regions higher (0.80).

  The control now permutes labels across all training frames before subsampling, averages five seeds and scores with leaf probabilities: AUROC below 0.6 on synthetic data, as it must be.
- `evaluate.py` and `security can-ids evaluate`: per set fit on train, threshold and alarm operating points on validation only, four test splits; ROAD with the release model; Pareto table; C-versus-Python check; report, metrics, quality results (refused for partial runs). Tests: 5, including 0 C-versus-Python mismatches on a synthetic benchmark.
- Third-party side effect found: emlearn calls `numpy.seterr(all='raise')` at import (`emlearn/bayes.py`); the export now restores numpy's error state, and the test suite isolates it per test.

## Device evidence path (2026-10-09)

- PlatformIO project `firmware/picket-forest/platformio/` (envs `esp32`, `esp8266` = D1 mini at 160 MHz) reusing the existing replay sketch; `security can-ids measure` generates the sketch's sources, exported headers and synthetic test vectors.
- Local check with the 3-tree fixture model: both envs build; Espressif QEMU 9.2.2 (installed in `~/qemu`) runs the ESP32 image: 4,000 frames, 0 score mismatches against the host build, 2 of 2 expected alarms; detector code 2.3 KiB, detector state 10.2 KiB.
- Not added to `firmware.yml`: the build needs an exported model; CI builds it once the release export is staged (follow-up).
