"""What actually stops a scroll: four share-card treatments in a mocked LinkedIn feed."""
import base64
import pathlib

ROOT = pathlib.Path("/Users/m.habedank/Projects/private/mobility-llm")
WT = ROOT / ".claude/worktrees/023-screenprint-mark"
OUT = ROOT / "drafts/logo"
MARK = ("M260.5 244.3 L243.1 345 L296.9 345 L328.9 160 L266 160 L216.3 214.2 L183.1 160 "
        "L125.1 160 L93.1 345 L146.9 345 L166.1 233.8 L207.7 301.8 Z")
hero = base64.b64encode(
    (WT / "zoo/site/images/hero-train-dawn/hero-train-dawn-960.webp").read_bytes()
).decode()


def mark_svg(ground: str, ink: str, dot: str, size: int = 46) -> str:
    return (
        f'<svg viewBox="0 0 512 512" width="{size}" height="{size}">'
        f'<rect width="512" height="512" fill="{ground}"/><path d="{MARK}" fill="{ink}"/>'
        f'<circle cx="376" cy="301" r="44" fill="{dot}"/></svg>'
    )


CARDS = [
    ("1  heute", "Indigo mit Neonmint, wie die Seite sie heute ausliefert", f"""
     <div class="og" style="background:#0A0F2E">
       {mark_svg("#1B3BD8", "#FFFFFF", "#6FFFC8")}
       <h2 style="color:#EEF1FF">Safer, more affordable and better mobility through AI.</h2>
       <p style="color:#A7B1DE">Mobility Model Zoo</p>
       <span class="pill" style="background:#6FFFC8;color:#0A0F2E">3 published</span>
     </div>"""),
    ("2  Plakat, ruhig", "Navy und Orange in der Palette der Bilder", f"""
     <div class="og" style="background:#062544">
       {mark_svg("#FBEED0", "#062544", "#ED9B20")}
       <h2 style="color:#FBEED0">Safer, more affordable and better mobility through AI.</h2>
       <p style="color:#A5DBC6">Mobility Model Zoo</p>
       <span class="pill" style="background:#ED9B20;color:#062544">3 published</span>
     </div>"""),
    ("3  Plakat, laut", "Gleiche Welt, aber das Orange als Fl&auml;che statt als Tupfer", f"""
     <div class="og" style="background:#062544">
       <div class="band" style="background:#FF8A00"></div>
       {mark_svg("#FBEED0", "#062544", "#062544")}
       <h2 style="color:#FBEED0">Safer, more affordable and better mobility through AI.</h2>
       <p style="color:#FBEED0">Mobility Model Zoo</p>
       <span class="pill" style="background:#FBEED0;color:#062544">3 published</span>
     </div>"""),
    ("4  Bild statt Typo", "Eine der 91 Plakatabbildungen tr&auml;gt die Karte, Text als Leiste", f"""
     <div class="og img" style="background:#062544">
       <img src="data:image/webp;base64,{hero}">
       <div class="strip">{mark_svg("#FBEED0", "#062544", "#ED9B20", 34)}
         <b>Safer, more affordable and better mobility through AI.</b></div>
     </div>"""),
]

posts = "".join(f"""
  <article class="post">
    <div class="who"><span class="av"></span><span><b>Martin Habedank</b><i>Mobility &amp; AI &middot; 2h</i></span></div>
    <p class="txt">A new model is out. Same answers on the board, measured against a frozen
    benchmark &mdash; and the limits are written down.</p>
    {card}
    <div class="meta"><span>{title}</span><span>{note}</span></div>
  </article>""" for title, note, card in CARDS)

html = f"""<!doctype html><meta charset="utf-8"><style>
  body {{ margin:0; padding:24px 0; background:#F4F2EE;
          font-family:-apple-system,"Segoe UI",sans-serif; color:#191919; }}
  h1 {{ width:552px; margin:0 auto 16px; font-size:17px; }}
  h1 small {{ display:block; font-weight:400; color:#5E5E5E; font-size:13px; margin-top:3px; }}
  .post {{ width:552px; margin:0 auto 20px; background:#fff; border:1px solid #E0DFDC; border-radius:8px; }}
  .who {{ display:flex; align-items:center; gap:10px; padding:12px 14px 6px; }}
  .av {{ width:40px; height:40px; border-radius:50%; background:#C9C6C1; flex:none; }}
  .who b {{ display:block; font-size:14px; }}
  .who i {{ font-style:normal; font-size:12px; color:#5E5E5E; }}
  .txt {{ margin:0; padding:2px 14px 12px; font-size:14px; line-height:1.45; }}
  .og {{ position:relative; width:552px; height:290px; padding:26px 30px;
         box-sizing:border-box; display:flex; flex-direction:column; align-items:flex-start;
         justify-content:center; gap:8px; overflow:hidden; }}
  .og h2 {{ font-size:25px; line-height:1.15; font-weight:700; margin:4px 0 0; max-width:15ch;
            letter-spacing:-.02em; }}
  .og p {{ margin:0; font-size:14px; font-weight:600; }}
  .pill {{ position:absolute; right:28px; bottom:26px; padding:5px 12px; border-radius:999px;
           font-size:12px; font-weight:700; }}
  .band {{ position:absolute; inset:0 0 auto 0; height:74px; }}
  .og.img {{ padding:0; justify-content:flex-end; }}
  .og.img img {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
  .strip {{ position:relative; display:flex; align-items:center; gap:12px; width:100%;
            padding:14px 20px; background:rgba(6,37,68,.92); box-sizing:border-box; }}
  .strip b {{ color:#FBEED0; font-size:17px; line-height:1.2; font-weight:700; letter-spacing:-.01em; }}
  .meta {{ display:flex; justify-content:space-between; gap:12px; padding:10px 14px;
           font-size:12px; color:#5E5E5E; border-top:1px solid #E0DFDC; }}
  .meta span:first-child {{ font-weight:700; color:#191919; }}
</style>
<h1>Vier Teilekarten im Feed<small>552&nbsp;px breit, auf LinkedIn-Grau. So gro&szlig; sieht sie jemand beim Scrollen.</small></h1>
{posts}"""
(OUT / "feed.html").write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 640, "height": 900}, device_scale_factor=2)
    pg.goto((OUT / "feed.html").as_uri())
    pg.wait_for_timeout(900)
    pg.screenshot(path=str(OUT / "feed.png"), full_page=True)
    b.close()
print("ok")
