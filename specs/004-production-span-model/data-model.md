# Data Model: Production span model

Phase 1 of [plan.md](plan.md). Existing pilot entities (snapshot, chunk, run, consensus, score) keep their definitions from `specs/001-jtbd-extraction-pilot/data-model.md`; only additions and changes are listed. Release entities (model, release record, results) are defined in `specs/003-model-zoo-hf-release/data-model.md`.

## Training dataset `span-train-v1`

Config `configs/productdev/jtbd/span-train-v1.yaml`, data under `data/span-train-v1/` (gitignored).

| Field | Type | Rule |
|-------|------|------|
| `dataset` | string | `span-train-v1` |
| `data_dir` | path | `data/span-train-v1` |
| `snapshots_dir`, `ledger` | path | shared with the pilot |
| `exclude_benchmark` | config path | `configs/productdev/jtbd/pilot-v1.yaml` (or the version of the pilot's final decision) |
| `redaction.version` | string | `redact-v2` |
| `redaction.review` | enum | `sampled` (pilot: `full`) |
| `redaction.sample` | object | `{fraction: 0.10, min: 100, always_review_source_types: [forum_review]}` |
| `composition_targets` | object | `{min_share_per_language: {de: 0.30, en: 0.30}, min_offtopic_share: 0.15, min_source_types: 3, all_sub_areas: true}`; reported, not enforced |
| `validation` | object | `{fraction_of_snapshots: 0.10, seed: 20261002}` |
| `min_usable_chunks` | int | `600`; `span train` refuses below it (FR-005) |
| `retention` | object | `{rule: "while a model trained on it is current", review_by_months_after_freeze: 24}` |

Directory layout:

```text
data/span-train-v1/
├── chunks/            # Chunk records, split = train (existing chunk schema)
├── runs/              # teacher runs (role teacher), train-split ensemble run if used
├── rows/rows.jsonl    # TrainingRow, one per usable chunk
├── rows/rows.stats.json
├── analysis/provenance.json   # data-check result
├── analysis/candidates.json   # benchmark-evaluated candidates (cap 3)
├── frozen.json        # hashes of chunks and rows (freeze-data)
└── retention.yaml
```

## Chunk (unchanged schema, new constraints)

Training chunks use the existing chunk record with `split: train`. Additional constraints checked by `--exclude-benchmark` and `span data-check`:

- the chunk's snapshot has `permitted_uses == training_allowed`;
- the snapshot, its normalized origin URL and its content hash do not occur among the snapshots of any main or holdout chunk of the excluded benchmark, including superseded snapshots;
- the snapshot is not referenced by any spike chunk in `data/spike/` (spike chunks are spike data);
- `redact-check` passed under the dataset's policy.

## Run (changed)

| Field | Change |
|-------|--------|
| `role` | adds `teacher` (labels split `train` only; model must equal `decision.json → teacher_fitness.recommended`, or be one of its members if that is the ensemble) and `student` (trained model of this task; split `main` only, the holdout stays unused) |
| `backend` | adds `span` (outputs written by `jtbd span label`, no model calls through a labeling backend) |
| `settings.dimensions` | for `span` runs: the attribute dimensions the model produces |
| `settings.model_sha256` | for `span` runs: SHA-256 of `model.safetensors` |
| `parsed/<chunk>.json` | for `span` runs: a `jtbd-span-v1` output ([contracts/span-output.schema.json](contracts/span-output.schema.json)); for all other backends unchanged |

Loading a `span` run produces `LocatedItem`s with `span = (start, end)`, `quote = text[start:end]`, `actor = None`, `statement = None` and `None` for every non-produced attribute.

## TrainingRow

One line in `rows/rows.jsonl`.

| Field | Type | Rule |
|-------|------|------|
| `chunk_id` | string | training chunk |
| `snapshot_id` | string | for the validation split by snapshot |
| `text` | string | redacted chunk text |
| `relevant` | bool | teacher's relevance decision |
| `items[]` | list | `{span: [start, end], kind, <produced attributes>}`; spans from the repaired quote location |
| `split` | enum | `train` or `val` (10% of snapshots, fixed seed) |

`rows.stats.json`: chunks in, chunks excluded (no valid teacher output), items in, items repaired, items dropped, rows per split, composition by language, source type, sub-area and off-topic share.

## Span model recipe `configs/productdev/jtbd/span-xlmr.yaml`

| Field | Value or rule |
|-------|---------------|
| `model` | `productdev-jtbd-span-xlmr` |
| `base_encoder` | `FacebookAI/xlm-roberta-large` (with revision) |
| `dataset` | `span-train-v1` |
| `benchmark_config` | pilot config of the final decision |
| `dimensions` | filled from `decision.json` (passed attribute dimensions); `relevance`, `item_matching`, `kind` are required |
| `windows` | `{max_length: 512, stride: 128}` |
| `training` | `{lr: 1.5e-5, weight_decay: 0.01, warmup: 0.10, grad_clip: 1.0, batch_size: 4, max_epochs: 8, seed: 20261002, bio_loss_weight: 0.5, relevance_loss_weight: 0.5}` |
| `thresholds.unit_grid` | `[0.2, 0.3, 0.4, 0.5, 0.6]` |
| `selection` | `{benchmark_candidate_cap: 3, rule: "among candidates that meet every release_bar condition, the highest comparison composite; within 0.02, the one with the higher chunks_per_min; if none meets the bar, none is selected"}`; fixed before training, applied by `jtbd span select` |
| `release_bar` | `{beat_every_zero_shot_baseline_on: comparison_composite, deterministic_checks: {quotes_verbatim: 1.0, schema_valid: 1.0, consistency: 1.0}, max_peak_ram_gb: 4, max_latency_s_9k: 10}` |
| `release_bar_changes` | list of `{date, change, rationale}`; empty unless the bar is changed after training started (Principle IV) |
| `committed_before_training` | checked: the commit that introduced `release_bar` precedes the first training run's recorded commit |

## SpanModelVersion (model files)

See [contracts/model-files.md](contracts/model-files.md). `span_config.json` holds labels, produced dimensions, thresholds, windows, base encoder, hyperparameters, seed, dataset hash, best epoch, validation scores and the recipe commit.

## Candidate

One entry in `analysis/candidates.json` per model evaluated on the benchmark.

| Field | Rule |
|-------|------|
| `candidate_id` | `c1` … `c3` |
| `model_sha256` | of `model.safetensors` |
| `change` | what differs from the previous candidate and why (decided before evaluation) |
| `run_id` | the `student` run on the main split |
| `scores` | path to the score file |
| `selected` | at most one `true`; the published one |

All candidates appear in the recipe document and on the card's limitations if more than one was evaluated.

## Comparison composite

For a set of dimensions `D` (relevance, item matching, kind, plus the produced attributes) and a model `m`: the composite computed by the harness's existing composite function restricted to `D`, from `m`'s score file on the same benchmark version. Computed for: the span model, every pilot zero-shot baseline, the recommended teacher (raw and repaired view, as scored in the pilot) and the frontier-versus-frontier reference. Dimensions outside `D` are reported separately and never mixed in.

## Results files (feature 003 schema, contents for this model)

`zoo/models/productdev-jtbd-span-xlmr/results/0.1.0/quality.json`, metrics (all with `reference`, `benchmark`, `n_items`, `date`):

- `agreement_relevance`, `agreement_item_matching`, `agreement_kind`, `agreement_<attribute>` for each produced attribute
- `comparison_composite`
- `quotes_verbatim_rate`, `schema_valid_rate`, `consistency_rate`, `contested_items`
- `comparison_composite_best_baseline` (description names the baseline), `comparison_composite_teacher`, `comparison_composite_reference`, `comparison_composite_reference_85pct`

`performance.json`, metrics (all with `hardware`):

- `latency_9k_chars_s`, `load_time_s`, `peak_ram_gb`, `chunks_per_min`

## State transitions

```text
corpus: cut → redacted → reviewed (sampled) → data-checked
            → [pilot decision available] → teacher-labeled → rows built → frozen
model:  candidate trained → thresholds tuned → evaluated (≤ 3)
            → every evaluated candidate perf-measured on reference VM → Pareto front → selected → release-checked
            → passes bar: staged → record complete → gate passes → repo public → tagged → approved → published
            → misses bar: reported, not published (terminal for 0.1.0)
```
