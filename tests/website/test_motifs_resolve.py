"""One resolver for every motif use (feature 016, FR-025; research R10)."""

from __future__ import annotations

from site_fixture import MODEL

from mobility_model_zoo.site import motifs


def test_site_yaml_key_wins_then_file_by_name(site_env):
    assert motifs.resolve(site_env.reg, MODEL) == "scout-large.svg"  # site.yaml names it
    assert motifs.resolve(site_env.reg, "picket-forest") == "picket-forest.svg"  # file fallback
    assert motifs.resolve(site_env.reg, "no-such-model") is None


def test_a_site_yaml_key_that_names_a_missing_file_falls_back(site_env):
    site_env.edit_yaml(f"zoo/models/{MODEL}/site.yaml", lambda d: d.update(motif="missing.svg"))
    assert motifs.resolve(site_env.reg, MODEL) == "scout-large.svg"


def test_roadmap_entry_tries_model_then_id_then_name(site_env):
    reg = site_env.reg
    assert (
        motifs.resolve_entry(reg, {"model": "picket-forest", "id": "x", "name": "y"})
        == "picket-forest.svg"
    )
    assert (
        motifs.resolve_entry(reg, {"id": "hum-bearing", "name": "Bearing monitor"}) == "hum-bearing.svg"
    )
    assert motifs.resolve_entry(reg, {"id": "x", "name": "picket-signal"}) == "picket-signal.svg"
    assert motifs.resolve_entry(reg, {"id": "x", "name": "y"}) is None


def test_every_shipped_motif_is_a_file(site_env):
    files = motifs.files()
    assert {"scout-large", "picket-forest", "hum-bearing", "picket-signal", "rough-road"} <= set(files)
    assert all(p.suffix == ".svg" for p in files.values())
