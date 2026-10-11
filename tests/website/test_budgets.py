"""The counting rule of the depth budgets (feature 014, research R5)."""

from __future__ import annotations

from mobility_model_zoo.site import budgets


def test_words_counts_placeholders_as_value_and_unit():
    assert budgets.words("Runs in {metric:performance.latency_9k_chars_s} on four cores") == 7
    assert budgets.words("  ") == 0


def test_sentences():
    assert budgets.sentences("One. Two! Three?") == 3
    assert budgets.sentences("No full stop") == 1
    assert budgets.sentences("Version 0.2 is here.") == 1
    assert budgets.sentences("") == 0


def test_visible_words_skips_budget_skip_and_closed_details():
    root = budgets.tree(
        "<section><p>one two three</p>"
        '<div data-budget="skip"><span>chip chip</span></div>'
        "<details><summary>more here</summary><p>hidden hidden hidden</p></details>"
        "<details open><summary>open</summary><p>shown words<sup><a>1</a></sup></p></details>"
        "<script>var x = 1;</script></section>"
    )
    section = root.find(lambda n: n.tag == "section")
    assert budgets.visible_words(section) == 3 + 2 + 1 + 2
    assert "hidden" in section.text()
    assert "chip" not in section.text(visible=True)


def test_tree_handles_void_elements_and_layers():
    root = budgets.tree(
        '<main><section id="top" data-layer="overview"><img src="a.svg" alt="x"><br><p>hi</p></section>'
        '<section id="quality" data-layer="quality"><p>q</p></section></main>'
    )
    assert [n.get("data-layer") for n in budgets.layers(root)] == ["overview", "quality"]
    assert root.by_id("quality").text() == "q"
    assert root.by_id("top").text() == "hi"


def test_status_words():
    assert budgets.STATUS_WORDS.search("An Experimental detector")
    assert budgets.STATUS_WORDS.search("not production ready")
    assert not budgets.STATUS_WORDS.search("A detector for experiments")


def test_words_before_quality_on_the_fixture_page(built):
    from site_fixture import MODEL

    from mobility_model_zoo.site import depth

    root = budgets.tree(built.html(f"models/{MODEL}/index.html"))
    assert 0 < depth.words_before_quality(root) <= budgets.WORDS_BEFORE_QUALITY
    assert list(depth.check_words_before_quality(built.reg, built.out)) == []


def test_long_tagline_and_audience_break_the_page_budget(site_env):
    from site_fixture import MODEL

    from mobility_model_zoo.site import depth

    filler = " ".join(["word"] * 100)
    site_env.edit_yaml(f"zoo/models/{MODEL}/site.yaml", lambda s: s.update(audience=filler))
    site_env.build()
    found = list(depth.check_words_before_quality(site_env.reg, site_env.out))
    assert any("before the quality layer" in f[2] for f in found)
