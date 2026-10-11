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


def test_a2_field_table_on_the_format_page_and_link_on_the_model_page(built):
    """Feature 013: the field table moved to the format page; the model page links it."""
    from site_fixture import MODEL

    fmt = built.out / "formats" / "jtbd-span-v1" / "index.html"
    fmt.write_text(fmt.read_text().replace('class="tbl"', 'class="x"'))
    model = built.out / "models" / MODEL / "index.html"
    model.write_text(model.read_text().replace('/formats/jtbd-span-v1/"', '/elsewhere/"'))
    found = [f for f in run(built) if f[0] == "A2"]
    assert any(f[1].startswith("formats/") and "field table" in f[2] for f in found)
    assert any(f[1].startswith("models/") and "output format" in f[2] for f in found)


def test_d6_placement_of_the_layers(built):
    """Feature 013, SC-001 to SC-003: figures within 2 screens, limits within 4, terms on top."""
    from site_fixture import MODEL

    assert [f for f in run(built) if f[0] == "D6"] == []
    page = built.out / "models" / MODEL / "index.html"
    spacer = '<div style="height:5000px"></div>'
    page.write_text(page.read_text().replace('<p class="lead">', spacer + '<p class="lead">', 1))
    found = [f for f in run(built) if f[0] == "D6"]
    assert any("first quality figure" in f[2] for f in found)
    assert any("limits layer" in f[2] for f in found)
