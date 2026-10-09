"""`zoo site check`: the checks that block publication of the website (contracts/checks.md).

Static checks read the built files; the browser checks (A1-A4, P2, S2) are in `a11y.py` and run
with `--a11y`. Every finding is printed as `<check id> <page> <detail>`; any finding fails.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urlparse

from mobility_model_zoo.release.card import num
from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import Registry, load_yaml

NUMBER = re.compile(r"(?<![\w.,-])\d+(?:[.,]\d+)*(?![\w-]|[.,]\d)")
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
ADVERTISING = re.compile(r"\b(sponsor|donate|donation|pricing|consulting|hire us|book a call)\b", re.I)
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
        self.scripts: list[dict[str, str | None]] = []
        self._skip = 0
        self._footer = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
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

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.text.append(data)


def parse(path: Path) -> Page:
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    return page


def pages(out: Path) -> list[Path]:
    return sorted(p for p in out.rglob("*.html") if "_build" not in p.parts)


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


def literal_numbers(text: str) -> list[str]:
    from mobility_model_zoo.site.facts import PLACEHOLDER

    return [m.group(0) for m in NUMBER.finditer(PLACEHOLDER.sub(" ", text))]


def _prose(pitch: dict) -> Iterable[tuple[str, str]]:
    for key in ("tagline", "audience", "hardware_note"):
        if pitch.get(key):
            yield key, pitch[key]
    for i, d in enumerate(pitch.get("differentiators", [])):
        yield f"differentiators[{i}]", f"{d['title']} {d['text']}"
    for i, c in enumerate(pitch.get("metric_cards", [])):
        yield f"metric_cards[{i}]", " ".join([c["label"], c.get("compare_label", "")])


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


def check_external_links(out: Path) -> Iterable[Finding]:
    """L2: external links answer (HEAD with a GET fallback, two retries)."""
    import httpx

    urls: dict[str, str] = {}
    for path in pages(out):
        for url in parse(path).links:
            if external(url):
                urls.setdefault(urldefrag(url)[0], rel(out, path))
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
    """L3: legal links on every page; licence, limits and AI Act note on every model page; the
    imprint is the one named in the compliance register."""
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
            ):
                if needle not in text:
                    yield Finding("L3", rel(out, path), f"no {what}")


def check_resources(out: Path) -> Iterable[Finding]:
    """P1: no resource is loaded from another host (navigation links are fine)."""
    for path in pages(out):
        for url in parse(path).resources:
            if external(url):
                yield Finding("P1", rel(out, path), f"loads {url}")
    for css in sorted(out.rglob("*.css")):
        for m in CSS_URL.findall(css.read_text(encoding="utf-8")):
            url = m[0] or m[1]
            if external(url):
                yield Finding("P1", rel(out, css), f"loads {url}")


def check_branding(site: dict, out: Path) -> Iterable[Finding]:
    """P3: no company branding (the imprint link is the one allowed mention), no advertising."""
    for path in pages(out):
        html = path.read_text(encoding="utf-8")
        mentions = html.lower().count("miskatonic")
        allowed = html.count(site["legal"]["imprint"])
        if mentions > allowed:
            yield Finding("P3", rel(out, path), "mentions Miskatonic outside the imprint link")
        page = parse(path)
        for chunk in page.text:
            m = ADVERTISING.search(chunk)
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
        and p.name not in ("OFL.txt", "og.png")
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


def check_language(out: Path) -> Iterable[Finding]:
    """FR-023: every page is marked as English."""
    for path in pages(out):
        if '<html lang="en">' not in path.read_text(encoding="utf-8"):
            yield Finding("E1", rel(out, path), 'missing <html lang="en">')


def run_checks(
    reg: Registry,
    out: Path,
    a11y: bool = False,
    only: set[str] | None = None,
    offline: bool = False,
    say: Callable[[str], None] = print,
) -> list[Finding]:
    from mobility_model_zoo.site import context

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
    ]
    if not offline:
        checks.append(("L2", lambda: check_external_links(out)))
    if a11y:
        from mobility_model_zoo.site import a11y as browser

        checks.append(("A", lambda: browser.run(out)))
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
