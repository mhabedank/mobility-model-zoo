# Contract: commands

New and changed commands. Existing `zoo` and `jtbd` commands keep their behaviour unless listed. Exit codes follow the `zoo` convention (0 ok, 1 usage, 2 check failed, 3 refused, 4 external service, 5 missing input, 6 internal).

## `zoo data` (shared, `mobility_model_zoo.datasets`)

| Command | Behaviour |
|---|---|
| `zoo data list [--topic T] [--status S]` | Table of declarations: id, topic, license, permitted use, commercial, size, status. |
| `zoo data info ID` | Full declaration plus local state (`SOURCE.json` if downloaded). |
| `zoo data verify [ID…]` | For each declaration with an API (Zenodo, UCI), compares the license the provider declares today with the declaration; `manual` entries report their last manual check date. Exit 2 on any mismatch, naming the dataset. |
| `zoo data download ID [--force] [--max N]` | Downloads into `$MMZ_DATA/<id>/` (default `~/.cache/mobility-model-zoo/datasets`), refuses paths inside the repository (exit 3), refuses `rejected` and, without `--force`, `broken_at_source` (exit 3); verifies the license first; writes `SOURCE.json` (origin, license, retrieval date, per-file sha256 and size). |
| `zoo data path ID`, `zoo data tree ID` | Local path; file listing. |
| `zoo data validate` | Validates every `topics/*/datasets.yaml` against `datasets.schema.json` (also run by `zoo validate --all`). |

Library guard: `mobility_model_zoo.datasets.require_training_allowed(id)` raises `UsageRefused` (exit 3) unless the declaration has `permitted_use: training_allowed` and `status: active`.

## `edge` (shared, `mobility_model_zoo.edge.bench`; former `hilbench`)

Same subcommands and options as `hilbench` on the volta branch, with these changes:

- Removed: `hub …`, `train …` (training moves to the task tools).
- `zoo` → `refs`: rebuilds the synthetic bench reference models deterministically.
- `build` generates `firmware/bench/lib/modelzoo/src/model_zoo.{c,h}` from the reference models plus any models given with `--model PATH.npz` (repeatable); generated files are gitignored.
- Default inventory: `hil/boards.yaml` (`MMZ_BOARDS` overrides); results in `results/edge/<timestamp>/` (gitignored).
- `edge measure MODEL.npz -b BOARD --out FILE.json`: runs the performance suite for one model and writes performance metrics in the `results.schema.json` format with `origin` set from the board type (`real_board`, `emulator`, `simulator`).

## `security can-ids` (task tool, `mobility_model_zoo.security.can_ids`)

| Command | Behaviour |
|---|---|
| `security can-ids frames DATASET` | Converts a downloaded dataset (`can-train-and-test`, `road`) into the common frame format (Parquet) under `$MMZ_DATA/derived/`. |
| `security can-ids evaluate MODEL --benchmark can-ids-v1` | Scores a model on every split of the frozen benchmark; writes frame and event metrics (quality results format). |
| `security can-ids forest evaluate|alarms|export|convert|testvectors` | The goldberg pipeline steps for `canary-forest`; `testvectors` writes into `$MMZ_DATA/derived/`, never into the repository. |
| `security can-ids mlp train [--epochs N] [--seed S]` | Trains `canary-mlp` (int8, bit-exact check against TFLite), output outside the repository. |
| `security can-ids freeze` | Freezes benchmark `can-ids-v1` (split manifest with hashes). |

## `condmon` (task tools, `mobility_model_zoo.condition_monitoring`)

| Command | Behaviour |
|---|---|
| `condmon sound-anomaly train|evaluate|freeze` | `murmur-fan` on MIMII 6 dB fan; benchmark `mimii-fan-v1`. |
| `condmon activity train|evaluate|freeze` | `pace-cnn` on UCI HAR; benchmark `uci-har-v1`. |

Every `train` command calls `require_training_allowed` for each dataset it reads.

## `zoo` changes

- `zoo check` runs the new rule 15 (device evidence) and the extended rules 6, 10, 12, 13 ([release-format.md](release-format.md)).
- `zoo validate --all` also validates dataset declarations and topic folders (each non-sandbox topic has `topics/<id>/README.md` and `datasets.yaml`).
- `zoo deprecate` renders the card from `model.yaml` at the version's tag.
- `zoo history-check` unchanged (gitleaks plus forbidden paths); `.bin` stays forbidden in git.
