# Validation log: picket-forest 0.2.0

## Development decisions (2026-10-10, before any test capture was scored)

Data used: can-train-and-test `train_01` captures (training, validation, and non-calibration captures as development set), ROAD ambient `train` captures (calibration; `ambient_highway_street_driving_long` held out as development false-alarm capture), ROAD attack captures `_1` and `_3` (development only, never training). No ROAD `_2` capture and no ROAD test ambient capture was scored.

1. Interval features against a running mean (0.1.0) absorb a sustained rate doubling; ROAD fabrication attacks double the rate of one ID (100 → 200 frames/s) and label every frame of that ID in the window. First calibrated features (interval / calibrated median): ROAD dev F1 0.52, AUROC 0.95.
2. Interval percentiles flagged bursty event-triggered IDs; replaced by frame counts per ID in a window of max(0.25 s, 4 periods) against the calibrated maximum. Counts are also robust to the compressed timestamps of can-train-and-test attack captures.
3. ROAD fuzzing labels every frame in the injection window; about 6.5 % of them carry unknown IDs, against one unknown frame per hour outside. Added unknown-ID counts over the last 256 and 2048 bus frames (fuzzing state). Single unknown IDs alone do not flag (sporadic wake-up IDs missing from a short calibration caused most false alarms).
4. Warm-up after capture start (0, 2, 5 s) compared: 0 s keeps episode recall and stays below 3 false alarms per hour; chosen 0 s.
5. Development results (no warm-up):

| Variant | ROAD dev F1 | ROAD held-out ambient FA/h | ctt dev F1 (set_01..04) | ctt dev FA/h (set_01..04) |
|---|---|---|---|---|
| forest (calibrated features) | 0.829 | 0.00 | 0.91 / 0.98 / 0.97 / 0.95 | 1.87 / 1.60 / 0.00 / 0.68 |
| rules only (same table) | 0.972 | 0.00 | 0.84 / 0.57 / 0.87 / 0.60 | 4.36 / 3.73 / 1.86 / 1.36 |
| forest OR rules | 0.972 | 0.00 | 0.84 / 0.57 / 0.87 / 0.60 | 4.36 / 3.73 / 1.86 / 1.36 |

6. **Release candidate: the forest on the calibrated features, no warm-up**, threshold chosen on can-train-and-test validation captures.
7. **Reading of R4 "forest vs. rules", fixed before the test run**: the forest is kept if it beats the rules-only baseline on at least one of (ROAD F1, false alarms per hour on unknown vehicles); otherwise the rules are released. The rules-only baseline is reported with the same metrics. Reason for writing this down: the sentence in research R4 is ambiguous; on development data the rules miss the false-alarm goal (up to 4.36 per hour) and the forest misses nothing.

## Test run on can-ids-v2 (2026-10-10, first and primary result)

Seven detectors, four sets plus ROAD, threshold from can-train-and-test validation captures only. Calibration: 11.8–24.9 min per can-train-and-test vehicle, 141.6 min for ROAD.

| Detector | ROAD F1 (in scope) | ROAD test ambient FA/h | Unknown-vehicle FA/h, worst cell (median) | Unknown-vehicle episode recall (median) | F1 median, unknown vehicle × known / unknown attack |
|---|---|---|---|---|---|
| picket-forest-v2 | **0.755** (P 0.999, R 0.606; fabrication 0.84, fuzzing 0.12) | 0.00 | 8.76 (0.00); 7 of 8 cells 0.00 | 0.74 | 0.93 / 0.91 |
| rules-v2 | 0.997 | 0.00 | 9.85 (0.34) | 0.80 | 0.55 / 0.76 |
| ctrl-forest-v2-with-id | 0.650 | 0.00 | 8.76 (0.00) | 0.83 | 0.91 / 0.92 |
| ctrl-shuffled-v2 | 0.040 | 3,590 | 3,383 (2,064) | 0.95 | 0.22 / 0.19 |
| picket-forest 0.1.0 | 0.398 | 3,569 | 17.2 (0.00) | 0.81 | – |

- Goals: ROAD F1 met; unknown-vehicle false alarms missed in one cell (`set_04`, Traverse, unknown attacks: 8.76 per hour); episode recall met. Verdict of the harness: goal missed.
- Controls: raw CAN ID adds nothing (passed); `ctrl-id-lookup` far below (passed); forest beats rules on unknown-vehicle false alarms (passed, rules reach higher ROAD F1); shuffled-label control **failed** under the amended rule of feature 007 (F1 at the validation point up to 0.60, AUROC above the isolation-forest reference). The shuffled forest produces 2,000–3,400 false alarms per hour; its frame F1 comes from the calibrated features themselves being label-free anomaly signals (the untrained rules on the same table reach F1 0.49–0.76). The labels are permuted before any other step, so no label information can reach it; the pre-registered rule nevertheless counts as failed and is reported as such.

## Data finding after the v2 test run (2026-10-10)

- All alarms of the failing cell fall into two 4–5 s captures (`set_04/test_04/fuzzing-1`, `-2`, byte-identical to `set_02/train_01/fuzzing-1`, `-2`). Their benign frames use 12 IDs that occur in none of the four vehicles' calibration captures (ID overlap 0–8 %).
- Audit of all 174 unique can-train-and-test captures with the same test (share of benign frames whose ID is known to the labelled vehicle below 0.9, or a better-matching vehicle): exactly four captures flagged, all with the same 12 foreign IDs: `set_01/train_01/DoS-1`, `DoS-2` and `set_02/train_01/fuzzing-1`, `fuzzing-2`. They were also the source of the start-of-capture false alarms seen during development.
- New benchmark version `can-ids-v3` = `can-ids-v2` without these captures (role `excluded`, reason recorded). Because the audit followed the first test run, v2 stays the primary result and v3 is reported as the corrected result next to it.
