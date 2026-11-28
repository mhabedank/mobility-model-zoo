"""The allow-list guard (feature 017 T031; FR-023, FR-024, contracts/tracking.md)."""

from pathlib import Path

import pytest

from mobility_model_zoo.edge.paths import data_root, repo_root
from mobility_model_zoo.tracking import guard
from mobility_model_zoo.tracking.guard import GuardRefused

ROOT = repo_root()


@pytest.mark.parametrize("key", ["loss", "count.captures", "dist.role.test", "a/b-c_d"])
def test_good_keys(key):
    assert guard.check_key(key) == key


@pytest.mark.parametrize("key", ["Loss", "a b", "", "x" * 121, "ä"])
def test_bad_keys(key):
    with pytest.raises(GuardRefused):
        guard.check_key(key)


def test_params_are_short_single_values():
    assert guard.check_param("lr", 0.001) == "0.001"
    assert guard.check_param("flag", True) == "true"
    assert guard.check_param("model", "xlm-roberta-large") == "xlm-roberta-large"
    for prose in ("Nach 22 Uhr fährt kein Bus mehr, also nehme ich das Auto.", "a\nb", "x" * 121):
        with pytest.raises(GuardRefused):
            guard.check_param("text", prose)


def test_paths_become_repository_relative_or_are_refused():
    assert guard.check_param("config", str(ROOT / "configs" / "x.yaml")) == "configs/x.yaml"
    assert guard.check_param("data", str(data_root() / "road")) == "$MMZ_DATA/road"
    with pytest.raises(GuardRefused):
        guard.check_param("home", "/etc/passwd")


def test_tags_only_from_the_allow_list():
    assert guard.check_tag("mmz.benchmark", "can-ids-v3") == "can-ids-v3"
    with pytest.raises(GuardRefused):
        guard.check_tag("note", "anything")
    with pytest.raises(GuardRefused):
        guard.check_tag("mmz.model", "x\ny")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "1", None, True])
def test_metrics_are_finite_numbers(value):
    with pytest.raises(GuardRefused):
        guard.check_metric("m", value)


def test_artifact_allow_list(tmp_path):
    ok = tmp_path / "summary.json"
    ok.write_text("{}")
    assert guard.check_artifact(ok) == ok
    for name, size in (("model.safetensors", 10), ("rows.jsonl", 10), ("notes.txt", 10)):
        p = tmp_path / name
        p.write_bytes(b"x" * size)
        with pytest.raises(GuardRefused):
            guard.check_artifact(p)
    big = tmp_path / "profile.json"
    big.write_bytes(b"x" * (guard.MAX_ARTIFACT + 1))
    with pytest.raises(GuardRefused):
        guard.check_artifact(big)


def test_config_copies_only_from_configs(tmp_path):
    committed = ROOT / "configs" / "security" / "can-ids" / "picket-forest.yaml"
    assert guard.check_artifact(committed, "config/picket-forest.yaml") == committed
    stray = tmp_path / "picket-forest.yaml"
    stray.write_text("a: 1\n")
    with pytest.raises(GuardRefused):
        guard.check_artifact(stray, "config/picket-forest.yaml")


def test_sanitize_key():
    assert guard.sanitize_key("Fuzzing Attack!") == "fuzzing_attack"
    assert guard.sanitize_key(None) == "none"
    assert Path(guard.sanitize_key("set_01/test_04")).as_posix() == "set_01/test_04"
