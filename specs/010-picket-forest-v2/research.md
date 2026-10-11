# picket-forest 0.2.0: pre-registration (2026-10-10)

Written before any 0.2.0 measurement on test captures (constitution IV). Owner goal: frame-level attack-class F1 >= 0.7 on ROAD and fewer than 3 false alarms per hour on vehicles not seen in training, without methodological errors (memorisation, leakage).

## R1 Architecture: calibrate on the vehicle, then detect

- **Calibration phase (benign traffic of the target vehicle, on the device)**: a fixed table per CAN ID learned from benign frames only: median period, low percentile of the interval, expected count in a window, DLC, plus the set of known IDs and the bus frame rate. No attack label is used.
- **Features per frame, relative to the table** (so they transfer between vehicles): known ID, interval / calibrated period, frames of this ID in the last window / calibrated expected count, DLC differs from the calibrated DLC, payload change features of 0.1.0, unknown-ID and bus-rate ratios in the last window. No raw CAN ID, no absolute timestamps, no bus-level inter-frame gap (logger dependent; can-train-and-test attack captures carry a timestamp artefact there, see research 07).
- **Model**: random forest trained across vehicles on these relative features (can-train-and-test training captures, each with the table of its own vehicle), plus the alarm stage of 0.1.0. Hyperparameters and threshold chosen on validation captures only.
- **Why**: 0.1.0 compares an interval with a running mean of the same capture; a sustained rate doubling (all ROAD fabrication attacks: 100 → 200 frames/s of one ID) is absorbed after a few frames, and normal timing of an unseen vehicle looks abnormal. A fixed per-vehicle table removes both effects. This is how production IDS work (communication matrix or learned cycle times; research 07).

## R2 Benchmark `can-ids-v2` (new version; `can-ids-v1` stays frozen)

Same captures, roles and protocol as `can-ids-v1`, plus a role `calibration`:

- **can-train-and-test**: for every set and every vehicle that appears in the set (known and unknown), the calibration captures are that vehicle's attack-free and accessory captures from any `train_01`, excluding every capture whose content hash also appears in the set's test or validation captures. Benign frames only. Unknown vehicles therefore get a benign calibration recorded separately from the test captures, as a device would after installation.
- **ROAD**: calibration = the ROAD ambient captures with role `train` (2.4 h); the ROAD attack captures `_1` and `_3` are development captures (design checks only, never training data, never threshold selection); the `_2` attack captures and the four test ambient captures are touched once, for the final result.
- Calibration length is reported; a sweep (5, 15, 60 min, all) shows how false alarms depend on it.

## R3 Metrics and success criteria

- **ROAD**: frame-level attack-class F1 on the in-scope test captures (fabrication and fuzzing, `_2`), with the threshold chosen on can-train-and-test validation captures, never on ROAD. Success: F1 >= 0.70. Also reported: AUROC, episode recall, false alarms per hour on the ROAD test ambient captures.
- **Unseen vehicles**: false alarms per hour of the alarm rule on `test_02` and `test_04` (unknown vehicle) of every set. Success: below 3 per hour in every set (worst set), with the median reported; and ROAD test ambient below 3 per hour. Detection must not be bought with silence: episode recall on the same splits is reported and must be at least 0.5 (median).
- 0.1.0 is reported next to 0.2.0 on the same benchmark.

## R4 Controls against memorisation and leakage (all must pass)

- Calibration captures and test captures are disjoint by content hash (checked in code, run fails otherwise).
- No raw CAN ID and no absolute time among the features; a control forest with the raw CAN ID added must not be better than picket-forest on unknown vehicles by more than 0.05 F1 (if it is, the model leans on identifiers).
- `ctrl-id-lookup` (attack rate per CAN ID) must stay below picket-forest's F1 on unknown vehicles and on ROAD.
- Shuffled-label control: judged as amended in feature 007 (label-free reference and validation operating point); additionally a **rules-only baseline** on the same calibration table (flag if interval < 0.5 x calibrated period, rate ratio > 1.5, unknown ID or DLC change). If the forest does not beat the rules-only baseline on ROAD F1 or on unknown-vehicle false alarms, the release uses the rules and says so.
- Test captures are used once per configuration that is reported; every design decision is taken on validation and development captures and logged in `validation.md` with date.

## R5 Kill criteria

- ROAD F1 below 0.70 or unseen-vehicle false alarms at or above 3 per hour (worst set) with the final configuration: the goal is not met; report the numbers, keep 0.2.0 `experimental` (constitution 2.1.0) and decide on more data (research on additional datasets runs in parallel).
- Any control in R4 fails: no claim on transfer; investigate before release.
