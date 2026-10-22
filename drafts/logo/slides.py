"""The LinkedIn explainer graphics in both palettes.

Same rebuild on both sides, same typeface, so the comparison shows the palette and nothing else.
In the posters the one warm accent marks the subject; in these graphics the neon marks the number
that matters. That is the same job, which is what makes the swap a translation and not a repaint.
"""
import base64
import pathlib

ROOT = pathlib.Path("/Users/m.habedank/Projects/private/mobility-llm")
WT = ROOT / ".claude/worktrees/023-screenprint-mark"
OUT = ROOT / "drafts/logo"
FONTS = WT / "src/mobility_model_zoo/site/static/fonts"
MARK = ("M260.5 244.3 L243.1 345 L296.9 345 L328.9 160 L266 160 L216.3 214.2 L183.1 160 "
        "L125.1 160 L93.1 345 L146.9 345 L166.1 233.8 L207.7 301.8 Z")
train = base64.b64encode(
    (WT / "zoo/site/images/model-scout-large-window/model-scout-large-window-960.webp").read_bytes()
).decode() if (WT / "zoo/site/images/model-scout-large-window/model-scout-large-window-960.webp").exists() else None
if train is None:
    train = base64.b64encode(
        (WT / "zoo/site/images/hero-train-dawn/hero-train-dawn-960.webp").read_bytes()
    ).decode()

TODAY = dict(
    name="heute &mdash; Indigo und Neonmint",
    bg="#0A0F2E", panel="#111846", border="#2F3C86", ink="#EEF1FF", muted="#A7B1DE",
    struct="#8B9BE8", block="#8B9BE8", hot="#6FFFC8", warm="#F0A868", markbg="#1B3BD8", markink="#FFFFFF",
    markdot="#6FFFC8", onhot="#0A0F2E", job="#8B9BE8", pain="#F0A868", gain="#6FFFC8",
)
POSTER = dict(
    name="Plakat &mdash; Navy, Creme, ein warmes Orange",
    bg="#062544", panel="#0B3050", border="#17496F", ink="#FBEED0", muted="#A5DBC6",
    struct="#A5DBC6", block="#5F8E8A", hot="#ED9B20", warm="#CA6A0A", markbg="#FBEED0", markink="#062544",
    markdot="#ED9B20", onhot="#062544", job="#86B6D8", pain="#ED9B20", gain="#9BD4A6",
)

LAYERS = [
    ("input", "window", "128&times;9", "1,152", "&ndash;", 120, "block"),
    ("conv", "k5 &middot; 16", "128&times;16", "2,048", "864", 150, "hot"),
    ("max-pool", "&divide;2", "64&times;16", "1,024", "&ndash;", 74, "block"),
    ("conv", "k5 &middot; 32", "64&times;32", "2,048", "2,848", 104, "hot"),
    ("max-pool", "&divide;2", "32&times;32", "1,024", "&ndash;", 62, "block"),
    ("conv", "k3 &middot; 32", "32&times;32", "1,024", "3,360", 62, "hot"),
    ("avg-pool", "over time", "1&times;32", "32", "&ndash;", 20, "block"),
    ("dense", "&rarr; 6", "1&times;6", "6", "246", 16, "warm"),
]


def mark(p, size=40):
    return (f'<svg viewBox="0 0 512 512" width="{size}" height="{size}">'
            f'<rect width="512" height="512" fill="{p["markbg"]}"/>'
            f'<path d="{MARK}" fill="{p["markink"]}"/>'
            f'<circle cx="376" cy="301" r="44" fill="{p["markdot"]}"/></svg>')


def slide_one(p):
    cols = "".join(
        f'<div class="lcol"><span class="lname">{n}</span><span class="lsub">{s}</span>'
        f'<span class="lbar" style="height:{h * 1.5}px;background:{p[c]}"></span></div>'
        for n, s, _, _, _, h, c in LAYERS)
    rows = ""
    for label, idx in (("shape", 2), ("RAM, bytes", 3), ("flash, bytes", 4)):
        cells = "".join(
            f'<td class="{"hot" if c == "hot" and idx == 3 else ""}">{L[idx]}</td>'
            for L in LAYERS for c in [L[6]])
        rows += f"<tr><th>{label}</th>{cells}</tr>"
    return f"""
    <div class="slide" style="background:{p['bg']}">
      <p class="eyebrow">The problem</p>
      <h2>What is this person doing right now?</h2>
      <p class="lede">Walking, taking the stairs, sitting or lying: pace-cnn tells it from
        <b>2.56 seconds of a waist-worn motion sensor</b>, and the model runs
        <b>on the microcontroller itself</b>.</p>
      <div class="flow">
        <div class="box"><b>Motion sensor</b><span>accelerometer + gyroscope<br>at the waist, 9 channels</span></div>
        <span class="arr">&rarr;</span>
        <div class="box hotbox"><b class="hot">pace-cnn</b><span>int8 CNN on an ESP32<br>55 ms per window</span></div>
        <span class="arr">&rarr;</span>
        <div class="box"><b>One of 6 activities</b>
          <span class="pills">{"".join(f"<i>{a}</i>" for a in ("walk", "up", "down", "sit", "stand", "lie"))}</span></div>
      </div>
      <p class="huge"><span class="hot">5.2 KB</span> <em>of RAM</em>
        <span class="aside">(yes, kilobytes:<br>5,254 bytes on a real ESP32)</span></p>
      <p class="cap"><b>The model:</b> <code>a 1D CNN, three int8 conv layers &middot; block area = bytes</code></p>
      <div class="layers">{cols}</div>
      <table class="tbl">{rows}</table>
      <p class="cap2"><b>Only two layers sit in RAM at once</b>
        <code>&middot; two buffers the size of the largest layer</code></p>
      <div class="eq">
        <span class="eqbox"><b>2,048</b><i>read buffer</i></span><span class="op">+</span>
        <span class="eqbox"><b>2,048</b><i>write buffer</i></span><span class="op">+</span>
        <span class="eqbox"><b>1,152</b><i>input window</i></span><span class="op">+</span>
        <span class="eqbox"><b>6</b><i>scores</i></span><span class="op">=</span>
        <span class="eqbox solid"><b>5,254 B</b><i>of RAM</i></span>
      </div>
      <div class="stats">
        <div><b>0.92</b><span>macro-F1 on 9 people it never saw</span></div>
        <div><b>7.2 KB</b><span>weights, kept in flash</span></div>
        <div><b>bit-exact</b><span>same outputs on the board as on the host</span></div>
      </div>
      <p class="url">mhabedank.github.io/mobility-model-zoo</p>
    </div>"""


def slide_two(p):
    quotes = [
        ("job", "job", "&ldquo;Develop strategies for scaling up EV Charging infrastructure&rdquo;", "p. 74"),
        ("pain", "pain", "&ldquo;The victims largely belong to the young, productive age group.&rdquo;", "p. 84"),
        ("gain", "gain", "&ldquo;&hellip;significantly reducing emissions and improving air quality.&rdquo;", "p. 73"),
    ]
    rows = "".join(
        f'<div class="q"><span class="qc" style="border-color:{p[k]};color:{p[k]}">{lab}</span>'
        f'<span class="qt">{t}</span><span class="qp">{pg}</span></div>'
        for k, lab, t, pg in quotes)
    return f"""
    <div class="slide" style="background:{p['bg']}">
      <div class="topbar">{mark(p, 34)}<b>Mobility Model Zoo</b>
        <span class="chip">scout-large &middot; experimental</span></div>
      <img class="shot" src="data:image/webp;base64,{train}">
      <p class="eyebrow2">Not every text task needs an LLM</p>
      <div class="thru">
        <div><b class="big">173</b><span>pages of text</span><i>80,231 tokens</i></div>
        <div class="arrowbox"><b class="hot">5.8 s</b><span class="line"></span><i>14k tokens/s</i></div>
        <div class="right"><b class="big hot">170</b><span>jobs, pains &amp; gains</span><i>each a verbatim quote</i></div>
      </div>
      {rows}
      <p class="url">mhabedank.github.io/mobility-model-zoo</p>
    </div>"""


def css(p, tag):
    return f"""
  .{tag} .slide {{ width:720px; padding:30px 32px 26px; box-sizing:border-box; color:{p['ink']};
     font-family:Fig,sans-serif; }}
  .{tag} .eyebrow {{ font-size:12px; letter-spacing:.14em; text-transform:uppercase;
     color:{p['muted']}; margin:0 0 6px; font-weight:600; }}
  .{tag} h2 {{ font-size:30px; line-height:1.1; margin:0 0 10px; font-weight:800; letter-spacing:-.02em; }}
  .{tag} .lede {{ font-size:14px; line-height:1.5; margin:0 0 18px; color:{p['muted']}; }}
  .{tag} .lede b {{ color:{p['ink']}; }}
  .{tag} .flow {{ display:flex; align-items:center; gap:8px; margin-bottom:22px; }}
  .{tag} .box {{ flex:1; border:1.5px solid {p['border']}; border-radius:9px; padding:9px 11px; }}
  .{tag} .hotbox {{ border-color:{p['hot']}; }}
  .{tag} .box b {{ display:block; font-size:13px; margin-bottom:3px; }}
  .{tag} .box span {{ font-size:10.5px; line-height:1.35; color:{p['muted']}; display:block; }}
  .{tag} .hot {{ color:{p['hot']}; }}
  .{tag} .arr {{ color:{p['muted']}; font-size:15px; }}
  .{tag} .pills i {{ display:inline-block; border:1px solid {p['border']}; border-radius:999px;
     padding:1px 6px; margin:3px 3px 0 0; font-style:normal; font-size:9.5px; color:{p['muted']}; }}
  .{tag} .huge {{ margin:0 0 14px; display:flex; align-items:baseline; gap:8px; }}
  .{tag} .huge .hot {{ font-size:56px; font-weight:800; letter-spacing:-.03em; line-height:1; }}
  .{tag} .huge em {{ font-style:normal; font-size:22px; font-weight:700; }}
  .{tag} .aside {{ margin-left:auto; font-family:Mono; font-size:11px; color:{p['muted']};
     text-align:right; line-height:1.4; }}
  .{tag} .cap, .{tag} .cap2 {{ font-size:12px; margin:0 0 8px; }}
  .{tag} code {{ font-family:Mono; font-size:11.5px; color:{p['muted']}; }}
  .{tag} .layers {{ display:flex; align-items:flex-end; gap:6px; height:200px; margin-bottom:6px; }}
  .{tag} .lcol {{ flex:1; display:flex; flex-direction:column; align-items:center;
     justify-content:flex-end; height:100%; }}
  .{tag} .lname {{ font-size:10.5px; font-weight:700; }}
  .{tag} .lsub {{ font-family:Mono; font-size:9px; color:{p['muted']}; margin-bottom:6px; }}
  .{tag} .lbar {{ width:62%; border-radius:2px; }}
  .{tag} .tbl {{ width:100%; border-collapse:collapse; margin-bottom:14px; }}
  .{tag} .tbl th {{ font-family:Mono; font-size:9.5px; color:{p['muted']}; text-align:left;
     font-weight:400; padding:3px 0; }}
  .{tag} .tbl td {{ font-size:10.5px; font-weight:700; text-align:center;
     border-top:1px solid {p['border']}; padding:3px 0; }}
  .{tag} .tbl td.hot {{ color:{p['hot']}; }}
  .{tag} .eq {{ display:flex; align-items:center; gap:7px; margin-bottom:18px; }}
  .{tag} .eqbox {{ border:1.5px solid {p['border']}; border-radius:8px; padding:6px 10px;
     text-align:center; }}
  .{tag} .eqbox b {{ display:block; font-family:Mono; font-size:15px; }}
  .{tag} .eqbox i {{ font-style:normal; font-size:9px; color:{p['muted']}; }}
  .{tag} .eqbox.solid {{ background:{p['hot']}; border-color:{p['hot']}; }}
  .{tag} .eqbox.solid b, .{tag} .eqbox.solid i {{ color:{p['onhot']}; }}
  .{tag} .op {{ color:{p['muted']}; font-size:13px; }}
  .{tag} .stats {{ display:flex; gap:26px; border-top:1px solid {p['border']}; padding-top:12px; }}
  .{tag} .stats div {{ flex:1; }}
  .{tag} .stats b {{ display:block; font-size:21px; font-weight:800; }}
  .{tag} .stats span {{ font-size:10.5px; color:{p['muted']}; }}
  .{tag} .url {{ font-size:11px; color:{p['muted']}; margin:18px 0 0; }}
  .{tag} .topbar {{ display:flex; align-items:center; gap:10px; margin:-30px -32px 0;
     padding:10px 32px; background:{p['ink']}; color:{p['bg']}; }}
  .{tag} .topbar b {{ font-size:17px; }}
  .{tag} .chip {{ margin-left:auto; border:1px solid {p['bg']}; border-radius:999px;
     padding:3px 11px; font-size:11px; font-weight:600; }}
  .{tag} .shot {{ display:block; width:calc(100% + 64px); margin:0 -32px 18px; }}
  .{tag} .eyebrow2 {{ font-size:12.5px; letter-spacing:.16em; text-transform:uppercase;
     color:{p['muted']}; font-weight:700; margin:0 0 14px; }}
  .{tag} .thru {{ display:flex; align-items:center; gap:18px; margin-bottom:18px; }}
  .{tag} .thru > div {{ flex:1; }}
  .{tag} .thru .right {{ text-align:right; }}
  .{tag} .big {{ font-size:46px; font-weight:800; line-height:1; letter-spacing:-.03em; display:block; }}
  .{tag} .thru span {{ font-size:13px; font-weight:700; display:block; margin-top:4px; }}
  .{tag} .thru i {{ font-style:normal; font-size:11px; color:{p['muted']}; }}
  .{tag} .arrowbox {{ text-align:center; }}
  .{tag} .arrowbox b {{ font-size:22px; font-weight:800; display:block; }}
  .{tag} .line {{ display:block; height:3px; background:{p['hot']}; margin:5px 0; }}
  .{tag} .q {{ display:flex; align-items:center; gap:11px; border:1.5px solid {p['border']};
     border-radius:9px; padding:9px 12px; margin-bottom:7px; background:{p['panel']}; }}
  .{tag} .qc {{ border:1.5px solid; border-radius:999px; padding:2px 10px; font-size:10.5px;
     font-weight:700; flex:none; }}
  .{tag} .qt {{ font-size:12.5px; flex:1; }}
  .{tag} .qp {{ font-family:Mono; font-size:10px; color:{p['muted']}; flex:none; }}
"""


html = f"""<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:Fig;src:url("{(FONTS / 'Figtree-variable-latin.woff2').as_uri()}");font-weight:300 900;}}
@font-face{{font-family:Mono;src:url("{(FONTS / 'JetBrainsMono-variable-latin.woff2').as_uri()}");font-weight:100 800;}}
  body {{ margin:0; padding:22px; background:#E9E7E2; font-family:-apple-system,sans-serif; }}
  h1 {{ font-size:17px; margin:0 0 3px; }}
  p.l {{ font-size:12.5px; color:#5E5E5E; margin:0 0 16px; }}
  .cols {{ display:flex; gap:20px; align-items:flex-start; }}
  .col {{ flex:none; }}
  .col > h3 {{ font-size:13px; margin:0 0 8px; }}
  .slide {{ margin-bottom:16px; }}
{css(TODAY, 'a')}
{css(POSTER, 'b')}
</style>
<h1>Die Erkl&auml;rgrafiken in beiden Paletten</h1>
<p class="l">Gleicher Nachbau, gleiche Schrift (Figtree) auf beiden Seiten &mdash; nur die Farben wechseln.
Neonmint markiert heute die Zahl, auf die es ankommt; rechts tut das Orange dasselbe.</p>
<div class="cols">
  <div class="col a"><h3>{TODAY['name']}</h3>{slide_one(TODAY)}{slide_two(TODAY)}</div>
  <div class="col b"><h3>{POSTER['name']}</h3>{slide_one(POSTER)}{slide_two(POSTER)}</div>
</div>"""
(OUT / "slides.html").write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1560, "height": 1000}, device_scale_factor=1.6)
    pg.goto((OUT / "slides.html").as_uri())
    pg.wait_for_timeout(1200)
    pg.screenshot(path=str(OUT / "slides.png"), full_page=True)
    b.close()
print("ok")
