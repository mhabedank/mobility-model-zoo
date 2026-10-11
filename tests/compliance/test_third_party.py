"""Register of third-party models: checks C-X1 and C-X2, derived restriction, stage metadata
(feature 011, T031). No network."""

from pathlib import Path

import pytest
import yaml
from compliance_helpers import load, write

from mobility_model_zoo.compliance.usage import (
    LicenceList,
    third_party_class,
    third_party_findings,
    third_party_metadata,
)

ROOT = Path(__file__).resolve().parents[2]
REV = "a" * 40
USING = {"encoder": {"model_id": "org/encoder", "revision": REV}}


def record(**changes):
    rec = {
        "id": "org/encoder", "revision": REV, "remote_code": None, "weights_licence": "MIT",
        "training_data_named": True,
        "training_data": [{"name": "corpus", "url": "https://example.org/c", "licence": "CC-BY-4.0"}],
        "used_by": [], "owner": "o", "last_reviewed": "2026-10-10", "next_review": "2027-04-10",
    }
    rec.update(changes)
    return rec


def register(root, *records):
    write(root, "compliance/third-party-models.yaml", {"models": list(records)})


def checks(root):
    return [(f.check_id, f.reason) for f in third_party_findings(root, load(root))]


def stage(root, rel, data):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_training_data_governs_the_weights_licence():
    rec = record(training_data=[{"name": "XNLI", "url": "u", "licence": "CC-BY-NC-4.0"}])
    cls, reasons, findings = third_party_class(rec, LicenceList.load(ROOT))
    assert str(cls) == "non-commercial" and reasons == ["training data XNLI (CC-BY-NC-4.0)"]
    assert findings == []


def test_share_alike_training_data_does_not_bind_our_model():
    rec = record(training_data=[{"name": "Wikipedia", "url": "u", "licence": "CC-BY-SA-3.0"}])
    cls, _, _ = third_party_class(rec, LicenceList.load(ROOT))
    assert str(cls) == "commercial"


def test_clean_register_passes(register_tree):
    register(register_tree, record())
    assert checks(register_tree) == []


def test_unregistered_pinned_model_in_settings_is_c_x1(register_tree):
    register(register_tree, record())
    stage(register_tree, "configs/x/stage.yaml", {"encoder": {"model_id": "org/other", "revision": REV}})
    assert [c for c, _ in checks(register_tree)] == ["C-X1"]


def test_differing_revision_is_c_x1(register_tree):
    register(register_tree, record())
    stage(register_tree, "configs/x/stage.yaml",
          {"encoder": {"model_id": "org/encoder", "revision": "b" * 40}})
    assert any(c == "C-X1" and "pinned to" in r for c, r in checks(register_tree))


def test_remote_code_must_be_pinned_in_settings(register_tree):
    register(register_tree, record(remote_code={"repo": "org/impl", "revision": "c" * 40}))
    stage(register_tree, "configs/x/stage.yaml",
          {"encoder": {"model_id": "org/encoder", "revision": REV, "code_revision": None}})
    assert any(c == "C-X1" and "code_revision" in r for c, r in checks(register_tree))


def test_unregistered_base_model_is_c_x1(register_tree):
    register(register_tree, record())
    stage(register_tree, "zoo/models/m-x/model.yaml", {"base_model": "org/base"})
    assert any(c == "C-X1" and "org/base" in r for c, r in checks(register_tree))


def test_used_by_must_resolve(register_tree):
    register(register_tree, record(used_by=[{"kind": "stage", "ref": "configs/x/stage.yaml#encoder"}]))
    assert any(c == "C-X1" and "does not name" in r for c, r in checks(register_tree))
    stage(register_tree, "configs/x/stage.yaml", USING)
    assert checks(register_tree) == []


def test_unknown_training_data_licence_blocks_only_a_used_model(register_tree):
    unknown = [{"name": "Reddit", "url": "u", "licence": "unknown"}]
    register(register_tree, record(training_data=unknown))
    assert checks(register_tree) == []  # registered for information, not used yet
    use = [{"kind": "stage", "ref": "configs/x/stage.yaml#encoder"}]
    register(register_tree, record(training_data=unknown, used_by=use))
    stage(register_tree, "configs/x/stage.yaml", USING)
    assert [c for c, _ in checks(register_tree)] == ["C-X2"]
    # an owner decision that names the record accepts it
    decisions = yaml.safe_load((register_tree / "compliance/decisions.yaml").read_text())
    decisions["decisions"][0]["scope"].append("compliance/third-party-models.yaml#org/encoder")
    write(register_tree, "compliance/decisions.yaml", decisions)
    assert checks(register_tree) == []


def test_unlisted_licence_is_c_u1(register_tree):
    register(register_tree, record(weights_licence="LicenseRef-something"))
    assert [c for c, _ in checks(register_tree)] == ["C-K1"]


def test_stage_metadata(register_tree):
    register(register_tree, record(training_data=[{"name": "MS MARCO", "url": "u",
                                                   "licence": "LicenseRef-MSMARCO-terms"}]))
    meta = third_party_metadata(register_tree, ["org/encoder"])
    assert meta == [{"id": "org/encoder", "revision": REV, "usage_class": "non-commercial",
                     "reason": "training data MS MARCO (LicenseRef-MSMARCO-terms)"}]
    with pytest.raises(KeyError):
        third_party_metadata(register_tree, ["org/missing"])


def test_real_register_derives_the_009_candidates():
    from mobility_model_zoo.compliance.usage import third_party_records

    licences = LicenceList.load(ROOT)
    classes = {k: str(third_party_class(r, licences)[0]) for k, r in third_party_records(ROOT).items()}
    assert classes["FacebookAI/xlm-roberta-large"] == "commercial"
    assert classes["intfloat/multilingual-e5-base"] == "non-commercial"
    assert classes["Alibaba-NLP/gte-multilingual-base"] == "commercial"
    assert classes["MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"] == "non-commercial"


def test_real_register_passes_the_meta_checks():
    from mobility_model_zoo.compliance.register import Register

    assert third_party_findings(ROOT, Register.load(ROOT)) == []
