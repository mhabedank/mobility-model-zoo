# Implementation Plan: Quickstart that works from a fresh install

**Branch**: `013-fresh-install-quickstart` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/013-fresh-install-quickstart/spec.md`

## Summary

Every published model card must be followable from a fresh Python 3.12 environment: install line,
pasted snippet, printed result. Today picket-forest's card cannot be followed at all (missing
libraries in its extra, a Python reference that compiles C from the repository checkout, undefined
inputs, no example data in the model repository) and nothing in the gate notices, because the
fresh-environment runner installs without the card's extras and never runs the snippet of a
microcontroller model. scout-large works but drags 877 MB of text stack into every install and
nobody states the Python requirement.

Approach: (1) split the dependencies into a small base and one extra per model kind (`text`,
`edge`), each card's install line naming its extra; (2) a user-facing module
`security.can_ids.picket_forest` that reimplements the calibrated features, rules, alarm stage and
forest vote in numpy, bit-exact against the C chain, so no compiler is needed; (3) example captures
and the calibration table published in the model repository as JSON and a complete `how_to_run`
that downloads, scores and prints; (4) the gate's `VenvRunner` installs with the card's extras and
runs `how_to_run` for microcontroller models too, recording the output on the card; (5) a
"Try it in five minutes" quickstart (`docs/quickstart.md`, rendered on the website, linked from the
README) and the Python requirement next to every install line (already in the working tree);
(6) patch releases picket-forest 0.2.1 and scout-large 0.1.3 through the pipeline, 0.2.0
deprecated.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python >=3.12`, unchanged; stated on cards and website)

**Primary Dependencies**: base `huggingface_hub`, `numpy`; extra `text` = torch, transformers,
safetensors, sentencepiece (today's base); extra `edge` gains `scikit-learn`, `joblib` (the
published forest is a scikit-learn object in `model.joblib`); `jtbd` includes `text`. The
user-facing picket-forest module imports only numpy, joblib, scikit-learn and the standard
library; no pandas, no ctypes, no `edge.paths`.

**Storage**: Hugging Face model repository (files `examples/*.json`, `calibration_table.json` added
to picket-forest); registry YAML (`zoo/models/<name>/model.yaml`, release records); no database.

**Testing**: pytest. Compiler-free tests: numpy reference reproduces `expected_scores` and
`expected_alarms` of the three example captures bit-exactly; import-hygiene test of the user-facing
module; gate tests with `FakeRunner`; install-line parsing of `VenvRunner`. Compiler tests (in the
firmware CI job, as today): numpy reference against the C chain on the parity captures.
Integration test (network, slow marker): real `VenvRunner` with `[edge]` on the local checkout runs
picket-forest's `how_to_run` against the staging repository.

**Target Platform**: user machines on macOS and Linux with Python 3.12 (Windows: not tested, no
compiler needed any more so nothing excludes it); gate on GitHub runners (ubuntu) and the owner's
Mac.

**Project Type**: library + CLI (`zoo`, `security`) + static website generator; single package.

**Performance Goals**: picket-forest install under 300 MB installed (lean set measured at 144 MB
installed on 2026-10-11, numpy + scipy + scikit-learn + joblib + huggingface_hub); the example
snippet (3,000 frames) prints within 2 s after download; the numpy reference processes a 1 M-frame
parity capture within the test budget (vectorised per ID; only the alarm stage iterates, over
flagged frames).

**Constraints**: bit-exact parity with the C chain (float32 features, log2 quantised to 1/256,
integer microseconds); published versions immutable (patch = new version); no dataset content in
the model repository (examples are synthetic); the gate stays one gate for every model; CI jobs that
sync `--extra edge` or `--extra jtbd` keep working.

**Scale/Scope**: 2 models to re-release, 6 model.yaml files to touch (install lines), ~10 source
files, 1 new module (~350 lines), 1 new doc page, 1 website template, gate rule 12 extended.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / section | Touched | How the plan complies |
|---|---|---|
| III Measure Before Optimizing | yes | The numpy reference is a third implementation of the device chain; its agreement with the C chain is a deterministic check: bit-exact on the parity captures (compiler job) and on the example captures (every CI run, no compiler). Reported in the gate output, not inferred. |
| V Small and Local by Default | yes | Install of an edge model drops from 877 MB to under 300 MB; nothing hosted enters the run path. Budgets of the models are untouched (no model change). |
| VI Clean Provenance | yes | Only the three synthetic example captures (SOURCES.yaml: `synthetic`) are added to the model repository; `forbidden_upload` still blocks `data/`, `.jsonl`, `.eval.npz`. |
| IX Reproducible, Dated Releases | yes | 0.2.0 and 0.1.2 stay as published; fixes are 0.2.1 and 0.1.3 with `change_type: patch`; 0.2.0 is deprecated with a successor (card-only commit); both go through gate, preview and owner approval. Weights and device headers are byte-identical (the gate's sha256 list proves it). |
| Tasks and Releases: one gate | yes | No model-specific gate: rule 12 runs `how_to_run` for every runtime; `VenvRunner` derives the extras from the card's install line for every model. |
| Development Workflow: gate before a release | yes | The fresh-environment run becomes part of the gate; a failing snippet blocks `zoo build`. |
| X Scope Discipline, FR-015 | yes | No model, threshold, feature or device code changes; the C sources are untouched. |

No violation; Complexity Tracking stays empty.

**Post-design re-check (after Phase 1)**: unchanged. The design adds one optional card field
(`card.own_data`) and one JSON file format; neither changes a model or a release's results.

## Project Structure

### Documentation (this feature)

```text
specs/013-fresh-install-quickstart/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R10
├── data-model.md        # Phase 1: entities and file formats
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   ├── dependency-layout.md     # extras, install lines, CI syncs
│   ├── picket-forest-api.md     # the user-facing Python module
│   ├── model-repo-files.md      # examples/*.json and calibration_table.json
│   └── gate-and-card.md         # VenvRunner, rule 12, card template, model.schema
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
pyproject.toml                                   # base/text/edge/jtbd extras (R1)
src/mobility_model_zoo/
├── security/can_ids/
│   ├── picket_forest.py                         # NEW: numpy reference, loaders, score(), summary()
│   ├── calibrated.py                            # Table/calibrate/rules move to picket_forest; re-exports; C path stays as parity oracle
│   ├── forest.py                                # vote_score moves to picket_forest; re-export
│   ├── release_export_v2.py                     # export() also writes examples/ and calibration_table.json; parity() adds numpy vs C
│   └── frames.py                                # read_candump delegates to picket_forest.read_candump (numpy only)
├── security/cli.py                              # `v2 table` writes the JSON table next to the header
├── release/
│   ├── usage.py                                 # VenvRunner: extras from the install line
│   ├── gate.py                                  # rule 12: mcu runs how_to_run; tree-file rule checks examples/ and table JSON
│   ├── card.py                                  # how_to_run_output, own_data into the template
│   ├── templates/model_card.md.j2               # "Output:" after the snippet (mcu); "Use it on your own data"
│   └── schemas/model.schema.json                # card.own_data (optional)
├── site/
│   ├── build.py                                 # /quickstart/ page from docs/quickstart.md; own_data in quickstart partial
│   ├── templates/quickstart.html.j2             # NEW page template
│   └── templates/partials/quickstart.html.j2    # output + own-data steps for mcu
docs/quickstart.md                               # NEW: "Try it in five minutes" (single source)
README.md                                        # short "Try it" section linking docs/quickstart.md
zoo/models/*/model.yaml                          # install lines with extras; picket-forest how_to_run + own_data
zoo/models/picket-forest/releases/0.2.1.yaml     # created by `zoo stage`
zoo/models/scout-large/releases/0.1.3.yaml       # copied record, same files and staging revision
specs/005-topic-layout-security-merge/contracts/release-format.md  # rule 12 wording, new files
docs/adding-a-model.md                           # install line names the extra; how_to_run must run as pasted

tests/
├── security/can_ids/
│   ├── test_picket_forest_reference.py          # NEW: examples bit-exact (no compiler); import hygiene; loaders; candump
│   └── test_release_export_v2.py                # numpy vs C parity on parity captures (compiler job)
├── release/
│   ├── test_usage_runner.py                     # NEW: install-line parsing; integration run (network marker)
│   ├── test_gate_rules.py / test_edge_rules.py  # rule 12 for mcu; the five replayed failures
│   └── fixtures/golden/*.README.md              # regenerated
└── website/                                     # quickstart page; partial with output and own-data steps
```

**Structure Decision**: single package as today; the one new module sits next to the code it
replaces for users (`security/can_ids/`). The quickstart doc lives in `docs/` (repository-wide
material, as the constitution's layout rule requires for cross-topic content) and is rendered by
the site, not duplicated by hand.

## Complexity Tracking

No constitution violations to justify.

## Phase 0 and Phase 1 outputs

- [research.md](research.md): R1 dependency layout, R2 numpy port and float parity, R3 files in
  the model repository and patch releases without retraining, R4 `VenvRunner` extras, R5 running
  `how_to_run` for mcu models and showing its output, R6 quickstart placement, R7 candump without
  pandas, R8 deprecation, R9 environment tool and pitfalls, R10 the five replayed failures.
- [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md).
