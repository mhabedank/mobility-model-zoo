"""zoo/MODELS.md and topic collections (T048)."""

from __future__ import annotations

import shutil

from conftest import FakeRunner

from mobility_model_zoo.release import index
from mobility_model_zoo.release import publish as ops
from mobility_model_zoo.release.gate import Gate
from mobility_model_zoo.release.registry import dump_yaml


def quiet(line: str) -> None:
    pass


def add_topic_and_model(env, topic: str, name: str) -> None:
    """A new topic and a copy of the sandbox model in it, without any code change."""
    topics = env.reg.topics()
    topics.append(
        {"id": topic, "title": topic.upper(), "description": "Test topic.", "hf_collection": None}
    )
    env.reg.write_topics(topics)
    src, dst = env.reg.model_dir(env.model), env.reg.model_dir(name)
    shutil.copytree(src, dst)
    model = env.reg.model_raw(name)
    parts = name.split("-")
    model.update(
        name=name,
        topic=topic,
        task=parts[1],
        variant="-".join(parts[2:]),
        base_model="FacebookAI/xlm-roberta-base",
        base_model_license="MIT",
        repos={"public": f"mobility-model-zoo/{name}", "staging": f"mobility-model-zoo/{name}-staging"},
    )
    (dst / "model.yaml").write_text(dump_yaml(model), encoding="utf-8")
    # A public model needs its website text before it can be published (gate rule 17, feature 008).
    site = {
        "tagline": "Finds anomalies in test data.",
        "audience": "For the release tests.",
        "differentiators": [{"title": t, "text": f"{t} test text."} for t in ("One", "Two", "Three")],
        "quickstart_example": "01-bus.txt",
    }
    (dst / "site.yaml").write_text(dump_yaml(site), encoding="utf-8")
    record = env.reg.record_raw(name, env.version)
    record.update(model=name, sandbox=False)
    record["staging"]["repo"] = model["repos"]["staging"]
    env.reg.write_record(name, env.version, record)
    for kind in ("quality", "performance"):
        path = env.reg.results_path(name, env.version, kind)
        path.write_text(
            path.read_text()
            .replace('"synthetic": true', '"synthetic": false')
            .replace('"model": "sandbox-pipeline-tiny"', f'"model": "{name}"')
        )
    staged = env.hub.files_at(env.record()["staging"]["repo"], "main")
    revision = env.hub.seed(model["repos"]["staging"], staged, private=True)
    record["staging"]["revision"] = revision
    env.reg.write_record(name, env.version, record)


def test_models_md_lists_topics_and_hides_the_sandbox(zoo_env):
    text = index.render(zoo_env.reg)
    assert "## Product development (`productdev`)" in text
    assert "Pipeline tests" not in text and "sandbox-pipeline-tiny" not in text


def test_new_topic_needs_no_code_change(zoo_env):
    add_topic_and_model(zoo_env, "iot", "iot-anomaly-test")
    Gate(zoo_env.reg, "iot-anomaly-test", zoo_env.version, only={1, 2, 3, 6, 7, 8, 11, 14}).run(quiet)
    text = index.render(zoo_env.reg)
    assert "## IOT (`iot`)" in text
    assert "| `iot-anomaly-test` | anomaly | – | not published |" in text


def test_publish_creates_the_topic_collection_once(zoo_env, tmp_path):
    add_topic_and_model(zoo_env, "iot", "iot-anomaly-test")
    name = "iot-anomaly-test"
    out = tmp_path / "build"
    ops.build(zoo_env.reg, name, zoo_env.version, out, zoo_env.hub, FakeRunner(), quiet)
    ops.preview(zoo_env.reg, name, zoo_env.version, out, zoo_env.hub, quiet)
    ops.publish(zoo_env.reg, name, zoo_env.version, f"{name}/v0.1.0", zoo_env.hub, quiet)

    slug = zoo_env.reg.topic("iot")["hf_collection"]
    assert slug and zoo_env.hub.collections[slug]["items"][0][0] == f"mobility-model-zoo/{name}"
    assert zoo_env.hub.repos[f"mobility-model-zoo/{name}"].private is False
    models_md = (zoo_env.root / "zoo/MODELS.md").read_text()
    assert f"| `{name}` | anomaly | 0.1.0 | experimental |" in models_md

    ops.add_to_collection(zoo_env.reg, zoo_env.reg.model(name), zoo_env.hub, quiet)
    assert len(zoo_env.hub.collections) == 1
