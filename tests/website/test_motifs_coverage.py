"""Every model the site shows has a motif on a plate (feature 016, US2; checks M1, sizes)."""

from __future__ import annotations

import re

import pytest
from site_fixture import MODEL

from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.site import motifs, roadmap


def test_every_shown_name_resolves(site_env):
    plan = roadmap.load_and_check(site_env.reg)
    names = {n for n, _ in motifs.shown_names(site_env.reg, plan)}
    assert {MODEL, "picket-forest", "hum-bearing", "picket-signal"} <= names
    assert motifs.coverage(site_env.reg, plan) == []


def test_a_roadmap_name_without_a_motif_fails_the_build(site_env, monkeypatch):
    real = motifs.resolve

    def resolve(reg, name):
        return None if name == "hum-bearing" else real(reg, name)

    monkeypatch.setattr(motifs, "resolve", resolve)
    with pytest.raises(GateFailed) as e:
        site_env.build()
    assert any(f.startswith("M1 hum-bearing") and "roadmap entry" in f for f in e.value.failures)


def test_tiles_roadmap_and_mini_cards_carry_plates(built):
    index = built.html("index.html")
    tile = re.search(rf'<a class="tile" href="models/{MODEL}/">(.*?)</a>', index, re.S).group(1)
    assert (
        '<span class="plate plate-72" data-motif="scout-large.svg"><svg width="64" height="64"' in tile
    )
    mini = re.search(r'<a class="mini" href="roadmap/#hum-bearing">(.*?)</a>', index, re.S).group(1)
    assert 'class="plate plate-48" data-motif="hum-bearing.svg"><svg width="40"' in mini
    road = built.html("roadmap/index.html")
    assert 'class="plate plate-48" data-motif="picket-signal.svg"><svg width="40"' in road


def test_model_hero_shows_the_plate_without_an_image(built):
    html = built.html(f"models/{MODEL}/index.html")
    assert (
        '<div class="stage-alone"><span class="plate plate-hero" data-motif="scout-large.svg">' in html
    )
    assert "-hero.svg" not in html  # the hero draws the same motif larger (research R10)
