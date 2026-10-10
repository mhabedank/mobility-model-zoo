"""The model page (contracts/site-tree.md): sections in order, facts from the release (US1)."""

from __future__ import annotations

import re

from site_fixture import MODEL, VERSION

SECTIONS = [
    "top",
    "why",
    "quickstart",
    "interface",
    "examples",
    "quality",
    "limits",
    "provenance",
    "versions",
    "cite",
]


def test_sections_in_order(built):
    html = built.html(f"models/{MODEL}/index.html")
    positions = [html.find(f'id="{s}"') for s in SECTIONS]
    assert all(p > 0 for p in positions), dict(zip(SECTIONS, positions, strict=True))
    assert positions == sorted(positions)


def test_quickstart_is_pinned_and_shows_the_published_output(built):
    html = built.html(f"models/{MODEL}/index.html")
    assert f"@{MODEL}/v{VERSION}" in html
    assert f"revision=&#34;v{VERSION}&#34;" in html or f'revision="v{VERSION}"' in html
    assert (
        "02-depot-charging.txt" in html
        and "&#34;output_format_version&#34;: &#34;jtbd-span-v1&#34;" in html
    )


def test_numbers_come_with_their_reference(built):
    html = built.html(f"models/{MODEL}/index.html")
    assert "0.7234" in html and "0.6672" in html
    assert "frontier reference models" in html and "pilot-v2" in html
    notes = re.findall(r'<li id="fn-(\d+)">', html)
    refs = set(re.findall(r'href="#fn-(\d+)"', html))
    assert refs and refs <= set(notes)


def test_deterministic_checks_and_contested_items_are_visible(built):
    html = built.html(f"models/{MODEL}/index.html")
    checks = html[html.find('class="checks"') : html.find('class="grid3"', html.find('class="checks"'))]
    for text in ("pilot-v2", "verbatim", "valid against", "consistency", "disagree on"):
        assert text in checks, text


def test_charts_have_value_tables(built):
    html = built.html(f"models/{MODEL}/index.html")
    assert html.count('<figure class="chart">') == 2
    assert html.count("Values of this chart") == 2
    assert "Claude Opus 5.5 (reference)" in html  # label from the declared label file


def test_without_chart_declaration_there_are_no_charts(site_env):
    site_env.edit_yaml(f"zoo/models/{MODEL}/site.yaml", lambda p: p.pop("charts"))
    site_env.build()
    assert '<figure class="chart">' not in site_env.html(f"models/{MODEL}/index.html")


def test_facts_file_lists_every_rendered_metric(built):
    import json

    rows = json.loads((built.out / "_build" / "facts.json").read_text())
    assert {r["metric"] for r in rows} >= {"comparison_composite", "latency_9k_chars_s", "peak_ram_gb"}
    assert all(r["source"].startswith(f"zoo/models/{MODEL}/results/{VERSION}/") for r in rows)


def test_unpublished_model_has_no_page(built):
    assert not (built.out / "models" / "picket-forest").exists()
    assert (built.out / "formats" / "jtbd-span-v1" / "index.html").exists()
    assert (built.out / "404.html").exists()
