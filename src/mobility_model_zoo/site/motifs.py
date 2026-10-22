"""Model motifs (feature 016, research R10 and R11): the one place that maps a model or roadmap
name to its motif, the coverage check M1 and the grammar lint M2.

A motif is a hand-authored SVG in `static/img/motifs/<name>.svg`: a 96-unit grid, one group leaning
`skewX(-8)`, cut caps, strokes of 4.5 or 5 (ink), 8 (greys) and 12 or 16 (the one accent
element), colours only from the tokens, no text. Every model the site shows must have one.

Feature 023: the caps are cut (`square`), not round, so the motifs are printed in the same hand as
the website imagery. `square` rather than `butt` because a square cap covers exactly what the round
one covered, which keeps every motif's footprint and the zero-length runs that draw as dots.
"""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path
from typing import Any

from mobility_model_zoo.release.registry import Registry, load_yaml

MOTIF_DIR = "static/img/motifs"
MAX_BYTES = 1536
STROKE_WIDTHS = {"4.5", "5", "8", "12", "16"}
COLOURS = {"var(--text)", "var(--border-strong)", "var(--mark)"}
_SVG_OPEN = re.compile(r"<svg\b[^>]*\bviewBox=\"([^\"]+)\"", re.S)
_ATTR = re.compile(r"\b(stroke|fill|stroke-width|stroke-linecap|transform)=\"([^\"]*)\"")
_FORBIDDEN = ("<text", "<image", "<linearGradient", "<radialGradient", "<pattern", "<foreignObject")


def motif_dir() -> Any:
    return resources.files("mobility_model_zoo.site").joinpath(MOTIF_DIR)


def files() -> dict[str, Path]:
    """Motif name (without `.svg`) -> file, for every shipped motif."""
    with resources.as_file(motif_dir()) as root:
        return {p.stem: p for p in sorted(Path(root).glob("*.svg")) if not p.stem.endswith("-hero")}


def resolve(reg: Registry | None, name: str) -> str | None:
    """The motif file name of a model or roadmap name: `site.yaml` `motif`, else `<name>.svg`."""
    if reg is not None and name in reg.model_names():
        site = reg.model_dir(name) / "site.yaml"
        if site.exists():
            motif = (load_yaml(site) or {}).get("motif")
            if motif and motif_dir().joinpath(motif).is_file():
                return motif
    return f"{name}.svg" if motif_dir().joinpath(f"{name}.svg").is_file() else None


def resolve_entry(reg: Registry, entry: dict[str, Any]) -> str | None:
    """A roadmap entry: its registered model first, then its id, then its name (renames keep it)."""
    for key in ("model", "id", "name"):
        value = entry.get(key)
        if value:
            found = resolve(reg, value)
            if found:
                return found
    return None


def shown_names(reg: Registry, plan: dict[str, Any] | None) -> list[tuple[str, str]]:
    """(name, where) of every model the site shows: tiles, model pages and open roadmap entries."""
    from mobility_model_zoo.site import context, roadmap

    names: list[tuple[str, str]] = []
    for sm in context.site_models(reg):
        if sm["status"] != "in_progress":
            names.append((sm["name"], "start page tile"))
    if plan:
        for e in roadmap.open_entries(reg, plan):
            names.append((e.get("model") or e["name"], f"roadmap entry {e['id']}"))
    return names


def coverage(reg: Registry, plan: dict[str, Any] | None) -> list[str]:
    """M1: every shown name resolves to a motif."""
    out = []
    seen: set[str] = set()
    for name, where in shown_names(reg, plan):
        if name in seen:
            continue
        seen.add(name)
        if where.startswith("roadmap"):
            entry = next(e for e in roadmap_entries(reg, plan) if (e.get("model") or e["name"]) == name)
            found = resolve_entry(reg, entry)
        else:
            found = resolve(reg, name)
        if not found:
            out.append(f"M1 {name}: no motif ({where}); add {MOTIF_DIR}/{name}.svg")
    return out


def roadmap_entries(reg: Registry, plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    from mobility_model_zoo.site import roadmap

    return roadmap.open_entries(reg, plan) if plan else []


def lint(path: Path) -> list[str]:
    """M2: the motif grammar (contracts/checks.md)."""
    name = path.name
    out = []
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        out.append(f"M2 {name}: {len(data)} bytes, more than {MAX_BYTES}")
    text = data.decode("utf-8", errors="replace")
    m = _SVG_OPEN.search(text)
    if not m or m.group(1).split() != ["0", "0", "96", "96"]:
        out.append(f"M2 {name}: viewBox is not 0 0 96 96")
    for tag in _FORBIDDEN:
        if tag in text:
            out.append(f"M2 {name}: contains {tag}")
    attrs = _ATTR.findall(text)
    if sum(1 for k, v in attrs if k == "transform" and "skewX(-8)" in v) != 1:
        out.append(f"M2 {name}: needs exactly one group with skewX(-8)")
    if not any(k == "stroke-linecap" and v == "square" for k, v in attrs):
        out.append(f"M2 {name}: strokes are not cut-capped (stroke-linecap square)")
    for k, v in attrs:
        if k == "stroke-width" and v not in STROKE_WIDTHS:
            out.append(f"M2 {name}: stroke-width {v} is not one of {sorted(STROKE_WIDTHS)}")
        if k in ("stroke", "fill") and v not in COLOURS | {"none"}:
            out.append(f"M2 {name}: colour {v} is not a token")
    accent = sum(1 for k, v in attrs if k in ("stroke", "fill") and v == "var(--mark)")
    if accent != 1:
        out.append(f"M2 {name}: {accent} accent elements, needs exactly one")
    return out


def lint_all() -> list[str]:
    return [f for p in files().values() for f in lint(p)]
