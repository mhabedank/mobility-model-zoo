---
description: "Tasks for feature 009: deduplication and clustering of JTBD items"
---

# Tasks: Deduplication and clustering of JTBD items

**Input**: Design documents from `specs/009-jtbd-dedup-cluster/`: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. The plan lists the test modules, and the guarantees of this feature (quotes unchanged, kind separation, stable ids, corrections, tuning only on development data) are only trustworthy with tests.

**Test file names**: every test module under `tests/unit/cluster/` starts with `test_cluster_` (the tests have no packages, so basenames must be unique across `tests/unit/`); shared helpers are in `tests/unit/cluster/cluster_helpers.py`.

**Organization**: Tasks are grouped by user story. Paths follow the plan: package `src/mobility_model_zoo/productdev/jtbd/cluster/`, configs `configs/productdev/jtbd/`, topic material `topics/productdev/`, tests `tests/unit/cluster/`, `tests/integration/`, `tests/fixtures/cluster/`. **(ops)** marks a manual step for the owner (paid or hosted runs, reference VM). **GATE** marks a point where work stops until a condition holds.

Runtime modules (`bundle`, `embed`, `dedup`, `specificity`, `hierarchy`, `continuity`, `corrections`, `annotations`, `stage`, `checks`, `report`) import only the standard library, the base install (`torch`, `transformers`, `huggingface_hub`, `safetensors`) and the `cluster` extra (`numpy`, `scipy`, `scikit-learn`, `pyyaml`, `jsonschema`). Measurement modules (`bench`, `prompt`, `label`, `metrics`, `decide`, `tune`, `perf`) may use the `jtbd` extra and reuse `labeling/base.py`, `budget.py`, `freeze.py`, `metrics.py` and `compliance/presend.py` by import. No test downloads a model: tests use the stub encoder and stub NLI of T011.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US5 from spec.md

---

## Phase 1: Setup

**Purpose**: Task document, guideline, criteria and configs that must exist, and be committed, before code that depends on them and before any labeling (constitution IV).

- [X] T001 Commit `specs/009-jtbd-dedup-cluster/` (spec, checklist, plan, research, data model, contracts, quickstart, tasks) on branch `009-jtbd-dedup-cluster` after checking that nothing under `data/` or `.env` is staged.
- [X] T002 [P] Write `topics/productdev/tasks/jtbd-cluster.md` in the structure of `topics/security/tasks/can-ids.md`: Scope (in: deduplication, specificity relation, clusters across kinds, continuity, slots; out: prioritisation, opportunity scoring, importance/satisfaction values, generated statements or labels, personas, ontology, changes to scout), Reference (consensus of `claude-reference` and `gpt-mini-reference` on benchmark `cluster-v1`; metrics named as agreement), Benchmark `cluster-v1` (research R10), Metrics table (pair precision/recall/F1 and B-cubed precision/recall/F1 for duplicates; precision/recall/F1 of "more specific than"; B-cubed F1 for clusters; kappa for reference agreement), Tool (`uv run jtbd cluster …`), Riskiest assumption (references agree on "same need" and "belongs together"), Hardware budget (50,000 items ≤ 15 min, ≤ 4 GB RAM, 4 vCPU, no GPU, offline), Status. Add the task row to `topics/productdev/README.md`.
- [X] T003 [P] Write the guideline `topics/productdev/guideline/cluster-v1/guideline-cluster-v1.md`: definitions of *same* (one duplicate group), *more specific than* (one states a narrower version of the other's need, same kind) and *different*; the rule that only the quote is judged, never text outside it; that duplicates and specificity never cross kinds; that clusters may combine a job with its pains and gains; how to treat short or generic quotes; a decision procedure for borderline cases ("when unsure between same and more specific, choose more specific; between more specific and different, choose different"). Add `topics/productdev/guideline/cluster-v1/examples.yaml` (YAML, not Markdown: German examples are prompt data, and Markdown under `topics/` must be English) with at least 12 German and 12 English pair examples (4 per label and language) and 2 set examples with their partitions. All examples fictional; no names, handles or e-mail addresses.
- [X] T004 [P] Create `configs/productdev/jtbd/cluster-criteria.yaml` per research R12: `duplicate_kappa_min: 0.60`, `specificity_kappa_min: 0.40`, `cluster_bcubed_f1_min: 0.60`, `revise: {max_reruns: 1, holdout_pairs: 300, holdout_sets: 4}`, `rethink: {duplicate: stop_task, specificity: not_produced, clusters: not_produced, cluster_level_2: not_produced}`, `baseline_bar: {ratio_to_reference: 0.85, levels: [duplicate, specificity, clusters]}`, `contested: neutral`, `bootstrap: {resamples: 2000, seed: 20261009}`, `criteria_changes: []`. Commit it on its own with the message "Record cluster agreement criteria before labeling".
- [X] T005 [P] Create `configs/productdev/jtbd/cluster-v1.yaml` (benchmark config): `benchmark_version: cluster-v1`; `pool: {span_run: <run id of the released scout-large on the stored chunks>, splits: [main], datasets: [span-train-v1], exclude_splits: [holdout]}`; `split_by: snapshot`, `dev_fraction: 0.30`, `seed: 20261009`; `pairs: {test: 1200, dev: 400, holdout: 300, strata: {high: 0.34, middle: 0.33, random: 0.33}, same_kind_only: true, samplers: [{name: labse, model_id: sentence-transformers/LaBSE, revision: <pinned>}, {name: lexical, method: token_set_ratio}]}`; `sets: {test: 12, dev: 4, holdout: 4, size: 40, neighbourhood_k: 39, coarse_partition: optional}`; `reference_models: [claude-reference, gpt-mini-reference]`; `batch_size: 20`; `guideline: topics/productdev/guideline/cluster-v1/`; `criteria: configs/productdev/jtbd/cluster-criteria.yaml`; `paths.budget: configs/productdev/jtbd/budget-cluster.yaml`; `budget_name: cluster-v1`; data under `data/cluster/`. Extend the settings loader in `src/mobility_model_zoo/productdev/jtbd/config.py` so a `cluster` top-level key loads (unknown keys must still fail) without changing how `pilot-v1.yaml`, `span-train-v1.yaml` and `spike-v1.yaml` load.
- [X] T006 [P] Create `configs/productdev/jtbd/budget-cluster.yaml` as its own budget file (not a block in the frozen `budget.yaml`, as in feature 004 T004): `budget_eur: 20`, `key_cap_eur: 18.4`, `api_key_env: OPENROUTER_API_KEY_CLUSTER`, prices for the two reference routes, reference VM hourly price.
- [X] T007 [P] Create `configs/productdev/jtbd/cluster-baseline.yaml` (stage settings): `encoder: {model_id: intfloat/multilingual-e5-base, revision: <pinned>, prefix: "query: ", pooling: mean, normalize: true, batch_size: 64, max_length: 128, licence_basis: MIT}`; `nli: {model_id: MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7, revision: <pinned>, licence_basis: <recorded in T008>}`; `neighbours: {k: 30, candidate_floor: 0.50}`; `thresholds: {t_dup: 0.88, t_spec: 0.75, t_nli: 0.80}` (starting values, replaced by tuning in T044); `levels: [0.70, 0.55]`; `representative: medoid`; `settings_changes: []`. Add `cluster-e5-small.yaml` and `cluster-gte-base.yaml` with the same fields for the two other candidates (research R5).
- [ ] T008 **(ops)** Record the licence basis of every third-party model used (multilingual-e5-small, multilingual-e5-base, gte-multilingual-base, LaBSE, the mDeBERTa NLI model including the licences of its training data) in the settings files of T005 and T007 and in `topics/productdev/compliance/` if the register requires model records; a model whose licence does not permit commercial use is removed from the candidate list. Also pin `revision` to a commit in every settings file; until both are set, `HFEncoder` refuses to load the model (UsageError). **Status 2026-10-09**: licence bases recorded from the model cards for multilingual-e5-small/-base (MIT), gte-multilingual-base and LaBSE (Apache-2.0); revisions are pinned locally with `topics/productdev/scripts/cluster/pin_revisions.py --write` (Hugging Face was blocked in the cloud build environment); the NLI model stays without licence basis because its training data includes ANLI subsets (owner decision, see `handover-local.md`). **Status 2026-10-10**: all revisions pinned locally; none of the encoder repositories has a LICENSE file, so the basis is the model card licence tag. gte-multilingual-base loads its architecture code from `Alibaba-NLP/new-impl` (Apache-2.0, reviewed: model code only); `code_revision` pins that code and `HFEncoder` refuses remote code without it; gte uses CLS pooling as on its model card. Smoke test with multilingual-e5-base on `basic.jsonl` passed (German/English paraphrases share groups, all checks pass). The NLI model's training data includes XNLI and ANLI, both CC BY-NC 4.0; under constitution 2.1.0 it makes the stage output non-commercial, so it stays blocked until the owner decides.
- [X] T062 [P] Declare retention and non-publication of the `cluster-v1` data (item pool, pair and set lists, reference answers under `data/cluster/`) in the `retention` block of `configs/productdev/jtbd/cluster-v1.yaml`, as `span-train-v1.yaml` does for its training data: "while the benchmark version is current", reviewed for deletion no later than 24 months after freezing; licences of the source chunks apply; never published (spec FR-027, constitution VI). **Deviation**: not in `topics/productdev/compliance/datasets.yaml`, whose schema is for third-party datasets (origin URL, creators, provider). Run `uv run zoo compliance check --ci`.
- [X] T009 [P] Add the extra `cluster = ["numpy>=1.26", "scipy>=1.13", "scikit-learn>=1.5", "pyyaml>=6.0", "jsonschema>=4.23", "typer>=0.12"]` to `pyproject.toml` and update `uv.lock` with `uv lock`. Mention the extra in the README Setup section. **Done 2026-10-10** locally: extra added, `uv.lock` regenerated.

---

## Phase 2: Foundational (contracts in code, bundle, stubs)

**Purpose**: Input and output formats, ids, independence units, stub models and the CLI skeleton. Every story builds on them. **No story work starts before this phase is complete.**

- [X] T010 Copy `specs/009-jtbd-dedup-cluster/contracts/cluster-input.schema.json` to `src/mobility_model_zoo/productdev/jtbd/cluster/jtbd-cluster-input-v1.schema.json` and `contracts/cluster-output.schema.json` to `src/mobility_model_zoo/productdev/jtbd/cluster/jtbd-cluster-v1.schema.json`, as package data. Test in `tests/unit/cluster/test_cluster_schemas.py`: copies equal the contracts byte for byte; both are valid Draft 2020-12 schemas; `output_format_version` must be `jtbd-cluster-v1`; ids must match `^it-[0-9a-f]{12}$`, `^dg-[0-9]{6}$`, `^cl-[0-9]{6}$`.
- [X] T011 [P] Create `tests/fixtures/cluster/` with: `stub_models.py` (a `StubEncoder` that maps quotes to fixed vectors from a JSON table and hashes unknown quotes to random unit vectors with a fixed seed; a `StubNLI` that returns entailment probabilities from a table), `bundles/basic.jsonl` (about 30 sources, German and English, with known paraphrase pairs, two sources with the same `text_sha256`, a forum reply quoting its parent under the same `origin`, one undated source, one source with `relevant: false` and no items), `bundles/more.jsonl` (10% more sources for continuity tests), `bundles/mixed_kinds.jsonl` (a job, two of its pains, a gain, and a more specific variant of the job), and `bundles/bad_version.jsonl` (an output with `output_format_version: jtbd-span-v0`). All texts fictional.
- [X] T012 Implement `src/mobility_model_zoo/productdev/jtbd/cluster/bundle.py` per data-model.md "Input" and "Item": `read_bundle(path)` validates every line against `jtbd-cluster-input-v1` and the embedded output against `jtbd-span-v1` (`src/mobility_model_zoo/productdev/jtbd/span/jtbd-span-v1.schema.json`), refuses any other `output_format_version` with `ValueError` naming the line, refuses duplicate `source_id`; `item_id(source_id, start, end, kind)` = `"it-"` + first 12 hex of SHA-256 over the four values joined by `\x00`; `exact_copy_key(kind, quote)` = SHA-256 over kind and the quote after Unicode NFKC, casefold, whitespace collapse and stripping surrounding punctuation (research R4); `independence_key(source)` = `origin` if set, else `source_id`, with sources sharing a non-null `text_sha256` collapsed to the key of the first such source in `source_id` order (research R3); items carry `date` from the source or `null` (FR-016). Quotes are copied, never modified (FR-002). Tests in `tests/unit/cluster/test_cluster_bundle.py`.
- [X] T013 [P] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/embed.py`: an `Encoder` protocol (`embed(quotes) -> np.ndarray` of L2-normalised float32 rows); `HFEncoder.from_settings(encoder_settings)` loading `AutoModel` and `AutoTokenizer` at the pinned revision, adding the configured prefix, mean pooling over the attention mask, normalising, CPU, `torch.inference_mode()`; `EmbeddingCache(map_dir, model_id, revision)` storing vectors under `cache/embeddings/` keyed by SHA-256 of the normalised quote, so a re-run embeds only new quotes and old vectors are reused bit-identically (research R6). Tests in `tests/unit/cluster/test_cluster_embed.py` with the stub encoder: cache hit returns identical bytes; changing the revision misses the cache.
- [X] T014 [P] Implement the first part of `src/mobility_model_zoo/productdev/jtbd/cluster/checks.py`: `validate_result(result)` against `jtbd-cluster-v1`, and the semantic checks of FR-026 that need only items and groups: every item is a member of exactly the group named by its `group_id`; quotes are byte-identical to the bundle; all members of a group share its `kind`; `counts.mentions` equals the number of members; `counts.independent_sources` equals the number of distinct `independence_key`s. Each check returns a named pass/fail with the offending ids. Tests in `tests/unit/cluster/test_cluster_checks.py` with hand-built valid and broken results.
- [X] T015 Create `src/mobility_model_zoo/productdev/jtbd/cluster/cli.py` with an empty `typer` sub-app `cluster`, register it in `src/mobility_model_zoo/productdev/jtbd/cli.py` as `app.add_typer(cluster_app, name="cluster")`, and create `src/mobility_model_zoo/productdev/jtbd/cluster/__init__.py` exporting `ClusterStage` and `read_bundle` (lazy import of `stage`). Exit codes as in contracts/cli.md and `errors.py`: 0 ok, 1 validation failed, 2 usage, 3 frozen artifact changed, 4 budget guard, 6 backend failure or model version changed mid-run.

**Checkpoint**: Bundles load and validate, items have stable ids and independence keys, results can be validated.

---

## Phase 3: User Story 1 - Duplicates become evidence-backed groups (Priority: P1) 🎯 MVP

**Goal**: One run turns scout outputs into duplicate groups with representative quotes, member lists and counts.

**Independent Test**: quickstart S1 on `tests/fixtures/cluster/bundles/basic.jsonl` with stub models: `jtbd cluster check` exits 0; every item in exactly one group; quotes byte-identical; no group mixes kinds; the two sources with the same text count as one independence unit; the German/English paraphrase pair is one group.

### Tests for User Story 1

- [X] T016 [P] [US1] Write `tests/unit/cluster/test_cluster_dedup.py`: exact copies are must-linked before similarity; items of different kind never share a group even at cosine 1.0; a chain A≈B≈C with A far from C does not collapse into one group under average linkage; a group of one is kept; output is identical for shuffled input order; memory stays sparse (no dense n×n matrix is built for n = 5,000 stub items, checked by patching `numpy` allocation size or by asserting the neighbour graph type is `scipy.sparse`).
- [X] T017 [P] [US1] Write `tests/integration/test_cluster_us1.py`: run `jtbd cluster run --input tests/fixtures/cluster/bundles/basic.jsonl --map <tmp>` with stub models injected through a test settings file, then `jtbd cluster check --map <tmp>` exits 0; `bad_version.jsonl` exits 1 with a message naming the line; the source with no items is counted as processed.

### Implementation for User Story 1

- [X] T018 [US1] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/dedup.py` per research R7: per kind, k-nearest neighbours (k from settings) by blocked matrix products on normalised vectors, keeping edges with cosine ≥ `candidate_floor` as a `scipy.sparse` connectivity matrix; exact-copy must-links merged first; `sklearn.cluster.AgglomerativeClustering(linkage="average", metric="cosine", connectivity=…, distance_threshold=1 - t_dup, n_clusters=None)` on each connected component; deterministic order by item id; returns a list of member lists per kind. Accepts optional must-link and cannot-link sets for later use by corrections (T048), unused in this story.
- [X] T019 [US1] Implement group assembly in `src/mobility_model_zoo/productdev/jtbd/cluster/stage.py`: `ClusterStage.from_settings(path)` (loads encoder, thresholds, neighbours, levels; NLI loaded lazily in US3), `ClusterStage.run(sources, map_dir=None)`; groups get `group_id` `dg-` + 6 digits assigned in order of their smallest member item id (continuity comes in US4), `kind`, sorted `members`, `representative` = member with the highest mean cosine to the other members, ties by item id (research R9), `parent: null`, `children: []`, `counts` (`mentions`, `independent_sources`, `independence_rule`: `origin` if every member's source has an origin, `source_id` if none has, else `mixed`), `distributions` (counts per value of actor_type, evidence_type, evidence_scope present in scout's `dimensions`), `dates` (`first`, `last`, `undated`), `statement: null`, `assignments: []`, `corrected: false`; `clusters: []` until US3; `settings` with `settings_sha256` of the settings file, encoder `model_id` and `revision`, thresholds; `inputs` with bundle SHA-256s and counts; `checks` from T014. Writes `result.json` into `map_dir` when given.
- [X] T020 [US1] Add `jtbd cluster run` and `jtbd cluster check` to `src/mobility_model_zoo/productdev/jtbd/cluster/cli.py` per contracts/cli.md (`--input` repeatable, `--map`, `--settings` defaulting to `configs/productdev/jtbd/cluster-baseline.yaml`). `check` re-reads the bundles listed in `inputs.bundles` to verify quotes byte for byte and exits 1 on any failed check.
- [X] T021 [US1] Add `jtbd cluster collect --run <span-run> --out <bundle.jsonl>` in `src/mobility_model_zoo/productdev/jtbd/cluster/cli.py` in `src/mobility_model_zoo/productdev/jtbd/cluster/collect.py` (needs the `jtbd` extra, so not in `bundle.py`): one source line per chunk of the span run, `source_id` = chunk id, `source_class` = chunk `source_type`, `date` = chunk `date`, `origin` = the snapshot's `origin_url` without query string, `text_sha256` = SHA-256 of the chunk text, `output` = the run's parsed `jtbd-span-v1` document unchanged. No author field is written (research R3). Test in `tests/unit/cluster/test_cluster_collect.py` on the span fixtures of feature 004.

**Checkpoint**: The MVP works: a deduplicated list of needs with counts and verbatim evidence (spec SC-001 on real scout outputs).

---

## Phase 4: User Story 2 - Quality is measured against a frozen reference (Priority: P1)

**Goal**: Benchmark `cluster-v1`, reference labels, agreement pilot with a decision per level, tuned and scored training-free baseline.

**Independent Test**: quickstart S2: `agreement.json` with kappa and B-cubed F1 per level, CIs and decisions; contested pairs separate; `tune --split test` refused; `score-*.json` per level with the ratio to the reference-vs-reference value.

### Tests for User Story 2

- [X] T022 [P] [US2] Write `tests/unit/cluster/test_bench.py`: the dev/test/holdout split is by snapshot (no snapshot in two splits); pairs are same-kind only; strata shares match the config within one pair; samplers are only LaBSE and lexical, never a candidate encoder; the pilot holdout chunks are never in the pool; the same seed gives the same lists.
- [X] T023 [P] [US2] Write `tests/unit/cluster/test_cluster_metrics.py`: pair precision/recall/F1 on hand cases; B-cubed precision/recall/F1 equal published worked examples (Amigó et al. 2009 toy cases); kappa per level reuses `src/mobility_model_zoo/productdev/jtbd/metrics.py:kappa`; contested pairs are excluded from the score and counted; ratio to reference computed per level.
- [X] T024 [P] [US2] Write `tests/unit/cluster/test_label.py` with the `mock` backend: pair batches of 20; answers outside `same | a_more_specific | b_more_specific | different` are invalid; a set answer that misses or repeats an item is invalid and retried up to the runner's limit, then excluded and counted; raw responses are written once and never overwritten; a changed guideline hash exits 3; the budget guard exits 4; only models with `role: reference` and `benchmark_labeler: true` are accepted; the pre-send check runs on every batch.
- [X] T025 [P] [US2] Write `tests/unit/cluster/test_decide_tune.py`: decisions `go`, `revise`, `rethink` per level from fixed agreement values and `cluster-criteria.yaml`; at most one rerun; `tune` refuses `--split test` and `--split holdout` with exit 2; the chosen thresholds and the full grid are written into a new settings file.

### Implementation for User Story 2

- [X] T026 [US2] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/bench.py` per research R10: build the item pool from the configured span run with `collect` (T021); split sources by snapshot into `dev` (30%) and `test`, plus the holdout reserve; sample same-kind pairs per split and stratum from LaBSE cosine and lexical token-set ratio (`rapidfuzz.fuzz.token_set_ratio`); build neighbourhood sets of 40 items (a seed and its 39 nearest neighbours by LaBSE, any kind); write `data/cluster/bench/cluster-v1/{pairs,sets,pool}.jsonl`. Add `jtbd cluster bench build --config …` to `cluster/cli.py`. **Done 2026-10-10**: the holdout reserve is a share of snapshots of its own (`holdout_fraction: 0.15` in `cluster-v1.yaml`), taken before dev (30%), so test is 55% of the snapshots and no snapshot is in two splits; the LaBSE sampler embeds with CLS pooling; the pool keeps each item's snapshot and redaction patterns version for the pre-send check, and `pool-bundle.jsonl` keeps the bundle lines for scoring.
- [X] T027 [US2] Implement freezing in `src/mobility_model_zoo/productdev/jtbd/cluster/bench.py` using `src/mobility_model_zoo/productdev/jtbd/freeze.py` helpers (`sha256_canonical`, `sha256_text`): manifest `topics/productdev/benchmarks/cluster-v1/manifest.json` with `version`, `state` (`draft` → `frozen`), `frozen_at` and `hashes` of guideline, examples, prompt, wire schema, criteria, budget file, pair list, set list and item pool; pair and set lists with ids, item ids, split and stratum only, never text. Add `jtbd cluster freeze --config …`. **Done 2026-10-10**: after a `revise` decision `jtbd cluster freeze` freezes a revised guideline, examples and prompt once more (everything else must be unchanged) for the re-pilot.
- [X] T028 [US2] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/prompt.py`: system prompt built from the frozen guideline and examples; wire schema for pair batches (`{"pairs": [{"pair_id": str, "label": "same"|"a_more_specific"|"b_more_specific"|"different"}]}`) and for sets (`{"clusters": [{"cluster_id": str, "members": [item ids]}], "coarse": [{"group_id": str, "clusters": [cluster ids]}] | null}`, the optional coarse partition grouping fine clusters for a second cluster level); `prompt_sha256` included in the manifest hashes.
- [X] T029 [US2] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/label.py` per research R11: units are pair batches and sets; uses `labeling/base.py:make_backend`, `budget.guard` and `budget.record` under `budget_name: cluster-v1`, `compliance/presend.py:check_batch` before each call and `check_answer` after hosted answers; raw responses under `data/cluster/runs/<run_id>/raw/` written once; parsed `pairs.jsonl` and `sets.jsonl`; manifest like `LabelRunManifest` (role `reference`, backend, model version, settings, cost, excluded units, status); resumable; stops with exit 6 on a model version change. Add `jtbd cluster label --model … --split test|holdout`. **Done 2026-10-10**: `--split dev` is also accepted, because tuning (T032) needs reference labels of the development pairs; the holdout split unlocks after a `revise` decision.
- [X] T030 [US2] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/metrics.py`: reference-vs-reference kappa on `same` vs. not-same; kappa on {a more specific, b more specific, neither} over pairs both call not-same; B-cubed F1 between the two references' fine partitions per set, averaged, and the same on the coarse partitions where both references gave one (cluster level 2); bootstrap CIs with `metrics.py:bootstrap_ci` over pairs and sets; consensus (`consensus.jsonl`) and contested (`contested.jsonl`); candidate scores per level (pair P/R/F1 and B-cubed P/R/F1 for duplicates on test pairs and sets, specificity P/R/F1, cluster B-cubed F1) with contested pairs scored neutrally. Write `data/cluster/analysis/cluster-v1/agreement.json`. Add `jtbd cluster agreement --split …`. **Done 2026-10-10**: `--split dev` writes `agreement-dev.json` and `consensus-dev.jsonl` for tuning only and does not change the benchmark state; candidate cluster scores are the mean B-cubed F1 against each reference's partition.
- [X] T031 [US2] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/decide.py` and `jtbd cluster decide`: apply the frozen `cluster-criteria.yaml` (verify its hash against the manifest, exit 3 on change) to `agreement.json`; per measurement level (duplicate, specificity, cluster level 1, cluster level 2) `go`, `revise` or `rethink`; advance the manifest state `frozen` → `piloted` → `decided`; write `data/cluster/analysis/cluster-v1/decision.json` with `specificity_produced`, `cluster_levels_produced` (0, 1 or 2) and, for a duplicate level that ends `rethink`, `task_stopped: true`. The stage reads this file and does not produce a level that is not `go` (spec FR-024). **Done 2026-10-10**: decisions use the point estimate against the threshold; the stage reads the file named by `decision:` in its settings and refuses to run when the task is stopped.
- [X] T032 [US2] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/tune.py` and `jtbd cluster tune --settings … --split dev`: grid over `t_dup` (0.80–0.95, step 0.01) on development pairs only, selected by duplicate pair F1; write a new settings file with the chosen value and the full grid under `tuning:`; refuse `test` and `holdout`. Specificity and cluster thresholds are added in T043.
- [X] T033 [US2] Add `jtbd cluster score --settings …` (the command only; the owner scores on test once, in T044, after US3): run the stage on the test pool, score each level against the consensus with T030, write `data/cluster/analysis/cluster-v1/score-<settings name>.json` with every number named as agreement with `claude-reference` and `gpt-mini-reference` on `cluster-v1`, the ratio to the reference-vs-reference value per level, the deterministic check results and `settings_sha256`. At most three candidates may be scored on test (research R5), counted by encoder model id across all score runs; a fourth exits 2, and a second score run of the same candidate is allowed only with an unchanged settings hash.
- [X] T034 [US2] **(ops)** After T063, freeze the benchmark: `jtbd cluster bench build` and `jtbd cluster freeze` on the stored chunks; commit the manifest. Check that `data/` is not staged. **Done 2026-10-10**: frozen with 12,783 items from 165 snapshots (dev 50, test 90, holdout 25). Before the freeze, spot checks changed three sampling details, all recorded in `cluster-v1.yaml`: LaBSE embeds with its pooler (dense + tanh) instead of plain CLS, which separates unrelated quotes better; the lexical sampler uses `token_sort_ratio`, because `token_set_ratio` scores 1.0 for any word subset and filled the high stratum with short generic quotes; `high` and `middle` draw from the top 1% and the 1-20% band of ranked neighbour pairs, because the pool holds few paraphrases. 33 fragments without a word (".", "B.", "Dr.") stay in the pool but are not sampled. `data/` is not staged.
- [X] T063 [US2] **(ops)** Before T034: run the released `scout-large` over every pool chunk (pilot-v2 main and `span-train-v1`, no holdout) with `jtbd span label` and record the run id in `configs/productdev/jtbd/cluster-v1.yaml` (`pool.span_run`). Local, no cash. **Done 2026-10-10**: the pilot part is the existing candidate run c1 of the released scout-large 0.1.2 (`data/models/span-xlmr-c1`, byte-identical to the release files); `jtbd span label` cannot run over span-train-v1 (it is the candidate evaluation of feature 004), so the new `jtbd cluster extract` wrote `run-student-scout-large-pool-932c33e3a85a-train` over its 1,100 chunks (split `train`). Both run ids are in `cluster.pool.span_run`.
- [ ] T035 [US2] **(ops)** Label the test split with both references (`jtbd cluster label --model claude-reference --split test`, then `gpt-mini-reference`), within the €20 budget. Label the dev split the same way (needed by T032; 400 pairs and 4 sets per model).
- [ ] T036 [US2] **(ops)** Run `jtbd cluster agreement --split test` and `jtbd cluster decide`. **GATE**: if the duplicate level is `revise`, revise the guideline once (new guideline version, re-freeze), label the holdout split and decide on it; a duplicate level that ends `rethink` stops the task here with the outcome recorded in `topics/productdev/reports/cluster-v1/`.

**Checkpoint**: The task has a frozen reference and a measured agreement per level.

---

## Phase 5: User Story 3 - Groups form a hierarchy of opportunities (Priority: P2)

**Goal**: More specific groups under more general ones, clusters across kinds in one or two levels, and the two views.

**Independent Test**: quickstart S3 on `tests/fixtures/cluster/bundles/mixed_kinds.jsonl` with stub models: the specific job group is a child of the general job group; job, pains and gain share a cluster; `kinds` shows all three; `tree.md` shows the nesting; `needs.csv` lists every group exactly once per kind.

### Tests for User Story 3

- [ ] T037 [P] [US3] Write `tests/unit/cluster/test_specificity.py` with the stub NLI: A entails B and B does not entail A makes A a child of B; both directions entailing gives no link; links never cross kinds; each group has at most one parent (the most similar general candidate, ties by id); a cycle A→B→C→A is broken at its weakest edge, ties by id; with `specificity_produced: false` no `dg-` parents are set.
- [ ] T038 [P] [US3] Write `tests/unit/cluster/test_hierarchy.py`: clusters may mix kinds; a child group sits under its parent group and inherits the parent's cluster; level 2 clusters contain only level 1 clusters or top-level groups; `counts`, `distributions`, `dates` and `kinds` of every cluster equal the aggregate over all items below; filtering by kind lists every group of that kind exactly once; the structure is a forest without cycles.

### Implementation for User Story 3

- [ ] T039 [US3] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/specificity.py` per research R8: candidate pairs are same-kind group pairs that are neighbours with representative cosine in `[t_spec, t_dup)`; an `NLI` protocol plus `HFNLI.from_settings` (pinned revision, CPU, batched, premise/hypothesis in both directions, entailment probability); parent choice and cycle breaking as tested in T037; skipped entirely when the decision file says `specificity_produced: false`.
- [ ] T040 [US3] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/hierarchy.py` per research R9: group centroids (normalised mean of member vectors); average linkage across kinds on a sparse k-nearest-neighbour graph of centroids for each configured level, coarser level built on the finer level's clusters; only top-level groups (no `dg-` parent) are clustered, children follow their parent; cluster ids `cl-` + 6 digits in order of their smallest item id; `representative` = item below the node with the highest mean cosine to the node's items, ties by item id; aggregates including `kinds`.
- [ ] T041 [US3] Wire specificity and hierarchy into `ClusterStage.run` in `src/mobility_model_zoo/productdev/jtbd/cluster/stage.py`, producing only the levels that `decision.json` allows (no file: all levels, marked `measured: false` in `settings`); set `settings.nli`, `settings.specificity_produced` and the produced cluster levels; extend `src/mobility_model_zoo/productdev/jtbd/cluster/checks.py` with the remaining FR-026 checks: a group's `dg-` parent has the same kind; every node has at most one parent; no cycles; parent and children lists agree; aggregates equal the items below; the representative is an item below the node.
- [ ] T042 [US3] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/report.py` and `jtbd cluster report --map … [--out …]` per research R16: `tree.md` (top-level nodes by descending independent sources; each line with id, kind or kinds, mentions, independent sources and the representative quote in quotation marks; children indented; statements shown when present) and `needs.csv` (columns `group_id, kind, mentions, independent_sources, first_date, last_date, parent, top_cluster, representative_quote`); both rendered from `result.json` only. Test in `tests/unit/cluster/test_report.py`.
- [ ] T043 [US3] Extend `jtbd cluster tune` (T032) with `t_spec` (0.65–0.85, step 0.05), `t_nli` (0.6–0.9, step 0.1) and the cluster level thresholds on development pairs and sets, selecting by duplicate pair F1, then specificity F1, then cluster B-cubed F1; extend `jtbd cluster score` (T033) to the specificity and cluster levels; both skip levels that `decision.json` marks as not produced.
- [ ] T044 [US3] **(ops)** Tune each candidate on dev (`jtbd cluster tune --settings configs/productdev/jtbd/cluster-baseline.yaml --split dev`, same for the two other candidate files), then score at most three tuned settings files on test (`jtbd cluster score`). Each candidate is scored on test once. Record which candidate meets the baseline bar per level (spec SC-003); if none meets it on the duplicate level, record that a trained model is to be decided in a new feature (spec FR-025).

**Checkpoint**: A result can be read as the opportunity layer of an Opportunity Solution Tree and as a needs list by kind.

---

## Phase 6: User Story 4 - An opportunity map can be continued (Priority: P2)

**Goal**: Stable ids across runs, human corrections that persist, a change report, identical output for identical input.

**Independent Test**: quickstart S4: after adding `more.jsonl`, at least 95% of groups with unchanged members keep their id; merge, split and move show `applied`; a correction on removed items shows `stale`; merging a pain with a job shows `refused`; two identical runs give byte-identical `result.json`.

### Tests for User Story 4

- [ ] T045 [P] [US4] Write `tests/unit/cluster/test_continuity.py`: unchanged groups keep their id; a new item joining a group keeps the group id; merge keeps the id with the most previous members, ties to the older id; split keeps the id on the part with the most previous members, the other parts get new ids from the counter; counters never reuse an id; `changes.json` lists new, grown, shrunk, merged, split and removed nodes.
- [ ] T046 [P] [US4] Write `tests/unit/cluster/test_corrections.py`: `merge`, `split`, `move` and `representative` from `corrections.yaml` take precedence over the automatic result and survive a re-run on extended input; operations refer to item ids; an operation whose items are all missing is `stale`; merging groups of different kind and a specificity move across kinds are `refused` with a reason; moving a group of another kind into a cluster is `applied`; operations apply in file order; affected nodes have `corrected: true`.
- [ ] T047 [P] [US4] Write `tests/integration/test_cluster_us4.py`: run on `basic.jsonl`, add three corrections with `jtbd cluster correct`, run on `basic.jsonl` + `more.jsonl`, check SC-004 (≥ 95% of unchanged groups keep their id; 100% of applicable corrections in effect), then run the same command twice and compare `result.json` byte for byte (FR-020).

### Implementation for User Story 4

- [ ] T048 [US4] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/corrections.py` per research R14 and data-model.md "Correction": load and validate `corrections.yaml` (`op` one of `merge`, `split`, `move`, `representative`; `items` for merge, `sets` for split, `item` and `under` (item id or null) for move, `item` for representative; optional `note`); compile to must-link sets, cannot-link sets, parent pins and representative pins; status per operation `applied`, `stale` or `refused` with reason; written into `result.checks.corrections`.
- [ ] T049 [US4] Apply corrections in `src/mobility_model_zoo/productdev/jtbd/cluster/stage.py` after the automatic step: must-links merge groups (refused across kinds), cannot-links split a group by assigning each remaining member to the nearest of the separated seeds, pins override parents (refused for a `dg-` parent of another kind), representative pins replace the representative; recompute aggregates; mark `corrected`.
- [ ] T050 [US4] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/continuity.py` per research R13: `state.json` with counters for `dg-` and `cl-`, previous membership by node id and `settings_sha256`; one-to-one matching of new to previous nodes by Jaccard over item ids (`scipy.optimize.linear_sum_assignment`, minimum overlap > 0); merge and split id rules as tested in T045; `changes.json` per data-model.md "Change report". Call it from `stage.py` before writing `result.json`. A settings hash change is recorded in `changes.json`.
- [ ] T051 [US4] Add `jtbd cluster correct --map … merge <it>… | split <it>… -- <it>… | move <it> --under <it>|--top | representative <it>` to `src/mobility_model_zoo/productdev/jtbd/cluster/cli.py`, appending to `corrections.yaml` with the same validation as the loader.
- [ ] T052 [US4] Make the run deterministic (FR-020): sort sources and items by id before every step, use the embedding cache for all vectors, fix `torch` to deterministic CPU inference with one thread count recorded in `settings`, serialise `result.json` with sorted keys and a fixed float format.

**Checkpoint**: A map can be run again on new texts without losing ids or manual work.

---

## Phase 7: User Story 5 - Downstream methods can attach their own information (Priority: P3)

**Goal**: Statements and assignments stored with the map and merged into every result; source dates on every item.

**Independent Test**: quickstart S5: after `annotate` and a re-run, the cluster still carries the statement and the assignment with origin `person`; undated items are counted.

### Tests for User Story 5

- [ ] T053 [P] [US5] Write `tests/unit/cluster/test_annotations.py`: statements (`text`, `by` matching `^(person|model:.+)$`, `at` as ISO date) and assignments (`scheme`, `value`, `origin` matching `^(person|model:.+)$`) are merged into the node with that id; several schemes coexist; annotations survive a re-run while the id is kept; annotations on a removed id are listed under `orphaned_annotations` in `changes.json`; this feature never writes a statement on its own (the stage leaves `statement: null` without annotations).

### Implementation for User Story 5

- [ ] T054 [US5] Implement `src/mobility_model_zoo/productdev/jtbd/cluster/annotations.py` per research R15 and data-model.md "Annotation": read and validate `annotations.jsonl`, merge by node id into `result.json`, report orphans to `continuity.py`.
- [ ] T055 [US5] Add `jtbd cluster annotate --map … --node <id> [--statement <text>] [--assign <scheme>=<value>]… --by person|model:<id>` to `src/mobility_model_zoo/productdev/jtbd/cluster/cli.py`, appending one line to `annotations.jsonl` with today's date.

**Checkpoint**: All five stories work on the fixtures.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T056 Implement `src/mobility_model_zoo/productdev/jtbd/cluster/perf.py` and `jtbd cluster perf --settings … [--scale N]` per research R17: the stage runs in a child process; wall time and peak RSS from the child; `--scale` builds a scale set by resampling real pool items with unique source ids and a non-word suffix that defeats exact-copy merging; the record states machine, item count, origin (`real` or `scale-set`) and that models were cached and network was off. Test in `tests/unit/cluster/test_perf.py` with stub models and a small scale.
- [ ] T057 **(ops)** On the reference VM (8 GB RAM, 4 vCPU, no GPU), models downloaded beforehand, network off: `jtbd cluster perf` on the real pool and with `--scale 50000` for every candidate scored in T044 (constitution III). Check SC-005 (≤ 15 min, ≤ 4 GB) for the chosen candidate. Delete the VM afterwards; record its cost in the ledger.
- [ ] T058 [P] Write `topics/productdev/reports/cluster-v1/report.md` and the figure `topics/productdev/reports/cluster-v1/pareto.png`: benchmark composition, reference agreement per measurement level with CIs and decisions, contested counts, candidate scores per level with ratios to the reference, a quality-vs-cost Pareto front of all scored candidates (duplicate pair F1 against wall time and peak memory on the reference VM, constitution III), chosen candidate, speed and memory with origin, cash spent (SC-007), known limits (short and generic quotes, levels not produced, scale set instead of 50,000 real items). The report MUST NOT quote corpus texts; examples are fictional (constitution VI, IX).
- [ ] T059 **(ops)** Reader check (SC-006): give `result.json`, `tree.md` and `needs.csv` from a real run to a person who did not build the stage; record time and outcome in the report of T058.
- [ ] T060 [P] Update `README.md` (task row in the Topics table, quick command `uv run jtbd cluster --help`), `topics/productdev/README.md` and `docs/layout.md` if it lists task subpackages.
- [ ] T061 Run `uv run ruff check`, `uv run pytest`, `uv run zoo compliance check --ci` and the quickstart scenarios S1, S3, S4 and S5 on the fixtures; fix what fails.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: T002–T009 and T062 can start now; T004 must be committed before T035. Task ids are stable since the first publication; T062 and T063 were added later and run where they are listed (T062 in Phase 1, T063 before T034).
- **Foundational (Phase 2)**: depends on T009 (extra) for imports; blocks every story.
- **US1 (Phase 3)**: after Phase 2. MVP.
- **US2 (Phase 4)**: T022–T032 after Phase 2; T033 needs US1 (stage). The ops tasks T034–T036 need T003–T006 committed and the released `scout-large` span run.
- **US3 (Phase 5)**: after US1; T043–T044 also need US2 (T030–T033, decision T036).
- **US4 (Phase 6)**: after US1; corrections of hierarchy (move) need US3.
- **US5 (Phase 7)**: after US1; orphan reporting needs US4 (T050).
- **Polish (Phase 8)**: T056 after US1; T057 after T044; T058–T059 after T044 and T057.

### Within each story

Tests first and failing, then implementation, then CLI wiring, then ops.

### Parallel opportunities

- Phase 1: T002, T003, T004, T005, T006, T007, T009, T062 in parallel (T008 after T005 and T007).
- Phase 2: T011, T013, T014 in parallel after T010; T012 after T011.
- US2: T022–T025 (tests) in parallel; T026–T032 can be built while US1 is in progress, since they use the stage only in T033.
- US3, US4 and US5 tests (T037, T038, T045, T046, T047, T053) in parallel once US1 is done.

## Parallel example: User Story 2

```bash
Task: "Write tests/unit/cluster/test_bench.py"
Task: "Write tests/unit/cluster/test_cluster_metrics.py"
Task: "Write tests/unit/cluster/test_label.py"
Task: "Write tests/unit/cluster/test_decide_tune.py"
```

## Implementation strategy

### MVP first (User Story 1)

1. Phase 1 and Phase 2.
2. Phase 3: deduplication with counts and verbatim evidence.
3. Stop and validate with quickstart S1 on fixtures, then on a real span run (spec SC-001).

### Incremental delivery

1. US1 → deduplicated list of needs (usable for a first manual opportunity map).
2. US2 → measured: benchmark, agreement, baseline score; no cash before T035.
3. US3 → hierarchy and the two views.
4. US4 → maps can be continued with manual work preserved.
5. US5 → slots for statements and assignments.

## Notes

- No task trains or releases a model. If the baseline misses the bar on the duplicate level (T044), a trained model is a new feature with its own spec (spec FR-025).
- Thresholds are tuned on `dev` only; `test` is used once per candidate, for at most three candidates (T044); `holdout` only for one re-pilot (T036).
- A measurement level that fails the pilot is not produced (spec FR-024, `decision.json`).
- Commit after each task or logical group; never stage `data/` or `.env`.
