"""`zoo site build`: render the website from the registry into `_site/` (contracts/site-tree.md).

Pages: the start page, the quickstart (`docs/quickstart.md`), the roadmap (`zoo/roadmap/roadmap.yaml`,
feature 015), one page per published model, one page per output format, a 404 page.
Every model fact comes from the release records and results (FR-004); `_build/facts.json` lists
each rendered fact with its source for `zoo site check` and is removed before deployment. Every
shareable page also gets a preview image (`og.py`, feature 012), listed in `_build/og.json`.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

import jinja2
from markupsafe import Markup

from mobility_model_zoo.release.card import (
    REPO_URL,
    fill,
    install_line,
    num,
    python_requirement,
    status_sentence,
    topic_url,
)
from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry
from mobility_model_zoo.site import (
    charts,
    context,
    examples,
    facts,
    motifs,
    og,
    roadmap,
    schema_doc,
)
from mobility_model_zoo.site import images as image_records
from mobility_model_zoo.site.markdown import md

PACKAGE = "mobility_model_zoo.site"
DETERMINISTIC = ("quotes_verbatim_rate", "schema_valid_rate", "consistency_rate")
QUICKSTART = "docs/quickstart.md"
_QUICKSTART_FIELD = re.compile(r"\{(install|snippet|output):([a-z0-9-]+)\}")
NO_OUTPUT = "(the model page shows what the program prints)"


def _static() -> Any:
    return resources.files(PACKAGE).joinpath("static")


def _svg(rel: str) -> str:
    return _static().joinpath(f"img/{rel}").read_text(encoding="utf-8").strip()


def mark(size: int) -> Markup:
    body = _svg("mark.svg").replace('role="img" aria-label="Mobility Model Zoo"', "")
    return Markup(body.replace("<svg ", f'<svg width="{size}" height="{size}" aria-hidden="true" ', 1))


def motif(name: str | None, size: int = 48, label: str = "", plate: int | str | None = None) -> Markup:
    """A motif inlined, so it follows the theme tokens; decorative unless `label` is given.
    With `plate` (a size in px or "hero") it sits on the dark plate of feature 016 (research R9)."""
    if not name or not _static().joinpath(f"img/motifs/{name}").is_file():
        return Markup("")
    a11y = f'role="img" aria-label="{label}"' if label else 'aria-hidden="true" focusable="false"'
    attrs = f'width="{size}" height="{size}" {a11y}' if size else a11y
    svg = _svg(f"motifs/{name}").replace("<svg ", f"<svg {attrs} ", 1)
    if plate is None:
        return Markup(svg)
    return Markup(f'<span class="plate plate-{plate}" data-motif="{name}">{svg}</span>')


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
    env.globals.update(mark=mark, motif=motif, og_width=og.WIDTH, og_height=og.HEIGHT)
    return env


# ---- the model page ---------------------------------------------------------------------------
def _schema_url(reg: Registry, fmt: dict[str, Any], tag: str) -> str:
    """The output schema at the release tag, or on main if it was documented after the release."""
    import subprocess

    at_tag = subprocess.run(
        ["git", "-C", str(reg.root), "cat-file", "-e", f"{tag}:{fmt['schema_path']}"],
        capture_output=True,
        check=False,
    )
    return context.gh_blob(fmt["schema_path"], tag if at_tag.returncode == 0 else "main")


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
    card = {"label": spec["label"], "m": m, "note": notes.ref(m), "compare": None, "bar": None}
    if spec.get("compare"):
        ckind, cname = spec["compare"].split(".", 1)
        c = facts.metric(reg, name, version, ckind, cname)
        f.add(page, f"card:{spec['compare']}", c["value"], c["source"], cname)
        card["compare"] = {"m": c, "label": spec.get("compare_label", c["description"])}
        card["bar"] = charts.comparison_bar(
            m["raw"], c["raw"], m["unit"], spec["label"], card["compare"]["label"]
        )
    return card


def _evidence(reg: Registry, name: str, version: str, latest: dict[str, Any]) -> list[dict[str, str]]:
    """Where the limits come from (feature 014, FR-013): method, results, release notes, compliance."""
    tag = latest["tag"]
    rec = reg.record_raw(name, version)
    out = []
    doc = (rec.get("recipe") or {}).get("doc")
    at_tag = doc and subprocess.run(
        ["git", "-C", str(reg.root), "cat-file", "-e", f"{tag}:{doc}"], capture_output=True, check=False
    )
    model = reg.model_raw(name)
    current = f"topics/{model['topic']}/recipes/{name}.md"
    if at_tag and at_tag.returncode == 0:
        out.append({"label": "How it is built and measured", "url": context.gh_blob(doc, tag)})
    elif (reg.root / current).exists():  # the recipe moved after the release (layout changes)
        out.append({"label": "How it is built and measured", "url": context.gh_blob(current)})
    results = f"zoo/models/{name}/results/{version}"
    if (reg.root / results).is_dir():
        out.append({"label": f"Results of v{version}", "url": f"{REPO_URL}/tree/{tag}/{results}"})
    out.append({"label": "Release notes", "url": "#versions"})
    if latest["links"].get("compliance"):
        out.append({"label": f"Compliance record of v{version}", "url": latest["links"]["compliance"]})
    return out


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
    schema = fmt["schema"] if fmt else None
    run_output = None
    if reg.runtime(m) == "mcu":
        exs = examples.device(reg, name, version, schema)
        run_output = examples.run_output(reg, name, version, offline, refresh)
    else:
        exs = examples.load(reg, name, version, schema, offline, refresh)
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
        "usage": sm["usage"],
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
        "python_requirement": python_requirement(),
        "how_to_run": fill(
            m["card"]["how_to_run"], m["repos"]["public"], f"v{version}", quick["text"] if quick else ""
        ).strip(),
        "run_output": run_output,
        "own_data": fill(m["card"].get("own_data", ""), m["repos"]["public"], f"v{version}", "").strip(),
        "quick": quick,
        "examples": exs,
        "fmt": fmt,
        "schema_url": _schema_url(reg, fmt, latest["tag"]) if fmt else None,
        "benchmark": benchmark,
        "checks": checks,
        "cards": [_card(reg, name, version, c, f, notes, page) for c in pitch.get("metric_cards", [])],
        "charts": charts.render(reg, name, version, pitch.get("charts", []), f, page),
        "quality_rows": _metric_rows(reg, name, version, "quality", f, page),
        "performance_rows": _metric_rows(reg, name, version, "performance", f, page),
        # feature 014: release status, short forms of the card, unmet criteria with their values
        "release_status": sm["release_status"],
        "status_sentence": status_sentence(sm["release_status"] or ""),
        "not_for": [res(t, f"not_for{i}") for i, t in enumerate(sm["short"]["not_for"])],
        "limits_short": [res(t, f"limits_short{i}") for i, t in enumerate(sm["short"]["limits_short"])],
        "unmet": facts.unmet_rows(reg, name, version, sm["short"]["unmet_criteria"], f, notes, page),
        "evidence": _evidence(reg, name, version, latest),
        "notes": notes.items,
        "recipe": context.gh_blob(recipe) if (reg.root / recipe).exists() else None,
        "hf": f"{context.HF}/{m['repos']['public']}",
    }


def quickstart(reg: Registry, models: list[dict[str, Any]], offline: bool, refresh: bool) -> str:
    """The text of `docs/quickstart.md` with the install line, program and printed output of the
    named models filled in from the registry (latest published version), so the page cannot drift
    from the model cards. Fields: `{install:<model>}`, `{snippet:<model>}`, `{output:<model>}`."""
    by_name = {sm["name"]: sm for sm in models}
    failures: list[str] = []

    def field(match: re.Match[str]) -> str:
        kind, name = match.groups()
        sm = by_name.get(name)
        if sm is None or not sm["latest"]:
            failures.append(f"Q1 {QUICKSTART} names {name}, which has no published version")
            return match.group(0)
        m, version = sm["m"], sm["latest"]
        mcu = reg.runtime(m) == "mcu"
        if kind == "install":
            return install_line(m, version)
        if kind == "snippet":
            texts = [] if mcu else reg.examples(name)
            first = texts[0][1] if texts else ""
            return fill(m["card"]["how_to_run"], m["repos"]["public"], f"v{version}", first).strip()
        shown = examples.run_output(reg, name, version, offline, refresh) if mcu else None
        return shown or NO_OUTPUT

    body = _QUICKSTART_FIELD.sub(field, (reg.root / QUICKSTART).read_text(encoding="utf-8"))
    if failures:
        raise GateFailed(failures)
    return body


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
    images: bool = True,
) -> dict[str, Any]:
    site = context.load_site_config(reg)
    models = context.site_models(reg)
    env = environment()
    f = facts.Facts()
    failures: list[str] = []
    # feature 015: the roadmap record and its checks RM1-RM8 (contracts/checks.md)
    plan: dict[str, Any] | None = None
    try:
        plan = roadmap.load_and_check(reg)
    except GateFailed as e:
        failures += e.failures
    else:
        for warning in roadmap.warnings(plan):
            say(warning)
    ahead = roadmap.page_context(reg, plan) if plan else {"upcoming": []}
    # feature 016: image records (I1, I2) and motif coverage (M1) gate the build
    records, image_failures = image_records.load_records(reg)
    image_failures += image_records.series_findings(reg, records)
    image_failures += image_records.library_findings(reg, records)
    failures += image_failures
    failures += motifs.coverage(reg, plan)
    failures += motifs.lint_all()
    # feature 019: the pool stays out of the build; only placed records produce files, credits
    # and the set digest (FR-018)
    placed_records = [r for r in records if r.get("placements")]
    placed = image_records.by_placement(placed_records)
    warnings: list[str] = []

    def picture(
        placement: str, topic: str | None, root: str, eager: bool = False
    ) -> dict[str, Any] | None:
        rec, warning = image_records.resolve(placed, placement, topic)
        if warning:
            warnings.append(warning)
        return image_records.view(rec, root, eager) if rec else None

    for sm in models:
        sm["motif"] = motifs.resolve(reg, sm["name"])

    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    with resources.as_file(_static()) as static:
        shutil.copytree(static, out / "assets", dirs_exist_ok=True)
    if placed_records:
        (out / image_records.ASSETS).mkdir(parents=True, exist_ok=True)
        for src, name in image_records.asset_files(placed_records):
            shutil.copyfile(src, out / image_records.ASSETS / name)
    _write(
        out,
        image_records.SET_FILE,
        json.dumps(image_records.set_digest(placed_records), indent=1) + "\n",
    )

    formats = []
    for format_id in schema_doc.format_ids(reg):
        try:
            fmt = schema_doc.output_format(reg, format_id)
        except GateFailed as e:
            failures += e.failures
            continue
        if fmt is None:
            failures.append(f"B5 {format_id}: zoo/formats/{format_id}.yaml is missing")
            continue
        formats.append(fmt)

    share = og.cards(reg, site, models, formats)
    failures += og.card_errors(share)
    renderer = og.renderer_id(reg.root)
    for card in share:
        html = og.card_html(env, card)
        card["html"] = f"{og.CARD_DIR}/{card['slug']}.html"
        _write(out, card["html"], html)
        card["inputs_sha256"] = og.input_hash(html, (out / card["html"]).parent, renderer)
        card["file"] = og.card_file(card, card["inputs_sha256"])
    by_page = {c["page"]: c for c in share}

    common = {"site": site, "has_images": bool(records)}
    pages = 0

    def render(rel: str, template: str, root: str, path: str, **ctx: Any) -> None:
        nonlocal pages
        card = by_page.get(path, by_page[""])
        ctx.setdefault("page_images", [])
        html = env.get_template(template).render(**common, root=root, path=path, card=card, **ctx)
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
        ctx["motif"] = sm["motif"]
        stage = picture(f"model:{sm['name']}", sm["m"]["topic"], "../../")
        ctx["stage"] = stage
        render(
            f"models/{sm['name']}/index.html",
            "model.html.j2",
            "../../",
            f"models/{sm['name']}/",
            p=ctx,
            page_images=[stage] if stage else [],
        )
        rendered.append(sm["name"])
    for fmt in formats:
        render(
            f"formats/{fmt['id']}/index.html",
            "format.html.j2",
            "../../",
            f"formats/{fmt['id']}/",
            fmt=fmt,
        )
    if (reg.root / QUICKSTART).is_file():
        try:
            body = quickstart(reg, models, offline, refresh)
        except GateFailed as e:
            failures += e.failures
        else:
            render("quickstart/index.html", "quickstart.html.j2", "../", "quickstart/", body=body)
    if plan:
        render("roadmap/index.html", "roadmap.html.j2", "../", "roadmap/", r=ahead)
    topics = [t for t in reg.topics() if t["id"] != "sandbox"]
    hero_image = picture("start-hero", None, "", eager=True)
    topic_images = {t["id"]: picture(f"topic:{t['id']}", None, "") for t in topics}
    model_images = {
        sm["name"]: picture(f"model:{sm['name']}", sm["m"]["topic"], "")
        for sm in models
        if sm["name"] in rendered
    }
    render(
        "index.html",
        "start.html.j2",
        "",
        "",
        topics=topics,
        topic_url=topic_url,
        models=models,
        linked=set(rendered),
        upcoming=ahead["upcoming"],
        hero_image=hero_image,
        topic_images=topic_images,
        model_images=model_images,
        page_images=[i for i in [hero_image, *topic_images.values(), *model_images.values()] if i],
    )
    if placed_records:
        render(
            "credits/index.html",
            "credits.html.j2",
            "../",
            "credits/",
            entries=image_records.credits(placed_records, {"start": "../"}),
            licence_label="CC0 1.0",
            thumbs={r["id"]: image_records.view(r, "../") for r in placed_records},
            page_images=[image_records.view(r, "../") for r in placed_records],
        )
    for warning in sorted(set(warnings)):
        say(f"warning: {warning}")
    base = "/" + site["canonical_url"].split("://", 1)[1].split("/", 1)[1]
    render("404.html", "404.html.j2", base, "404.html")
    if failures:
        raise GateFailed(failures)
    f.write(out)
    started = time.monotonic()
    if images:
        og.render(share, out, say)
    seconds = time.monotonic() - started
    manifest = {"renderer": renderer, "cards": [og.manifest_card(c) for c in share]}
    _write(out, og.MANIFEST, json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    drawn = len(share) if images else 0
    in_progress = sum(1 for sm in models if sm["status"] == "in_progress")
    say(
        f"site: {pages} pages, {drawn} images in {seconds:.1f} s, {len(rendered)} models, "
        f"{len(ahead['upcoming'])} coming next"
    )
    return {
        "pages": pages,
        "images": drawn,
        "image_seconds": round(seconds, 1),
        "models": len(rendered),
        "in_progress": in_progress,
        "upcoming": len(ahead["upcoming"]),
    }
