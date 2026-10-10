"""Usage class on the website (feature 011, FR-016, SC-001 and SC-006)."""

from __future__ import annotations

from pathlib import Path

from site_fixture import MODEL, VERSION

from mobility_model_zoo.release.registry import load_yaml
from mobility_model_zoo.site import check, context

ROOT = Path(__file__).resolve().parents[2]
NC_USAGE = {
    "class": "non-commercial",
    "licence": "CC-BY-NC-4.0",
    "restricting_inputs": [{"kind": "dataset", "id": "nc-corpus", "licence": "CC-BY-NC-4.0",
                            "restriction": "non-commercial"}],
}


def test_commercial_model_page_states_its_class(built):
    html = built.html(f"models/{MODEL}/index.html")
    assert "Licence Apache-2.0 · commercial" in html
    assert '<th scope="row">Usage</th><td>Commercial use permitted · licence Apache-2.0.</td>' in html
    assert "Non-commercial use only" not in html


def test_non_commercial_model_is_marked_before_the_install_line(site_env):
    site_env.edit_yaml(f"zoo/models/{MODEL}/model.yaml",
                       lambda m: m.update(usage_class="non-commercial", license="CC-BY-NC-4.0"))
    site_env.edit_yaml(f"zoo/models/{MODEL}/releases/{VERSION}.yaml", lambda r: r.update(usage=NC_USAGE))
    site_env.build()
    html = site_env.html(f"models/{MODEL}/index.html")
    assert "Licence CC-BY-NC-4.0 · non-commercial" in html
    notice = html.find("Non-commercial use only.</strong>")
    assert 0 < notice < html.find('id="qs-install"')
    assert "because of dataset nc-corpus (CC-BY-NC-4.0)" in html
    start = site_env.html("index.html")
    assert "<dt>Usage</dt><dd>non-commercial</dd>" in start


def test_model_page_without_usage_is_l3(built):
    site = context.load_site_config(built.reg)
    path = built.out / "models" / MODEL / "index.html"
    path.write_text(path.read_text().replace('<th scope="row">Usage</th>', "<th>Use</th>"))
    assert any(f[0] == "L3" and "usage class" in f[2] for f in check.check_legal(site, built.out))


def test_start_page_lists_every_class(built):
    start = built.html("index.html")
    assert start.count("<dt>Usage</dt>") >= 1


def test_zoo_copy_makes_no_zoo_wide_promise_of_commercial_use():
    text = (ROOT / "zoo" / "site.yaml").read_text(encoding="utf-8")
    assert "including commercial use" not in text
    site = load_yaml(ROOT / "zoo" / "site.yaml")
    assert any("non-commercial" in p["text"] for p in site["principles"])
