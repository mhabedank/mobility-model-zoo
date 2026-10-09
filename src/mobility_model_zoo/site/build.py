"""`zoo site build`: render the website from the registry into `_site/` (contracts/site-tree.md).

Pages: the start page, one page per published model, one page per output format, a 404 page.
Every model fact comes from the release records and results (FR-004); `_build/facts.json` lists
each rendered fact with its source for `zoo site check` and is removed before deployment.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

import jinja2
from markupsafe import Markup

from mobility_model_zoo.release.card import fill, install_line, num, topic_url
from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry
from mobility_model_zoo.site import charts, context, examples, facts, schema_doc
from mobility_model_zoo.site.markdown import md

PACKAGE = "mobility_model_zoo.site"
DETERMINISTIC = ("quotes_verbatim_rate", "schema_valid_rate", "consistency_rate")


def _static() -> Any:
    return resources.files(PACKAGE).joinpath("static")


def _svg(rel: str) -> str:
    return _static().joinpath(f"img/{rel}").read_text(encoding="utf-8").strip()


def mark(size: int) -> Markup:
    body = _svg("mark.svg").replace('role="img" aria-label="Mobility Model Zoo"', "")
    return Markup(body.replace("<svg ", f'<svg width="{size}" height="{size}" aria-hidden="true" ', 1))


def motif(name: str | None, size: int = 48, label: str = "") -> Markup:
    """A motif inlined, so it follows the theme tokens; decorative unless `label` is given."""
    if not name or not _static().joinpath(f"img/motifs/{name}").is_file():
        return Markup("")
    a11y = f'role="img" aria-label="{label}"' if label else 'aria-hidden="true" focusable="false"'
    attrs = f'width="{size}" height="{size}" {a11y}' if size else a11y
    return Markup(_svg(f"motifs/{name}").replace("<svg ", f"<svg {attrs} ", 1))


def environment() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.PackageLoader(PACKAGE, "templates"),
        autoescape=True,
        undefined=jinja2.StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["num"] = num
    env.filters["md"] = md
    env.filters["ucfirst"] = lambda s: s[:1].upper() + s[1:]
    env.globals.update(mark=mark, motif=motif)
    return env


# ---- the model page ---------------------------------------------------------------------------
def _metric_rows(reg: Registry, name: str, version: str, kind: str, f: facts.Facts, page: str):
    rows = []
    for m in reg.results(name, version, kind)["metrics"]:
        resolved = facts.metric(reg, name, version, kind, m["name"])
        f.add(page, f"table:{kind}.{m['name']}", resolved["value"], resolved["source"], m["name"])
        rows.append({**resolved, "n_items": m.get("n_items")})
    return rows


def _card(reg, name, version, spec, f: facts.Facts, notes: facts.Notes, page) -> dict[str, Any]:
    kind, metric_name = spec["metric"].split(".", 1)
    m = facts.metric(reg, name, version, kind, metric_name)
    f.add(page, f"card:{spec['metric']}", m["value"], m["source"], metric_name)
    card = {"label": spec["label"], "m": m, "note": notes.ref(m), "compare": None}
    if spec.get("compare"):
        ckind, cname = spec["compare"].split(".", 1)
        c = facts.metric(reg, name, version, ckind, cname)
        f.add(page, f"card:{spec['compare']}", c["value"], c["source"], cname)
        card["compare"] = {"m": c, "label": spec.get("compare_label", c["description"])}
    return card


def model_page(
    reg: Registry, sm: dict[str, Any], f: facts.Facts, offline: bool, refresh: bool
) -> dict[str, Any]:
    name, m, version = sm["name"], sm["m"], sm["latest"]
    page = f"models/{name}/"
    pitch, notes = sm["pitch"], facts.Notes()
    latest = sm["releases"][0]

    def res(text: str, key: str) -> Markup:
        return Markup(facts.resolve(text or "", reg, name, version, f, notes, page, key))  # noqa: S704

    fmt = None
    if latest["output_format_version"]:
        fmt = schema_doc.output_format(reg, latest["output_format_version"])
    exs = examples.load(reg, name, version, fmt["schema"] if fmt else None, offline, refresh)
    quick = next((e for e in exs if e["file"] == pitch["quickstart_example"]), exs[0] if exs else None)
    quality = {q["name"]: q for q in reg.results(name, version, "quality")["metrics"]}
    benchmark = next((q.get("benchmark") for q in quality.values() if q.get("benchmark")), None)
    checks = []
    for metric_name in DETERMINISTIC + ("contested_items",):
        if metric_name in quality:
            resolved = facts.metric(reg, name, version, "quality", metric_name)
            f.add(page, f"checks:{metric_name}", resolved["value"], resolved["source"], metric_name)
            checks.append(resolved)
    recipe = f"topics/{m['topic']}/recipes/{name}.md"
    topic = reg.topic(m["topic"]) or {"id": m["topic"], "title": m["topic"]}
    return {
        "name": name,
        "m": m,
        "topic": topic,
        "topic_url": topic_url(topic),
        "status": sm["status"],
        "latest": latest,
        "releases": sm["releases"],
        "pitch": pitch,
        "tagline": res(pitch["tagline"], "tagline"),
        "audience": res(pitch["audience"], "audience"),
        "differentiators": [
            {"title": res(d["title"], f"diff{i}.title"), "text": res(d["text"], f"diff{i}.text")}
            for i, d in enumerate(pitch["differentiators"])
        ],
        "hardware_note": res(pitch.get("hardware_note", ""), "hardware_note"),
        "install": install_line(m, version),
        "how_to_run": fill(
            m["card"]["how_to_run"], m["repos"]["public"], f"v{version}", quick["text"] if quick else ""
        ).strip(),
        "quick": quick,
        "examples": exs,
        "fmt": fmt,
        "benchmark": benchmark,
        "checks": checks,
        "cards": [_card(reg, name, version, c, f, notes, page) for c in pitch.get("metric_cards", [])],
        "charts": charts.render(reg, name, version, pitch.get("charts", []), f, page),
        "quality_rows": _metric_rows(reg, name, version, "quality", f, page),
        "performance_rows": _metric_rows(reg, name, version, "performance", f, page),
        "notes": notes.items,
        "recipe": context.gh_blob(recipe) if (reg.root / recipe).exists() else None,
        "hf": f"{context.HF}/{m['repos']['public']}",
    }


# ---- building ---------------------------------------------------------------------------------
def _write(out: Path, rel: str, html: str) -> None:
    path = out / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def build(
    reg: Registry,
    out: Path,
    offline: bool = False,
    refresh: bool = False,
    say: Callable[[str], None] = print,
) -> dict[str, int]:
    site = context.load_site_config(reg)
    models = context.site_models(reg)
    env = environment()
    f = facts.Facts()
    failures: list[str] = []

    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    with resources.as_file(_static()) as static:
        shutil.copytree(static, out / "assets", dirs_exist_ok=True)

    common = {"site": site}
    pages = 0

    def render(rel: str, template: str, root: str, path: str, **ctx: Any) -> None:
        nonlocal pages
        html = env.get_template(template).render(**common, root=root, path=path, **ctx)
        _write(out, rel, html)
        pages += 1
        say(f"  wrote {rel}")

    rendered = []
    for sm in models:
        if sm["status"] == "in_progress":
            continue
        try:
            ctx = model_page(reg, sm, f, offline, refresh)
        except GateFailed as e:
            failures += e.failures
            continue
        render(
            f"models/{sm['name']}/index.html", "model.html.j2", "../../", f"models/{sm['name']}/", p=ctx
        )
        rendered.append(sm["name"])
    for format_id in schema_doc.format_ids(reg):
        try:
            fmt = schema_doc.output_format(reg, format_id)
        except GateFailed as e:
            failures += e.failures
            continue
        if fmt is None:
            failures.append(f"B5 {format_id}: zoo/formats/{format_id}.yaml is missing")
            continue
        render(
            f"formats/{format_id}/index.html",
            "format.html.j2",
            "../../",
            f"formats/{format_id}/",
            fmt=fmt,
        )
    topics = [t for t in reg.topics() if t["id"] != "sandbox"]
    render(
        "index.html",
        "start.html.j2",
        "",
        "",
        topics=topics,
        topic_url=topic_url,
        models=models,
        linked=set(rendered),
    )
    base = "/" + site["canonical_url"].split("://", 1)[1].split("/", 1)[1]
    render("404.html", "404.html.j2", base, "404.html")
    if failures:
        raise GateFailed(failures)
    f.write(out)
    in_progress = sum(1 for sm in models if sm["status"] == "in_progress")
    say(f"site: {pages} pages, {len(rendered)} models ({in_progress} in progress)")
    return {"pages": pages, "models": len(rendered), "in_progress": in_progress}
