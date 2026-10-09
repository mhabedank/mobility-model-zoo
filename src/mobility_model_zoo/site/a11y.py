"""Browser checks of the website with Playwright and the vendored axe-core (contracts/checks.md):

- A1: axe-core, WCAG 2.0/2.1 A and AA, every page in the light and the dark colour scheme.
- A2: with JavaScript disabled, model pages still hold quickstart, field table, examples, limits.
- A3: every image has a text alternative; every chart has a table of its values.
- A4: keyboard: the skip link comes first, every control is reachable and shows a focus ring.
- P2: every request goes to the local server; no page sets a cookie.
- A5: reflow: no page scrolls sideways at a phone width of 390 px (WCAG 1.4.10).
- S2: Largest Contentful Paint at most 2 s under a slow mobile network and a 4x slower CPU.
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
        if not rel.startswith("models/"):
            continue
        page.goto(base + rel)
        required = {
            "#quickstart pre": "quickstart code",
            "#interface table.tbl": "field table",
            "#examples pre": "example JSON",
            "#limits .callout": "limitations",
        }
        for selector, what in required.items():
            if not page.query_selector(selector):
                findings.append(Finding("A2", rel, f"without JavaScript: no {what} ({selector})"))
        examples = page.query_selector_all("#examples article.example")
        for ex in examples:
            if not ex.query_selector("details pre"):
                findings.append(Finding("A2", rel, f"example {ex.get_attribute('id')} has no full JSON"))
    ctx.close()
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
