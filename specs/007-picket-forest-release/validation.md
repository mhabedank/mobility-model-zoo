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
