"""pace-cnn card: every missed criterion of the verdict is on the card (feature 021, T054; R6)."""

import json

import yaml

from mobility_model_zoo.edge.paths import repo_root

ROOT = repo_root()
VERDICT = ROOT / "topics/condition-monitoring/reports/pace-cnn/0.1.0/verdict.json"
MODEL = ROOT / "zoo/models/pace-cnn/model.yaml"


def _card():
    return yaml.safe_load(MODEL.read_text())["card"]


def test_every_missed_criterion_is_on_the_card():
    verdict = json.loads(VERDICT.read_text())
    unmet = " ".join(
        f"{u['criterion']} {u.get('note', '')}" for u in _card()["unmet_criteria"]
    )
    for c in verdict["criteria"]:
        if not c["met"]:
            assert c["id"] in unmet, f"{c['id']} missing from card.unmet_criteria"
    for k in verdict["kill"]["fired"]:
        assert k in unmet, f"kill criterion {k} missing from card.unmet_criteria"


def test_unmet_and_limits_short_hold_at_most_five_items():
    card = _card()
    assert len(card["unmet_criteria"]) + len(card["limits_short"]) <= 5  # gate rule 18


def test_status_on_record_matches_the_verdict():
    verdict = json.loads(VERDICT.read_text())
    record = yaml.safe_load((ROOT / "zoo/models/pace-cnn/releases/0.1.0.yaml").read_text())
    assert record["status"] == verdict["status"] == "experimental"
