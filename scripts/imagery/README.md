# Website imagery: rendering on the DGX Spark

The images of the zoo website (features 016 and 019) are generated, never fetched. The recipe of every
image lives in its record under `zoo/site/images/<id>/image.yaml`; the art direction is the
series file `zoo/site/images/series/siebdruck.yaml`. This directory holds the generator and its
container. Nothing here is part of the package, and `zoo site build` never needs it.

Hardware: the DGX Spark (`cst-ai-02`, GB10, reached over the VPN; see the project's `.env`
`SPARK_HOST`). A developer machine with a CUDA GPU works too; the record then says
`hardware: dev-machine`.

## 1. Build the container (once)

```bash
docker build -t zoo-flux scripts/imagery
```

## 2. Cache the models (once)

Both models are Apache-2.0 and not gated. Downloads go faster with the xet backend disabled.

```bash
docker run --rm -e HF_HUB_DISABLE_XET=1 -v ~/.cache/huggingface:/root/.cache/huggingface zoo-flux \
  python -c "from huggingface_hub import snapshot_download as d; d('black-forest-labs/FLUX.2-klein-4B'); d('Qwen/Qwen-Image-2512')"
```

No Hugging Face token is needed. If one is used for speed, remove it afterwards; none stays on
the machine.

## 3. Render a series

Copy the series file and this script to the machine (for example into `~/zoo-imagery/`), then:

```bash
docker run --rm --gpus all --ipc=host \
  -e ZOO_GEN_COMMIT=$(git rev-parse --short HEAD) \
  -e ZOO_GEN_IMAGE=$(docker inspect --format '{{index .RepoDigests 0}}' zoo-flux 2>/dev/null || docker images --no-trunc -q zoo-flux) \
  -v ~/.cache/huggingface:/root/.cache/huggingface -v ~/zoo-imagery:/work zoo-flux \
  python /work/gen.py --series /work/siebdruck.yaml --model final --seeds 4 --out /work/rounds/1
```

- The series file lists subjects per theme (`themes`); files are named `<theme>--<subject>--<seed>.png`.
- `--model draft` renders with FLUX.2-klein-4B in about 4 s per image, for checking subjects.
- `--model final` renders with Qwen-Image-2512 (50 steps, about 3 min per image on the GB10).
- `--only rail,water/lock-gate` limits the run to themes or subjects; `--reserve` adds the reserve subjects; a `next.txt` in the output directory (written by `zoo site images pick`) selects the subjects of a follow-up round; `--seed-base 1000` gives a second round new seeds. Existing files are skipped.
- `--plan` prints the files a run would write, without touching the GPU.
- The output holds the PNGs and `manifest.json`, which `zoo site images triage` and `pick` read.

Long runs go in a detached script with a log (`nohup rounds/1/run.sh > rounds/1/render.log &`); a full round of about 105 subjects × 4 seeds takes a day.

## 4. Triage, picks and import (feature 019)

On the developer machine, with the round copied back:

```bash
uv sync --extra release --extra images
rsync -a dienstollama@10.123.47.52:zoo-imagery/rounds/1/ ~/zoo-imagery/rounds/1/
uv run zoo site images triage ~/zoo-imagery/rounds/1      # faces, text, style, duplicates → sheet.html
open ~/zoo-imagery/rounds/1/sheet.html                      # the owner picks by number
uv run zoo site images pick ~/zoo-imagery/rounds/1 --dry-run
uv run zoo site images pick ~/zoo-imagery/rounds/1          # records under zoo/site/images/, next.txt
```

`picks.yaml` in the round directory maps `theme/subject` to a number or `none` (optionally
`{number: 2, focal: [0.4, 0.6]}`). The import re-runs every check, copies scene and alt text from
the series, keeps no source PNG, and writes nothing if any pick fails. Single images can still be
imported with `zoo site images add <png> --manifest <manifest.json> --theme … --subject …
[--placement …] [--no-source]`. See
[specs/019-mobility-image-library/contracts/cli.md](../../specs/019-mobility-image-library/contracts/cli.md).

`scripts/imagery/wrap_manifest.py` wraps older, placement-keyed outputs into a round (used once for
the calibration of the style check).
