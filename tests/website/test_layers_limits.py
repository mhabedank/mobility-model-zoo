"""Layer 3 of the model page: limits and status before any code (feature 013, US3, checks D1-D3)."""

from __future__ import annotations

import json

from site_fixture import MODEL, VERSION

from mobility_model_zoo.site import budgets, context, depth

PAGE = f"models/{MODEL}/index.html"
MODEL_YAML = f"zoo/models/{MODEL}/model.yaml"
RECORD = f"zoo/models/{MODEL}/releases/{VERSION}.yaml"
MEASURED = {
    "criterion": "Item matching with the reference models",
    "target": {"op": ">=", "value": 0.7, "unit": "", "source": "zoo/models/scout-large/model.yaml"},
    "measured": "{metric:quality.agreement_item_matching}",
}


def _limits(env) -> budgets.Node:
    return budgets.tree(env.html(PAGE)).find(lambda n: n.get("data-layer") == "limits")


def _d1(env):
    return [f for f in depth.check_short_forms(env.reg) if f[0] == "D1"]


# ---- D1 -------------------------------------------------------------------------------------------
def test_fixture_short_forms_pass(site_env):
    assert _d1(site_env) == []


def test_experimental_without_unmet_criteria_fails(site_env):
    site_env.edit_yaml(MODEL_YAML, lambda m: m["card"].pop("unmet_criteria"))
    assert any("unmet" in f[2] for f in _d1(site_env))


def test_released_with_unmet_criteria_fails(site_env):
    site_env.edit_yaml(RECORD, lambda r: r.update(status="released"))
    assert any("released" in f[2] for f in _d1(site_env))


def test_missing_not_for_or_limits_short_fails(site_env):
    site_env.edit_yaml(MODEL_YAML, lambda m: m["card"].pop("not_for"))
    assert any("not_for" in f[2] for f in _d1(site_env))
    site_env.edit_yaml(MODEL_YAML, lambda m: m["card"].pop("limits_short"))
    assert any("limits_short" in f[2] for f in _d1(site_env))


def test_unresolvable_measure_or_missing_source_fails(site_env):
    bad = {**MEASURED, "measured": "{metric:quality.not_measured}"}
    site_env.edit_yaml(MODEL_YAML, lambda m: m["card"].update(unmet_criteria=[bad]))
    assert any("not_measured" in f[2] for f in _d1(site_env))
    bad = {**MEASURED, "target": {**MEASURED["target"], "source": "topics/none.md"}}
    site_env.edit_yaml(MODEL_YAML, lambda m: m["card"].update(unmet_criteria=[bad]))
    assert any("topics/none.md" in f[2] for f in _d1(site_env))


# ---- the short form on the page ----------------------------------------------------------------
def test_limits_open_with_the_short_form_and_keep_the_full_texts(built):
    layer = _limits(built)
    short = layer.find(lambda n: n.get("data-short") == "limits")
    assert short is not None
    text = short.text()
    assert "Experimental: not ready for production use." in text
    assert "Reader test passed by a person outside the project: not run yet" in text
    items = short.find_all(lambda n: n.tag == "li")
    assert len(items) <= budgets.LIMITS_SHORT_ITEMS
    assert budgets.visible_words(short) <= budgets.LIMITS_SHORT_WORDS
    for summary in ("Intended use", "Out of scope", "All limitations"):
        d = layer.find(lambda n, s=summary: n.tag == "details" and s in n.text())
        assert d is not None and "open" not in d.attrs, summary
    model = context.short_forms(built.reg.model_raw(MODEL))
    assert model["limits_short"] and depth.limits_findings(PAGE, budgets.tree(built.html(PAGE))) == []


def test_limits_come_before_the_quickstart(built):
    html = built.html(PAGE)
    assert 0 < html.find('id="limits"') < html.find('id="quickstart"')


def test_measured_criterion_shows_value_target_and_registers_facts(site_env):
    site_env.edit_yaml(MODEL_YAML, lambda m: m["card"]["unmet_criteria"].insert(0, MEASURED))
    site_env.edit_yaml(MODEL_YAML, lambda m: m["card"]["limits_short"].pop())
    site_env.build()
    short = _limits(site_env).find(lambda n: n.get("data-short") == "limits")
    text = short.text(visible=True)
    assert "Item matching with the reference models: 0.5882 (target ≥ 0.7)" in text
    rows = json.loads((site_env.out / "_build" / "facts.json").read_text())
    keys = {r["key"]: r for r in rows if r["page"] == f"models/{MODEL}/"}
    assert keys["unmet0:target"]["source"] == MODEL_YAML and keys["unmet0:target"]["value"] == "0.7"
    assert "unmet0:quality.agreement_item_matching" in keys
    from mobility_model_zoo.site import check

    assert [f for f in check.check_facts(site_env.reg, site_env.out)] == []


def test_short_form_over_budget_fails(built):
    long = "<li>" + " ".join(["word"] * budgets.LIMITS_SHORT_WORDS) + "</li>"

    def add(h):
        return h.replace('data-short="limits">', 'data-short="limits"><ul>' + long + "</ul>", 1)

    findings = depth.limits_findings(PAGE, budgets.tree(add(built.html(PAGE))))
    assert any(f[0] == "D2" and "words" in f[2] for f in findings)
