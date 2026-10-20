"""Status by rule from the pre-registered criteria (feature 021, T013; FR-018, research R6)."""

import yaml
from condmon_helpers import CRITERIA_YAML

from mobility_model_zoo.condition_monitoring.activity import evaluate as ev

CRITERIA = yaml.safe_load(CRITERIA_YAML)
GOOD = {
    "int8_macro_f1": 0.93,
    "int8_accuracy": 0.94,
    "int8_f1_min_class": 0.85,
    "float_macro_f1": 0.94,
}


def _perf(flash=60.0, ram=20.0, latency=40000.0, origin="real_board"):
    rows = [("flash_kb", flash), ("ram_kb", ram), ("latency_us", latency)]
    return {
        "metrics": [
            {"name": n, "value": v, "origin": origin, "hardware": "ESP32 (esp32-1)"} for n, v in rows
        ]
    }


def _by_id(verdict):
    return {c["id"]: c for c in verdict["criteria"]}


def test_untested_transfer_keeps_the_release_experimental():
    v = ev.derive_verdict(CRITERIA, GOOD, _perf(), {"transfer_tested": False})
    c = _by_id(v)
    assert all(c[i]["met"] for i in ("S1", "S2", "S3", "S4"))
    assert c["S5"]["met"] is False and c["S5"]["measured"] is False
    assert v["status"] == "experimental"
    assert v["kill"] == {"fired": [], "outcome": "none"}
    assert any(r.startswith("S5") for r in v["reasons"])
    assert v["criteria_version"] == 1


def test_released_only_when_every_criterion_is_met():
    v = ev.derive_verdict(CRITERIA, GOOD, _perf(), {"transfer_tested": True})
    assert v["status"] == "released" and v["reasons"] == []


def test_budgets_without_performance_are_not_measured():
    v = ev.derive_verdict(CRITERIA, GOOD, None, {"transfer_tested": True})
    s4 = _by_id(v)["S4"]
    assert s4 == {
        "id": "S4",
        "measured": None,
        "threshold": "flash_kb <= 128, ram_kb <= 32, latency_us <= 100000 "
        "on ESP32 (esp32-1, LilyGO LoRa32)",
        "met": False,
        "note": "not measured",
    }
    assert v["status"] == "experimental"
    assert "K3" not in v["kill"]["fired"]


def test_emulator_budgets_do_not_meet_the_reference_criterion():
    v = ev.derive_verdict(CRITERIA, GOOD, _perf(origin="emulator"), {"transfer_tested": True})
    s4 = _by_id(v)["S4"]
    assert s4["met"] is False and "emulator" in s4["note"]
    assert v["status"] == "experimental"


def test_k1_fires_below_the_macro_f1_floor():
    metrics = {**GOOD, "int8_macro_f1": 0.79, "float_macro_f1": 0.80}  # K2 stays quiet
    v = ev.derive_verdict(CRITERIA, metrics, _perf(), {"transfer_tested": False})
    assert v["kill"] == {"fired": ["K1"], "outcome": "kill"}


def test_k2_fires_on_a_large_int8_loss():
    metrics = {**GOOD, "int8_macro_f1": 0.91, "float_macro_f1": 0.95}
    v = ev.derive_verdict(CRITERIA, metrics, _perf(), {"transfer_tested": False})
    assert v["kill"]["fired"] == ["K2"]


def test_k3_fires_when_the_reference_board_exceeds_a_budget():
    v = ev.derive_verdict(CRITERIA, GOOD, _perf(latency=150000.0), {"transfer_tested": False})
    assert v["kill"]["fired"] == ["K3"]
    assert _by_id(v)["S4"]["met"] is False


def test_reasons_name_every_missed_criterion_with_its_value():
    metrics = {**GOOD, "int8_accuracy": 0.88, "int8_f1_min_class": 0.71}
    v = ev.derive_verdict(CRITERIA, metrics, None, {"transfer_tested": False})
    ids = [r.split(" ", 1)[0] for r in v["reasons"]]
    assert ids == ["S2", "S3", "S4", "S5"]
    assert "0.88" in v["reasons"][0] and "0.71" in v["reasons"][1]
