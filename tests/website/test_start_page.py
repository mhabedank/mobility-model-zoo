"""The start page (US3): topics, model tiles by status, a new model needs no code change."""

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
    assert t["picket-forest"].startswith('<div class="tile">') and "in progress" in t["picket-forest"]
    assert "none yet" in t["picket-forest"]


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
