"""`zoo build` is deterministic and refuses staged files that do not match (T025)."""

from __future__ import annotations

import pytest
from conftest import FakeRunner

from mobility_model_zoo.release import publish as ops
from mobility_model_zoo.release.errors import GateFailed


def quiet(line: str) -> None:
    pass


def test_build_twice_is_byte_identical(zoo_env, tmp_path):
    a = ops.build(
        zoo_env.reg, zoo_env.model, zoo_env.version, tmp_path / "a", zoo_env.hub, FakeRunner(), quiet
    )
    b = ops.build(
        zoo_env.reg, zoo_env.model, zoo_env.version, tmp_path / "b", zoo_env.hub, FakeRunner(), quiet
    )
    assert a == b
    for name in ("README.md", "build.json", "config.json", "model.safetensors"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    readme = (tmp_path / "a" / "README.md").read_text()
    assert "(produced by the release gate" not in readme  # example outputs are filled in
    assert "sandbox-pipeline-tiny/v0.1.0" in readme


def test_build_refuses_mismatching_staged_files(zoo_env, tmp_path):
    record = zoo_env.record()
    record["files"][0]["sha256"] = "f" * 64
    zoo_env.set_record(record)
    with pytest.raises(GateFailed) as exc:
        ops.build(
            zoo_env.reg,
            zoo_env.model,
            zoo_env.version,
            tmp_path / "out",
            zoo_env.hub,
            FakeRunner(),
            quiet,
        )
    assert any(f.startswith("rule 5:") for f in exc.value.failures)
    assert not (tmp_path / "out").exists()
