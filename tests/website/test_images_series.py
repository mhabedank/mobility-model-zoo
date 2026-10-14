"""The series file is the art direction every record must come from (feature 016, FR-003,
FR-010, FR-011; check I2)."""

from __future__ import annotations

from test_images_record import make_record

from mobility_model_zoo.release.registry import dump_yaml, load_yaml
from mobility_model_zoo.site import images

SERIES = {
    "name": "siebdruck",
    "style": "style text",
    "negative": "text",
    "models": {
        "draft": {
            "id": "black-forest-labs/FLUX.2-klein-4B",
            "pipeline": "Flux2KleinPipeline",
            "licence": "Apache-2.0",
            "card": "https://huggingface.co/x",
            "steps": 4,
            "guidance": 1.0,
        },
        "final": {
            "id": "Qwen/Qwen-Image-2512",
            "pipeline": "QwenImagePipeline",
            "licence": "Apache-2.0",
            "card": "https://huggingface.co/y",
            "steps": 50,
            "true_cfg_scale": 4.0,
        },
    },
    "subjects": {"start-hero": ["an orange-yellow tram"], "topic:security": ["a dashboard"]},
}


def write_series(root, series=SERIES):
    d = root / images.SERIES_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / "siebdruck.yaml").write_text(dump_yaml(series), encoding="utf-8")


def findings_for(site_env, edit=None, rid="hero-test"):
    d = make_record(site_env.root, rid)
    if edit:
        rec = load_yaml(d / "image.yaml")
        edit(rec)
        (d / "image.yaml").write_text(dump_yaml(rec), encoding="utf-8")
    records, _ = images.load_records(site_env.reg)
    return images.series_findings(site_env.reg, records)


def test_record_from_the_series_passes(site_env):
    write_series(site_env.root)
    assert findings_for(site_env) == []


def test_missing_series_file_is_i2(site_env):
    assert any("has no file" in f for f in findings_for(site_env))


def test_prompt_outside_the_series_is_i2(site_env):
    write_series(site_env.root)
    out = findings_for(
        site_env, lambda r: r["generation"].update(prompt="a real Berlin tram, style text")
    )
    assert any("prompt is not a subject" in f for f in out)


def test_a_subject_may_serve_another_placement(site_env):
    """The owner chose a security subject for product development (data-model.md, Series)."""
    write_series(site_env.root)
    out = findings_for(site_env, lambda r: r["generation"].update(prompt="a dashboard, style text"))
    assert out == []


def test_negative_model_and_licence_are_i2(site_env):
    write_series(site_env.root)
    out = findings_for(site_env, lambda r: r["generation"].update(negative_prompt=""), "a")
    assert any("negative prompt" in f for f in out)
    out = findings_for(site_env, lambda r: r["generation"].update(model="x/y"), "b")
    assert any("is not in series" in f for f in out)
    series = {**SERIES, "models": {"final": {**SERIES["models"]["final"], "licence": "other"}}}
    write_series(site_env.root, series)
    out = findings_for(site_env, lambda r: r["generation"].update(model_licence="other"), "c")
    assert any("licence other is not accepted" in f for f in out)
