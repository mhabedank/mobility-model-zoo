"""Image records of the website (feature 016, data-model.md): loading and validating
`zoo/site/images/<id>/image.yaml`, the series file, placement resolution with fallbacks, the credits
context and the set digest. Checks I1 and I2 live here; nothing here imports the `images` extra.
"""

from __future__ import annotations

import hashlib
import json
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import jsonschema

from mobility_model_zoo.release.registry import Registry, load_yaml

IMAGES_DIR = "zoo/site/images"
SERIES_DIR = f"{IMAGES_DIR}/series"
ASSETS = "assets/images"
SET_FILE = f"{ASSETS}/set.json"
WIDTHS = (480, 960, 1600)
BYTE_CAPS = {480: 60_000, 960: 140_000, 1600: 300_000}
ACCEPTED_MODEL_LICENCES = {"Apache-2.0", "MIT"}
IPTC_MARKER = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
ALT_SUFFIX = "(AI-generated image)"
DISCLOSURE = "AI-generated"
LICENCE_DEED = "https://creativecommons.org/publicdomain/zero/1.0/"


@cache
def schema() -> dict[str, Any]:
    text = resources.files("mobility_model_zoo.site").joinpath("schemas/image-record.schema.json")
    return json.loads(text.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records_dir(reg: Registry) -> Path:
    return reg.root / IMAGES_DIR


# ---- records (I1) -----------------------------------------------------------------------------
def load_records(reg: Registry) -> tuple[list[dict[str, Any]], list[str]]:
    """Every record with its directory, and the I1 findings. A record with findings is still
    returned (so the build can name it), but the build fails on any finding."""
    root = records_dir(reg)
    records: list[dict[str, Any]] = []
    findings: list[str] = []
    if not root.is_dir():
        return records, findings
    validator = jsonschema.Draft202012Validator(
        schema(), format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    for d in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "series"):
        path = d / "image.yaml"
        if not path.exists():
            findings.append(f"I1 {d.name}: image.yaml is missing")
            continue
        rec = load_yaml(path) or {}
        errors = sorted(validator.iter_errors(rec), key=lambda e: list(e.absolute_path))
        rec["_dir"] = d
        for e in errors:
            where = "/".join(str(p) for p in e.absolute_path) or "(root)"
            findings.append(f"I1 {d.name}: {where}: {e.message}")
        if errors:
            records.append(rec)
            continue
        if rec["id"] != d.name:
            findings.append(f"I1 {d.name}: id {rec['id']} differs from the directory name")
        src = d / rec["source"]["file"]
        if not src.exists():
            findings.append(f"I1 {d.name}: source {rec['source']['file']} is missing")
        elif sha256(src) != rec["source"]["sha256"]:
            findings.append(f"I1 {d.name}: source {rec['source']['file']} does not match its sha256")
        for w in WIDTHS:
            der = rec["derivatives"][str(w)]
            f = d / der["file"]
            if not f.exists():
                findings.append(f"I1 {d.name}: derivative {der['file']} is missing")
                continue
            size = f.stat().st_size
            if size != der["bytes"] or sha256(f) != der["sha256"]:
                findings.append(f"I1 {d.name}: derivative {der['file']} does not match its record")
            if size > BYTE_CAPS[w]:
                findings.append(f"I1 {d.name}: {der['file']} is {size} bytes, more than {BYTE_CAPS[w]}")
        records.append(rec)
    findings += placement_findings(reg, records)
    return records, findings


def placement_findings(reg: Registry, records: list[dict[str, Any]]) -> list[str]:
    from mobility_model_zoo.site import context

    out = []
    topics = {t["id"] for t in reg.topics()}
    shown = {sm["name"] for sm in context.site_models(reg) if sm["status"] != "in_progress"}
    seen: dict[str, str] = {}
    for rec in records:
        for pl in rec.get("placements", []):
            if pl in seen:
                out.append(f"I1 {rec['id']}: placement {pl} is also used by {seen[pl]}")
            seen[pl] = rec["id"]
            kind, _, target = pl.partition(":")
            if kind == "topic" and target not in topics:
                out.append(f"I1 {rec['id']}: unknown topic {target}")
            if kind == "model" and target not in shown:
                out.append(f"I1 {rec['id']}: model {target} is not shown on the site")
    return out


# ---- series (I2) ------------------------------------------------------------------------------
def load_series(reg: Registry, name: str) -> dict[str, Any] | None:
    path = reg.root / SERIES_DIR / f"{name}.yaml"
    if not path.exists():
        return None
    series = load_yaml(path) or {}
    series["style"] = " ".join(str(series.get("style", "")).split())
    series["negative"] = " ".join(str(series.get("negative", "")).split())
    return series


def series_findings(reg: Registry, records: list[dict[str, Any]]) -> list[str]:
    """I2: prompt = subject + style, negative = series negative, model in the series, licence
    accepted."""
    out = []
    cache_: dict[str, dict[str, Any] | None] = {}
    for rec in records:
        g = rec.get("generation") or {}
        name = rec.get("series")
        if name not in cache_:
            cache_[name] = load_series(reg, name) if name else None
        series = cache_[name]
        if series is None:
            out.append(f"I2 {rec['id']}: series {name} has no file under {SERIES_DIR}")
            continue
        subjects = [s for lst in series.get("subjects", {}).values() for s in lst]
        expected = [f"{s}, {series['style']}" for s in subjects]
        if g.get("prompt") not in expected:
            out.append(f"I2 {rec['id']}: prompt is not a subject of series {name} followed by its style")
        models = {m["id"]: m for m in series.get("models", {}).values()}
        if g.get("model") not in models:
            out.append(f"I2 {rec['id']}: model {g.get('model')} is not in series {name}")
        elif g.get("negative_prompt", "") != (
            "" if "true_cfg_scale" not in models[g["model"]] else series["negative"]
        ):
            out.append(f"I2 {rec['id']}: negative prompt differs from the series")
        if g.get("model_licence") not in ACCEPTED_MODEL_LICENCES:
            out.append(f"I2 {rec['id']}: model licence {g.get('model_licence')} is not accepted")
    return out


# ---- placement resolution and page context ----------------------------------------------------
def by_placement(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {pl: rec for rec in records for pl in rec.get("placements", [])}


def resolve(
    placed: dict[str, dict[str, Any]], placement: str, topic: str | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """The record for a placement with the fallback table of data-model.md, and a warning."""
    if placement in placed:
        return placed[placement], None
    if placement.startswith("model:") and topic and f"topic:{topic}" in placed:
        return placed[f"topic:{topic}"], f"no image for {placement}, using topic:{topic}"
    if placement.startswith("model:"):
        return None, f"no image for {placement}, motif only"
    return None, f"no image for {placement}"


def view(rec: dict[str, Any], root: str, eager: bool = False) -> dict[str, Any]:
    """What a template needs to draw one image."""
    files = {w: f"{root}{ASSETS}/{rec['derivatives'][str(w)]['file']}" for w in WIDTHS}
    fx, fy = rec["focal_point"]
    aw, ah = (16, 9) if rec["aspect"] == "16:9" else (3, 2)
    return {
        "id": rec["id"],
        "src": files[960],
        "srcset": ", ".join(f"{files[w]} {w}w" for w in WIDTHS),
        "width": aw * 100,
        "height": ah * 100,
        "alt": rec["alt"],
        "position": f"{round(fx * 100)}% {round(fy * 100)}%",
        "eager": eager,
        "scene": rec["scene"],
    }


def credits(records: list[dict[str, Any]], pages: dict[str, str]) -> list[dict[str, Any]]:
    """Entries of /credits/ (data-model.md "Credits entry"): one per record, in id order."""
    out = []
    for rec in sorted(records, key=lambda r: r["id"]):
        g = rec["generation"]
        used = []
        for pl in rec["placements"]:
            kind, _, target = pl.partition(":")
            if pl == "start-hero":
                used.append({"label": "Start page", "href": pages["start"]})
            elif kind == "topic":
                used.append({"label": f"Topic {target}", "href": pages["start"] + "#topics"})
            elif kind == "model":
                used.append({"label": target, "href": f"{pages['start']}models/{target}/"})
        out.append(
            {
                "id": rec["id"],
                "scene": rec["scene"],
                "disclosure": (
                    f"{DISCLOSURE} with {g['model']} ({g['model_licence']}) "
                    f"on the project's own hardware "
                    f"({g['hardware']}), {g['generated']}"
                ),
                "model": g["model"],
                "model_card": g["model_card"],
                "model_licence": g["model_licence"],
                "generated": g["generated"],
                "hardware": g["hardware"],
                "used": used,
                "licence": rec["licence"],
                "licence_label": "CC0 1.0",
                "licence_url": LICENCE_DEED,
            }
        )
    return out


def set_digest(records: list[dict[str, Any]]) -> dict[str, Any]:
    """`assets/images/set.json`: the image set the deployment approval compares (FR-017)."""
    items = sorted(
        ({"id": r["id"], "sha256": sha256(r["_dir"] / "image.yaml")} for r in records),
        key=lambda i: i["id"],
    )
    h = hashlib.sha256("".join(i["id"] + i["sha256"] for i in items).encode()).hexdigest()
    return {"images": items, "digest": h}


def asset_files(records: list[dict[str, Any]]) -> list[tuple[Path, str]]:
    """(source file, published name) of every derivative."""
    return [
        (r["_dir"] / r["derivatives"][str(w)]["file"], r["derivatives"][str(w)]["file"])
        for r in records
        for w in WIDTHS
    ]
