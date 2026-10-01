"""SC-005: removing any required field blocks the release, names the field, and uploads nothing."""

from __future__ import annotations

import pytest
from conftest import FakeRunner, make_env
from typer.testing import CliRunner

from mobility_model_zoo.release import publish as ops
from mobility_model_zoo.release.cli import app
from mobility_model_zoo.release.errors import GateFailed
from mobility_model_zoo.release.registry import dump_yaml, schema


def required_paths(node: dict, prefix: tuple = ()) -> list[tuple]:
    paths = []
    props = node.get("properties", {})
    for name in node.get("required", []):
        paths.append((*prefix, name))
        child = props.get(name, {})
        types = child.get("type")
        if child.get("required") and (
            types == "object" or (isinstance(types, list) and "object" in types)
        ):
            paths += required_paths(child, (*prefix, name))
    return paths


MODEL_FIELDS = required_paths(schema("model"))
RECORD_FIELDS = [
    p for p in required_paths(schema("release-record")) if p[0] not in ("published", "deprecated")
]


def _delete(data: dict, path: tuple) -> None:
    for key in path[:-1]:
        data = data[key]
    del data[path[-1]]


@pytest.mark.parametrize("path", MODEL_FIELDS + [("record",) + p for p in RECORD_FIELDS], ids=".".join)
def test_missing_required_field_blocks_and_uploads_nothing(tmp_path, monkeypatch, path):
    env = make_env(tmp_path)
    if path[0] == "record":
        record = env.record()
        _delete(record, path[1:])
        env.set_record(record)
    else:
        model = env.reg.model_raw(env.model)
        _delete(model, path)
        (env.reg.model_dir(env.model) / "model.yaml").write_text(dump_yaml(model), encoding="utf-8")

    with pytest.raises(GateFailed) as exc:
        ops.check(env.reg, env.model, env.version, env.hub, FakeRunner(), lambda line: None)
    assert any(path[-1] in failure for failure in exc.value.failures), exc.value.failures
    assert env.hub.writes == []

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["check", env.model, env.version, "--offline"])
    assert result.exit_code == 1
    assert path[-1] in result.output


def test_every_required_field_is_covered():
    assert len(MODEL_FIELDS) >= 20 and len(RECORD_FIELDS) >= 25
