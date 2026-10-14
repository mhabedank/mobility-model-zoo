"""`zoo site check`: the checks that block publication of the website (contracts/checks.md).

Static checks read the built files; the browser checks (A1-A4, P2, S2) are in `a11y.py` and run
with `--a11y`. Every finding is printed as `<check id> <page> <detail>`; any finding fails.
"""

from __future__ import annotations

import json
import re
import struct
from collections.abc import Callable, Iterable
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

from mobility_model_zoo.compliance.release_checks import BRAND, FUNDING
from mobility_model_zoo.release.card import num
from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry, load_yaml
from mobility_model_zoo.site import images, motifs, og
from mobility_model_zoo.site.facts import NUMBER, literal_numbers, target_key

PREFIX = "/mobility-model-zoo/"
RESOURCE_ATTRS = {
    ("img", "src"),
    ("img", "srcset"),
    ("script", "src"),
    ("link", "href"),
    ("source", "src"),
    ("source", "srcset"),
    ("video", "src"),
    ("video", "poster"),
    ("audio", "src"),
    ("iframe", "src"),
    ("embed", "src"),
    ("object", "data"),
    ("image", "href"),
    ("use", "href"),
}
CSS_URL = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)|@import\s+['"]([^'"]+)['"]""")
# Advertising wording beyond the repository-wide markers of the compliance harness (FUNDING).
ADVERTISING = re.compile(r"\b(sponsor|donate|donation|hire us|book a call)\b", re.I)
MAX_PAGE_BYTES, MAX_TOTAL_BYTES = 150_000, 300_000


class Finding(tuple):
    def __new__(cls, check: str, page: str, detail: str):
        return super().__new__(cls, (check, page, detail))

    def line(self) -> str:
        return f"{self[0]} {self[1]} {self[2]}"


# ---- parsing ----------------------------------------------------------------------------------
class Page(HTMLParser):
    """Links, resource references, ids, text nodes and footer links of one HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.resources: list[str] = []
        self.ids: set[str] = set()
        self.text: list[str] = []
        self.footer_links: list[str] = []
        self.footer_link_text: list[str] = []
        self.scripts: list[dict[str, str | None]] = []
        self.images: list[dict[str, str | None]] = []  # feature 016: img[data-image]
        self.figure_text: list[str] = []  # text nodes inside figures that hold an image (X1)
        self._skip = 0
        self._footer = 0
        self._figure = 0
        self._figure_text: list[str] = []
        self._figure_has_image = False
        self._in_footer_a = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "img" and "data-image" in a:
            self.images.append(a)
            if self._figure:
                self._figure_has_image = True
        if tag == "figure":
            self._figure += 1
            self._figure_text, self._figure_has_image = [], False
        if tag == "a" and self._footer:
            self._in_footer_a += 1
        if tag in ("script", "style"):
            self._skip += 1
        if tag == "script":
            self.scripts.append(a)
        if tag == "footer":
            self._footer += 1
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if self._footer:
                self.footer_links.append(a["href"])
        for key, value in attrs:
            if (tag, key) in RESOURCE_ATTRS and value:
                if key == "srcset":
                    self.resources += [part.strip().split(" ")[0] for part in value.split(",")]
                elif not (tag == "link" and a.get("rel") in ("canonical",)):
                    self.resources.append(value)
            if key == "style" and value:
                self.resources += [m[0] or m[1] for m in CSS_URL.findall(value)]

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        if tag == "footer" and self._footer:
            self._footer -= 1
        if tag == "figure" and self._figure:
            self._figure -= 1
            if self._figure_has_image:
                self.figure_text += self._figure_text
            self._figure_text, self._figure_has_image = [], False
        if tag == "a" and self._in_footer_a:
            self._in_footer_a -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.text.append(data)
            if self._figure:
                self._figure_text.append(data.strip())
            if self._in_footer_a:
                self.footer_link_text.append(data.strip())


def parse(path: Path) -> Page:
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    return page


def pages(out: Path) -> list[Path]:
    return sorted(p for p in out.rglob("*.html") if "_build" not in p.parts)


def card_pages(out: Path) -> list[Path]:
    """The preview image pages (feature 012); P1 and P3 cover them too."""
    return sorted((out / og.CARD_DIR).glob("*.html"))


def rel(out: Path, path: Path) -> str:
    return str(path.relative_to(out))


def external(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.scheme not in ("data",)) or url.startswith("//")


def resolve_local(out: Path, page: Path, url: str) -> tuple[Path, str]:
    """The file and fragment an internal URL points to."""
    target, fragment = urldefrag(url)
    target = unquote(target)
    if target.startswith(PREFIX):
        base = out / target[len(PREFIX) :]
    elif target.startswith("/"):
        base = out / target.lstrip("/")
    elif target:
        base = page.parent / target
    else:
        base = page
    if base.is_dir() or target.endswith("/") or not target and base == page.parent:
        base = base / "index.html"
    return base.resolve(), fragment


# ---- checks -----------------------------------------------------------------------------------
def check_facts(reg: Registry, out: Path) -> Iterable[Finding]:
    """F1: every rendered fact equals its source value, formatted as on the card."""
    path = out / "_build" / "facts.json"
    if not path.exists():
        yield Finding("F1", "_build/facts.json", "missing; run zoo site build")
        return
    cache: dict[str, dict[str, object]] = {}
    for row in json.loads(path.read_text(encoding="utf-8")):
        source = reg.root / row["source"]
        if not source.exists():
            yield Finding("F1", row["page"], f"{row['key']}: source {row['source']} does not exist")
            continue
        if row["source"] not in cache:
            if source.name == "model.yaml":  # targets of unmet criteria (feature 014)
                items = ((load_yaml(source) or {}).get("card") or {}).get("unmet_criteria") or []
                cache[row["source"]] = {
                    target_key(i): it["target"]["value"]
                    for i, it in enumerate(items)
                    if it.get("target")
                }
            else:
                data = json.loads(source.read_text(encoding="utf-8"))
                cache[row["source"]] = {m["name"]: m["value"] for m in data["metrics"]}
        values = cache[row["source"]]
        if row["metric"] not in values:
            yield Finding("F1", row["page"], f"{row['key']}: {row['metric']} not in {row['source']}")
        elif num(values[row["metric"]]) != row["value"]:
            yield Finding(
                "F1",
                row["page"],
                f"{row['key']}: shows {row['value']}, source has {num(values[row['metric']])}",
            )


def _prose(pitch: dict) -> Iterable[tuple[str, str]]:
    for key in ("tagline", "share_line", "audience", "hardware_note"):
        if pitch.get(key):
            yield key, pitch[key]
    for i, d in enumerate(pitch.get("differentiators", [])):
        yield f"differentiators[{i}]", f"{d['title']} {d['text']}"
    for i, c in enumerate(pitch.get("metric_cards", [])):
        yield f"metric_cards[{i}]", " ".join([c["label"], c.get("compare_label", "")])


def _card_prose(card: dict) -> Iterable[tuple[str, str]]:
    for key in ("not_for", "limits_short"):
        for i, text in enumerate(card.get(key) or []):
            yield f"{key}[{i}]", text
    for i, item in enumerate(card.get("unmet_criteria") or []):
        for field in ("criterion", "note"):
            if item.get(field):
                yield f"unmet_criteria[{i}].{field}", item[field]


class _TemplateText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.text: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs) -> None:
        if tag in ("style", "script", "svg"):
            self._skip += 1

    def handle_endtag(self, tag) -> None:
        if tag in ("style", "script", "svg") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.text.append(data)


def template_text(source: str) -> str:
    """Literal text nodes of a Jinja template: expressions, tags, attributes and SVG removed."""
    stripped = re.sub(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", " ", source, flags=re.S)
    parser = _TemplateText()
    parser.feed(stripped)
    return " ".join(parser.text)


def check_literal_numbers(reg: Registry) -> Iterable[Finding]:
    """F2: numbers only as placeholders in site.yaml prose, none in template text."""
    for name in reg.model_names():
        path = reg.model_dir(name) / "site.yaml"
        if not path.exists():
            continue
        for key, text in _prose(load_yaml(path) or {}):
            for n in literal_numbers(text):
                yield Finding("F2", f"zoo/models/{name}/site.yaml", f"{key}: literal number {n!r}")
    for name in reg.model_names():  # feature 014: short forms of the card
        card = reg.model_raw(name).get("card") or {}
        for key, text in _card_prose(card):
            for n in literal_numbers(text):
                yield Finding("F2", f"zoo/models/{name}/model.yaml", f"card.{key}: literal number {n!r}")
    from importlib import resources

    base = resources.files("mobility_model_zoo.site").joinpath("templates")
    for tpl in sorted(Path(str(base)).rglob("*.j2")):
        for n in literal_numbers(template_text(tpl.read_text(encoding="utf-8"))):
            yield Finding("F2", f"templates/{tpl.relative_to(Path(str(base)))}", f"literal number {n!r}")


def check_wording(out: Path) -> Iterable[Finding]:
    """F3: agreement with reference models is never called accuracy."""
    for path in pages(out):
        page = parse(path)
        for chunk in page.text:
            for m in re.finditer(r"\baccuracy\b", chunk, re.I):
                window = chunk[max(0, m.start() - 12) : m.start()].lower()
                if "not " in window or "no " in window:
                    continue  # "not accuracy" is the honest statement itself
                yield Finding(
                    "F3",
                    rel(out, path),
                    f"uses 'accuracy': …{chunk[max(0, m.start() - 40) : m.end() + 20]}…",
                )


def check_card_parity(reg: Registry, out: Path) -> Iterable[Finding]:
    """F4: every number the site shows for a model is also printed on its model card."""
    from mobility_model_zoo.release import card as cards
    from mobility_model_zoo.site import context

    path = out / "_build" / "facts.json"
    if not path.exists():
        return
    rows = json.loads(path.read_text(encoding="utf-8"))
    for sm in context.site_models(reg):
        if sm["status"] == "in_progress":
            continue
        page = f"models/{sm['name']}/"
        try:
            card = cards.render(
                cards.CardInput(
                    reg,
                    sm["name"],
                    sm["latest"],
                    model=cards.model_at_tag(reg, sm["name"], sm["latest"]),
                )
            )
        except Exception as e:  # a registry without compliance data cannot render the full card
            yield Finding("F4", page, f"card could not be rendered: {type(e).__name__}: {e}")
            continue
        on_card = {m.group(0) for m in NUMBER.finditer(card)}
        for row in rows:
            if row["page"] == page and row["value"] not in on_card:
                yield Finding("F4", page, f"{row['key']} = {row['value']} is not on the model card")


def check_links(out: Path) -> Iterable[Finding]:
    """L1: every internal link, resource and anchor resolves inside the site."""
    parsed = {path.resolve(): parse(path) for path in pages(out)}
    for path in pages(out):
        page = parsed[path.resolve()]
        for url in page.links + page.resources:
            if external(url) or url.startswith(("mailto:", "data:")):
                continue
            target, fragment = resolve_local(out, path, url)
            if not target.exists():
                yield Finding("L1", rel(out, path), f"{url} -> {target} does not exist")
            elif fragment and target.suffix == ".html":
                ids = parsed[target].ids if target in parsed else parse(target).ids
                if fragment not in ids:
                    yield Finding("L1", rel(out, path), f"{url}: no element with id {fragment!r}")


def check_external_links(out: Path, root: Path | None = None) -> Iterable[Finding]:
    """L2: external links answer (HEAD with a GET fallback, two retries). Links to files of this
    repository on main are checked in the checkout instead: a pull request may add the file."""
    import httpx

    from mobility_model_zoo.release.card import REPO_URL

    on_main = f"{REPO_URL}/blob/main/"
    urls: dict[str, str] = {}
    for path in pages(out):
        for url in parse(path).links:
            target = urldefrag(url)[0]
            if root is not None and target.startswith(on_main):
                if not (root / unquote(target[len(on_main) :])).exists():
                    yield Finding("L2", rel(out, path), f"{target}: no such file in the repository")
            elif external(url):
                urls.setdefault(target, rel(out, path))
    with httpx.Client(
        follow_redirects=True, timeout=20, headers={"User-Agent": "mobility-model-zoo-site-check"}
    ) as client:
        for url, page in sorted(urls.items()):
            status = None
            for _ in range(3):
                try:
                    status = client.head(url).status_code
                    if status in (403, 405):
                        status = client.get(url).status_code
                    if status < 500:
                        break
                except httpx.HTTPError as e:
                    status = f"{type(e).__name__}"
            if not isinstance(status, int) or status >= 400:
                yield Finding("L2", page, f"{url} answered {status}")


def check_legal(site: dict, out: Path, root: Path | None = None) -> Iterable[Finding]:
    """L3: legal links on every page; licence, usage class, limits and AI Act note on every model
    page; the imprint is the one named in the compliance register."""
    legal = site["legal"]
    controller = root / "compliance" / "controller.yaml" if root else None
    if controller and controller.exists():
        imprint = (load_yaml(controller) or {}).get("imprint_url")
        if imprint and imprint != legal["imprint"]:
            yield Finding(
                "L3",
                "zoo/site.yaml",
                f"imprint {legal['imprint']} is not {imprint} (compliance/controller.yaml)",
            )
    for path in pages(out):
        page = parse(path)
        for key in ("imprint", "privacy", "copyright"):
            if legal[key] not in page.footer_links:
                yield Finding("L3", rel(out, path), f"footer has no link to the {key} page")
        if path.parent.parent.name == "models":
            text = path.read_text(encoding="utf-8")
            for needle, what in (
                ('id="limits"', "limitations section"),
                ("ai-act.md", "AI Act note"),
                ("Licence", "licence"),
                ('<th scope="row">Usage</th>', "usage class"),
            ):
                if needle not in text:
                    yield Finding("L3", rel(out, path), f"no {what}")


def check_resources(out: Path) -> Iterable[Finding]:
    """P1: no resource is loaded from another host (navigation links are fine)."""
    for path in pages(out) + card_pages(out):
        for url in parse(path).resources:
            if external(url):
                yield Finding("P1", rel(out, path), f"loads {url}")
    for css in sorted(out.rglob("*.css")):
        for m in CSS_URL.findall(css.read_text(encoding="utf-8")):
            url = m[0] or m[1]
            if external(url):
                yield Finding("P1", rel(out, css), f"loads {url}")


def check_branding(site: dict, out: Path) -> Iterable[Finding]:
    """P3: no company branding (the imprint link is the one allowed mention), no advertising
    (the compliance harness markers BRAND and FUNDING plus ADVERTISING)."""
    for path in pages(out) + card_pages(out):
        html = path.read_text(encoding="utf-8")
        mentions = len(BRAND.findall(html))
        allowed = html.count(site["legal"]["imprint"])
        if mentions > allowed:
            yield Finding("P3", rel(out, path), "names the consulting brand outside the imprint link")
        page = parse(path)
        for chunk in page.text:
            m = ADVERTISING.search(chunk) or FUNDING.search(chunk)
            if m:
                yield Finding("P3", rel(out, path), f"advertising wording {m.group(0)!r}")


def check_size(out: Path) -> Iterable[Finding]:
    """S1: page weight and deferred scripts."""
    total = sum(
        p.stat().st_size
        for p in out.rglob("*")
        if p.is_file()
        and "_build" not in p.parts
        and p.suffix != ".woff2"
        and p.name != "OFL.txt"
        and not rel(out, p).startswith(og.OG_DIR + "/")  # loaded by link previews, not visitors (O1)
        and not rel(out, p).startswith(
            images.ASSETS + "/"
        )  # one page loads only its own (feature 016, S4)
    )
    if total > MAX_TOTAL_BYTES:
        yield Finding("S1", "(site)", f"{total} bytes without fonts, more than {MAX_TOTAL_BYTES}")
    for path in pages(out):
        size = path.stat().st_size
        if size > MAX_PAGE_BYTES:
            yield Finding("S1", rel(out, path), f"{size} bytes, more than {MAX_PAGE_BYTES}")
        for script in parse(path).scripts:
            if script.get("src") and "defer" not in script:
                yield Finding("S1", rel(out, path), f"script {script['src']} is not deferred")


# ---- preview images (feature 012, specs/012-social-preview-images/contracts/checks.md) ---------
class _Meta(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        key = a.get("property") or a.get("name")
        if tag == "meta" and key and key.startswith(("og:image", "twitter:")):
            self.meta[key] = a.get("content") or ""


def og_meta(path: Path) -> dict[str, str]:
    parser = _Meta()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.meta


def png_size(path: Path) -> tuple[int, int] | None:
    """Width and height from the IHDR chunk, or None if the file is not a PNG."""
    head = path.read_bytes()[:24]
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def og_manifest(out: Path) -> dict | None:
    path = out / og.MANIFEST
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def page_file(out: Path, page: str) -> Path:
    return out / page / "index.html"


def check_og_files(site: dict, out: Path) -> Iterable[Finding]:
    """O1: metadata on every shareable page; the image exists, is a 1200 x 630 PNG, small enough."""
    manifest = og_manifest(out)
    if manifest is None:
        yield Finding("O1", og.MANIFEST, "missing; run zoo site build")
        return
    base = site["canonical_url"]
    expected = {
        "og:image:type": "image/png",
        "og:image:width": str(og.WIDTH),
        "og:image:height": str(og.HEIGHT),
        "twitter:card": "summary_large_image",
    }
    targets = [(c["page"], page_file(out, c["page"]), c) for c in manifest["cards"]]
    zoo = next((c for c in manifest["cards"] if c["kind"] == "zoo"), None)
    if zoo and (out / "404.html").exists():
        targets.append(("404.html", out / "404.html", zoo))
    for page, path, card in targets:
        name = page or "index.html"
        if not path.exists():
            yield Finding("O1", name, "page of this preview image does not exist")
            continue
        meta = og_meta(path)
        for key in ("og:image", "og:image:alt", "twitter:image", "twitter:image:alt", *expected):
            if not meta.get(key):
                yield Finding("O1", name, f"no {key} tag")
        for key, value in expected.items():
            if meta.get(key) and meta[key] != value:
                yield Finding("O1", name, f"{key} is {meta[key]!r}, not {value!r}")
        for key in ("og:image", "twitter:image"):
            if meta.get(key) and meta[key] != base + card["file"]:
                yield Finding("O1", name, f"{key} is {meta[key]}, not {base + card['file']}")
    for card in manifest["cards"]:
        name, image = card["page"] or "index.html", out / card["file"]
        if not image.exists():
            yield Finding("O1", name, f"{card['file']} does not exist (built with --no-images?)")
            continue
        size = png_size(image)
        if size is None:
            yield Finding("O1", name, f"{card['file']} is not a PNG")
        elif size != (og.WIDTH, og.HEIGHT):
            yield Finding(
                "O1", name, f"{card['file']} is {size[0]} x {size[1]}, not {og.WIDTH} x {og.HEIGHT}"
            )
        if image.stat().st_size > og.MAX_BYTES:
            yield Finding(
                "O1", name, f"{card['file']} has {image.stat().st_size} bytes, more than {og.MAX_BYTES}"
            )


def check_og_layout(out: Path) -> Iterable[Finding]:
    """O2: no text overflows, all text inside the margins, mark and title inside the centre square."""
    manifest = og_manifest(out) or {"cards": []}
    lo, hi = og.SAFE_X
    for card in manifest["cards"]:
        name, layout = card["page"] or "index.html", card.get("layout")
        if not layout:
            continue  # O1 reports the missing image
        for block in layout["overflow"]:
            yield Finding("O2", name, f"{block} overflows its box")
        for block, box in layout["boxes"].items():
            if not box:
                continue
            x, y, w, h = box
            if (
                x < og.MARGIN - 0.5
                or y < og.MARGIN - 0.5
                or x + w > og.WIDTH - og.MARGIN + 0.5
                or y + h > og.HEIGHT - og.MARGIN + 0.5
            ):
                yield Finding("O2", name, f"{block} lies outside the {og.MARGIN} px margins")
            if block in ("mark", "title") and (x < lo - 0.5 or x + w > hi + 0.5):
                yield Finding("O2", name, f"{block} lies outside the centre square x {lo}-{hi}")


def check_og_parity(reg: Registry, out: Path) -> Iterable[Finding]:
    """O4: title, line and labels on the image are the registry's; alt texts match the manifest."""
    manifest = og_manifest(out) or {"cards": []}
    built = {c["page"]: c for c in manifest["cards"]}
    for card in og.site_cards(reg):
        name = card["page"] or "index.html"
        got = built.get(card["page"])
        if got is None:
            yield Finding("O4", name, "has no preview image")
            continue
        for key in ("title", "line", "labels", "alt"):
            if got[key] != card[key]:
                yield Finding("O4", name, f"{key} is {got[key]!r}, the registry says {card[key]!r}")
        path = page_file(out, card["page"])
        if path.exists():
            meta = og_meta(path)
            for key in ("og:image:alt", "twitter:image:alt"):
                if meta.get(key) and meta[key] != got["alt"]:
                    yield Finding("O4", name, f"{key} differs from the image's alt text")
    for page in set(built) - {c["page"] for c in og.site_cards(reg)}:
        yield Finding("O4", page or "index.html", "preview image for a page that should not have one")


def check_og_hash(reg: Registry, out: Path) -> Iterable[Finding]:
    """O5: each file name carries the hash of what is drawn; no image without a page."""
    manifest = og_manifest(out) or {"cards": []}
    renderer = og.renderer_id(reg.root)
    named = set()
    for card in manifest["cards"]:
        name = card["page"] or "index.html"
        html_path = out / card["html"]
        named.add(card["file"])
        if not html_path.exists():
            yield Finding("O5", name, f"{card['html']} is missing")
            continue
        digest = og.input_hash(html_path.read_text(encoding="utf-8"), html_path.parent, renderer)
        if og.card_file(card | {"slug": Path(card["html"]).stem}, digest) != card["file"]:
            yield Finding(
                "O5", name, f"{card['file']} does not carry the hash of its inputs ({digest[:12]})"
            )
    folder = out / og.OG_DIR
    for image in sorted(folder.glob("*")) if folder.exists() else []:
        if rel(out, image) not in named:
            yield Finding("O5", rel(out, image), "no page uses this image")


def check_language(out: Path) -> Iterable[Finding]:
    """FR-023: every page is marked as English."""
    for path in pages(out):
        if '<html lang="en">' not in path.read_text(encoding="utf-8"):
            yield Finding("E1", rel(out, path), 'missing <html lang="en">')


def check_roadmap_pages(reg: Registry, out: Path) -> Iterable[Finding]:
    """RM9 (feature 015): the roadmap page and the start-page cards show exactly the open entries of
    the record, in record order, and the models heading counts what is shown."""
    from mobility_model_zoo.site import roadmap

    try:
        record = roadmap.load(reg)
    except GateFailed as e:
        yield from (Finding("RM9", "zoo/roadmap/roadmap.yaml", f) for f in e.failures)
        return
    ctx = roadmap.page_context(reg, record)
    page = out / "roadmap" / "index.html"
    if not page.exists():
        yield Finding("RM9", "roadmap/index.html", "missing")
        return
    html = page.read_text(encoding="utf-8")
    for h in ctx["horizons"]:
        start = html.find(f'id="h-{h["id"]}"')
        if start < 0:
            yield Finding("RM9", "roadmap/index.html", f"no section for {h['label']}")
            continue
        end = html.find('<section class="horizon"', start + 1)
        shown = re.findall(
            r'<li class="entry [^"]*" id="([^"]+)"', html[start : end if end > 0 else None]
        )
        expected = [e["id"] for e in h["entries"]]
        if shown != expected:
            yield Finding(
                "RM9", "roadmap/index.html", f"{h['label']} shows {shown}, the record has {expected}"
            )
    start_page = (out / "index.html").read_text(encoding="utf-8")
    cards = re.findall(r'<a class="mini" href="roadmap/#([^"]+)"', start_page)
    expected = [e["id"] for e in ctx["upcoming"]]
    if cards != expected:
        yield Finding("RM9", "index.html", f"Coming next shows {cards}, the record has {expected}")
    tiles = len(re.findall(r'<(?:a|div) class="tile"', start_page))
    heading = re.search(r'id="m-h">(\d+) published · (\d+) coming next\.<', start_page)
    if not heading:
        yield Finding("RM9", "index.html", "models heading does not count published and coming next")
    elif (int(heading.group(1)), int(heading.group(2))) != (tiles, len(cards)):
        yield Finding(
            "RM9",
            "index.html",
            f"heading says {heading.group(1)} published and {heading.group(2)} coming next, "
            f"the page shows {tiles} tiles and {len(cards)} cards",
        )


# ---- feature 016: motifs (M1, M2) and images (I1-I3, C1, X1) ----------------------------------
IMAGE_PAGES = re.compile(r"^(index\.html|models/[^/]+/index\.html|credits/index\.html)$")


def check_motifs(reg: Registry) -> Iterable[Finding]:
    """M1 coverage and M2 grammar, as the build runs them."""
    from mobility_model_zoo.site import roadmap

    try:
        plan = roadmap.load_and_check(reg)
    except GateFailed:
        plan = None
    for line in motifs.coverage(reg, plan) + motifs.lint_all():
        check_id, _, rest = line.partition(" ")
        name, _, detail = rest.partition(": ")
        yield Finding(check_id, name, detail)


def check_image_records(reg: Registry) -> Iterable[Finding]:
    """I1 records, files and placements; I2 recipe against the series."""
    records, findings = images.load_records(reg)
    for line in findings + images.series_findings(reg, records):
        check_id, _, rest = line.partition(" ")
        name, _, detail = rest.partition(": ")
        yield Finding(check_id, name, detail)


def check_image_markup(reg: Registry, out: Path) -> Iterable[Finding]:
    """I3: every img[data-image] has a record, size, alt, srcset and lazy loading; images only on the
    start, model and credits pages (FR-007); no orphan files; every derivative carries the marker."""
    records, _ = images.load_records(reg)
    by_id = {r["id"]: r for r in records}
    used: set[str] = set()
    for path in pages(out):
        page = parse(path)
        where = rel(out, path)
        if page.images and not IMAGE_PAGES.match(where):
            yield Finding("I3", where, "shows images, but only the start, model and credits pages may")
        for img in page.images:
            rec = by_id.get(img.get("data-image") or "")
            if rec is None:
                yield Finding("I3", where, f"image {img.get('data-image')} has no record")
                continue
            for attr in ("width", "height", "srcset", "alt"):
                if not img.get(attr):
                    yield Finding("I3", where, f"image {rec['id']} has no {attr}")
            if img.get("alt") and img["alt"] != rec["alt"]:
                yield Finding("I3", where, f"image {rec['id']}: alt differs from the record")
            if img.get("fetchpriority") != "high" and img.get("loading") != "lazy":
                yield Finding("I3", where, f"image {rec['id']} is neither lazy nor the hero")
            for ref in [img.get("src") or ""] + [
                p.strip().split(" ")[0] for p in (img.get("srcset") or "").split(",")
            ]:
                if ref:
                    used.add(Path(ref).name)
    published = sorted((out / images.ASSETS).glob("*.webp")) if (out / images.ASSETS).is_dir() else []
    known = {name for _, name in images.asset_files(records)}
    for f in published:
        if f.name not in known:
            yield Finding("I3", rel(out, f), "orphan file: no record uses it")
        elif not _has_marker(f):
            yield Finding("I3", rel(out, f), "no IPTC trainedAlgorithmicMedia marker")


def _has_marker(path: Path) -> bool:
    """The XMP packet of a WebP is plain text inside the file; no decoder needed."""
    return images.IPTC_MARKER.encode() in path.read_bytes()


def check_credits(reg: Registry, out: Path) -> Iterable[Finding]:
    """C1: the credits page lists every record with its disclosure; every page with images links it
    from the footer with the words "AI-generated"."""
    records, _ = images.load_records(reg)
    if not records:
        return
    credits = out / "credits" / "index.html"
    if not credits.exists():
        yield Finding("C1", "credits/index.html", "missing")
        return
    from html import unescape

    html = unescape(credits.read_text(encoding="utf-8"))
    for r in records:
        g = r["generation"]
        for needle, what in (
            (f'id="{r["id"]}"', "entry"),
            (r["scene"], "scene"),
            (g["model"], "model"),
            (g["model_licence"], "model licence"),
            (g["generated"], "date"),
            (g["hardware"], "hardware class"),
        ):
            if needle not in html:
                yield Finding("C1", "credits/index.html", f"{r['id']}: no {what}")
    if images.DISCLOSURE not in html:
        yield Finding("C1", "credits/index.html", "does not say AI-generated")
    for path in pages(out):
        page = parse(path)
        if not page.images:
            continue
        where = rel(out, path)
        target = resolve_local(out, path, "credits/")[0] if where == "index.html" else None
        footer_ok = any("credits/" in href for href in page.footer_links)
        if not footer_ok:
            yield Finding("C1", where, "no footer link to the image credits")
        if not any("AI-generated" in t for t in page.footer_link_text):
            yield Finding("C1", where, 'footer link does not say "AI-generated"')
        del target


def check_text_on_images(out: Path) -> Iterable[Finding]:
    """X1: no text inside a figure that holds an image (text never sits on an image, FR-004)."""
    for path in pages(out):
        page = parse(path)
        if page.images and page.figure_text:
            yield Finding(
                "X1", rel(out, path), f"text inside an image figure: {page.figure_text[0][:40]!r}"
            )


def run_checks(
    reg: Registry,
    out: Path,
    a11y: bool = False,
    only: set[str] | None = None,
    offline: bool = False,
    say: Callable[[str], None] = print,
) -> list[Finding]:
    from mobility_model_zoo.site import context, depth

    if not (out / "index.html").exists():
        raise GateFailed([f"no site in {out}; run zoo site build first"])
    site = context.load_site_config(reg)
    checks: list[tuple[str, Callable[[], Iterable[Finding]]]] = [
        ("F1", lambda: check_facts(reg, out)),
        ("F2", lambda: check_literal_numbers(reg)),
        ("F3", lambda: check_wording(out)),
        ("F4", lambda: check_card_parity(reg, out)),
        ("L1", lambda: check_links(out)),
        ("L3", lambda: check_legal(site, out, reg.root)),
        ("P1", lambda: check_resources(out)),
        ("P3", lambda: check_branding(site, out)),
        ("S1", lambda: check_size(out)),
        ("E1", lambda: check_language(out)),
        ("O1", lambda: check_og_files(site, out)),
        ("O2", lambda: check_og_layout(out)),
        ("O4", lambda: check_og_parity(reg, out)),
        ("O5", lambda: check_og_hash(reg, out)),
        ("D4", lambda: depth.check_overview(reg, out)),
        ("D3", lambda: depth.check_quality(reg, out)),
        ("D1", lambda: depth.check_short_forms(reg)),
        ("D3", lambda: depth.check_limits(reg, out)),
        ("D3", lambda: depth.check_code_order(reg, out)),
        ("D5", lambda: depth.check_order(reg, out)),
        ("D2", lambda: depth.check_words_before_quality(reg, out)),
        ("RM9", lambda: check_roadmap_pages(reg, out)),
        ("M", lambda: check_motifs(reg)),
        ("I", lambda: check_image_records(reg)),
        ("I3", lambda: check_image_markup(reg, out)),
        ("C1", lambda: check_credits(reg, out)),
        ("X1", lambda: check_text_on_images(out)),
    ]
    if not offline:
        checks.append(("L2", lambda: check_external_links(out, reg.root)))
    if a11y:
        from mobility_model_zoo.site import a11y as browser

        checks.append(("A", lambda: browser.run(out)))
        checks.append(("O3", lambda: browser.contrast(out)))
    findings: list[Finding] = []
    for check_id, fn in checks:
        if only and not any(i.startswith(check_id) or check_id.startswith(i) for i in only):
            continue
        found = list(fn())
        if only:
            found = [f for f in found if f[0] in only or any(f[0].startswith(i) for i in only)]
        findings += found
        say(f"{check_id:<3} {'FAIL' if found else 'PASS'}" + (f" ({len(found)})" if found else ""))
    for f in findings:
        say(f.line())
    if findings:
        raise GateFailed([f.line() for f in findings])
    return findings
