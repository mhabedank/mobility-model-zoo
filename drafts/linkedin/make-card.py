#!/usr/bin/env python3
"""Render a social card for a field note: a library image above a solid night-print panel.

    uv run --group site-check python drafts/linkedin/make-card.py \
        --image model-pace-cnn-stairs \
        --eyebrow 'Mapping the mobility experience' \
        --title 'Whose journey<em>?</em>' \
        --sub 'Three people in the same two square metres. Three different problems.' \
        --foot 'Field note · Part 1 of 5' \
        --out drafts/linkedin/whose-journey-linkedin.png

`--format portrait` (the default) draws 1080 x 1350, the most feed height a picture gets on a
phone; `--format square` draws 1200 x 1200 for a post that is also shared elsewhere. The output
is twice that, as PNG. `--title` may contain <em>…</em>; that part is set in the warm accent, and
it should be one glyph. The image is a record id under zoo/site/images/; its focal point is read
from the record, so the crop matches the one the website uses. The font comes from the
repository when the screenprint identity is merged, otherwise from the copy next to this script.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
TEMPLATE = HERE / "card-template.html"
FONT_IN_REPO = ROOT / "src/mobility_model_zoo/site/static/fonts/Archivo-variable-latin.woff2"
FONT_LOCAL = HERE / "Archivo-variable-latin.woff2"
# canvas width, height and the height of the picture above the panel
FORMATS = {"portrait": (1080, 1350, 740), "square": (1200, 1200, 640)}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", required=True, help="record id under zoo/site/images/")
    p.add_argument("--title", required=True)
    p.add_argument("--sub", required=True)
    p.add_argument("--eyebrow", default="")
    p.add_argument("--foot", default="Field note")
    p.add_argument("--out", required=True)
    p.add_argument("--format", choices=sorted(FORMATS), default="portrait")
    a = p.parse_args()
    width, height, picture_height = FORMATS[a.format]

    folder = ROOT / "zoo/site/images" / a.image
    record = yaml.safe_load((folder / "image.yaml").read_text(encoding="utf-8"))
    fx, fy = record["focal_point"]
    picture = folder / record["derivatives"]["1600"]["file"]
    font = FONT_IN_REPO if FONT_IN_REPO.is_file() else FONT_LOCAL

    html = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("{{IMAGE}}", picture.as_uri())
        .replace("{{FONT}}", font.as_uri())
        .replace("{{FOCAL}}", f"{round(fx * 100)}% {round(fy * 100)}%")
        .replace("{{W}}", str(width))
        .replace("{{H}}", str(height))
        .replace("{{PIC}}", str(picture_height))
        .replace("{{EYEBROW}}", a.eyebrow)
        .replace("{{TITLE}}", a.title)
        .replace("{{SUB}}", a.sub)
        .replace("{{FOOT}}", a.foot)
    )
    page = HERE / ".card.html"
    page.write_text(html, encoding="utf-8")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("needs Playwright: uv run --group site-check python …", file=sys.stderr)
        return 1

    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        tab = browser.new_page(
            viewport={"width": width, "height": height}, device_scale_factor=2
        )
        tab.goto(page.as_uri(), wait_until="networkidle")
        tab.screenshot(path=str(out))
        browser.close()
    page.unlink()
    print(f"wrote {out} ({out.stat().st_size // 1024} kB, {width * 2} x {height * 2} px, {a.format})")
    print(f"credit the image as: {record['scene']} (AI-generated, CC0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
