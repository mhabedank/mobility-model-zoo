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
