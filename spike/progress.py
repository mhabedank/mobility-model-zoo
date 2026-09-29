# ruff: noqa: E501 - HTML and SVG templates
"""Progress page for the spike run on the MacBook: training loss and benchmark agreement.

Writes data/spike/progress.html (refreshes itself every 60 s). Run repeatedly while the spike runs:
    uv run python spike/progress.py [--loop]
The provisional composite scores only the chunks a run has finished so far, and scores the teacher
on the same chunks, so the numbers are comparable at every point but move until the run is done.
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from jtbd_pilot.config import load_settings
from jtbd_pilot.consensus import load_consensus
from jtbd_pilot.jsonio import read_json
from jtbd_pilot.metrics import CATEGORY_LABELS, EVIDENCE_LABELS, composite, f1_stat, kappa_stat
from jtbd_pilot.runs import load_outputs
from jtbd_pilot.scoring import RELEVANCE_LABELS, score_units

ROOT = Path(__file__).resolve().parent.parent
SPIKE = ROOT / "data/spike"
LOG = SPIKE / "train-mlx.log"
OUT = SPIKE / "progress.html"
TOTAL_ITERS = 549
RUNS = {  # label -> run id; teacher first so it is always series 1 when present
    "Teacher qwen3.6 35B": "run-teacher_candidate-teacher-qwen3.6-main-3223351c",
    "Basis Qwen3-4B": "run-baseline-spike-base-main-3223351c",
    "Trainiert Qwen3-4B + LoRA": "run-baseline-spike-tuned-main-3223351c",
}
DIMS = ["relevance", "item_matching", "kind", "actor_type", "evidence_type", "evidence_scope"]
DIM_NAMES = ["Relevanz", "Items finden", "Art", "Akteurstyp", "Evidenztyp", "Evidenzumfang"]

TRAIN_RE = re.compile(r"Iter (\d+): Train loss ([\d.]+).*?It/sec ([\d.]+).*?Peak mem ([\d.]+)")
VAL_RE = re.compile(r"Iter (\d+): Val loss ([\d.]+)")


def training() -> dict:
    text = LOG.read_text(errors="replace") if LOG.exists() else ""
    train = [(int(i), float(v)) for i, v, *_ in TRAIN_RE.findall(text)]
    val = [(int(i), float(v)) for i, v in VAL_RE.findall(text)]
    speeds = [float(m[2]) for m in TRAIN_RE.findall(text)]
    peak = max((float(m[3]) for m in TRAIN_RE.findall(text)), default=None)
    done = train[-1][0] if train else 0
    eta = None
    if speeds and speeds[-1] > 0:
        eta = (TOTAL_ITERS - done) / speeds[-1]
    return {"train": train, "val": val, "iter": done, "eta_s": eta, "peak_gb": peak,
            "finished": "Saved final weights" in text,
            "error": (text.strip().splitlines() or [""])[-1][:200] if "Traceback" in text else None,
            "started": LOG.exists()}


def dim_scores(units: dict) -> dict:
    stats = {"relevance": kappa_stat(RELEVANCE_LABELS), "item_matching": f1_stat,
             "evidence_type": kappa_stat(EVIDENCE_LABELS, "quadratic"),
             **{d: kappa_stat(labels) for d, labels in CATEGORY_LABELS.items()}}
    out = {}
    for d in DIMS:
        payloads = [p for _, p in units[d]]
        try:
            value = stats[d](payloads) if payloads else None
        except Exception:  # noqa: BLE001 - too few units for a kappa: show as n/a
            value = None
        out[d] = None if value is None or value != value else round(float(value), 3)
    return out


def benchmark(settings) -> dict:
    consensus, contested, _ = load_consensus(settings, "main")
    min_iou = float(settings.pilot.get("min_iou", 0.3))
    runs_dir = SPIKE / "runs"
    teacher_outputs = None
    result = {}
    for label, run_id in RUNS.items():
        if not (runs_dir / run_id / "manifest.json").exists():
            continue
        outputs = load_outputs(settings, run_id)
        manifest = read_json(runs_dir / run_id / "manifest.json")
        if teacher_outputs is None and "teacher" in run_id:
            teacher_outputs = outputs
        done = sorted(outputs)
        entry = {"done": len(done), "status": manifest.get("status"), "run_id": run_id}
        if done:
            units, _ = score_units(consensus, contested, done, outputs, min_iou)
            entry["dims"] = dim_scores(units)
            entry["composite"] = composite(entry["dims"].values())
            if teacher_outputs is not None and "teacher" not in run_id:
                t_units, _ = score_units(consensus, contested, done, teacher_outputs, min_iou)
                entry["teacher_same_chunks"] = composite(dim_scores(t_units).values())
        final = SPIKE / "analysis/spike-v1/scores" / f"{run_id}.json"
        if final.exists():
            entry["final"] = read_json(final)["composite"]
        rates = SPIKE / "analysis/spike-v1/checks" / f"{run_id}.summary.json"
        if rates.exists():
            pr = read_json(rates)["pass_rates"]
            entry["quote"] = pr.get("quote_verbatim", {}).get("rate")
            entry["schema"] = pr.get("schema_valid", {}).get("rate")
        result[label] = entry
    return result


def fmt(x, digits=2):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def duration(seconds):
    if seconds is None:
        return "–"
    h, m = divmod(int(seconds) // 60, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def loss_chart(tr: dict) -> str:
    w, h, left, right, top, bottom = 720, 300, 48, 110, 16, 36
    series = [("Trainings-Loss", tr["train"], "s1")]
    points = [p for _, s, _ in series for p in s]
    if not points:
        return '<p class="muted">Noch keine Loss-Werte. Der erste erscheint nach 10 Schritten.</p>'
    ymax = max(v for _, v in points) * 1.1
    ymax = max(ymax, 0.5)
    x = lambda i: left + (w - left - right) * i / TOTAL_ITERS  # noqa: E731
    y = lambda v: top + (h - top - bottom) * (1 - v / ymax)  # noqa: E731
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Loss je Trainingsschritt">']
    step = 0.5 if ymax <= 3 else 1.0
    v = 0.0
    while v <= ymax + 1e-9:
        parts.append(f'<line class="grid" x1="{left}" x2="{w - right}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                     f'<text class="tick" x="{left - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{fmt(v, 1)}</text>')
        v += step
    for i in range(0, TOTAL_ITERS + 1, 100):
        parts.append(f'<text class="tick" x="{x(i):.1f}" y="{h - bottom + 18}" text-anchor="middle">{i}</text>')
    parts.append(f'<text class="tick" x="{x(TOTAL_ITERS):.1f}" y="{h - bottom + 18}" text-anchor="middle">{TOTAL_ITERS}</text>')
    parts.append(f'<text class="axis" x="{(left + w - right) / 2}" y="{h - 4}" text-anchor="middle">Trainingsschritt</text>')
    for name, data, cls in series:
        if not data:
            continue
        path = " ".join(f"{'M' if k == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for k, (i, v) in enumerate(data))
        parts.append(f'<path class="line {cls}" d="{path}"/>')
        for i, v in data:
            parts.append(f'<circle class="dot {cls}" cx="{x(i):.1f}" cy="{y(v):.1f}" r="4"/>')
        li, lv = data[-1]
        parts.append(f'<text class="label" x="{x(li) + 8:.1f}" y="{y(lv) + 4:.1f}">{name} {fmt(lv)}</text>')
    parts.append(f'<line id="xhair" class="xhair" y1="{top}" y2="{h - bottom}" x1="0" x2="0" visibility="hidden"/>')
    parts.append(f'<rect id="hit" x="{left}" y="{top}" width="{w - left - right}" height="{h - top - bottom}" fill="transparent"/>')
    parts.append("</svg>")
    return "".join(parts)


def score_chart(bench: dict) -> str:
    rows = [(label, e.get("final", e.get("composite")), "final" in e, e["done"])
            for label, e in bench.items() if e.get("composite") is not None or e.get("final")]
    if not rows:
        return '<p class="muted">Noch keine bewerteten Chunks.</p>'
    w, bar_h, gap, left, right = 720, 28, 14, 210, 150
    h = len(rows) * (bar_h + gap) + 30
    x = lambda v: left + (w - left - right) * v  # noqa: E731
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Gesamtwert je Modell">']
    for v in (0, 0.25, 0.5, 0.75, 1.0):
        parts.append(f'<line class="grid" x1="{x(v):.1f}" x2="{x(v):.1f}" y1="0" y2="{h - 24}"/>'
                     f'<text class="tick" x="{x(v):.1f}" y="{h - 8}" text-anchor="middle">{fmt(v)}</text>')
    for k, (label, value, final, done) in enumerate(rows):
        top = k * (bar_h + gap) + 4
        width = max(x(value or 0) - left, 2)
        cls = "bar" + ("" if final else " provisional")
        parts.append(f'<text class="rowlabel" x="{left - 10}" y="{top + bar_h / 2 + 5}" text-anchor="end">{html.escape(label)}</text>')
        parts.append(f'<path class="{cls}" d="M{left},{top} h{width - 4} a4,4 0 0 1 4,4 v{bar_h - 8} a4,4 0 0 1 -4,4 h-{width - 4} z"/>')
        note = "final" if final else f"vorläufig, {done}/35 Chunks"
        parts.append(f'<text class="label" x="{left + width + 8}" y="{top + bar_h / 2 + 5}">{fmt(value)} · {note}</text>')
    parts.append("</svg>")
    return "".join(parts)


def checkpoints() -> dict:
    path = SPIKE / "checkpoints.json"
    return json.loads(path.read_text()).get("checkpoints", {}) if path.exists() else {}


def ckpt_best(ckpts: dict) -> str:
    trained = {k: v for k, v in ckpts.items() if k != "base"}
    if not trained:
        return "–"
    k = max(trained, key=lambda n: trained[n]["score"])
    return f"Schritt {trained[k]['step']}: {fmt(trained[k]['score'])}"


def ckpt_table(ckpts: dict) -> str:
    if not ckpts:
        return '<p class="muted">Nach dem Training generiert jeder Zwischenstand Antworten für die 10 Validierungsbeispiele (dauert ca. 1 Stunde).</p>'
    rows = "".join(
        f"<tr><td>{'Basis (ohne Training)' if k == 'base' else 'Schritt ' + str(v['step'])}</td>"
        f"<td>{fmt(v['schema_valid'])}</td><td>{fmt(v['relevance_acc'])}</td><td>{fmt(v['item_f1'])}</td>"
        f"<td><b>{fmt(v['score'])}</b></td></tr>" for k, v in ckpts.items())
    return ("<div class=\"scroll\"><table><tr><th>Checkpoint</th><th>Gültiges JSON</th><th>Relevanz richtig</th>"
            f"<th>Items F1</th><th>Score</th></tr>{rows}</table></div>")


def render(tr: dict, bench: dict, log_tail: str) -> str:
    ckpts = checkpoints()
    pct = 100 * tr["iter"] / TOTAL_ITERS
    if tr["error"]:
        status = f"ABGEBROCHEN bei Schritt {tr['iter']}"
    elif tr["finished"]:
        status = "fertig"
    elif not tr["started"]:
        status = "wartet"
    else:
        status = f"Schritt {tr['iter']} von {TOTAL_ITERS}"
    tiles = [
        ("Training", status, tr["error"] or ("Adapter gespeichert" if tr["finished"] else f"noch ca. {duration(tr['eta_s'])}")),
        ("Bester Checkpoint (Validierung)", ckpt_best(ckpts),
         "Score aus Relevanz und Items auf 10 Validierungsbeispielen" if ckpts else "wird nach dem Training bestimmt"),
    ]
    for label, e in bench.items():
        if "teacher" in e["run_id"]:
            continue
        tiles.append((label, f"{e['done']}/35 Chunks",
                      f"Gesamtwert {fmt(e.get('final', e.get('composite')))} · Teacher auf denselben Chunks {fmt(e.get('teacher_same_chunks'))}"))
    tile_html = "".join(f'<div class="tile"><div class="k">{html.escape(a)}</div><div class="v">{html.escape(b)}</div>'
                        f'<div class="muted">{html.escape(c)}</div></div>' for a, b, c in tiles)
    dim_rows = "".join(
        f"<tr><td>{html.escape(label)}</td>" + "".join(f"<td>{fmt((e.get('dims') or {}).get(d))}</td>" for d in DIMS)
        + f"<td><b>{fmt(e.get('final', e.get('composite')))}</b></td><td>{fmt(e.get('quote'), 2)}</td><td>{e['done']}/35</td></tr>"
        for label, e in bench.items())
    loss_rows = "".join(f"<tr><td>{i}</td><td>{fmt(v, 3)}</td></tr>" for i, v in tr["train"][-12:])
    data = json.dumps({"train": tr["train"], "val": tr["val"], "total": TOTAL_ITERS})
    now = datetime.now().strftime("%H:%M:%S")
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="60">
<title>Spike-Fortschritt</title>
<style>
:root{{color-scheme:light;--surface:#fcfcfb;--card:#ffffff;--text:#0b0b0b;--muted:#52514e;--grid:#e4e3df;--s1:#2a78d6;--s2:#eb6834}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--surface:#1a1a19;--card:#222221;--text:#ffffff;--muted:#c3c2b7;--grid:#3a3a38;--s1:#3987e5;--s2:#d95926}}}}
:root[data-theme="dark"]{{color-scheme:dark;--surface:#1a1a19;--card:#222221;--text:#ffffff;--muted:#c3c2b7;--grid:#3a3a38;--s1:#3987e5;--s2:#d95926}}
body{{margin:0;background:var(--surface);color:var(--text);font:14px/1.5 system-ui,sans-serif}}
main{{max-width:960px;margin:0 auto;padding:20px 16px 40px}}
h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:15px;margin:28px 0 4px}}
.muted{{color:var(--muted);font-size:13px}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}}
.tile{{background:var(--card);border:1px solid var(--grid);border-radius:8px;padding:12px}}
.tile .k{{color:var(--muted);font-size:12px}} .tile .v{{font-size:20px;font-weight:600;margin:2px 0}}
.progress{{height:8px;background:var(--grid);border-radius:4px;overflow:hidden;margin:8px 0}}
.progress div{{height:100%;background:var(--s1);border-radius:4px}}
.card{{background:var(--card);border:1px solid var(--grid);border-radius:8px;padding:12px;position:relative}}
svg{{width:100%;height:auto;display:block}}
.grid{{stroke:var(--grid);stroke-width:1}} .tick,.axis{{fill:var(--muted);font-size:11px}}
.line{{fill:none;stroke-width:2}} .line.s1{{stroke:var(--s1)}} .line.s2{{stroke:var(--s2)}}
.dot{{stroke:var(--card);stroke-width:2}} .dot.s1{{fill:var(--s1)}} .dot.s2{{fill:var(--s2)}}
.label,.rowlabel{{fill:var(--text);font-size:12px}}
.bar{{fill:var(--s1)}} .bar.provisional{{fill:var(--s1);opacity:.45}}
.xhair{{stroke:var(--muted);stroke-width:1;stroke-dasharray:3 3}}
.legend{{display:flex;gap:16px;font-size:12px;color:var(--muted);margin:4px 0 8px}}
.legend i{{display:inline-block;width:14px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}}
#tip{{position:absolute;pointer-events:none;background:var(--card);border:1px solid var(--grid);border-radius:6px;padding:6px 8px;font-size:12px;display:none;box-shadow:0 2px 8px #0002}}
table{{border-collapse:collapse;width:100%;font-size:13px}} td,th{{border-bottom:1px solid var(--grid);padding:4px 6px;text-align:right}}
td:first-child,th:first-child{{text-align:left}} .scroll{{overflow-x:auto}}
details{{margin-top:8px}} pre{{white-space:pre-wrap;font-size:11px;color:var(--muted)}}
</style></head><body><main>
<h1>Spike-Fortschritt</h1>
<div class="muted">Stand {now} · aktualisiert sich jede Minute · MacBook M3 Pro, MLX, Qwen3-4B 4-Bit</div>
<div class="muted">Pipeline: {html.escape((log_tail.strip().splitlines() or ["–"])[-1])}</div>
<div class="progress" aria-label="Trainingsfortschritt {pct:.0f} %"><div style="width:{pct:.1f}%"></div></div>
<div class="tiles">{tile_html}</div>

<h2>Lernt das Modell? Loss je Trainingsschritt</h2>
<div class="muted">Trainings-Loss alle 10 Schritte, niedriger ist besser. Zweiter Versuch: Loss als Summe über alle Antwort-Tokens (geteilt durch die mittlere Antwortlänge), daher schwankt er mit der Länge der Beispiele. Das ehrliche Signal ist die Tabelle darunter.</div>
<div class="card" id="losscard">{loss_chart(tr)}<div id="tip"></div></div>

<h2>Welcher Zwischenstand ist der beste? Generierung auf 10 Validierungsbeispielen</h2>
<div class="muted">Jeder Checkpoint beantwortet die zurückgehaltenen Beispiele wie im Benchmark. Score = Mittel aus „Relevanz richtig“ und „Items F1“ gegen die Teacher-Antwort; erfundene Zitate zählen als Fehler. Der beste Checkpoint geht in den Benchmark.</div>
<div class="card">{ckpt_table(ckpts)}</div>

<h2>Wie gut ist es? Gesamtwert gegen Claude (0 bis 1)</h2>
<div class="muted">Haupt-KPI: Mittel aus sechs Übereinstimmungswerten mit der Claude-Referenz auf den 35 Bewertungs-Chunks. Helle Balken sind vorläufig (nur bisher gelabelte Chunks).</div>
<div class="card">{score_chart(bench)}</div>

<h2>Tabelle</h2>
<div class="scroll"><table><tr><th>Modell</th>{"".join(f"<th>{n}</th>" for n in DIM_NAMES)}<th>Gesamt</th><th>Zitat wörtlich</th><th>Chunks</th></tr>{dim_rows}</table></div>
<details><summary class="muted">Letzte Loss-Werte und Log</summary><table><tr><th>Schritt</th><th>Trainings-Loss</th></tr>{loss_rows}</table><pre>{html.escape(log_tail)}</pre></details>
</main>
<script>
const D={data};
const svg=document.querySelector('#losscard svg'),tip=document.getElementById('tip'),hit=document.getElementById('hit'),xh=document.getElementById('xhair');
if(svg&&hit){{
 const L=48,R=110,W=720;
 hit.addEventListener('mousemove',e=>{{
  const pt=svg.createSVGPoint();pt.x=e.clientX;pt.y=e.clientY;const p=pt.matrixTransform(svg.getScreenCTM().inverse());
  const it=Math.round((p.x-L)/(W-L-R)*D.total);
  const near=a=>a.length?a.reduce((b,c)=>Math.abs(c[0]-it)<Math.abs(b[0]-it)?c:b):null;
  const t=near(D.train),v=near(D.val);if(!t)return;
  const xx=L+(W-L-R)*t[0]/D.total;xh.setAttribute('x1',xx);xh.setAttribute('x2',xx);xh.setAttribute('visibility','visible');
  tip.innerHTML='Schritt '+t[0]+'<br>Trainings-Loss '+t[1].toFixed(3)+(v&&Math.abs(v[0]-t[0])<=10?'<br>Validierungs-Loss '+v[1].toFixed(3):'');
  const r=svg.getBoundingClientRect(),c=svg.parentNode.getBoundingClientRect();
  tip.style.display='block';tip.style.left=(xx/W*r.width+r.left-c.left+10)+'px';tip.style.top='20px';
 }});
 hit.addEventListener('mouseleave',()=>{{tip.style.display='none';xh.setAttribute('visibility','hidden')}});
}}
</script></body></html>"""


def main() -> None:
    settings = load_settings(ROOT / "configs/spike-v1.yaml")
    while True:
        tr = training()
        bench = benchmark(settings)
        run_log = SPIKE / "run-mac.log"
        tail = run_log.read_text(errors="replace")[-1500:] if run_log.exists() else ""
        OUT.write_text(render(tr, bench, tail), encoding="utf-8")
        last = (tail.strip().splitlines() or [""])[-1]
        finished = last.endswith(" done") or ("training finished (rc" in last and "(rc 0)" not in last)
        if "--loop" not in sys.argv or finished:
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
