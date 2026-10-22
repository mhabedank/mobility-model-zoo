"""Browser checks of the website with Playwright and the vendored axe-core (contracts/checks.md):

- A1: axe-core, WCAG 2.0/2.1 A and AA, every page in the light and the dark colour scheme.
- A2: with JavaScript disabled, model pages still hold quickstart, examples, limits and a link to
  their output format; format pages hold the field table (feature 014 moved it there).
- A3: every image has a text alternative; every chart has a table of its values.
- A4: keyboard: the skip link comes first, every control is reachable and shows a focus ring.
- P2: every request goes to the local server; no page sets a cookie.
- A5: reflow: no page scrolls sideways at a phone width of 390 px (WCAG 1.4.10).
- S2: Largest Contentful Paint at most 2 s under a slow mobile network and a 4x slower CPU.
- O3: colour contrast of the preview image pages (feature 012).
- D6: placement of the model page layers on screen (feature 014, SC-001 to SC-003).
- S3: Cumulative Layout Shift at most 0.1; S4: bytes per page at 390 px, DPR 2 (feature 016).
- M3: motifs' ink differs pairwise (Jaccard distance >= 0.5); M4: motif sizes; M5: stroke contrast.
"""

from __future__ import annotations

import base64
from collections.abc import Iterable
from importlib import resources
from pathlib import Path
from urllib.parse import urlparse

from mobility_model_zoo.site.check import Finding, pages
from mobility_model_zoo.site.serve import background

AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
LCP_LIMIT_MS = 2000
CLS_LIMIT = 0.1
PAGE_BYTES_WITH_IMAGES, PAGE_BYTES_PLAIN = 600_000, 300_000
MOTIF_MIN_DIFF = 0.5  # Jaccard distance of the ink masks
MOTIF_MIN_CONTRAST = 3.0
SLOW_NETWORK = {
    "offline": False,
    "latency": 150,
    "downloadThroughput": 1_600_000 / 8,
    "uploadThroughput": 750_000 / 8,
}
MAX_TABS = 400

LCP_JS = """() => new Promise(resolve => {
  let last = 0;
  new PerformanceObserver(list => { for (const e of list.getEntries()) last = e.startTime; })
    .observe({type: 'largest-contentful-paint', buffered: true});
  setTimeout(() => resolve(last), 300);
})"""

CLS_JS = """() => new Promise(resolve => {
  let cls = 0;
  new PerformanceObserver(list => {
    for (const e of list.getEntries()) if (!e.hadRecentInput) cls += e.value; })
    .observe({type: 'layout-shift', buffered: true});
  setTimeout(() => resolve(cls), 300);
})"""

MOTIF_SIZES_JS = """() => {
  const h = el => Math.round(el.getBoundingClientRect().height);
  return {
    tiles: [...document.querySelectorAll('.tile .plate svg')].map(h),
    roadmap: [...document.querySelectorAll('.entry-name .plate svg, a.mini .plate svg')].map(h),
    hero: [...document.querySelectorAll('.hero-art .plate')].map(el => {
      const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return {h: Math.round(r.height),
              visible: s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0};
    }),
  };
}"""

MASK_JS = """data => new Promise(resolve => {
  const img = new Image();
  img.onload = () => {
    const c = document.createElement('canvas'); c.width = 96; c.height = 96;
    const ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0, 96, 96);
    const px = ctx.getImageData(0, 0, 96, 96).data, ink = [];
    for (let i = 0; i < 96 * 96; i++) {
      const l = 0.299 * px[i * 4] + 0.587 * px[i * 4 + 1] + 0.114 * px[i * 4 + 2];
      if (l > 60) ink.push(i);
    }
    resolve(ink);
  };
  img.src = 'data:image/png;base64,' + data;
})"""

MOTIF_COLOURS_JS = """() => [...document.querySelectorAll('.plate')].slice(0, 1).map(p => {
  const s = getComputedStyle(p);
  return {plate: s.backgroundColor, text: s.getPropertyValue('--text').trim(),
          grey: s.getPropertyValue('--border-strong').trim(),
          accent: s.getPropertyValue('--mark').trim()};
})"""

FOCUS_JS = """() => {
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const s = getComputedStyle(el);
  return {index: Array.prototype.indexOf.call(document.querySelectorAll('*'), el),
          tag: el.tagName, id: el.id, cls: el.className,
          text: (el.textContent || '').trim().slice(0, 40),
          outline: parseFloat(s.outlineWidth) || 0, style: s.outlineStyle,
          href: el.getAttribute('href')};
}"""

FOCUSABLE_JS = """() => Array.from(document.querySelectorAll('a[href], button, summary, [tabindex]'))
  .filter(el => el.tabIndex >= 0 && !el.disabled && el.offsetParent !== null
          && getComputedStyle(el).visibility !== 'hidden'
          && (el.tagName === 'SUMMARY' || !el.closest('details:not([open])'))).length"""

NAMES_JS = """() => {
  const bad = [];
  document.querySelectorAll('img').forEach(i => {
    if (!i.hasAttribute('alt')) bad.push('img ' + i.src);
  });
  document.querySelectorAll('svg[role="img"], [role="img"]').forEach(s => {
    if (!(s.getAttribute('aria-label') || s.getAttribute('aria-labelledby') || s.querySelector('title')))
      bad.push(s.tagName + ' without a name');
  });
  document.querySelectorAll('figure.chart').forEach((f, n) => {
    if (!f.querySelector('table')) bad.push('chart ' + (n + 1) + ' has no table of values');
  });
  return bad;
}"""


def _axe() -> str:
    return (
        resources.files("mobility_model_zoo.site")
        .joinpath("checks_vendor/axe.min.js")
        .read_text(encoding="utf-8")
    )


def run(out: Path) -> Iterable[Finding]:
    from playwright.sync_api import sync_playwright

    axe = _axe()
    srv, base = background(out)
    host = urlparse(base).netloc
    rels = [str(p.relative_to(out)).replace("index.html", "") for p in pages(out)]
    findings: list[Finding] = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            findings += _axe_and_network(browser, base, host, rels, axe)
            findings += _no_js(browser, base, rels)
            findings += _keyboard(browser, base, rels)
            findings += _load_time(browser, base, rels)
            findings += placement(browser, base, rels)
            findings += motif_checks(browser, base, rels, out)
            browser.close()
    finally:
        srv.shutdown()
    return findings


def _axe_and_network(browser, base: str, host: str, rels: list[str], axe: str) -> list[Finding]:
    findings = []
    for scheme in ("light", "dark"):
        ctx = browser.new_context(color_scheme=scheme, viewport={"width": 1280, "height": 900})
        requests: list[tuple[str, str]] = []
        page = ctx.new_page()
        page.on("request", lambda r, pages_=requests, pg=page: pages_.append((pg.url, r.url)))
        for rel in rels:
            page.goto(base + rel, wait_until="networkidle")
            page.add_script_tag(content=axe)
            result = page.evaluate(
                "tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", AXE_TAGS
            )
            for v in result["violations"]:
                targets = ", ".join(str(n["target"][0]) for n in v["nodes"][:3])
                findings.append(
                    Finding(
                        "A1",
                        rel or "index.html",
                        f"{scheme}: {v['id']} ({v['impact']}): {v['help']} at {targets}",
                    )
                )
            for bad in page.evaluate(NAMES_JS):
                if scheme == "light":
                    findings.append(Finding("A3", rel or "index.html", bad))
            cookie = page.evaluate("document.cookie")
            if cookie:
                findings.append(Finding("P2", rel or "index.html", f"sets document.cookie {cookie!r}"))
        for cookie in ctx.cookies():
            findings.append(Finding("P2", "(site)", f"cookie {cookie['name']} for {cookie['domain']}"))
        for page_url, url in requests:
            parsed = urlparse(url)
            if parsed.scheme in ("http", "https") and parsed.netloc != host:
                findings.append(
                    Finding("P2", page_url.replace(base, "") or "index.html", f"requests {url}")
                )
        ctx.close()
    return findings


def _no_js(browser, base: str, rels: list[str]) -> list[Finding]:
    findings = []
    ctx = browser.new_context(java_script_enabled=False)
    page = ctx.new_page()
    for rel in rels:
        if rel.startswith("formats/"):
            page.goto(base + rel)
            if not page.query_selector("table.tbl"):
                findings.append(Finding("A2", rel, "without JavaScript: no field table (table.tbl)"))
            continue
        if not rel.startswith("models/"):
            continue
        page.goto(base + rel)
        required = {
            "#quickstart pre": "quickstart code",
            '#interface a[href*="/formats/"]': "link to the output format",
            "#examples pre": "example JSON",
            "#limits .callout": "limitations",
        }
        for selector, what in required.items():
            if not page.query_selector(selector):
                findings.append(Finding("A2", rel, f"without JavaScript: no {what} ({selector})"))
        examples = page.query_selector_all("#examples article.example")
        for ex in examples:
            if "device" in (ex.get_attribute("class") or "").split():
                # microcontroller examples hold thousands of frames: inline excerpt, full file linked
                if not ex.query_selector("pre") or not ex.query_selector('a[href*="/examples/"]'):
                    findings.append(
                        Finding("A2", rel, f"example {ex.get_attribute('id')} has no excerpt or link")
                    )
            elif not ex.query_selector("details pre"):
                findings.append(Finding("A2", rel, f"example {ex.get_attribute('id')} has no full JSON"))
    ctx.close()
    return findings


PLACEMENT_JS = """() => {
  const top = el => el ? el.getBoundingClientRect().top + scrollY : null;
  const bottom = el => el ? el.getBoundingClientRect().bottom + scrollY : null;
  const chips = [document.querySelector('[data-layer=overview] [data-status]'),
                 ...[...document.querySelectorAll('[data-layer=overview] .chip')]
                   .filter(c => /Licence|Non-commercial/.test(c.textContent))];
  const fig = document.querySelector(
    '[data-layer=quality] .metric, [data-layer=quality] figure.chart');
  return {first: top(fig),
          limits: top(document.getElementById('limits')),
          chips: chips.filter(Boolean).map(bottom), vh: innerHeight};
}"""
# Screen budgets (feature 014): first quality figure within 2 screens and limits within 4 on a
# desktop; status, usage class and licence in the first screen, within 2 screens on a phone.
PLACEMENT = (
    {"width": 1440, "height": 900, "first": 2, "limits": 4, "chips": 1},
    {"width": 390, "height": 844, "first": None, "limits": None, "chips": 2},
)


def placement(browser, base: str, rels: list[str]) -> list[Finding]:
    findings = []
    for vp in PLACEMENT:
        page = browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
        for rel in rels:
            if not rel.startswith("models/"):
                continue
            page.goto(base + rel)
            m = page.evaluate(PLACEMENT_JS)
            screens = {
                k: (v / m["vh"] if v is not None else None)
                for k, v in m.items()
                if k in ("first", "limits")
            }
            size = f"{vp['width']}x{vp['height']}"
            for key, what in (("first", "first quality figure"), ("limits", "limits layer")):
                limit = vp[key]
                if limit is None:
                    continue
                if screens[key] is None:
                    findings.append(Finding("D6", rel, f"{size}: no {what}"))
                elif screens[key] > limit:
                    findings.append(
                        Finding("D6", rel, f"{size}: {what} at screen {screens[key]:.1f}, limit {limit}")
                    )
            if not m["chips"] or max(m["chips"]) > vp["chips"] * m["vh"]:
                findings.append(
                    Finding(
                        "D6",
                        rel,
                        f"{size}: status, usage class or licence not within {vp['chips']} screen(s)",
                    )
                )
        page.close()
    return findings


def _keyboard(browser, base: str, rels: list[str]) -> list[Finding]:
    findings = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    for rel in rels:
        page.goto(base + rel, wait_until="networkidle")
        expected = page.evaluate(FOCUSABLE_JS)
        seen, first = set(), None
        for _ in range(min(MAX_TABS, expected + 5)):
            page.keyboard.press("Tab")
            info = page.evaluate(FOCUS_JS)
            if info is None:
                continue
            if first is None:
                first = info
            key = info["index"]
            if key in seen:
                break
            seen.add(key)
            if info["outline"] < 2 or info["style"] == "none":
                findings.append(
                    Finding(
                        "A4",
                        rel or "index.html",
                        f"no visible focus ring on {info['tag']} {info['text']!r}",
                    )
                )
        if not first or "skip" not in str(first["cls"]):
            findings.append(
                Finding("A4", rel or "index.html", "the first Tab stop is not the skip link")
            )
        if len(seen) < expected:
            findings.append(
                Finding(
                    "A4",
                    rel or "index.html",
                    f"Tab reached {len(seen)} of {expected} focusable elements",
                )
            )
    ctx.close()
    return findings


def _load_time(browser, base: str, rels: list[str]) -> list[Finding]:
    findings = []
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.emulateNetworkConditions", SLOW_NETWORK)
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    transferred: dict[str, list[tuple[str, int]]] = {}

    def on_response(resp, pages_=transferred):
        try:
            body = (
                len(resp.body())
                if resp.ok and resp.request.resource_type != "document" or resp.ok
                else 0
            )
        except Exception:  # noqa: BLE001 - a body that is gone is not counted
            body = 0
        pages_.setdefault(page.url, []).append((resp.url, body))

    page.on("response", on_response)
    for rel in rels:
        page.goto(base + rel, wait_until="load")
        lcp = page.evaluate(LCP_JS)
        cls = page.evaluate(CLS_JS)
        width = page.evaluate("document.documentElement.scrollWidth")
        has_images = page.evaluate("!!document.querySelector('img[data-image]')")
        got = transferred.pop(page.url, [])
        total = sum(n for url, n in got if not url.endswith(".woff2"))
        limit = PAGE_BYTES_WITH_IMAGES if has_images else PAGE_BYTES_PLAIN
        if total > limit:
            heaviest = max(got, key=lambda x: x[1])
            findings.append(
                Finding(
                    "S4",
                    rel or "index.html",
                    f"{total} bytes transferred without fonts, more than {limit}; "
                    f"heaviest {heaviest[0].split('/')[-1]} ({heaviest[1]})",
                )
            )
        if cls > CLS_LIMIT:
            findings.append(
                Finding(
                    "S3",
                    rel or "index.html",
                    f"Cumulative Layout Shift {cls:.3f}, more than {CLS_LIMIT}",
                )
            )
        if width > 390:
            findings.append(
                Finding("A5", rel or "index.html", f"scrolls sideways at 390 px ({width} px wide)")
            )
        if lcp > LCP_LIMIT_MS:
            findings.append(
                Finding(
                    "S2",
                    rel or "index.html",
                    f"Largest Contentful Paint {lcp:.0f} ms, more than {LCP_LIMIT_MS} ms",
                )
            )
    ctx.close()
    return findings


def contrast(out: Path) -> Iterable[Finding]:
    """O3: axe-core colour contrast on every preview image page, in the scheme it is drawn in."""
    from playwright.sync_api import sync_playwright

    from mobility_model_zoo.site import og
    from mobility_model_zoo.site.check import og_manifest

    manifest = og_manifest(out) or {"cards": []}
    axe = _axe()
    findings: list[Finding] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(
                viewport={"width": og.WIDTH, "height": og.HEIGHT}, color_scheme="dark"
            )
            page = ctx.new_page()
            for card in manifest["cards"]:
                page.goto((out / card["html"]).resolve().as_uri(), wait_until="load")
                page.add_script_tag(content=axe)
                result = page.evaluate(
                    "() => axe.run(document, {runOnly: {type: 'rule', values: ['color-contrast']}})"
                )
                for v in result["violations"]:
                    targets = ", ".join(str(n["target"][0]) for n in v["nodes"][:3])
                    findings.append(
                        Finding("O3", card["page"] or "index.html", f"{v['help']} at {targets}")
                    )
        finally:
            browser.close()
    return findings


# ---- feature 016: motif checks M3, M4, M5 --------------------------------------------------------
def _luminance(rgb: tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        v = c / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _parse_colour(value: str) -> tuple[int, int, int] | None:
    import re

    value = value.strip()
    m = re.match(r"#([0-9a-fA-F]{6})", value)
    if m:
        h = m.group(1)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", value)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def contrast_ratio(a: str, b: str) -> float | None:
    ca, cb = _parse_colour(a), _parse_colour(b)
    if not ca or not cb:
        return None
    la, lb = sorted((_luminance(ca), _luminance(cb)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def motif_checks(browser, base: str, rels: list[str], out: Path) -> list[Finding]:
    """M4 sizes and hero visibility, M5 stroke contrast against the plate, M3 pairwise difference."""
    findings = []
    for scheme, width in (("light", 1280), ("dark", 390)):
        ctx = browser.new_context(color_scheme=scheme, viewport={"width": width, "height": 900})
        page = ctx.new_page()
        for rel in rels:
            if rel not in ("", "roadmap/") and not rel.startswith("models/"):
                continue
            page.goto(base + rel, wait_until="load")
            sizes = page.evaluate(MOTIF_SIZES_JS)
            where = rel or "index.html"
            for h in sizes["tiles"]:
                if h < 64:
                    findings.append(
                        Finding("M4", where, f"{scheme} {width}px: tile motif {h} px, needs 64")
                    )
            for h in sizes["roadmap"]:
                if h < 40:
                    findings.append(
                        Finding("M4", where, f"{scheme} {width}px: roadmap/mini motif {h} px, needs 40")
                    )
            if rel.startswith("models/") and not any(h["visible"] for h in sizes["hero"]):
                findings.append(Finding("M4", where, f"{scheme} {width}px: hero motif not visible"))
            if scheme == "light" and rel == "":
                for c in page.evaluate(MOTIF_COLOURS_JS):
                    for name in ("text", "grey", "accent"):
                        ratio = contrast_ratio(c[name], c["plate"])
                        if ratio is not None and ratio < MOTIF_MIN_CONTRAST:
                            findings.append(
                                Finding(
                                    "M5",
                                    where,
                                    f"{name} on the plate: {ratio:.1f}:1, needs {MOTIF_MIN_CONTRAST}:1",
                                )
                            )
        ctx.close()
    findings += motif_distinctness(browser, out)
    return findings


def motif_distinctness(browser, out: Path) -> list[Finding]:
    """M3: every pair of motifs differs in at least 12 % of pixels at 96 px on the plate."""
    from mobility_model_zoo.site import motifs

    files = motifs.files()
    page = browser.new_page(viewport={"width": 120, "height": 120}, color_scheme="dark")
    # the plate colours inline (set_content cannot load file: stylesheets); same values as .plate
    style = (
        "body{margin:0;background:#fff}.plate{--text:#FBEED0;--border-strong:#A5DBC6;--mark:#ED9B20;"
        "display:inline-grid;place-items:center;background:#062544}"
    )
    raster: dict[str, bytes] = {}
    for name, path in files.items():
        svg = path.read_text(encoding="utf-8").replace("<svg ", '<svg width="96" height="96" ', 1)
        html = (
            f"<!doctype html><html><head><style>{style}</style></head>"
            '<body><span class="plate" style="width:120px;height:120px">'
            f"{svg}</span></body></html>"
        )
        page.set_content(html, wait_until="load")
        raster[name] = page.screenshot(type="png", omit_background=False)
    # ink = pixels that are not the plate, read back through a canvas in the browser so the check
    # needs nothing beyond Playwright; two motifs are distinct when at most half of their ink
    # overlaps (Jaccard distance >= MOTIF_MIN_DIFF). Near-duplicates overlap almost entirely.
    masks: dict[str, set[int]] = {}
    for name, png in raster.items():
        data = base64.b64encode(png).decode("ascii")
        masks[name] = set(page.evaluate(MASK_JS, data))
    page.close()
    findings = []
    names = sorted(masks)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            union = masks[a] | masks[b]
            dist = 1 - len(masks[a] & masks[b]) / len(union) if union else 0.0
            if dist < MOTIF_MIN_DIFF:
                findings.append(
                    Finding(
                        "M3",
                        f"{a} / {b}",
                        f"ink overlaps too much: distance {dist:.2f}, needs {MOTIF_MIN_DIFF}",
                    )
                )
    return findings
