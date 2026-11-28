---
description: "Tasks for feature 025: benchmark pilot-v3"
---

# Tasks: Benchmark pilot-v3 for scout guideline v3

**Input**: design documents in `specs/025-pilot-v3-benchmark/`: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md) and [contracts/](contracts/).

**Tests**: Required. SC-002 asks for hand-computed fixtures for every statistic and every branch of the decision rule. Each story writes its tests before its implementation.

**Organization**: by user story from spec.md (US1 and US2 are P1, US3 is P2, US4 is P3).

**Markers**:

- **(owner)** marks a step only the owner may do.
- **(run)** marks a real labeling or fetching run. It needs PRs #64, #63 and #65 merged, and it costs time or money.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [X] T001 Create the subpackage `src/mobility_model_zoo/productdev/jtbd/v3/__init__.py` and an empty Typer group in `src/mobility_model_zoo/productdev/jtbd/v3/cli.py`. Register it as `jtbd v3` in `src/mobility_model_zoo/productdev/jtbd/cli.py`.
- [X] T002 Add the top-level key `v3` to `TOP_LEVEL_KEYS` in `src/mobility_model_zoo/productdev/jtbd/config.py`, with these sub-keys and defaults in `V3_DEFAULTS`:
  - `package` (path)
  - `criteria`
  - `labeler_schemas`
  - `pool` (path)
  - `benchmarks: topics/productdev/benchmarks-v3`
  - `languages: [de, en]`
  - `seed`

  Then add `configs/productdev/jtbd/pilot-v3.yaml` with its own `paths.benchmarks` and data root `data/pilot-v3/` (research R8).
- [X] T003 [P] Add `configs/productdev/jtbd/budget-pilot-v3.yaml` with `budget_eur: 25`. Add the OpenRouter EUR prices per million tokens of `ref-deepseek-v4.1-flash` and of every baseline, read from the OpenRouter model list on the day of the commit, with the date recorded (research R11).
- [X] T004 [P] Add `configs/productdev/jtbd/criteria-pilot-v3.yaml` as a verbatim copy of `pilot_thresholds` from `topics/productdev/guideline/scout-v3/brief.yaml`. Add `bootstrap: {resamples: 2000, seed: 20261128}` and an empty `role_words` placeholder (research R7, R10).
- [X] T005 [P] Create the fixture `tests/fixtures/mini-corpus-v3/`. It needs:
  - 8 chunks, 4 German and 4 English, redaction passed;
  - a pilot-v3 config with `test_fixture: true`;
  - mock answers per pass (`mock/<model>/<chunk>.p<pass>.json`) for `mock-a`, `mock-b` (two families) and `mock-base`;
  - a `README.md` that lists the hand-computed expected figures.

---

## Phase 2: Foundational (blocks every story)

- [ ] T006 Draft the three pass instructions as a new brief key `pass_instructions: {pass1, pass2, pass3, drafted_by: claude, approval: pending}` in `topics/productdev/guideline/scout-v3/brief.yaml` (research R2). The content follows `assembly.passes`. It contains no output examples beyond what the package examples show. Record the draft in `brief-provenance.md`.
- [ ] T007 (owner) The owner approves the content of `pass_instructions` in a pop-up. Record the approval in `brief.yaml` and `brief-provenance.md`.
- [ ] T008 Extend `src/mobility_model_zoo/productdev/jtbd/guideline_package.py` so that `assemble` writes `instructions/pass1.md`, `pass2.md` and `pass3.md` from `pass_instructions` and leaves the key out of `guideline.md`. Add `tests/unit/test_guideline_package.py` cases: the instruction files exist, are hashed in `package.json`, and a change to one gives exit 3.
- [ ] T009 Reassemble `topics/productdev/guideline/scout-v3/package/` with `jtbd guide assemble`. The stale approval is dropped by design.
- [ ] T010 (owner) The owner runs `uv run jtbd guide approve --package topics/productdev/guideline/scout-v3/package --by "<full name>"`. Then `jtbd guide check` exits 0. Commit `approval.json`.
- [ ] T011 [P] Write `tests/unit/v3/test_schema.py`. The wire schema of each pass must equal `specs/025-pilot-v3-benchmark/contracts/labeler-pass{1,2,3}.schema.json`, and no schema node may carry `title` or `description`. Merging the passes must give an object that validates against `src/mobility_model_zoo/productdev/jtbd/span/jtbd-span-v2.schema.json` once `score` is added.
- [ ] T012 Implement `src/mobility_model_zoo/productdev/jtbd/v3/schema.py`:
  - Pydantic models `Pass1Answer`, `Pass2Answer`, `Pass3Answer`, each with `extra="forbid"`;
  - `wire_schema(pass_no)` without descriptions;
  - `labeler_schema_sha256(pass_no)`;
  - `merge(pass1, pass2, pass3) -> LabelerOutputV3`.

  The value lists must equal `brief.yaml` `mode.values` and `improve.values`, and the relations must be `causes|in_order_to|before|during`.
- [ ] T013 [P] Write `tests/unit/v3/test_tokens.py`: Unicode word tokens with offsets for German and English (umlauts, ß, hyphens, digits like 7:12), the token set of a character span, and IoU. Then implement `src/mobility_model_zoo/productdev/jtbd/v3/tokens.py` (research R5).
- [ ] T014 [P] Make the schema name configurable in `src/mobility_model_zoo/productdev/jtbd/labeling/openrouter.py`. The default stays `extraction_output` so v1 behaviour does not change. Add a test in `tests/unit/test_openrouter_schema_name.py`.

**Checkpoint**: the package is approved with pass instructions, and the schemas and tokens are tested.

---

## Phase 3: User Story 1 - Label a chunk with the approved guideline (P1) 🎯 MVP

**Goal**: one reference labels chunks in three passes from the approved package, and every output validates.

**Independent test**: on `mini-corpus-v3` with mock backends, `jtbd label` writes raw and parsed files per pass, and every merged output validates. A changed package gives exit 3, an unapproved one exit 7, and a Claude model exit 7.

- [ ] T015 [P] [US1] Write `tests/unit/v3/test_passes.py`. It must cover:
  - the prompt for each pass is the package `guideline.md`, then the examples, then `instructions/pass<n>.md`, byte for byte;
  - passes 2 and 3 receive the pass-1 items as a JSON list in the user message;
  - a pointer that is not a verbatim part of the chunk is set to null and counted, with no retry (FR-004);
  - pass 3 is skipped when there are fewer than 2 items;
  - raw files are named `raw/<chunk>.p<pass>.a<attempt>.json`, written exclusively and never overwritten;
  - a pass-1 failure excludes the chunk, while a pass-2 or pass-3 failure keeps the earlier passes and records the failed group;
  - a link that breaks a link rule from data-model.md is dropped and counted.
- [ ] T016 [P] [US1] Write `tests/unit/v3/test_label_v3_runner.py`. On `mini-corpus-v3`:
  - order of checks: the Claude gate exits 7 before the package check; a changed package exits 3; an unapproved package with drafts exits 7;
  - `--split holdout` is refused unless the state is `revise`, and `--split full` unless it is `full_labeling`;
  - the manifest records `passes`, `instructions_sha256`, `labeler_schema_sha256` and `package_manifest_sha256`;
  - the estimate counts 2 calls per chunk plus pass 3.
- [ ] T017 [US1] Implement `src/mobility_model_zoo/productdev/jtbd/v3/passes.py` with `label_chunk_v3(settings, backend, entry, chunk, run_path)`. It builds the system prompt per pass from package files only, calls `backend.call` per pass with the pass wire schema, validates the answer, locates quotes with `quotes.locate` and pointers with exact search under the nearest-occurrence rule of brief `executor_role.rule`, and merges, then writes `parsed/<chunk>.json` with `invalid` counts.
- [ ] T018 [US1] Extend `src/mobility_model_zoo/productdev/jtbd/labeling/runner.py`: when `settings.v3` is set, dispatch to `v3.passes.label_chunk_v3`, use a pass-aware `estimate_for`, pass `scope="benchmark:pilot-v3"` to `presend.check_batch` (research R13), and resolve the splits from `samples.json`. The v1 path stays byte-identical, and all existing tests must still pass.
- [ ] T019 [US1] Detect the language per chunk by code in `src/mobility_model_zoo/productdev/jtbd/v3/passes.py` (FR-001). Reuse the chunk's recorded language, and fall back to a simple stopword ratio for German versus English. Test it in `tests/unit/v3/test_passes.py`.
- [ ] T020 [US1] Run `UV_NO_SYNC=1 uv run pytest -q tests/unit tests/unit/v3`; everything must be green, including the v1 runner tests.

**Checkpoint**: US1 is done. A v3 labeling run works end to end with mocks.

---

## Phase 4: User Story 2 - Score the agreement pilot per field and language (P1)

**Goal**: agreement figures, intervals and outcomes per field and language, exactly as in the brief.

**Independent test**: hand-made label sets with known agreement give the expected figures to three decimals and the expected outcomes.

- [ ] T021 [P] [US2] Create `tests/fixtures/v3-agreement/`: two reference label sets per language and a `expected.json` with hand-computed values for:
  - item F1 at token IoU ≥ 0.5 and at any overlap;
  - kappa for kind, actor_type, evidence_scope and states_solution;
  - `states_solution` true-class F1;
  - `job_kind` kappa only on items both call job;
  - linear weighted kappa for evidence_type;
  - MASI alpha for mode and improve, both-empty counting as agreement;
  - per pointer the filled-or-empty kappa and the token F1;
  - link F1 on matched pairs and end to end;
  - the order-relation kappa;
  - relevance kappa and AC1.

  Write the arithmetic in the fixture's `README.md`.
- [ ] T022 [P] [US2] Write `tests/unit/v3/test_agreement.py` against `tests/fixtures/v3-agreement/expected.json` (SC-002), plus a test that bootstrap intervals resample chunks with the recorded seed.
- [ ] T023 [P] [US2] Write `tests/unit/v3/test_decision.py` with one case per branch of the brief's `decision` text:
  - fewer than 30 units gives underpowered, then extend once, then not measured;
  - an estimate below the floor gives not produced;
  - an estimate between floor and threshold gives revise, then a holdout rescore;
  - an estimate at the threshold with the lower bound below the floor gives extend;
  - a field with two numbers needs both;
  - `keep_always_stop` gives pilot stopped for that language only;
  - `per_language` outcomes are independent;
  - `job_kind` collapses to functional against other before it is dropped.
- [ ] T024 [US2] Implement `src/mobility_model_zoo/productdev/jtbd/v3/agreement.py`:
  - one-to-one Hungarian matching on token IoU ≥ 0.5, highest IoU first;
  - kappa and weighted kappa via `metrics.kappa`;
  - in-house Krippendorff's alpha with MASI distance and Gwet's AC1 (research R6);
  - pointer figures;
  - links on matched pairs;
  - `bootstrap_ci` with 2,000 resamples over chunks, per language;
  - output as in data-model.md "Agreement report".
- [ ] T025 [US2] Implement `src/mobility_model_zoo/productdev/jtbd/v3/decision.py` as a pure function `decide(field, figures, criteria, step) -> outcome` and `decide_all(...)`. It reads the thresholds from `configs/productdev/jtbd/criteria-pilot-v3.yaml` and has no hard-coded thresholds.
- [ ] T026 [US2] Implement `src/mobility_model_zoo/productdev/jtbd/v3/report.py`, which renders `report.md` from `agreement.json`. The report has:
  - a table per language with estimate, interval, units and outcome;
  - the figures that are only reported;
  - link prevalence from the random pilot only;
  - invalid-pointer counts;
  - excluded chunks per pass;
  - the cost per run (FR-013).
- [ ] T027 [US2] Add `agree --step`, `decide` and `report` to `src/mobility_model_zoo/productdev/jtbd/v3/cli.py`, following `contracts/cli.md`.

**Checkpoint**: US2 is done. The agreement step reproduces the hand-computed fixture.

---

## Phase 5: User Story 3 - Draw and freeze the pilot-v3 chunks (P2)

**Goal**: a pool of benchmark chunks with no overlap with training data, seeded samples, and a frozen criteria state.

**Independent test**: on fixtures, the draws are reproducible, disjoint and per language; the enriched draw uses connective chunks only; the freeze refuses drift.

- [ ] T028 [P] [US3] Write `tests/unit/test_separation_reverse.py`. A benchmark snapshot that shares a snapshot id, normalised URL, content hash or supersession with a `span-train-v1` snapshot must make `check_benchmark_against_training` fail.
- [ ] T029 [US3] Implement `check_benchmark_against_training(benchmark_pool, training_configs)` in `src/mobility_model_zoo/productdev/jtbd/corpus/separation.py`, plus the command `jtbd v3 separation` (research R9).
- [ ] T030 [P] [US3] Write `tests/unit/v3/test_sample.py`. It must check:
  - the same seed gives the same samples;
  - pilot, holdout, enriched and full are disjoint per language;
  - the enriched sample contains only chunks with a `link_connectives` hit, or with `actor_pair` words plus at least two role words from `criteria.role_words`, and records the connective;
  - `extend-enriched` works once only and grows the sample to 200;
  - link prevalence is computed from the pilot only.
- [ ] T031 [US3] Implement `src/mobility_model_zoo/productdev/jtbd/v3/sample.py` and the commands `sample` and `extend-enriched`.
- [ ] T032 [P] [US3] Write `tests/unit/v3/test_bench.py`:
  - every state transition in data-model.md is allowed, and every other one gives exit 1;
  - `freeze-criteria` refuses a criteria file that differs from the brief's `pilot_thresholds` (apart from `bootstrap` and `role_words`);
  - a changed chunk, package, schema, instruction file, criteria or budget gives exit 3;
  - `revise` works once only and requires a new package approval.
- [ ] T033 [US3] Implement `src/mobility_model_zoo/productdev/jtbd/v3/bench.py` (the manifest state machine, `freeze-criteria`, `revise`) and the commands, following `contracts/benchmark-manifest-v3.md`.
- [ ] T034 [US3] Propose the `role_words` list (German and English role nouns) in `configs/productdev/jtbd/criteria-pilot-v3.yaml`, used only for sampling and never shown to a labeler.
- [ ] T035 (owner) The owner approves the `role_words` approximation in a pop-up (plan owner gate 2).
- [ ] T036 (run) Build the fetch list from the resource index: `zoo catalog query` for German and English mobility sources whose permitted use allows benchmarking and that are not training sources. Target at least 500 usable chunks per language, English first. The owner approves the list before fetching.
- [ ] T037 (run) Fetch each listed source once with `jtbd --config configs/productdev/jtbd/pilot-v3.yaml source fetch --permitted-uses benchmark_only`. Then `corpus autochunk` into `data/pilot-v3/chunks`, `corpus redact`, `corpus pii-review --model teacher-qwen3.8` on the DGX Spark, and `corpus redact-check` (full).
- [ ] T038 (run) Import the pilot-v2 chunk texts into the pool with `source_class: pilot-v2-text`. Texts only: never read `data/runs/*`, consensus or contested files of pilot-v2.
- [ ] T039 (run) Run `jtbd v3 separation` (exit 0), then `jtbd v3 sample --seed 20261128`, then `jtbd v3 freeze-criteria`. Commit `topics/productdev/benchmarks-v3/pilot-v3/{manifest.json,samples.json}`.

**Checkpoint**: US3 is done. The benchmark is in state `criteria_frozen`.

---

## Phase 6: Agreement pilot run (US1 + US2 + US3 together)

- [ ] T040 (run) [US2] Label `--split pilot` with `ref-qwen3.8-27b` (ollama, spark) and with `ref-deepseek-v4.1-flash` (openrouter). Then label `--split enriched` with both. Run `jtbd v3 extend-enriched` once if a link type has fewer than 30 units, and label the extension.
- [ ] T041 (run) [US2] Run `jtbd v3 agree --step pilot`, `jtbd v3 decide` and `jtbd v3 report`. Commit `topics/productdev/benchmarks-v3/pilot-v3/report.md`.
- [ ] T042 (owner) [US2] The owner reads the report. If the decision says `revise`: the owner approves the revised brief, the package is reassembled and approved again, then `jtbd v3 revise --rationale …`, both references label `--split holdout`, and `agree --step holdout` and `decide` run. This round may happen at most once.

---

## Phase 7: User Story 4 - Label the full benchmark and measure the baselines (P3)

**Goal**: a frozen pilot-v3 with consensus per produced field and language, and the baselines scored on it.

**Independent test**: on `mini-corpus-v3` with mocks, the full run, consensus, freeze and baseline scoring work; fields that are not produced appear in `absent_fields`.

- [ ] T043 [P] [US4] Write `tests/unit/v3/test_consensus_v3.py`. It must check:
  - consensus and contested entries are built per produced field and language;
  - fields that are not produced are omitted and listed in `absent_fields`;
  - contested entries are kept;
  - the freeze refuses mock runs unless `test_fixture`.
- [ ] T044 [P] [US4] Write `tests/unit/v3/test_score_v3.py`: baseline scores per field and language with intervals, using only produced fields.
- [ ] T045 [US4] Implement `consensus`, `freeze` and `score` in `src/mobility_model_zoo/productdev/jtbd/v3/bench.py` and `src/mobility_model_zoo/productdev/jtbd/v3/agreement.py`, plus the commands.
- [ ] T046 [US4] Write `tests/integration/test_pilot_v3_chain.py`, the mock chain of quickstart.md section 0: sample, freeze-criteria, label pilot with mocks, agree, decide, label full, consensus, freeze, and score the baseline.
- [ ] T047 (run) [US4] Write down the full benchmark size per language from the pilot's variance (about 2 F1 points separable). Label `--split full` with both references in the languages that passed. Run `jtbd v3 consensus` and `jtbd v3 freeze`.
- [ ] T048 (owner) [US4] The owner picks up to 3 non-Claude zero-shot baselines. The defaults are the earlier pilot baselines that are not Claude, re-checked against the registry.
- [ ] T049 (run) [US4] Label `--split full` with each baseline (`--role baseline`) and run `jtbd v3 score`. Add the baseline table to `report.md`.

**Checkpoint**: US4 is done. pilot-v3 is frozen, and the baselines are scored.

---

## Phase 8: Polish and cross-cutting

- [ ] T050 [P] Update `topics/productdev/research/scout-large-architecture/roadmap.md` (the phase 3 status) and `topics/productdev/research/opportunity-interface/README.md` (the fields that are absent per language after the pilot).
- [ ] T051 [P] Add a "pilot-v3" section to `topics/productdev/recipes/scout-large.md` with the commands of quickstart.md.
- [ ] T052 Run `UV_NO_SYNC=1 uv run pytest -q`, `uv run ruff check`, `uv run zoo compliance check --ci` and `uv run zoo validate --all`; all must be green.
- [ ] T053 Check that no run manifest under `data/pilot-v3/runs/` records a Claude model, and that every one has `package_manifest_sha256` (SC-004). Record the check in `report.md`.

---

## Dependencies and execution order

- **Setup (T001–T005)**: blocks everything.
- **Foundational (T006–T014)**: blocks every story. The owner gates T007 and T010 block US1 runs, but not US1 code with mocks.
- **US1 (T015–T020)** and **US2 (T021–T027)**: can run in parallel after the foundational phase. US2 needs only fixture label sets, not real runs.
- **US3 code (T028–T033)**: can run in parallel with US1 and US2. US3 runs (T036–T039) need PRs #64, #63 and #65 merged, and T035.
- **Pilot run (T040–T042)**: needs US1, US2 and US3 complete.
- **US4 (T043–T049)**: tests and code after US2. Runs only after T041 or T042 and a passed core.
- **Polish (T050–T053)**: last.

## Parallel examples

```text
After Phase 2:
  T015, T016 (US1 tests) | T021, T022, T023 (US2 fixtures and tests) | T028, T030, T032 (US3 tests)
Within US2:
  T024 agreement.py | T025 decision.py | T026 report.py
Within US4:
  T043 | T044
```

## Implementation strategy

1. **MVP**: Setup, Foundational and US1. A real three-pass labeling run on a few chunks with one reference proves the package, schemas and gates.
2. Add US2 (agreement and decision on fixtures), then the US3 code.
3. Owner gates and source runs (T035–T039), then the agreement pilot (T040–T042).
4. US4 only if the core passes in at least one language.

Total: 53 tasks. Setup 5, Foundational 9, US1 6, US2 7, US3 12, pilot run 3, US4 7, Polish 4.
