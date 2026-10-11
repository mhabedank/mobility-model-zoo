"""Preview image cards, page metadata and addresses without a browser (feature 012)."""

from __future__ import annotations

import json
import re
from importlib import metadata

from site_fixture import MODEL

from mobility_model_zoo.site import og
from mobility_model_zoo.site.check import og_meta

CANONICAL = "https://mhabedank.github.io/mobility-model-zoo/"


def manifest(env) -> dict:
    return json.loads((env.out / og.MANIFEST).read_text(encoding="utf-8"))


def files(env) -> dict[str, str]:
    return {c["page"]: c["file"] for c in manifest(env)["cards"]}


def test_cards_cover_exactly_the_shareable_pages(site_env):
    pages = [c["page"] for c in og.site_cards(site_env.reg)]
    assert pages == ["", f"models/{MODEL}/", "formats/jtbd-span-v1/"]  # no unpublished, no sandbox


def test_model_card_labels_and_alt(site_env):
    card = next(c for c in og.site_cards(site_env.reg) if c["kind"] == "model")
    assert card["labels"] == ["experimental"]  # the fixture record: experimental, commercial
    assert card["alt"] == f"{MODEL}, Mobility Model Zoo: {card['line']} (experimental)"
    fmt = next(c for c in og.site_cards(site_env.reg) if c["kind"] == "format")
    assert fmt["alt"].startswith("Output format jtbd-span-v1, Mobility Model Zoo: ")


def test_labels_follow_the_record(site_env):
    site_env.edit_yaml(f"zoo/models/{MODEL}/releases/0.1.2.yaml", lambda r: r.update(status="released"))
    site_env.edit_yaml(
        f"zoo/models/{MODEL}/model.yaml", lambda m: m.update(usage_class="non-commercial")
    )
    card = next(c for c in og.site_cards(site_env.reg) if c["kind"] == "model")
    assert card["labels"] == ["non-commercial"]


def test_input_hash_follows_its_inputs(tmp_path):
    css = tmp_path / "a.css"
    css.write_text("body{}", encoding="utf-8")
    html = '<link rel="stylesheet" href="a.css"><p>scout-large</p>'
    first = og.input_hash(html, tmp_path, "playwright 1")
    assert og.input_hash(html, tmp_path, "playwright 1") == first
    assert og.input_hash(html.replace("scout", "other"), tmp_path, "playwright 1") != first
    assert og.input_hash(html, tmp_path, "playwright 2") != first
    css.write_text("body{color:red}", encoding="utf-8")
    assert og.input_hash(html, tmp_path, "playwright 1") != first


def test_renderer_id_does_not_depend_on_an_installed_browser(site_env, monkeypatch):
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    installed = og.renderer_id(repo)

    def missing(_name):
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(og.metadata, "version", missing)
    assert og.renderer_id(repo) == installed  # from uv.lock


def test_model_page_metadata(built):
    meta = og_meta(built.out / "models" / MODEL / "index.html")
    card = next(c for c in manifest(built)["cards"] if c["kind"] == "model")
    assert re.fullmatch(rf"{CANONICAL}assets/og/{MODEL}-[0-9a-f]{{12}}\.png", meta["og:image"])
    assert meta["og:image"] == CANONICAL + card["file"] == meta["twitter:image"]
    assert (meta["og:image:width"], meta["og:image:height"]) == ("1200", "630")
    assert meta["og:image:type"] == "image/png"
    assert meta["twitter:card"] == "summary_large_image"
    assert meta["og:image:alt"] == meta["twitter:image:alt"] == card["alt"]


def test_start_format_and_404_cards(built):
    found = files(built)
    assert re.fullmatch(r"assets/og/zoo-[0-9a-f]{12}\.png", found[""])
    assert re.fullmatch(
        r"assets/og/format-jtbd-span-v1-[0-9a-f]{12}\.png", found["formats/jtbd-span-v1/"]
    )
    assert og_meta(built.out / "404.html")["og:image"] == CANONICAL + found[""]
    assert "404.html" not in found
    for page in built.out.rglob("*.html"):
        assert "assets/img/og.png" not in page.read_text(encoding="utf-8")


def test_new_model_gets_card_and_meta(site_env):
    site_env.clone_model(MODEL, "scout-mini")
    site_env.build()
    meta = og_meta(site_env.out / "models" / "scout-mini" / "index.html")
    assert re.search(r"assets/og/scout-mini-[0-9a-f]{12}\.png$", meta["og:image"])
    assert "models/scout-mini/" in files(site_env)


def test_address_changes_with_content(site_env):
    site_env.build()
    first = files(site_env)
    site_env.build()
    assert files(site_env) == first  # SC-006

    site_env.edit_yaml(f"zoo/models/{MODEL}/site.yaml", lambda p: p.update(share_line="Finds jobs."))
    site_env.build()
    second = files(site_env)
    assert second[f"models/{MODEL}/"] != first[f"models/{MODEL}/"]
    assert {k: v for k, v in second.items() if k != f"models/{MODEL}/"} == {
        k: v for k, v in first.items() if k != f"models/{MODEL}/"
    }

    site_env.edit_yaml(
        f"zoo/models/{MODEL}/releases/0.1.2.yaml",
        lambda r: r.update(deprecated={"reason": "superseded", "successor": None}),
    )
    site_env.build()
    card = next(c for c in manifest(site_env)["cards"] if c["kind"] == "model")
    assert "deprecated" in card["labels"]
    assert card["file"] != second[f"models/{MODEL}/"]


def test_site_weight_ignores_preview_images(built):
    from mobility_model_zoo.site.check import check_size

    folder = built.out / og.OG_DIR
    folder.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        (folder / f"big-{i}.png").write_bytes(b"\0" * 150_000)
    assert list(check_size(built.out)) == []


def test_share_line_errors_stop_the_build(site_env):
    import pytest

    from mobility_model_zoo.release.errors import GateFailed

    site_env.edit_yaml("zoo/site.yaml", lambda s: s.update(share_line="Since 2026 for everyone"))
    with pytest.raises(GateFailed) as e:
        site_env.build()
    assert 'B6 zoo: share line contains the number "2026"' in e.value.failures
