"""Layer 2 of the model page: quality and speed, figures first (feature 013, US2, check D3)."""

from __future__ import annotations

import json

from site_fixture import MODEL

from mobility_model_zoo.site import budgets, charts, depth


def _quality(env, html=None) -> budgets.Node:
    root = budgets.tree(html or env.html(f"models/{MODEL}/index.html"))
    return root.find(lambda n: n.get("data-layer") == "quality")


def _findings(env, mutate=None):
    html = env.html(f"models/{MODEL}/index.html")
    return depth.quality_findings(
        f"models/{MODEL}/index.html", budgets.tree(mutate(html) if mutate else html)
    )


def test_quality_follows_the_overview_with_figures_charts_and_a_link(built):
    layer = _quality(built)
    figures = layer.find_all(lambda n: "metric" in n.classes)
    assert 1 <= len(figures) <= budgets.HEADLINE_FIGURES_MAX
    assert len(layer.find_all(lambda n: n.tag == "figure")) == 2
    assert layer.find(lambda n: n.tag == "a" and n.get("href") == "#metrics")
    assert _findings(built) == []
    assert list(depth.check_quality(built.reg, built.out)) == []


def test_full_metric_tables_are_in_the_details_layer(built):
    root = budgets.tree(built.html(f"models/{MODEL}/index.html"))
    metrics = root.by_id("metrics")
    details = root.find(lambda n: n.get("data-layer") == "details")
    assert metrics is not None and details.by_id("metrics") is metrics
    assert len(metrics.find_all(lambda n: n.tag == "table")) == 2
    quality = _quality(built)
    tables = quality.find_all(lambda n: n.tag == "table")
    assert all(any(a.tag == "details" for a in _ancestors(t)) for t in tables)


def _ancestors(node):
    while node.parent is not None:
        node = node.parent
        yield node


def test_table_outside_a_chart_prose_before_figures_and_missing_link_fail(built):
    def add_table(h):
        return h.replace(
            '<div class="checks"', '<table><tr><td>x</td></tr></table><div class="checks"', 1
        )

    assert any(f[0] == "D3" and "table" in f[2] for f in _findings(built, add_table))

    def add_prose(h):
        return h.replace(
            '<div class="checks"', '<p>One sentence. Another one.</p><div class="checks"', 1
        )

    assert any(f[0] == "D3" and "sentence" in f[2] for f in _findings(built, add_prose))
    assert any(
        f[0] == "D3" and "#metrics" in f[2]
        for f in _findings(built, lambda h: h.replace('href="#metrics"', 'href="#x"'))
    )


def test_too_many_figures_fail(built):
    def five(h):
        i = h.index('<div class="metric"')
        j = h.index("</div></div>", i) + len("</div></div>")
        return h[:j] + h[i:j] * 4 + h[j:]

    assert any(f[0] == "D3" and "headline figures" in f[2] for f in _findings(built, five))


def test_comparison_bar_has_both_values_on_one_scale():
    svg = str(charts.comparison_bar(0.72, 0.67, "", "scout-large", "best zero-shot small model"))
    assert 'role="img"' in svg
    assert "0.72" in svg and "0.67" in svg and "best zero-shot small model" in svg
    widths = [float(w) for w in __import__("re").findall(r'width="([0-9.]+)" height="10"', svg)]
    assert len(widths) == 2 and abs(widths[1] / widths[0] - 0.67 / 0.72) < 0.02


def test_cards_with_a_comparison_have_a_bar_and_add_no_fact(built):
    layer = _quality(built)
    for card in layer.find_all(lambda n: "metric" in n.classes):
        has_compare = card.find(lambda n: "ref" in n.classes) is not None
        has_bar = card.find(lambda n: n.tag == "svg" and n.get("role") == "img") is not None
        assert has_compare == has_bar
    keys = [r["key"] for r in json.loads((built.out / "_build" / "facts.json").read_text())]
    assert not any(k.startswith("bar:") for k in keys)
