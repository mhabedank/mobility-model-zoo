import csv

from helpers import copy_fixture, pilot, reference_chain

from mobility_model_zoo.productdev.jtbd.config import load_settings


def _fill(path, mapping):
    rows = list(csv.DictReader(path.open()))
    for row in rows:
        row["category"] = mapping.get(row["id"], "")
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_categorize_workflow(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    exported = pilot(config, "categorize", "--export")
    assert exported["exported"] == 3
    pilot(config, "categorize", "--check", expect=1)
    review = load_settings(config).analysis_dir / "contested-review.csv"
    ids = [r["id"] for r in csv.DictReader(review.open())]
    _fill(review, {ids[0]: "not_a_category"})
    pilot(config, "categorize", "--import", str(review), expect=1)
    _fill(review, {ids[0]: "pain_vs_negated_gain",
                   ids[1]: "evidence_boundary_observation_measurement",
                   ids[2]: "item_split_merge"})
    pilot(config, "categorize", "--import", str(review))
    result = pilot(config, "categorize", "--check")
    assert result["uncategorized"] == []
    assert sum(result["counts"].values()) == 3
    assert all(len(v) == 1 for v in result["examples"].values())


def test_freetext_sample(tmp_path):
    config = copy_fixture(tmp_path)
    reference_chain(config)
    result = pilot(config, "categorize", "--freetext")
    assert result["sampled"] == 6
