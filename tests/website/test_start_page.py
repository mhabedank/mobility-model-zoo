"""The start page (US3 of feature 008, US2 of feature 015): topics, tiles of published models, the
"Coming next" cards from the roadmap, a new model needs no code change."""

from __future__ import annotations

import re
import shutil

from site_fixture import MODEL, VERSION


def tiles(html: str) -> dict[str, str]:
    """Tile name -> its HTML, from the opening tag up to the next tile."""
    found = {}
    starts = [m.start() for m in re.finditer(r'<(a|div) class="tile"', html)]
    for i, start in enumerate(starts):
        chunk = html[start : starts[i + 1] if i + 1 < len(starts) else html.find("</section>", start)]
        found[re.search(r'class="h3"[^>]*>([^<]+)<', chunk).group(1)] = chunk
    return found


def test_topics_and_tiles(built):
    html = built.html("index.html")
    for title in ("Product development", "Automotive security", "Condition monitoring"):
        assert title in html
    assert "Pipeline tests" not in html and "sandbox-pipeline-tiny" not in html
    t = tiles(html)
    assert t[MODEL].startswith(f'<a class="tile" href="models/{MODEL}/"') and VERSION in t[MODEL]
    # feature 015: an unpublished model is a "Coming next" card, not a tile (FR-019)
    assert "picket-forest" not in t
    assert "picket-forest" in [c["name"] for c in minis(html)]


def minis(html: str) -> list[dict[str, str]]:
    """The "Coming next" cards in page order."""
    out = []
    for m in re.finditer(r'<a class="mini" href="([^"]+)">(.*?)</a>', html):
        body = m.group(2)
        out.append(
            {
                "href": m.group(1),
                "name": re.search(r'class="mini-name">([^<]+)<', body).group(1),
                "horizon": re.search(r'class="chip">([^<]+)<', body).group(1),
                "body": body,
            }
        )
    return out


def test_coming_next_cards(built):
    html = built.html("index.html")
    cards = minis(html)
    assert [(c["name"], c["horizon"], c["href"]) for c in cards] == [
        ("picket-forest", "Q4 2026", "roadmap/#picket-forest"),
        ("hum-bearing", "H1 2027", "roadmap/#hum-bearing"),
        ("picket-signal", "H2 2027", "roadmap/#picket-signal"),
    ]
    assert "working name" in cards[1]["body"] and "working name" not in cards[0]["body"]
    for c in cards:  # no version, no sentence, no digits apart from the horizon label
        assert not re.search(r"\d", c["body"].replace(c["horizon"], ""))
    assert "1 published · 3 coming next." in html
    assert 'href="roadmap/">See the roadmap' in html
    assert "Reader test" not in html  # updates never appear as cards


def test_published_entry_leaves_the_cards(site_env):
    path = site_env.root / "zoo" / "models" / "picket-forest" / "releases" / "0.1.0.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "model: picket-forest\nversion: 0.1.0\ndate: 2026-10-10\nstatus: experimental\n"
        "published:\n  tag: v0.1.0\n  published_at: 2026-10-10T10:00:00Z\n",
        encoding="utf-8",
    )
    from mobility_model_zoo.site import context, roadmap

    record = roadmap.load(site_env.reg)
    assert [e["id"] for e in roadmap.page_context(site_env.reg, record)["upcoming"]] == [
        "hum-bearing",
        "picket-signal",
    ]
    assert context.status(site_env.reg, "picket-forest")[0] == "published"


def test_deprecated_model_is_marked(site_env):
    site_env.edit_yaml(
        f"zoo/models/{MODEL}/releases/{VERSION}.yaml",
        lambda r: r.update(deprecated={"reason": "A bug in offsets.", "successor": None}),
    )
    site_env.build()
    assert "deprecated" in tiles(site_env.html("index.html"))[MODEL]
    assert "A bug in offsets." in site_env.html(f"models/{MODEL}/index.html")


def test_new_published_model_needs_no_code_change(site_env):
    src = site_env.root / "zoo" / "models" / MODEL
    dst = site_env.root / "zoo" / "models" / "scout-small"
    shutil.copytree(src, dst)
    site_env.edit_yaml(
        "zoo/models/scout-small/model.yaml", lambda m: m.update(name="scout-small", variant="small")
    )
    for rel in ("releases/0.1.2.yaml",):
        site_env.edit_yaml(f"zoo/models/scout-small/{rel}", lambda r: r.update(model="scout-small"))
    cache = site_env.root / ".cache" / "site"
    shutil.copytree(cache / MODEL, cache / "scout-small")
    site_env.build()
    assert (site_env.out / "models" / "scout-small" / "index.html").exists()
    assert 'href="models/scout-small/"' in site_env.html("index.html")
