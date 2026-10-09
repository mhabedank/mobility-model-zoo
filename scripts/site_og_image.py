"""Render the Open Graph image of the zoo website (feature 008) with Playwright.

Usage: uv run --group site-check python scripts/site_og_image.py

Writes src/mobility_model_zoo/site/static/img/og.png (1200 x 630): mark, wordmark and tagline on
the light page background, with the self-hosted fonts. Rerun after a change to the mark or the
tagline in zoo/site.yaml.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "mobility_model_zoo" / "site" / "static"


def main() -> None:
    site = yaml.safe_load((ROOT / "zoo" / "site.yaml").read_text(encoding="utf-8"))
    mark = (STATIC / "img" / "mark.svg").read_text(encoding="utf-8")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{(STATIC / "css" / "tokens.css").as_uri()}">
<style>
html, body {{ margin: 0; width: 1200px; height: 630px; background: #F7F8FC; color: #0E1330;
  font-family: "Figtree", sans-serif; }}
body {{ display: flex; flex-direction: column; justify-content: center; gap: 36px; padding: 0 96px;
  box-sizing: border-box; }}
.brand {{ display: flex; align-items: center; gap: 24px; font-size: 44px; font-weight: 700; }}
.brand svg {{ width: 96px; height: 96px; border-radius: 16px; }}
h1 {{ margin: 0; font-size: 68px; line-height: 1.08; letter-spacing: -.025em; max-width: 960px; }}
.bar {{ width: 120px; height: 10px; border-radius: 5px; background: #6FFFC8; }}
</style></head><body>
<div class="brand">{mark}<span>{site["title"]}</span></div>
<h1>{site["tagline"]}</h1>
<div class="bar"></div>
</body></html>"""
    page_file = STATIC / "img" / "_og.html"
    page_file.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1200, "height": 630})
            page.goto(page_file.as_uri())
            page.wait_for_timeout(300)
            page.screenshot(path=str(STATIC / "img" / "og.png"))
            browser.close()
    finally:
        page_file.unlink()
    print(f"wrote {STATIC / 'img' / 'og.png'}")


if __name__ == "__main__":
    main()
