"""scan-publish: non-text datasets need no text snapshot (feature 021, T052; research R13)."""

import pytest

from mobility_model_zoo.compliance import cli as ccli
from mobility_model_zoo.compliance import release_checks as rc

CLASSES = {
    "imu-activity-datasets": {"id": "imu-activity-datasets", "modality": "motion_sensor"},
    "open-papers": {"id": "open-papers"},  # no modality: text
}


def _src(i, cls):
    return {"id": i, "class": cls, "origin_url": f"https://example.org/{i}", "used_by": ["m@0.1.0"]}


def test_non_text_dataset_is_exempt_with_its_reason():
    texts, exempt = rc.split_text_sources(
        CLASSES, [_src("uci-har", "imu-activity-datasets"), _src("paper-1", "open-papers")]
    )
    assert [s["id"] for s in texts] == ["paper-1"]
    assert exempt == [
        {
            "id": "uci-har",
            "class": "imu-activity-datasets",
            "modality": "motion_sensor",
            "reason": rc.NON_TEXT_REASON.format(modality="motion sensor"),
        }
    ]
    assert "personal-data scan" in exempt[0]["reason"]


def test_unknown_class_counts_as_text():
    texts, exempt = rc.split_text_sources(CLASSES, [_src("x", "undeclared-class")])
    assert [s["id"] for s in texts] == ["x"] and exempt == []


def test_a_text_source_without_snapshot_still_fails(tmp_path):
    class Reg:
        root = tmp_path

    (tmp_path / "data" / "snapshots").mkdir(parents=True)
    with pytest.raises(Exception, match="the scan needs the snapshots under data/snapshots"):
        ccli._corpus_texts(Reg(), [_src("paper-1", "open-papers")])


def test_declared_classes_set_their_modality():
    import yaml

    from mobility_model_zoo.edge.paths import repo_root

    def modalities(topic):
        path = repo_root() / "topics" / topic / "compliance" / "source-classes.yaml"
        return {c["id"]: c.get("modality", "text") for c in yaml.safe_load(path.read_text())["classes"]}

    assert modalities("condition-monitoring") == {
        "machine-sound-datasets": "audio",
        "imu-activity-datasets": "motion_sensor",
    }
    assert modalities("security") == {"can-bus-datasets": "can_frames"}
    assert set(modalities("productdev").values()) == {"text"}
