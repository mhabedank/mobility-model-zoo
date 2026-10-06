---
description: "Tasks for feature 004: production span model, first public release"
---

# Tasks: Production span model, first public release

**Input**: Design documents from `specs/004-production-span-model/`: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. The plan lists the test files, and the guards (source separation, teacher role, candidate cap, release bar) are only trustworthy with tests.

**Organization**: Tasks are grouped by user story. Paths follow the plan: `src/mobility_model_zoo/productdev/jtbd/`, `configs/productdev/jtbd/`, `tests/`, `zoo/models/productdev-jtbd-span-xlmr/`. **(ops)** marks a manual step for the owner (Spark runs, paid runs, reference VM, Hub, GitHub settings). **GATE** marks a point where work stops until a condition holds.

The spike code in `spike/span_model.py`, `spike/train_span.py`, `spike/eval_span.py` and `spike/tune_span_threshold.py` is the reference for porting. Nothing in `src/` may import from `spike/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US4 from spec.md

---

## Phase 1: Setup

**Purpose**: Configs and criteria that must exist, and be committed, before any code or training.

- [X] T001 Commit `specs/004-production-span-model/` on branch `004-production-span-model` (spec, plan, research, data model, contracts, quickstart, tasks) after checking that nothing under `data/` or `.env` is staged.
- [X] T002 Create `configs/productdev/jtbd/span-xlmr.yaml` with the fields from data-model.md "Span model recipe": `model: productdev-jtbd-span-xlmr`; `base_encoder: {name: FacebookAI/xlm-roberta-large, revision: <current main commit of that HF repo>}`; `dataset: span-train-v1`; `benchmark_config: configs/productdev/jtbd/pilot-v1.yaml`; `dimensions: null` (filled in T037 from `decision.json`); `windows: {max_length: 512, stride: 128}`; `training: {lr: 1.5e-5, weight_decay: 0.01, warmup: 0.10, grad_clip: 1.0, batch_size: 4, max_epochs: 8, seed: 20261002, bio_loss_weight: 0.5, relevance_loss_weight: 0.5}`; `thresholds: {unit_grid: [0.2, 0.3, 0.4, 0.5, 0.6]}`; `selection: {benchmark_candidate_cap: 3, rule: "among candidates that meet every release_bar condition, the highest comparison composite; within 0.02, the one with the higher chunks_per_min; if none meets the bar, none is selected"}`; `release_bar: {beat_every_zero_shot_baseline_on: comparison_composite, deterministic_checks: {quotes_verbatim: 1.0, schema_valid: 1.0, consistency: 1.0}, max_peak_ram_gb: 4, max_latency_s_9k: 10}`; `release_bar_changes: []`. Commit it on its own with the message "Record span model release bar before training" (Principle IV; `span train` checks this commit precedes it, T029).
- [X] T003 [P] Create `configs/productdev/jtbd/span-train-v1.yaml` per data-model.md "Training dataset": `dataset: span-train-v1`, `data_dir: data/span-train-v1`, snapshots dir and ledger shared with `pilot-v1.yaml`, `exclude_benchmark: configs/productdev/jtbd/pilot-v1.yaml`, `redaction: {version: redact-v2, review: sampled, sample: {fraction: 0.10, min: 100, always_review_source_types: [forum_review]}}`, `composition_targets: {min_share_per_language: {de: 0.30, en: 0.30}, min_offtopic_share: 0.15, min_source_types: 3, all_sub_areas: true}`, `validation: {fraction_of_snapshots: 0.10, seed: 20261002}`, `min_usable_chunks: 600`, `retention: {rule: "while a model trained on it is current", review_by_months_after_freeze: 24}`. Extend the settings model in `src/mobility_model_zoo/productdev/jtbd/config.py` so these keys load (unknown keys must still fail), with defaults that leave `pilot-v1.yaml` and `spike-v1.yaml` unchanged (`redaction.review: full`).
- [X] T004 [P] Named budget `span-xlmr-0.1.0` on the shared ledger. **Deviation**: instead of a block inside `configs/productdev/jtbd/budget.yaml` (which is part of the pilot's frozen hashes and covered by `tests/unit/test_rename_hashes.py`), the budget lives in its own file `configs/productdev/jtbd/budget-span-xlmr.yaml` (`budget_eur: 20`, `key_cap_eur: 18.4` for the USD 20 key limit, `api_key_env: OPENROUTER_API_KEY_SPAN`, teacher prices), selected by `span-train-v1.yaml` via `paths.budget` and `budget_name: span-xlmr-0.1.0`. `config.py` loads `budget_name` (default `pilot-v1`); `budget.py` writes the name into every ledger row and counts only rows of the active budget (rows without a name count as `pilot-v1`); the OpenRouter backend reads its key from the budget's `api_key_env`. Every `jtbd` command run with `--config configs/productdev/jtbd/span-train-v1.yaml` therefore spends from this budget; no `--budget` option is needed. Test in `tests/unit/test_budget_named.py`.
- [X] T005 [P] Create `configs/productdev/jtbd/perf/interview-9k-de.txt`: a fictional German interview of 9,000 ± 300 characters, cut at a sentence end. Base it on `data/interviews/fiktiv-interview-fussgaenger-berlin.txt` only after confirming it is fictional and contains no real names, e-mail addresses or handles; otherwise write a new fictional text. The file has no header line, because it is measured as is; record its origin in `configs/productdev/jtbd/perf/README.md`.

---

## Phase 2: Foundational (inference package)

**Purpose**: The inference half of the span model (research R10, R11, R18). Training, evaluation and the published usage example all use it. **No story work starts before this phase is complete.**

- [X] T006 Copy `specs/004-production-span-model/contracts/span-output.schema.json` to `src/mobility_model_zoo/productdev/jtbd/span/jtbd-span-v1.schema.json` and include it as package data in `pyproject.toml` if hatchling does not pick it up. Write `tests/unit/span/test_output_schema.py`: the copy equals the contract byte for byte; a valid example validates; `additionalProperties` false at both levels; `output_format_version` must be `jtbd-span-v1`; `kind` only `job`, `pain`, `gain`.
- [X] T007 [P] Implement `src/mobility_model_zoo/productdev/jtbd/span/units.py` (stdlib and `transformers` tokenizer only), ported from `spike/span_model.py:32-54` and `:121-140`: `UNIT_SPLIT = r"(?<=[.!?;])\s+|\n\s*\n"`; `units(text) -> list[tuple[int, int]]` (whitespace trimmed, a single line break is not an end); `windows(tokenizer, text, max_length=512, stride=128)` built by hand (510 content tokens per window, step 382; special and pad tokens get offset `(0, 0)`), returning input ids, attention masks and offset mappings. Tests in `tests/unit/span/test_units.py`: units on German and English samples with abbreviations-free sentences, blank lines and PDF line breaks; windows cover every content token at least once; offsets map back to the text.
- [X] T008 [P] Implement `src/mobility_model_zoo/productdev/jtbd/span/model.py`: `SpanTagger(nn.Module)` with an encoder built from a `transformers` config (`AutoModel.from_config`), heads `heads.bio` (7 labels), `heads.relevance` (1 logit on the first token), `heads.unit` (`O/job/pain/gain`) and `heads.attrs.<dimension>` **only for the dimensions passed in** (label lists from `span_config.json`: `actor_type` 5, `evidence_type` 5, `evidence_scope` 3); dropout 0.1; no `context` variant. Forward returns token logits, relevance logit and token states. Port from `spike/span_model.py:57-104`.
- [X] T009 Implement `src/mobility_model_zoo/productdev/jtbd/span/extractor.py` per contracts/python-api.md: `SpanExtractor.from_pretrained(name_or_path, revision=None, device="cpu", token=None)` (local directory or `huggingface_hub.snapshot_download`; reads `span_config.json`; encoder from `config.json`, no base-model download; one `model.safetensors` with `heads.`-prefixed head tensors; tokenizer from the same directory; `ValueError` on unknown `output_format_version` or head/dimension mismatch; eval mode, no gradients); `extract(text) -> dict` (window merging by averaging token states across windows keyed by character offsets, unit score `1 − P(O)`, kind by argmax over job/pain/gain, keep units with score ≥ `thresholds.unit`, relevant when the best item score ≥ `thresholds.relevance`, else no items; ported from `spike/span_model.py:166-252`); output exactly `jtbd-span-v1` with `dimensions`, items sorted by `start`, `quote == text[start:end]`, no timing field; empty or whitespace-only text returns `relevant: false`, `relevance_probability: 0.0`, `items: []`); `extract_many(texts)`; `save_pretrained(directory)` writing the files in contracts/model-files.md and nothing else (no pickle). Properties `dimensions` and `output_format_version`.
- [X] T010 Create `src/mobility_model_zoo/productdev/jtbd/span/__init__.py` exporting only `SpanExtractor`. The modules `units.py`, `model.py`, `extractor.py` and `__init__.py` import only the standard library, `torch`, `transformers`, `huggingface_hub` and `safetensors`.
- [X] T011 [P] Create `tests/fixtures/span/conftest.py` (or a fixture module imported by `tests/conftest.py`) with a session-scoped fixture `tiny_span_model(dimensions)` that builds, without network access, a tiny model directory: an `XLMRobertaConfig` with hidden size 32, 2 layers, 2 heads, a `PreTrainedTokenizerFast` built with the `tokenizers` library (word-level or BPE trained on a few German and English sentences, with offsets), random weights with a fixed seed, and a `span_config.json` per contracts/model-files.md. Parametrise the produced dimensions (all three; only `actor_type`; none).
- [X] T012 Write `tests/unit/span/test_extractor.py` on the tiny model: output validates against `jtbd-span-v1`; non-produced dimensions are absent from every item and from `dimensions`; `quote == text[start:end]` for every item; same output on two calls; `save_pretrained` then `from_pretrained` round-trips to identical output; the directory contains only the files of contracts/model-files.md; a weights file with an extra attribute head raises `ValueError`; empty text gives an empty, irrelevant result; a 20,000-character text (several windows) works.
- [X] T013 [P] Write `tests/integration/test_span_base_install.py` (marked `slow`): create a fresh `uv venv` on Python 3.12 with `UV_TORCH_BACKEND=cpu`, `uv pip install` the repository root (base dependencies only), and run `python -c "from mobility_model_zoo.productdev.jtbd.span import SpanExtractor"` plus `extract` on the tiny model directory. Fails if any `[jtbd]` dependency is imported.

**Checkpoint**: The model can be built, saved, loaded and run on CPU with the base install.

---

## Phase 3: User Story 1 - A trained span model with honest, comparable results (Priority: P1) 🎯 MVP

**Goal**: A span model trained on regular data from the recommended teacher, scored in the shared harness on the frozen benchmark and measured on the reference VM, with a release-bar verdict.

**Independent Test**: `jtbd score` on the `student` run lists every produced dimension with a confidence interval, the checks and `comparison_composite`; `jtbd perf --backend span` on the reference VM gives latency, load time and peak memory for the same files; `jtbd span release-check` prints a verdict per condition (quickstart scenarios 2, 5, 6, 7).

### Harness: roles, backend, runs, checks, scoring

- [X] T014 [US1] Extend `src/mobility_model_zoo/productdev/jtbd/schema.py`: role `teacher` and role `student`; backend `span`; manifest `settings` may carry `dimensions` (list of attribute dimensions) and `model_sha256` (64 hex characters) for `span` runs. The LLM output schema (`ExtractionOutput`, its JSON schema file and its hash) MUST NOT change; add a test in `tests/unit/test_schema_frozen.py` that the output schema hash equals the value before this task.
- [X] T015 [US1] Extend `src/mobility_model_zoo/productdev/jtbd/runs.py`: for runs with backend `span`, load `parsed/<chunk>.json` as `jtbd-span-v1` and build `LocatedItem`s with `span = (start, end)`, `quote = text[start:end]`, `actor = None`, `statement = None`, and `None` for every attribute not in `settings.dimensions`. Allow `None` for `actor` and `statement` in `LocatedItem` only for `span` runs; every other backend keeps its current validation.
- [X] T016 [US1] Extend `src/mobility_model_zoo/productdev/jtbd/checks.py` (`jtbd check`): for `span` runs, validate every parsed output against `jtbd-span-v1` (schema validity), check `quote == text[start:end]`, `start < end`, items sorted and non-overlapping, item attribute keys exactly equal to `dimensions`, and `relevant == false` implies no items (consistency). Report them under the existing check names.
- [X] T017 [US1] Extend `src/mobility_model_zoo/productdev/jtbd/scoring.py` and `metrics.py`: score only the dimensions a run produces (`relevance`, `item_matching`, `kind` always; attributes from `settings.dimensions`); write `"not_produced"` for the others, never 0 and never silently skipped; add `comparison_composite(score_file, dimensions)` that applies the existing composite function to exactly the given dimension set, and write `comparison_composite` with its `dimensions` into the score file of a `student` run. `score_run` accepts role `student`.
- [X] T018 [US1] Write `tests/unit/test_span_runs.py` with a fixture benchmark (`tests/fixtures/span/bench.yaml` with a tiny frozen consensus, 5 chunks): a hand-written `span` run with only `actor_type` loads, passes `check`, scores with `evidence_type` and `evidence_scope` as `not_produced`; `comparison_composite` over `{relevance, item_matching, kind, actor_type}` equals the manual computation; a run with a wrong quote offset fails the verbatim check; an item with an extra attribute key fails consistency.

### Training corpus (can run before the pilot finishes)

- [X] T019 [P] [US1] Add `--exclude-benchmark <config>` to `jtbd corpus autochunk` in `src/mobility_model_zoo/productdev/jtbd/corpus/autochunk.py` (contracts/cli.md): refuse with exit 1, listing snapshot and rule, any snapshot mapped to `train` that matches a snapshot of a main or holdout chunk of that benchmark by snapshot ID, normalized origin URL (lowercase scheme and host, `www.` removed, trailing slash removed, `utm_*`, `fbclid`, `gclid` query parameters removed) or SHA-256 of the raw snapshot content, including snapshots linked by supersession; also refuse snapshots referenced by any chunk under `data/spike/`. Put URL normalization and the match in `src/mobility_model_zoo/productdev/jtbd/corpus/separation.py` for reuse by T022. Tests in `tests/unit/test_exclude_benchmark.py` (each rule, supersession, spike snapshot, a clean snapshot passes).
- [X] T020 [P] [US1] Add the sampled review policy in `src/mobility_model_zoo/productdev/jtbd/corpus/redact.py` and a command `jtbd corpus review-sample --seed <n>`: draws a stratified sample of `max(min, fraction × chunks)` (strata: language × source type) plus every chunk whose source type is in `always_review_source_types`, records it in `<data_dir>/chunks/review-sample.json`, and refuses to redraw; add an automated identifier scan (e-mail, `@`-handles, phone numbers, URLs with user paths) run on every chunk. `redact-check` with `review: sampled` passes when every chunk passed redaction and the scan and every sampled chunk has `manual_review_at`; with `review: full` it behaves as before. Tests in `tests/unit/test_redaction_sampled.py`.
- [X] T021 [US1] Guard `jtbd label --role teacher` in `src/mobility_model_zoo/productdev/jtbd/labeling/runner.py` (research R5): only `--split train`; refuse with exit 1 if `<benchmark analysis dir>/decision.json` (from `exclude_benchmark`) is missing, if the model is not `teacher_fitness.recommended` (or a member of it when it is the ensemble), if the guideline or schema hash differs from the decision's, or if the model is a benchmark reference. Allow `jtbd ensemble --split train` over complete `teacher` runs, writing a `teacher` ensemble run with the frozen teacher-scoring configuration. Tests in `tests/unit/test_teacher_role.py`.
- [X] T022 [US1] Implement `jtbd span data-check` in `src/mobility_model_zoo/productdev/jtbd/span/datacheck.py`: for every chunk of the dataset, `permitted_uses == training_allowed`, no separation match (T019 module) against the excluded benchmark, no spike snapshot, redaction check passed; write `<data_dir>/analysis/provenance.json` with counts per source (origin, license, permitted use), zero-violation counts and composition against `composition_targets` (language shares, off-topic share, source types, sub-areas), and exit 1 on any violation (composition misses are reported, not failures). Test in `tests/unit/span/test_datacheck.py`.
- [X] T023 *(done 2026-10-06: 1,100 chunks from 87 snapshots, incl. 16 Bundestag plenary protocols of WP 20 added for German text; 5 spike snapshots dropped by the separation check.)* **(ops)** [US1] Build the training corpus (research R3): list stored `training_allowed` snapshots not used by `pilot-v1` main or holdout; write `data/span-train-v1/autochunk-map.yaml` mapping them to `use: train`; run `uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml corpus autochunk --map data/span-train-v1/autochunk-map.yaml --exclude-benchmark configs/productdev/jtbd/pilot-v1.yaml`. If fewer than about 1,000 chunks result, fetch new lawful sources once with `jtbd source fetch/register --permitted-uses training_allowed` (with `retention_until`), add them to the map and rerun. Requires pilot-v1 main and holdout chunks to exist (001 T033–T035); if they do not, wait.
- [X] T024 *(done 2026-10-06: pii-review changed 202 chunks, 895 replacements, none unresolved; redact-check 1100/1100; data-check exit 0, targets missed: German 28% (target 30%), source types 2 (target 3; no forum source allows training).)* **(ops)** [US1] Redact and review (amended 2026-10-06, no manual review): `jtbd corpus redact`, `jtbd corpus pii-review` (local model, every chunk), `jtbd corpus redact-check` until it exits 0, then `jtbd span data-check` until it exits 0. Keep `provenance.json` for the recipe document.

### Span build CLI

- [X] T025 [US1] Implement `src/mobility_model_zoo/productdev/jtbd/span/rows.py` and `jtbd span build-rows --run <teacher run>` (research R7): refuse runs that are not role `teacher` on split `train` or not complete; apply the frozen quote repair from `configs/productdev/jtbd/teacher-scoring.yaml` (reuse `quotes.repair`); locate each item's span by the repaired quote; align to units (a unit takes the item that overlaps it most if the overlap covers ≥ 50% of the unit or ≥ 50% of the item); keep only attributes in `span-xlmr.yaml → dimensions`; exclude chunks without a valid teacher output; assign `split` `val` to 10% of snapshots (seed from the dataset config) and `train` to the rest; write `rows/rows.jsonl` with `{chunk_id, snapshot_id, text, relevant, items[{span, kind, <produced attributes>}], split}` and `rows/rows.stats.json` (chunks in, excluded, items in, repaired, dropped, rows per split, composition). Tests in `tests/unit/span/test_rows.py` (alignment, repair, split by snapshot never shares a snapshot, dimension filtering).
- [X] T026 [P] [US1] Implement `jtbd span freeze-data` in `src/mobility_model_zoo/productdev/jtbd/span/rows.py`: write `<data_dir>/frozen.json` with SHA-256 of every chunk file and of `rows.jsonl` plus a combined hash, and `<data_dir>/retention.yaml` from the config (`frozen_at`, `review_by`); refuse to overwrite a different frozen state. Test in `tests/unit/span/test_freeze_data.py`.
- [X] T027 [US1] Implement `src/mobility_model_zoo/productdev/jtbd/span/train.py` (research R8, R9), ported from `spike/train_span.py` without its spike imports: loss `bio_loss_weight × CE(BIO, ignore -100) + relevance_loss_weight × BCE(relevance) + CE(unit) over units fully inside a window + Σ CE(attribute) over item units` for produced dimensions only; units cut by a window edge skipped in that window; AdamW, linear warm-up, gradient clipping, batch size, epochs and seed from `span-xlmr.yaml`; validation score `(item F1 + mean attribute agreement) / 2` on `val` rows after each epoch; keep the best epoch; save with `SpanExtractor.save_pretrained` and write into `span_config.json` the hyperparameters, best epoch, validation scores, dataset hash from `frozen.json`, base encoder name and revision, and the recipe commit.
- [X] T028 [P] [US1] Implement `src/mobility_model_zoo/productdev/jtbd/span/tune.py` and `jtbd span tune --model-dir <dir>`: choose the unit threshold from `thresholds.unit_grid` by validation score, then the relevance threshold (thresholds ≥ the unit threshold, median of the ties for best validation chunk accuracy), on `val` rows only; write both into `span_config.json` with the tuning table. Ported from `spike/tune_span_threshold.py`.
- [X] T029 [US1] Implement `jtbd span train --recipe <yaml> --out <dir> [--device cuda]` in `src/mobility_model_zoo/productdev/jtbd/span/cli.py` and register the `span` sub-app in `src/mobility_model_zoo/productdev/jtbd/cli.py`. Refuse with exit 1 if `frozen.json` is missing, if `span-xlmr.yaml → dimensions` is null or differs from the passed attribute dimensions in `decision.json`, if `relevance` or `kind` did not pass, if the commit that introduced `release_bar` is not an ancestor of `HEAD`, if `release_bar` at `HEAD` differs from its content in that commit unless `span-xlmr.yaml` contains a `release_bar_changes` entry with date and rationale (Principle IV), if `rows.jsonl` has fewer than `min_usable_chunks` (600) rows in train and val together, or if `src/` or `configs/` have uncommitted changes. Test the refusals and a one-epoch CPU run on the tiny model with 6 fixture rows in `tests/unit/span/test_train.py`.
- [X] T030 [US1] Implement `src/mobility_model_zoo/productdev/jtbd/span/evaluate.py` and `jtbd span label --model-dir <dir> --split main --candidate-change "<text>" [--config]`: run `extract_many` over the split's chunks and write a regular run directory (`manifest.json` with role `student`, backend `span`, model id `productdev-jtbd-span-xlmr`, `settings.dimensions`, `settings.model_sha256`, the git commit, guideline and schema hashes of the benchmark; `parsed/<chunk>.json`); append the candidate to `<span data_dir>/analysis/candidates.json` (`candidate_id`, `model_sha256`, `change`, `run_id`, `scores`, `selected: false`). Refuse any split other than `main` (the holdout stays unused, spec Assumptions), and refuse when the cap from `selection.benchmark_candidate_cap` (3) is reached, when the same `model_sha256` was already evaluated, or on a dirty tree. Tests in `tests/unit/span/test_label_cap.py`.
- [X] T031 [US1] Extend `src/mobility_model_zoo/productdev/jtbd/perf.py` and `jtbd perf` with `--backend span --model-dir <dir> [--text <file>]` (research R13): run in a child process with `torch.set_num_threads(<vcpus>)`; measure `load_time_s`, `latency_9k_chars_s` (median of 5 runs after one warm-up on `--text`, default `configs/productdev/jtbd/perf/interview-9k-de.txt`), `chunks_per_min` over the main split and `peak_rss_mb` (maximum RSS of the child process sampled from `/proc`, cross-checked with `ru_maxrss`); reuse `hardware_info` and `percentile`; write `analysis/perf/<model>.json` with the SHA-256 of `model.safetensors`; refuse if that hash differs from the quality run's `settings.model_sha256`. Test on the tiny model in `tests/unit/test_perf_span.py` (Linux-only parts skipped on macOS).
- [X] T032 [US1] Implement `src/mobility_model_zoo/productdev/jtbd/span/results.py` with `jtbd span results --run <student run> --perf <perf file> --version 0.1.0` and `jtbd span release-check --version 0.1.0` and `jtbd span select` (applies `selection.rule` from `span-xlmr.yaml` to every candidate in `candidates.json` with a score and a perf file, prints the ranking and writes `selected: true` for the result, or for none) (research R14, data-model.md "Results files"): write `zoo/models/productdev-jtbd-span-xlmr/results/0.1.0/quality.json` with metrics `agreement_<dimension>` for every produced dimension, `comparison_composite`, `quotes_verbatim_rate`, `schema_valid_rate`, `consistency_rate`, `contested_items`, `comparison_composite_best_baseline` (description names the baseline), `comparison_composite_teacher`, `comparison_composite_reference`, `comparison_composite_reference_85pct`, each with `reference`, `benchmark`, `n_items`, `date`, and `source_run`; and `performance.json` with `latency_9k_chars_s`, `load_time_s`, `peak_ram_gb`, `chunks_per_min`, each with `hardware`. Both must validate against the feature 003 results schema; no metric name may contain "accuracy". `release-check` prints each `release_bar` condition (comparison composite above every zero-shot baseline's, each deterministic check at the value in `release_bar.deterministic_checks`, `peak_ram_gb ≤ 4`, `latency_9k_chars_s ≤ 10`) with pass or fail, prints every `release_bar_changes` entry, and exits 1 if any condition fails or if `release_bar` changed without such an entry. Tests in `tests/unit/span/test_results.py`, including a model that ties the best baseline (fails), and `select` cases: two passing candidates 0.01 apart (the faster wins), 0.05 apart (the better wins), none passing (none selected).
- [X] T033 [P] [US1] Write `scripts/spark/train_span.sh <candidate>`: on the Spark, run `uv run jtbd span train --recipe configs/productdev/jtbd/span-xlmr.yaml --out data/models/span-xlmr-<candidate> --device cuda` inside `nvcr.io/nvidia/pytorch:25.09-py3` with `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, the repository mounted read-only except `data/`, then `jtbd span tune`; log to `data/models/span-xlmr-<candidate>.train.log` (next to the model directory, so the log is never staged with the model files). Host and user come from `.env` (`SPARK_HOST`), never hard-coded.
- [X] T034 [US1] Write `tests/integration/test_span_end_to_end.py` on the tiny model and the fixture benchmark: rows → train (1 epoch, CPU) → tune → `span label` → `check` → `score` → `perf --backend span` → `results` → `release-check`, each exit code as in contracts/cli.md (quickstart scenarios 1–2).
- [X] T035 [P] [US1] Write the recipe document `docs/recipes/productdev-jtbd-span-xlmr.md`: data (dataset config, separation rule, redaction policy, `data-check`), teacher labeling, rows, training, tuning, evaluation (candidate cap), perf on the reference VM, results, staging; every step as a command; where the hyperparameters live; how to retrain on a new base model (Principle IX). Placeholders for the actual numbers are filled in T048.

### Real runs

- [X] T036 *(2026-10-06: pilot-v2 frozen; decision on the holdout: relevance, kind and all three attributes go, item_matching rethink; recommended teacher teacher-or-mimo-v2.6-pro. benchmark_config and exclude_benchmark stay on pilot-v1.yaml, whose active version is pilot-v2 via benchmarks/current.)* **GATE** [US1] Wait until the pilot (feature 001) has frozen its benchmark and written `data/analysis/decision.json` with the decision, the passed label dimensions and `teacher_fitness.recommended` (001 T059, T073, T081). If the final decision used a rerun, set `benchmark_config` in `span-xlmr.yaml` and `exclude_benchmark` in `span-train-v1.yaml` to that version and rerun T023–T024's `data-check`.
- [X] T037 *(2026-10-06: no stop; dimensions = actor_type, evidence_type, evidence_scope. The gate no longer treats item_matching as a stop criterion, matching the spec edge cases.)* [US1] Stop check: if `relevance` or `kind` did not pass, or no teacher is fit, write `specs/004-production-span-model/outcome.md` with the reason and the pilot numbers, and stop the feature (spec edge cases). Otherwise set `dimensions` in `configs/productdev/jtbd/span-xlmr.yaml` to the passed attribute dimensions and commit.
- [ ] T038 **(ops)** [US1] Teacher labels: ~~if the teacher is hosted, create the OpenRouter key with a hard limit of USD 20 and store it in `.env` as `OPENROUTER_API_KEY_SPAN`~~ *(owner decision 2026-10-06: the pilot key `OPENROUTER_API_KEY` is shared; the span budget's guard cap is EUR 13, what was left on that key)*; run `uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml budget --estimate --model <teacher> --chunks <n>` for each member; run `uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml label --role teacher --model <teacher> --split train` (each ensemble member, then `jtbd ensemble --split train`), with `--retry-failed` after network failures; `jtbd check` each run. At most 2% excluded chunks per run.
- [ ] T039 **(ops)** [US1] `uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml span build-rows --run <teacher run>`, review `rows.stats.json` (repair rate, validation size about 100 chunks); if fewer than 600 usable rows remain, write `specs/004-production-span-model/outcome.md` and stop before training (FR-005); otherwise `uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml span freeze-data` and commit nothing from `data/`.
- [ ] T040 **(ops)** [US1] Candidate c1: `scripts/spark/train_span.sh c1`; copy the model directory back; `uv run jtbd span label --model-dir data/models/span-xlmr-c1 --split main --candidate-change "c1: recipe defaults"`; `uv run jtbd check --run <run>`; `uv run jtbd score --run <run>`. Expected: quotes 100% verbatim, schema 100% valid.
- [ ] T041 **(ops)** [US1] Only if c1 misses the bar or the budget for a reason with a concrete fix decided **before** evaluation (for example the speed fallback of research R13: int8 dynamic quantization, then XLM-RoBERTa-base): train and evaluate c2 (and at most c3) the same way, with the change written into `--candidate-change`.
- [ ] T042 **(ops)** [US1] Reference VM: provision the 8 GB / 4 vCPU / no-GPU VM (the pilot's type), install `uv` and the repository with the base install plus `[jtbd]`, copy every model directory evaluated in T040–T041, verify each SHA-256 against its `student` run, run `uv run jtbd perf --backend span --model-dir <dir> --hardware "<provider type>, 8 GB RAM, 4 vCPU, no GPU"` for each candidate (Principle III: every change is measured on quality and speed), copy `analysis/perf/` back, run `uv run jtbd span select` (the rule fixed in `span-xlmr.yaml` before training) only now, delete the VM, and record its cost with `uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml budget --add "reference VM" --eur <n>`.
- [X] T043 [US1] Extend `src/mobility_model_zoo/productdev/jtbd/report/pareto.py` so that `student` runs with a perf file are plotted next to the pilot baselines on the same benchmark version: comparison composite (y) against chunks per minute on the reference hardware (x), each candidate labelled with its ID and the benchmark version. Write the figure to `docs/recipes/figures/productdev-jtbd-span-xlmr-pareto.png` and the points to `docs/recipes/figures/productdev-jtbd-span-xlmr-pareto.json`. Needs the pilot baselines' perf files from the reference VM (001 T074). Test with fixture score and perf files in `tests/unit/test_pareto_student.py` (constitution gate before reporting a result).
- [ ] T044 [US1] `uv run jtbd span results --run <selected run> --perf <perf file> --version 0.1.0` and `uv run jtbd span release-check --version 0.1.0`. If it exits 1: write `specs/004-production-span-model/outcome.md` with the measured results, label them as an unpublished model, and stop before Phase 4. Commit the results files only if the bar passes.

**Checkpoint**: A measured model and a release-bar verdict exist (MVP). Everything after this point publishes it.

---

## Phase 4: User Story 2 - The model is public on Hugging Face (Priority: P1)

**Goal**: `mobility-model-zoo/productdev-jtbd-span-xlmr` `0.1.0` published through the feature 003 pipeline, with the repository public.

**Independent Test**: On a clean CPU machine, the card's install line and usage example produce the card's output for example 1 (quickstart scenarios 8–9).

- [X] T045 [US2] Add `jtbd span record --version 0.1.0` in `src/mobility_model_zoo/productdev/jtbd/span/results.py`: fill `zoo/models/productdev-jtbd-span-xlmr/releases/0.1.0.yaml` with `provenance.sources` grouped from `provenance.json` (`origin`, `license`, `permitted_use: training_allowed`, `count`), `provenance.teachers` from `decision.json` and `models.yaml` (`model_id`, `license_basis`, `training_on_outputs_permitted: true`), `spike_data: false`, `evaluation.benchmark` and `evaluation.reference` from the benchmark, `performance.budget: {ram_gb: 4, gpu: false}`, `performance.hardware` from the perf file, `recipe.config: configs/productdev/jtbd/span-xlmr.yaml`, `recipe.doc: docs/recipes/productdev-jtbd-span-xlmr.md`, `recipe.git_commit` from `span_config.json`, and today's `date`. Leave `files` and `staging.revision` to `zoo stage`. Test in `tests/unit/span/test_record.py` against the release-record schema.
- [ ] T046 [US2] Update the card texts in `zoo/models/productdev-jtbd-span-xlmr/model.yaml` (FR-018): `summary` with the measured latency on the reference VM; `summary` or `limitations` names the benchmark and guideline version and states that the GPT-family reference is the mini tier for budget reasons (pilot FR-017); `input_output` describing `jtbd-span-v1` including the `dimensions` field; `limitations` naming every attribute dimension left out and the pilot reason, the missing free-text actor and English statement, the number of evaluated candidates if more than one, and "agreement with frontier models, not human judgement"; keep the existing intended use, out-of-scope use and citation. Every number in these texts must also be a metric in the results files (gate rule 9).
- [ ] T047 **(ops)** [US2] `uv run zoo init-model productdev-jtbd-span-xlmr` (creates the private staging repo); add `mobility-model-zoo/productdev-jtbd-span-xlmr-staging` to `HF_STAGING_TOKEN`'s repo list; on the Spark run `uv run jtbd span record --version 0.1.0` then `uv run zoo stage productdev-jtbd-span-xlmr 0.1.0 --from data/models/span-xlmr-<selected>`. Verify that the staged `model.safetensors` SHA-256 equals the perf file's.
- [ ] T048 [US2] Fill the numbers in `docs/recipes/productdev-jtbd-span-xlmr.md` (dataset size, repair rate, candidates, selected epoch, thresholds), commit the record, card texts, results and recipe document, and run `uv run zoo check productdev-jtbd-span-xlmr 0.1.0 --offline` and then online. All 14 rules must pass. A failure caused by the zoo tooling (not by the record) is fixed in `src/mobility_model_zoo/release/` with a test in `tests/release/`, never worked around in the record.
- [ ] T049 **(ops)** [US2] Open a pull request from `004-production-span-model` to `main` and merge it after CI is green (the release workflows run from `main`).
- [ ] T050 **(ops)** [US2] Make the repository public (FR-019, also US4 scenario 1): on `main`, run `uv run zoo history-check` (exit 0 required; on findings, rewrite history before continuing), then `gh repo edit mhabedank/mobility-model-zoo --visibility public --accept-visibility-change-consequences`. Record date and result in `specs/004-production-span-model/validation.md`.
- [ ] T051 **(ops)** [US2] On `main`, tag `productdev-jtbd-span-xlmr/v0.1.0` on the commit holding the release record and push the tag. Check the verify workflow's gate table and the preview card; then start `release-publish.yml` with `model`, `version`, `confirm`. Confirm the public model page, the tag `0.1.0` on the Hub, and the updated `zoo/MODELS.md` (SC-001).
- [ ] T052 **(ops)** [US2] Clean-machine test (SC-005): on a CPU machine (or VM) with Python 3.12 and no project checkout, run the card's install line and usage example on example 1; compare with the card's output (same items: kind, start, end and attributes; scores within 1e-4); record the result in `specs/004-production-span-model/validation.md`.

**Checkpoint**: The first model of the zoo is public.

---

## Phase 5: User Story 3 - A visitor understands the model's strengths and limits (Priority: P2)

**Goal**: The public page passes the reader test and shows every comparison FR-018 requires.

**Independent Test**: Reader test with `specs/003-model-zoo-hf-release/reader-test.md`: at least 6 of 7 correct.

- [ ] T053 [US3] Check the public card against FR-018 and record the result in `specs/004-production-span-model/validation.md`: benchmark and guideline version, reference models, comparison composite next to the best baseline, the teacher and the 85%-of-reference mark, omitted dimensions with reasons, what the generative approach adds, speed and memory with the hardware, three examples with real output.
- [ ] T054 **(ops)** [US3] Run the reader test with a person who did not work on the project; record date, role (no name), card version, answers, score and unclear points in `specs/004-production-span-model/validation.md` (SC-004). Unclear points become card changes for a `0.1.1` patch release, listed there.

---

## Phase 6: User Story 4 - The repository is public and the spike code is retired (Priority: P3)

**Goal**: Production code and docs no longer depend on the spike; the public recipe reference works.

**Independent Test**: Without access rights, follow the card's recipe reference to the commit, config and recipe document, and install with the card's install line.

- [X] T055 [P] [US4] Write `tests/unit/test_no_spike_imports.py`: fails if any file under `src/` imports from `spike` or adds `spike/` to `sys.path`, or if any config under `configs/productdev/jtbd/span-*.yaml` references `data/spike`.
- [ ] T056 [P] [US4] Update `README.md`: the "Fast span model" section states that the spike model is history and points to the published model, its card and `SpanExtractor` usage; the model overview row for `productdev-jtbd-span-xlmr` matches `zoo/MODELS.md`; the commands for the span model use `jtbd span …` and `scripts/spark/train_span.sh`.
- [ ] T057 **(ops)** [US4] From a browser without a GitHub login: open the repository, follow the card's recipe reference to the recipe commit, `configs/productdev/jtbd/span-xlmr.yaml` and `docs/recipes/productdev-jtbd-span-xlmr.md`; record the result in `specs/004-production-span-model/validation.md`.

---

## Phase 7: Polish & cross-cutting concerns

- [ ] T058 [P] Run `uv run ruff check` and `uv run pytest` (including `slow`); all green.
- [ ] T059 [P] Run every quickstart scenario in `specs/004-production-span-model/quickstart.md` that has not been run as part of a task, and record the results in `specs/004-production-span-model/validation.md`.
- [ ] T060 Traceability check: every FR and SC in spec.md maps to at least one task, artifact or test; write the table to `specs/004-production-span-model/validation.md`. Include the budget total from `uv run jtbd --config configs/productdev/jtbd/span-train-v1.yaml budget` (SC-007, ≤ €20) and the zero-violation counts from `provenance.json` (SC-006).
- [ ] T061 [P] Update `.specify/memory/constitution.md`: remove the resolved follow-up TODO "Feature 004 (production span model) must use the release record and gate from feature 003" from the Sync Impact Report (PATCH 1.3.1, rationale recorded), and `specs/003-model-zoo-hf-release/handover-004.md` with a closing line pointing to the published version.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: none. T002 must be committed before any training run (checked by T029).
- **Foundational (Phase 2)**: after Setup; blocks all stories.
- **US1 (Phase 3)**: after Phase 2. Code tasks T014–T035 can start now. T023–T024 need the pilot's main and holdout chunks. T036 is a hard gate on the pilot; T037–T044 follow it in order.
- **US2 (Phase 4)**: after T044 passes. T045–T048 before T049; T050 (repository public) before T051 (tag and approval).
- **US3 (Phase 5)**: after T051 (needs the public page). Card texts were written in T046, so US3 only verifies and tests.
- **US4 (Phase 6)**: T055–T056 can run any time after Phase 2; T057 after T050.
- **Polish (Phase 7)**: after all stories.

### Cross-story notes

- US2 contains the step that makes the repository public (T050), which also satisfies US4 scenario 1, because publication must not happen before it (FR-019).
- US3's content (T046) is written inside US2, because the card is built at tagging time; US3 verifies it on the public page.

### Within US1

- T014 → T015 → T016, T017 → T018
- T019, T020 in parallel → T021 → T022 → T023 → T024
- T025 → T026; T027 → T028 → T029; T030, T031 after T015–T017; T032 after T030–T031; T034 after T032
- T036 → T037 → T038 → T039 → T040 → (T041) → T042 → T043 → T044; T043 also needs 001 T074

### Parallel opportunities

- Phase 1: T003, T004, T005 together after T002.
- Phase 2: T007, T008, T011, T013 together; T009 after T007–T008.
- US1 code: T019, T020, T026, T028, T033, T035 in parallel with the harness tasks T014–T018 (different files).
- US4: T055, T056 any time after Phase 2.

## Parallel Example: User Story 1

```text
# Harness and corpus tooling at the same time:
Task: "T014 Extend schema.py with roles teacher, student and backend span"
Task: "T019 Add --exclude-benchmark to corpus autochunk (separation.py)"
Task: "T020 Sampled review policy and review-sample command in corpus/redact.py"
Task: "T033 Write scripts/spark/train_span.sh"
Task: "T035 Write docs/recipes/productdev-jtbd-span-xlmr.md"
```

## Implementation Strategy

### MVP (User Story 1)

1. Phases 1–2: configs, release bar committed, inference package with tests.
2. US1 code (T014–T035) and the corpus (T023–T024) while the pilot finishes.
3. After the pilot gate (T036): labels, training, evaluation, reference VM, Pareto front, release check (T037–T044).
4. **Stop and review**: the release-check verdict decides whether US2 starts.

### Incremental delivery

1. US1 → measured model and verdict.
2. US2 → public model (the overall goal of features 003 and 004).
3. US3 → reader test, possible `0.1.1` card patch.
4. US4 → spike retired in docs, public recipe verified.
