"""Images on the start page and model pages (feature 016, US1 and US3; checks I3, X1, C1)."""

from __future__ import annotations

import re

from site_fixture import MODEL
from test_images_record import make_record
from test_images_series import write_series

from mobility_model_zoo.site import check, images


def with_images(site_env, model_image: bool = True):
    write_series(site_env.root)
    make_record(site_env.root, "hero", ("start-hero",))
    make_record(site_env.root, "pd", ("topic:productdev",), "3:2")
    if model_image:
        make_record(site_env.root, "scout", (f"model:{MODEL}",), "3:2")
    site_env.build()
    return site_env


def img(html: str, record_id: str) -> dict[str, str]:
    m = re.search(rf'<img data-image="{record_id}"([^>]*)>', html)
    assert m, f"no image {record_id}"
    return dict(re.findall(r'(\w[\w-]*)="([^"]*)"', m.group(1)))


def test_start_page_without_images_keeps_the_text_hero(built):
    html = built.html("index.html")
    assert "hero-stage" not in html and "data-image" not in html
    assert "credits/" not in html and "Images are AI-generated" not in html


def test_hero_and_topic_images_with_srcset_and_lazy_loading(site_env):
    env = with_images(site_env)
    html = env.html("index.html")
    hero = img(html, "hero")
    assert hero["fetchpriority"] == "high" and "loading" not in hero
    assert hero["srcset"].split(", ") == [f"assets/images/hero-{w}.webp {w}w" for w in images.WIDTHS]
    assert (hero["width"], hero["height"]) == ("1600", "900") and hero["alt"].endswith(
        "(AI-generated image)"
    )
    assert hero["style"] == "object-position:50% 55%"
    pd = img(html, "pd")
    assert pd["loading"] == "lazy" and (pd["width"], pd["height"]) == ("300", "200")
    assert html.count("data-image=") == 2
    assert (env.out / "assets/images/hero-960.webp").exists()
    assert (env.out / "assets/images/set.json").exists()


def test_model_page_stage_and_fallback_to_the_topic(site_env):
    env = with_images(site_env)
    html = env.html(f"models/{MODEL}/index.html")
    assert '<figure class="stage"><img data-image="scout"' in html
    assert 'class="plate plate-hero" data-motif="scout-large.svg"' in html
    # without its own image the model falls back to its topic's image (FR-016, Story 3)
    import shutil

    shutil.rmtree(env.root / images.IMAGES_DIR / "scout")
    env.build()
    html = env.html(f"models/{MODEL}/index.html")
    assert '<figure class="stage"><img data-image="pd"' in html
    assert "credits/#pd" in html


def test_warnings_name_the_missing_placements(site_env):
    from mobility_model_zoo.site.build import build

    said = []
    write_series(site_env.root)
    make_record(site_env.root, "hero", ("start-hero",))
    build(site_env.reg, site_env.out, offline=True, say=said.append, images=False)
    assert "warning: no image for topic:productdev" in said
    assert f"warning: no image for model:{MODEL}, motif only" in said


def test_static_checks_pass_with_images(site_env):
    env = with_images(site_env)
    for fn in (check.check_image_markup, check.check_credits):
        assert list(fn(env.reg, env.out)) == []
    assert list(check.check_text_on_images(env.out)) == []


def test_images_elsewhere_orphans_and_text_on_images_are_found(site_env):
    env = with_images(site_env)
    quick = env.out / "quickstart" / "index.html"
    quick.write_text(quick.read_text().replace("</main>", '<img data-image="hero" alt="x"></main>'))
    (env.out / "assets/images/orphan-480.webp").write_bytes(b"RIFF")
    index = env.out / "index.html"
    index.write_text(
        index.read_text().replace(
            '<figure class="hero-stage">', '<figure class="hero-stage"><b>On the image</b>'
        )
    )
    found = {f[0] + " " + f[2] for f in check.check_image_markup(env.reg, env.out)}
    assert any("only the start, model and credits" in x for x in found)
    assert any("orphan file" in x for x in found)
    assert any("has no width" in x or "no width" in x for x in found)
    assert list(check.check_text_on_images(env.out))[0][0] == "X1"


def test_credits_page_and_footer_disclosure(site_env):
    env = with_images(site_env)
    credits = env.html("credits/index.html")
    for rid in ("hero", "pd", "scout"):
        assert f'id="{rid}"' in credits
    from html import unescape

    credits = unescape(credits)
    assert (
        "AI-generated with Qwen/Qwen-Image-2512 (Apache-2.0) on the project's own hardware "
        "(dgx-spark), 2026-10-14" in credits
    )
    assert "CC0 1.0" in credits
    index = env.html("index.html")
    assert 'href="credits/">Images are AI-generated · Image credits</a>' in index
    assert (
        '<details class="credits wrap"><summary>Images on this page are AI-generated</summary>' in index
    )
    page = check.parse(env.out / "index.html")
    assert any("AI-generated" in t for t in page.footer_link_text)
    quick = env.html("quickstart/index.html")
    assert "Images on this page" not in quick  # no images, no block (FR-007)
