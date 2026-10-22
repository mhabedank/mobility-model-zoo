"""Measure, do not squint: does Archivo's width axis actually change the set width?"""
import pathlib

ROOT = pathlib.Path("/Users/m.habedank/Projects/private/mobility-llm")
FONTS = ROOT / "drafts/fonts"
URL = (FONTS / "ArchivoVar.woff2").as_uri()

html = f"""<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:AR;src:url("{URL}") format("woff2");font-weight:100 900;font-stretch:62% 125%;}}
span {{ font-family:AR; font-size:46px; font-weight:700; white-space:nowrap; }}
</style>
<span id="a">affordable and better</span><br>
<span id="b" style="font-stretch:78%">affordable and better</span><br>
<span id="c" style="font-variation-settings:'wdth' 78">affordable and better</span><br>
<span id="d" style="font-variation-settings:'wdth' 125">affordable and better</span>
"""
page = ROOT / "drafts/logo/measure.html"
page.write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page()
    pg.goto(page.as_uri())
    pg.wait_for_timeout(900)
    for i, label in [("a", "normal"), ("b", "font-stretch:78%"), ("c", "wdth 78"), ("d", "wdth 125")]:
        w = pg.evaluate(f"document.getElementById('{i}').getBoundingClientRect().width")
        print(f"{label:20} {w:7.1f} px")
    b.close()
