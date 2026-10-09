# Implementation Plan: picket-forest 0.1.0, honest CAN IDS benchmark and first release

**Branch**: `007-picket-forest-release` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-picket-forest-release/spec.md`

## Summary

The feature does five things:

- **Freeze `can-ids-v1`.** The benchmark covers can-train-and-test v1 (official splits) and ROAD held-out captures. Every capture is hashed, and duplicate captures under different labels must be resolved and recorded before the freeze.
- **Evaluate in one harness.** picket-forest runs next to four shortcut controls and a set of baselines.
- **Report what an operator sees.** The headline is event-level: the share of attack episodes detected at ≤ 1 and ≤ 10 false alarms per hour, and the time to alarm. Other metrics are attack-class only.
- **Release-gate support for tree models.** A new `engine: emlearn` path in the release gate replays synthetic frame examples through a host build of the staged C code.
- **Release 0.1.0 as experimental.** The release adds host, emulator and real-board (ESP8266 substitute) measurements, a compliance record and a card. It goes through the existing pipeline.

Success, partial and kill criteria for the transfer claim are fixed in advance ([research R10](research.md)).

## Technical Context

**Language/Version**: Python 3.12 (the venv runs 3.13); C99 for the device code.

**Primary Dependencies**:
- Existing: scikit-learn and emlearn (`edge-train` extra), numpy and pandas, the ctypes feature library (`forest_features.py`), PlatformIO and Espressif QEMU through `edge.bench`, and the `zoo` release tool and compliance harness.
- New: none.

**Storage**:
- Datasets, feature caches and detector runs live in `$MMZ_DATA`.
- In git: the manifest, resolutions, report, results, examples and card inputs.

**Testing**: pytest, with fixtures as tiny synthetic CAN logs and a tiny emlearn forest. The full evaluation is a manual run (hours) recorded in `validation.md`.

**Target Platform**:
- Training and evaluation: the owner's machine (macOS arm64) and Linux CI for the tests.
- Device: ESP32-class MCUs; reference board ESP32-S3.

**Project Type**: Library and CLI inside the zoo monorepo (`security` task tool, `zoo` release tool), plus firmware.

**Performance Goals**:
- Whole detection chain under 100 µs per frame on the reference board (headroom against about 225 µs per frame at full 500 kbit/s load). This is checked on the owner's ESP8266 (D1 mini) as a conservative substitute.
- The full evaluation run completes within one working day locally.

**Constraints**:
- ≤ 16 KB RAM and ≤ 128 KB flash on ESP32-S3 (task document).
- Test data is never used for thresholds or selection.
- No dataset content in git or on Hugging Face.
- No cash cost.

**Scale/Scope**:
- can-train-and-test v1: 4 sets, about 193 M frames, 7.5 GB.
- ROAD: 45 captures.
- Detectors: 1 model, 4 controls and about 10 baselines.

## Constitution Check

*GATE: checked before Phase 0, re-checked after Phase 1.*

| Principle | How the plan complies |
|---|---|
| I, II, VII, X (JTBD) | Not applicable (scope note of the constitution). |
| III Measure before optimising | Ground-truth task; the reference is the labels of can-train-and-test and ROAD, frozen as `can-ids-v1` before the first zoo result. Thresholds and alarm points are chosen on validation captures (R3). The deterministic C-versus-Python check is reported on its own (gate rules 12/13). Metric names state the reference; support-weighted metrics are banned (FR-007). |
| IV Riskiest assumption first | Named: transfer to unknown vehicles without identifier memorisation. Success, partial and kill criteria are written before the evaluation (R10). |
| V Small, local, budgets | Budgets from the task document (16 KB RAM, 128 KB flash, ESP32-S3, latency target in R9). Every measurement records its origin; emulator latency is labelled as not representative. |
| VI Clean provenance | Datasets are declared (CC BY 4.0, `training_allowed`, redistribution `unclear`). Examples are synthetic only (R8). The data stays in `$MMZ_DATA`. Attribution goes into the card and notices through the compliance record. |
| VIII Fair comparison | All detectors use the same benchmark version and harness (R5). |
| IX Reproducible, dated releases | The benchmark is frozen and versioned. The model is reproducible from the config and the code commit. The release goes through the existing pipeline. |
| Tasks and releases | The release is `experimental` without real-board latency (gate rule 15). |
| Resources and cost | Local runs only, no hosted API, no cost. |

Result: **PASS**, with no violations. The re-check after Phase 1 is also **PASS**. The design adds no runtime dependency and keeps test data out of selection.

## Project Structure

### Documentation (this feature)

```text
specs/007-picket-forest-release/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/cli.md
├── checklists/requirements.md
└── tasks.md               # /speckit-tasks
```

### Source Code (repository root)

```text
src/mobility_model_zoo/security/can_ids/
├── benchmark.py           # new: freeze, manifest, hash check, roles (R1, R2, R6)
├── evaluate.py            # new: harness, detector registry, report and results writer (R3, R5)
├── detectors.py           # new: controls and baselines behind one interface (R5)
├── synth.py               # new: synthetic frame generator for examples (R8)
├── measure.py             # new: host and QEMU measurements (R9)
├── metrics.py             # changed: time-to-alarm fix, budget operating points, MCC, recall at FPR (R3, R4)
├── forest.py              # changed: export staged file set, examples command; evaluate delegates to evaluate.py
└── cli.py                 # changed (security/cli.py): freeze, evaluate, measure, forest examples

src/mobility_model_zoo/release/
├── gate.py                # changed: engine emlearn branch for rules 12/13, rule 11 size cap (R7)
├── card.py, templates/    # changed: tree-model examples and usage on the mcu card
└── schemas/model.schema.json  # changed: engine field

firmware/picket-forest/platformio/   # new: PlatformIO project for the ESP32 replay benchmark (R9)

topics/security/benchmarks/can-ids-v1/{manifest.json,resolutions.yaml}
topics/security/reports/picket-forest/can-ids-v1/{report.md,metrics.json}
zoo/models/picket-forest/{model.yaml,examples/*.json,releases/0.1.0*.yaml,results/0.1.0/*.json}

tests/security/can_ids/test_benchmark.py, test_evaluate.py, test_detectors.py, test_synth.py, test_metrics_alarm.py
tests/release/test_gate_emlearn.py (+ fixture tree model under tests/release/fixtures/)
```

**Structure Decision**: The work extends the existing `security.can_ids` package and the release tool. The new modules keep `forest.py` from growing further: the benchmark, the harness and the detectors are shared by every future CAN model.

## Complexity Tracking

None. No constitution violations need justifying.
