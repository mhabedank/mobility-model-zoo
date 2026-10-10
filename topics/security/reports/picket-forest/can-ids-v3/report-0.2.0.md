# picket-forest 0.2.0 on can-ids-v3 (2026-10-10)

Feature 010. Pre-registration: `specs/010-picket-forest-v2/research.md`; every decision with date and data used: `specs/010-picket-forest-v2/validation.md`. Results file: `zoo/models/picket-forest/results/0.2.0/quality.json`.

## What changed against 0.1.0

0.1.0 learned "normal" from four vehicles and failed on others (ROAD F1 0.05, thousands of false alarms per hour on unseen vehicles at the event level). 0.2.0 first **calibrates on the vehicle**: a fixed table per CAN ID learned from benign traffic only (median interval, usual DLC, the largest number of frames in a window of max(0.25 s, 4 periods)), plus the set of known IDs. Ten features are expressed relative to this table (frame count against the calibrated maximum, interval against the calibrated period, unknown-ID counts over the last 256/2048 bus frames within 2 s, payload changes); no raw CAN ID, no absolute time, no bus-level gap. A random forest trained on can-train-and-test scores frames; an **event-level decision** then flags the following frames of an ID while its count stays 25 % above the calibrated maximum after two forest flags (an injection episode), and flags frames while several unknown IDs appear (fuzzing state).

## Benchmarks

- `can-ids-v2` = `can-ids-v1` plus a calibration plan (benign captures recorded separately from each set's test and validation captures; content-hash disjointness checked in code). Calibration: 11.8–24.9 min per can-train-and-test vehicle, 141.6 min for ROAD.
- `can-ids-v3` = `can-ids-v2` without four captures whose benign traffic is not from the labelled vehicle (12 IDs found in none of the four vehicles; audit of all 174 unique captures).
- Independent false-alarm data: KCID (DTU, CC BY 4.0), vehicles in no training data.

## Results (can-ids-v3, threshold from can-train-and-test validation captures only)

| Detector | ROAD F1 | ROAD test ambient FA/h | Unknown-vehicle FA/h, worst cell (median) | Unknown-vehicle episode recall (median) | Frame F1 median, unknown vehicle × known / unknown attack |
|---|---|---|---|---|---|
| `picket-forest-v2` (0.2.0) | **0.997** | **0.00** | **0.86** (0.00) | 0.83 | 0.55 / 0.77 |
| `ctrl-forest-v2-frames` (forest, no event decision) | 0.679 | 0.00 | 0.51 (0.00) | 0.80 | 0.93 / 0.91 |
| `rules-v2` (same table, no training) | 0.997 | 0.00 | 0.86 (0.00) | 0.80 | 0.55 / 0.77 |
| `ctrl-forest-v2-with-id` | 0.727 | 0.00 | 0.51 (0.00) | 0.82 | 0.92 / 0.92 |
| `ctrl-shuffled-v2` | 0.193 | 3,588 | 3,384 (1,439) | 0.96 | 0.33 / 0.22 |
| `ctrl-id-lookup` | 0.037 | 3,598 | 3,488 (3,245) | 1.00 | 0.01 / 0.02 |
| `bl-isolation-forest` | 0.010 | 145 | 3,323 (1,415) | 0.83 | 0.39 / 0.02 |
| `picket-forest` 0.1.0 | 0.258 | 3,570 | 26.4 (0.00) | 0.81 | 0.93 / 0.92 |

ROAD in detail (0.2.0): precision 0.996, recall 0.998; fabrication 0.998, fuzzing 0.993. Masquerade (out of scope): not detected (F1 0.0).

Frame F1 on can-train-and-test is lower with the event decision because that dataset labels only the injected frames, while the event decision also flags the legitimate frames of an attacked ID during the episode (ROAD labels those as attack). Both conventions are reported.

Known-vehicle cells are not part of the goal; the worst one (`set_01`, Impala, known attacks) has 7.86 false alarms per hour (rules 3.63).

### Independent false alarms (KCID, never used for a decision)

| Vehicle | Calibration | Test traffic | Alarms |
|---|---|---|---|
| 2017 Ford Focus (other drivers and days) | first 15 min of the first trace | 4.89 h | 0 |
| 2022 Honda CR-V | first 15 min of the first trace | 47.99 h | 0 |
| 2011 Chevrolet Traverse with OBD requests | 60 min of the same setup, diagnostic IDs included | 22.0 h | 0 |

74.9 h without an alarm bound the rate below 0.04 per hour (95 %). Limits found on the same data: calibrated from another recording of the same Traverse (can-train-and-test, no parked/accessory phases, no diagnostics) the detector alarms about 3,000 times per hour, because IDs of the parked mode and the diagnostic IDs are unknown; a diagnostic dongle plugged in after calibration alone causes about 850–1,100 alarms per hour (it is a new device querying ECUs, which is security relevant, but a flood in operation). On AutoHack, with only 16 s to 6 min of attack-free calibration per bus, F1 is 0.68–0.83 and false alarms are 105–741 per hour.

## Goals of the owner (research R3)

- ROAD F1 ≥ 0.7: **met** (0.997).
- Fewer than 3 false alarms per hour on unseen vehicles: **met** on can-ids-v3 (worst cell 0.86) and on KCID (0 in 74.9 h), provided the calibration covers the vehicle's operating modes.
- Episode recall on unknown vehicles ≥ 0.5: met (0.83).

## Methodological checks and caveats

- Calibration and test captures are content-hash disjoint (checked in code); no raw CAN ID among the features; the raw ID adds nothing (control passed); the per-ID lookup fails (control passed).
- **Shuffled-label control fails its pre-registered rule.** The shuffled forest reaches frame F1 up to 0.63 at the validation operating point but raises 1,400–3,400 false alarms per hour. Its labels are permuted before any other step, so no label information can reach it; the calibrated features are themselves label-free anomaly signals (the untrained rules on the same table reach F1 0.55/0.77). Reported as failed, not explained away.
- **Forest versus rules:** on the goal metrics the event candidate and the untrained rules are practically equal (ROAD F1 0.9972 vs. 0.9968, same worst-cell false alarms). The calibration and the relative counts do the work; the forest adds episode recall (0.83 vs. 0.80) and frame precision under the can-train-and-test convention. The pre-registered check "forest beats rules on ROAD F1 or false alarms" passes only by 0.0004 F1.
- **Test reuse:** the ROAD and can-train-and-test test captures were scored five times during this feature (v2; v3; event candidate with a harness bug; corrected harness; after the recording-gap fix). Every change was decided on development data, except two flaws found by diagnosing test results (harness threshold, recording gap); both are logged. KCID is the independent confirmation.
- Data findings published in the validation log: four can-train-and-test captures carry benign traffic of no labelled vehicle; the CAN-MIRGU archive at UCI is corrupt.

## Verification after the result (memorisation, blind spots)

See `specs/010-picket-forest-v2/validation.md`, section "Verification". In short: no memorisation (untrained rules give the same numbers); detector live on unseen vehicles (injected attacks: rules 30/30 episodes, event candidate 23/30, missing fabrications); false alarms depend strongly on the calibration (ROAD: 44 FA/h with 15 min, 0 with 142 min); one new legitimate ID causes 444–531 FA/h on AutoHack C-CAN; KCID Honda CR-V is a gateway-filtered port with 6 IDs and weak evidence. The false-alarm goal is therefore met only under a calibration that covers the vehicle; it is not shown in general.

## Not done yet

- C port of the calibration table and the event decision, device measurement (ESP32-S3 budget 16 KB RAM, 128 KB flash), release export and card.
- Diagnostic sessions: one event per new ID instead of continuous alarms, and diagnostic IDs as their own category.
- Release status: `experimental` per constitution 2.2.0 until the owner decides (shuffled-label control failed formally; no device evidence yet).
