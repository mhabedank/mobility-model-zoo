"""Browser checks (A1-A4, P2, S2) with Playwright and axe-core; slow, needs Chromium."""

from __future__ import annotations

import pytest

pytest.importorskip("playwright")
pytestmark = pytest.mark.slow


def run(env):
    from mobility_model_zoo.site import a11y

    try:
        return list(a11y.run(env.out))
    except Exception as e:  # pragma: no cover - Chromium not installed
        if "Executable doesn't exist" in str(e):
            pytest.skip("run `uv run playwright install chromium`")
        raise


def test_built_site_passes_the_browser_checks(built):
    assert run(built) == []


def test_injected_faults_are_found(built):
    page = built.out / "index.html"
    html = page.read_text()
    html = html.replace(
        "</head>", '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter"></head>'
    )
    html = html.replace(
        "</main>",
        '<svg role="img" width="10" height="10"></svg>'
        '<p class="hl job" style="color:var(--muted)">muted on a job highlight</p></main>',
    )
    page.write_text(html)
    css = built.out / "assets" / "css" / "site.css"
    css.write_text(css.read_text() + "\n:focus-visible { outline: none; }\n")
    ids = {f[0] for f in run(built)}
    assert {"P2", "A3", "A4"} <= ids
    assert "A1" in ids  # the muted-on-highlight pair fails contrast in dark mode (research R9)
