# Validation: feature 004, scout-large 0.1.0

Model `mobility-model-zoo/scout-large` (renamed from `productdev-jtbd-span-xlmr` on 2026-10-07, constitution 1.4.0, commit 5479d66). Checks run on 2026-10-07 on branch `004-production-span-model`, before publication.

## 1. Checks run for this record

### Budget (SC-007)

| Command | Exit | Result |
|---|---|---|
| `uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml budget` | 0 | budget `span-xlmr-0.1.0`: spent €3.55 of €20 (OpenRouter teacher labels, 4 ledger rows), remaining €16.45; guard cap €13 |
| `uv run jtbd --config configs/productdev/jtbd/pilot-v1.yaml budget` | 0 | budget `pilot-v1`: spent €9.61 of €20 (OpenRouter €8.11, manual €1.50), 21 rows |

The reference machine (Railway service `jtbd-perf`, about 8.8 h) is one ledger row of €1.50, booked on the `pilot-v1` budget; it served both the pilot baselines and the span model perf runs (T042). Counting it fully against this feature gives €3.55 + €1.50 = €5.05, below €20.

### Training data provenance (SC-006, FR-004)

`uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml span data-check`: exit 0. 1,100 chunks from 87 sources, excluded benchmark `configs/productdev/jtbd/pilot-v1.yaml` (active version pilot-v2).

| Violation | Count |
|---|---|
| not `training_allowed` | 0 |
| shared with benchmark or holdout | 0 |
| spike data | 0 |
| redaction not passed | 0 |

Composition: German 28.3% (target 30%, missed), English 71.7%, off-topic 20% (target 15%, met), source types 2 (target 3, missed: no forum source allows training), all five sub-areas present. Misses are reported, not failures (T022); recorded in the T024 note.

### Release bar (FR-015, SC-002, SC-003)

`uv run jtbd --config configs/productdev/jtbd/pilot-v1.yaml span release-check --version 0.1.0`: exit 0, `passed: true`, release bar commit ac253b8 (2026-10-02, before training), `release_bar_changes: []`.

| Condition | Value | Limit | Result |
|---|---|---|---|
| comparison composite above every zero-shot baseline | 0.723 | 0.667 (gemma4:e4b) | pass |
| quotes verbatim rate | 1.0 | 1.0 | pass |
| schema valid rate | 1.0 | 1.0 | pass |
| consistency rate | 1.0 | 1.0 | pass |
| peak RAM (GB) | 2.488 | 4 | pass |
| latency, 9,000-character text (s) | 8.106 | 10 | pass |

### Release gate (FR-016, FR-017)

`set -a; . ./.env; set +a; uv run zoo check scout-large 0.1.0 --offline`: exit 0. Rules 1–4, 6–11, 13, 14 pass; rule 5 (staged files) and rule 12 (usage example) are skipped offline because they need the Hub. The online check passed all 14 rules on 2026-10-07 (T048).

## 2. Traceability (T060)

Status: **met**, **met with deviation** (deviation and where it is recorded), **open (after publication)**.

| ID | Evidence: tasks | Evidence: artifacts and tests | Status |
|---|---|---|---|
| FR-001 | T021, T036, T037 | `data/analysis/decision.json` (pilot-v2); `tests/unit/test_teacher_role.py` (refuses without `decision.json`) | met |
| FR-002 | T014–T018, T030, T036 | `src/mobility_model_zoo/productdev/jtbd/{runs,checks,scoring}.py`; `tests/unit/test_span_runs.py`; `zoo/models/scout-large/results/0.1.0/quality.json` (benchmark pilot-v2, same harness as baselines and teachers) | met |
| FR-003 | T021, T038 | teacher `teacher-or-mimo-v2.6-pro` (pilot recommendation), guideline v2; `tests/unit/test_teacher_role.py` | met |
| FR-004 | T019, T022, T023, T024 | `src/mobility_model_zoo/productdev/jtbd/corpus/separation.py`, `span/datacheck.py`; `tests/unit/test_exclude_benchmark.py`, `tests/unit/span/test_datacheck.py`; data-check above: 0 violations | met |
| FR-005 | T003, T020, T023, T024 | `configs/productdev/jtbd/span-train-v1.yaml`; `tests/unit/test_redaction_sampled.py`; 1,100 chunks from 87 snapshots, 202 chunks changed by `pii-review`, redact-check 1100/1100 | met with deviation: review by a local model instead of manual review (spec FR-005 amended 2026-10-06, `reports/pilot-v2/deviations.yaml`, T024 note); composition targets missed (German 28%, 2 source types; T024 note) |
| FR-005a | T025, T039 | `span/rows.py`; `tests/unit/span/test_rows.py`; `rows.stats.json`: 852 of 11,740 items repaired, 16 dropped, 0 chunks excluded | met |
| FR-005b | T026, T039 | `data/span-train-v1/retention.yaml` (review by 2028-10-07, `published: false`); `data/` in `.gitignore`; `tests/unit/span/test_freeze_data.py` | met |
| FR-006 | T006–T009, T037 | `span/extractor.py`, `span/model.py`, `span/jtbd-span-v1.schema.json`; `tests/unit/span/test_extractor.py`, `test_output_schema.py`; all three attribute dimensions passed the pilot | met |
| FR-007 | T007, T009, T012 | `tests/unit/span/test_extractor.py` (empty text, 20,000-character text over several windows); `SpanExtractor.extract(text)` takes text only, no persona | met |
| FR-008 | T009 | `span/extractor.py` (every unit above threshold is returned, no dedup or clustering); contract `contracts/python-api.md` | met |
| FR-009 | T031, T042, T013 | `performance.json`: peak 2.488 GB on 4 vCPU / 8 GB, CPU only; `tests/integration/test_span_base_install.py` (base install, local model directory, no API) | met with deviation: reference machine is a Railway service limited to 4 vCPU / 8 GB (AMD EPYC 9655P), not a rented VM (`reports/pilot-v2/deviations.yaml`, T042 note) |
| FR-010 | T025, T028 | `span/tune.py` (val rows only, 105 rows from 9 snapshots); `tests/unit/span/test_train.py` | met |
| FR-011 | T002, T029, T035, T048 | `configs/productdev/jtbd/span-xlmr.yaml`, `docs/recipes/scout-large.md`, release record `recipe.git_commit` 4a7091a; gate rule 8 | met with deviation: model rename after training; the record names the recipe document by its path at the training commit (`docs/recipes/productdev-jtbd-span-xlmr.md`), now `docs/recipes/scout-large.md` (`zoo/models/scout-large/releases/0.1.0.yaml`, commit 9264eb7, constitution 1.4.0) |
| FR-012 | T009, T010, T013, T055 | `src/mobility_model_zoo/productdev/jtbd/span/`; `tests/integration/test_span_base_install.py`, `tests/unit/test_no_spike_imports.py` | met |
| FR-013 | T016, T017, T032, T043 | `quality.json` (agreement with 95% CI per dimension, contested items 1,574, check rates); `docs/recipes/figures/scout-large-pareto.{png,json}`; `tests/unit/span/test_results.py`, `tests/unit/test_pareto_student.py` | met |
| FR-014 | T031, T042 | `performance.json` (latency 8.1 s, load 12.2 s separately, 21.6 chunks/min); model hash check in `perf.py`; `tests/unit/test_perf_span.py` | met with deviation: Railway reference machine as in FR-009 |
| FR-015 | T002, T032, T044 | release-check above (exit 0); `tests/unit/span/test_results.py` (a tie with the best baseline fails) | met |
| FR-016 | T047–T051 | gate passes offline (above) and online (T048); tag and publish workflow not yet run | open (after publication): T049–T051 |
| FR-017 | T045, T047, T048 | `zoo/models/scout-large/releases/0.1.0.yaml` (5 files with SHA-256, recipe, budget, sources, teacher, results); `tests/unit/span/test_record.py`; gate rules 5, 7, 8, 9 | met |
| FR-018 | T046, T053 | `zoo/models/scout-large/model.yaml`, `examples/01–03`, `quality.json` (best baseline, teacher, 85% mark); gate rules 9, 10, 13 | met for the staged card; check of the public page open (T053) |
| FR-019 | T050 | — | open (after publication): T050 (history check, repository public) |
| SC-001 | T051 | — | open (after publication): T051 |
| SC-002 | T040, T044 | release-check above: 0.723 vs 0.667, quotes and schema 100% over 1,441 items | met |
| SC-003 | T042 | `performance.json`: 8.1 s (second run 7.5 s), 2.488 GB | met with deviation: Railway reference machine as in FR-009 |
| SC-004 | T054 | `specs/003-model-zoo-hf-release/reader-test.md` | open (after publication): T054 |
| SC-005 | T052 | gate rule 12 ran the usage example online on 2026-10-07 (T048) | open (after publication): T052 clean-machine test |
| SC-006 | T022, T024 | data-check above: 0 violations; `data/span-train-v1/analysis/provenance.json` | met |
| SC-007 | T004, T038, T042 | budget above: €3.55 on `span-xlmr-0.1.0`, €5.05 with the reference machine | met with deviation: the pilot's OpenRouter key was shared instead of a new key, guard cap €13 (owner decision 2026-10-06, T038 note); the reference machine cost is booked on the `pilot-v1` budget (ledger row 2026-10-07) |
| SC-008 | T032, T046, T048 | gate rule 9 (results and traceability) passes; every card number is a metric in `results/0.1.0/` | met for the staged card; public page rechecked in T053 |

Totals: 29 rows (21 FR, 8 SC): 18 met, 6 met with deviation, 5 open (after publication). Every FR and SC maps to at least one task.

## 3. Quickstart scenarios (T059)

| # | Scenario | Run here | Command | Exit | Result |
|---|---|---|---|---|---|
| 1 | Inference package on the base install | yes | `uv run pytest tests/unit/span tests/integration/test_span_end_to_end.py` | 0 | 50 passed |
| 1 | (fresh environment, base dependencies) | yes | `uv run pytest -m slow tests/integration/test_span_base_install.py` | 0 | 1 passed |
| 2 | Harness accepts a span run, cap 3 | yes, as tests | `uv run pytest tests/unit/test_span_runs.py tests/unit/span/test_label_cap.py` (in the batch below) | 0 | passed. The literal commands name `tests/fixtures/span/bench.yaml`, which does not exist; the tests build the fixture benchmark in a temp directory |
| 3 | Training corpus guards | yes, as tests plus the real data-check | `uv run pytest tests/unit/test_exclude_benchmark.py tests/unit/test_redaction_sampled.py tests/unit/span/test_datacheck.py`; `jtbd span data-check` (section 1) | 0 | passed; real corpus built in T023–T024 (`review-sample` replaced by `pii-review`, FR-005 amendment) |
| 4 | Teacher guard and labeling | guard only | `uv run pytest tests/unit/test_teacher_role.py tests/unit/span/test_rows.py tests/unit/span/test_freeze_data.py` | 0 | passed; real labeling is paid, done in T038–T039 |
| 5 | Train, tune, evaluate | guards only | `uv run pytest tests/unit/span/test_train.py tests/unit/span/test_label_cap.py` | 0 | passed; real run on the Spark done in T040 |
| 6 | Speed on the reference machine | tests only | `uv run pytest tests/unit/test_perf_span.py tests/unit/test_pareto_student.py` | 0 | passed, 1 skipped (`/proc` is Linux only); real runs done in T042–T043 |
| 7 | Results and release bar | release-check | `jtbd span release-check --version 0.1.0` (section 1); `uv run pytest tests/unit/span/test_results.py tests/unit/span/test_record.py` | 0 | passed; `span results` not rerun (writes committed files), done in T044 |
| 8 | Release (feature 003 pipeline) | gate offline | `uv run zoo check scout-large 0.1.0 --offline` (section 1); `uv run pytest tests/release` | 0 | 12 pass, 2 skip offline; online 14/14 in T048; 131 release tests passed. `init-model` and `stage` done in T047; `history-check`, tag and publish open (T050, T051) |
| 9 | After publication | budget only | `jtbd budget` (section 1) | 0 | €3.55 ≤ €20; clean machine open (T052), reader test open (T054) |

The guard tests of scenarios 2–7 ran in one batch (16 files): 63 passed, 1 skipped, exit 0. No scenario failed.

## 4. After publication (to be filled)

- T050 repository public: date, history-check result.
- T052 clean-machine test (SC-005).
- T053 public card against FR-018.
- T054 reader test (SC-004).
- T057 recipe reference without login.
