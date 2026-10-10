"""Models, status and releases as the website sees them (data-model.md; checks B1, B2)."""

from __future__ import annotations

import pytest
from site_fixture import MODEL, VERSION

from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.site import context, facts


def test_status_published_in_progress_and_sandbox_excluded(site_env):
    models = {m["name"]: m for m in context.site_models(site_env.reg)}
    assert models[MODEL]["status"] == "published" and models[MODEL]["latest"] == VERSION
    assert models["picket-forest"]["status"] == "in_progress"
    assert models["picket-forest"]["latest"] is None
    assert "sandbox-pipeline-tiny" not in models


def test_deprecated_latest(site_env):
    rel = f"zoo/models/{MODEL}/releases/{VERSION}.yaml"
    site_env.edit_yaml(rel, lambda r: r.update(deprecated={"reason": "broken", "successor": "0.2.0"}))
    state, latest = context.status(site_env.reg, MODEL)
    assert (state, latest) == ("deprecated", VERSION)


def test_release_links_only_for_existing_files(site_env):
    release = context.site_release(site_env.reg, MODEL, VERSION)
    assert set(release["links"]) == {"training_data_summary", "ai_act", "hf_tree"}
    assert release["links"]["ai_act"].endswith(
        f"/blob/{MODEL}/v{VERSION}/zoo/models/{MODEL}/releases/{VERSION}.ai-act.md"
    )
    assert release["links"]["hf_tree"].endswith(release["published"]["repo_commit"])


def test_missing_site_yaml_is_b1(site_env):
    (site_env.root / f"zoo/models/{MODEL}/site.yaml").unlink()
    with pytest.raises(GateFailed, match="B1"):
        context.site_models(site_env.reg)


def test_invalid_site_yaml_is_b1(site_env):
    site_env.edit_yaml(f"zoo/models/{MODEL}/site.yaml", lambda p: p.pop("tagline"))
    with pytest.raises(GateFailed, match="B1.*tagline"):
        context.load_pitch(site_env.reg, MODEL)


def test_pitch_errors_name_unknown_metrics_and_examples(site_env):
    def broken(p):
        p["differentiators"][0]["text"] = "Takes {metric:performance.no_such_metric}."
        p["quickstart_example"] = "99-missing.txt"

    site_env.edit_yaml(f"zoo/models/{MODEL}/site.yaml", broken)
    errors = context.pitch_errors(site_env.reg, MODEL, VERSION)
    assert any("B2" in e and "no_such_metric" in e for e in errors)
    assert any("99-missing.txt" in e for e in errors)


def test_metric_formats_like_the_card_and_names_its_reference(site_env):
    m = facts.metric(site_env.reg, MODEL, VERSION, "quality", "comparison_composite")
    assert m["value"] == "0.7234"
    assert "frontier reference models" in m["against"] and "pilot-v2" in m["against"]
    p = facts.metric(site_env.reg, MODEL, VERSION, "performance", "chunks_per_min_dgx_spark_gpu")
    assert p["unit"] == "texts/min" and "DGX Spark" in p["against"]


def test_metric_without_reference_is_b2(site_env):
    import json

    path = site_env.root / f"zoo/models/{MODEL}/results/{VERSION}/quality.json"
    data = json.loads(path.read_text())
    del data["metrics"][0]["reference"]
    path.write_text(json.dumps(data))
    with pytest.raises(GateFailed, match="B2.*no reference"):
        facts.metric(site_env.reg, MODEL, VERSION, "quality", data["metrics"][0]["name"])


def test_placeholders_resolve_with_notes_and_facts(site_env):
    f, notes = facts.Facts(), facts.Notes()
    html = facts.resolve(
        "A {metric:quality.comparison_composite} <b>", site_env.reg, MODEL, VERSION, f, notes, "p/", "k"
    )
    assert "0.7234" in html and "&lt;b&gt;" in html and 'href="#fn-1"' in html
    assert (
        f.rows[0]["metric"] == "comparison_composite"
        and notes.items[0]["metric"] == "quality.comparison_composite"
    )
