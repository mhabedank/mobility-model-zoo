# Quickstart: validating the mobility image library

Feature: [spec.md](spec.md) · Contracts: [cli.md](contracts/cli.md), [checks.md](contracts/checks.md)

## Prerequisites

- `uv sync --extra release --extra images --group site-check` and `uv run playwright install chromium`
- For rendering: the DGX Spark over the VPN with the `zoo-flux` container and the model cache (016 README under `scripts/imagery/`)

## 1. Calibration before rendering (research R4, R5, R11)

```bash
uv run zoo site images triage ~/zoo-imagery/calib --round 0
```

`~/zoo-imagery/calib` holds the 016 renders (`out6`, 60 PNGs with manifest) and a manifest-wrapped copy of the rejected night-and-rain and photoreal series. Expected: all six approved images and at least 70% of the 016 shortlist `shown`; every image of the rejected series `rejected` by I6; between seeds of one subject, I7 rejects at most one in twenty. Otherwise adjust `palette` thresholds or `duplicate_max_bits` in the series file and repeat; if no setting separates them, apply the kill criterion of R4.

## 2. Draft pass (agent review of subjects)

On the Spark:

```bash
python /work/gen.py --series /work/siebdruck.yaml --model draft --seeds 2 --out /work/rounds/draft
```

About 15 minutes. The agent looks at the drafts, rewrites subjects the model misreads in `subjects.md` and the series file, and re-drafts only those (`--only theme/subject`).

## 3. Final pass and triage

```bash
python /work/gen.py --series /work/siebdruck.yaml --model final --seeds 4 --out /work/rounds/1
rsync -a dienstollama@10.123.47.52:zoo-imagery/rounds/1/ ~/zoo-imagery/rounds/1/
uv run zoo site images triage ~/zoo-imagery/rounds/1 --round 1
open ~/zoo-imagery/rounds/1/sheet.html
```

Expected: about 420 candidates; the summary names how many are shown, how many are rejected per check, and which subjects have no shown candidate. The sheet shows only `shown` candidates, numbered within each subject, grouped by theme.

## 4. Picks and import

The owner states picks by number (`rail/high-speed-viaduct: 3`, `water/lock-gate: none`, …). The agent writes `~/zoo-imagery/rounds/1/picks.yaml`, then:

```bash
uv run zoo site images pick ~/zoo-imagery/rounds/1 --dry-run
uv run zoo site images pick ~/zoo-imagery/rounds/1
uv run zoo site images check --require-coverage
```

Expected: one record per numbered pick under `zoo/site/images/<theme>-<subject>/` with three derivatives and no PNG; `next.txt` lists the `none` subjects; the coverage report shows every theme's count. `triage.json`, `picks.yaml` and `next.txt` are copied to `specs/019-mobility-image-library/rounds/1/`.

## 5. Second round

```bash
scp ~/zoo-imagery/rounds/1/next.txt dienstollama@10.123.47.52:zoo-imagery/rounds/2/next.txt
python /work/gen.py --series /work/siebdruck.yaml --model final --seeds 4 --seed-base 1000 --out /work/rounds/2
```

Then steps 3 and 4 for round 2. Repeat until `check --require-coverage` passes (SC-001).

## 6. Site and repository checks

```bash
uv run zoo site images check --deep        # I1, I2, I4 (on the 1600 px derivatives), I7, I8, L1
uv run zoo site build && uv run zoo site check --a11y
du -sh zoo/site/images                     # ≤ 40 MB of derivatives (L1 also enforces it)
ls _site/assets/images | wc -l             # 3 × placed records (+ set.json): no unplaced image in the build
uv run zoo compliance render && uv run reuse lint
uv run pytest tests/website tests/imagery
```

Expected: every check passes; `_site/assets/images/` holds only the placed records' derivatives; the credits page lists the placed records only; `REUSE.toml` has one annotation per record directory.

## 7. Placement from the pool (SC-008)

```bash
uv run zoo site images overview && open .cache/site/pool.html
```

Pick an image for a model that has only its topic image, add `model:<name>` to that record's `placements`, rebuild and open the model page: the image is on the stage behind the motif plate, the credits page lists it, `set.json` changed. No rendering, one record change.

## 8. Reproducibility (SC-006)

On the Spark, in the container, with three records chosen at random:

```bash
uv run zoo site images check --regenerate   # I5 against the 1600 px derivative
```

Expected: pHash distance ≤ 4 for each.

## 9. Blind test (SC-003)

Show ten library images from at least five themes to five people: "Do these come from one source or series?" and "What is each image about?" Record the answers in `validation.md`. Target: at least four of five say one series; at least four of five name the mobility subject of each image.
