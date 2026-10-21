"""The rendered pace-cnn card holds every item FR-020 names (feature 021, T057)."""

import json

import pytest

from mobility_model_zoo.edge.paths import repo_root
from mobility_model_zoo.release import card as cards
from mobility_model_zoo.release.registry import Registry

ROOT = repo_root()
QUALITY = ROOT / "zoo/models/pace-cnn/results/0.1.0/quality.json"
PERFORMANCE = ROOT / "zoo/models/pace-cnn/results/0.1.0/performance.json"


@pytest.fixture(scope="module")
def card() -> str:
    if not PERFORMANCE.exists():
        pytest.skip("the card renders only with device results (performance.json, US2 T049)")
    reg = Registry(ROOT)
    return cards.render(
        cards.CardInput(reg, "pace-cnn", "0.1.0", record=reg.record_raw("pace-cnn", "0.1.0"))
    )


def _section(card, heading):
    return card.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_status_usage_class_and_licence(card):
    assert "status: **experimental**" in card
    assert "Commercial use permitted · licence Apache-2.0" in card


def test_intended_use_out_of_scope_and_limitations(card):
    out = _section(card, "Out-of-scope use").lower()
    for use in ("work", "insurance", "credit", "profiling", "fall detection", "transport"):
        assert use in out, use
    limits = _section(card, "Limitations and risks").lower()
    assert "sitting" in limits and "worst test subject" in limits
    assert _section(card, "Intended use").strip()


def test_quality_rows_with_reference(card):
    quality = _section(card, "Quality")
    assert "labels of the uci-har dataset" in quality and "uci-har-v1" in quality
    names = [m["name"] for m in json.loads(QUALITY.read_text())["metrics"]]
    for name in names:  # headline, per-class, worst subject, seed spread, float, mismatches
        assert f"`{name}`" in quality, name


def test_budget_rows_with_origin(card):
    if not PERFORMANCE.exists():
        pytest.skip("device results not measured yet (US2)")
    speed = _section(card, "Speed and memory")
    for name in ("flash_kb", "ram_kb", "latency_us"):
        assert f"`{name}`" in speed
    assert "real board" in speed or "emulator" in speed


def test_dataset_attribution_input_contract_and_privacy(card):
    data = _section(card, "Training data and attribution")
    for item in ("Reyes-Ortiz", "Human Activity Recognition Using Smartphones", "10.24432/C54S4K"):
        assert item in data, item
    assert "CC BY 4.0" in data and "Modifications:" in data
    io = _section(card, "Input and output")
    for item in ("50 Hz", "128", "0.3 Hz", "config.json", "g", "rad/s"):
        assert item in io, item
    privacy = _section(card, "Privacy and personal data")
    assert "volunteers" in privacy and "subject number" in privacy


def test_no_pre_zoo_numbers_on_the_card(card):
    assert "93.3" not in card  # the pre-zoo research report never reaches the card (SC-007)
