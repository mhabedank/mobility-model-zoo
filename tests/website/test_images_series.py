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
    "negative_history": ["old negative"],
    "palette": {
        "anchors": {
            "navy": [12, 12, -32],
            "mint": [94, -14, 2],
            "cream": [93, 1, 11],
            "accent": [72, 22, 68],
        },
        "tolerance_de": 18,
        "other_max": 0.12,
        "accent_min": 0.015,
        "accent_max": 0.30,
        "largest_min": 0.50,
        "top_max": 0.15,
    },
    "duplicate_max_bits": 10,
    "themes": {
        "rail": [
            {
                "id": "tram",
                "aspect": "16:9",
                "prompt": "an orange-yellow tram",
                "scene": "A tram at a stop at sunrise on a boulevard",
                "alt": "An orange-yellow tram glides out of a stop at sunrise",
            }
        ],
        "private-road": [
            {
                "id": "dashboard",
                "prompt": "a dashboard",
                "scene": "A car dashboard at sunrise on an open road",
                "alt": "A car dashboard with orange-yellow needles at sunrise",
            },
            {
                "id": "workshop",
                "prompt": "a workshop bay",
                "scene": "A clean workshop bay in the morning light",
                "alt": "An orange-yellow car in a clean workshop bay in the morning",
            },
        ],
    },
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
    out = findings_for(
        site_env,
        lambda r: (
            r["generation"].update(prompt="a dashboard, style text"),
            r.update(theme="private-road", subject="dashboard"),
        ),
    )
    assert out == []


def test_an_old_negative_prompt_from_the_history_passes(site_env):
    """Feature 019 (research R2): the six 016 records keep their earlier negative text."""
    write_series(site_env.root)
    out = findings_for(site_env, lambda r: r["generation"].update(negative_prompt="old negative"))
    assert out == []


def test_unknown_or_shared_subjects_are_i8(site_env):
    write_series(site_env.root)
    out = findings_for(site_env, lambda r: r.update(theme="water", subject="ferry"), "a")
    assert any("I8 a: theme/subject water/ferry is not in series" in f for f in out)
    out = findings_for(site_env, None, "b")  # b is the only record on rail/tram
    assert not any("I8 b" in f and "not in series" in f for f in out)
    out = findings_for(site_env, None, "c")  # b and c both use rail/tram
    assert any("I8 c: subject rail/tram is also used by b" in f for f in out)


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
