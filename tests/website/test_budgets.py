"""The counting rule of the depth budgets (feature 013, research R5)."""

from __future__ import annotations

from mobility_model_zoo.site import budgets


def test_words_counts_placeholders_as_one():
    assert budgets.words("Runs in {metric:performance.latency_9k_chars_s} on four cores") == 6
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
        "<details open><summary>open</summary><p>shown words</p></details>"
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
