# Task: CAN intrusion detection (`can-ids`)

Models: `picket-forest` (random forest, emlearn C) and `picket-mlp` (int8 MLP on the `microinfer` engine).

## Scope

- **In:** per-frame and per-event detection of injection, fuzzing, masquerade and scanning attacks on classic CAN (11-bit identifiers, up to 8 data bytes), running on a gateway or ECU-class microcontroller.
- **Out:** CAN FD, automotive Ethernet, response or blocking actions, root-cause attribution of an attack. The models raise an alarm; they are not a safety mechanism and do not replace an intrusion detection system certified for a vehicle.

## Reference

Dataset labels (ground truth). Each frame of the test captures is labelled attack or benign by the dataset authors:

- can-train-and-test (Lampe & Meng, CC BY 4.0): the `attack` column.
- ROAD (ORNL, CC BY 4.0): frames inside the injection interval that carry the injected identifier (any identifier for fuzzing), from `capture_metadata.json`.

Metrics name this reference. Agreement with other models is never reported as accuracy.

## Benchmark `can-ids-v1`

Built from the common frame format (`security/can_ids/frames.py`: `ts_us, can_id, dlc, b0..b7, label, capture, vehicle`) and frozen at first use (`security can-ids freeze`, split manifest with hashes):

- **can-train-and-test, four-way split** per set (set_01..set_04): train on `train_01`; test on known vehicle × known attack, unknown vehicle × known attack, known vehicle × unknown attack and unknown vehicle × unknown attack.
- **ROAD held-out captures:** attack captures whose name ends in `_2` (also `_2_masquerade`), and every fourth ambient capture by a CRC32 hash of the file name.

Both `picket-*` models are scored on both test sets with the same code (constitution VIII). The reported result is the deployed arithmetic: emlearn float C code for `picket-forest` (checked against Python, identical scores), int8 on the bit-exact host reference for `picket-mlp`. Float results of `picket-mlp` are informative only.

## Metrics

Formulas as in `src/mobility_model_zoo/security/can_ids/metrics.py`.

| Level | Metric | Definition |
|---|---|---|
| frame | precision, recall, F1 | attack is the positive class; prediction = score ≥ threshold |
| frame | FPR | share of benign frames flagged |
| frame | AUC-PR | average precision of the score |
| event | episode recall | attack frames closer than 1 s form an episode; an episode is detected if an alarm falls inside it or up to 1 s (grace) after it ends |
| event | time to alarm | median delay from episode start to the first true alarm |
| event | **false alarms per hour** (headline) | alarms outside every episode and its grace period, per hour of recording |

The headline pair is false alarms per hour at the chosen alarm rule, reported with episode recall: an operator sees alarms, not frames.

## Tool

`uv run security can-ids …` (`frames`, `forest evaluate|alarms|export|convert|testvectors`, `mlp train`, `evaluate`, `freeze`). Data and outputs live in `$MMZ_DATA`, never in the repository.

## Frameworks and why

- **scikit-learn + emlearn** for tree models: random forests are strong on tabular per-frame features, need no floating-point heavy maths at inference, and emlearn exports them as plain C. The split thresholds are written as float32 literals that reproduce scikit-learn's decisions exactly, so the C code and Python give identical scores.
- **Keras + LiteRT (TFLite) int8** for neural nets: full-integer quantisation gives one model file that runs on the zoo's `microinfer` engine bit-exactly (checked against the TFLite interpreter) and on other TFLite runtimes.

## Riskiest assumption

Detection transfers to unseen vehicles and unseen attack types. The four-way split of can-train-and-test tests this before any scaling (constitution IV): a model that only works on the vehicle it was trained on is not released.

## Hardware budget

Reference board ESP32-S3. Per model at most **16 KB RAM** (features, model state and alarm stage) and **128 KB flash**. Measured on the HIL bench; each measurement records whether it comes from a real board, an emulator or the simulator.

## Status

Pre-zoo research results of `picket-forest` (from the former repository mhabedank/mobility-security-ml) are kept in `topics/security/reports/picket-forest/` and labelled "pre-zoo research result: not a benchmark result". They do not pass or fail a gate, set a threshold or appear in a model card.
