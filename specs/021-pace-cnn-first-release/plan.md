# Implementation Plan: pace-cnn first release (activity recognition on a microcontroller)

**Branch**: `021-pace-cnn-first-release` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/021-pace-cnn-first-release/spec.md`

## Summary

Publish `pace-cnn` 0.1.0, the first model of the `condition-monitoring` topic, as `experimental`. The plan has three parts:

1. **Measured candidate (US1).** Freeze benchmark `uci-har-v1` with a subject-wise validation split. Commit the owner's success and kill criteria before the first run. Train the existing 9-channel recipe with five pre-registered seeds and no selection step. Report int8 results on the bit-exact host reference with per-class, per-subject and seed-spread rows, and derive the status by rule.
2. **Device evidence (US2).** Fix the HIL harness so a trained model runs through it. Measure the model's own flash and RAM from the ELF and its latency on the real ESP32 board, plus informative runs on the ESP32 emulator, the ESP8266 and the host. Ship standalone C sources with the release.
3. **Publication (US3).** Close the gaps the release gate reports today: results files, examples, site and format files, compliance record and SBOM. Create the topic collection before the card is rendered, fix the dataset attribution on the card, then stage, verify and publish with the owner's approval.

Research decisions: [research.md](research.md) (R1–R22).

## Technical Context

**Language/Version**: Python 3.12 (`uv`); C for the int8 engine and generated model sources (ESP32 Arduino core, ESP8266 core, host gcc/clang for the native bench build)

**Primary Dependencies**:

- **Training**: TensorFlow/Keras for training and full-int8 conversion (`edge-train` extra; `uv.lock` resolves TensorFlow 2.21.0, Keras 3.15.1).
- **Arithmetic**: the zoo's own int8 engine (`microinfer`) and its bit-exact Python host reference.
- **Bench**: PlatformIO for the bench firmware, Espressif QEMU for the emulated ESP32.
- **Release**: `huggingface_hub` for staging, publishing and collections.

**Storage**:

- **Outside git**: the dataset and run outputs in `$MMZ_DATA`.
- **In git**: the benchmark manifest, criteria, evaluation report, results JSONs and records.
- **On the Hub**: the release files (private staging, public repo).

**Testing**: pytest (unit, condition_monitoring, edge, release, compliance areas selected by `scripts/ci/select_tests.py`); HIL suite on sim (CI `edge-sim`), ESP32 QEMU (CI `edge-qemu`) and real boards (local run); release gate `zoo check` (18 rules); compliance harness

**Target Platform**:

- **Reference**: ESP32 classic (esp32-1, LilyGO LoRa32, 240 MHz).
- **Informative**: ESP32 QEMU, ESP8266 (esp8266-1), host simulator.
- **Training and evaluation**: the owner's laptop CPU.

**Project Type**: Python package with CLI tools (`condmon`, `edge`, `zoo`) plus microcontroller firmware

**Performance Goals**: Average inference per 2.56 s window ≤ 100 ms on esp32-1. Training of one run in minutes on a laptop CPU.

**Constraints**:

- Model footprint ≤ 128 KB flash and ≤ 32 KB RAM (weights, engine, arena, I/O).
- Bit-exact agreement of host reference, reference interpreter and board.
- No dataset content or subject numbers in public files.
- No Claude output as data, label, judgment or selection signal.
- Cash budget 0 €.

**Scale/Scope**:

- One model, one benchmark, five training runs plus one reproduction.
- About 7 k parameters, 2,947 test windows, 9 test subjects.
- Four measured targets.

## Constitution Check

*GATE: checked before Phase 0 research and again after Phase 1 design.*

Principles I, II, VII and X apply to the JTBD extraction task only and are not touched.

| Principle or section | Gate question | Before design | After design |
|---|---|---|---|
| III Measure Before Optimizing | Ground-truth reference named and frozen before first use; test never used for selection; deterministic checks separate; int8 result reported; metric names honest | Pass: spec FR-003, FR-004, FR-010, FR-011 | Pass. The manifest freezes the splits; `train` and `evaluate` refuse without it (R1). There is no selection step (R3). The interpreter check covers all test windows (R5). Metric rows name the dataset labels as reference |
| IV Riskiest Assumption First | Riskiest assumption named; success and kill criteria recorded before the experiment | Pass: FR-001, FR-007, FR-009 | Pass. The criteria file is enforced by `train` (R2). S5 records the untested transfer and makes 0.1.0 `experimental` |
| V Small and Local, Budgets per Task | Concrete budgets; reference hardware named; origin of every measurement; emulator not presented as hardware | Pass: FR-014, FR-015 | Pass. The model footprint is defined (R7). `edge performance` refuses a non-real-board reference unless a substitute is declared, and keeps origin per row (R9) |
| VI Clean Provenance | Dataset declared; usage class from all inputs; no dataset in git or in the release; personal data minimised; attribution | Pass: FR-005, FR-023, FR-027, FR-028 | Pass. The manifest hashes subject lists instead of listing them (R1). The release has an allow-list (release-files.md). `used_by` is set and the card shows `attribution_text` (R13). Usage class `commercial` is unchanged |
| VIII Fair Architecture Comparison | One task tool, one benchmark for all runs | Pass | Pass. All runs go through `condmon activity` on `uci-har-v1` |
| IX Reproducible, Dated Releases | Reproducible from config; status by rule; publish only through the pipeline after owner approval; immutable | Pass: FR-013, FR-018, FR-024 | Pass. The reproduction command and the recorded versions (R4) back reproducibility. `verdict.json` computes the status (R6). The card is rendered once and approved in preview (R12) |
| XI No Claude in Model Learning | No Claude output as data, label, judgment, selection signal; gate checks it | Pass: FR-006, FR-008 | Pass. Labels are dataset ground truth. Selection is fixed in the criteria file. Claude only writes code and runs pre-registered commands. Gate rule 7 gets a check that confirms no Claude inputs: no teacher, route or recorded run of the release belongs to the Claude family (`model_family` per route); the frozen references that XI keeps are excepted (R21). The evaluation report records the evaluated model file |
| Roadmap and Delivery Pace | Delivery counted at publication | Pass | Pass. The roadmap reads `published_at` (R15); no roadmap edit is needed |
| Resources & Cost Discipline | Local first; cash budget | Pass | Pass. Laptop CPU, 0 € (R20) |
| Tasks and Releases | One task tool; one release gate and pipeline | Pass | Pass. Shared pieces go to `edge/` only where a second model needs them: int8 exporter, performance merge, SBOM (R9, R10) |
| Quality Gates | Before experiment, before reporting, before release | Pass | Pass. Criteria are committed before the run (V2), the report names a frozen benchmark (V4), and the gate and compliance pass before staging (V9, V10) |

No violation, so Complexity Tracking stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/021-pace-cnn-first-release/
├── plan.md              # this file
├── research.md          # R1–R22
├── data-model.md        # entities, fields, transitions
├── quickstart.md        # validation scenarios V1–V13
├── contracts/
│   ├── cli.md           # commands and exit codes
│   ├── records.md       # manifest, criteria, verdict, metric names, footprint, example format
│   └── release-files.md # upload allow-list
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
configs/condition-monitoring/activity/
├── pace-cnn.yaml                    # validation and normalisation wording (subject-wise)
└── pace-cnn-criteria.yaml           # new: pre-registration (R2)

src/mobility_model_zoo/condition_monitoring/
├── cli.py                           # freeze, evaluate, reproduce, export become real
├── benchmark.py                     # new: manifest build, compare, refuse (R1)
└── activity/
    ├── train.py                     # subject files, subject-wise validation, normalisation on training subjects
    ├── evaluate.py                  # new: metrics, report, verdict, quality.json (R5, R6)
    ├── prepare.py                   # new: host reference of the input preparation (R11)
    └── pace-cnn-v1.schema.json      # new: example format

src/mobility_model_zoo/edge/
├── int8/keras_export.py             # op determinism, run report fields, criteria check, seed folders
├── int8/tflite_import.py            # interpreter check over all test windows
├── int8/release_export.py           # new: generic int8 release folder (R10)
├── bench/measure.py                 # --footprint model (R7)
├── bench/performance.py             # new: merge into performance.json (R9)
├── bench/reference_models.py        # eval path fix (R8)
└── cli.py                           # `edge performance`, `measure --footprint`

src/mobility_model_zoo/release/       # publish.py: collection ensure at init-model, make public at publish (R12)
src/mobility_model_zoo/release/gate.py   # rule 7: no Claude inputs (R21); rule 9: benchmark trace of the runs (R22)
compliance/providers.yaml             # model_family per route (R21)
src/mobility_model_zoo/compliance/    # scan-publish exemption for non-text datasets; card attribution text (R13)
src/mobility_model_zoo/release/sbom.py   # new: SBOM generator moved from security/can_ids/release_export.py (R10)

firmware/bench/                       # serial RX buffer 4096 on ESP32/ESP8266 (R8)
hil/targets.yaml                      # esp32 budgets: {pace-cnn: 100000}
tests/edge/hil/                       # catalogue from bench_models() (R8)

topics/condition-monitoring/
├── tasks/activity.md                # benchmark definition, reference hardware, budgets, criteria pointer
├── benchmarks/uci-har-v1/manifest.json   # new (freeze)
├── reports/pace-cnn/0.1.0/          # new (evaluate)
├── compliance/datasets.yaml         # used_by: [pace-cnn@0.1.0]
└── README.md                        # manual row at release

zoo/
├── models/pace-cnn/{model.yaml, site.yaml (new), releases/0.1.0.yaml, releases/0.1.0.compliance.yaml (new), results/0.1.0/{quality,performance}.json (new)}
├── formats/pace-cnn-v1.yaml         # new
└── topics.yaml                      # condition-monitoring hf_collection

tests/condition_monitoring/          # freeze, subject split, criteria refusal, evaluate, verdict, prepare
tests/edge/                          # footprint, performance merge, release export, host compile of c/
tests/release/, tests/compliance/    # collection ensure, exemption, attribution on card
README.md                             # manual row at release
```

**Structure Decision**: Single Python package with the existing topic layout (constitution "Project Scope"): task code in `condition_monitoring/activity/`, topic material in `topics/condition-monitoring/`, configuration in `configs/condition-monitoring/activity/`. Code that `hum-fan` and `picket-mlp` will need as well goes to `edge/`: the int8 release exporter, footprint and performance merge. The SBOM generator goes to `release/sbom.py`, shared by the security exporter and the int8 exporter. The new paths sit inside areas that `scripts/ci/select_tests.py` already maps (`condition_monitoring`, `edge`, `release`, `topics/condition-monitoring`). The security tests that cover the moved SBOM code must stay selected for changes to `release/sbom.py` (checked in the tasks).

## Build order

Each step ends with a measurable result before the next one starts (constitution, iterative delivery).

1. **Benchmark and pre-registration (US1, P1).**
   - Read the subject files and switch validation to whole subjects.
   - Implement `freeze`.
   - Update the task document.
   - Write and commit `pace-cnn-criteria.yaml`.
   - Add the train refusals.
   - Validated by V1 and V2.
2. **Runs and evaluation (US1).**
   - Add op determinism, the extended run report and the interpreter check over all test windows.
   - Train five seeds.
   - Implement `evaluate`, which writes `quality.json` and the report with the verdict.
   - Implement `reproduce`.
   - Validated by V3, V4 and V5. The owner sees the first honest result here.
3. **Input preparation (US1/US3).**
   - Read units and filters from the downloaded README.
   - Write `prepare.py` and run the fidelity check.
   - Write the input contract text.
4. **Device (US2, P2).**
   - Fix the HIL harness and the serial buffer.
   - Add the esp32 budget.
   - Run sim, then QEMU, then esp32-1 (owner connects the board), then esp8266-1.
   - Add `measure --footprint model` and `edge performance`.
   - Validated by V6 and V7.
5. **Release folder (US2/US3).**
   - Write the generic int8 exporter, the shared SBOM module, the examples and their schema.
   - Add the host compile test of `c/`.
   - Update `device_usage`.
   - Validated by V8.
6. **Card, site, compliance (US3, P3).**
   - Update the `model.yaml` card from `verdict.json`.
   - Add `site.yaml` and the format YAML.
   - Implement the `scan-publish` exemption and the attribution text on the card.
   - Add the gate checks for no Claude inputs (rule 7, R21) and the benchmark trace (rule 9, R22), and confirm that published releases still pass.
   - Set `used_by` and write the compliance record.
   - Validated by V9 and V10. The owner signs off.
7. **Publication (US3).**
   - Collection ensure in `init-model`, make public in `publish`.
   - `init-model` (owner's go), stage, full gate, PR and merge, tag, preview review, publish (owner).
   - Edit the README rows by hand.
   - Validated by V11, V12 and V13.

## Risks

| Risk | Effect | Handling |
|---|---|---|
| Quality thresholds missed (sitting/standing) | More unmet criteria on the card | Expected for an experimental release. The card lists values, and grouping keeps rule 18's limit of five items |
| Kill criterion K1 or K2 fires | Quality claims blocked | Report the outcome. Still `experimental` (constitution IX). The owner decides about a new iteration with a new criteria version |
| esp32-1 not answering (AXP power chip) | No real-board evidence | Press PWR as `hil/boards.yaml` notes. Otherwise use the emulator as substitute with `--allow-substitute`, and the card lists the real-board measurement as not done |
| INFER line overflows the serial buffer | Device test fails | Buffer to 4096 (R8), checked on QEMU before the board |
| Training not bit-deterministic | Reproduction differs | Report the deviation (FR-013). The candidate stays seed 0 |
| `scan-publish` exemption weakens checks for text sources | Compliance gap | The exemption applies only to declarations with a non-text class and records the reason. Text classes keep the snapshot requirement (test) |
| Q4 deadline | Roadmap slip | Steps 1–2 give the first result early. A slip is recorded honestly at the pace review |

## Follow-ups outside this feature

- picket-forest: the published cards show an empty attribution table (R13). It needs a patch release with `used_by` and the card fix.
- `mode-cnn`: the MobilitApp dataset (CC0) is a candidate for its declaration check (spec, Assumptions).
- SAMD21 support in the bench firmware (R16), then an informative SAMD21 measurement of pace-cnn.
- A 6-channel variant without a gravity filter as the next pace-cnn candidate (R11).
- CI: after publication, `edge-qemu` can fetch `pace-cnn.npz` from the public repo at its pinned revision, so pace-cnn is regression-tested on every firmware change.
- `release/cli.py` help text still says "all 14 rules" while the gate has 18.

## Complexity Tracking

No constitution violation; nothing to justify.
