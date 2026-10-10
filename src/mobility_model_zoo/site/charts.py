"""Charts of the model page as inline SVG and HTML, drawn from the results of a release
(research R6; style from the identity sheet, section 06).

Charts are declared per model in `site.yaml` (`charts: [{type, metrics, labels}]`). Every number
comes from the results JSON; the label file only gives display names and is read at the release
tag. Each chart comes with a table of all its values, so nothing is shown only as a picture.

- `quality_vs_speed`: the comparison composite (quality metric `comparison_composite`) against
  texts per minute (performance metrics starting with `metrics`) for this model on each machine,
  the generative models it was compared with (`comparison_composite_<id>` and
  `comparison_chunks_per_min_<id>`) and the best zero-shot small model as a reference line.
- `latency_per_machine`: the time for one text (performance metrics starting with `metrics`), one
  bar per machine on a log scale.
"""

from __future__ import annotations

import json
import math
from html import escape
from typing import Any

from markupsafe import Markup

from mobility_model_zoo.release.card import num
from mobility_model_zoo.release.registry import Registry
from mobility_model_zoo.site.context import file_at_tag
from mobility_model_zoo.site.facts import Facts, unit_label

W, H, LEFT, RIGHT, TOP, BOTTOM = 560, 400, 56, 540, 20, 340


def _metrics(reg: Registry, name: str, version: str, kind: str) -> dict[str, dict[str, Any]]:
    return {m["name"]: m for m in reg.results(name, version, kind)["metrics"]}


def _labels(reg: Registry, name: str, version: str, path: str | None) -> dict[str, dict[str, str]]:
    if not path:
        return {"scout": {}, "others": {}}
    text = file_at_tag(reg, path, f"{name}/v{version}")
    data = json.loads(text) if text else {}
    return {
        "scout": {e.get("id", ""): e.get("label", "") for e in data.get("scout", [])},
        "others": {e.get("id", ""): e.get("label", "") for e in data.get("others", [])},
    }


def _machines(perf: dict[str, dict[str, Any]], prefix: str) -> list[tuple[str, dict[str, Any]]]:
    """(machine id, metric) for `prefix` (id "") and `prefix_<id>`; comparison metrics excluded."""
    found = []
    for metric_name, m in perf.items():
        if metric_name == prefix:
            found.append(("", m))
        elif metric_name.startswith(prefix + "_"):
            found.append((metric_name[len(prefix) + 1 :], m))
    return found


def _source(reg: Registry, name: str, version: str, kind: str) -> str:
    return str(reg.results_path(name, version, kind).relative_to(reg.root))


def quality_vs_speed(
    reg: Registry, name: str, version: str, chart: dict[str, Any], facts: Facts, page: str
) -> dict[str, Any]:
    quality = _metrics(reg, name, version, "quality")
    perf = _metrics(reg, name, version, "performance")
    labels = _labels(reg, name, version, chart.get("labels"))
    q_src, p_src = _source(reg, name, version, "quality"), _source(reg, name, version, "performance")
    own_q = quality["comparison_composite"]
    facts.add(page, "chart:quality_vs_speed:own", num(own_q["value"]), q_src, own_q["name"])
    own = []
    for machine, m in _machines(perf, chart["metrics"]):
        facts.add(page, f"chart:quality_vs_speed:{m['name']}", num(m["value"]), p_src, m["name"])
        own.append(
            {
                "label": labels["scout"].get(machine) or machine or "reference machine",
                "x": m["value"],
                "y": own_q["value"],
                "hardware": m["hardware"],
            }
        )
    others = []
    for metric_name, m in perf.items():
        if not metric_name.startswith("comparison_chunks_per_min_"):
            continue
        oid = metric_name[len("comparison_chunks_per_min_") :]
        q = quality.get(f"comparison_composite_{oid}")
        facts.add(page, f"chart:quality_vs_speed:{metric_name}", num(m["value"]), p_src, metric_name)
        if q:
            facts.add(page, f"chart:quality_vs_speed:{q['name']}", num(q["value"]), q_src, q["name"])
        others.append(
            {
                "label": labels["others"].get(oid) or oid,
                "x": m["value"],
                "y": q["value"] if q else None,
                "hardware": m["hardware"],
            }
        )
    base = quality.get("comparison_composite_best_baseline")
    ys = [p["y"] for p in own + others if p["y"] is not None] + ([base["value"]] if base else [])
    y0, y1 = math.floor(min(ys) * 10) / 10, math.ceil(max(ys) * 10) / 10
    xs = [p["x"] for p in own + others]
    x0, x1 = math.floor(math.log10(min(xs))), math.ceil(math.log10(max(xs)))

    def px(x: float) -> float:
        return LEFT + (math.log10(x) - x0) / (x1 - x0) * (RIGHT - LEFT)

    def py(y: float) -> float:
        return BOTTOM - (y - y0) / (y1 - y0) * (BOTTOM - TOP)

    steps = range(round((y1 - y0) * 10) + 1)
    rows = "".join(f"M{LEFT} {py(y0 + i / 10):.0f}H{RIGHT}" for i in steps)
    cols = "".join(f"M{px(10**e):.0f} {TOP}V{BOTTOM}" for e in range(x0, x1 + 1))
    parts = [f'<path class="gr" d="{rows}"/>', f'<path class="gr" d="{cols}"/>']
    if base:
        facts.add(page, "chart:quality_vs_speed:baseline", num(base["value"]), q_src, base["name"])
        parts.append(f'<path class="sbl" d="M{LEFT} {py(base["value"]):.0f}H{RIGHT}"/>')
        parts.append(
            f'<text class="mut" x="{RIGHT - 4}" y="{py(base["value"]) + 16:.0f}" text-anchor="end">'
            f"best zero-shot small model: {num(base['value'])}</text>"
        )
    parts.append(f'<path class="ax" d="M{LEFT} {TOP}V{BOTTOM}H{RIGHT}"/>')
    for i in steps:
        y = round(y0 + i / 10, 1)
        parts.append(
            f'<text class="mut" x="{LEFT - 6}" y="{py(y) + 4:.0f}" text-anchor="end">{y:g}</text>'
        )
    for e in range(x0, x1 + 1):
        parts.append(
            f'<text class="mut" x="{px(10**e):.0f}" y="{BOTTOM + 18}" text-anchor="middle">'
            f"{10**e:,g}</text>"
        )
    parts.append(
        f'<text class="mut" x="{(LEFT + RIGHT) / 2:.0f}" y="{BOTTOM + 40}" text-anchor="middle">'
        "texts per minute, log scale</text>"
    )
    parts.append(
        f'<text class="mut" x="14" y="{(TOP + BOTTOM) / 2:.0f}" text-anchor="middle" '
        f'transform="rotate(-90 14 {(TOP + BOTTOM) / 2:.0f})">comparison composite</text>'
    )
    for p in others:
        if p["y"] is not None:
            parts.append(f'<circle class="sb" cx="{px(p["x"]):.1f}" cy="{py(p["y"]):.1f}" r="6"/>')
    for p in own:
        parts.append(f'<circle class="sa" cx="{px(p["x"]):.1f}" cy="{py(p["y"]):.1f}" r="8"/>')
    best = max(own, key=lambda p: p["x"])
    parts.append(
        f'<text x="{px(best["x"]) - 12:.0f}" y="{py(best["y"]) - 14:.0f}" text-anchor="end" '
        f'style="font-weight:700">{escape(name)} {num(own_q["value"])}</text>'
    )
    gen = [p for p in others if p["y"] is not None]
    if gen:
        lo, hi = min(p["x"] for p in gen), max(p["x"] for p in gen)
        parts.append(
            f'<text class="mut" x="{px(math.sqrt(lo * hi)):.0f}" y="{TOP + 16}" text-anchor="middle">'
            "open circles: models compared</text>"
        )
    alt = (
        f"Scatter plot. {name} reaches a comparison composite of {num(own_q['value'])} at "
        + ", ".join(f"{num(p['x'])} texts per minute on {p['label']}" for p in own)
        + ". "
        + (f"Dashed line: best zero-shot small model, {num(base['value'])}. " if base else "")
        + "Models compared: "
        + "; ".join(
            f"{p['label']} {num(p['y']) if p['y'] is not None else 'reference'} at "
            f"{num(p['x'])} texts per minute"
            for p in others
        )
        + "."
    )
    svg = (
        f'<svg class="ch" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(alt)}">'
        + "".join(parts)
        + "</svg>"
    )
    rows = [
        {
            "model": f"{name} ({p['label']})",
            "quality": num(p["y"]),
            "speed": num(p["x"]),
            "hardware": p["hardware"],
        }
        for p in own
    ]
    rows += [
        {
            "model": p["label"],
            "quality": num(p["y"]) if p["y"] is not None else "reference",
            "speed": num(p["x"]),
            "hardware": p["hardware"],
        }
        for p in others
    ]
    return {
        "type": "quality_vs_speed",
        "caption": "Agreement composite against speed",
        "html": Markup(svg),  # noqa: S704 - built from escaped values above
        "note": (
            f"Composite = {own_q['description'].lower()}, measured against "
            f"{own_q['reference']} on benchmark {own_q['benchmark']}; not accuracy. "
            "Speeds of the generative models are one request at a time."
        ),
        "columns": ["Model", "Comparison composite", "Texts per minute", "Measured on"],
        "rows": [[r["model"], r["quality"], r["speed"], r["hardware"]] for r in rows],
    }


def latency_per_machine(
    reg: Registry, name: str, version: str, chart: dict[str, Any], facts: Facts, page: str
) -> dict[str, Any]:
    perf = _metrics(reg, name, version, "performance")
    labels = _labels(reg, name, version, chart.get("labels"))
    src = _source(reg, name, version, "performance")
    bars = []
    for machine, m in _machines(perf, chart["metrics"]):
        facts.add(page, f"chart:latency:{m['name']}", num(m["value"]), src, m["name"])
        bars.append(
            {
                "label": labels["scout"].get(machine) or machine or "reference machine",
                "value": m["value"],
                "unit": unit_label(m.get("unit")),
                "hardware": m["hardware"],
                "description": m.get("description", ""),
            }
        )
    bars.sort(key=lambda b: b["value"])
    lo = 10 ** math.floor(math.log10(min(b["value"] for b in bars)))
    hi = 10 ** math.ceil(math.log10(max(b["value"] for b in bars)))
    out = [
        '<div class="lol" role="img" aria-label="'
        + escape(
            f"{bars[0]['description']}: "
            + "; ".join(f"{b['label']} {num(b['value'])} {b['unit']}" for b in bars)
        )
        + '">'
    ]
    for b in bars:
        pct = (math.log10(b["value"]) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * 92 + 4
        pos = f"left:{pct + 3:.1f}%" if pct < 80 else f"right:{100 - pct + 3:.1f}%"
        out.append(
            f'<div aria-hidden="true">{escape(b["label"])}</div>'
            f'<div class="tr" aria-hidden="true"><div class="ln" style="width:{pct:.1f}%"></div>'
            f'<div class="dt" style="left:{pct:.1f}%"></div>'
            f'<div class="vl" style="{pos}">{num(b["value"])} {escape(b["unit"])}</div></div>'
        )
    out.append("</div>")
    return {
        "type": "latency_per_machine",
        "caption": next(
            (m["description"] for k, m in perf.items() if k == chart["metrics"]), bars[0]["description"]
        )
        or "Time per text",
        "html": Markup("".join(out)),  # noqa: S704 - built from escaped values above
        "note": (
            f"Log scale from {num(lo)} to {num(hi)} {bars[0]['unit']}; the same text on every machine."
        ),
        "columns": ["Machine", f"Time ({bars[0]['unit']})", "Measured on"],
        "rows": [[b["label"], num(b["value"]), b["hardware"]] for b in bars],
    }


CHARTS = {"quality_vs_speed": quality_vs_speed, "latency_per_machine": latency_per_machine}


def render(
    reg: Registry, name: str, version: str, declared: list[dict[str, Any]], facts: Facts, page: str
) -> list[dict[str, Any]]:
    return [CHARTS[c["type"]](reg, name, version, c, facts, page) for c in declared]
