# Data Model: JTBD Extraction Pilot

All records are stored as files under `data/` (gitignored), except the benchmark manifest. IDs are stable strings. Hashes are SHA-256 over canonical bytes: UTF-8, LF line endings, and sorted keys for YAML and JSON.

## Source / Snapshot

A fetched document, stored once as a complete raw copy (FR-013a, crawl once). Contract: [source-snapshot.schema.json](contracts/source-snapshot.schema.json).

| Field | Type | Rules |
|-------|------|-------|
| `snapshot_id` | string | `snap-<sha256[:12]>` of the raw bytes |
| `origin_url` | string | canonical URL. **Unique**: a second fetch of the same canonical URL is refused unless `supersedes` is set |
| `source_type` | enum | `paper` (papers and industry studies), `reddit`, `forum_review`, `transcript` |
| `retrieved_at` | datetime | UTC |
| `raw_path` | path | `data/snapshots/<snapshot_id>/raw.<ext>`, never modified |
| `text_path` | path | extracted plain text, derived and re-creatable |
| `raw_sha256` | string | integrity check |
| `license` | string | SPDX ID or a short description |
| `legal_basis` | string | e.g. "CC BY 4.0", "§ 5 UrhG official work", "§ 60d UrhG, Reddit Data API" |
| `access_terms_checked` | string | ToS and robots.txt note, and the date checked |
| `permitted_uses` | enum | `benchmark_only` or `training_allowed`. Reddit is always `benchmark_only` |
| `retention_until` | date | required (Principle VI) |
| `supersedes` | snapshot_id? | only for a documented update |
| `update_reason` | string? | required when `supersedes` is set |

## Chunk

A self-contained text unit cut from a snapshot. Contract: [chunk-record.schema.json](contracts/chunk-record.schema.json).

| Field | Type | Rules |
|-------|------|-------|
| `chunk_id` | string | `ch-<nnn>` |
| `snapshot_id` | ref | must exist |
| `char_start`, `char_end` | int | position in the snapshot text. For thread replies, a list of ranges that includes the parent context (FR-009) |
| `text` | string | **redacted** text given to models; 300–1500 tokens |
| `split` | enum | `main` or `holdout` |
| `sub_area` | enum | `public_transport_rural`, `logistics_delivery`, `emobility_charging`, `car_ownership_use`, `sharing_platforms`, `none` (for irrelevant chunks) |
| `source_type` | enum | copied from the snapshot |
| `region` | enum | `DACH`, `EU_other`, `non_EU` (plus country code) |
| `language` | enum | `de`, `en` |
| `date` | date | publication date of the content |
| `license` | string | copied from the snapshot |
| `relevance_intent` | enum | `relevant`, `irrelevant`, `near_miss`. This is a collection note and is **never** shown to models |
| `redaction` | object | `{method, patterns_version, manual_review_at, check_passed}` |

**Validation**:
- The composition targets from FR-002 to FR-007 are checked separately for `main` and `holdout`.
- `redaction.check_passed` must be true before a chunk can be frozen.

## LabelingGuideline, DecisionCriteria

| Field | Type | Rules |
|-------|------|-------|
| `version` | string | e.g. `guideline-v1` |
| `path` | path | `guideline/guideline-v1.md` or `configs/decision-criteria.yaml` |
| `sha256` | string | set by `pilot freeze` |
| `frozen_at` | datetime | set once and never changed. A change creates a new version with a `rationale` |

The decision criteria follow [decision-criteria.schema.json](contracts/decision-criteria.schema.json).

## LabelRun

One model's pass over a split. Contract: [label-run-manifest.schema.json](contracts/label-run-manifest.schema.json).

| Field | Type | Rules |
|-------|------|-------|
| `run_id` | string | `run-<role>-<model-slug>-<date>` |
| `role` | enum | `reference`, `teacher_candidate`, `baseline` |
| `backend` | enum | `claude_cli`, `openrouter`, `ollama` |
| `model_id` | string | the requested ID |
| `model_version` | string | as reported by the backend: the Claude response model ID, the OpenRouter response model or version, or the Ollama digest |
| `family` | string | e.g. `anthropic-claude`, `openai-gpt`, `qwen`, `glm` |
| `host` | string | `subscription`, the OpenRouter provider name, or `spark` / `vm-<type>` |
| `quantization` | string? | required for `ollama` |
| `settings` | object | temperature (or `"not_settable"`), max tokens, structured-output mode, seed |
| `guideline_sha256`, `schema_sha256`, `criteria_sha256` | string | must match the frozen values |
| `split` | enum | `main` or `holdout` |
| `started_at`, `finished_at` | datetime | |
| `cost_eur` | number | 0 for `claude_cli` and `ollama` |
| `license_basis` | string? | required for `teacher_candidate` |

**Rules**:
- The two `reference` runs must come from different `family` values.
- A `teacher_candidate` family must differ from both reference families.
- A model used as `reference` is flagged `benchmark_labeler` and can never be a `teacher_candidate`.

## RawResponse

One per chunk and run, stored unmodified in `data/runs/<run_id>/raw/<chunk_id>.json`. Fields: `chunk_id`, `attempt`, `request_ts`, `latency_ms`, `raw_body`, `usage` (tokens), `backend_meta` (generation ID, session ID), `error?`.

## ExtractionOutput and Item

This is the parsed model output. Contract: [extraction-output.schema.json](contracts/extraction-output.schema.json).

- **ExtractionOutput**: `relevant: bool` and `items: Item[]`. An empty list is valid.
- **Item**:
  - `kind` (`job`, `pain` or `gain`)
  - `quote`
  - `actor`
  - `actor_type` (`individual`, `worker`, `organization`, `public_sector` or `society`)
  - `statement` (English)
  - `evidence_type`: `opinion` < `anecdote` < `routine` < `observation` < `measurement`, ordinal 0–4
  - `evidence_scope` (`single`, `multiple` or `quantified`)
- **Derived** (not produced by the model): `span` (`char_start`, `char_end`) from the quote locator, and `valid` (the quote was found).

## CheckResult

Fields: `run_id`, `chunk_id`, `item_index?`, `check` (`quote_verbatim`, `schema_valid` or `consistency.<rule>`), `passed`, `detail`.

The consistency rules are:
- `irrelevant_no_items`
- `enum_values`
- `quantified_has_quantity`

## ItemMatch

Fields: `chunk_id`, `run_a`, `run_b`, `item_a?`, `item_b?`, `iou`, `same_kind`.

`item_a` or `item_b` is null when an item is unmatched. The matching is one-to-one: Hungarian on IoU, with a kind bonus used only as a tie-break and a minimum IoU from `pilot-v1.yaml`.

## ConsensusEntry / ContestedEntry

- **ConsensusEntry**: `chunk_id`, `level` (`relevance` or `item`), agreed values per dimension, and the source item references.
- **ContestedEntry**: `chunk_id`, `level`, `dimensions` (the dimensions where the models disagree), the values of each reference model, `category` (primary disagreement category, assigned in the analysis) and `note`.

An item can be in the consensus for some dimensions and contested for others (FR-021, FR-022).

## ModelScore

Fields:
- `run_id` and `benchmark_version`
- per dimension: `score`, `n`, `ci_low`, `ci_high`, `underpowered` (n < 30)
- `composite`, the unweighted mean of the dimension scores
- `frontier_composite_consensus_units`: frontier-versus-frontier composite with the same metrics on the same consensus units (basis of FR-031 ratio a)
- `frontier_composite_all_units`: frontier-versus-frontier composite on all units (basis of FR-031 ratio b)
- `neutral_contested_hits`, per dimension
- `check_pass_rates`

## PerfMeasurement

Fields: `run_id`, `hardware` (VM type, vCPU, RAM, CPU model), `model_digest` (must equal the digest of the quality run), `warmup_chunks`, `chunks_per_min`, `output_tok_per_s`, `latency_p50_ms`, `latency_p95_ms`, `peak_rss_mb`, `measured_at`.

## BudgetLedger

Append-only JSONL with these fields: `ts`, `item` (a run ID or `vm`), `estimated_eur`, `actual_eur`, `cumulative_eur`, `cap_eur`.

The guard refuses a run when `cumulative + estimated > budget` (€20), and also when it would exceed the key cap (€12).

## BenchmarkVersion

Fields: `version` (e.g. `pilot-v1`), `test_only` (true only for fixture configs with `test_fixture: true`), `chunk_ids` plus hashes, guideline, schema and criteria hashes, the reference run IDs, consensus and contested hashes, `frozen_at`.

**State**: `draft → frozen`. Freezing happens once reference labeling and consensus are done, and before baseline scoring. Any change creates `pilot-v2`.

## PilotDecision

Fields:
- `benchmark_version`
- per-dimension `agreement` against the thresholds
- `path`: which rows of the decision table fired
- `decision`: `go`, `revise` or `rethink`, per dimension and overall
- `finetuning`: `optional` or `required` (FR-031), with `quality_ratio_a` (against the consensus units, which decides the classification), `quality_ratio_b` (against all units, reported only), `throughput_ratio` (against GPT mini-tier chunks/min) and the model the ratios refer to
- `rerun`: `none` or `holdout`
- `deviations`: documented rationales

## Pilot state machine

```text
collecting ──► criteria_frozen ──► labeled ──► evaluated ──► decided
                                                   │
                                                   └─(revise, first time only)─► rerun_holdout ──► decided
```

- In `decided`, a dimension that still fails after `rerun_holdout` becomes `rethink` (FR-030: at most one rerun).
- `criteria_frozen` requires hashes for the guideline, schema, decision criteria and budget.
- `labeled` requires both reference runs to be complete, with at most 2% of chunks excluded per model (SC-002).
