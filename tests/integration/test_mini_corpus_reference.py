import json

import pytest
from helpers import FIXTURE, copy_fixture, pilot, reference_chain

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.freeze import load_manifest

EXPECTED = json.loads((FIXTURE / "expected.json").read_text())["reference"]


def test_reference_chain_reproduces_expected(tmp_path):
    config = copy_fixture(tmp_path)
    ids = reference_chain(config)
    manifest = load_manifest(load_settings(config))
    assert manifest["state"] == "frozen" and manifest["test_only"] is True
    checks = pilot(config, "check", "--run", ids["mock-b"])["pass_rates"]
    assert checks["quote_verbatim"]["n"] == 7 and checks["quote_verbatim"]["passed"] == 6
    agreement = pilot(config, "agreement")
    assert agreement["dimensions"]["kind"]["score"] == pytest.approx(EXPECTED["kind_kappa"])
    assert agreement["wording"].startswith("agreement between frontier reference models")


def test_agreement_requires_frozen_benchmark(tmp_path):
    config = copy_fixture(tmp_path)
    pilot(config, "freeze")
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-a")
    pilot(config, "label", "--role", "reference", "--backend", "mock", "--model", "mock-b")
    settings = load_settings(config)
    runs = sorted(p.name for p in settings.runs_dir.glob("run-*"))
    pilot(config, "consensus", "--reference", *runs)
    pilot(config, "agreement", expect=1)
