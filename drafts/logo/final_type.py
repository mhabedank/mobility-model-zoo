"""Head to head: Archivo at two widths against Instrument Sans, as a real page head."""
import pathlib

ROOT = pathlib.Path("/Users/m.habedank/Projects/private/mobility-llm")
FONTS = ROOT / "drafts/fonts"
OUT = ROOT / "drafts/logo"
MARK = ("M260.5 244.3 L243.1 345 L296.9 345 L328.9 160 L266 160 L216.3 214.2 L183.1 160 "
        "L125.1 160 L93.1 345 L146.9 345 L166.1 233.8 L207.7 301.8 Z")
PAPER, INK, ACCENT, MUTED, BORDER = "#FAF3E4", "#062544", "#CA6A0A", "#4B5D54", "#D8CDB4"

PANELS = [
    ("A  Archivo", "AR", "normal", "Eine Breite f&uuml;r alles, Schlagzeile wie Flie&szlig;text", 90),
    ("B  Archivo, schmale Schlagzeile", "AR", "narrow",
     "Flie&szlig;text normal, Schlagzeile &uuml;ber die Breitenachse auf 78&nbsp;% gestaucht", 90),
    ("C  Instrument Sans", "IS", "normal", "Eine Breite, etwas schmaler gezeichnet, n&uuml;chterner", 30),
]

panels = []
for title, fam, mode, note, kb in PANELS:
    narrow = "font-stretch:78%;" if mode == "narrow" else ""
    panels.append(f"""
    <section class="panel" style="font-family:{fam},sans-serif">
      <header><h2>{title}</h2><span>{note} &middot; {kb}&nbsp;KB</span></header>
      <div class="bar">
        <span class="brand"><svg viewBox="0 0 512 512" width="30" height="30">
          <rect width="512" height="512" fill="{INK}"/><path d="{MARK}" fill="{PAPER}"/>
          <circle cx="376" cy="301" r="44" fill="{ACCENT}"/></svg><b>Mobility Model Zoo</b></span>
        <nav>Models Roadmap Topics Principles Resources</nav>
      </div>
      <p class="eyebrow">Vision</p>
      <h3 style="{narrow}">Safer, more affordable and better mobility through AI.</h3>
      <p class="body">We build machine learning models for real mobility problems and make them
        available to everyone, for research and, where their licences allow it, for commercial use.</p>
      <p class="row"><span class="btn">Quickstart</span><span class="chip">experimental &middot; v0.1.0</span></p>
    </section>""")

html = f"""<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:AR;src:url("{(FONTS / 'ArchivoVar.woff2').as_uri()}") format("woff2");
  font-weight:100 900;font-stretch:62% 125%;}}
@font-face{{font-family:IS;src:url("{(FONTS / 'InstrumentSans.woff2').as_uri()}") format("woff2");
  font-weight:100 900;}}
  body {{ margin:0; padding:26px; background:{PAPER}; color:{INK}; font-family:-apple-system,sans-serif; }}
  h1 {{ font-size:18px; margin:0 0 4px; }}
  p.l {{ font-size:13px; color:{MUTED}; margin:0 0 20px; }}
  .panel {{ background:#FFFDF7; border:1px solid {BORDER}; padding:0 0 24px; margin-bottom:20px; }}
  .panel header {{ display:flex; align-items:baseline; gap:12px; padding:12px 24px;
    border-bottom:1px solid {BORDER}; font-family:-apple-system,sans-serif; background:{PAPER}; }}
  .panel header h2 {{ font-size:14px; margin:0; }}
  .panel header span {{ font-size:12px; color:{MUTED}; }}
  .bar {{ display:flex; align-items:center; justify-content:space-between; gap:24px;
    padding:10px 24px; border-bottom:1px solid {BORDER}; }}
  .brand {{ display:flex; align-items:center; gap:10px; font-size:18px; font-weight:700; letter-spacing:-.01em; }}
  nav {{ display:flex; gap:20px; font-size:15px; font-weight:500; }}
  .eyebrow {{ font-size:12px; font-weight:650; letter-spacing:.1em; text-transform:uppercase;
    color:{MUTED}; margin:22px 24px 8px; }}
  h3 {{ font-size:46px; line-height:1.06; font-weight:700; letter-spacing:-.025em;
    margin:0 24px 14px; max-width:17ch; }}
  .body {{ font-size:17px; line-height:1.6; margin:0 24px 18px; max-width:60ch; }}
  .row {{ display:flex; align-items:center; gap:14px; margin:0 24px; }}
  .btn {{ background:{INK}; color:{PAPER}; padding:11px 22px; font-weight:650; font-size:15px; }}
  .chip {{ border:1px solid {BORDER}; padding:8px 14px; font-size:14px; }}
</style>
<h1>Letzter Vergleich: Archivo gegen Instrument Sans</h1>
<p class="l">Beide OFL und selbst hostbar. B zeigt, was die Breitenachse kann: dieselbe Schrift,
die Schlagzeile schmaler gesetzt &mdash; ein Kernmerkmal der Plakate der Zeit.</p>
{''.join(panels)}"""
(OUT / "final_type.html").write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1180, "height": 900}, device_scale_factor=2)
    pg.goto((OUT / "final_type.html").as_uri())
    pg.wait_for_timeout(1000)
    pg.screenshot(path=str(OUT / "final_type.png"), full_page=True)
    b.close()
print("ok")
