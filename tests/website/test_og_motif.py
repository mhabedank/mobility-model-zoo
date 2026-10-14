"""Preview cards carry the motif as the main figure (feature 016, US5; FR-025, FR-026)."""

from __future__ import annotations

from site_fixture import MODEL

from mobility_model_zoo.site import context, og


def test_cards_get_their_motif_through_the_resolver(site_env):
    reg = site_env.reg
    site_env.edit_yaml(f"zoo/models/{MODEL}/site.yaml", lambda d: d.pop("motif", None))
    cards = {
        c["slug"]: c for c in og.cards(reg, context.load_site_config(reg), context.site_models(reg), [])
    }
    assert cards[MODEL]["motif"] == "scout-large.svg"  # no site.yaml key needed (FR-025)
    assert cards["zoo"]["motif"] is None


def test_card_page_centres_one_opaque_motif(built):
    html = (built.out / og.CARD_DIR / f"{MODEL}.html").read_text(encoding="utf-8")
    assert html.count('data-motif="scout-large.svg"') == 1
    assert '<div class="og-motif" data-og="motif"><span class="plate plate-og"' in html
    assert "og-motif-l" not in html and "og-motif-r" not in html
    css = (built.out / "assets/css/og.css").read_text(encoding="utf-8")
    assert "opacity: .55" not in css
