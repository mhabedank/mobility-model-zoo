"""Layer 1 of the model page: what it is, may I use it (feature 013, US1, checks D2-D4)."""

from __future__ import annotations

from site_fixture import MODEL, VERSION

from mobility_model_zoo.site import budgets, context, depth

PAGE = f"models/{MODEL}/index.html"
RECORD = f"zoo/models/{MODEL}/releases/{VERSION}.yaml"
MODEL_YAML = f"zoo/models/{MODEL}/model.yaml"
SITE_YAML = f"zoo/models/{MODEL}/site.yaml"
SENTENCE = "Experimental: not ready for production use."
LEAD = '<p class="lead">'


NC_USAGE = {
    "class": "non-commercial",
    "licence": "CC-BY-NC-4.0",
    "restricting_inputs": [
        {
            "kind": "dataset",
            "id": "nc-corpus",
            "licence": "CC-BY-NC-4.0",
            "restriction": "non-commercial",
        }
    ],
}


def _findings(env, mutate_html=None):
    sm = next(s for s in context.site_models(env.reg) if s["name"] == MODEL)
    html = env.html(f"models/{MODEL}/index.html")
    if mutate_html:
        html = mutate_html(html)
    return depth.overview_findings(f"models/{MODEL}/index.html", budgets.tree(html), sm)


def _overview(env) -> budgets.Node:
    root = budgets.tree(env.html(f"models/{MODEL}/index.html"))
    return root.find(lambda n: n.get("data-layer") == "overview")


def test_fixture_overview_passes(built):
    assert _findings(built) == []
    assert list(depth.check_overview(built.reg, built.out)) == []


def test_status_comes_from_the_record_with_its_sentence(built):
    layer = _overview(built)
    chip = layer.find(lambda n: n.get("data-status") is not None)
    assert chip.get("data-status") == "experimental"
    line = layer.find(lambda n: "status-line" in n.classes)
    assert "Experimental: not ready for production use." in line.text()
    assert line.find(lambda n: n.tag == "a" and n.get("href") == "#limits")


def test_lifecycle_chip_only_and_missing_sentence_fail(built):
    findings = _findings(
        built, lambda h: h.replace('data-status="experimental"', 'data-status="published"')
    )
    assert any(f[0] == "D4" and "status chip" in f[2] for f in findings)
    findings = _findings(built, lambda h: h.replace(SENTENCE, "Hello."))
    assert any(f[0] == "D4" and "status sentence" in f[2] for f in findings)


def test_released_record_has_no_experimental_sentence(site_env):
    site_env.edit_yaml(RECORD, lambda r: r.update(status="released"))
    site_env.edit_yaml(f"zoo/models/{MODEL}/model.yaml", lambda m: m["card"].pop("unmet_criteria"))
    site_env.build()
    layer = _overview(site_env)
    assert layer.find(lambda n: n.get("data-status") == "released")
    assert "Experimental" not in layer.text()
    assert _findings(site_env) == []


def test_non_commercial_is_in_the_overview(site_env):
    site_env.edit_yaml(
        MODEL_YAML, lambda m: m.update(usage_class="non-commercial", license="CC-BY-NC-4.0")
    )
    site_env.edit_yaml(f"zoo/models/{MODEL}/releases/{VERSION}.yaml", lambda r: r.update(usage=NC_USAGE))
    site_env.build()
    assert "Non-commercial" in _overview(site_env).text()
    assert _findings(site_env) == []
    findings = _findings(site_env, lambda h: h.replace(">Non-commercial<", "><"))
    assert any(f[0] == "D4" and "Non-commercial" in f[2] for f in findings)


def test_status_words_in_site_text_fail(site_env):
    site_env.edit_yaml(SITE_YAML, lambda s: s.update(tagline="An experimental extractor of needs."))
    site_env.build()
    assert any(f[0] == "D4" and "tagline" in f[2] for f in _findings(site_env))


def test_overview_budgets(site_env):
    long = " ".join(["word"] * (budgets.DIFFERENTIATOR_TEXT_WORDS + 1))
    site_env.edit_yaml(SITE_YAML, lambda s: s["differentiators"][0].update(text=long))
    site_env.build()
    assert any(f[0] == "D2" and "reason 1" in f[2] for f in _findings(site_env))


def test_overview_word_and_not_for_limits(built):
    filler = "<p>" + " ".join(["more"] * (budgets.OVERVIEW_WORDS + 1)) + "</p>"
    findings = _findings(built, lambda h: h.replace('<p class="lead">', filler + '<p class="lead">', 1))
    assert any(f[0] == "D2" and "running text" in f[2] for f in findings)
    findings = _findings(built, lambda h: h.replace('data-short="not-for"', 'data-x="y"'))
    assert any(f[0] == "D2" and "'Not for'" in f[2] for f in findings)


def test_no_code_tables_or_figures_in_the_overview(built):
    extras = (
        "<pre>pip install</pre>",
        "<table><tr><td>x</td></tr></table>",
        '<div class="metric">x</div>',
    )
    for extra in extras:
        findings = _findings(built, lambda h, e=extra: h.replace(LEAD, e + LEAD, 1))
        assert any(f[0] == "D3" for f in findings), extra
