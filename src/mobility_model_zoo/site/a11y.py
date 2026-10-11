"""Browser checks of the website with Playwright and the vendored axe-core (contracts/checks.md):

- A1: axe-core, WCAG 2.0/2.1 A and AA, every page in the light and the dark colour scheme.
- A2: with JavaScript disabled, model pages still hold quickstart, examples, limits and a link to
  their output format; format pages hold the field table (feature 013 moved it there).
- A3: every image has a text alternative; every chart has a table of its values.
- A4: keyboard: the skip link comes first, every control is reachable and shows a focus ring.
- P2: every request goes to the local server; no page sets a cookie.
- A5: reflow: no page scrolls sideways at a phone width of 390 px (WCAG 1.4.10).
- S2: Largest Contentful Paint at most 2 s under a slow mobile network and a 4x slower CPU.
- O3: colour contrast of the preview image pages (feature 012).
- D6: placement of the model page layers on screen (feature 013, SC-001 to SC-003).
"""

from __future__ import annotations

from collections.abc import Iterable
from importlib import resources
from pathlib import Path
from urllib.parse import urlparse

from mobility_model_zoo.site.check import Finding, pages
from mobility_model_zoo.site.serve import background

AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
LCP_LIMIT_MS = 2000
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
# Screen budgets (feature 013): first quality figure within 2 screens and limits within 4 on a
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
    for rel in rels:
        page.goto(base + rel, wait_until="load")
        lcp = page.evaluate(LCP_JS)
        width = page.evaluate("document.documentElement.scrollWidth")
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
