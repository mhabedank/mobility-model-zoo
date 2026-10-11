"""Layer 4 of the model page: the quickstart after the limits, no code before them (feature 013, US4)."""

from __future__ import annotations

from site_fixture import MODEL

from mobility_model_zoo.site import budgets, depth

PAGE = f"models/{MODEL}/index.html"


def test_quickstart_is_layer_four_with_install_run_and_output(built):
    root = budgets.tree(built.html(PAGE))
    order = [n.get("data-layer") for n in budgets.layers(root)]
    assert order.index("quickstart") == 3
    layer = root.by_id("quickstart")
    for ident in ("qs-install", "qs-run", "qs-out"):
        assert layer.by_id(ident) is not None, ident


def test_jump_link_from_the_first_screen(built):
    overview = budgets.tree(built.html(PAGE)).by_id("top")
    assert overview.find(lambda n: n.tag == "a" and n.get("href") == "#quickstart")


def test_no_code_before_the_limits(built):
    root = budgets.tree(built.html(PAGE))
    assert depth.code_findings(PAGE, root) == []
    assert list(depth.check_code_order(built.reg, built.out)) == []
    html = built.html(PAGE).replace('<p class="lead">', '<pre>pip install</pre><p class="lead">', 1)
    assert any("code before #limits" in f[2] for f in depth.code_findings(PAGE, budgets.tree(html)))
