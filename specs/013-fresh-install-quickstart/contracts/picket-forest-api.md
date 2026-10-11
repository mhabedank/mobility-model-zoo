# Contract: `mobility_model_zoo.security.can_ids.picket_forest`

The user-facing Python module of picket-forest. Pure numpy (plus joblib and scikit-learn for the
forest), no compiler, no repository checkout, no pandas. Every function is deterministic.

```python
from mobility_model_zoo.security.can_ids import picket_forest as pf
```

## Loading

| Function | Signature | Behaviour |
|---|---|---|
| `load_model` | `(path) -> dict` | `joblib.load`; validates `format == "picket-forest-v2"` and the keys `model`, `threshold`, `rules_margin`, `alarm`; raises `ValueError` otherwise |
| `load_table` | `(path) -> Table` | reads `picket-forest-table-v1` JSON; raises `ValueError` on another `format` |
| `save_table` | `(table, path, note="") -> None` | writes the JSON (sorted ids, 2-space indent, trailing newline) |
| `load_capture` | `(path) -> dict` | reads an `examples/*.json` file into a capture (`ts` seconds, `can_id`, `dlc`, `data`, `y` zeros, `id` = file stem) |
| `read_candump` | `(path, name=None) -> dict` | candump log lines `(ts) iface ID#DATA` into a capture; frames without a match are ignored; `y` zeros |

## Calibrating

| Function | Signature | Behaviour |
|---|---|---|
| `calibrate` | `(captures: list[dict], max_seconds=None) -> Table` | moved from `calibrated.py` unchanged; refuses captures with attack labels |
| `Table` | dataclass | moved from `calibrated.py` unchanged (`period`, `window`, `max_count`, `dlc`, `bus_rate`, `seconds`, `entries()`) |

## Scoring

| Function | Signature | Behaviour |
|---|---|---|
| `features` | `(cap, table) -> float32[n, 10]` | the ten calibrated features of every frame, bit-exact with `msml_cal_update` |
| `rules` | `(x, margin=0.25) -> float32[n]` | the rules decision per frame (moved from `calibrated.py`) |
| `alarms` | `(ts_us, flagged, k, window_ms, holdoff_ms=1000.0) -> uint8[n]` | alarm stage, bit-exact with `msml_alarm_update` |
| `vote_score` | `(clf, x) -> float32[n]` | share of trees voting attack (moved from `forest.py`) |
| `score` | `(cap, table, model: dict) -> (float32[n], uint8[n])` | `features` → `vote_score` and `rules(margin=model["rules_margin"])` → `alarms(**model["alarm"])`; same result as `release_export_v2.reference` |
| `summary` | `(cap, scores, alarms) -> str` | deterministic text: `"<n> frames, <s> s; <k> alarm(s) at frame <i> (t=<t> s) ...; highest forest score <v>"` |

## Compatibility

- `calibrated.Table`, `calibrated.calibrate`, `calibrated.rules`, `calibrated.to_us`,
  `calibrated.bucket_counts`, `calibrated.FEATURE_NAMES` and `forest.vote_score` keep working as
  re-exports; `calibrated.features` (C) and `calibrated.event_flags` (C) are unchanged.
- `release_export_v2.reference` keeps its signature and result; its implementation may call
  `picket_forest` or the C path, but `parity()` reports both against C.

## Parity guarantees (tests)

- Without a compiler: for each of the three example captures, `score()` with the released model
  and the published table reproduces `expected_scores` (float32 bit patterns) and `expected_alarms`
  exactly.
- With a compiler (firmware job): `features()` equals `calibrated.features()` bit for bit, and
  `alarms()` equals `forest_features.alarms()`, on every parity capture of
  `test_release_export_v2.py` and on the examples; `parity()` reports
  `{frames, score_mismatches, alarm_mismatches, numpy_feature_mismatches}` and the export refuses
  a release when any count is non-zero.

## The card snippet (`card.how_to_run` of picket-forest)

```python
from huggingface_hub import hf_hub_download

from mobility_model_zoo.security.can_ids import picket_forest as pf

model = pf.load_model(hf_hub_download("{repo_id}", "model.joblib", revision="{revision}"))
table = pf.load_table(hf_hub_download("{repo_id}", "calibration_table.json", revision="{revision}"))
capture = pf.load_capture(hf_hub_download("{repo_id}", "examples/01-fabrication.json", revision="{revision}"))
scores, alarms = pf.score(capture, table, model)
print(pf.summary(capture, scores, alarms))
```

## The own-data snippet (`card.own_data` of picket-forest)

```python
from mobility_model_zoo.security.can_ids import picket_forest as pf

benign = [pf.read_candump(p) for p in ["drive.log", "idle.log", "parked.log"]]  # candump -L logs, benign traffic only
table = pf.calibrate(benign)  # cover driving, idle and parked; at least 60 minutes
pf.save_table(table, "my_vehicle_table.json")  # use it in place of calibration_table.json above
# For the device: `zoo-security can-ids v2 table drive.log idle.log parked.log` writes picket_forest_table.h
```
