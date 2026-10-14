# Website imagery: rendering on the DGX Spark

The images of the zoo website (feature 016) are generated, never fetched. The recipe of every
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
  python /work/gen.py --series /work/siebdruck.yaml --model final --seeds 4 --out /work/out/siebdruck
```

- `--model draft` renders with FLUX.2-klein-4B in about 4 s per image, for exploring subjects.
- `--model final` renders with Qwen-Image-2512 (50 steps, about 3 min per image on the GB10).
- `--only start-hero,topic:security` limits the run; existing files are skipped.
- The output holds the PNGs and `manifest.json`, which `zoo site images add` reads.

## 4. Import

On the developer machine, with the output copied back:

```bash
uv sync --extra release --extra images
uv run zoo site images add out/siebdruck/start-hero-2-1021.png --manifest out/siebdruck/manifest.json \
  --placement start-hero --focal 0.5,0.55 --scene "Regional train leaving a small station at dawn" \
  --alt "An orange-yellow regional train leaves a small station platform in warm morning light"
```

The import checks the recipe against the series, rejects faces and readable text, writes the
record with three WebP derivatives, and refuses anything that fails. See
[specs/016-emotional-imagery-motifs/contracts/cli.md](../../specs/016-emotional-imagery-motifs/contracts/cli.md).
