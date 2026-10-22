"""Field notes: long-form notes in `zoo/notes/*.md` (feature 022, contracts/checks.md N1 and N2).

A note is CommonMark with a YAML front matter block. A line `[diagram:<name>]` on its own is
replaced by the SVG `zoo/notes/diagrams/<name>.svg`, written into the page rather than linked as an
`<img>`, so the drawing inherits the site's colour tokens and follows light and dark mode. A marker
`[ref:<id>]` becomes a numbered link into the reference list built from the front matter; a
citation without an entry, or an entry never cited, stops the build. Raw HTML in the body stays
disabled (markdown.py).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from markupsafe import Markup

from mobility_model_zoo.site.markdown import md

DIR = "zoo/notes"
DIAGRAMS = "diagrams"
SERIES = "series.yaml"
_MARKER = re.compile(r"^\[diagram:([a-z0-9-]+)\]$", re.M)
_CITE = re.compile(r"\[ref:([a-z0-9-]+)\]")
_SLUG = re.compile(r"^\d+-(.+)$")


def _split(raw: str, where: Path) -> tuple[dict[str, Any], str]:
    if not raw.startswith("---\n"):
        raise ValueError(f"{where}: a post starts with a YAML front matter block")
    _, front, body = raw.split("---\n", 2)
    return yaml.safe_load(front) or {}, body.lstrip("\n")


def _diagram(root: Path, name: str, caption: str | None, where: Path) -> str:
    path = root / DIR / DIAGRAMS / f"{name}.svg"
    if not path.is_file():
        raise ValueError(f"{where.name}: no drawing {name!r} in {DIR}/{DIAGRAMS}/")
    svg = path.read_text(encoding="utf-8").strip()
    cap = f'<figcaption class="cap">{caption}</figcaption>' if caption else ""
    return f'<figure class="diagram-fig" data-diagram="{name}">{svg}{cap}</figure>'


def _cites(html: str, order: list[str]) -> str:
    """`[ref:id]` becomes a superscript link to the reference list; numbers follow first use."""

    def one(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in order:
            order.append(key)
        n = order.index(key) + 1
        return (
            f'<sup class="cite"><a id="cite-{key}" href="#ref-{key}" '
            f'aria-label="Reference {n}">{n}</a></sup>'
        )

    return _CITE.sub(one, html)


def body_html(
    root: Path, body: str, captions: dict[str, str], order: list[str], where: Path
) -> Markup:
    """The post body as HTML: diagram lines inlined, `[ref:…]` turned into numbered links."""
    out: list[str] = []
    at = 0
    for m in _MARKER.finditer(body):
        out.append(_cites(str(md(body[at : m.start()])), order))
        out.append(_diagram(root, m.group(1), captions.get(m.group(1)), where))
        at = m.end()
    out.append(_cites(str(md(body[at:])), order))
    return Markup("".join(out))  # noqa: S704 - the parts are escaped markdown and own SVG files


def series(root: Path, found: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The series overview: every planned part, with the published ones linked."""
    path = root / DIR / SERIES
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    by_slug = {p["slug"]: p for p in found}
    for part in data.get("parts") or []:
        post = by_slug.get(part.get("slug") or "")
        part["published"] = post is not None
        part["href"] = post["path"] if post else None
        part["date"] = post["date"] if post else None
    return data


def posts(root: Path) -> list[dict[str, Any]]:
    """Every note, newest first. Empty when the project has no `zoo/notes/`."""
    folder = root / DIR
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.glob("*.md")):
        meta, body = _split(path.read_text(encoding="utf-8"), path)
        match = _SLUG.match(path.stem)
        meta["slug"] = match.group(1) if match else path.stem
        meta["path"] = f"notes/{meta['slug']}/"
        order: list[str] = []
        meta["body"] = body_html(root, body, meta.get("diagrams") or {}, order, path)
        refs = {r["id"]: r for r in meta.get("references") or []}
        missing = [k for k in order if k not in refs]
        unused = [k for k in refs if k not in order]
        if missing or unused:
            raise ValueError(
                f"{path.name}: references cited but not listed {missing}, "
                f"listed but not cited {unused}"
            )
        meta["references"] = [dict(refs[k], number=i + 1) for i, k in enumerate(order)]
        meta["date"] = str(meta.get("date", ""))
        found.append(meta)
    return sorted(found, key=lambda p: (p["date"], p.get("part", 0)), reverse=True)
