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
# Feature 019: the library's themes with the spec's coverage table (FR-002), the pool budget
# (FR-016) and where sources may be cached outside git (research R1).
THEMES = (
    "rail",
    "public-road",
    "private-road",
    "active",
    "water",
    "air",
    "infrastructure",
    "workshop",
    "iot",
    "ai",
)
THEME_MINIMUMS = {
    "rail": 10,
    "public-road": 6,
    "private-road": 8,
    "active": 6,
    "water": 5,
    "air": 4,
    "infrastructure": 14,
    "workshop": 8,
    "iot": 10,
    "ai": 10,
}
THEME_CAP = 0.20
LIBRARY_MIN = 100
LIBRARY_MAX_BYTES = 40_000_000
SOURCES_CACHE = ".cache/site/sources"


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
        if "file" in rec["source"]:  # library records keep only the hash (feature 019, FR-015)
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


# ---- series (I2, I8) --------------------------------------------------------------------------
def load_series(reg: Registry, name: str) -> dict[str, Any] | None:
    path = reg.root / SERIES_DIR / f"{name}.yaml"
    if not path.exists():
        return None
    series = load_yaml(path) or {}
    series["style"] = " ".join(str(series.get("style", "")).split())
    series["negative"] = " ".join(str(series.get("negative", "")).split())
    series["negative_history"] = [" ".join(str(n).split()) for n in series.get("negative_history") or []]
    return series


def subjects(series: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """`theme/id` → subject object of the series' `themes` (feature 019, data-model.md). A legacy
    placement-keyed `subjects` map is folded in as `<placement>/<n>` with a prompt only."""
    out: dict[str, dict[str, Any]] = {}
    for theme, lst in (series.get("themes") or {}).items():
        for s in lst or []:
            out[f"{theme}/{s['id']}"] = {"theme": theme, **s}
    for placement, lst in (series.get("subjects") or {}).items():
        for n, prompt in enumerate(lst or [], 1):
            out.setdefault(f"{placement}/{n}", {"theme": placement, "id": str(n), "prompt": prompt})
    return out


def series_findings(reg: Registry, records: list[dict[str, Any]]) -> list[str]:
    """I2: prompt = subject + style, negative = the series' current or a historical negative,
    model in the series, licence accepted. I8: the record's theme/subject exists in the series and
    is used by one record only."""
    out = []
    cache_: dict[str, dict[str, Any] | None] = {}
    used: dict[str, str] = {}
    for rec in records:
        g = rec.get("generation") or {}
        name = rec.get("series")
        if name not in cache_:
            cache_[name] = load_series(reg, name) if name else None
        series = cache_[name]
        if series is None:
            out.append(f"I2 {rec['id']}: series {name} has no file under {SERIES_DIR}")
            continue
        subs = subjects(series)
        expected = [f"{s['prompt']}, {series['style']}" for s in subs.values()]
        if g.get("prompt") not in expected:
            out.append(f"I2 {rec['id']}: prompt is not a subject of series {name} followed by its style")
        models = {m["id"]: m for m in series.get("models", {}).values()}
        if g.get("model") not in models:
            out.append(f"I2 {rec['id']}: model {g.get('model')} is not in series {name}")
        else:
            accepted = (
                {""}
                if "true_cfg_scale" not in models[g["model"]]
                else {series["negative"], *series["negative_history"]}
            )
            if g.get("negative_prompt", "") not in accepted:
                out.append(f"I2 {rec['id']}: negative prompt differs from the series")
        if g.get("model_licence") not in ACCEPTED_MODEL_LICENCES:
            out.append(f"I2 {rec['id']}: model licence {g.get('model_licence')} is not accepted")
        key = f"{rec.get('theme')}/{rec.get('subject')}"
        if key not in subs or key.split("/")[0] not in (series.get("themes") or {}):
            out.append(f"I8 {rec['id']}: theme/subject {key} is not in series {name}")
        elif key in used:
            out.append(f"I8 {rec['id']}: subject {key} is also used by {used[key]}")
        else:
            used[key] = rec["id"]
    return out


# ---- library (I7, L1, L2) ---------------------------------------------------------------------
def coverage(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per theme: count, minimum, share (feature 019, FR-002)."""
    total = len(records)
    out = {}
    for theme in THEMES:
        n = sum(1 for r in records if r.get("theme") == theme)
        out[theme] = {
            "count": n,
            "minimum": THEME_MINIMUMS[theme],
            "share": (n / total) if total else 0.0,
        }
    return out


def coverage_findings(records: list[dict[str, Any]]) -> list[str]:
    """L2: every theme at its minimum, none over the cap, at least LIBRARY_MIN records."""
    out = []
    if len(records) < LIBRARY_MIN:
        out.append(f"L2 library: {len(records)} records, fewer than {LIBRARY_MIN}")
    for theme, c in coverage(records).items():
        if c["count"] < c["minimum"]:
            out.append(f"L2 {theme}: {c['count']} records, fewer than the minimum {c['minimum']}")
        if c["share"] > THEME_CAP:
            out.append(f"L2 {theme}: {c['share']:.0%} of the library, more than {THEME_CAP:.0%}")
    return out


def phash_distance(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def library_findings(reg: Registry, records: list[dict[str, Any]]) -> list[str]:
    """L1: derivative bytes ≤ LIBRARY_MAX_BYTES. I7: no two records within the series'
    duplicate threshold (stored pHash, no image decoding)."""
    out = []
    sizes = sorted(
        ((sum(d["bytes"] for d in r.get("derivatives", {}).values()), r["id"]) for r in records),
        reverse=True,
    )
    total = sum(s for s, _ in sizes)
    if total > LIBRARY_MAX_BYTES:
        heaviest = ", ".join(f"{i} ({s} B)" for s, i in sizes[:3])
        out.append(
            f"L1 library: {total} bytes of derivatives, more than {LIBRARY_MAX_BYTES}; "
            f"heaviest {heaviest}"
        )
    thresholds: dict[str, int] = {}
    hashed = []
    for r in records:
        h = ((r.get("checks") or {}).get("measures") or {}).get("phash")
        if not h:
            continue
        name = r.get("series") or ""
        if name not in thresholds:
            series = load_series(reg, name) if name else None
            thresholds[name] = int((series or {}).get("duplicate_max_bits", 10))
        hashed.append((r["id"], h, thresholds[name]))
    for i, (ida, ha, ta) in enumerate(hashed):
        for idb, hb, _ in hashed[:i]:
            bits = phash_distance(ha, hb)
            if bits <= ta:
                out.append(f"I7 {ida}: near-duplicate of {idb} ({bits} bits)")
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


def credits(
    records: list[dict[str, Any]],
    pages: dict[str, str],
    note_titles: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
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
            elif kind == "note" and target == "series":
                used.append({"label": "Field notes", "href": f"{pages['start']}notes/"})
            elif kind == "note":
                title = (note_titles or {}).get(target, target)
                used.append({"label": title, "href": f"{pages['start']}notes/{target}/"})
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
