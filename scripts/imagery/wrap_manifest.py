"""Wrap earlier generator outputs (feature 016 layout: placement-keyed manifests) into one
round directory that `zoo site images triage` understands (feature 019, task T024).

    python scripts/imagery/wrap_manifest.py --out ~/zoo-imagery/calib/round \
        approved-qwen=~/zoo-imagery/calib/approved-qwen rejected-night=~/zoo-imagery/calib/rejected-night

Each `label=dir` argument becomes a theme `calib`, subject `<label>-<placement>`; files are
hard-linked (or copied) into `--out` with the label as a prefix, so nothing is renamed in place.
Missing recipe fields of the old manifests are filled with placeholders that the schema accepts
(the calibration never imports a record).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--series", default="siebdruck")
    ap.add_argument("sets", nargs="+", help="label=directory")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    images = []
    for item in a.sets:
        label, _, d = item.partition("=")
        src = Path(os.path.expanduser(d))
        manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
        for im in manifest.get("images", []):
            placement = im.get("placement") or im.get("subject") or "x"
            subject = f"{label}-{placement}".replace(":", "-")
            name = f"calib--{subject}--{im['seed']}.png"
            target = a.out / name
            if not target.exists():
                try:
                    os.link(src / im["file"], target)
                except OSError:
                    shutil.copyfile(src / im["file"], target)
            images.append(
                {
                    "file": name,
                    "theme": "calib",
                    "subject": subject,
                    "aspect": "16:9" if im["width"] * 9 == im["height"] * 16 else "3:2",
                    "seed_base": 0,
                    "prompt": im["prompt"],
                    "negative_prompt": im.get("negative_prompt", ""),
                    "seed": im["seed"],
                    "steps": im.get("steps", 1),
                    "guidance": im.get("guidance", 1.0),
                    "width": im["width"],
                    "height": im["height"],
                    "model": im.get("model") or manifest.get("model") or "x/y",
                    "revision": im.get("revision") or "0" * 40,
                    "model_licence": im.get("model_licence", "Apache-2.0"),
                    "model_card": im.get("model_card", "https://huggingface.co/x"),
                    "pipeline": im.get("pipeline", "x"),
                    "series": a.series,
                    "generated": im.get("generated", "2026-10-13"),
                    "hardware": im.get("hardware", "dgx-spark"),
                    "generator": im.get("generator") or {"commit": "unversioned", "image_digest": ""},
                    "set": label,
                }
            )
    (a.out / "manifest.json").write_text(
        json.dumps({"series": a.series, "model": "mixed", "images": images}, indent=1),
        encoding="utf-8",
    )
    print(f"{len(images)} candidates in {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
