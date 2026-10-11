"""Preview images drawn in Chromium (feature 012): size, layout, checks, new models, speed.

Slow, needs Playwright and its Chromium."""

from __future__ import annotations

import json

import pytest
from site_fixture import MODEL

from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.site import og
from mobility_model_zoo.site.check import png_size, run_checks

pytest.importorskip("playwright")
pytestmark = pytest.mark.slow


def draw(env, **kwargs):
    try:
        return env.build(images=True, **kwargs)
    except Exception as e:  # pragma: no cover - Chromium not installed
        if "playwright install" in str(e):
            pytest.skip("run `uv run playwright install chromium`")
        raise


def manifest(env) -> dict:
    return json.loads((env.out / og.MANIFEST).read_text(encoding="utf-8"))


def test_model_image_is_drawn_and_fits(site_env):
    draw(site_env)
    card = next(c for c in manifest(site_env)["cards"] if c["page"] == f"models/{MODEL}/")
    image = site_env.out / card["file"]
    assert png_size(image) == (og.WIDTH, og.HEIGHT)
    assert image.stat().st_size <= og.MAX_BYTES
    layout = card["layout"]
    assert layout["title_px"] == og.TITLE_SIZES[0]  # an eleven-character name at full size
    assert layout["line_lines"] <= og.MAX_LINES
    assert layout["overflow"] == []
    lo, hi = og.SAFE_X
    for block in ("mark", "title"):
        x, _, w, _ = layout["boxes"][block]
        assert lo - 0.5 <= x and x + w <= hi + 0.5, block


def test_full_check_passes_and_contrast_faults_are_found(site_env):
    draw(site_env)
    assert run_checks(site_env.reg, site_env.out, a11y=True, offline=True, say=lambda _: None) == []

    from mobility_model_zoo.site import a11y

    card = next(c for c in manifest(site_env)["cards"] if c["kind"] == "model")
    page = site_env.out / card["html"]
    html = page.read_text(encoding="utf-8")
    page.write_text(
        html.replace('class="og-line"', 'class="og-line" style="color:#333"'), encoding="utf-8"
    )
    assert any(f[0] == "O3" for f in a11y.contrast(site_env.out))


def test_new_model_image_rendered(site_env):
    site_env.clone_model(MODEL, "scout-mini")
    draw(site_env)
    card = next(c for c in manifest(site_env)["cards"] if c["page"] == "models/scout-mini/")
    assert png_size(site_env.out / card["file"]) == (og.WIDTH, og.HEIGHT)


def test_title_too_long_fails(site_env):
    long_name = "scout-" + "x" * 34  # forty characters: wider than the 630 px title box at 48 px
    site_env.clone_model(MODEL, long_name)
    with pytest.raises(GateFailed) as e:
        draw(site_env)
    assert f"B7 models/{long_name}/: title does not fit at 48 px" in e.value.failures


def test_render_time_five_models(site_env):
    for i in range(4):
        site_env.clone_model(MODEL, f"scout-copy-{i}")
    result = draw(site_env)
    assert result["images"] == 7  # zoo, five models, one format
    assert result["image_seconds"] < 60  # SC-005


def test_relative_output_directory(site_env, monkeypatch):
    """`zoo site build` runs with `--out _site`, a relative path."""
    from mobility_model_zoo.site.build import build

    monkeypatch.chdir(site_env.out.parent)
    try:
        result = build(site_env.reg, type(site_env.out)("rel_site"), offline=True, say=lambda _: None)
    except Exception as e:  # pragma: no cover - Chromium not installed
        if "playwright install" in str(e):
            pytest.skip("run `uv run playwright install chromium`")
        raise
    assert result["images"] == 3
