"""Preview images for shared links (specs/012-social-preview-images).

Every shareable page (the start page, each published model, each output format) gets one image,
1200 x 630: zoo mark and wordmark, the page title, a one-line share text without numbers and,
for models, the labels `experimental`, `deprecated` and `non-commercial`. `zoo site build` fills
`templates/og/card.html.j2` per page and screenshots it in headless Chromium (Playwright). The
file name carries a hash of everything that is drawn, so platforms that cache previews by URL
fetch a changed image and keep an unchanged one (research R5).
"""

from __future__ import annotations

import hashlib
import re
import tomllib
from collections.abc import Callable, Iterable
from importlib import metadata
from pathlib import Path
from typing import Any

from mobility_model_zoo.release.errors import GateFailed, UsageError
from mobility_model_zoo.site.facts import PLACEHOLDER, literal_numbers

WIDTH, HEIGHT = 1200, 630
MAX_BYTES = 300_000
MAX_LINE = 90
MAX_LINES = 3
TITLE_SIZES = (76, 60, 48)
MARGIN = 48
SAFE_X = (285, 915)
OG_DIR = "assets/og"
CARD_DIR = "_build/og"
MANIFEST = "_build/og.json"
# The code points the shipped Figtree subset draws (research R7), read from its cmap; control
# characters are included because they are never drawn. tests/website/test_og_fonts.py
# checks this list against the font file.
LATIN_RANGES = (
    (0x0000, 0x00AC),
    (0x00AE, 0x00FF),
    (0x0102, 0x0102),
    (0x0131, 0x0131),
    (0x0152, 0x0153),
    (0x02C6, 0x02C6),
    (0x02DA, 0x02DA),
    (0x02DC, 0x02DC),
    (0x0300, 0x0301),
    (0x0303, 0x0304),
    (0x0308, 0x0308),
    (0x2013, 0x2014),
    (0x2018, 0x201A),
    (0x201C, 0x201E),
    (0x2022, 0x2022),
    (0x2026, 0x2026),
    (0x2039, 0x203A),
    (0x2044, 0x2044),
    (0x20AC, 0x20AC),
    (0x2122, 0x2122),
    (0x2191, 0x2191),
    (0x2193, 0x2193),
    (0x2212, 0x2212),
    (0x2215, 0x2215),
)
NO_BROWSER = (
    "images need the site-check group: uv sync --group site-check && "
    "uv run playwright install chromium (or pass --no-images)"
)
ROADMAP_TITLE, ROADMAP_LINE = "What comes next", "What the zoo plans to release next."
ASSET_REF = re.compile(r"""<link[^>]+href="([^"]+)"|url\(\s*['"]?([^'")]+)['"]?\s*\)""")


# ---- the share line (B6) ----------------------------------------------------------------------
def share_line(source: dict[str, Any]) -> tuple[str, bool]:
    """The line on the image: `share_line`, else the tagline; and whether it is the tagline."""
    if source.get("share_line"):
        return " ".join(str(source["share_line"]).split()), False
    return " ".join(str(source.get("tagline", "")).split()), True


def in_fonts(ch: str) -> bool:
    return any(lo <= ord(ch) <= hi for lo, hi in LATIN_RANGES)


def share_line_errors(owner: str, text: str, from_tagline: bool = False) -> list[str]:
    errors = []
    if len(text) > MAX_LINE:
        errors.append(f"share line has {len(text)} characters, at most {MAX_LINE}")
    if PLACEHOLDER.search(text):
        errors.append("share line contains a metric placeholder")
    errors += [f'share line contains the number "{n}"' for n in literal_numbers(text)]
    errors += [
        f"character U+{ord(ch):04X} is not in the site fonts"
        for ch in sorted(set(text))
        if not in_fonts(ch)
    ]
    hint = "; add share_line to site.yaml" if from_tagline else ""
    return [f"B6 {owner}: {e}{hint}" for e in errors]


# ---- cards ------------------------------------------------------------------------------------
def _card(page: str, kind: str, slug: str, title: str, line: str, **extra: Any) -> dict[str, Any]:
    labels = extra.pop("labels", [])
    lead = f"Output format {title}" if kind == "format" else title
    alt = f"{lead}, Mobility Model Zoo: {line}" + (f" ({', '.join(labels)})" if labels else "")
    return {
        "page": page,
        "kind": kind,
        "slug": slug,
        "title": title,
        "line": line,
        "labels": labels,
        "alt": alt,
        "eyebrow": extra.pop("eyebrow", ""),
        "motif": extra.pop("motif", None),
        "owner": extra.pop("owner"),
        "from_tagline": extra.pop("from_tagline", False),
    }


def labels(sm: dict[str, Any]) -> list[str]:
    """Release status, deprecation and usage class, as the latest release record states them."""
    out = []
    status = sm["releases"][0]["status"] if sm["releases"] else "released"
    if status != "released":
        out.append(status)
    if sm["status"] == "deprecated" and "deprecated" not in out:
        out.append("deprecated")
    if sm["usage"]["class"].startswith("non-commercial"):
        out.append("non-commercial")
    return out


def cards(
    reg: Any, site: dict[str, Any], models: list[dict[str, Any]], formats: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """One card per shareable page: the zoo, the roadmap, every published model, every output format."""
    line, from_tagline = share_line(site)
    out = [_card("", "zoo", "zoo", site["title"], line, owner="zoo", from_tagline=from_tagline)]
    # feature 015: the roadmap page; its line comes from zoo/site.yaml roadmap.share_line
    plan = " ".join(str((site.get("roadmap") or {}).get("share_line") or ROADMAP_LINE).split())
    out.append(
        _card("roadmap/", "page", "roadmap", ROADMAP_TITLE, plan, eyebrow="Roadmap", owner="roadmap")
    )
    for sm in models:
        if sm["status"] == "in_progress" or not sm.get("pitch"):
            continue
        line, from_tagline = share_line(sm["pitch"])
        topic = reg.topic(sm["m"]["topic"]) or {"title": sm["m"]["topic"]}
        out.append(
            _card(
                f"models/{sm['name']}/",
                "model",
                sm["name"],
                sm["name"],
                line,
                labels=labels(sm),
                eyebrow=topic["title"],
                motif=sm["pitch"].get("motif"),
                owner=sm["name"],
                from_tagline=from_tagline,
            )
        )
    for fmt in formats:
        out.append(
            _card(
                f"formats/{fmt['id']}/",
                "format",
                f"format-{fmt['id']}",
                fmt["id"],
                " ".join(fmt["title"].split()),
                eyebrow="Output format",
                owner=f"format {fmt['id']}",
            )
        )
    return out


def card_errors(all_cards: Iterable[dict[str, Any]]) -> list[str]:
    return [e for c in all_cards for e in share_line_errors(c["owner"], c["line"], c["from_tagline"])]


def site_cards(reg: Any) -> list[dict[str, Any]]:
    """The cards of the current registry, as the build makes them (check O4)."""
    from mobility_model_zoo.site import context, schema_doc

    formats = [schema_doc.output_format(reg, i) for i in schema_doc.format_ids(reg)]
    return cards(reg, context.load_site_config(reg), context.site_models(reg), [f for f in formats if f])


# ---- card pages and their addresses -----------------------------------------------------------
def card_html(env: Any, card: dict[str, Any]) -> str:
    return env.get_template("og/card.html.j2").render(card=card, root="../../assets/")


def assets(html: str, base: Path) -> list[Path]:
    """Files a card page loads: its style sheets and what they load in turn (fonts)."""
    found: list[Path] = []
    todo = [(m[0] or m[1], base) for m in ASSET_REF.findall(html)]
    while todo:
        ref, at = todo.pop()
        path = (at / ref).resolve()
        if path in found or not path.is_file():
            continue
        found.append(path)
        if path.suffix == ".css":
            css = path.read_text(encoding="utf-8")
            todo += [(m[0] or m[1], path.parent) for m in ASSET_REF.findall(css)]
    return sorted(found)


def renderer_id(root: Path) -> str:
    """`playwright <version>`: installed, else as locked in uv.lock. The Playwright version pins its
    Chromium, and a build without a browser must give the same addresses (research R5)."""
    try:
        return f"playwright {metadata.version('playwright')}"
    except metadata.PackageNotFoundError:
        pass
    lock = root / "uv.lock"
    if lock.exists():
        for pkg in tomllib.loads(lock.read_text(encoding="utf-8")).get("package", []):
            if pkg.get("name") == "playwright":
                return f"playwright {pkg['version']}"
    return "playwright unknown"


def input_hash(html: str, base: Path, renderer: str) -> str:
    h = hashlib.sha256(html.encode("utf-8"))
    for path in assets(html, base):
        h.update(path.name.encode("utf-8"))
        h.update(path.read_bytes())
    h.update(renderer.encode("utf-8"))
    return h.hexdigest()


def card_file(card: dict[str, Any], digest: str) -> str:
    return f"{OG_DIR}/{card['slug']}-{digest[:12]}.png"


def manifest_card(card: dict[str, Any]) -> dict[str, Any]:
    keys = ("page", "kind", "title", "line", "labels", "alt", "file", "inputs_sha256", "html")
    out = {k: card[k] for k in keys}
    if "layout" in card:
        out["layout"] = card["layout"]
    return out


# ---- rendering (B7) ---------------------------------------------------------------------------
FIT_JS = """sizes => {
  const q = s => document.querySelector(`[data-og="${s}"]`);
  const title = q('title');
  let px = null;
  for (const s of sizes) {
    title.style.fontSize = s + 'px';
    if (title.scrollWidth <= title.clientWidth) { px = s; break; }
  }
  const line = q('line');
  const lh = parseFloat(getComputedStyle(line).lineHeight);
  const lines = line.textContent.trim() ? Math.round(line.getBoundingClientRect().height / lh) : 0;
  const box = s => { const e = q(s); if (!e) return null;
    const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; };
  const overflow = [];
  document.querySelectorAll('[data-og]').forEach(e => {
    // the title clips at its box on purpose (overflow: hidden), so only its width counts
    const tall = e !== title && e.scrollHeight > e.clientHeight + 1;
    if (e.scrollWidth > e.clientWidth + 1 || tall) overflow.push(e.dataset.og);
  });
  return {title_px: px, line_lines: lines, overflow,
          boxes: {brand: box('brand'), mark: box('mark'), title: box('title'), line: box('line'),
                  labels: box('labels')}};
}"""


def _local_only(route: Any) -> None:
    if route.request.url.startswith("file:"):
        route.continue_()
    else:
        route.abort()


def render(all_cards: list[dict[str, Any]], out: Path, say: Callable[[str], None] = print) -> None:
    """Screenshot each card page into its file; record the layout; B7 if text does not fit."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise UsageError(NO_BROWSER) from e
    failures = []
    (out / OG_DIR).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception as e:
            if "Executable doesn't exist" in str(e):
                raise UsageError(NO_BROWSER) from e
            raise
        try:
            ctx = browser.new_context(
                viewport={"width": WIDTH, "height": HEIGHT},
                device_scale_factor=1,
                color_scheme="dark",
            )
            page = ctx.new_page()
            page.route("**/*", _local_only)
            for card in all_cards:
                page.goto((out / card["html"]).resolve().as_uri(), wait_until="load")
                page.evaluate("() => document.fonts.ready.then(() => true)")
                layout = page.evaluate(FIT_JS, list(TITLE_SIZES))
                card["layout"] = layout
                where = card["page"] or "(start)"
                if layout["title_px"] is None:
                    failures.append(f"B7 {where}: title does not fit at {TITLE_SIZES[-1]} px")
                    continue
                if layout["line_lines"] > MAX_LINES:
                    n = layout["line_lines"]
                    failures.append(f"B7 {where}: share line needs {n} lines, at most {MAX_LINES}")
                    continue
                page.screenshot(path=str(out / card["file"]), type="png")
                say(f"  drew {card['file']}")
        finally:
            browser.close()
    if failures:
        raise GateFailed(failures)
