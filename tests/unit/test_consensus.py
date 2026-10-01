import json

from helpers import copy_fixture, reference_chain

from mobility_model_zoo.productdev.jtbd.config import load_settings
from mobility_model_zoo.productdev.jtbd.consensus import load_consensus

EXPECTED = json.loads((__import__("helpers").FIXTURE / "expected.json").read_text())["reference"]


def test_consensus_and_contested(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    consensus, contested, meta = load_consensus(load_settings(config))
    items = [c for c in consensus if c["level"] == "item"]
    assert len(items) == EXPECTED["consensus_items"]
    assert sum(c["level"] == "relevance" for c in consensus) == EXPECTED["consensus_relevance"]
    got = sorted((c["chunk_id"], c["dimensions"]) for c in contested)
    assert got == sorted((c["chunk_id"], c["dimensions"]) for c in EXPECTED["contested"])
    kind_item = next(c for c in contested if c["dimensions"] == ["kind"])
    partial = next(c for c in items if c["item_key"] == kind_item["item_key"])
    assert "kind" not in partial["values"] and partial["values"]["evidence_type"] == "routine"
    assert meta["invalid_quotes"] == {meta["reference_runs"][0]: 0, meta["reference_runs"][1]: 1}
