"""Layers 5 and 6 of the model page: reference and details, old anchors (feature 014, US5, D3, D5)."""

from __future__ import annotations

from site_fixture import MODEL, VERSION

from mobility_model_zoo.site import budgets, depth

PAGE = f"models/{MODEL}/index.html"


def _root(env) -> budgets.Node:
    return budgets.tree(env.html(PAGE))


def test_six_layers_in_order_and_old_anchors_resolve(built):
    root = _root(built)
    assert [n.get("data-layer") for n in budgets.layers(root)] == list(budgets.LAYERS)
    assert depth.order_findings(PAGE, root) == []
    assert list(depth.check_order(built.reg, built.out)) == []
    ids = {n.get("id") for n in root.iter() if n.get("id")}
    for anchor in (*budgets.ANCHORS, "ex1", "fn-1"):
        assert anchor in ids, anchor
    details = root.by_id("details")
    for ident in ("metrics", "notes", "provenance", "versions", "cite"):
        assert details.by_id(ident) is not None, ident


def test_interface_is_short_and_links_the_format_page(built):
    interface = _root(built).by_id("interface")
    assert interface.find(lambda n: n.tag == "table") is None
    assert interface.find(lambda n: n.tag == "a" and "/formats/jtbd-span-v1/" in (n.get("href") or ""))
    fmt = built.html("formats/jtbd-span-v1/index.html")
    assert 'class="tbl"' in fmt  # the field table lives on the format page


def test_layer_order_and_field_table_findings(built):
    html = built.html(PAGE)
    swapped = html.replace('data-layer="quality"', 'data-layer="tmp"').replace(
        'data-layer="limits"', 'data-layer="quality"'
    )
    swapped = swapped.replace('data-layer="tmp"', 'data-layer="limits"')
    assert any(f[0] == "D5" for f in depth.order_findings(PAGE, budgets.tree(swapped)))
    table = html.replace('<p class="reference-link">', "<table><tr><td>f</td></tr></table><p>", 1)
    assert any("field table" in f[2] for f in depth.order_findings(PAGE, budgets.tree(table)))
    gone = html.replace('id="cite"', 'id="citation"')
    assert any("#cite" in f[2] for f in depth.order_findings(PAGE, budgets.tree(gone)))


def test_model_without_examples_has_no_empty_heading(built):
    """A published model always has examples (B4); the template still renders none as nothing."""
    from mobility_model_zoo.site.build import environment

    html = environment().get_template("partials/viewer.html.j2").render(p={"examples": []})
    assert 'id="examples"' in html and "Worked examples" not in html
    empty = (
        '<div class="sec" id="examples"><div class="wrap">'
        '<div class="eyebrow">Worked examples</div></div></div>'
    )
    page = built.html(PAGE)
    i, j = (
        page.index('<div class="sec" id="examples">'),
        page.index("</section>", page.index('id="reference"')),
    )
    findings = depth.order_findings(PAGE, budgets.tree(page[:i] + empty + page[j:]))
    assert any("empty 'Worked examples'" in f[2] for f in findings)


def test_deprecation_banner_stays_above_main(site_env):
    site_env.edit_yaml(
        f"zoo/models/{MODEL}/releases/{VERSION}.yaml",
        lambda r: r.update(status="deprecated", deprecated={"reason": "Superseded.", "successor": None}),
    )
    site_env.build()
    html = site_env.html(PAGE)
    assert 0 < html.find('class="banner"') < html.find("<main")
    chip = _root(site_env).find(lambda n: n.get("data-status") is not None)
    assert chip.get("data-status") == "experimental"  # the status the version had before
