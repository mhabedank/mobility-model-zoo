"""The packaged schemas equal the contracts and enforce the data-model rules (T015)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from mobility_model_zoo.release.registry import SCHEMAS, schema_errors

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "specs/005-topic-layout-security-merge/contracts"  # latest owner of the format
PACKAGED = ROOT / "src/mobility_model_zoo/release/schemas"


@pytest.mark.parametrize("name", SCHEMAS)
def test_packaged_schema_equals_contract(name):
    assert (PACKAGED / f"{name}.schema.json").read_bytes() == (
        CONTRACTS / f"{name}.schema.json"
    ).read_bytes()


def test_valid_fixture_files_validate(zoo_env):
    reg = zoo_env.reg
    assert schema_errors("topics", reg.topics_raw()) == []
    assert schema_errors("model", reg.model_raw(zoo_env.model)) == []
    assert schema_errors("release-record", zoo_env.record()) == []
    for kind in ("quality", "performance"):
        assert schema_errors("results", reg.results(zoo_env.model, zoo_env.version, kind)) == []


def _invalid(name, data, mutate):
    data = copy.deepcopy(data)
    mutate(data)
    return schema_errors(name, data)


def test_patterns_from_the_data_model(zoo_env):
    reg = zoo_env.reg
    topics, model, record = reg.topics_raw(), reg.model_raw(zoo_env.model), zoo_env.record()
    quality = reg.results(zoo_env.model, zoo_env.version, "quality")

    assert _invalid("topics", topics, lambda d: d["topics"][0].update(id="Product-Dev"))
    assert _invalid("model", model, lambda d: d.update(name="productdev"))
    assert _invalid("model", model, lambda d: d.update(name="productdev_jtbd_span"))
    assert _invalid("release-record", record, lambda d: d.update(version="1.0"))
    assert _invalid("release-record", record, lambda d: d.update(status="beta"))
    assert _invalid("release-record", record, lambda d: d["files"][0].update(sha256="abc"))
    assert _invalid("release-record", record, lambda d: d["staging"].update(revision="abc"))
    assert _invalid("release-record", record, lambda d: d["performance"]["budget"].update(gpu=True))
    assert _invalid("model", model, lambda d: d.update(license="MIT", license_exception=None))
    assert not _invalid(
        "model", model, lambda d: d.update(license="MIT", license_exception="base model is MIT")
    )
    # the "accuracy" ban moved to gate rule 10 (model_consensus only), feature 005
    assert not _invalid("results", quality, lambda d: d["metrics"][0].update(name="span_accuracy"))
    assert _invalid("model", model, lambda d: d["card"].update(how_to_run="print('no placeholders')"))
