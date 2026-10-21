"""Card section "Training data and attribution" for datasets (feature 021, T053; research R13)."""

from mobility_model_zoo.release import card as cards

ATTRIBUTION = "Human Activity Recognition Using Smartphones by J. Reyes-Ortiz et al. (CC BY 4.0)"
NOTE = "Trained on motion signals of 30 volunteers; no data or subject number is in the release."


def _context(*_args):
    return {
        "rc": {"version": "0.1.0", "card_privacy_note": NOTE},
        "sources": [
            {
                "id": "uci-har",
                "is_dataset": True,
                "class": "imu-activity-datasets",
                "title": "Human Activity Recognition Using Smartphones",
                "creators": ["J. Reyes-Ortiz", "D. Anguita"],
                "origin_url": "https://archive.ics.uci.edu/dataset/240",
                "doi": "10.24432/C54S4K",
                "licence": "CC-BY-4.0",
                "licence_url": "https://creativecommons.org/licenses/by/4.0/",
                "attribution_text": ATTRIBUTION,
                "modifications": "Converted to int8 windows for training; not redistributed.",
            }
        ],
        "routes": [],
        "base_notice": None,
        "mit_text": "",
        "security": False,
        "decisions": [],
        "controller": {"privacy_contact": "privacy@example.org"},
    }


def _section(card, heading):
    return card.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_dataset_attribution_and_privacy_note(mcu_env, monkeypatch):
    monkeypatch.setattr(cards, "compliance_context", _context)
    card = cards.render(cards.CardInput(mcu_env.reg, mcu_env.model, mcu_env.version))
    data = _section(card, "Training data and attribution")
    assert "1 published dataset, credited below as its licence requires" in data
    assert ATTRIBUTION in data
    assert "[10.24432/C54S4K](https://doi.org/10.24432/C54S4K)" in data
    assert "Converted to int8 windows" in data
    assert "published documents" not in data and "training texts" not in data
    teachers = _section(card, "Teacher and labeling models")
    assert "None. The model learned only from the labels of its training dataset" in teachers
    privacy = _section(card, "Privacy and personal data")
    assert NOTE in privacy
    assert "passages of the text" not in privacy


def test_long_device_example_inputs_are_shortened_on_the_card(mcu_env):
    import json

    ex_dir = mcu_env.reg.model_dir(mcu_env.model) / "examples"
    ex = json.loads(sorted(ex_dir.glob("*.json"))[0].read_text())
    shown, note = cards._short_vector(list(range(1152)), "example-1.json")
    assert json.loads(shown) == list(range(24)) and "1,152" in note
    assert cards._short_vector(ex["input"], "x.json")[1] == ""  # the fixture stays complete
