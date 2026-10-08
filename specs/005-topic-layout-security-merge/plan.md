# Implementation Plan: Topic layout and security merge

**Branch**: `005-topic-layout-security-merge` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-topic-layout-security-merge/spec.md`

## Summary

The zoo repository is reorganised by topic, and the content of `mhabedank/mobility-security-ml` is merged into it with its history:

1. **Layout** (R3, R14): every topic gets `topics/<topic>/` (README, research, datasets, reports, recipes). The productdev material moves there from the top level without touching published release records; `model.yaml` figure paths and every config, script and test reference follow; `zoo deprecate` renders from the tagged `model.yaml`.
2. **Constitution 2.0.0** (R12, done before implementation on 2026-10-08): model-labeled vs. ground-truth tasks, metric naming instead of an accuracy ban, tools and budgets per task, measurement origin, dataset storage outside git with a redistribution check, topic layout.
3. **History import** (R1, R4): both source branches are rewritten with `git filter-repo` to the zoo paths ([contracts/path-map.md](contracts/path-map.md)) and merged with unrelated histories. Raw dataset frames, firmware images, generated sources, weights and the separate Hugging Face pipeline are stripped from every commit.
4. **Integration** (R5, R9, R11, R15, R16): code becomes `mobility_model_zoo.{datasets, edge.int8, edge.bench, security.can_ids, condition_monitoring.*}` with CLIs `zoo data`, `edge`, `security`, `condmon`; overlapping code is reduced to one implementation per concern; tests, extras and lint follow the zoo's conventions.
5. **Datasets** (R10): per-topic `datasets.yaml`, shared downloader writing outside the repository, license verification in CI, a training guard for `benchmark_only` data.
6. **Release tool for edge models** (R13): `runtime: mcu`, KB budgets, measurement origin, ground-truth quality wording, dataset license compatibility, host-reference examples, new gate rule 15 ([contracts/release-format.md](contracts/release-format.md)).
7. **Models and tasks** (R7, R8): `picket-forest`, `picket-mlp` (security, `can-ids`), `hum-fan` (condition-monitoring, `sound-anomaly`), `pace-cnn` (condition-monitoring, `activity`) registered with draft `0.1.0` records; three task documents with scope, reference, frozen benchmark names and budgets. Nothing is published.
8. **Docs and retirement** (R17, R18): English translations, README and adding-a-model guide, credentials document; secret scan; pull request; after the merge the old repository gets a pointer README, loses its secrets and is archived.

## Technical Context

**Language/Version**: Python 3.12 with `uv` (unchanged); C99 and C++ (Arduino) for firmware; ESP-IDF 5.5 for the `picket-forest` device build.

**Primary Dependencies**:
- Base install (what `scout-large` users get): unchanged.
- `release` extra: unchanged plus nothing new.
- New `edge` extra: numpy, pyserial, pyyaml, jsonschema. `edge-hw`: esptool, platformio, pytest-xdist. `edge-train`: tensorflow-cpu, tflite, ai-edge-litert, scikit-learn, emlearn, setuptools, pandas, pyarrow (R16).
- Tools: `git-filter-repo` (installed), `gitleaks` (used by `zoo history-check`), `gh`.

**Storage**: Files. Registry in `zoo/`, declarations in `topics/*/datasets.yaml`, downloaded data in `$MMZ_DATA` outside the repository, generated firmware sources and bench results gitignored.

**Testing**: `pytest`. Existing suite (363 passed, 1 skipped, about 143 s offline) must stay green. New: dataset declaration schema and guard, downloader (mocked HTTP, from volta), int8 engine and TFLite import (from volta), bench unit tests (from volta), CAN features and metrics (from goldberg), release format changes (schemas, rules 1, 6, 10, 12, 13, 15, card rendering for `mcu`, deprecate from tag), layout checks in `zoo validate`, merge-log completeness. HIL suites marked `hil`, run in CI against the simulator and QEMU (R15).

**Target Platform**: Development on macOS (Apple silicon) and Linux; CI on `ubuntu-latest`; models on ESP8266, ESP32, ESP32-S3, ESP32-C3, RP2040/RP2350, STM32F446, nRF52840.

**Project Type**: single project (library plus the CLIs `zoo`, `jtbd`, `edge`, `security`, `condmon`) with firmware.

**Performance Goals**: default `pytest` run stays under 4 minutes; the CI `test` job stays under 10 minutes; firmware matrix only on firmware changes.

**Constraints**:
- No model is published and nothing is written to Hugging Face; the old staging repos are only listed.
- Published `scout-large` records, tags and cards are not modified (FR-004).
- No dataset content and no credentials in any commit of the merged history (SC-005).
- All documents in English (FR-012).
- No cash cost.

**Scale/Scope**: about 50 files from goldberg and 95 from volta (before stripping), about 60 productdev files moved, 4 models registered, 3 new task documents, about 15 dataset declarations, 5 new or changed workflows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version **2.0.0** (amended from 1.4.0 on 2026-10-08 as a separate step before implementation, R12). Tasks touched: `jtbd` (paths only), new `can-ids`, `sound-anomaly`, `activity`; release through `zoo`.

| Principle | Touched | Pre-design | Post-design | How the plan complies |
|-----------|---------|------------|-------------|-----------------------|
| I. Problem-First | no | ✅ | ✅ | Scoped to model-labeled tasks by the existing scope note; no change for JTBD. |
| II. Grounded Evidence | no | ✅ | ✅ | As I. |
| III. Measure Before Optimizing | yes | ⚠ conflict (1.4.0) | ✅ (2.0.0) | Each new task names dataset labels as its frozen reference and gets a benchmark name and protocol before any result is reported (R8); metrics state their reference; old-repo numbers are reports, not benchmark results (R8). |
| IV. Riskiest Assumption First | yes | ⚠ conflict (1.4.0) | ✅ (2.0.0) | The agreement pilot applies to model-labeled tasks; each task document names its riskiest assumption (for `can-ids`: transfer to unseen vehicles and attacks). |
| V. Small and Local, Budgets per Task | yes | ⚠ gap (1.4.0) | ✅ (2.0.0) | Each task document defines its budgets (KB flash and RAM, latency) and reference board; measurement origin recorded; release beyond `experimental` needs a real board (gate rule 15). |
| VI. Clean Provenance | yes | ✅ | ✅ | Dataset declarations with license, permitted use, commercial use, retention (R10); downloads outside the repository; raw frames stripped from history (R4); share-alike enforced (rule 6); `redistribution` recorded per dataset, all `unclear` for now; no dataset published (FR-011). |
| VII. Metadata over Inference | no | ✅ | ✅ | Scoped to JTBD. |
| VIII. Fair Comparison | yes | ⚠ conflict (1.4.0) | ✅ (2.0.0) | One protocol per task; both CAN models on both test sets (R8). Tools follow the task: scikit-learn/emlearn for trees, Keras/LiteRT for int8 nets, justified in the task documents. |
| IX. Reproducible, Dated Releases | yes | ✅ | ✅ | Only the zoo pipeline publishes; volta's `hub` and `train` workflows dropped (R17); weights come from a retraining run at a zoo commit (R4); published versions untouched (R14). |
| X. Scope Discipline | no | ✅ | ✅ | Scoped to JTBD; each new task states scope in its task document. |
| Project Scope | yes | ✅ | ✅ | `<name>-<variant>` names (R7); one collection per topic; a new topic changes no existing model; topic layout added by amendment. |
| Tasks and Releases | yes | ✅ | ✅ | One tool per task (`security can-ids`, `condmon …`); shared `datasets` and `edge` modules are extracted because three tasks use them (R5). |
| Resources & Cost | yes | ✅ | ✅ | No cash cost; free CI runners for simulator and QEMU; real boards optional; development hardware kept apart from target boards (origin field). |
| Technical Spikes | yes | ✅ | ✅ | `spike/` moves unchanged; `src/` still never imports it (test path updated). |
| Development Workflow & Quality Gates | yes | ✅ | ✅ | Plan lists principles; amendment carries version bump and rationale; gate before reporting a result scoped per reference kind. |

Gate result: pass against constitution 2.0.0; no deviations.

## Project Structure

### Documentation (this feature)

```text
specs/005-topic-layout-security-merge/
├── plan.md              # This file
├── research.md          # Phase 0: R1–R18
├── data-model.md        # Phase 1: topic, task, model, dataset declaration, device measurement, credential, merge log
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   ├── path-map.md          # where every file goes (productdev move, both imports)
│   ├── cli.md               # zoo data, edge, security, condmon, zoo changes
│   └── release-format.md    # schema and gate changes for mcu models (schema copies added in implementation)
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/mobility_model_zoo/
├── release/                     # zoo CLI; schemas, gate, card extended (R13)
├── datasets/                    # declarations loader, downloader, license check, training guard (R10)
├── edge/
│   ├── int8/                    # QModel, quant, reference, floatnet, codegen, tflite_import, train
│   └── bench/                   # HIL bench, pytest plugin, `edge` CLI, synthetic reference models
├── productdev/jtbd/             # unchanged code, path defaults updated
├── security/can_ids/            # frames, forest (+ forest_features via C), mlp, metrics, cli
├── condition_monitoring/
│   ├── sound_anomaly/           # features (log-mel), train, evaluate
│   └── activity/                # train, evaluate
└── sandbox/

firmware/
├── bench/                       # PlatformIO project: benchapp, microinfer, HALs, native simulator
├── components/can_features/     # C streaming CAN features + alarm stage (ESP-IDF component, host build)
└── picket-forest/               # c/, esp-idf/, esp8266/

hil/                             # boards.yaml, qemu-boards.yaml, targets.yaml, udev rules, setup-host.sh

topics/
├── productdev/                  # README, datasets.yaml, research/, reports/, recipes/, guideline/, benchmarks/, spike/, deploy/, scripts/
├── security/                    # README, datasets.yaml, roadmap.md, research/ (+ merge-log.md), tasks/can-ids.md, reports/, recipes/
└── condition-monitoring/        # README, datasets.yaml, research/, tasks/{sound-anomaly,activity}.md, reports/, recipes/

configs/{productdev/jtbd, security/can-ids, condition-monitoring/{sound-anomaly,activity}}/
zoo/models/{scout-large, sandbox-pipeline-tiny, picket-forest, picket-mlp, hum-fan, pace-cnn}/
docs/{adding-a-model.md, layout.md, credentials.md, edge/, hf-org/}
scripts/{hf_org_avatar.py, setup-cloud.sh, import/}       # import/: filter-repo driver, merge-log check
tests/{unit, release, integration, datasets, edge/{int8,bench,hil}, security/can_ids, condition_monitoring}/
.github/workflows/{ci, firmware, datasets, hil, release-verify, release-publish, zoo-audit}.yml
```

**Structure Decision**: Single Python package with shared modules for datasets and edge deployment, one subpackage per topic and task, firmware and bench inventory at the top level, and all non-code material per topic under `topics/<topic>/` (R3, [contracts/path-map.md](contracts/path-map.md)).

## Implementation phases

| Phase | Content | Done when |
|---|---|---|
| 1 Layout | productdev move, reference updates, figure path pattern, deprecate-from-tag, `zoo validate` topic folder check, topic READMEs, `docs/layout.md` | tests green, `zoo validate --all` ok |
| 2 Constitution | amendment 2.0.0 with rationale (done, `d5ec1c1`) | version bumped, sync report at top |
| 3 Import goldberg | `scripts/import/` driver with path map and strip list; filter-repo; merge | `git log --follow` shows original commits; no stripped path in history |
| 4 Import volta | same | same |
| 5 Integration | package renames, imports, split `train_real.py`, CLIs, extras, ruff, tests moved, pytest plugin via `-p`, generated firmware sources at build time, synthetic refs regenerated | default `pytest` green incl. imported tests; `edge run -b sim` green |
| 6 Datasets | schema, declarations for both topics plus empty productdev file, `zoo data`, Bitbucket provider, manual license entries, training guard, `datasets.yml` | US3 scenarios pass |
| 7 Release format | schemas, contract copies, gate rules 1/6/10/12/13/15, card template, tests | release tests green; sandbox and scout-large unaffected |
| 8 Models and tasks | task documents, configs, four `model.yaml` + draft `0.1.0` records, results fixtures from the research runs marked as research, `zoo index` | `zoo check … --offline` gives a definite answer for all four |
| 9 Docs | translations, topic READMEs, top-level README, adding-a-model, credentials, merge log | no German file (SC-007); merge log complete (SC-001) |
| 10 CI and scans | `ci.yml` jobs, `firmware.yml`, `hil.yml` with variable gate, `zoo history-check`, PR | CI green on the PR; history check clean |
| 11 Retirement | after merge to `main`: old README, delete old secrets, archive, list `hilbench-*` staging repos for the owner | US5 scenarios pass |

## Complexity Tracking

No unjustified violation. The four conflicts with 1.4.0 (III, IV, V, VIII) were resolved by constitution 2.0.0, amended as its own step before implementation (FR-026, R12); the simpler alternative, a recorded deviation per model, was rejected because every edge model would repeat it.
