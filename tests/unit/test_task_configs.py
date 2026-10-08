"""Task configs match the code they document (feature 005, T043)."""

from pathlib import Path

import pytest

from mobility_model_zoo.condition_monitoring.activity import train as pace
from mobility_model_zoo.condition_monitoring.sound_anomaly import train as hum
from mobility_model_zoo.edge.int8.keras_export import TRAIN_DEFAULTS, load_config
from mobility_model_zoo.security.can_ids import mlp

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ("configs/security/can-ids/picket-mlp.yaml", mlp),
    ("configs/condition-monitoring/sound-anomaly/hum-fan.yaml", hum),
    ("configs/condition-monitoring/activity/pace-cnn.yaml", pace),
]


@pytest.mark.parametrize(("path", "module"), CASES)
def test_config_matches_code(path, module):
    opts = load_config(ROOT / path, module.NAME, module.FIXED)
    assert set(opts) == set(TRAIN_DEFAULTS)


def test_drift_is_refused(tmp_path):
    text = (ROOT / CASES[0][0]).read_text().replace("- 64", "- 65", 1)
    p = tmp_path / "c.yaml"
    p.write_text(text)
    with pytest.raises(SystemExit, match="architecture"):
        load_config(p, mlp.NAME, mlp.FIXED)


def test_wrong_model_is_refused():
    with pytest.raises(SystemExit, match="expected"):
        load_config(ROOT / CASES[0][0], "hum-fan", hum.FIXED)


def test_forest_config_matches_code():
    yaml = pytest.importorskip("yaml")
    from mobility_model_zoo.security.can_ids import forest

    cfg = yaml.safe_load((ROOT / "configs/security/can-ids/picket-forest.yaml").read_text())
    assert cfg["model"] == "picket-forest"
    assert cfg["grid"] == forest.GRID
    assert cfg["benign_keep"] == forest.BENIGN_KEEP
    assert cfg["alarm"]["holdoff_ms"] == forest.ALARM_HOLDOFF_MS
    assert cfg["alarm"]["budget_false_alarms_per_hour"] == forest.ALARM_BUDGET_PER_HOUR
    assert cfg["features"] == forest.EXPORT_FEATURES
    assert cfg["min_samples_leaf"] == 20
    assert forest.ALARM_GRID == [
        (k, w) for k in cfg["alarm"]["grid_k"] for w in cfg["alarm"]["grid_window_ms"]
    ]
