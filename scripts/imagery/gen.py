"""Render website imagery from a series file (feature 016, contracts/cli.md "Generator").

Runs inside the `zoo-flux` container on the DGX Spark (see README.md). Reads a series file
(`zoo/site/images/series/<name>.yaml`: style, negative, subjects per placement, draft and final
model), writes `<out>/<placement>-<n>-<seed>.png` and `<out>/manifest.json` with one entry per
image: the exact recipe `zoo site images add` copies into the image record. Existing files are
skipped, so an interrupted run can be resumed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

SIZES = {"16:9": (1344, 768), "3:2": (1200, 800)}


def aspect_of(placement: str) -> str:
    return "16:9" if placement == "start-hero" else "3:2"


def load_series(path: Path) -> dict:
    import yaml

    series = yaml.safe_load(path.read_text(encoding="utf-8"))
    series["style"] = " ".join(series["style"].split())
    series["negative"] = " ".join(series.get("negative", "").split())
    return series


def hardware_class() -> str:
    return (
        "dgx-spark"
        if Path("/proc/driver/nvidia").exists() and platform.machine() == "aarch64"
        else "dev-machine"
    )


def generator_identity() -> dict[str, str]:
    """Commit of this script and the container image digest, passed in by the launcher."""
    return {
        "commit": os.environ.get("ZOO_GEN_COMMIT", "unknown"),
        "image_digest": os.environ.get("ZOO_GEN_IMAGE", "unknown"),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def build_pipeline(model: dict):
    import diffusers
    import torch
    from huggingface_hub import snapshot_download

    local = snapshot_download(model["id"])
    revision = Path(local).name
    pipe = (
        getattr(diffusers, model["pipeline"])
        .from_pretrained(local, torch_dtype=torch.bfloat16)
        .to("cuda")
    )
    return pipe, revision


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument(
        "--series", required=True, type=Path, help="series file (zoo/site/images/series/<name>.yaml)"
    )
    ap.add_argument("--model", default="final", choices=("draft", "final"))
    ap.add_argument("--seeds", type=int, default=1, help="seeds per subject")
    ap.add_argument("--steps", type=int, default=0, help="0 = the model's default from the series file")
    ap.add_argument("--only", default="", help="comma-separated placements")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)

    import torch

    series = load_series(a.series)
    model = series["models"][a.model]
    steps = a.steps or model["steps"]
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"series": series["name"], "model": model["id"], "images": []}
    )
    pipe, revision = build_pipeline(model)
    only = {p for p in a.only.split(",") if p}
    for placement, prompts in series["subjects"].items():
        if only and placement not in only:
            continue
        w, h = SIZES[aspect_of(placement)]
        for i, subject in enumerate(prompts, 1):
            for s in range(a.seeds):
                seed = 1000 + i * 10 + s
                name = f"{placement}-{i}-{seed}.png"
                if (out / name).exists():
                    continue
                prompt = f"{subject}, {series['style']}"
                kw = dict(
                    prompt=prompt,
                    num_inference_steps=steps,
                    width=w,
                    height=h,
                    generator=torch.Generator("cuda").manual_seed(seed),
                )
                if "true_cfg_scale" in model:
                    kw.update(true_cfg_scale=model["true_cfg_scale"], negative_prompt=series["negative"])
                    guidance = model["true_cfg_scale"]
                else:
                    kw["guidance_scale"] = model["guidance"]
                    guidance = model["guidance"]
                t0 = time.time()
                image = pipe(**kw).images[0]
                image.save(out / name)
                manifest["images"].append(
                    {
                        "file": name,
                        "placement": placement,
                        "subject": subject,
                        "prompt": prompt,
                        "negative_prompt": series["negative"] if "true_cfg_scale" in model else "",
                        "seed": seed,
                        "steps": steps,
                        "guidance": guidance,
                        "width": w,
                        "height": h,
                        "model": model["id"],
                        "revision": revision,
                        "model_licence": model["licence"],
                        "model_card": model["card"],
                        "pipeline": model["pipeline"],
                        "series": series["name"],
                        "generated": dt.date.today().isoformat(),
                        "hardware": hardware_class(),
                        "generator": generator_identity(),
                        "seconds": round(time.time() - t0, 1),
                    }
                )
                manifest_path.write_text(
                    json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8"
                )
                print(f"{name} {time.time() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
