# Quickstart: validating feature 016

Run these steps to show that the feature works end to end. Contracts: [checks](contracts/checks.md), [cli](contracts/cli.md). Entities: [data model](data-model.md).

## Prerequisites

On the developer machine:

```bash
uv sync --extra release --extra images --group site-check
uv run playwright install chromium
```

On the Spark (once; see `scripts/imagery/README.md`): build the `zoo-flux` container and let the first run cache the models.

## 1. Every model has a motif (Story 2)

```bash
uv run zoo site build --no-images
uv run zoo site check --only M1,M2
```

Expected: both pass. Remove one motif file and rebuild; the build fails with M1 and names the model. Restore it.

## 2. Render and import an image (Stories 1, 3, 4)

On the Spark, render the series with the final model:

```bash
docker run --rm --gpus all --ipc=host -v ~/.cache/huggingface:/root/.cache/huggingface -v ~/zoo-imagery:/work zoo-flux \
  python /work/gen.py --series /work/siebdruck.yaml --model final --seeds 4 --out /work/out/siebdruck
```

Copy the output directory to the developer machine, then import the chosen seed:

```bash
uv run zoo site images add out/siebdruck/start-hero-2-1021.png --manifest out/siebdruck/manifest.json \
  --placement start-hero --focal 0.5,0.55 \
  --scene "Regional train leaving a small station at dawn" \
  --alt "A regional train pulls out of a small station platform in warm morning light" --dry-run
```

Expected: every check prints `pass`. Run again without `--dry-run`; `zoo/site/images/<id>/` now holds the record, the source PNG and three WebP files with the IPTC marker.

Rejection cases (each must fail with a named reason and write nothing):
- a render with a visible face (faces);
- a render with readable text or a plate-like string (text);
- a manifest entry with a missing field or a model outside the accepted set (I2).

## 3. Build, check, look

```bash
uv run zoo site build
uv run zoo site check --a11y
uv run zoo site images check --deep
uv run zoo site serve
```

Expected: all checks pass, including S1 to S4, C1, I1 to I4, M3 to M5 and X1. Open `http://localhost:8000/mobility-model-zoo/` at desktop and 390 px width, in light and dark mode:
- the start page shows the hero image and the topic images, and the purpose line is on a plain surface;
- tiles show motifs on plates at least 64 px tall;
- a published model page shows the plate in front of the image stage, also at 390 px;
- `/credits/` lists every image as AI-generated with model, licence, date and hardware class, and every page footer says "Images are AI-generated".

## 4. Removal and fallback (Story 4, FR-016)

```bash
uv run zoo site images remove <id>
uv run zoo site build --no-images
```

Expected: the files and credit are gone, a warning names the placement, the page shows the fallback and no broken image. `git checkout` the directory to restore it.

## 5. Reproducibility (FR-018, SC-008)

On the Spark:

```bash
uv run zoo site images check --regenerate
```

Expected: every record's regenerated PNG is within the perceptual tolerance of its source (I5); a bit-identical match is reported as such.

## 6. Preview cards (Story 5)

```bash
uv run zoo site build
uv run zoo site check --only O1,O2,O3,O4,O5
```

Expected: every card shows its model's motif fully opaque in the centre; picket-forest now has one.

## 7. Compliance

```bash
uv run zoo compliance render
uv run reuse lint
```

Expected: `REUSE.toml` and `THIRD_PARTY_NOTICES.md` contain the image and model blocks; lint passes.

## 8. User test (SC-001, SC-003)

Show the start page for five seconds to at least five people, then ask what they saw and ask them to match three motifs to model names. Record the answers in `validation.md` of this feature. It can share its session with the 008 SC-001 test.
