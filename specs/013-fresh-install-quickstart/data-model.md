# Data model: Quickstart that works from a fresh install

Entities of the feature, their fields and the rules the gate enforces. File formats are the
contract for the model repository; see [contracts/model-repo-files.md](contracts/model-repo-files.md).

## Install line (`model.yaml` → `card.install`)

| Field | Value |
|---|---|
| text | `pip install "mobility-model-zoo[<extra>] @ git+https://github.com/mhabedank/mobility-model-zoo@<tag>"` |
| extra | `text` for runtime `python` models, `edge` for runtime `mcu` models; exactly the extra whose dependencies the run snippet imports |
| `<tag>` | replaced by `<name>/v<version>` at card build (`install_line`) |

Rules: the gate's fresh environment is built from this line alone (R4); the Python requirement
printed next to it comes from the package metadata (`python_requirement()`), never from the YAML.

## Run snippet (`card.how_to_run`) and own-data snippet (`card.own_data`, new, optional)

| Field | `how_to_run` | `own_data` |
|---|---|---|
| placeholders | `{repo_id}`, `{revision}`; `{text}` for runtime `python` | `{repo_id}`, `{revision}` optional |
| completeness | every name it uses is imported, defined or downloaded inside the snippet | may name user files (`drive.log`) that the user supplies |
| executed by the gate | yes, every runtime, fresh environment (rule 12) | no (needs the user's data); shown on card and website |
| output | recorded: per example for `python`, once as `how_to_run_output` for `mcu` | none |

## Example capture (`zoo/models/picket-forest/examples/<nn>-<attack>.json`, published as `examples/<file>`)

Existing format (gate `TREE_EXAMPLE_FIELDS`), unchanged:

| Field | Type | Meaning |
|---|---|---|
| `source` | `"synthetic"` | provenance; only `synthetic` or a redistributable dataset may be published |
| `generator` | `{name, version, seed, attack}` | how the capture was made |
| `frames` | list of `[ts_us, can_id, dlc, data[8]]` | frames in bus order, integer microseconds |
| `expected_scores` | list of 8-hex-digit strings | float32 bit pattern of the forest score per frame, produced by the release's C scorer |
| `expected_alarms` | list of frame indices | frames at which the alarm stage fires |

Rules: the staged copy is byte-identical to the registry file (new check in the tree-file rule);
`picket_forest.load_capture` reads it into a capture.

## Capture (in memory, `picket_forest` module)

A `dict` as the tooling uses today: `ts` (float64 seconds), `can_id` (uint32), `dlc` (uint8),
`data` (uint8, n × 8), `y` (int8 labels, zeros for benign); optional `id` (name). `read_candump`
and `load_capture` produce it; `calibrate` refuses a capture with `y != 0`.

## Calibration table (`Table` in memory; `calibration_table.json` published; `picket_forest_table.h` on the device)

| Field | In memory (`Table`) | JSON (`picket-forest-table-v1`) | C header |
|---|---|---|---|
| ids | keys of `dlc` | `ids[]` sorted by `id` | entries sorted by id |
| `period_us` | `period[id]` (absent → 0) | int | `uint32` |
| `window_us` | `window[id]` | int | `uint32` |
| `max_count` | `max_count[id]` (clipped to 65535 in `entries()`) | int | `uint16` |
| `dlc` | `dlc[id]` | int | `uint8` |
| `bus_rate` | float32 value | number | `float` |
| `seconds` | benign seconds used | number | comment only |
| `note` | — | string (origin of the table) | comment |

Rules: `load_table(save_table(t)) == t` for every field; the JSON of a release parses to the
entries of its header (gate check); `calibrate` keeps at most 128 ids (`MAX_IDS`).

## Model file (`model.joblib`, existing)

Dict with `model` (scikit-learn `RandomForestClassifier`), `threshold`, `decision`,
`rules_margin`, `alarm` (`{k, window_ms, holdoff_ms}`), `features`, `format`.
`picket_forest.load_model(path)` returns it; `score(cap, table, saved)` reads `model`,
`rules_margin` and `alarm` from it.

## Score result

`score()` returns `(scores: float32[n], alarms: uint8[n])`; `summary(cap, scores, alarms)` returns
the printed text: frame count, duration, number of alarms with frame index and time, highest
forest score. The text is deterministic (fixed number formats) so the gate can record it.

## Fresh environment (gate)

| Field | Value |
|---|---|
| interpreter | Python 3.12 via `uv venv` |
| install | `"<checkout>[<extras of the install line>]"`, `UV_TORCH_BACKEND=cpu` |
| run | one script per snippet, `HOME` and `HF_HOME` inside the temp dir, token only through `HF_TOKEN`, 600 s limit |
| result | `(returncode, stdout, stderr)`; stderr with the token masked |

## Release record (patch)

`0.2.1.yaml` (picket-forest): written by `zoo stage` from the repacked directory; `files` lists
the 0.2.0 files plus `examples/*.json` and `calibration_table.json`; `change_type: patch`.
`0.1.3.yaml` (scout-large): copy of `0.1.2.yaml` with new `version`, `date`, `change_type: patch`,
`changes`, `recipe.git_commit`; `files` and `staging` unchanged; `published` and `deprecated` null.

## Quickstart document (`docs/quickstart.md`)

Sections: prerequisites (Python 3.12, uv), one environment, install (install line of the latest
published picket-forest and scout-large, taken from the registry at site build), run (a script
file), expected output, pitfalls (R9), where to go next (model pages). Rendered at `/quickstart/`
and linked from the README.
