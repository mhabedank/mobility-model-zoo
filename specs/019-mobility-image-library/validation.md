# Validation: Mobility image library in the house style

Feature: [spec.md](spec.md) · Plan: [plan.md](plan.md) · Quickstart: [quickstart.md](quickstart.md)

## 1. Calibration of I6 and I7 (task T025, research R4 and R5), 2026-10-14

**Data**: the 016 renders still on the Spark, copied to `~/zoo-imagery/calib/` and wrapped into round 0 with `scripts/imagery/wrap_manifest.py` (audit trail: [rounds/0/](rounds/0/)):

| Set | Source on the Spark | Renders | Owner's judgement |
|---|---|---|---|
| approved-qwen | `out6/qwen` | 44 | SIEBDRUCK finals the six picks came from |
| approved-qwen-fix | `out6/qwen-fix` | 12 | SIEBDRUCK finals, corrected subjects |
| approved-klein | `out6/klein` | 22 | SIEBDRUCK drafts (information only) |
| rejected-night | `out` | 11 | night-and-rain series, rejected as depressive |
| rejected-photoreal | `out3/qwen` | 44 | photoreal FORWARD series, rejected as too close to photographs |

**Anchors**: k-means with k = 6 over the Lab pixels of the 56 approved Qwen renders (`measure_anchors`): accent `[57.0, 21.5, 53.9]` and five tones from navy `[11.9, 3.2, -21.2]` to cream `[92.2, -4.7, 14.7]`, written to `palette.anchors` of the series file.

**Measured shares of pixels outside the palette (`other_share`, tolerance ΔE 18)**:

| Set | min | median | max |
|---|---|---|---|
| approved-qwen (44) | 0.015 | 0.047 | 0.175 |
| approved-qwen-fix (12) | 0.032 | 0.047 | 0.139 |
| the six records | 0.032 | 0.054 | 0.139 |
| approved-klein (22) | 0.015 | 0.070 | 0.250 |
| rejected-night (11) | 0.275 | 0.561 | 0.737 |
| rejected-photoreal (44) | 0.530 | 0.682 | 0.836 |

`other_max = 0.22` separates every approved final render from every rejected render with margin (0.175 vs 0.275). The accent-concentration measure (`accent_largest_share`) does not separate the sets (approved 0.08–0.93, rejected 0.15–0.96; wheels, lamps and details split the accent), so `largest_min` is set to 0.07, which catches only scattered accent. `accent_top_share` is at most 0.107 on approved renders and up to 0.685 on the photoreal sunrises, so `top_max = 0.15` holds. `accent_min = 0.0015` (approved minimum 0.002), `accent_max = 0.30`.

**Triage of round 0 with the calibrated series** (`zoo site images triage ~/zoo-imagery/calib/round0 --round 0`, 47 s for 133 candidates):

| Set | shown | I4 faces | I4 text | I6 style | I7 duplicate |
|---|---|---|---|---|---|
| approved-qwen | 30 | 3 | 7 | 0 | 4 |
| approved-qwen-fix | 4 | 0 | 0 | 0 | 8 |
| approved-klein | 19 | 1 | 1 | 1 | 0 |
| rejected-night | 0 | 4 | 0 | 7 | 0 |
| rejected-photoreal | 0 | 23 | 2 | 19 | 0 |

- **Owner-approved images**: the six records themselves appear in the sets as identical files and are flagged by I7 as twins of the records (0 bits), which is the intended behaviour; none of the 56 approved finals fails I6. The I4 rejections among them (dial digits, small faces) are the same renders 016 rejected.
- **Owner-rejected series**: 55 of 55 rejected; of those not already stopped by the face detector, 26 of 26 fail I6, and the measured `other_share` shows every one of them would (minimum 0.275 > 0.22).
- **Kill criteria** (plan, Constitution Check): not triggered.

**I7 threshold**: pHash Hamming distances over the 56 approved finals: between seeds of one subject min 10, median 28 (196 pairs); between different subjects min 0 (identical renders present in both `qwen` and `qwen-fix`), 5th percentile 22 (1344 pairs). At `duplicate_max_bits = 10`, one of 196 same-subject pairs is flagged (0.5 %, under the one-in-twenty limit) and, apart from identical files, one different-subject pair (two picket-forest renders of nearly the same bench composition). The provisional value 10 is kept.

## 2. Migration of the six 016 records (task T026)

`theme` and `subject` added (rail/regional-dawn, rail/tram-interior, private-road/workshop-bay, rail/wheelset-hall, rail/train-window-notebook, workshop/circuit-bench); I6 measured on the sources (`other_share` 0.032–0.139, all pass); pHashes stored; the six source PNGs removed from the tree (FR-015; they stay in git history and on the Spark); `source.file` dropped. `zoo site images check` passes (I1, I2, I7, I8, L1). After the migration `zoo site build` (9 pages, 6 images) and `zoo site check --a11y --offline` pass every check, including the browser checks (2026-10-14).

**Deep check without sources** (found while running T051 on the migrated records): on the 1600 px derivatives the detectors flagged the approved picket-forest image (a 31 px "face", text "600") and, at source scale, the wheelset image (text "CO") although both source PNGs passed at import. Lossy derivatives are not the checked picture, so `check --deep` now reports derivative hits as notes and fails only on sources (contracts/checks.md, I4; research R1). The site job in CI keeps running `--deep` for I1 and for any cached sources.

## 3. Draft pass (task T027), 2026-10-14

210 drafts (105 subjects × 2 seeds, FLUX.2-klein-4B, median 4.1 s per image) reviewed by the agent on per-theme contact sheets. The draft model misreads the same kind of subject 016 saw: whenever the subject is a piece of equipment rather than a vehicle (sensor, cabinet, test rig, drone, console), it paints a vehicle. 27 prompts were rewritten with a close view, the equipment named first and an explicit "no vehicles" where needed:

- rail: level-crossing (lowered barrier arms), track-maintenance (rail-mounted), pantograph (train roof)
- public-road: coach-motorway (touring coach with a high deck, had become a van)
- private-road: car-sharing-row (one orange car among navy ones; the accent had spread over the row)
- active: cycle-highway (had become cars on a flyover), pedestrian-street (a bus had appeared), scooter-dock (one orange scooter)
- air: cargo-drone-field (quadcopter with four rotors, had become a helicopter)
- infrastructure: control-room (console had become a van), signal-cabinet (cabinet had become a van), weather-mast, spiral-ramp
- workshop: axle-press, brake-rig (had become a truck), engine-stand (had become a locomotive), rail-pit (had become a trailer), wind-tunnel (had become a real train)
- iot: bearing-sensor (had become a locomotive), bridge-strain (trains on the bridge), cabinet-gateway, gantry-camera (a van on the gantry), roof-antenna (a pantograph), tyre-valve-sensor (a whole car)
- ai: drone-yard (helicopter), edge-box-bus (bus exterior), spectrogram-screen

The rewritten subjects were re-drafted (`rounds/draft2`) before the final pass. Known weak subjects kept as they are because Qwen rendered them correctly in 016: wheelset-hall, circuit-bench.

## 4. Rounds and coverage (SC-001, SC-002)

| Round | Rendered | Shown | Rejected (faces / text / style / duplicate) | Owner picks | none |
|---|---|---|---|---|---|
| 1 (105 subjects × 4 seeds, 2026-10-15) | 420 | 369 | 19 / 7 / 19 / 6 | 72 | 25 (+2 subjects without a shown candidate) |
| 2 (27 open + 5 reserve subjects, seeds +1000, 2026-10-16) | 128 | 111 | 5 / 5 / 5 / 2 | 13 | 19 |

Audit trail: [rounds/1/](rounds/1/), [rounds/2/](rounds/2/) (manifest, triage, picks, next). The owner picked on the clickable contact sheet (picks kept in the browser, exported as `picks.yaml`).

**Pool at the close of the feature (2026-10-16): 91 records**, the six 016 images included.

| Theme | Records | Minimum | Share |
|---|---|---|---|
| rail | 13 | 10 | 14 % |
| public-road | 8 | 6 | 9 % |
| private-road | 10 | 8 | 11 % |
| active | 8 | 6 | 9 % |
| water | 7 | 5 | 8 % |
| air | 6 | 4 | 7 % |
| infrastructure | 15 | 14 | 16 % |
| workshop | 5 | 8 | 5 % |
| iot | 8 | 10 | 9 % |
| ai | 11 | 10 | 12 % |

**SC-001 not met**: 91 < 100, `workshop` and `iot` under their minimums. The owner declined a third round on 2026-10-16 ("we have enough images for now") after rejecting the remaining workshop and IoT subjects twice (eight seeds each). The coverage table stays the target for later rounds; `check --require-coverage` reports the gap and is not part of CI. No theme exceeds the 20 % cap.

**SC-002 met**: `zoo site images check --deep` passes for all 91 records (I1, I2, I7, I8, L1; I4 on the derivatives at source scale, reported as notes per section 2). Every rejection of both rounds is in `triage.json` with its reason.

## 4a. Weight of the pool (FR-016, L1)

91 records: 9 163 116 bytes of derivatives (9.2 MB, L1 limit 40 MB), 9.7 MB on disk including the records; about 101 KB per image.

## 4b. Site and full run (SC-007, FR-018, FR-021), 2026-10-16

With 91 records: `zoo site build` renders 9 pages with 6 images in 1.6 s; `_site/assets/images/` holds 19 files (the six placed records' derivatives plus `set.json`), no file of an unplaced record; `zoo site check --a11y --offline` passes every check including the browser checks; 291 fast and 27 slow tests pass; `zoo compliance render` writes one CC0 annotation per record directory and `reuse lint` passes.

## 5. Repository weight and clone time (SC-005)

Baseline before the pool (main at `8aebe7e`, 2026-10-14): `git clone` from GitHub 2.89 s, pack 13.91 MiB.

After the pool (uncommitted working tree, 2026-10-16): the pool adds 9.7 MB of records and derivatives plus 1.5 MB of round audit files (`rounds/0..2`), about 11.2 MB against a pack of 13.9 MiB; the derivatives are already compressed, so the pack grows by roughly the same amount. Measured clone time after the merge to main: _owner step, see tasks T044_ (expected well under the 25 % limit only if the network, not the pack, dominates; a 2.9 s baseline clone could become about 5 s, which is over 25 % but under 3 s absolute growth; the spec's 25 % criterion is reported as at risk).

## 6. Regeneration (SC-006), 2026-10-16

Three records chosen at random (`random.seed(19)` over the round-rendered records) were re-rendered on the Spark in the `zoo-flux` container from their recipes (`scripts/imagery` recipe dump, `regen.py`; model revision `25468b98e3276ca6700de15c6628e51b7de54a26` as recorded):

| Record | sha256 equals the recorded source | pHash vs original PNG | pHash vs 1600 px derivative |
|---|---|---|---|
| active-riverside-cyclists | yes (bit-identical) | 0 bits | 4 bits |
| ai-tablet-trackside | yes (bit-identical) | 0 bits | 0 bits |
| rail-freight-containers | yes (bit-identical) | 0 bits | 4 bits |

**SC-006 met**: all three are bit-identical to the sources the records describe, and within the 4-bit I5 threshold even against the lossy derivative. The regenerated PNGs stay under `~/zoo-imagery/regen/out/` on both machines.

## 7. Blind test (SC-003), owner-run

Show ten library images from at least five themes to five people. Ask: "Do these come from one source or series?" and "What is each image about?" Target: at least four of five say one series; at least four of five name the mobility subject of each image. Record the answers here.

| Person | One series? | Subjects named correctly (of 10) |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
