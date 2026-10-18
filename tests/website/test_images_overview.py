"""The local pool overview and the themed list (feature 019, US3; FR-019)."""

from __future__ import annotations

from test_images_record import make_record
from test_images_series import write_series

from mobility_model_zoo.site import images
from mobility_model_zoo.site import images_triage as rounds


def test_overview_groups_by_theme_with_counts_and_relative_links(site_env):
    write_series(site_env.root)
    make_record(site_env.root, "rail-tram", (), "16:9", "rail", "tram", source_file=False)
    make_record(site_env.root, "pd-dash", ("topic:productdev",), "3:2", "private-road", "dashboard")
    out = rounds.write_overview(site_env.reg, site_env.root / ".cache" / "site" / "pool.html")
    html = out.read_text(encoding="utf-8")
    assert html.index('id="rail"') < html.index('id="private-road"') < html.index('id="water"')
    assert "1 of minimum 10" in html and "under minimum" in html
    assert "<script" not in html and "no records yet" in html  # empty themes still listed
    assert 'class="placed">topic:productdev' in html
    assert html.count("<figure>") == 2
    import re

    src = re.search(r'<img src="([^"]+rail-tram-480\.webp)"', html).group(1)
    assert (out.parent / src).resolve().exists()
    # over the cap: two of two records in one theme
    make_record(site_env.root, "pd-two", (), "3:2", "private-road", "workshop", source_file=False)
    html = rounds.write_overview(site_env.reg, out).read_text(encoding="utf-8")
    assert "over cap" in html


def test_coverage_counts_only_records_of_known_themes(site_env):
    write_series(site_env.root)
    make_record(site_env.root, "a", (), "3:2", "rail", "tram", source_file=False)
    records, _ = images.load_records(site_env.reg)
    assert images.coverage(records)["rail"]["count"] == 1
    assert sum(c["count"] for c in images.coverage(records).values()) == 1
