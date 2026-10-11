"""Dataset declaration rules (feature 005 T047, data-model.md "Dataset declaration")."""

import copy
from pathlib import Path

import pytest
import yaml

from mobility_model_zoo.datasets.registry import declarations, load, validate

ROOT = Path(__file__).resolve().parents[2]


def _real(ds_id: str) -> dict:
    return copy.deepcopy(next(r for _, r in declarations(ROOT) if r["id"] == ds_id))


def _tree(tmp_path, topics: dict[str, list[dict]]) -> Path:
    for topic, recs in topics.items():
        d = tmp_path / "topics" / topic / "compliance"
        d.mkdir(parents=True)
        (d / "datasets.yaml").write_text(yaml.safe_dump({"datasets": recs}))
    return tmp_path


def test_real_topic_files_validate():
    assert validate(ROOT) == []
    topics = {s.topic for s in load(ROOT).values()}
    assert {"security", "condition-monitoring"} <= topics
    assert all(s.redistribution != "allowed" for s in load(ROOT).values())  # FR-011


def _bad(**changes):
    rec = _real("road")
    for k, v in changes.items():
        if v is None:
            rec.pop(k, None)
        else:
            rec[k] = v
    return rec


@pytest.mark.parametrize(
    "rec",
    [
        _bad(id="Road_1"),
        _bad(licence="CC-BY-NC-4.0"),
        _bad(licence="CC-BY-ND-4.0"),
        _bad(status="rejected", reason=None),
        _bad(status="broken_at_source", reason=""),
        _bad(license_check="manual", license_checked=None),
        _bad(redistribution=None),
        _bad(redistribution="maybe"),
        _bad(redistribution="allowed", redistribution_basis=""),
    ],
    ids=[
        "bad-id",
        "training-nc-marked-commercial",
        "training-nd",
        "rejected-without-reason",
        "broken-empty-reason",
        "manual-without-date",
        "redistribution-missing",
        "redistribution-unknown-value",
        "allowed-without-basis",
    ],
)
def test_rule_violations_are_rejected(tmp_path, rec):
    assert validate(_tree(tmp_path, {"security": [rec]}))


def test_duplicate_id_across_topics(tmp_path):
    root = _tree(tmp_path, {"security": [_real("road")], "other": [_real("road")]})
    assert any("declared in topics" in p for p in validate(root))


def test_nc_dataset_may_train_non_commercial_models(tmp_path):
    # constitution 2.1.0: NC data is training_allowed with commercial_use false
    rec = _bad(licence="CC-BY-NC-4.0", commercial_use=False)
    assert validate(_tree(tmp_path, {"security": [rec]})) == []


def _producer(root, name="teach-small-nc"):
    d = root / "zoo" / "models" / name
    d.mkdir(parents=True)
    (d / "model.yaml").write_text("usage_class: non-commercial\n")


def test_data_of_a_non_commercial_producer_is_non_commercial(tmp_path):
    _producer(tmp_path / "a")
    problems = validate(_tree(tmp_path / "a", {"security": [_bad(produced_by="teach-small-nc")]}))
    assert any("commercial_use must be false" in p for p in problems)
    _producer(tmp_path / "b")
    rec = _bad(produced_by="teach-small-nc", commercial_use=False)
    assert validate(_tree(tmp_path / "b", {"security": [rec]})) == []


def test_valid_copy_passes(tmp_path):
    assert validate(_tree(tmp_path, {"security": [_real("road")]})) == []
