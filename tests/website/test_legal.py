"""Use, limits, provenance and legal links (US4; checks L3, P3)."""

from __future__ import annotations

from site_fixture import MODEL

from mobility_model_zoo.release.registry import load_yaml
from mobility_model_zoo.site import check, context


def test_every_page_links_the_legal_pages(built):
    site = context.load_site_config(built.reg)
    assert list(check.check_legal(site, built.out)) == []
    for path in check.pages(built.out):
        footer = check.parse(path).footer_links
        assert {site["legal"][k] for k in ("imprint", "privacy", "copyright")} <= set(footer)


def test_missing_imprint_link_is_l3(built):
    site = context.load_site_config(built.reg)
    path = built.out / "index.html"
    path.write_text(path.read_text().replace(site["legal"]["imprint"], "#"))
    assert any(f[0] == "L3" and "imprint" in f[2] for f in check.check_legal(site, built.out))


def test_all_limitations_are_on_the_page(built):
    from markupsafe import escape

    model = load_yaml(built.root / f"zoo/models/{MODEL}/model.yaml")
    html = built.html(f"models/{MODEL}/index.html")
    limits = html[html.find('id="limits"') : html.find('id="provenance"')]
    for line in model["card"]["limitations"].splitlines():
        words = line.lstrip("- ").split("`")[0][:50]
        assert str(escape(words)) in limits, words


def test_provenance_links(built):
    html = built.html(f"models/{MODEL}/index.html")
    section = html[html.find('id="provenance"') : html.find('id="versions"')]
    assert "0.1.2.training-data-summary.md" in section and "0.1.2.ai-act.md" in section
    assert "FacebookAI/xlm-roberta-large" in section and "Apache-2.0" in section


def test_branding_and_advertising_are_p3(built):
    site = context.load_site_config(built.reg)
    assert list(check.check_branding(site, built.out)) == []
    path = built.out / "index.html"
    path.write_text(
        path.read_text().replace("</main>", "<p>Miskatonic consulting: book a call</p></main>")
    )
    found = list(check.check_branding(site, built.out))
    assert {f[0] for f in found} == {"P3"} and len(found) == 2
