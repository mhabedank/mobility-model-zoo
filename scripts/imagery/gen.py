"""Render website imagery from a series file (features 016 and 019, contracts/cli.md "Generator").

Runs inside the `zoo-flux` container on the DGX Spark (see README.md). Reads a series file
(`zoo/site/images/series/<name>.yaml`: style, negative, draft and final model, and `themes`:
theme id → subjects with id, prompt, aspect), writes `<out>/<theme>--<subject>--<seed>.png` and
`<out>/manifest.json` with one entry per image: the exact recipe `zoo site images pick` copies
into the image record. Existing files are skipped, so an interrupted run can be resumed.

Seeds: `seed_base + (97 * crc32("theme/subject")) % 1_000_000 + s`, so a subject keeps its seeds
across runs and no two subjects share one; a second round uses `--seed-base 1000`.
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
import zlib
from pathlib import Path

SIZES = {"16:9": (1344, 768), "3:2": (1200, 800)}


def load_series(path: Path) -> dict:
    import yaml

    series = yaml.safe_load(path.read_text(encoding="utf-8"))
    series["style"] = " ".join(series["style"].split())
    series["negative"] = " ".join(series.get("negative", "").split())
    return series


def subjects(series: dict) -> list[dict]:
    """Every subject as {key, theme, id, prompt, aspect, reserve} in series order."""
    out = []
    for theme, lst in (series.get("themes") or {}).items():
        for s in lst or []:
            out.append(
                {
                    "key": f"{theme}/{s['id']}",
                    "theme": theme,
                    "id": s["id"],
                    "prompt": s["prompt"],
                    "aspect": s.get("aspect", "3:2"),
                    "reserve": bool(s.get("reserve")),
                }
            )
    return out


def seed_for(key: str, seed_base: int, s: int) -> int:
    return seed_base + (97 * zlib.crc32(key.encode("utf-8"))) % 1_000_000 + s


def selected(subs: list[dict], only: set[str], reserve: bool) -> list[dict]:
    """`only` holds themes or theme/subject keys; empty means every non-reserve subject."""
    out = []
    for s in subs:
        if only and s["theme"] not in only and s["key"] not in only:
            continue
        if s["reserve"] and not reserve and s["key"] not in only:
            continue
        out.append(s)
    return out


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


def plan(series: dict, a) -> list[dict]:
    """The (subject, seed, file name) list of a run; separated from rendering for tests."""
    only = {p.strip() for p in a.only.split(",") if p.strip()}
    next_file = a.out / "next.txt"
    if not only and next_file.exists():
        only = {ln.strip() for ln in next_file.read_text(encoding="utf-8").splitlines() if ln.strip()}
    jobs = []
    for s in selected(subjects(series), only, a.reserve):
        for i in range(a.seeds):
            seed = seed_for(s["key"], a.seed_base, i)
            jobs.append({**s, "seed": seed, "file": f"{s['theme']}--{s['id']}--{seed}.png"})
    return jobs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument(
        "--series", required=True, type=Path, help="series file (zoo/site/images/series/<name>.yaml)"
    )
    ap.add_argument("--model", default="final", choices=("draft", "final"))
    ap.add_argument("--seeds", type=int, default=1, help="seeds per subject")
    ap.add_argument("--seed-base", type=int, default=0, help="added to every seed (round 2: 1000)")
    ap.add_argument("--steps", type=int, default=0, help="0 = the model's default from the series file")
    ap.add_argument("--only", default="", help="comma-separated themes or theme/subject keys")
    ap.add_argument("--reserve", action="store_true", help="include subjects marked reserve")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--plan", action="store_true", help="print the jobs and exit (no GPU)")
    a = ap.parse_args(argv)

    series = load_series(a.series)
    model = series["models"][a.model]
    steps = a.steps or model["steps"]
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    jobs = plan(series, a)
    if a.plan:
        for j in jobs:
            print(j["file"])
        return 0

    import torch

    manifest_path = out / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {"series": series["name"], "model": model["id"], "images": []}
    )
    pipe, revision = build_pipeline(model)
    for j in jobs:
        if (out / j["file"]).exists():
            continue
        w, h = SIZES[j["aspect"]]
        prompt = f"{j['prompt']}, {series['style']}"
        kw = dict(
            prompt=prompt,
            num_inference_steps=steps,
            width=w,
            height=h,
            generator=torch.Generator("cuda").manual_seed(j["seed"]),
        )
        if "true_cfg_scale" in model:
            kw.update(true_cfg_scale=model["true_cfg_scale"], negative_prompt=series["negative"])
            guidance = model["true_cfg_scale"]
        else:
            kw["guidance_scale"] = model["guidance"]
            guidance = model["guidance"]
        t0 = time.time()
        image = pipe(**kw).images[0]
        image.save(out / j["file"])
        manifest["images"].append(
            {
                "file": j["file"],
                "theme": j["theme"],
                "subject": j["id"],
                "aspect": j["aspect"],
                "seed_base": a.seed_base,
                "prompt": prompt,
                "negative_prompt": series["negative"] if "true_cfg_scale" in model else "",
                "seed": j["seed"],
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
        manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{j['file']} {time.time() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
