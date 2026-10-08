# Contract: path map

Where every file goes. Import rows are fed to `git filter-repo` (`--path-rename old:new`); a file in a source branch that matches no row and is not in the strip list fails the import script. Paths ending in `/` are directories.

## A. Productdev move (ordinary `git mv` on the feature branch)

| From | To |
|---|---|
| `guideline/` | `topics/productdev/guideline/` |
| `reports/pilot-v2/`, `reports/spike-v2/`, `reports/scout-large/` | `topics/productdev/reports/…` (same subfolders) |
| `benchmarks/` | `topics/productdev/benchmarks/` |
| `spike/` | `topics/productdev/spike/` |
| `deploy/railway-perf/` | `topics/productdev/deploy/railway-perf/` |
| `docs/recipes/` (including `figures/`) | `topics/productdev/recipes/` |
| `scripts/pilot/`, `scripts/span/`, `scripts/railway/`, `scripts/spark/` | `topics/productdev/scripts/…` (same subfolders) |
| `docs/adding-a-model.md`, `docs/hf-org/`, `scripts/hf_org_avatar.py` | unchanged (shared) |
| `configs/productdev/jtbd/` | unchanged; `root`, `guideline`, `examples`, `benchmarks`, `reports` entries updated |

Not moved: `data/` (gitignored working data, stays at the top level and is never committed), `zoo/`, `specs/`, `src/`, `tests/`.

## B. goldberg (`origin/claude/clever-goldberg-ygio83`)

| From | To |
|---|---|
| `README.md` | `topics/security/README.md` (rewritten in English after import) |
| `docs/roadmap.md` | `topics/security/roadmap.md` |
| `docs/research/README.md` | `topics/security/research/README.md` |
| `docs/research/01-bedrohungslandschaft.md` | `topics/security/research/01-threat-landscape.md` |
| `docs/research/02-literatur.md` | `topics/security/research/02-literature.md` |
| `docs/research/03-datensaetze.md` | `topics/security/research/03-datasets.md` |
| `docs/research/04-hardware.md` | `topics/security/research/04-hardware.md` |
| `docs/research/05-toolchain-und-publishing.md` | `topics/security/research/05-toolchain-and-publishing.md` |
| `docs/research/notes/` | `topics/security/research/notes/` |
| `src/msml/__init__.py`, `src/msml/{can,datasets,eval}/__init__.py` | dropped (replaced by zoo package `__init__`s) |
| `src/msml/can/features.py` | `src/mobility_model_zoo/security/can_ids/forest_features.py` |
| `src/msml/datasets/can_train_and_test.py` | `src/mobility_model_zoo/security/can_ids/can_train_and_test.py` |
| `src/msml/eval/metrics.py` | `src/mobility_model_zoo/security/can_ids/metrics.py` |
| `models/can-ids-tiny/pipeline.py` | `src/mobility_model_zoo/security/can_ids/forest.py` |
| `models/can-ids-tiny/MODEL_CARD.md` | `topics/security/reports/picket-forest/research-card.md` |
| `models/can-ids-tiny/README.md` | `topics/security/recipes/picket-forest.md` |
| `models/can-ids-tiny/results/config.json`, `protocol_results.json`, `benchmarks/qemu-*.json` | `topics/security/reports/picket-forest/…` (same names) |
| `models/can-ids-tiny/c/can_ids_tiny.{c,h}`, `c/host_score.c` | `firmware/picket-forest/c/…` (renamed `picket_forest.{c,h}` after import) |
| `models/can-ids-tiny/c/generated/can_ids_tiny_config.h` | `firmware/picket-forest/c/generated/` (small, needed by the host build) |
| `models/can-ids-tiny/firmware/` | `firmware/picket-forest/esp-idf/` |
| `models/can-ids-tiny/firmware-esp8266/` | `firmware/picket-forest/esp8266/` |
| `models/can-ids-tiny/prebuilt/README.md` | `firmware/picket-forest/README.md` |
| `firmware/components/msml_can_features/` | `firmware/components/can_features/` |
| `scripts/setup-cloud.sh` | `scripts/setup-cloud.sh` |
| `tests/test_can_features.py`, `tests/test_metrics.py` | `tests/security/can_ids/…` |

**Stripped from every commit**: `models/can-ids-tiny/c/generated/test_vectors.h`, `models/can-ids-tiny/c/generated/can_ids_tiny_model.h`, `models/can-ids-tiny/prebuilt/*.bin`, `models/can-ids-tiny/results/model.joblib`, `models/can-ids-tiny/results/logs/`, `models/can-ids-tiny/publish.py`, `.github/`, `.gitignore`, `LICENSE`, `pyproject.toml`, `uv.lock`.

## C. volta (`origin/claude/cool-volta-rqsgdx`)

| From | To |
|---|---|
| `README.md` | `docs/edge/hil-bench.md` |
| `docs/ci.md`, `docs/extending.md`, `docs/hardware.md`, `docs/protocol.md` | `docs/edge/{ci,extending,hardware,protocol}.md` |
| `docs/datasets.md` | `topics/condition-monitoring/research/datasets-volta.md` (split after import into the two topics' `datasets.yaml` and research notes) |
| `hilbench/__init__.py` | `src/mobility_model_zoo/edge/bench/__init__.py` |
| `hilbench/{build,cli,config,device,discovery,flash,lock,power,pytest_plugin,qemu,results,session,transport}.py` | `src/mobility_model_zoo/edge/bench/…` (same names) |
| `hilbench/data/{__init__,registry,download}.py` | `src/mobility_model_zoo/datasets/…` (same names) |
| `hilbench/ml/__init__.py` | `src/mobility_model_zoo/edge/int8/__init__.py` |
| `hilbench/ml/{model,quant,reference,floatnet,codegen,tflite_import,train}.py` | `src/mobility_model_zoo/edge/int8/…` (same names) |
| `hilbench/ml/datasets.py` | `src/mobility_model_zoo/edge/bench/synthetic.py` |
| `hilbench/ml/zoo.py` | `src/mobility_model_zoo/edge/bench/reference_models.py` |
| `hilbench/ml/features.py` | `src/mobility_model_zoo/condition_monitoring/sound_anomaly/features.py` |
| `hilbench/ml/train_real.py` | `src/mobility_model_zoo/edge/train_real.py` (split after import into `security/can_ids/mlp.py`, `condition_monitoring/sound_anomaly/train.py`, `condition_monitoring/activity/train.py`) |
| `firmware/lib/benchapp/`, `firmware/lib/microinfer/`, `firmware/native/`, `firmware/src/`, `firmware/scripts/`, `firmware/platformio.ini` | `firmware/bench/…` (same relative paths) |
| `hil/` | `hil/` |
| `conftest.py` | dropped (plugin loaded via `-p`, R15) |
| `tests/unit/test_{c_engine,quant,tflite_import}.py`, `tests/unit/data/` | `tests/edge/int8/…` |
| `tests/unit/test_{config_discovery,device_session,flash_power,models_zoo}.py`, `tests/unit/conftest.py` | `tests/edge/bench/…` |
| `tests/unit/test_data_range.py` | `tests/datasets/test_download_range.py` |
| `tests/unit/test_train_real.py` | `tests/edge/test_train_real.py` (split with `train_real.py`) |
| `tests/hil/` | `tests/edge/hil/` |

**Stripped from every commit**: `firmware/lib/modelzoo/` (generated at build time), `models/` (weights, eval sets, manifest, train and hub requests), `hilbench/hub.py`, `.github/`, `.gitignore`, `LICENSE`, `pyproject.toml`.

## D. Resulting top level

```text
configs/<topic>/<task>/          configs/productdev/jtbd, configs/security/can-ids, configs/condition-monitoring/{sound-anomaly,activity}
docs/                            adding-a-model.md, credentials.md, layout.md, edge/, hf-org/
firmware/                        bench/ (PlatformIO + microinfer), components/can_features/, picket-forest/
hil/                             board inventory, targets, udev rules, host setup
scripts/                         shared scripts only (hf_org_avatar.py, setup-cloud.sh, import/)
specs/                           NNN-feature/
src/mobility_model_zoo/          release/, datasets/, edge/{int8,bench}/, productdev/jtbd/, security/can_ids/, condition_monitoring/{sound_anomaly,activity}/, sandbox/
tests/                           unit/, release/, integration/, datasets/, edge/, security/, condition_monitoring/
topics/<topic>/                  README.md, research/, datasets.yaml, reports/, recipes/ (+ topic-specific)
zoo/                             topics.yaml, MODELS.md, models/<name>/
```
