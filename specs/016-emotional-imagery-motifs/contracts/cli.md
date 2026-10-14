# Contract: command line of feature 016

Two parts: the generator, which runs on the GPU machine, and `zoo site images`, which imports and checks images in the repository. The existing `zoo site build`, `check` and `serve` keep their options.

## Generator: `scripts/imagery/gen.py` (runs inside the `zoo-flux` container on the Spark)

```
python gen.py --series <name>.yaml --model {klein|qwen} [--seeds N] [--steps N] [--only placement,...] --out <dir>
```

- Reads the series file (style, negative, subjects per placement, model defaults).
- Writes `<out>/<placement>-<n>-<seed>.png` and `<out>/manifest.json` with one entry per image: model, revision, pipeline, prompt, negative prompt, seed, steps, guidance, width, height, seconds, generated date, hardware class, generator commit and container image digest.
- Skips images that already exist, so a run can be resumed.
- `scripts/imagery/Dockerfile` builds `zoo-flux` from the NGC PyTorch container; `scripts/imagery/README.md` gives the three commands to build, download and render.

## `zoo site images add <png> --manifest <manifest.json>`

Imports one generated image from a generator output directory.

| Option | Meaning |
|--------|---------|
| `<png>` | The source PNG as written by the generator |
| `--manifest` | The generator's manifest; the entry is matched by file name |
| `--id` | Record id (default: derived from placement and seed) |
| `--placement` (repeatable, required) | `start-hero`, `topic:<id>` or `model:<name>` |
| `--focal X,Y` (required) | Fractions of width and height that stay visible in every crop |
| `--scene "<line>"` (required) | One-line description for the credits page |
| `--alt "<sentence>"` (required) | Scene sentence; the "(AI-generated image)" suffix is added |
| `--dry-run` | Run every check, write nothing, print the findings |

Behaviour:
1. Verify the manifest entry is complete and the model's licence is accepted (I2).
2. Run the face and text checks on the PNG (I4).
3. Crop around the focal point, encode the three WebP derivatives with the IPTC marker, enforce byte caps.
4. On success write `zoo/site/images/<id>/image.yaml`, copy the PNG and write the derivatives. On any failure write nothing.

Exit codes: 0 written (or dry run passed), 1 a check failed (every failed check is printed with its reason), 2 the manifest entry was not found.

## `zoo site images check [--deep] [--regenerate]`

Validates all records (I1, I2). `--deep` re-runs the detectors on the source PNGs (I4). `--regenerate` re-renders each record on the current machine and compares hashes (I5; needs the GPU and the `images` extra plus the model cache). Exit 0 or 1.

## `zoo site images list`

One line per image: id, series, placements, model, generated date, bytes of the 960 px derivative.

## `zoo site images remove <id>`

Deletes the image directory. The next `zoo site build` no longer contains the files or the credit, and the affected placements fall back (FR-016). Prints the placements that now fall back.

## `zoo site build` (changed)

- Copies image derivatives to `_site/assets/images/`, writes `assets/images/set.json`, renders `/credits/`.
- Fails when a model the site shows has no motif (M1).
- Prints one warning per placement without an image.

## `zoo compliance render` (changed)

Adds the image and model blocks to `REUSE.toml`, `THIRD_PARTY_NOTICES.md` and the record of processing (data model, "Generated compliance blocks").

## Dependencies

- New optional extra `images` in `pyproject.toml`: `pillow`, `opencv-python-headless`, `rapidocr-onnxruntime`. Only `zoo site images add` and `check --deep` import them; if the extra is missing, those commands print the install line and exit 2.
- The generator's dependencies (torch, diffusers) live only in the container, never in the package.
