#!/usr/bin/env python3
"""Render 4:5 diagram cards for the field notes: headline, a diagram drawn for phone size,
what the model does now, and a band of the note's lead image at the bottom.

    uv run --group site-check python drafts/linkedin/make-diagram-cards.py [slug ...]

Writes drafts/linkedin/<slug>-diagram-linkedin.png at 2400 x 3000 px. The diagrams are
simplified versions of the ones in zoo/notes/diagrams/, with type large enough to read in
a phone feed. Colours are the night print of the site (tokens.css, dark).
"""

from __future__ import annotations

import pathlib
import sys

import yaml

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
FONT_IN_REPO = ROOT / "src/mobility_model_zoo/site/static/fonts/Archivo-variable-latin.woff2"
FONT_LOCAL = HERE / "Archivo-variable-latin.woff2"

W, H = 1200, 1500


def arrow_h(x1: int, x2: int, y: int, dashed: bool = False) -> str:
    colour = "var(--mark)" if dashed else "var(--line)"
    dash = ' stroke-dasharray="12 9"' if dashed else ""
    return (
        f'<path d="M {x1} {y} L {x2} {y}" stroke="{colour}" stroke-width="3"{dash}/>'
        f'<path d="M {x2 - 11} {y - 9} L {x2} {y} L {x2 - 11} {y + 9}" stroke="{colour}" stroke-width="3"/>'
    )


def arrow_up(x: int, y1: int, y2: int) -> str:
    return (
        f'<path d="M {x} {y1} L {x} {y2}" stroke="var(--line)" stroke-width="3"/>'
        f'<path d="M {x - 9} {y2 + 11} L {x} {y2} L {x + 9} {y2 + 11}" stroke="var(--line)" stroke-width="3"/>'
    )


def node(x: int, y: int, kind: str = "plain") -> str:
    fill = {"plain": "var(--bg)", "felt": "var(--mark)", "cause": "var(--bg)"}[kind]
    stroke = "var(--mark)" if kind == "cause" else "var(--text)"
    width = 5 if kind == "cause" else 3
    return f'<circle cx="{x}" cy="{y}" r="16" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


def text(x, y, s, size=28, anchor="middle", colour="var(--muted)", weight=400) -> str:
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{colour}" '
        f'font-weight="{weight}">{s}</text>'
    )


def pill(x: int, y: int, w: int, label: str, colour: str) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="44" rx="22" fill="{colour}"/>'
        + text(x + w / 2, y + 30, label, 22, colour="var(--bg)", weight=700)
    )


def part3() -> tuple[str, int]:
    g = [text(0, 36, "Told in one text", 30, "start", "var(--text)", 700),
         pill(878, 6, 170, "STORED", "var(--text)")]
    xs = [130, 524, 918]
    g += [arrow_h(152, 500, 120), arrow_h(546, 894, 120)]
    g += [text(326, 102, "then", 24), text(720, 102, "two stops later", 24)]
    for x, label in zip(xs, ["Buy at the machine", "Get on", "Wrong zone"]):
        g += [node(x, 120), text(x, 174, label)]
    g.append(text(524, 236, "“…got on, and only at the second stop realised it was the wrong zone.”",
                  25, colour="var(--text)"))
    o = 310
    g += [text(0, o + 36, "Assembled across four texts", 30, "start", "var(--text)", 700),
          pill(838, o + 6, 210, "HYPOTHESIS", "var(--mark)")]
    xs = [80, 376, 672, 968]
    for a, b in zip(xs, xs[1:]):
        g += [arrow_h(a + 22, b - 22, o + 130, dashed=True),
              text((a + b) / 2, o + 116, "?", 32, colour="var(--mark)", weight=700)]
    for x, tag, label in zip(xs, "ABCD", ["App", "Queue", "Platform", "Connection"]):
        g += [text(x, o + 92, f"text {tag}", 22), node(x, o + 130), text(x, o + 184, label)]
    g.append(text(524, o + 246, "Every step has a quote. The order between them has none.", 25))
    return "".join(g), o + 262


def part2() -> tuple[str, int]:
    tx, ox = 360, 700
    g = [text(tx, 34, "Traveller", 30, colour="var(--text)", weight=700),
         text(ox, 34, "Operator", 30, colour="var(--text)", weight=700)]
    g += [arrow_up(tx, 452, 130), text(tx + 16, 210, "in order to", 22, "start")]
    g += [arrow_up(ox, 382, 100), text(ox - 16, 172, "in order to", 22, "end")]
    for y, label in [(110, "Live without a car"), (290, "Get to work on time")]:
        g += [node(tx, y), text(tx - 30, y + 10, label, 28, "end")]
    g += [node(tx, 470, "felt"),
          text(tx - 30, 480, "Right ticket, now", 28, "end", "var(--text)", 700),
          text(tx - 30, 518, "felt here", 26, "end", "var(--mark)", 700)]
    for y, label in [(80, "Pay for the network"), (400, "Staff the counter")]:
        g += [node(ox, y), text(ox + 30, y + 10, label, 28, "start")]
    g += [node(ox, 240, "cause"),
          text(ox + 30, 250, "Set the fare zones", 28, "start", "var(--text)", 700),
          text(ox + 30, 288, "caused here", 26, "start", "var(--mark)", 700)]
    g.append('<path d="M 684 250 L 378 462" stroke="var(--mark)" stroke-width="3" '
             'stroke-dasharray="12 9"/>')
    g.append(text(524, 586, "Complaints are written at the bottom of one chain.", 25))
    g.append(text(524, 622, "The cause sits in the middle of another.", 25))
    return "".join(g), 640


def part1() -> tuple[str, int]:
    rows = [
        ("Drawn as the traveller’s map", ["Plan", "Walk in", "Counter", "Board"],
         "employee and operator: one box"),
        ("Drawn as the employee’s map", ["Shift", "Queue", "This customer", "Next"],
         "traveller: “a customer”"),
        ("Drawn as the operator’s map", ["Budget", "Staffing", "This counter", "Review"],
         "both others: a number"),
    ]
    xs = [70, 370, 670, 970]
    g = []
    for i, (title, labels, note) in enumerate(rows):
        o = i * 200
        g += [text(0, o + 34, title, 30, "start", "var(--text)", 700),
              f'<path d="M 40 {o + 90} L 1008 {o + 90}" stroke="var(--line)" stroke-width="3"/>']
        for j, (x, label) in enumerate(zip(xs, labels)):
            hot = j == 2
            g += [node(x, o + 90, "felt" if hot else "plain"),
                  text(x, o + 140, label, 27, colour="var(--text)" if hot else "var(--muted)",
                       weight=700 if hot else 400)]
        g.append(text(670, o + 176, note, 23, colour="var(--mark)"))
    return "".join(g), 590


CARDS = {
    "whose-journey": dict(
        image="infrastructure-platform-canopy",
        title="Whose journey<em>?</em>",
        sub="One ticket counter, three maps. Each one deletes the other two.",
        draw=part1,
        now="My model now looks for two actors where their paths cross, not one actor per complaint.",
    ),
    "how-big-is-the-question": dict(
        image="infrastructure-junction-above",
        title="Felt here. Caused <em>there</em>.",
        sub="Why a model trained on complaints finds the pain, but rarely the cause.",
        draw=part2,
        now="My model now stores “in order to” links with a quote, not strategic or tactical labels.",
    ),
    "what-follows-what": dict(
        image="water-lock-gate",
        title="What follows what<em>?</em>",
        sub="Most texts describe one moment. The order between them is usually mine.",
        draw=part3,
        now="My model now stores an order only when one text tells it. The rest is a hypothesis.",
    ),
}

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
:root{{--bg:#041C33;--text:#EFF2F0;--muted:#A3B5AD;--line:#6C928C;--mark:#ED9B20}}
@font-face{{font-family:Archivo;src:url("{font}") format("woff2");font-weight:400 800;font-stretch:78% 100%}}
*{{box-sizing:border-box;margin:0}}
body{{width:{w}px;height:{h}px;background:var(--bg);font-family:Archivo,sans-serif;position:relative;
  overflow:hidden;color:var(--text)}}
.main{{position:absolute;left:76px;right:76px;top:70px}}
.eyebrow{{font-size:22px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-stretch:92%}}
h1{{font-size:88px;line-height:1;letter-spacing:-.025em;font-weight:700;font-stretch:80%;margin-top:22px}}
h1 em{{font-style:normal;color:var(--mark)}}
.sub{{font-size:32px;line-height:1.3;color:var(--muted);margin-top:18px;max-width:30ch;font-stretch:92%}}
svg{{display:block;margin-top:56px;font-family:Archivo,sans-serif;font-stretch:92%}}
.now{{margin-top:44px}}
.now b{{display:block;font-size:21px;letter-spacing:.09em;text-transform:uppercase;color:var(--mark);
  font-weight:700;font-stretch:92%}}
.now p{{font-size:33px;line-height:1.28;margin-top:10px;font-stretch:92%;max-width:34ch}}
.band{{position:absolute;left:0;right:0;bottom:0;height:250px}}
.band img{{width:100%;height:100%;object-fit:cover;object-position:{focal}}}
.band:before{{content:"";position:absolute;inset:0;background:linear-gradient(to bottom,
  rgba(4,28,51,1) 0%,rgba(4,28,51,.2) 40%,rgba(4,28,51,.35) 60%,rgba(4,28,51,.88) 80%,rgba(4,28,51,1) 100%)}}
.foot{{position:absolute;left:76px;right:76px;bottom:40px;display:flex;justify-content:space-between;
  font-size:22px;color:var(--text);font-stretch:92%}}
.foot b{{color:var(--mark)}}
</style></head><body>
<div class="main">
<div class="eyebrow">Building a model that reads customer journeys from text</div>
<h1>{title}</h1><p class="sub">{sub}</p>
<svg xmlns="http://www.w3.org/2000/svg" width="1048" height="{dh}" viewBox="0 0 1048 {dh}">
<g fill="none" stroke-linecap="round">{diagram}</g></svg>
<div class="now"><b>What the model does now</b><p>{now}</p></div>
</div>
<div class="band"><img src="{image}"></div>
<div class="foot"><span>Field note · open models, open notes</span><b>mobility model zoo</b></div>
</body></html>"""


def main(slugs: list[str]) -> int:
    from playwright.sync_api import sync_playwright

    font = (FONT_IN_REPO if FONT_IN_REPO.is_file() else FONT_LOCAL).as_uri()
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        tab = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for slug in slugs or list(CARDS):
            card = CARDS[slug]
            folder = ROOT / "zoo/site/images" / card["image"]
            record = yaml.safe_load((folder / "image.yaml").read_text(encoding="utf-8"))
            fx, fy = record["focal_point"]
            diagram, dh = card["draw"]()
            html = PAGE.format(
                font=font, w=W, h=H, title=card["title"], sub=card["sub"], now=card["now"],
                diagram=diagram, dh=dh, focal=f"{round(fx * 100)}% {round(fy * 100)}%",
                image=(folder / record["derivatives"]["1600"]["file"]).as_uri(),
            )
            page = HERE / ".diagram-card.html"
            page.write_text(html, encoding="utf-8")
            tab.goto(page.as_uri(), wait_until="networkidle")
            out = HERE / f"{slug}-diagram-linkedin.png"
            tab.screenshot(path=str(out))
            page.unlink()
            print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} kB)")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
